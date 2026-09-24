# Predicting Hard Drive Failure from Fleet Telemetry

IST 707 group project, fall 2026. Tyler Katz, Hashim Khan, Mrgaj Iyer.

Every hard drive in a data center reports daily records of its own condition. We
predict which drives are likely to fail in the next 30 days, so operators can
replace risky drives on planned maintenance instead of reacting to outages.

Full scope, stakeholder analysis, methods and risks: [documents/proposal.md](documents/proposal.md).
Current state: [WORKPLAN.md](WORKPLAN.md). What got done and when: [WORKLOG.md](WORKLOG.md).

## Data

[Backblaze Drive Stats](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data),
twelve quarters spanning Q1 2023 to Q4 2025. One row per drive per day. Backblaze
requires attribution and permits derivative works. The data holds only machine
telemetry and no personally identifiable information.

| | |
| --- | --- |
| Raw drive-days | 314,457,081 |
| After excluding SSD boot drives | 311,740,279 |
| Distinct drive models | 94 |
| Columns kept | 33 (5 identifiers, 14 SMART attributes as raw and normalized) |
| Narrowed dataset on disk | 5.7 GB as Parquet |

**The schema drifts across this range.** Q1 2023 ships 179 columns, Q2 2023 ships
186, Q3 2023 through Q1 2024 ship 193, and Q2 2024 onward ship 197. Only the 179
columns common to every quarter are usable, because we train on 2023 to 2024 and
evaluate on 2025.

## Repository layout

```
documents/proposal.md         The approved proposal
eda/column_coverage.py        Measures column coverage and schema stability
eda/locked_columns.txt        The 33 columns the pipeline narrows to
eda/coverage_all_quarters.csv Coverage pooled across all twelve quarters
eda/coverage_by_quarter.csv   Coverage per column per quarter
eda/models_all_quarters.csv   Drive-days per model, used to identify SSDs
scripts/build_dataset.py      Narrows the daily CSVs to one Parquet per quarter
scripts/build_modeling_table.py  Windows, labels and samples the modeling table
data/raw/                     Quarterly zips, gitignored
data/processed/               Narrowed Parquet, gitignored
data/buckets/                 Stage 1 scratch, drive-keyed, gitignored
data/modeling/                The modeling table, gitignored, emailed to the team
```

## Reproducing the dataset

The data is not in the repository. These two commands rebuild it from the public
archives. Budget about 15 GB of free disk and half an hour.

**1. Environment**

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**2. Download the twelve quarterly archives** into `data/raw/` (11 GB):

```
mkdir -p data/raw && cd data/raw
for q in Q1 Q2 Q3 Q4; do for y in 2023 2024 2025; do
  curl -L -C - -O "https://f001.backblazeb2.com/file/Backblaze-Hard-Drive-Data/data_${q}_${y}.zip"
done; done
cd ../..
```

**3. Measure coverage and lock the column set** (about 16 minutes):

```
python eda/column_coverage.py data/raw/*.zip \
  --out eda/coverage_all_quarters.csv \
  --per-quarter-out eda/coverage_by_quarter.csv \
  --columns-out eda/locked_columns.txt \
  --models-out eda/models_all_quarters.csv
```

**4. Build the narrowed dataset** (about four minutes, 5.7 GB out):

```
python scripts/build_dataset.py data/raw/*.zip \
  --columns eda/locked_columns.txt \
  --out-dir data/processed
```

Both scripts print a reconciliation at the end. Step 4 should report
311,740,279 rows kept and 0.864% dropped as SSD. If either figure differs, stop
and find out why before building anything on top of it.

## Building the modeling table

`scripts/build_modeling_table.py` turns the 311 million daily snapshots into one
row per drive per non-overlapping 30-day window, labeled 1 if the drive records a
failure in the following 30 days.

```
python scripts/build_modeling_table.py \
  --in-dir data/processed \
  --bucket-dir data/buckets \
  --out-dir data/modeling
```

About 3.5 minutes, and it needs roughly 8.5 GB of scratch space for the
intermediate buckets. Pass `--skip-shuffle` on a re-run to reuse them, or delete
`data/buckets/` when you are done.

