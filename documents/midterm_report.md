# Predicting Hard Drive Failure from Fleet Telemetry

## 1. Problem

### 1.1 Problem Statement

### 1.2 Project Goal

## 2. Stakeholders and Significance

### 2.1 Data Center and Cloud Storage Operators

### 2.2 Enterprise IT Teams

### 2.3 Backblaze and Storage Providers

### 2.4 Drive Manufacturers

### 2.5 Why the Problem Matters

## 3. Related Work

### 3.1 Current Drive-Monitoring Practices

### 3.2 Prior Research on Hard Drive Failures

### 3.3 Limitations of Existing Approaches

### 3.4 How This Project Builds on Related Work

## 4. Dataset

### 4.1 Data Source and Provenance

### 4.2 Dataset Scope and Time Period

### 4.3 Modeling Table and Unit of Observation

### 4.4 Target Label

### 4.5 Features and SMART Attributes

### 4.6 Data Quality, Missingness, and Trustworthiness

### 4.7 Preprocessing and Excluded Data

### 4.8 Data Access and Repository Location

## 5. Exploratory Data Analysis

The exploratory data analysis was carried out in the EDA_HDD_Failure.ipynb file, where within class comparisons were carried out. Training data gas 8087 failures and the 20:1 down sampling removed healthy windows at random making the SMART attributes in each class unbiased. Most instances of SMART attributes are zero for most drives to counter this U tests, x^2 test of independence,  spearman correlation and Poisson confidence intervals were used to analyse the data.

### 5.1 Analysis 1: Class Imbalance and the Train → Test Prior Shift

We examined the failure rate in each split with the 95% Wilson confidence interval on each window. As the failures are very rare in the original data, the train set was rebalanced. A model trained on the 1:20 ratio gives out a lot of false negatives, and if a model was to predict a drive not to fail for all test data that it would get an accuracy of 99%, which is misleading. 

As a result we came to the conclusion that there is a severe imbalance. The train has 1 failure : 20 healthy (4.76%). Calib and test are about 1 : 900 (0.11%). A classifier trained on this data will over predict failure. To counter this we need to take into account PR-AUC or set a false alarm rate.

| Split | Period | Drive-windows | Failures | Failure rate (95% Wilson CI) | Healthy : failed |
|---|---|---|---|---|---|
| Train | Jan 2023 – Oct 2024 | 169,827 | 8,087 | 4.762% (4.662–4.864%) | 20 : 1 |
| Calibration | Nov – Dec 2024 | 297,009 | 328 | 0.110% (0.099–0.123%) | 905 : 1 |
| Test | Jan – Dec 2025 | 3,521,973 | 3,722 | 0.106% (0.102–0.109%) | 945 : 1 |

### 5.2 Analysis 2: Who Fails? Manufacturer, Model and Age

In this analysis we calculate annual failure rate (afr) for all the manufacturers, and for the 15 most common drive models. We also check if failure is independent of the model and plot afr against drive age. This will help us determine if the failure is dependent on the model, because if it is then there should be equal representation of all models in the train test split. We use the test split for this analysis as the results on the train split will be inflated.

The results show that HGST drives fail 4.7× as often as WDC drives, and the confidence intervals do not overlap. A x^2 test of independence across 19 models rejects the null hypothesis "failure does not depend on the model" with a p value<0.001.

We also determined that age follows the classic reliability curve, as AFR is 0.97%  in the first year and rises to 3.1% at 6-8 years and then drops after 8 years. Another observation is that capacity also has a hand in drive failure. The older 8-12 TB drives fail more often than the newer 20-22 TB drives.

  | Capacity | 8 TB | 12 TB | 14 TB | 16 TB | 20 TB | 22 TB | 24 TB |
  |---|---|---|---|---|---|---|---|
  | AFR | 1.87% | 2.29% | 1.16% | 1.01% | 0.58% | **0.41%** | 2.56% |


### 5.3 Analysis 3: SMART Signatures of Failing vs Healthy Drives

In this analysis we check how different the failing values of the 14 SMART attributes are to the healthy ones. We check the % on non-zero values by class and the odds ratio of failure with non-zero values. This will help tell us which attributes carry a signal and whether it is the presence or the size of the value that matters.

The following table shows the attributes, what percantage of the failed drives had a non-zero value for that attribute and the 95% confidence interval.

