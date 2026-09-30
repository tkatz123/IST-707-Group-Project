# Work Plan

Where the project is going. Completed work is recorded in
[WORKLOG.md](WORKLOG.md), and the approved scope is in
[documents/proposal.md](documents/proposal.md).

**Last updated:** September 30, 2026

## Status

| Milestone | Due | State |
| --- | --- | --- |
| Written proposal | Sept 15, 2026 | Submitted |
| Data acquired and cleaned | Sept 28, 2026 | **Done, four days early** |
| Modeling table and baselines | Oct 19, 2026 | **Modeling table done. Baselines not started** |
| Midterm presentation and report | **Oct 20, 2026** | Not started |
| Model trained, tuned, audited | Nov 9, 2026 | Not started |
| Final evaluation and draft report | Nov 30, 2026 | Not started |
| Final report and presentation | Week of Dec 1, 2026 | Not started |

Only two class meetings fall between now and the midterm presentation, because
October 13 is fall break. The midterm rubric was posted September 29: 12 to 15
minutes including Q&A, at least five statistical analyses in the EDA, a
no-training baseline, one trained model, and future work plus problems and
challenges.

## Who owns what

The remaining work is split three ways. Recorded September 27, 2026.

| Person | Owns | Covers |
| --- | --- | --- |
| Hashim Khan | EDA | Exploratory analysis of the modeling table, which the project spec requires. Task 8. |
| Mrgaj Iyer | Baseline models | The threshold rule and logistic regression. Tasks 5 and 6. |
| Tyler Katz | Final tuning and evaluation | XGBoost, tuning, calibration against `modeling_calib.parquet`, and the final evaluation on test. The Nov 9 and Nov 30 milestones. |

Column meanings, dataset sizes and what to drop before fitting are in
[documents/data_card.md](documents/data_card.md). Read it before loading the data.

## Current phase: EDA and baselines

The modeling table is built. What remains in this milestone is EDA and the two
baselines, which can run in parallel.

| # | Task | Owner | State |
| --- | --- | --- | --- |
| 1 | Aggregate each drive's history into one row per drive per 30-day window | Tyler | Done, `scripts/build_modeling_table.py` |
| 2 | Construct the label: failure within the following 30 days | Tyler | Done |
| 3 | Chronological, drive-grouped train/test split | Tyler | Done, see D2 |
| 4 | Keep all positives, sample negatives at 20:1 | Tyler | Done, training split only |
| 5 | Baseline 1: the threshold rule operators use today, any non-zero SMART 5 | Mrgaj | Not started |
| 6 | Baseline 2: logistic regression on the populated attributes | Mrgaj | Not started |
| 7 | Hold out an unsampled, true-prevalence slice for recalibration | Tyler | Done, `modeling_calib.parquet` |
| 8 | EDA on the modeling table (train and calib only, not test) | Hashim | Not started |

**Closed September 27, 2026: four SSD models had got past the SSD filter**, 500
training rows and 870 calibration rows. The filter was fixed and the pipeline
rebuilt the same day. No SSD model remains in any file, verified September 30.
Nothing needs dropping at load time.

### The modeling table

| split | period | rows | positives | prevalence |
| --- | --- | --- | --- | --- |
| train | 2023-01-01 to 2024-10-21 | 169,827 | 8,087 | sampled to 20:1 |
| calib | 2024-11-01 to 2024-12-20 | 297,009 | 328 | 1 in 905, true |
| test | 2025-01-01 to 2025-12-15 | 3,521,973 | 3,722 | 1 in 946, true |

94 columns: 28 sensors as first, last and delta within the window (84), plus
`capacity_bytes`, `model`, `days_observed`, `days_span`, `drive_days_to_date`,
`serial_number`, `window`, `window_first_date`, `window_last_date` and `label`.

**Recovery is 91.4%:** 12,137 of the 13,282 failure events in the source become
positives. The missing 8.6% is structural and not a defect: a drive that fails in
its first observed window has no preceding window to label, the final window of
the data has no successor to read the outcome from, and windows whose label
period straddles a split boundary are discarded by the buffer described in D2.

