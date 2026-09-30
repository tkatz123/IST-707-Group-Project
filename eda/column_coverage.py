"""
Measure SMART column coverage across one or more quarters of Backblaze Drive Stats.

Answers four questions in a single pass over the daily CSVs:
  1. What fraction of rows is each column populated on?
  2. Which columns are present in EVERY quarter, and which drop out somewhere?
  3. How many distinct drive models are in the fleet?
  4. How many of those are SSDs rather than spinning disks?

Question 2 is the reason this reads whole years rather than one quarter. The
schema drifts: Q1 2023 ships 179 columns, Q2 2023 ships 186, Q3 2023 through
Q1 2024 ship 193, and Q2 2024 onward ship 197. A feature that only exists from
mid-2024 would be absent across the 2023-2024 training span and present in the
2025 test span, which silently breaks the comparison. Only columns present in
every quarter are safe to model on.

Files are read straight out of the quarterly zips, so the roughly 110 GB of
decompressed CSV is never written to disk. Nothing is held in memory beyond one
daily file per worker: coverage is two additive counters, a per-column non-null
count and a total row count, so each day is read, folded in, and discarded.

Quarters are independent, so they are scanned in parallel across processes and
folded together in the parent.

Usage:
    python eda/column_coverage.py <zip> [<zip> ...] [options]

Example:
    python eda/column_coverage.py data/raw/*.zip \
        --out eda/outputs/coverage_all_quarters.csv \
        --per-quarter-out eda/outputs/coverage_by_quarter.csv \
        --columns-out eda/outputs/locked_columns.txt \
        --models-out eda/outputs/models_all_quarters.csv
"""

import argparse
import multiprocessing
import pathlib
import sys
import time
import zipfile

import pandas as pd

# Non-SMART columns. These are always populated when present, so their coverage
# is not interesting; they are reported but flagged separately. Six of them
# (datacenter through is_legacy_format) do not exist in the earliest quarters.
ADMIN_COLUMNS = {
    "date",
    "serial_number",
    "model",
    "capacity_bytes",
    "failure",
    "datacenter",
    "cluster_id",
    "vault_id",
    "pod_id",
    "pod_slot_num",
    "is_legacy_format",
}

# Progress is printed every Nth daily file. Twelve quarters is about 1,100 files
# across several workers, so printing every one buries the summary in scrollback.
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
        "--out",
        type=pathlib.Path,
        default=pathlib.Path("eda/outputs/coverage_all_quarters.csv"),
        help="Where to write the pooled per-column coverage table.",
    )
    parser.add_argument(
        "--per-quarter-out",
        type=pathlib.Path,
        default=None,
        help="Optional long-format table of coverage per column per quarter.",
    )
    parser.add_argument(
        "--columns-out",
        type=pathlib.Path,
        default=None,
        help=(
            "Optional newline-delimited list of the columns that are present in "
            "every quarter and clear --min-coverage. This is the locked column "
            "set the cleaning pass narrows to."
        ),
    )
    parser.add_argument(
        "--models-out",
        type=pathlib.Path,
        default=None,
        help="Optional path for the per-model drive-day counts.",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=90.0,
        help="Coverage percent a SMART column must clear to be locked in.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=(
            "Quarters scanned in parallel. Defaults to min(6, cpu count, "
            "number of zips). Set 1 to scan serially, which is slower but makes "
            "a traceback easy to read."
        ),
    )
    return parser.parse_args()


def quarter_label(zip_path):
    """Turn data_Q1_2023.zip into Q1_2023.

    Falls back to the whole stem if the filename is not in Backblaze's shape,
    so an oddly named archive is still reported rather than crashing the run.
    """
    stem = zip_path.stem
    return stem[len("data_"):] if stem.startswith("data_") else stem


