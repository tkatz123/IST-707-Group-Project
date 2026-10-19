# Work Log

What actually got done, newest week first. One entry per week, per person.
Forward-looking plans live in [WORKPLAN.md](WORKPLAN.md).

## Week of October 13 to 19, 2026

### Tyler Katz

- **Wrote sections 1 to 4 of the midterm report**: Problem, Stakeholders and
  Significance, Related Work, and Dataset. Cut the section skeleton for these
  from 19 subsections down to the rubric's own headings, with Dataset split into
  Source, Size and Features, and Why We Trust It.
- **Rebuilt Related Work in response to the proposal feedback** that the
  literature review was too narrow. It now covers current threshold practice,
  the two 2007 field studies, and machine learning work from 2005 to 2021
  (Murray et al., Li et al., Botezatu et al., Aussel et al., Lu et al., Amram et
  al.), plus Backblaze's own 2016 SMART analysis, then states where this project
  fits and what it inherits as a limit. Nine sources, cited with GitHub footnotes.
- **Corrected the proposal's dataset figures in the report**: 22 SSD models and
  1.142% of rows (not 13 and 0.78%), and SMART 187 and 188 at 35% coverage, so
  excluded.
- **Cross-checked our data against Backblaze's published totals.** Our cleaned
  2025 data holds 116,161,686 drive-days against Backblaze's published
  115,638,676, within 0.5%. Counted from the per-quarter build output, without
  opening the test file.
- Added where the data can be found (Backblaze's Drive Stats page and the
  README's rebuild steps), since the rubric does not allow submitting data.
- **Moved `midterm_report.md` to the repository root**, where the rubric
  requires it, and updated its image path to `documents/images/`.
- **Sent Hashim a fix list for the EDA notebook** (October 15) after reviewing
  it against the split rules in WORKPLAN.md.
- **Corrected sections 5 and 9 of the report against the fixed EDA notebook**: calibration-split figures (1 in 905, 43x, weight x36) in place of
  test-split ones, removed claims and tests the notebook no longer computes, and
  fixed the capacity table.
- **Reviewed Mrgaj's logistic regression notebook and sent a fix list**
  (October 17): the no-training baseline was missing, the threshold was chosen
  on the train fold rather than calib, and the data path failed from the repo
  root.
- **Moved `baseline_models.ipynb` into `baselines/`**, so its
  `../data/modeling` path resolves and matches section 6.
- **Added Mrgaj's section 7 text to the report** and filled in the logistic
  regression results in 7.4 and 7.5 from the notebook's saved outputs.
- Fixed two inconsistencies between sections: section 3's model count (six, to
  match section 8) and section 8.1's handling of missing S197 values (to match
  9.2).

### Hashim Khan

- **Wrote section 5, Exploratory Data Analysis** (October 13): the five
  analyses (class imbalance and prior shift; failure by manufacturer, model and
  age; SMART signatures of failing vs healthy drives; raw vs normalized SMART
  values; correlation, redundancy and degradation), with the 5.4A figure.
- **Wrote section 9, Problems and Challenges** (October 13 to 15): class
  imbalance, missing and manufacturer-dependent SMART attributes, temporal shift
  and unseen drive models, and the challenges and workarounds table.
- **Fixed the EDA notebook from the October 15 review**: the test
  split now loads only the serial number and window keys, Analysis 2 and the
  chi-square test run on calib, the negative weight is corrected to 36.05, and
  the overclaims and contradictions are fixed. Updated section 5 to match.
- **Wrote section 8, Future Work** (October 18): the six models, tuning
  and calibration, the manufacturer-bias audit, the final evaluation plan, and the
  timeline.

### Mrgaj Iyer

- **Built the logistic regression baseline** (October 16):
  chronological fit and validation folds, signed-log scaling, a budget table on
  calib, and a Platt calibration check.
- **Reworked it into `baseline_models.ipynb` after the October 17 review**: added the SMART 5 rule as the no-training baseline, chose the
  threshold on calib, split calib 50/50 by drive (half A picks the threshold and
  fits Platt scaling, half B checks both), left window 17 out as a gap between
  fit and validation, added an S197 missing indicator, and used vendor and
  capacity in place of drive model. PR-AUC 0.082 against 0.0073 for the rule and
  0.0011 for random.
- **Wrote section 6, Baselines**, and updated 9.2 to describe the
  S197 indicator.
- **Wrote section 7, Best Model So Far** (October 18), sent to Tyler and added to
  the report.

## Week of October 6 to 12, 2026

### Tyler Katz

- No commits this week.

### Hashim Khan

- **Built the EDA notebook (`EDA_HDD_Failure.ipynb`):**
  - Documented dataset provenance, dataset sizes, and a feature catalogue.
  - Completed a 12-point data-quality audit, with all checks passing.
  - Analyzed missing values and identified gaps associated with specific drive models, indicating that average imputation may be inappropriate.
  - Conducted five statistical analyses:
    1. Class imbalance and differences in failure rates across dataset splits.
    2. Failure rates by manufacturer, model, and age.
    3. SMART warning signs in failing versus healthy drives.
    4. Raw versus vendor-normalized SMART values.
    5. Correlation, feature redundancy, and changes within each window.
  - Reviewed the charts for readability and color-blind accessibility, fixing overlapping labels and titles.

- **Created the midterm report skeleton** (`documents/midterm_report.md`,
  October 8).

### Mrgaj Iyer

- No commits this week.

## Week of September 29 to October 5, 2026

### Tyler Katz

- **Fixed the negative-sampling seed** in `scripts/build_modeling_table.py`. It
  mixed the seed with Python's `hash()`, which changes every time Python starts,
  so each rebuild drew a different set of training negatives. Replaced with a
  fixed seed of 42.
- **Rebuilt the modeling table and verified it is reproducible.** A second run
  into a separate folder produced a training file identical to the first
  (`DataFrame.equals`). Train 169,827 rows (8,087 positives), calib 297,009
  (328), test 3,521,973 (3,722). The difference from the September 27 figures is
  exactly the four SSD models removed that day.
- Checked the rebuilt training file for data quality before EDA starts. The notes
  are in `documents/data_card.md` under "Worth knowing before EDA".
- Moved the EDA output files into `eda/outputs/` and updated the paths in
  `eda/column_coverage.py`, `scripts/build_dataset.py` and the README. Re-ran both
  scripts on Q1 2023 to confirm they still work: the column list and the
  narrowed Parquet matched the committed versions exactly.
- Updated the README, WORKPLAN and data card to the rebuilt numbers. Several
  still carried figures from before the SSD fix.

### Hashim Khan

- **Focus:** Understanding the modeling files and building the analysis.
- **Profiled the three modeling files:**
  - Train: 169,827 windows, including 8,087 failures.
  - Calibration: 297,009 windows, including 328 failures.
  - Test: 3,521,973 windows.
  - Confirmed that the datasets contain Backblaze SMART data organized into 30-day windows and are split chronologically. The training set was down-sampled to exactly 20 healthy windows per failure.

- **Set up the environment:** Installed the plotting, statistical analysis, and notebook libraries, including `matplotlib`, `seaborn`, `scipy`, `scikit-learn`, `nbformat`, and `nbconvert`.


### Mrgaj Iyer

- No commits this week.

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
- **Fixed the SSD filter and rebuilt the pipeline the same day.** All 22 SSD
  models are now excluded, and the narrowed dataset holds 310,866,734 rows.

### Hashim Khan

- No commits this week.

### Mrgaj Iyer

- No commits this week.

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