| File | Period | Rows | Positives | Prevalence |
| --- | --- | --- | --- | --- |
| `modeling_train.parquet` | 2023-01-01 to 2024-10-21 | 170,205 | 8,105 | sampled to 20:1 |
| `modeling_calib.parquet` | 2024-11-01 to 2024-12-20 | 297,879 | 328 | 1 in 908, true |
| `modeling_test.parquet` | 2025-01-01 to 2025-12-15 | 3,531,820 | 3,722 | 1 in 948, true |

**None of these are in the repository.** `modeling_test.parquet` is 134 MB and
GitHub rejects any file over 100 MB, so rather than split the set across two
distribution methods all three files are sent to the team directly. Rebuild them
from the public archives with the commands on this page if you need a fresh copy,
then check the row counts against the table above to confirm the copy matches.

Per the data snooping rule, `modeling_test.parquet` should not be opened until
final evaluation.

**Why it works in two stages.** The narrowed data is partitioned by date, and
every feature is per drive over time. A drive in service from 2023 into 2025 has
its rows spread across up to twelve files, and all twelve is about 68 GB in
memory. So stage 1 repartitions into 64 buckets keyed on a hash of
`serial_number`, which puts every row for a given drive in exactly one bucket and
makes each bucket a self-contained slice that fits in memory. Stage 2 then windows
each bucket independently, in parallel. Because buckets are hashed on drive
identity rather than on anything about the outcome, sampling negatives inside a
bucket gives the same ratio globally.

### Columns

94 columns. For each of the 28 sensors, three features:

- `<sensor>_first`: the earliest reading in the window, the "30 days prior" value
- `<sensor>_last`: the latest reading in the window, the current value
- `<sensor>_delta`: last minus first

Divide `_delta` by `days_span` for a rate of change. The span is the real observed
distance between the two readings rather than an assumed 30, because drives drop
in and out of the fleet.

Plus `capacity_bytes`, `model`, `days_observed`, `days_span` and
`drive_days_to_date`.

**Not features, drop these before fitting:** `serial_number`, `window`,
`window_first_date`, `window_last_date`, and `label`.

### What is guaranteed about the table

- **Only the label looks forward.** Every feature is computed from readings inside
  the window. The label reads the next window and nothing else.
- **Windows are non-overlapping**, anchored to a fixed calendar grid from
  2023-01-01, so window N means the same 30 days for every drive.
- **The splits are chronological and buffered.** A window is kept only if its
  label period falls in the same split as its features, so no drive contributes
  overlapping or adjacent evidence to two splits. Drives may appear in more than
  one split; the smallest window gap for those in both train and test is 4.
- **Calibration and test are at true prevalence.** Only the training split is
  sampled. This is what the proposal's recalibration step needs.
- **91.3% of source failures become positives**, 12,155 of 13,307. The remainder
  is structural: a drive failing in its first window has nothing to label, the
  final window has no successor, and boundary windows are discarded by the buffer.

## Reading the dataset

The twelve files share one schema, so the whole three years loads as a single
frame:

```python
import pandas as pd
df = pd.read_parquet("data/processed")
```

That is 311 million rows and will not fit in memory on most machines. To work
with one quarter:

```python
df = pd.read_parquet("data/processed/drive_stats_Q1_2025.parquet")
```

Or a subset of columns across all quarters:

```python
df = pd.read_parquet("data/processed", columns=["date", "serial_number", "model", "failure", "smart_5_raw"])
```

## Notes on the data

- **SSD boot drives are excluded**, 18 models and 0.864% of rows. Four Micron
  models carry no "SSD" in their model string, and one has the part number
  mid-name, so the filter matches substrings rather than prefixes.
- **Normalized SMART values are stored as float32, raw values as float64.**
  Normalized readings are bounded 0 to 253. Raw readings are lifetime counters
  reaching the trillions, and float32 stops representing integers exactly above
  about 16.7 million.
- **Rows are in date order within each quarter**, and quarters sort
  chronologically by filename. The windowing step depends on this.