def daily_members(zip_path):
    """Return (archive, sorted CSV names) for one quarter's zip.

    The 2023 and 2024 archives carry a __MACOSX/ directory holding a ._<name>.csv
    resource fork beside every real file, so those archives list 184 entries for
    91 real days. Both forms parse as garbage, so they are filtered here rather
    than anywhere downstream. The 2025 archives are clean.

    The names are zero-padded ISO dates, so a plain sort is chronological.
    Order does not affect coverage, since addition commutes, but the cleaning
    pass depends on it and the habit is worth keeping.
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


def scan(archive, names, label):
    """Fold every daily file in one quarter into running totals.

    Returns the per-column non-null counts, the total row count, and the
    per-model drive-day counts.

    Series.add(fill_value=0) is used rather than plain addition so that a column
    or model appearing in only some files is treated as zero in the others
    instead of poisoning the total with NaN. Within a single quarter the schema
    is stable, but Backblaze adds SMART columns between years and the fleet
    turns over constantly, so this matters as soon as more than one quarter is
    in play.
    """
    non_null = pd.Series(dtype="int64")
    model_counts = pd.Series(dtype="int64")
    total_rows = 0

    for index, name in enumerate(names, start=1):
        # low_memory=False avoids DtypeWarning on the sparse SMART columns,
        # which pandas otherwise type-infers inconsistently chunk to chunk.
        with archive.open(name) as handle:
            frame = pd.read_csv(handle, low_memory=False)

        non_null = non_null.add(frame.notna().sum(), fill_value=0)
        model_counts = model_counts.add(
            frame["model"].value_counts(), fill_value=0
        )
        total_rows += len(frame)

        if index % PROGRESS_EVERY == 0 or index == len(names):
            print(
                f"  {label}  [{index:>3}/{len(names)}]  "
                f"{total_rows:>11,} rows so far",
                flush=True,
            )

    return non_null.astype("int64"), total_rows, model_counts.astype("int64")


def scan_quarter(zip_path):
    """Worker entry point: scan one quarter and return its totals.

    Kept at module level and given a single picklable argument so it works under
    the spawn start method, which is the default on macOS.
    """
    label = quarter_label(zip_path)
    archive, names = daily_members(zip_path)
    print(f"  {label}  opening {len(names)} daily files", flush=True)
    non_null, total_rows, model_counts = scan(archive, names, label)
    archive.close()
    return label, non_null, total_rows, model_counts


def build_coverage_table(non_null, total_rows):
    """Turn the raw counts into a sorted, reportable table."""
    table = pd.DataFrame(
        {
            "column": non_null.index,
            "non_null_rows": non_null.to_numpy(),
        }
    )
    table["total_rows"] = total_rows
    table["coverage_pct"] = (
        table["non_null_rows"] / total_rows * 100
    ).round(2)
    table["is_smart"] = ~table["column"].isin(ADMIN_COLUMNS)
    return table.sort_values(
        ["is_smart", "coverage_pct"], ascending=[True, False]
    ).reset_index(drop=True)


def build_presence_report(per_quarter):
    """Which columns exist in every quarter, and which drop out somewhere.

    Presence here means the column appeared in the CSV header at all, which is
    not the same as being populated. A column can be present in all twelve
    quarters and still be empty on 99% of rows; coverage answers that
    separately.
    """
    labels = sorted(per_quarter)
    column_sets = {label: set(per_quarter[label].index) for label in labels}

    everywhere = set.intersection(*column_sets.values())
    anywhere = set.union(*column_sets.values())
    partial = anywhere - everywhere

    rows = []
    for column in sorted(partial):
        missing = [label for label in labels if column not in column_sets[label]]
        rows.append(
            {
                "column": column,
                "quarters_present": len(labels) - len(missing),
                "missing_from": " ".join(missing),
            }
        )

    return everywhere, pd.DataFrame(rows)


def locked_columns(table, everywhere, min_coverage):
    """The column set the cleaning pass should narrow to.

    Two conditions, both required: present in every quarter, and populated on
    at least min_coverage percent of pooled rows. Admin columns that clear the
    presence test are always kept regardless of coverage, since they are the
    identifiers and the label rather than features.
    """
    present = table[table["column"].isin(everywhere)]
    admin = present[~present["is_smart"]]["column"].tolist()
    smart = present[
        present["is_smart"] & (present["coverage_pct"] >= min_coverage)
    ]["column"].tolist()
    return sorted(admin), sorted(smart)


def report(table, total_rows, model_counts, everywhere, partial, args):
    """Print the figures that go into the proposal's Data section."""
    smart = table[table["is_smart"]]

    above_90 = int((smart["coverage_pct"] > 90).sum())
    above_50 = int((smart["coverage_pct"] > 50).sum())
    below_1 = int((smart["coverage_pct"] < 1).sum())

    ssd_models = [m for m in model_counts.index if "ssd" in str(m).lower()]
    ssd_drive_days = int(model_counts[ssd_models].sum()) if ssd_models else 0

    print("\n" + "=" * 62)
    print("COVERAGE SUMMARY")
    print("=" * 62)
    print(f"total drive-day rows      : {total_rows:,}")
    print(f"total columns seen        : {len(table)}")
    print(f"SMART columns             : {len(smart)}")
    print(f"  populated  >90% of rows : {above_90}")
    print(f"  populated  >50% of rows : {above_50}")
    print(f"  populated   <1% of rows : {below_1}")
    print(f"distinct drive models     : {len(model_counts)}")
    print(f"  SSD models              : {len(ssd_models)}")
    print(f"  SSD drive-days          : {ssd_drive_days:,} "
          f"({ssd_drive_days / total_rows * 100:.2f}% of rows)")

    print("\n" + "=" * 62)
    print("SCHEMA STABILITY ACROSS QUARTERS")
    print("=" * 62)
    print(f"present in every quarter  : {len(everywhere)}")
    print(f"present in only some      : {len(partial)}")
    if not partial.empty:
        print("\nColumns that drop out somewhere:")
        for _, row in partial.iterrows():
            print(
                f"  {row['column']:<26} in {row['quarters_present']:>2} quarters,"
                f" missing from {row['missing_from']}"
            )

    admin, smart_locked = locked_columns(table, everywhere, args.min_coverage)
    print("\n" + "=" * 62)
    print(f"LOCKED COLUMN SET  (in all quarters, SMART >= {args.min_coverage}%)")
    print("=" * 62)
    print(f"admin / identifier columns : {len(admin)}")
    print(f"SMART columns              : {len(smart_locked)}")
    print(f"total to narrow to         : {len(admin) + len(smart_locked)}")
    print("\n  " + "\n  ".join(admin))
    print()
    for column in smart_locked:
        pct = table.loc[table["column"] == column, "coverage_pct"].iloc[0]
        print(f"  {column:<26} {pct:>6.2f}%")

    print("\nAttributes cited in the proposal:")
    for attribute in ["smart_5", "smart_197", "smart_198", "smart_9",
                      "smart_194", "smart_187", "smart_188"]:
        for suffix in ["_raw", "_normalized"]:
            name = attribute + suffix
            row = table[table["column"] == name]
            if not row.empty:
                flag = "" if name in everywhere else "   NOT IN ALL QUARTERS"
                print(f"  {name:<26} {row.iloc[0]['coverage_pct']:>6.2f}%{flag}")


