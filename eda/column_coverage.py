"""
Measure SMART column coverage across a quarter of Backblaze Drive Stats.

Answers three questions in a single pass over the daily CSVs:
  1. What fraction of rows is each column populated on?
  2. How many distinct drive models are in the fleet?
  3. How many of those are SSDs rather than spinning disks?

The files total roughly 10 GB uncompressed per quarter, so nothing is ever
held in memory beyond a single day. Coverage is just two additive counters,
a per-column non-null count and a total row count, so each daily file is
read, folded into the running totals, and discarded.

Usage:
    python eda/column_coverage.py <data_dir> [--out <csv path>]

Example:
    python eda/column_coverage.py ~/Downloads/data_Q1_2025 \
        --out eda/coverage_q1_2025.csv
"""

import argparse
import pathlib
import sys
import time

import pandas as pd

# Non-SMART columns. These are always populated, so their coverage is not
# interesting; they are reported but flagged separately.
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


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "data_dir",
        type=pathlib.Path,
        help="Directory holding the daily CSV files for one quarter.",
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=pathlib.Path("eda/coverage_q1_2025.csv"),
        help="Where to write the per-column coverage table.",
    )
    parser.add_argument(
        "--models-out",
        type=pathlib.Path,
        default=None,
        help="Optional path for the per-model drive-day counts.",
    )
    return parser.parse_args()


def daily_files(data_dir):
    """Return the quarter's daily CSVs in chronological order.

    The filenames are zero-padded ISO dates, so a plain sort is chronological.
    Order does not affect coverage, since addition commutes, but the real
    pipeline depends on it and the habit is worth keeping.
    """
    files = sorted(data_dir.glob("*.csv"))
    if not files:
        sys.exit(f"No CSV files found in {data_dir}")
    return files


def scan(files):
    """Fold every daily file into running totals.

    Returns the per-column non-null counts, the total row count, and the
    per-model drive-day counts.

    Series.add(fill_value=0) is used rather than plain addition so that a
    column or model appearing in only some files is treated as zero in the
    others instead of poisoning the total with NaN. Within a single quarter
    the schema is stable, but Backblaze adds SMART columns between years and
    the fleet turns over constantly, so this matters as soon as the script is
    pointed at more than one quarter.
    """
    non_null = pd.Series(dtype="int64")
    model_counts = pd.Series(dtype="int64")
    total_rows = 0

    for index, path in enumerate(files, start=1):
        # low_memory=False avoids DtypeWarning on the sparse SMART columns,
        # which pandas otherwise type-infers inconsistently chunk to chunk.
        frame = pd.read_csv(path, low_memory=False)

        non_null = non_null.add(frame.notna().sum(), fill_value=0)
        model_counts = model_counts.add(
            frame["model"].value_counts(), fill_value=0
        )
        total_rows += len(frame)

        print(
            f"  [{index:>2}/{len(files)}] {path.name}  "
            f"{len(frame):>7,} rows  (running total {total_rows:,})",
            flush=True,
        )

    return non_null.astype("int64"), total_rows, model_counts.astype("int64")


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


def report(table, total_rows, model_counts):
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
    print(f"total columns             : {len(table)}")
    print(f"SMART columns             : {len(smart)}")
    print(f"  populated  >90% of rows : {above_90}")
    print(f"  populated  >50% of rows : {above_50}")
    print(f"  populated   <1% of rows : {below_1}")
    print(f"distinct drive models     : {len(model_counts)}")
    print(f"  SSD models              : {len(ssd_models)}")
    print(f"  SSD drive-days          : {ssd_drive_days:,} "
          f"({ssd_drive_days / total_rows * 100:.2f}% of rows)")

    print("\nAttributes cited in the proposal:")
    for attribute in ["smart_5", "smart_197", "smart_198", "smart_9",
                      "smart_194", "smart_187", "smart_188"]:
        for suffix in ["_raw", "_normalized"]:
            name = attribute + suffix
            row = table[table["column"] == name]
            if not row.empty:
                print(f"  {name:<26} {row.iloc[0]['coverage_pct']:>6.2f}%")

    print("\nTop 10 SMART columns by coverage:")
    for _, row in smart.head(10).iterrows():
        print(f"  {row['column']:<26} {row['coverage_pct']:>6.2f}%")


def main():
    args = parse_args()
    files = daily_files(args.data_dir)

    print(f"Scanning {len(files)} daily files in {args.data_dir}\n")
    started = time.time()

    non_null, total_rows, model_counts = scan(files)
    table = build_coverage_table(non_null, total_rows)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.out, index=False)

    if args.models_out:
        args.models_out.parent.mkdir(parents=True, exist_ok=True)
        model_counts.sort_values(ascending=False).to_csv(
            args.models_out, header=["drive_days"]
        )

    report(table, total_rows, model_counts)
    print(f"\nWrote {args.out}  ({len(table)} rows)")
    print(f"Elapsed: {time.time() - started:.1f}s")


if __name__ == "__main__":
    main()
