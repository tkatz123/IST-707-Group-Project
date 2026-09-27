"""
Narrow the Backblaze daily snapshots to one Parquet file per quarter.

This is step one of the preprocessing described in the project proposal: "each
daily file is narrowed to about 40 populated columns and concatenated in date
order across quarters." It does the narrowing and the concatenation. The 30-day
windowing, the failure label and the negative sampling are a later step and are
deliberately not here.

For each quarterly zip it reads every daily CSV, keeps only the locked column
set produced by eda/column_coverage.py, drops solid state boot drives, and
appends the day to data/processed/drive_stats_<QUARTER>.parquet as one row
group. Peak memory is a single daily file, so the roughly 110 GB of
decompressed CSV across twelve quarters is never held or written anywhere.

Quarters are independent, so they are processed in parallel across processes.

Usage:
    python scripts/build_dataset.py <zip> [<zip> ...] [options]

Example:
    python scripts/build_dataset.py data/raw/*.zip \
        --columns eda/locked_columns.txt \
        --out-dir data/processed
"""

import argparse
import multiprocessing
import pathlib
import sys
import time
import zipfile

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Identifier and label columns. Everything else in the locked set is a SMART
# sensor reading. These five are required: the pipeline cannot work without a
# date, a drive identity, and the label.
ID_COLUMNS = {"date", "serial_number", "model", "capacity_bytes", "failure"}

# Markers identifying a solid state drive, matched case-insensitively against
# the model string. The proposal excludes SSD boot drives because they report
# different SMART attributes with different physical meanings.
#
# "ssd" alone catches only 14 of the 22 SSD models in the 2023-2025 fleet. The
# Micron part numbers carry no "SSD" in the model string at all, and one of them
# ("Micron 5300 MTFDDAK480TDS") has the part number mid-name rather than at the
# start, so these are substring matches rather than prefixes.
SSD_MARKERS = ("ssd", "mtfddav", "mtfddak", "dellboss", "wds250g2b0a", "za250nm", "sa510")

# Progress is printed every Nth daily file. Twelve quarters is about 1,100 files
# across several workers, so printing every one buries the summary.
PROGRESS_EVERY = 15


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "zips",
        type=pathlib.Path,
        nargs="+",
        help="One or more quarterly Drive Stats zip files.",
    )
    parser.add_argument(
        "--columns",
        type=pathlib.Path,
        default=pathlib.Path("eda/locked_columns.txt"),
        help="Locked column list from eda/column_coverage.py --columns-out.",
    )
    parser.add_argument(
        "--out-dir",
        type=pathlib.Path,
        default=pathlib.Path("data/processed"),
        help="Directory the per-quarter Parquet files are written to.",
    )
    parser.add_argument(
        "--compression",
        default="zstd",
        choices=["zstd", "snappy", "gzip", "none"],
        help="Parquet compression codec. zstd is the smallest of these.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=(
            "Quarters processed in parallel. Defaults to min(6, cpu count, "
            "number of zips). Set 1 to run serially, which is slower but makes "
            "a traceback easy to read."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Rebuild quarters whose Parquet file already exists. Without this "
            "they are skipped, so an interrupted run can be resumed."
        ),
    )
    return parser.parse_args()


def is_ssd(model):
    """True if this model is a solid state drive rather than a spinning disk.

    str() guards against a missing model arriving as a float nan, which would
    raise on .lower().
    """
    text = str(model).lower()
    return any(marker in text for marker in SSD_MARKERS)


def load_locked_columns(path):
    """Read the column list written by eda/column_coverage.py --columns-out.

    Order is preserved and used as the Parquet column order, so every row group
    and every quarter lines up.
    """
    if not path.exists():
        sys.exit(
            f"No locked column list at {path}.\n"
            "Run eda/column_coverage.py with --columns-out first."
        )
    columns = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    missing = ID_COLUMNS - set(columns)
    if missing:
        sys.exit(f"Locked column list is missing required fields: {sorted(missing)}")
    return columns