**Calibration and test prevalence agree to within 5% of each other** (1 in 905
against 1 in 946) across two independently held-out periods, which is the
strongest available evidence that the labeling is not drifting.

## How to model against this table

The table is not a fresh dataset, it is a pre-split one, so several steps from
Geron chapter 2 invert. **Everything below is a difference from the class
workflow, not a restatement of it.**

### The five columns that are not features

Drop these before fitting: `serial_number`, `window`, `window_first_date`,
`window_last_date`, and `label`.

`window` is the one to watch. It is an integer that increases with time and will
look like a strong feature to any model, while carrying nothing but the date.

### Do not split the data again

**No `train_test_split`, no `StratifiedShuffleSplit`.** The three files are the
split, made chronologically on purpose. A random split would put a drive's
January window in training and its February window in test, which is exactly the
leakage the chronological cut and the boundary buffer exist to prevent.

### Cross-validation has to be time-aware

**Plain `KFold` and `cross_val_score` leak inside the training split**, the same
way a random train/test split would. Use `TimeSeriesSplit`, or build folds by
hand on ordered ranges of the `window` column.

This is the easiest mistake to make here, because `cross_val_score` is the
function chapter 2 reaches for on every model it fits.

### Preprocessing differs per model

| Model | Imputation | Scaling | Encoding for `model` |
| --- | --- | --- | --- |
| Threshold rule (baseline 1) | none | none | none |
| Logistic regression (baseline 2) | required | required | required |
| XGBoost | not needed, handles NaN natively | not needed | required |

- **Baseline 1 fits nothing at all.** It is `smart_5_raw_last > 0`, the rule
  operators use today. No pipeline, no training. It is the number every later
  model has to beat.
- **Logistic regression needs both.** The sensors have genuine missing values, and
  the raw counters span many orders of magnitude (power-on hours in the tens of
  thousands next to reallocated sector counts in the single digits).
- **`model` is a string with 63 categories in train** (72 hard drive models across the whole fleet,
  so test may hold models train never saw). `ColumnTransformer` with one-hot is
  the straightforward choice. **Avoid target encoding**, which fits on the label
  and leaks unless the folds are handled carefully.

### Recalibration, which the class has not covered

**The training split was sampled to 20:1, so the model learns a base rate of
about 1 in 21 when reality is about 1 in 946.** Its predicted probabilities will
be far too high. They are still correctly *ranked*, which is why the proposal
treats ranking metrics as primary, but the probabilities themselves mean nothing
until they are corrected.

`modeling_calib.parquet` exists for this and nothing else. Fit on train, then
calibrate the fitted model against calib, which is at true prevalence.
`sklearn.calibration.CalibratedClassifierCV` with `cv="prefit"` is the tool.

**Validate the calibration before relying on it**, per risk 2 in the proposal. If
it does not transfer, drop probability claims and report rank-based precision and
recall at budget only.

### Do not touch the test set until the end

Chapter 2's data snooping rule, and it matters more here than in a class
exercise. Use train for fitting, calib for calibration and for choosing any
threshold. Every look at test spends some of its value, and there is no second
2025 to fall back on.

### Metrics

Already settled in the proposal, and they are not the class defaults:

- **Primary: precision and recall at a fixed replacement budget.** Replace the
  top N drives per thousand, then report what share of those were genuinely about
  to fail and what share of all failures were caught, against both baselines.
- **PR-AUC, not ROC-AUC.** ROC-AUC flatters models on imbalanced data.
- **A calibration curve.**
- **Never accuracy.** At 1 positive in 946 windows, always predicting "no
  failure" scores 99.89%.

## Decisions made

**D1. Window stride: non-overlapping.** Decided September 24, 2026. Sliding daily
windows would give about 30 overlapping positives per failing drive, each sharing
29 days of telemetry with the next, so near-duplicate rows would land on both
sides of the split and the metrics would measure memorization. Non-overlapping
also matches the approved wording literally. The cost is that less of the data is
used and production scoring would run monthly rather than daily, which belongs in
the report as a stated v1 tradeoff.

