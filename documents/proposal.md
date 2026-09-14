# Predicting Hard Drive Failure from Fleet Telemetry

## Team

| Name | GitHub ID | Role |
| --- | --- | --- |
| Tyler Katz | `tkatz123` | Point of contact, repository owner |
| Hashim Khan | `Khan-M-HashimKhan` | Team member |
| Mrgaj Iyer | `mriyer27` | Team member |

**Point of contact:** Tyler Katz.

## Introduction

### What are we trying to do?

Every hard drive in a data center reports daily records of its own condition. We are trying to leverage that data to predict which hard drives are likely to fail in the next 30 days. This helps the data centers to replace the risky drives before they fail and cause unexpected issues.

### What is new in our approach, and why do we think it will succeed?

Currently, data center operators wait for one reading to cross one line before acting on replacting a drive. We aim to change this approach by providing a means of proactively replacing hard drives at high risk to fail. First, we ask how likely a drive is to fail inside a 30-day window rather than whether it has tripped an alarm today, which gives operators a ranked list instead of a yes or no. Additionally, we have far more evidence than the studies that defined this problem. The two 2007 papers below worked with roughly 100,000 drives, the Backblaze archive which we are using gives us about 28 million daily records in a single quarter, with the failures labeled by the operator of the hardware itself. Leveraging the masssive amount of data available to us will help us to create a better performing, and more usable model.


### Who cares, and what difference will it make?

Data center operators and enterprise IT teams carry the cost of drive failure today, and both replace hardware under a fixed budget of spare drives and maintenance hours. A ranking of which drives are most likely to fail next turns that decision from reactive into planned work, reducing emergency repairs and unexpected storage outages. Storage providers such as Backblaze benefit through service reliability, and drive manufacturers benefit from knowing which health readings actually predict failure. Each group and what it specifically needs is set out in the stakeholder section below.

## Literature Review

### How is it done today, and what are the limits of current practice?

Commonly hard drives are monitored using health and warning levels, and when the levels drop below a certain threshold then the drive is replaced. This is a simple approach and it fails to address those drives that fail without reaching the threshold levels.

There are two studies from 2007 that researched real world drive failures. Pinheiro, Weber, and Barroso studied drives at Google and came to a conclusion that drive health readings are able to provide significant information about their failures, however they were unable to predict every failure reliably on their own.[^pinheiro2007] In another study Schroeder and Gibson realized that real world failure rates were far more complicated than the manufacturers initially estimated.[^schroeder2007]

Together the studies show that a large share of drives fail without any single health reading crossing the threshold that would trigger a replacement, and that warning signs are often visible only as changes over time rather than in one day's values. Our research will address this limitation by using several readings together and predicting the probability of the drive failing within 30 days

### Stakeholders and their needs

- **Data Centers and Cloud Storage Operators:** They manage large numbers of drives and need to decide which drives to replace first when they have a limited number of replacement drives and maintenance hours.
- **Enterprise IT Teams:** They manage storage for smaller organizations and need to identify drives that may fail soon so they can avoid unexpected outages.
- **Backblaze and similar storage providers:** They depend on reliable storage to serve customers and need to identify risky drives early to reduce unexpected failures.
- **Drive Manufacturers:** They produce the drives and their health-monitoring systems. They need to know which health readings are most useful for identifying future failures and improving drive reliability.

## Data and Methods

### Data

The project uses the Backblaze Drive Stats dataset, a public record of daily telemetry from every drive in Backblaze's data centers, published one archive per quarter at [Backblaze Drive Stats](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data).

We inspected a full quarter before committing to it. Q1 2025 holds 90 daily CSV files covering January 1 through March 31, 2025, with no missing or duplicate days, totaling 27,799,986 rows across 318,426 distinct drives, of which 1,067 recorded a failure. Each row is one drive observed on one calendar day. The project will use twelve quarters spanning 2023 through 2025, training on 2023 and 2024 and evaluating on 2025, since one quarter leaves too little room for a 30-day window and a later test period.

Each row contains 197 columns: 11 identifying and administrative fields (date, serial number, model, capacity, failure flag, location) and 186 SMART sensor columns, being 93 self-diagnostic attributes each reported as both a raw and a vendor-normalized value. The date is time series data, serial number and model are categorical, and the SMART attributes and capacity are numeric. Coverage is uneven and constrains feature selection for us. Measured across all 27,799,986 rows, only 28 SMART columns are populated on over 90% of rows and 106 on under 1%, though the attributes best supported in the literature all exceed 97%.

The data is published by the operator of the hardware itself, is documented with a published schema, and has been released quarterly since 2016. Backblaze's terms require attribution and permit derivative works. It holds only machine telemetry and no personally identifiable information, and no second dataset is required. One cleaning decision is forced by the data: the fleet includes solid state boot drives across 13 models and 0.78% of rows, and because SSDs report different SMART attributes with different physical meanings they are excluded.

### Methods

Preprocessing reduces the daily snapshots to a single modeling table. Each daily file is narrowed to about 40 populated columns and concatenated in date order across quarters; each drive's history is then aggregated into one row per drive per 30-day window, summarizing current values, values 30 days prior, and rates of change, alongside age, capacity and model. Each row is labeled 1 if that drive records a failure within the following 30 days. Every feature uses only information available on or before the prediction date; only the label looks forward. Because failures are rare, we keep all positives and sample negatives at about 20 to 1, then recalibrate predicted probabilities against a held-out set that preserves true prevalence.