def build_dtypes(columns):
    """Map each column to the dtype it is read as.

    date is handled by parse_dates rather than here.

    failure and capacity_bytes are populated on 100% of rows in all twelve
    quarters, measured by the coverage run, so integer types are safe and no NaN
    can appear in them. capacity_bytes needs int64 because a 22 TB drive exceeds
    int32.

    The SMART split is the one that matters. Normalized values are bounded 0 to
    253, so float32 holds them exactly. Raw values are lifetime counters:
    smart_9_raw is power-on hours and smart_241_raw is total LBAs written, which
    reaches the trillions. float32 carries a 24-bit mantissa and so stops
    representing integers exactly above about 16.7 million, which would silently
    round those counters. Raw therefore stays float64.

    Both are float rather than integer because they are genuinely missing on some
    rows and NaN has no integer representation.
    """
    dtypes = {
        "serial_number": "string",
        "model": "string",
        "capacity_bytes": "int64",
        "failure": "int8",
    }
    for column in columns:
        if column in ID_COLUMNS:
            continue
        dtypes[column] = "float32" if column.endswith("_normalized") else "float64"
    return dtypes


def daily_members(zip_path):
    """Return (archive, sorted CSV names) for one quarter's zip.

    The 2023 and 2024 archives carry a __MACOSX/ directory holding a ._<name>.csv
    resource fork beside every real file, so those archives list 184 entries for
    91 real days. Both forms parse as garbage and are filtered here.

    Names are zero-padded ISO dates, so a plain sort is chronological. That
    ordering is what makes the written Parquet date-ordered, which the windowing
    step depends on.
    """
    archive = zipfile.ZipFile(zip_path)
    names = [
        name
        for name in archive.namelist()
        if name.endswith(".csv")
        and not name.startswith("__MACOSX")
        and not pathlib.PurePosixPath(name).name.startswith("._")
    ]
    if not names:
        sys.exit(f"No daily CSVs found in {zip_path}")
    return archive, sorted(names)


def build_quarter(job):
    """Worker: narrow one quarter and write its Parquet file.

    Returns a small summary dict so the parent can report and verify without
    holding any data. Kept at module level with a single picklable argument so it
    works under the spawn start method, which is the default on macOS.
    """
    zip_path, columns, dtypes, out_dir, compression, overwrite = job
    label = zip_path.stem.removeprefix("data_")
    out_path = out_dir / f"drive_stats_{label}.parquet"

    if out_path.exists() and not overwrite:
        existing = pq.ParquetFile(out_path).metadata.num_rows
        print(f"  {label}  exists with {existing:,} rows, skipping", flush=True)
        return {
            "quarter": label,
            "path": out_path,
            "skipped": True,
            "days": 0,
            "rows_in": 0,
            "rows_out": existing,
            "dropped": 0,
            "failures": 0,
            "first_date": None,
            "last_date": None,
            "bytes": out_path.stat().st_size,
        }

    archive, names = daily_members(zip_path)
    writer = None
    rows_in = rows_out = failures = 0
    first_date = last_date = None

    # Written to a temporary name and moved into place at the end, so an
    # interrupted run never leaves a half-written file that --overwrite would
    # skip on the next pass.
    temp_path = out_path.with_suffix(".parquet.partial")

    try:
        for index, name in enumerate(names, start=1):
            with archive.open(name) as handle:
                frame = pd.read_csv(
                    handle,
                    usecols=columns,
                    dtype=dtypes,
                    parse_dates=["date"],
                )

            rows_in += len(frame)

            # Drop SSD boot drives, per day rather than once at the end so that
            # nothing but a single day is ever in memory.
            frame = frame[~frame["model"].map(is_ssd)]

            # usecols does not guarantee the order the columns were passed in, and
            # every row group in a Parquet file must share one schema, so the
            # order is pinned here.
            frame = frame[columns]

            rows_out += len(frame)
            failures += int(frame["failure"].sum())

            day_min = frame["date"].min()
            day_max = frame["date"].max()
            first_date = day_min if first_date is None else min(first_date, day_min)
            last_date = day_max if last_date is None else max(last_date, day_max)

            table = pa.Table.from_pandas(frame, preserve_index=False)
            if writer is None:
                # The first day defines the schema for the whole file. Every
                # later day must match it, which is what the explicit dtype map
                # guarantees: without it, a column that is empty on one day and
                # populated the next would arrive as a different type.
                writer = pq.ParquetWriter(
                    temp_path,
                    table.schema,
                    compression=None if compression == "none" else compression,
                )
            writer.write_table(table)

            if index % PROGRESS_EVERY == 0 or index == len(names):
                print(
                    f"  {label}  [{index:>3}/{len(names)}]  "
                    f"{rows_out:>11,} rows kept, {failures:>4} failures",
                    flush=True,
                )
    finally:
        if writer is not None:
            writer.close()
        archive.close()

    temp_path.replace(out_path)

    return {
        "quarter": label,
        "path": out_path,
        "skipped": False,
        "days": len(names),
        "rows_in": rows_in,
        "rows_out": rows_out,
        "dropped": rows_in - rows_out,
        "failures": failures,
        "first_date": first_date,
        "last_date": last_date,
        "bytes": out_path.stat().st_size,
    }


