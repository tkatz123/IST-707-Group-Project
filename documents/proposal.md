<!--
WORKING TEMPLATE. Delete this comment block before submitting.

IST 707 project proposal. Due Tuesday, September 15, 2026.
Deliverable: this file, proposal.md, in this repository, with McSweeney (pjmcswee) added as a collaborator.

HARD LIMIT: two to three pages. Shorter is allowed. Longer is not.
Rough budget to stay inside it: Introduction ~400 words, Literature Review ~450 words
(stakeholders included), Data and Methods ~450 words, Risks ~300 words, plus the plan table.

GRADING, 50 points:
  10  every listed section present. Presence only. Quality is not checked here.
      People lose these points purely by leaving a section out. Never delete a heading.
  10  stakeholders and their needs clearly identified (they live in the Literature Review).
  20  the five Heilmeier Catechism questions answered effectively.
  10  plan is feasible with enough detail to give confidence.

WHO WRITES WHAT, agreed September 11, 2026:
  Hashim Khan  -> Introduction, Literature Review
  Tyler Katz   -> Data and Methods
  Mrgaj Iyer   -> Project Plan, Risks

TWO STANDING RULES FROM THE RUBRIC:
  1. Weekly commit history is inspected and graded. Commit early, commit often,
     and make sure the work is visibly spread across all three of us.
  2. Citations must be real and must use GitHub footnote syntax. Find them on
     Google Scholar. Do not cite anything secondhand out of the project brief.

SOURCE MATERIAL: IST707_Project_Brief_DriveFailure.docx, one directory up from the repo.
It holds the verified data numbers, draft answers to all five Heilmeier questions,
and seven risks with mitigations. It is working material, not submission text.
Rewrite it in our own voice rather than pasting it.
-->

# Predicting Hard Drive Failure from Fleet Telemetry

<!-- Working title. Short, and enough for McSweeney to know roughly what this is. Change it if the team prefers something else. -->

## Team

| Name | GitHub ID | Role |
| --- | --- | --- |
| Tyler Katz | `tkatz123` | Point of contact, repository owner |
| Hashim Khan | `mriyer27` | Team member |
| Mrgaj Iyer | `TBD` | Team member |

<!--
The rubric requires full names, every member's GitHub id, and an explicitly named
point of contact who owns the repository.
Tyler is listed as point of contact because he created the repo. Say so if you want it changed.
BLOCKER: two GitHub ids are still missing and the rubric asks for them by name.
Fill them in and add all three plus pjmcswee as collaborators before Tuesday.
-->

**Point of contact:** Tyler Katz.

## Introduction

<!--
OWNER: Hashim Khan.
Three of the five Heilmeier questions get answered here. Keep the three sub-answers
distinct so a grader can find each one. No jargon at all in the first one: write it
so someone outside the class understands what we are doing.
Draft answers for all three are in section 3 of the brief.
-->

### What are we trying to do?

<!-- Heilmeier 1. Objectives in absolutely no jargon. No "model", no "features", no "classifier". -->

_To be written._

### What is new in our approach, and why do we think it will succeed?

<!-- Heilmeier 3. Brief here. The detail belongs in Data and Methods. The brief argues three points: probability over a window instead of a threshold alarm, sensors used together and over time, and far more labelled data than the 2007 studies had. -->

_To be written._

### Who cares, and what difference will it make?

<!-- Heilmeier 4. Name who benefits and what changes for them. This sets up the stakeholder list below, so keep the two consistent. -->

_To be written._

## Literature Review

<!--
OWNER: Hashim Khan.
This section carries 20 of the 50 points between the Heilmeier answer and the stakeholders,
so it is the highest-value section in the document.
-->

### How is it done today, and what are the limits of current practice?

<!--
Heilmeier 2. Review what has already been tried, with real citations, or cite literature
showing the method is novel. Google Scholar.
The two anchor papers are both from 2007 and both study large real fleets:
Pinheiro, Weber and Barroso (Google), and Schroeder and Gibson (Carnegie Mellon).
Look them up properly and cite the real records. Do not take the details from the brief.
Footnote syntax, which GitHub renders:
    ... a large fraction of drives fail with no prior warning.[^pinheiro2007]
    [^pinheiro2007]: Author, A., Author, B. "Title." *Venue*, Year. URL
-->

_To be written._

### Stakeholders and their needs

<!--
Worth 10 points on its own. For each stakeholder, state three things explicitly:
who they are, why they are a stakeholder, and what they specifically need.
McSweeney's own example of the shape he wants: "a city traffic planner needs to know about
temporal variation in pedestrian traffic and office building density in order to place traffic signals."
No interviews expected, but some online research is.
Whatever we say they need has to match what the evaluation in Data and Methods measures.
The brief lists four candidates: data center operators, smaller enterprise IT teams,
Backblaze and similar providers, and drive manufacturers.
-->

- **[Stakeholder]:** _why they are a stakeholder, and what they specifically need._
- **[Stakeholder]:** _why they are a stakeholder, and what they specifically need._
- **[Stakeholder]:** _why they are a stakeholder, and what they specifically need._
- **[Stakeholder]:** _why they are a stakeholder, and what they specifically need._

## Data and Methods

<!-- OWNER: Tyler Katz. -->

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

