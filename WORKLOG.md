# Work Log

What actually got done, newest week first. One entry per week, per person.
Forward-looking plans live in [WORKPLAN.md](WORKPLAN.md).

## Week of September 22 to 28, 2026

### Tyler Katz

- Downloaded all twelve quarterly Backblaze Drive Stats archives, Q1 2023 through
  Q4 2025. 11 GB compressed, about 110 GB of CSV, held in `data/raw/` and
  gitignored.
- Rewrote `eda/column_coverage.py` to read from the zips directly rather than a
  directory of loose CSVs, to scan quarters in parallel, and to answer a question
  the single-quarter version could not: which columns exist in every quarter.
- Ran the coverage pass over all twelve quarters. **314,457,081 drive-days.**
  Results in `eda/coverage_all_quarters.csv` and `eda/coverage_by_quarter.csv`.
- **Found that the schema drifts across the project's date range.** Q1 2023 ships
  179 columns, Q2 2023 ships 186, Q3 2023 through Q1 2024 ship 193, and Q2 2024
  onward ship 197. 179 columns are common to all twelve quarters. Since we train
  on 2023 to 2024 and test on 2025, any column missing from the early quarters
  would be absent in training and present in test, so only the common 179 are
  usable.
- Locked the modeling column set at **33 columns**: 5 identifiers plus 14 SMART
  attributes in raw and normalized form (1, 3, 4, 5, 7, 9, 10, 12, 192, 193, 194,
  197, 198, 199). Written to `eda/locked_columns.txt`.
- **Found that SMART 187 and 188 have only 35% coverage**, not the 97% the
  proposal's Data section implies for the literature-supported attributes. Both
  are among Backblaze's own five headline stats, so this needs addressing in the
  midterm report. See the open decision in WORKPLAN.md.
- **Corrected the SSD exclusion.** The proposal says 13 SSD models and 0.78% of
  rows, which comes from matching "SSD" in the model string. Four Micron models
  carry no "SSD" in their name (`MTFDDAV240TCB`, `MTFDDAV480TCB`,
  `MTFDDAV480TDS`, `Micron 5300 MTFDDAK480TDS`) and one has the part number
  mid-name rather than as a prefix. Across the full fleet the real figure is
  **18 models and 0.864% of rows.**
- Wrote `scripts/build_dataset.py` and built the narrowed dataset:
  **311,740,279 rows across 12 Parquet files, 5.7 GB**, in `data/processed/`.
  Reconciles exactly against the coverage count minus the SSD rows.
- Added `requirements.txt` so all three of us resolve the same package versions.
- Wrote `scripts/build_modeling_table.py` and built the modeling table.
  **The engineering problem it solves:** the data is partitioned by date and every
  feature is per drive over time, so a drive's history is spread across up to
  twelve files and the full dataset is about 68 GB in memory. It runs in two
  stages, first repartitioning into 64 buckets keyed on a hash of
  `serial_number` so every row for a drive lands in one bucket, then windowing
  each bucket independently in parallel.
- **Modeling table: 170,205 training rows at 20:1, 297,879 calibration rows and
  3,531,820 test rows at true prevalence, 94 columns, built in 3.5 minutes.**
  12,155 of the 13,307 source failure events become positives, 91.3%.
- **Found and fixed a labeling bug during validation.** The minimum-observed-days
  filter was being applied before labeling, which meant a window too sparse to be
  a feature row was also removed as a label source, so the window before it lost
  its successor and any failure in it vanished. Recovered 2.4% of positives.
- **Removed `failed_in_window` from the output.** It records whether the drive
  failed during the window itself, which is needed to label the previous window
  and is zero on all but 6 of 4 million rows afterwards. A column named that,
  sitting beside the label, is an invitation to train on it.
- Split the remaining work with the team: Hashim takes EDA, Mrgaj takes the
  baseline models, Tyler takes final tuning and evaluation. Recorded in
  WORKPLAN.md.
- Added `documents/data_card.md`: every column in the modeling table explained,
  the size of each dataset, and what to drop before fitting.
- **Found four SSD models that got past the SSD filter** while writing the data
  card: `DELLBOSS VD`, `WDC WDS250G2B0A`, `Seagate IronWolf ZA250NM10002` and
  `WD Blue SA510 2.5 250GB`. None has "SSD" or a Micron part number in its model
  string. They account for 500 training rows (18 positives) and 870 calibration
  rows, and they move the true SSD share to **22 models and 1.142% of rows**, not
  the 18 models and 0.864% recorded above.

### Hashim Khan

- _To fill in._

### Mrgaj Iyer

- _To fill in._

## Week of September 15 to 21, 2026

No commits were made to the repository this week. The written
proposal were both due September 15 and the week went to coursework.

## Week of September 8 to 14, 2026

### Tyler Katz

- Created the repository and the proposal template.
- Wrote the Data and Methods section of the proposal.
- Wrote `eda/column_coverage.py` and ran it over Q1 2025 to establish the column
  coverage figures cited in the proposal. Outputs committed as
  `eda/coverage_q1_2025.csv` and `eda/models_q1_2025.csv`.
- Inspected a full quarter before committing to the dataset: 90 daily files,
  no missing or duplicate days, 27,799,986 rows, 318,426 distinct drives,
  1,067 recorded failures.
- Added `pjmcswee` and both teammates as repository collaborators.
- Edited, checked against the rubric, and submitted the proposal.

### Hashim Khan

- Wrote the Introduction section of the proposal.
- Wrote the Literature Review, including the two 2007 papers (Pinheiro et al.
  and Schroeder and Gibson) and the references.

### Mrgaj Iyer

- Wrote the Project Plan section of the proposal.
- Wrote the Risks section.

## Week of September 1 to 7, 2026

- Project assigned in class September 1. Teams collected September 8.
- Team formed: Tyler Katz, Hashim Khan, Mrgaj Iyer.
- Topic chosen: predicting hard drive failure from Backblaze Drive Stats fleet
  telemetry. Checked against the instructor's stated exclusions (no
  recommendation systems, no reinforcement learning, no agents).