| Attribute | % non-zero, healthy | % non-zero, failed | Odds ratio (95% CI) |
|---|---:|---:|---:|
| S5 Reallocated Sectors | 3.4% | **47.9%** | 25.9 (24.6–27.3) |
| S197 Current Pending Sectors | 1.2% | **41.5%** | **59.0 (55.4–62.9)** |
| S198 Offline Uncorrectable | 0.8% | **30.9%** | 55.9 (52.0–60.2) |
| S9 Power-On Hours | Always > 0 | Always > 0 | N/A |
| S4 Start/Stop Count | Always > 0 | Always > 0 | N/A |
| S12 Power Cycle Count | Always > 0 | Always > 0 | N/A |
| S193 Load/Unload Cycles | Always > 0 | Always > 0 | N/A |
| S7 Seek Error Rate | 42.0% | 54.8% | 1.67 |
| S1 Read Error Rate | 42.1% | 57.3% | 1.84 |
| S3 Spin-Up Time | 50.4% | 35.3% | 0.54 |
| S194 Temperature | Always > 0 | Always > 0 | N/A |
| S192 Power-Off Retract | 87.7% | 89.9% | 1.24 |
| S199 UltraDMA CRC Errors | 1.4% | 1.6% | 1.09 (0.9–1.3) |
| S10 Spin Retry Count | 0.0% | 0.0% | — |


S5, S197, S198 are seen to be the three most dominant precursors. A non-zero value for these three attributes significantly raises the odds of failure. However they are not sufficient on their own because about half of the failing drives have s5=0 Drives that fail suddenly, for example through electronics, motor or head failure, give no warning in these counters, which caps the recall that SMART alone can achieve


### 5.4 Analysis 4: Raw vs Normalized SMART Values (What Normalization Does)

Every SMART attribute has a RAW and a NORMALIZED value. The RAW value is the physical value of the drive while the normalized value is a 1–253 score that the vendor's firmware derives from the raw value using a formula the vendor does not publish. The purpose of normalization is to put every attribute on a common "health" scale, where 100 (or 200) means new and a falling value means degradation. In this section we test whether that normalization helps or hurts prediction. This will help us determine which of the SMART columns to keep and how do we scale them.

The raw values have upto 72,000 different values, while the normalized values are fewer than 130.This results in lots of detail getting thrown away. For S5, the normalized value stays at 100 until there are thousands of reallocated sectors. The early warning we saw previously is invisible on the normalized scale. For S9, Toshiba's normalized value hits the floor of 1 at about 40,000 h (4.6 years), so every older Toshiba drive looks the same.
![Image 5.4A](images/5.4A.png)

Normalization has compressed large numbers of raw values into a few levels:
- S1: 72,495 raw values → 80 normalized levels
- S7: 72,332 → 48
- S9: 53,344 → 100

In the case of temperature Seagate's normalized value is the temperature in °C (median 32). HGST uses a falling curve (median 176). Toshiba reports a constant 100. WDC reports about 59. Even though the actual temperatures are almost the same (32–35 °C). S199's normalized baseline is 100 for WDC and 200 for everyone else. What we suggest is training the model on raw SMART values. We need to keep the vendor explicit feature and from the normalized values that are duplicate and can leak the vendor identity to the model.


### 5.5 Analysis 5: Correlation, Redundancy and Degradation

This analysis has 2 parts; (1) a spearman rank correlation, (2) whether the change during a window adds signal beyond the window.

Correlated features waste model capacity and make linear coefficients unstable. The table show the mode redundant attributes:

| Pair | Spearman ρ | Meaning |
|---|---|---|
| S4 Start/Stop ↔ S12 Power Cycles | **+0.997** | Effectively the same variable; keep one |
| S1 Read Error ↔ S7 Seek Error | +0.901 | Both Seagate-encoded composites (vendor artefact) |
| S9 Power-On Hours ↔ Capacity | **−0.845** | Bigger drives are newer, so age and capacity are confounded |
| S197 Pending ↔ S198 Uncorrectable | +0.803 | Related but not identical; keep both |
| S3 Spin-Up ↔ S7 / S1 / S193 | −0.74 to −0.76 | Vendor encoding again |


We can see clear correlation between s4 and s12 so we can drop one. S1 and S7 also have a high correlation and their correlation with other attributes is similar thus one of them could also be dropped. S197 and S198 are strongly related but their correlation with other attributes is not identical, so both stay.

The following table shows the attribute and the degradation it has during the final 30 days.

| Attribute | AUC of level | AUC of change | % failed with an increase | % healthy with an increase | Lift |
|---|---|---|---|---|---|
| S5 Reallocated | 0.725 | 0.656 | 32.6% | 0.6% | **54×** |
| S197 Pending | 0.702 | 0.594 | 25.4% | 0.3% | **82×** |
| S198 Uncorrectable | 0.651 | 0.574 | 17.1% | 0.2% | **97×** |
| S193 Load/Unload | 0.602 | 0.567 | 80.0% | 69.8% | 1.1× |
| S9 Power-On Hours | 0.632 | 0.511 | 99.9% | 99.9% | 1.0× |

We can see the growing amount of failures. A large number of drives gain error counters before failing. On its own, the change is slightly weaker than the level (S5: 0.656 vs 0.725). Many failing drives already had errors at the start of the window. S9 rises in almost every window for both classes. 



## 6. Baselines

### 6.1 Operational Threshold Baseline