<!--
OWNER: Mrgaj Iyer.
Roughly two months of work. Final report is due the first week of December.
McSweeney explicitly suggests a table, so use one. 10 points ride on this looking feasible
with enough detail to give confidence, which means real activities and a checkable milestone
per period, not "work on model" repeated five times.
Sanity check it against the risks section: if the data volume risk is real, the schedule
has to show time for it.
-->

| Period | Activity | Milestone |
| --- | --- | --- |
| Sept 15 – 28 | Acquire and clean the twelve quarters of Backblaze data: download, narrow each daily file to the populated columns, exclude SSD boot drives, and verify SMART attribute coverage. | Cleaned, concatenated 2023–2025 dataset committed to the repo, with a coverage report confirming which attributes clear the 90%/97% thresholds. |
| Sept 29 – Oct 19 | Build the 30-day windowing and aggregation pipeline (current values, values 30 days prior, rates of change), construct the failure label, and set up the chronological, drive-grouped train/test split. | Full modeling table ready, with the threshold-rule and logistic-regression baselines running end to end on it. |
| Oct 20 – Nov 9 | Train and tune XGBoost against the baselines; run the manufacturer-bias audit on the missing-column pattern; recalibrate predicted probabilities against a held-out, true-prevalence slice. | XGBoost model compared to both baselines on precision/recall at a fixed replacement budget, plus a written result on whether the model is relying on manufacturer identity rather than sensor health. |
| Nov 10 – 30 | Finalize evaluation (PR-AUC, calibration curve), do error analysis on missed and caught failures, and draft the full report and figures. | Complete draft report and slides ready for internal team review. |
| Week of Dec 1 | Final report and presentation | Report submitted |

## Risks

<!--
OWNER: Mrgaj Iyer.
This is Heilmeier 5, so it is worth real points rather than being a formality.
For each risk give three things: the pitfall, how we mitigate it, and what we do if
that part of the plan fails outright.
Section 4 of the brief has seven of them written out. The most interesting one, and the
one most likely to impress, is that the missing sensor columns are missing in a pattern
that tracks manufacturer rather than chance, so a careless model learns brand instead of health.
Do not minimise these. The rubric rewards identifying them honestly.
-->

1.  **Missing SMART columns tracking manufacturer instead of chance:** Coverage of the 186 SMART columns is highly uneven, and if which columns are populated correlates with drive manufacturer rather than random missingness, a model can learn to distinguish brands instead of drive health.


  **Mitigation:** audit feature importance against drive model/manufacturer directly, and re-run the model with manufacturer-correlated presence indicators removed to see whether performance holds.
  
 **If it fails:** restrict the feature set to the handful of attributes with over 97% coverage that are already validated in the literature, and report the resulting drop in discriminative power honestly rather than keeping a brand-driven model.
 
2. **Class imbalance and unreliable probability recalibration:** Failures are extremely rare (1,067 out of nearly 27.8 million drive-days), so we train on a 20:1 sampled subset and recalibrate against a held-out set at true prevalence; if that recalibration doesn't transfer, predicted probabilities could look reasonable internally but mis-rank drives in practice.

 **Mitigation:** validate calibration against a fully unsampled holdout before relying on it, and treat precision/recall at the operational replacement budget, not raw probability, as the primary metric throughout.
 
**If it fails:** drop probability-based claims entirely and report only rank-based precision/recall at budget.

3.   **Distribution shift between training years and the test year:** New drive models enter the fleet over time and SMART reporting can change with firmware, so a model trained on 2023–2024 data may not transfer cleanly to 2025.
   
**Mitigation:** check the overlap of drive models between train and test splits before finalizing results, and report performance broken out by model where sample size allows.

**If it fails:** limit conclusions to drive models present in training and disclose the generalization gap for unseen models rather than reporting one blended number.

4. **Data volume outrunning the schedule:** Twelve quarters of daily telemetry is on the order of hundreds of millions of rows before windowing, and if the aggregation pipeline takes longer to build than planned it directly eats into modeling time.

 **Mitigation:** build and test the full pipeline on a single quarter first, before scaling to all twelve, and reserve the first two weeks of the schedule specifically for this step.
   
**If it fails:** fall back to a reduced quarter range (e.g., 2024 training, 2025 test only) and disclose the narrower window in the final report.

## References

<!--
GitHub renders footnotes wherever they are defined, but keeping them here keeps the file tidy.
Every citation must be real and verified on Google Scholar. The syllabus warns explicitly
that AI tools invent plausible citations that do not exist, so check each one resolves
to a real paper before this is submitted.
-->

[^placeholder]: Author, A., Author, B. "Title." *Venue*, Year. URL

---

<!--
REQUIRED BY THE SYLLABUS. Do not delete this. Edit it to say what actually happened.
The AI use policy permits AI tools but requires all submitted work to document if and how
they were used, identifying AI-generated writing in a footnote or endnote. Failure to
acknowledge it counts as academic dishonesty.
Separately: grading is contingent on being able to verbally support this work in class,
so every one of us needs to be able to defend our own section out loud.
-->

**Use of AI tools:** _state here which tools were used, by whom, and for what (for example: structuring this document, editing prose, locating literature). Verify before submission that this describes what actually happened._
