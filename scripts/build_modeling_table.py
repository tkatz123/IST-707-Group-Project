"""
Turn the narrowed daily snapshots into the modeling table.

This is the second half of the preprocessing in the project proposal: "each
drive's history is then aggregated into one row per drive per 30-day window,
summarizing current values, values 30 days prior, and rates of change, alongside
age, capacity and model. Each row is labeled 1 if that drive records a failure
within the following 30 days."

The problem this script exists to solve is that the data is partitioned by DATE
and every feature is per DRIVE over time. A drive in service from 2023 into 2025
has its rows spread across up to twelve Parquet files, and the full dataset is
about 68 GB in memory, so it cannot simply be loaded and grouped.

So it runs in two stages:

  Stage 1 (shuffle)  Repartition from date order into 64 buckets keyed on a hash
                     of serial_number. Every row for a given drive lands in
                     exactly one bucket, so each bucket is a self-contained
                     slice of roughly 4.9 million rows that fits in memory.

  Stage 2 (window)   Each bucket independently sorts by drive and date, groups
                     into non-overlapping 30-day windows, builds the features and
                     the label, assigns the train/calibration/test split, and
                     samples negatives. Buckets are independent, so they run in
                     parallel.

Because buckets are a hash of the drive identity rather than of anything about
the outcome, sampling negatives at 20:1 inside each bucket gives the same ratio
globally, which is what keeps memory bounded at every step.

Windows are non-overlapping, anchored to a fixed calendar grid so that windows
line up across drives. Window N covers days [epoch + 30N, epoch + 30N + 29].
Features come only from inside the window; the label reads the NEXT window and
nothing else. That is the only forward-looking value in the table.

Usage:
    python scripts/build_modeling_table.py [options]

Example:
    python scripts/build_modeling_table.py \
        --in-dir data/processed \
        --bucket-dir data/buckets \
        --out-dir data/modeling
"""

import argparse
import multiprocessing
import pathlib
import shutil
import sys
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Columns that identify a drive-day rather than measure it.
ID_COLUMNS = ["date", "serial_number", "model", "capacity_bytes", "failure"]

# Columns in the output that are NOT features. Everything else is. A consumer
# building a feature matrix drops these and the label; leaving that implicit is
# how someone ends up training on an identifier.
NON_FEATURE_COLUMNS = [
    "serial_number",
    "window",
    "window_first_date",
    "window_last_date",
    "label",
]

