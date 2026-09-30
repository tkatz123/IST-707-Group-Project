# Data Card

What is in the modeling table, what each column means, what to drop before
fitting, and how big everything is. Every number below was measured from the
files themselves on September 30, 2026, after the rebuild that fixed the
negative-sampling seed. For how to model against the table
(splitting, cross-validation, calibration, metrics), see
[WORKPLAN.md](../WORKPLAN.md#how-to-model-against-this-table).

**Source:** [Backblaze Drive Stats](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data),
Q1 2023 through Q4 2025. Backblaze requires attribution and permits derivative
works. Machine telemetry only, no personally identifiable information.

**One row = one drive over one 30-day window.** The label says whether that drive
fails in the following 30 days.

## Dataset sizes

| Dataset | Files | Rows | Columns | Size on disk |
| --- | --- | --- | --- | --- |
| Raw quarterly archives (`data/raw/`) | 12 zips | 314,457,081 drive-days | 179 to 197, drifts by quarter | 12.2 GB |
| Narrowed daily data (`data/processed/`) | 12 Parquet | 310,866,734 drive-days | 33 | 6.1 GB |
| Modeling table (`data/modeling/`) | 3 Parquet | 3,988,809 windows | 94 | 163.4 MB |

### The three modeling files

| File | Period | Windows (`window`) | Rows | Positives | Prevalence | Drive models | Drives | Size |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `modeling_train.parquet` | 2023-01-01 to 2024-10-21 | 0 to 21 | 169,827 | 8,087 | sampled to 20:1 | 63 | 131,815 | 9.0 MB |
| `modeling_calib.parquet` | 2024-11-01 to 2024-12-20 | 22 to 23 | 297,009 | 328 | 1 in 905, true | 55 | 293,236 | 13.0 MB |
| `modeling_test.parquet` | 2025-01-01 to 2025-12-15 | 24 to 35 | 3,521,973 | 3,722 | 1 in 946, true | not inspected | not inspected | 141.4 MB |

Test's contents stay unopened until final evaluation, per the data snooping
rule. Only `serial_number` and `window` were read, to verify the train/test gap
in decision D2; the row and positive counts come from the build's own summary.

### The narrowed daily files, per quarter

| Quarter | 2023 rows | 2024 rows | 2025 rows |
| --- | --- | --- | --- |
| Q1 | 21,187,784 | 24,888,592 | 27,496,851 |
| Q2 | 21,558,164 | 25,718,932 | 28,502,694 |
| Q3 | 23,309,726 | 26,514,409 | 29,533,057 |
| Q4 | 24,490,358 | 27,037,083 | 30,629,084 |

## Columns

94 in total: 5 bookkeeping columns, 5 drive descriptors, and 84 SMART sensor
features.

### Bookkeeping: drop all five before fitting

| Column | Type | Meaning |
| --- | --- | --- |
| `serial_number` | string | Unique drive identifier. |
| `window` | int32 | Which 30-day window this is, on a fixed grid from 2023-01-01: window N covers days 30N to 30N + 29. **It rises with time and will look like a strong feature while carrying nothing but the date.** |
| `window_first_date` | timestamp | First day the drive actually reported inside the window. |
| `window_last_date` | timestamp | Last day the drive actually reported inside the window. |
| `label` | int8 | **The target.** 1 if the drive records a failure in the next window (the following 30 days), else 0. The only forward-looking value in the table. |

### Drive descriptors: features

| Column | Type | Meaning |
| --- | --- | --- |
| `model` | string | Drive model name. 63 distinct values in train, 55 in calib. Needs encoding. Models that appear in test but never in train are possible, so an encoder must tolerate unseen categories. |
| `capacity_bytes` | int64 | Drive capacity in bytes, 500 GB to 22 TB in train and calib. **`-1` means unknown**, Backblaze's missing-value marker. See the rows section below. |
| `days_observed` | int64 | Days the drive reported inside the window, 2 to 30. Windows with fewer than 2 were dropped, since first and last would be the same reading. |
| `days_span` | int16 | Days between the first and last reading in the window, 1 to 29. Divide any `_delta` by this for a rate of change. |
| `drive_days_to_date` | int64 | Running count of days the drive has been observed, through the end of this window. **Counted from 2023-01-01, not from installation**, so a drive installed in 2018 starts near 30. It is time in this dataset, not age. For true age use `smart_9_raw` (power-on hours). |

### SMART sensor features: 84 columns

Every drive reports SMART (Self-Monitoring, Analysis and Reporting Technology)
attributes daily. We keep 14 of them, each in two forms, each summarized three
ways over the window: 14 x 2 x 3 = 84.

**Naming:** `smart_<id>_<form>_<summary>`, for example `smart_5_raw_last`.

**Form:**

- `raw`: the actual counter or measurement, such as a count of bad sectors or
  hours powered on. Stored as float64, because lifetime counters exceed what
  float32 holds exactly.
- `normalized`: the manufacturer's health score for that attribute, 0 to 253.
  Usually starts at 100 or 200 and **falls** as the drive degrades. Stored as
  float32. **This is not feature scaling.** It is a column Backblaze ships, not
  something the pipeline computed, so logistic regression still needs its own
  scaling, fit on train only.

**Summary:**

- `_first`: the earliest reading in the window, the "30 days prior" value.
- `_last`: the latest reading in the window, the current value.
- `_delta`: last minus first. **For raw counters a positive delta is
  degradation; for normalized scores a negative delta is.**

| ID | Attribute | What the raw value measures |
| --- | --- | --- |
| 1 | Read Error Rate | Read errors. **Vendor-encoded on Seagate** (several counters packed into one number), so raw values are not comparable across manufacturers. Normalized is safer. |
| 3 | Spin-Up Time | Time for the platters to reach full speed. Units vary by vendor. |
| 4 | Start/Stop Count | Number of spindle start and stop cycles. |
| 5 | Reallocated Sectors Count | Bad sectors remapped to spare area. **One of Backblaze's headline failure predictors, and baseline 1 is `smart_5_raw_last > 0`.** |
| 7 | Seek Error Rate | Head positioning errors. **Vendor-encoded on Seagate**, same caveat as 1. |
| 9 | Power-On Hours | Lifetime hours powered on. The drive's real age. |
| 10 | Spin Retry Count | Times the drive had to retry spinning up. |
| 12 | Power Cycle Count | Full power on and off cycles. |
| 192 | Power-Off Retract Count | Emergency head retracts, typically from unsafe shutdowns. |
| 193 | Load/Unload Cycle Count | Times the heads parked and unparked. |
| 194 | Temperature | Drive temperature in degrees Celsius. |
| 197 | Current Pending Sector Count | Unstable sectors waiting to be remapped. **Headline predictor.** |
| 198 | Offline Uncorrectable | Sectors that failed the drive's offline scan. **Headline predictor.** |
| 199 | UltraDMA CRC Error Count | Data transfer errors on the cable or interface, usually a cabling problem rather than the disk itself. |

**Missing values.** Genuinely missing on a few rows, and the six columns for an
attribute are always missing together. Only two attributes have any:

| | SMART 197 | SMART 193 | Every other attribute |
| --- | --- | --- | --- |
| train | 2.2% | 0.13% | none |
| calib | 2.0% | 0.03% | none |

Before the SSD fix every attribute showed 0.2% to 0.4% missing, which matches
the SSD rows' share of the table.

XGBoost handles these natively. Logistic regression needs them imputed.

### Columns deliberately not in the table

- **SMART 187 and 188.** Two of Backblaze's headline predictors, excluded because
  they are reported on only 35% of drives, and which drives report them follows
  the manufacturer. Decision D3 in [WORKPLAN.md](../WORKPLAN.md).
- **`failed_in_window`.** Whether the drive failed during the window itself. Used
  internally to label the previous window, then removed so nobody trains on it.
- **`date` and `failure`** from the daily data, which the windowing turns into the
  window dates and `label`.
- **Every column not present in all twelve quarters.** The raw schema grows from
  179 to 197 columns across the date range, and a column missing from the
  training years is unusable.

## What to drop before modeling

### Columns

The five bookkeeping columns: `serial_number`, `window`, `window_first_date`,
`window_last_date`, `label`. Keep `label` aside as the target. That leaves 89
feature columns.

### Rows

**Nothing to drop.** Four SSD models had got past the original SSD filter,
because none of them has "SSD" or a Micron part number in its model string.
**Fixed September 27, 2026**: the filter now catches them, the pipeline was
rebuilt, and no SSD model remains in any file (verified September 30). For the
record, what they were:

| Model | What it is | Train rows | Train positives | Calib rows |
| --- | --- | --- | --- | --- |
| `DELLBOSS VD` | Dell BOSS mirrored M.2 SSD boot device | 273 | 2 | 431 |
| `WDC WDS250G2B0A` | WD Blue 250 GB SATA SSD | 83 | 2 | 176 |
| `Seagate IronWolf ZA250NM10002` | Seagate IronWolf 110 SSD | 74 | 0 | 136 |
| `WD Blue SA510 2.5 250GB` | WD Blue SA510 SSD | 70 | 14 | 127 |
| **Total** | | **500** | **18** | **870** (0 positives) |

SSDs report different attributes with different physical meanings, which is why
the proposal excludes them. **The true SSD share is 22 models and 1.142% of raw
rows**, not the 18 models and 0.864% first recorded in the WORKLOG.

### Values

`capacity_bytes == -1` is Backblaze's "unknown", not a real capacity. It appears
on 23 training rows across nine drive models, and none in calib. Replace it with
a missing value rather than dropping the rows: **5 of those 23 are positives**,
which is 22% against a 4.8% training base rate, so a drive failing to report its
own capacity may itself be a symptom.

### Worth knowing before EDA

Measured on the training file, September 30, 2026.

- **Most SMART raw counters are 0 on healthy drives, and that is the signal.**
  Share of rows with a nonzero value:

  | Column | Healthy (label 0) | Failing (label 1) |
  | --- | --- | --- |
  | `smart_5_raw_last` | 3.4% | 47.9% |
  | `smart_197_raw_last` | 1.2% | 40.7% |
  | `smart_198_raw_last` | 0.8% | 30.9% |
  | `smart_5_raw_delta` | 0.6% | 33.5% |

- **Near-constant columns, candidates to drop:** all six SMART 10 columns (the
  raw value is 0 on effectively every row), `smart_199_normalized_delta` (a single
  value), and the SMART 4 and 12 normalized scores, which barely move.
- **SMART 1 and 7 raw are 0 on over 99% of Toshiba, WD and HGST rows** and
  large encoded values on Seagate, up to about 2.8e14. The zeros are the manufacturer, not
  missing data.
- **Counters that should only rise sometimes fall, on about 0.2% of rows:** 23
  rows where power-on hours (SMART 9) drop, 21 of them `ST6000DX000`; 274 where
  SMART 198 drops; 69 where SMART 5 drops. Likely firmware resets or reused
  serial numbers. Too few to matter much, worth one line in the EDA.
- **SMART 199 (cable CRC errors) does not separate failures**: nonzero on 1.4% of
  healthy rows and 1.6% of failing ones, which fits it measuring the cable rather
  than the disk.