def verify(summaries):
    """Confirm each file holds the rows the worker claims it wrote.

    Reads Parquet footer metadata only, never the data, so this is effectively
    free. The point is that a row count in a printed summary is not evidence that
    the rows are on disk.
    """
    for summary in summaries:
        actual = pq.ParquetFile(summary["path"]).metadata.num_rows
        if actual != summary["rows_out"]:
            sys.exit(
                f"{summary['quarter']}: worker counted {summary['rows_out']:,} rows "
                f"but the file holds {actual:,}"
            )
    print("Verified: every file holds exactly the rows its worker counted.")


def report(summaries, columns, started):
    """Print the per-quarter table and the pooled totals."""
    summaries = sorted(summaries, key=lambda s: (s["quarter"][-4:], s["quarter"][:2]))

    rows_in = sum(s["rows_in"] for s in summaries)
    rows_out = sum(s["rows_out"] for s in summaries)
    dropped = sum(s["dropped"] for s in summaries)
    failures = sum(s["failures"] for s in summaries)
    total_bytes = sum(s["bytes"] for s in summaries)

    print("\n" + "=" * 86)
    print("PER QUARTER")
    print("=" * 86)
    print(
        f"{'quarter':<9}{'days':>5}{'rows in':>14}{'rows kept':>14}"
        f"{'ssd dropped':>13}{'failures':>10}{'size':>10}"
    )
    for summary in summaries:
        note = "  (skipped, already built)" if summary["skipped"] else ""
        print(
            f"{summary['quarter']:<9}{summary['days']:>5}{summary['rows_in']:>14,}"
            f"{summary['rows_out']:>14,}{summary['dropped']:>13,}"
            f"{summary['failures']:>10,}"
            f"{summary['bytes'] / 1e9:>9.2f}G{note}"
        )

    print("-" * 86)
    print(
        f"{'TOTAL':<9}{sum(s['days'] for s in summaries):>5}{rows_in:>14,}"
        f"{rows_out:>14,}{dropped:>13,}{failures:>10,}{total_bytes / 1e9:>9.2f}G"
    )

    print("\n" + "=" * 86)
    print("SANITY CHECKS")
    print("=" * 86)
    if rows_in:
        print(
            f"SSD share of rows dropped : {dropped / rows_in * 100:.3f}%  "
            f"(expected about 0.86% from the coverage run)"
        )
        print(
            f"failure rate              : 1 in {rows_out // max(failures, 1):,} "
            f"drive-days"
        )
    print(f"columns per row           : {len(columns)}")
    print(f"date span                 : "
          f"{min(s['first_date'] for s in summaries if s['first_date'] is not None).date()} "
          f"to "
          f"{max(s['last_date'] for s in summaries if s['last_date'] is not None).date()}")
    print(f"\nElapsed: {time.time() - started:.1f}s")


def main():
    args = parse_args()
    started = time.time()

    missing = [path for path in args.zips if not path.exists()]
    if missing:
        sys.exit("These zips do not exist:\n  " + "\n  ".join(map(str, missing)))

    columns = load_locked_columns(args.columns)
    dtypes = build_dtypes(columns)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    workers = args.workers or min(6, multiprocessing.cpu_count(), len(args.zips))
    print(
        f"Narrowing {len(args.zips)} quarter(s) to {len(columns)} columns "
        f"across {workers} worker(s).\n"
        f"Output: {args.out_dir}  (compression: {args.compression})\n"
    )

    jobs = [
        (path, columns, dtypes, args.out_dir, args.compression, args.overwrite)
        for path in args.zips
    ]

    if workers == 1:
        summaries = [build_quarter(job) for job in jobs]
    else:
        with multiprocessing.Pool(processes=workers) as pool:
            summaries = list(pool.imap_unordered(build_quarter, jobs))

    verify(summaries)
    report(summaries, columns, started)

    print("\nRead the whole thing back as one frame with:")
    print(f"    import pandas as pd")
    print(f"    df = pd.read_parquet('{args.out_dir}')")


if __name__ == "__main__":
    main()