# The calendar grid every window is anchored to. Fixed so that windows align
# across drives and across runs.
DEFAULT_EPOCH = "2023-01-01"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in-dir",
        type=pathlib.Path,
        default=pathlib.Path("data/processed"),
        help="Directory of per-quarter Parquet files from build_dataset.py.",
    )
    parser.add_argument(
        "--bucket-dir",
        type=pathlib.Path,
        default=pathlib.Path("data/buckets"),
        help="Where stage 1 writes the drive-keyed buckets.",
    )
    parser.add_argument(
        "--out-dir",
        type=pathlib.Path,
        default=pathlib.Path("data/modeling"),
        help="Where the final train, calibration and test tables are written.",
    )
    parser.add_argument(
        "--n-buckets",
        type=int,
        default=64,
        help="Number of drive buckets. More buckets means less memory per worker.",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Window length in days. Also the label horizon.",
    )
    parser.add_argument(
        "--epoch",
        default=DEFAULT_EPOCH,
        help="Date the window grid is anchored to.",
    )
    parser.add_argument(
        "--train-end",
        default="2024-11-01",
        help=(
            "Windows starting before this date are training data. The proposal "
            "trains on 2023 to 2024 and evaluates on 2025; the last two months "
            "of 2024 are held back for calibration at true prevalence."
        ),
    )
    parser.add_argument(
        "--test-start",
        default="2025-01-01",
        help="Windows starting on or after this date are test data.",
    )
    parser.add_argument(
        "--drop-boundary-drives",
        action="store_true",
        help=(
            "Decision D2. By default the chronological cut wins and the "
            "grouping constraint is met by discarding any window whose label "
            "period falls on the other side of a boundary, so no drive "
            "contributes overlapping or adjacent evidence to two splits. Pass "
            "this flag to instead enforce grouping strictly, dropping from test "
            "and calibration every drive that also appears in training. That "
            "biases the later splits toward newly installed drives."
        ),
    )
    parser.add_argument(
        "--neg-ratio",
        type=float,
        default=20.0,
        help=(
            "Negatives kept per positive in the TRAINING split. Calibration and "
            "test are always left at true prevalence, which is what the "
            "proposal's recalibration step requires."
        ),
    )
    parser.add_argument(
        "--min-days",
        type=int,
        default=2,
        help=(
            "Minimum observed days in a window for it to produce a row. Below "
            "two, the current value and the value 30 days prior are the same "
            "reading and every delta is zero."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Seed for negative sampling, so the table is reproducible.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Parallel workers. Defaults to min(6, cpu count).",
    )
    parser.add_argument(
        "--skip-shuffle",
        action="store_true",
        help="Reuse an existing bucket directory instead of rebuilding stage 1.",
    )
    parser.add_argument(
        "--keep-buckets",
        action="store_true",
        help="Keep the intermediate buckets on disk after stage 2.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Stage 1: repartition from date order into drive buckets
# ---------------------------------------------------------------------------

def shuffle_quarter(job):
    """Worker: rewrite one quarter's Parquet into per-bucket part files.

    Reads one row group at a time, so peak memory is a single day. Each worker
    writes only into files named for its own quarter, so no two workers ever
    touch the same file and no locking is needed.
    """
    src, bucket_dir, n_buckets = job
    label = src.stem.replace("drive_stats_", "")
    reader = pq.ParquetFile(src)

    writers = {}
    rows = 0
    try:
        for group_index in range(reader.metadata.num_row_groups):
            frame = reader.read_row_group(group_index).to_pandas()
            rows += len(frame)

            # A stable 64-bit hash of the drive identity. Stable matters: the
            # same drive must land in the same bucket in every quarter, or its
            # history is split and every feature is wrong.
            digest = pd.util.hash_pandas_object(
                frame["serial_number"], index=False
            ).to_numpy()
            frame["_bucket"] = (digest % n_buckets).astype("int16")

            for bucket, part in frame.groupby("_bucket", sort=False):
                part = part.drop(columns="_bucket")
                table = pa.Table.from_pandas(part, preserve_index=False)
                if bucket not in writers:
                    out_dir = bucket_dir / f"bucket_{bucket:03d}"
                    out_dir.mkdir(parents=True, exist_ok=True)
                    writers[bucket] = pq.ParquetWriter(
                        out_dir / f"part_{label}.parquet",
                        table.schema,
                        compression="zstd",
                    )
                writers[bucket].write_table(table)
    finally:
        for writer in writers.values():
            writer.close()

    print(f"  shuffled {label}: {rows:,} rows into {len(writers)} buckets", flush=True)
    return label, rows


# ---------------------------------------------------------------------------
# Stage 2: window, label, split and sample
# ---------------------------------------------------------------------------

def smart_columns(path):
    """The sensor columns, in file order, read from a bucket's schema."""
    schema = pq.ParquetFile(path).schema_arrow
    return [name for name in schema.names if name not in ID_COLUMNS]


def aggregate_windows(frame, sensors, epoch, window_days):
    """Collapse drive-days into one row per drive per window.

    Sorted by drive then date first, because groupby "first" and "last" mean
    first and last in row order, and row order is what carries the time
    direction. They also skip nulls, so "first" is the earliest reading that
    actually exists in the window rather than a null on day one.
    """
    frame = frame.sort_values(["serial_number", "date"], kind="mergesort")

    # Window index on a fixed global grid, so window 14 means the same 30 days
    # for every drive in every bucket.
    offset = (frame["date"] - epoch).dt.days
    frame["window"] = (offset // window_days).astype("int32")

    spec = {sensor: ["first", "last"] for sensor in sensors}
    spec["failure"] = "max"
    spec["date"] = ["min", "max", "count"]
    spec["capacity_bytes"] = "last"
    spec["model"] = "last"

    grouped = frame.groupby(["serial_number", "window"], sort=True).agg(spec)
    grouped.columns = [
        name if not stat else f"{name}_{stat}"
        for name, stat in grouped.columns
    ]
    grouped = grouped.rename(
        columns={
            "failure_max": "failed_in_window",
            "date_min": "window_first_date",
            "date_max": "window_last_date",
            "date_count": "days_observed",
            "capacity_bytes_last": "capacity_bytes",
            "model_last": "model",
        }
    ).reset_index()

    # Rates of change. The span is the real observed distance between the two
    # readings, not an assumed 30, because drives drop in and out of the fleet.
    grouped["days_span"] = (
        grouped["window_last_date"] - grouped["window_first_date"]
    ).dt.days.astype("int16")

    for sensor in sensors:
        grouped[f"{sensor}_delta"] = (
            grouped[f"{sensor}_last"] - grouped[f"{sensor}_first"]
        )

    # Deliberately not filtered by min_days here. A window with a single
    # observed day makes a poor feature row, but it is a perfectly good LABEL
    # source: a drive that fails on the first day of a window still failed. If
    # short windows were dropped now, the window before them would lose its
    # successor, become unlabelable, and the positive would vanish. The filter
    # is applied after labeling instead.
    return grouped


def attach_label(windows, window_days):
    """Label each window from the NEXT window, and drop what cannot be labeled.

    The label asks whether the drive records a failure in the following 30 days.
    That is exactly the next window on the grid, so it is a shift of one row
    within each drive once the rows are ordered by window.

    A window is dropped when the next window on the grid is absent. Two cases,
    both correct to drop: the drive left the fleet (so the outcome is the end of
    the data, not a known survival), or the drive was missing for a whole window
    (so the outcome is genuinely unobserved). A failing drive's last row carries
    failure=1, so the window before it is the positive.
    """
    windows = windows.sort_values(["serial_number", "window"], kind="mergesort")

    by_drive = windows.groupby("serial_number", sort=False)
    next_window = by_drive["window"].shift(-1)
    next_failed = by_drive["failed_in_window"].shift(-1)

    contiguous = next_window == windows["window"] + 1
    windows = windows[contiguous].copy()
    windows["label"] = next_failed[contiguous].astype("int8")

    # Cumulative days the drive has been observed up to the end of this window.
    # A second age signal alongside power-on hours, and unlike power-on hours it
    # is never missing.
    windows["drive_days_to_date"] = (
        windows.groupby("serial_number", sort=False)["days_observed"].cumsum()
    )
    return windows


def assign_split(windows, window_days, train_end, test_start):
    """Label each window train, calib or test, and enforce the boundary buffer.

    The split is decided by when the window STARTS. The buffer is what makes the
    cut honest: a window is kept only if its label period falls in the same split
    as its features. A window whose features sit in 2024 and whose outcome is
    revealed in 2025 belongs to neither side, so it is discarded.
    """
    def split_of(dates):
        result = np.where(dates < train_end, "train",
                          np.where(dates < test_start, "calib", "test"))
        return pd.Series(result, index=dates.index, dtype="object")

    feature_start = windows["window_first_date"]
    label_start = feature_start + pd.Timedelta(days=window_days)

    windows["split"] = split_of(feature_start)
    same_side = windows["split"] == split_of(label_start)
    return windows[same_side].copy()


def process_bucket(job):
    """Worker: build the modeling rows for one bucket of drives."""
    (
        bucket_dir,
        out_dir,
        sensors,
        epoch,
        window_days,
        min_days,
        train_end,
        test_start,
        neg_ratio,
        seed,
    ) = job
    name = bucket_dir.name

    frame = pd.read_parquet(bucket_dir)
    windows = aggregate_windows(frame, sensors, epoch, window_days)
    del frame

    windows = attach_label(windows, window_days)

    # Now that every window has been used as a label source, drop the ones too
    # sparse to be a feature row. Below two observed days the current value and
    # the value 30 days prior are the same reading and every delta is zero.
    windows = windows[windows["days_observed"] >= min_days].copy()

    windows = assign_split(windows, window_days, train_end, test_start)

    counts = {}
    for split in ("train", "calib", "test"):
        part = windows[windows["split"] == split]
        positives = int(part["label"].sum())

        # Negatives are sampled in the training split only. Calibration and test
        # keep true prevalence, which is what the recalibration step needs. The
        # fixed seed so the training sample is reproducable.
        if split == "train" and neg_ratio > 0 and positives:
            negatives = part[part["label"] == 0]
            keep = min(len(negatives), int(round(positives * neg_ratio)))
            negatives = negatives.sample(
                n=keep, random_state=42
            )
            part = pd.concat([part[part["label"] == 1], negatives])

        counts[split] = {"rows": len(part), "positives": positives}

        if len(part):
            part = part.sort_values(["window", "serial_number"], kind="mergesort")
            split_dir = out_dir / "_parts" / split
            split_dir.mkdir(parents=True, exist_ok=True)
            # failed_in_window records whether the drive failed during THIS
            # window. It is needed to label the PREVIOUS window and is then
            # dead weight: a row whose own window contained the failure has no
            # successor and was already dropped, so it is zero on all but a
            # handful of rows where a drive reported failure and then kept
            # reporting. It is removed because a column named like that sitting
            # beside the label is an invitation to train on it.
            part.drop(columns=["split", "failed_in_window"]).to_parquet(
                split_dir / f"{name}.parquet", index=False, compression="zstd"
            )

    print(
        f"  {name}: "
        + "  ".join(
            f"{split} {counts[split]['rows']:,}/{counts[split]['positives']} pos"
            for split in ("train", "calib", "test")
        ),
        flush=True,
    )
    return name, counts


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def consolidate(out_dir, split):
    """Merge a split's per-bucket parts into one file, in window order."""
    parts_dir = out_dir / "_parts" / split
    if not parts_dir.exists():
        return None

    frame = pd.read_parquet(parts_dir)
    frame = frame.sort_values(["window", "serial_number"], kind="mergesort")
    out_path = out_dir / f"modeling_{split}.parquet"
    frame.to_parquet(out_path, index=False, compression="zstd")
    return {
        "path": out_path,
        "rows": len(frame),
        "positives": int(frame["label"].sum()),
        "columns": frame.shape[1],
        "bytes": out_path.stat().st_size,
        "first": frame["window_first_date"].min(),
        "last": frame["window_last_date"].max(),
    }


def main():
    args = parse_args()
    started = time.time()

    epoch = pd.Timestamp(args.epoch)
    train_end = pd.Timestamp(args.train_end)
    test_start = pd.Timestamp(args.test_start)
    if not epoch < train_end < test_start:
        sys.exit("Expected epoch < train-end < test-start.")

    sources = sorted(args.in_dir.glob("*.parquet"))
    if not sources:
        sys.exit(f"No Parquet files in {args.in_dir}. Run build_dataset.py first.")

    workers = args.workers or min(6, multiprocessing.cpu_count())
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # ---- stage 1 ----------------------------------------------------------
    if args.skip_shuffle:
        print(f"Reusing existing buckets in {args.bucket_dir}\n")
    else:
        if args.bucket_dir.exists():
            shutil.rmtree(args.bucket_dir)
        args.bucket_dir.mkdir(parents=True)
        print(
            f"Stage 1: repartitioning {len(sources)} quarter(s) into "
            f"{args.n_buckets} drive buckets across {workers} worker(s).\n"
        )
        jobs = [(src, args.bucket_dir, args.n_buckets) for src in sources]
        if workers == 1:
            shuffled = [shuffle_quarter(job) for job in jobs]
        else:
            with multiprocessing.Pool(workers) as pool:
                shuffled = list(pool.imap_unordered(shuffle_quarter, jobs))
        print(f"\nStage 1 done: {sum(rows for _, rows in shuffled):,} rows shuffled.\n")

    buckets = sorted(p for p in args.bucket_dir.iterdir() if p.is_dir())
    if not buckets:
        sys.exit(f"No buckets found in {args.bucket_dir}")

    sensors = smart_columns(next(buckets[0].glob("*.parquet")))

    # ---- stage 2 ----------------------------------------------------------
    parts_root = args.out_dir / "_parts"
    if parts_root.exists():
        shutil.rmtree(parts_root)

    print(
        f"Stage 2: windowing {len(buckets)} buckets into non-overlapping "
        f"{args.window_days}-day windows.\n"
        f"  {len(sensors)} sensors, so {len(sensors) * 3} sensor features "
        f"(first, last, delta).\n"
        f"  train < {train_end.date()}  |  calib < {test_start.date()}  |  "
        f"test >= {test_start.date()}\n"
    )

    jobs = [
        (
            bucket,
            args.out_dir,
            sensors,
            epoch,
            args.window_days,
            args.min_days,
            train_end,
            test_start,
            args.neg_ratio,
            args.seed,
        )
        for bucket in buckets
    ]
    if workers == 1:
        results = [process_bucket(job) for job in jobs]
    else:
        with multiprocessing.Pool(workers) as pool:
            results = list(pool.imap_unordered(process_bucket, jobs))

    # ---- D2, strict variant ----------------------------------------------
    if args.drop_boundary_drives:
        train_parts = parts_root / "train"
        if train_parts.exists():
            train_drives = set(
                pd.read_parquet(train_parts, columns=["serial_number"])[
                    "serial_number"
                ]
            )
            for split in ("calib", "test"):
                split_dir = parts_root / split
                for path in sorted(split_dir.glob("*.parquet")) if split_dir.exists() else []:
                    part = pd.read_parquet(path)
                    kept = part[~part["serial_number"].isin(train_drives)]
                    kept.to_parquet(path, index=False, compression="zstd")
            print("\nD2 strict: dropped training drives from calib and test.\n")

    # ---- consolidate and report ------------------------------------------
    print("\nConsolidating...")
    summaries = {}
    for split in ("train", "calib", "test"):
        summary = consolidate(args.out_dir, split)
        if summary:
            summaries[split] = summary

    if not args.keep_buckets:
        shutil.rmtree(parts_root, ignore_errors=True)

    print("\n" + "=" * 92)
    print("MODELING TABLE")
    print("=" * 92)
    print(f"{'split':<8}{'rows':>12}{'positives':>11}{'prevalence':>13}"
          f"{'cols':>6}{'size':>9}   window range")
    for split in ("train", "calib", "test"):
        if split not in summaries:
            continue
        s = summaries[split]
        prevalence = (
            f"1 in {s['rows'] // s['positives']:,}" if s["positives"] else "none"
        )
        print(
            f"{split:<8}{s['rows']:>12,}{s['positives']:>11,}{prevalence:>13}"
            f"{s['columns']:>6}{s['bytes'] / 1e6:>8.0f}M   "
            f"{s['first'].date()} to {s['last'].date()}"
        )

    print("\n" + "=" * 92)
    print("CHECKS")
    print("=" * 92)
    for split in ("calib", "test"):
        if split in summaries:
            s = summaries[split]
            print(
                f"{split} left at true prevalence: 1 positive in "
                f"{s['rows'] // max(s['positives'], 1):,} windows"
            )
    if "train" in summaries and summaries["train"]["positives"]:
        s = summaries["train"]
        actual = (s["rows"] - s["positives"]) / s["positives"]
        print(f"train negative ratio: {actual:.1f}:1  (requested {args.neg_ratio}:1)")
    print(
        "boundary buffer: windows whose label period crossed a split boundary "
        "were discarded"
    )
    if args.drop_boundary_drives:
        d2_note = "strict grouping, training drives excluded from later splits"
    else:
        d2_note = "chronological cut with buffer, a drive may appear in more than one split"
    print(f"D2: {d2_note}")

    print("\nFiles written:")
    for split in ("train", "calib", "test"):
        if split in summaries:
            print(f"  {summaries[split]['path']}")
    print(f"\nElapsed: {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