### 6.2 Random or Null-Hypothesis Baseline

### 6.3 Baseline Evaluation Metrics

## 7. Best Model So Far

### 7.1 Model Description

### 7.2 Training and Validation Setup

### 7.3 Evaluation Metrics

### 7.4 Results

### 7.5 Comparison with Baselines

### 7.6 Interpretation and Limitations

## 8. Future Work

### 8.1 Remaining Modeling Tasks

### 8.2 Model Tuning and Probability Calibration

### 8.3 Manufacturer-Bias Audit

### 8.4 Final Evaluation and Error Analysis

### 8.5 Timeline and Deliverables

## 9. Problems and Challenges

### 9.1 Class Imbalance

In the original dataset 1 in 945 drive windows ends in failure. This led to four major problems:
1. Misleading Metrics: Accuracy can not be used to test how good the model is.If the model guessed healthy for all the drives then it would get an accuracy close to 99% We therefore use precision recall curves to test how good the model is. 

2. Train/Test Prior Shift: We down sampled the train set to 1:20 ratio which led to a 4.76% positive record, which is 45 times the test prevalence. A model trained on this data produces an inflated failure rate..

3. Cost of False Positive: The EDA shows how hard precision will be. Even the strongest simple rule we discovered "any of S5, S197, S198 is non-zero", flags 5.5% of the drive windows in which only 1.25% are true positives. Thus the threshold we choose must be explicit and not a default value,

4. Limited Data for some groups. Some models have insufficient failures in the data set for the model to truly understand them. The failure rate estimates are near 0% if normal approximation is used, so we use poisson confidence intervals to estimate their failure rate.


### 9.2 Missing and Manufacturer-Dependent SMART Attributes

S197 is missing for 2.2% of training rows. Every missing value comes from two Toshiba variants (MG08ACA16TEY, MG07ACA14TEY) that do not report the attribute. As this missingness is not random but tied to the model, mean or median imputation will result in false healthy readings, so we keep these values as 'NaN'.

Another issue we observed is the Vendor specific encoding on the SMART attributes. SMART is only loosely standardised. Seagate stores S1 (read error rate) and S7 (seek error rate) as 48-bit composite values in the tens of millions, while other vendors report. The normalized temperature is the actual °C for Seagate, a falling curve for HGST and a constant 100 for Toshiba. Thus some attributes look simple and would reveal the manufacturers and cause leakage.

### 9.3 Temporal Distribution Shift and Unseen Drive Models

The training set covers 2023 - Oct 2024 and the test set covers 2025. Evaluation therefore shows real world development. The health of median healthy drivers went from 2.9 to 3.4 years, the capacity shifted drastically as the news models had a 20-24 Tb storage. The newer models never appeared in the test set, and the last test windows show an artificially low failure rate. Taking all this into account we decided to perform vendor and capacity features over raw model identity and consider age features relative to each model's population.

### 9.4 Challenges Encountered and Workarounds

| Challenge | Why it was a problem | Workaround |
|---|---|---|
| Down-sampled training data | Failure rates computed on train are inflated about 45× | Real-world rates (AFR, risk by bucket) computed on the natural-prevalence test split. Where train was needed, negatives re-weighted ×20 |
| Rare events near 0% | Normal-approximation confidence intervals produced impossible negative bounds for small windows (e.g. 1 failure in 258 rows gives −0.37% to 1.15%) | Wilson score intervals for proportions; exact Poisson intervals for annualised rates |
| Zero-inflated, heavy-tailed counters | Means, Pearson correlation and t-tests dominated by outliers | Non-parametric tests (Mann–Whitney, KS, Spearman, Kruskal–Wallis, Wilcoxon), Cliff's δ effect sizes, log-scale plots |
| Odds ratios for counters that are always non-zero | "Odds of failure if non-zero" is undefined when nearly every drive is non-zero (e.g. S9, S194) | Reported "n/a" for those attributes and relied on Cliff's δ and KS instead |
| Vendor-encoded attributes | Apparent signal in S1, S3, S7 and normalized S194/S199 reflects manufacturer, not health | Within-vendor AUC computed alongside pooled AUC; vendor-confounded attributes flagged |
## 10. Conclusion

## References

[^pinheiro2007]: Pinheiro, E., Weber, W.-D. and Barroso, L. A. "Failure Trends in a Large Disk Drive Population." *Proceedings of the 5th USENIX Conference on File and Storage Technologies (FAST '07)*, 2007. https://www.usenix.org/legacy/event/fast07/tech/full_papers/pinheiro/pinheiro.pdf

[^schroeder2007]: Schroeder, B. and Gibson, G. A. "Disk Failures in the Real World: What Does an MTTF of 1,000,000 Hours Mean to You?" *Proceedings of the 5th USENIX Conference on File and Storage Technologies (FAST '07)*, 2007. https://www.usenix.org/legacy/event/fast07/tech/schroeder/schroeder.pdf