**D2. The chronological cut wins, with a buffer.** Decided September 24, 2026.
The proposal asks for splits that are both chronological and grouped by drive,
and a drive in service across the boundary cannot satisfy both. Rather than drop
those drives, which would bias the later splits toward newly installed and
therefore young drives, any window whose label period falls on the other side of
a boundary is discarded. A drive may appear in more than one split, but never
with overlapping or adjacent evidence: the smallest window gap for the 113,178
drives present in both train and test is 4 windows, verified again on
September 30, 2026. The strict variant
is available behind `--drop-boundary-drives` if the team prefers it.

**D3. SMART 187 and 188 are excluded.** Decided September 24, 2026. Both sit at
35% coverage across the fleet, which is a manufacturer split rather than random
missingness, so including them would import exactly the failure mode described in
risk 1. **The proposal's Data section needs correcting in the midterm report:** it
implies the literature-supported attributes all exceed 97% coverage, which holds
for SMART 5, 9, 194, 197 and 198 and does not hold for 187 and 188.

## Risks being actively watched

Full statements, mitigations and fallbacks are in the proposal. Current state:

1. **Missing SMART columns tracking manufacturer rather than chance.** Now
   concrete rather than hypothetical: SMART 187 and 188 sit at 35% coverage,
   which is a manufacturer split, not random missingness. See D3.
2. **Class imbalance and recalibration transfer.** Not yet testable. Needs the
   modeling table.
3. **Distribution shift between training years and the test year. Measured
   September 24, 2026, and it is real.** The failure rate per drive-day falls
   steadily across the three years:

   | year | average drive-days per failure |
   | --- | --- |
   | 2023 | about 21,000 |
   | 2024 | about 22,700 |
   | 2025 | about 27,000 |

   **In the modeling table that becomes a 30% gap in base rate between the period
   we fit on and the period we are judged on:** training sits at roughly 1
   positive in 722 windows before sampling, test at 1 in 946. A model that learns the 2023 and
   2024 base rate will systematically over-predict on 2025.

   **This is why the calibration slice sits at the end of the training span rather
   than being drawn from all of it.** Calibration (November and December 2024) is
   at 1 in 905 and test is at 1 in 946, about four and a half percent apart, because they are
   adjacent in time. Calibrating against the full training span would have
   imported the 2023 base rate and biased every predicted probability upward.

   **Still to check:** the drive model mix. The fleet holds 72 distinct hard drive models
   across the three years and turns over constantly, so train/test model overlap
   needs checking before any result is final, and performance should be broken out
   by model where sample size allows.

   **For the report:** this belongs in the results section as a property of the
   data, not as a caveat at the end. It is the clearest evidence that the
   chronological split was the right choice, because a random split would have
   hidden it completely.
4. **Data volume outrunning the schedule.** Closed. The full narrowing pass over
   314 million rows runs in about four minutes, and the proposal's fallback to a
   reduced quarter range is not needed.

## How the data is shared

The 12.2 GB of raw archives and the 6.1 GB narrowed dataset stay local to each
machine and are gitignored. What is committed is the scripts that rebuild them,
so anyone can reproduce them from the public archives. Reproduction steps are in
[README.md](README.md).

**Nothing under `data/` is committed.** The scripts reproduce all of it from the
public archives, and reproduction steps are in [README.md](README.md).

**The three modeling files are distributed to the team directly, by email**,
because `modeling_test.parquet` is 141 MB and GitHub rejects any file over 100 MB.
Rather than split the set across two distribution methods, all three travel the
same way.

| File | Size |
| --- | --- |
| `modeling_train.parquet` | 9.0 MB |
| `modeling_calib.parquet` | 13.0 MB |
| `modeling_test.parquet` | 141.4 MB |

**If any of the three is rebuilt, it has to be re-sent.** That is the cost of
distributing data outside version control, and it is why the scripts and the
locked column list are committed: the files can always be regenerated identically
from them. Anyone unsure whether their copy is current should rerun
`scripts/build_modeling_table.py` and check the row counts against the table in
the modeling table section above.

**Rebuilt September 30, 2026. Delete any copy from September 27.** The training
split's negative sampling used a seed that changed on every run, so rebuilds
drew different negatives. It now uses a fixed seed, and a second build was
compared against the first and matched exactly. Calib and test were never
sampled and are unchanged apart from the SSD fix.