Modeling starts from two baselines: the threshold rule operators use today, flagging any non-zero reallocated sector count, and logistic regression on the populated attributes. Against these we evaluate gradient-boosted trees (XGBoost). All splits are chronological and grouped by drive, so no drive appears on both sides.

Evaluation follows directly from stakeholder needs. An operator needs a ranking they can act on within a fixed weekly replacement budget, not a binary alarm, so our primary metrics are precision and recall at that budget: replacing the top N drives per thousand, the share of those replacements genuinely about to fail and the share of all failures caught, each against both baselines. We also report precision-recall AUC rather than ROC AUC, which flatters models on imbalanced data, and a calibration curve. Accuracy is not reported: at one failure per 26,054 drive-days, always predicting "no failure" scores above 99.99%.

## Project Plan

| Period | Activity | Milestone |
| --- | --- | --- |
| Sept 15 – 28 | Acquire and clean the twelve quarters of Backblaze data: download, narrow each daily file to the populated columns, exclude SSD boot drives, and verify SMART attribute coverage. | Cleaned, concatenated 2023–2025 dataset built and stored locally, with the download and cleaning scripts committed to the repo alongside a coverage report confirming which attributes clear the 90%/97% thresholds. |
| Sept 29 – Oct 19 | Build the 30-day windowing and aggregation pipeline (current values, values 30 days prior, rates of change), construct the failure label, and set up the chronological, drive-grouped train/test split. | Full modeling table ready, with the threshold-rule and logistic-regression baselines running end to end on it. |
| Oct 20 – Nov 9 | Train and tune XGBoost against the baselines; run the manufacturer-bias audit on the missing-column pattern; recalibrate predicted probabilities against a held-out, true-prevalence slice. | XGBoost model compared to both baselines on precision/recall at a fixed replacement budget, plus a written result on whether the model is relying on manufacturer identity rather than sensor health. |
| Nov 10 – 30 | Finalize evaluation (PR-AUC, calibration curve), do error analysis on missed and caught failures, and draft the full report and figures. | Complete draft report and slides ready for internal team review. |
| Week of Dec 1 | Final report and presentation | Report submitted |

## Risks

1. **Missing SMART columns tracking manufacturer instead of chance:** Coverage of the 186 SMART columns is highly uneven, and if which columns are populated correlates with drive manufacturer rather than random missingness, a model can learn to distinguish brands instead of drive health.

    **Mitigation:** audit feature importance against drive model/manufacturer directly, and re-run the model with manufacturer-correlated presence indicators removed to see whether performance holds.

    **If it fails:** restrict the feature set to the handful of attributes with over 97% coverage that are already validated in the literature, and report the resulting drop in discriminative power honestly rather than keeping a brand-driven model.

2. **Class imbalance and unreliable probability recalibration:** Failures are extremely rare (1,067 out of nearly 27.8 million drive-days), so we train on a 20:1 sampled subset and recalibrate against a held-out set at true prevalence; if that recalibration does not transfer, predicted probabilities could look reasonable internally but mis-rank drives in practice.

    **Mitigation:** validate calibration against a fully unsampled holdout before relying on it, and treat precision/recall at the operational replacement budget, not raw probability, as the primary metric throughout.

    **If it fails:** drop probability-based claims entirely and report only rank-based precision/recall at budget.

3. **Distribution shift between training years and the test year:** New drive models enter the fleet over time and SMART reporting can change with firmware, so a model trained on 2023–2024 data may not transfer cleanly to 2025.

    **Mitigation:** check the overlap of drive models between train and test splits before finalizing results, and report performance broken out by model where sample size allows.

    **If it fails:** limit conclusions to drive models present in training and disclose the generalization gap for unseen models rather than reporting one blended number.

4. **Data volume outrunning the schedule:** Twelve quarters of daily telemetry is on the order of hundreds of millions of rows before windowing, and if the aggregation pipeline takes longer to build than planned it directly eats into modeling time.

    **Mitigation:** build and test the full pipeline on a single quarter first, before scaling to all twelve, and reserve the first two weeks of the schedule specifically for this step.

    **If it fails:** fall back to a reduced quarter range (e.g., 2024 training, 2025 test only) and disclose the narrower window in the final report.

## References

[^pinheiro2007]: Pinheiro, E., Weber, W.-D. and Barroso, L. A. "Failure Trends in a Large Disk Drive Population." *Proceedings of the 5th USENIX Conference on File and Storage Technologies (FAST '07)*, 2007. https://www.usenix.org/legacy/event/fast07/tech/full_papers/pinheiro/pinheiro.pdf

[^schroeder2007]: Schroeder, B. and Gibson, G. A. "Disk Failures in the Real World: What Does an MTTF of 1,000,000 Hours Mean to You?" *Proceedings of the 5th USENIX Conference on File and Storage Technologies (FAST '07)*, 2007. https://www.usenix.org/legacy/event/fast07/tech/schroeder/schroeder.pdf

---

**Use of AI tools:**

- **Tyler Katz:** used Claude to build the section template and rubric scaffolding for this document, and to cut the Data and Methods section down from its original draft of roughly 900 words to about 560 words. Also used it for a copy-editing pass over the finished draft, covering citation formatting, list formatting, typos, and removing a duplicated passage.
- **Hashim Khan:** used an AI assistant to summarize the two 2007 papers cited in the Literature Review. The Introduction and Literature Review sections were written without it.
- **Mrgaj Iyer:** used an AI assistant for ideation on the Project Plan and Risks sections. Both sections were written without it.