def main():
    args = parse_args()
    started = time.time()

    missing = [path for path in args.zips if not path.exists()]
    if missing:
        sys.exit("These zips do not exist:\n  " + "\n  ".join(map(str, missing)))

    workers = args.workers or min(6, multiprocessing.cpu_count(), len(args.zips))
    print(
        f"Scanning {len(args.zips)} quarter(s) across {workers} worker(s).\n"
        f"This is a full pass over every daily file, so expect several minutes.\n"
    )

    # Overall accumulators, folded across all quarters.
    non_null = pd.Series(dtype="int64")
    model_counts = pd.Series(dtype="int64")
    total_rows = 0
    per_quarter_counts = {}
    per_quarter_rows = {}

    if workers == 1:
        results = (scan_quarter(path) for path in args.zips)
    else:
        pool = multiprocessing.Pool(processes=workers)
        results = pool.imap_unordered(scan_quarter, args.zips)

    for label, non_null_q, rows_q, models_q in results:
        per_quarter_counts[label] = non_null_q
        per_quarter_rows[label] = rows_q

        non_null = non_null.add(non_null_q, fill_value=0)
        model_counts = model_counts.add(models_q, fill_value=0)
        total_rows += rows_q

        print(f"DONE {label}: {rows_q:,} rows, {len(non_null_q)} columns", flush=True)

    if workers != 1:
        pool.close()
        pool.join()

    non_null = non_null.astype("int64")
    model_counts = model_counts.astype("int64")

    table = build_coverage_table(non_null, total_rows)
    everywhere, partial = build_presence_report(per_quarter_counts)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out, index=False)
    written = [args.out]

    if args.per_quarter_out:
        frames = []
        for label in sorted(per_quarter_counts):
            quarter_table = build_coverage_table(
                per_quarter_counts[label], per_quarter_rows[label]
            )
            quarter_table.insert(0, "quarter", label)
            frames.append(quarter_table)
        args.per_quarter_out.parent.mkdir(parents=True, exist_ok=True)
        pd.concat(frames, ignore_index=True).to_csv(
            args.per_quarter_out, index=False
        )
        written.append(args.per_quarter_out)

    if args.columns_out:
        admin, smart_locked = locked_columns(table, everywhere, args.min_coverage)
        args.columns_out.parent.mkdir(parents=True, exist_ok=True)
        args.columns_out.write_text("\n".join(admin + smart_locked) + "\n")
        written.append(args.columns_out)

    if args.models_out:
        args.models_out.parent.mkdir(parents=True, exist_ok=True)
        model_counts.sort_values(ascending=False).to_csv(
            args.models_out, header=["drive_days"]
        )
        written.append(args.models_out)

    report(table, total_rows, model_counts, everywhere, partial, args)

    print()
    for path in written:
        print(f"Wrote {path}")
    print(f"Elapsed: {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
