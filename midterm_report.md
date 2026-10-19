# Predicting Hard Drive Failure from Fleet Telemetry

## 1. Problem

Data centers are one of the most prevalent topics in the tech industry today, since they are powering the recent boom in artificial intelligence. Data centers are massive buildings filled with servers that enable customers to access computing resources they otherwise wouldn't be able to use on their own premises. Much like traditional computers, these servers store data on **hard drives**, which use a physical disk spinning at thousands of revolutions per minute to read and write data. Since these components use a moving part, although rare, there is a possibility of them failing and putting the data stored on them at risk.

Data centers hold hundreds of thousands of drives, and according to our data only about 1.3% of drives at Backblaze data centers failed per year. The problem here isn't that failures are common, it's that with a fleet of this size, a dozen happen every day and nobody knows in advance which ones will fail, making replacing drives a reactive task. Currently, drives are usually replaced once a warning counter trips, but in our data only about half of failing drives (47.9%) showed any bad sectors in the 30 days before failing, making this method of replacement unreliable. Our project aims to make replacing drives a proactive task by predicting if a drive will fail in the next 30 days, based on its readings over the past 30 days and how they changed. Operators work with a fixed weekly budget of spare drives and technician hours. Our project aims to produce a ranked list of drives, with drives at the highest risk of failure listed first, and so on. This way operators could use their weekly resources efficiently and replace drives before they fail.

## 2. Stakeholders and Significance

Drive failure affects the companies running large storage fleets, the smaller teams running their own storage, and the companies that build the drives. Each needs something different from a failure prediction.

Firstly, **data center and cloud storage operators** (Backblaze for example) are responsible for managing hundreds of thousands of drives storing data for their customers. Backblaze, for example, protects data by splitting each file into 20 pieces spread across 20 storage servers, with 17 pieces holding the data and 3 holding backup pieces of that data.[^backblaze_durability] Every failed drive uses up part of that safety margin until the drive is replaced and the data is rebuilt. Replacing a drive before it fails never uses up that margin, putting the data at less risk of being lost. Data center/cloud operators such as Backblaze work with a fixed budget of spare drives and technician hours so they need a set list of which drives to replace first, rather than replacing them as they fail. Today, about half of failing drives show no bad sectors beforehand, so replacing those drives is purely emergency work. A ranked list turns some of those failures into planned replacements.

Another stakeholder in this project is **enterprise IT teams**, these consist of companies running their own storage on a much smaller scale than a company like Backblaze. A company like Backblaze that owns a massive amount of drives only experiences about 1.3% drive failure per year,[^backblaze_drivestats] so a company with a smaller amount of drives, say 500, would only see about 6 or 7 failures per year. That is too few failures for one of these IT teams to learn failure patterns from their own data. They need an early warning of failures that avoids outages they likely don't have the staff or spare parts to absorb. They could likely benefit from using the learned pattern of failure from a company with hundreds of thousands of drives and apply it to their own storage infrastructure.

Finally, **drive manufacturers**, the ones who build the drives and decide what health readings each drive reports could benefit from our project as well. Readings aren't consistent across manufacturers and our data supports this. Some readings are reported on different scales by different manufacturers, and some are not reported at all by certain drive models. The clearest example of this is temperature: in the normalized temperature reading, Seagate reports the actual temperature, Toshiba reports a constant 100, and WDC reports about 59 on its own scale, even though all their drives run at 32 to 35 °C. This project can give manufacturers evidence of which readings actually predict failure, which are missing for some manufacturers, and which are inconsistent. This will help drive manufacturers determine what's worth reporting and hopefully standardize reporting across manufacturers.

## 3. Related Work

Today, most drives are monitored with a fixed threshold. Each drive's own firmware raises an alarm when a health reading crosses a limit set by the manufacturer, and operators like Backblaze investigate a drive once any of a handful of warning counters goes above zero. In a 2016 analysis, Backblaze found that 76.7% of its failed drives had at least one of its five watched counters above zero, compared with 4.2% of working drives. Initially that number can look promising, but on the flip side that means that 23.3% of failed drives gave no warning on those counters at all.[^klein2016] Two large field studies from 2007 help explain why this approach falls short. At Google, Pinheiro, Weber and Barroso found that some readings are strongly tied to failure (e.g. after its first scan error, a drive was 39 times more likely to fail within 60 days), yet over 56% of failed drives had no count in any of the four strongest readings. They concluded that models built on these readings alone are unlikely to predict individual drive failures.[^pinheiro2007] Schroeder and Gibson, studying about 100,000 drives, found that real-world replacement rates were typically 2-4% per year and as high as 13% on some systems, far above the 0.88% implied by manufacturer datasheets, and that replacement rates climbed steadily with age.[^schroeder2007] Our own data shows the same gap: only 47.9% of drives that failed showed any bad sectors in the 30 days before failure.

Machine learning research since then has tried to close this gap by combining many readings instead of watching each one separately. In an early example, Murray, Hughes and Kreutz-Delgado showed that support vector machines (SVMs) and a naive Bayes variant outperformed the threshold alarm built into drives while keeping false alarms low.[^murray2005] Li et al. trained decision trees on 25,792 drives and caught over 95% of failures with a false alarm rate under 0.1%. Their regression tree also gave each drive a health score instead of a simple pass or fail.[^li2014] Botezatu et al. at IBM Research used machine learning to predict disk replacements ahead of time in production data centers.[^botezatu2016] Aussel et al. used the same public Backblaze dataset as this project. They compared SVMs, random forests and gradient-boosted trees and reached over 95% precision and 67% recall on one year of data with roughly 5,000 healthy samples for every failure.[^aussel2017] More recently, Lu et al. reached a combined precision and recall score of 0.95 ten days ahead across 380,000 drives, but did so by adding performance and location data to the drives' own readings. That supports Pinheiro's conclusion that drive health readings alone have a ceiling.[^lu2020] Amram et al. have also argued that these models need to be interpretable for operators to trust and act on them.[^amram2021]

Our project builds on this work in three ways. First, it tests the model on a year it has never seen. Aussel et al. and Lu et al. both trained and evaluated within a single short window (one year and two months, respectively), while we train on 2023 and 2024, and test on all of 2025. This matters because the fleet changes over time: in our data, the failure rate per drive-day fell from about 1 in 21,000 in 2023 to 1 in 27,000 in 2025. Second, rather than reporting accuracy at a fixed alarm threshold, we rank drives by risk and measure how many real failures fall within a fixed replacement budget. This extends the health-score idea from Li et al. into the decision an operator actually makes. Third, we compare six models, including the gradient-boosted trees Aussel et al. tested, across three years of data rather than one. We also inherit a limit: the public dataset contains only drive health readings, so the ceiling Pinheiro et al. identified applies to our model too, and the extra signals Lu et al. used are not available to us. Because these studies use different datasets, prediction windows and metrics, their reported numbers are not directly comparable to each other or to ours.

## 4. Dataset

### 4.1 Source

The dataset used for this project is a drive stats dataset published by Backblaze, a cloud storage company that publishes its own fleet data.[^backblaze_drivestats] In each of their data centers, Backblaze takes a daily snapshot of each operational drive. Each daily snapshot of one drive is one row of data, meaning each row is one drive on one day. Backblaze releases data as one zip file per quarter, with one CSV file per day inside. Each row holds data that identifies the drive, and metrics about the drive: the date, serial number, model, capacity, SMART health readings (both a raw count and the manufacturer's normalized score), and a failure flag. For our project, we used twelve quarters of this data: Q1 2023 through Q4 2025. We split the data chronologically to create training and test sets, training on 2023 to 2024 (with the last two months of 2024 held back for calibration, see Section 4.2) and testing on 2025. Backblaze makes their data available for public use as long as they are cited as the source. The user is also solely responsible for how they use the data, and derivative work may be sold but the data itself cannot be since it is free.[^backblaze_drivestats]

**Where to find the data.** The data is not stored in our repository. It can be downloaded directly from [Backblaze's Drive Stats page](https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data), and our [README](https://github.com/tkatz123/IST-707-Group-Project#reproducing-the-dataset) lists the commands to download the twelve quarterly archives and the two scripts that rebuild the modeling tables from them (`scripts/build_dataset.py` and `scripts/build_modeling_table.py`). The build is deterministic, so following those steps reproduces the same tables we used.

### 4.2 Size and Features

Across the twelve quarters, the raw data holds 314,457,081 drive-days: 12.2 GB compressed and roughly 110 GB uncompressed as CSVs. The fleet grew over the period from 21.2 million drive-days in Q1 2023 to 30.6 million in Q4 2025, or roughly 236,000 to 333,000 drives in operation on an average day. The set of columns also changed over time, growing from 179 in Q1 2023 to 197 from Q2 2024 and onward. Because we train on 2023 and 2024 and test on 2025, only the 179 columns present in every quarter are usable. From those, we kept 33: five that identify the drive and day (date, serial number, model, capacity and the failure flag) and 14 SMART attributes, each as both its raw value and the manufacturer's normalized score. We excluded SMART 187 and 188 even though Backblaze highlights them, because only 35% of drives report them and which drives do depends on the manufacturer, so a model could learn the brand instead of the drive's health. We also removed solid state boot drives, which report different readings with different physical meanings: 22 models and 1.142% of rows. That leaves 310,866,734 drive-days across 72 hard drive models. Both figures correct our proposal, which listed 13 SSD models at 0.78% and stated that the best-supported attributes all exceeded 97% coverage.

We then grouped each drive's days into non-overlapping 30-day windows on a fixed calendar starting January 1, 2023, so a given window covers the same 30 days for every drive. Each row of the modeling table is one drive over one window, 3,988,809 rows in total. For each of the 14 attributes, in both forms, we record the first reading in the window, the last reading and the change between them, giving 84 SMART features. Five drive descriptors (model, capacity, days observed in the window, days between the first and last reading, and days observed so far) bring the total to 89 features. The label is 1 if the drive records a failure in the next 30-day window and 0 otherwise. It is the only value that looks forward in time. Of the 13,282 failures in the source data, 12,137 (91.4%) became labeled failures. The rest cannot be labeled: a drive that fails in its first window has no earlier window, the final window has no next window, and windows at split boundaries are removed.

| Split | Period | Rows | Failures | Failure rate |
|---|---|---|---|---|
| Train | Jan 1, 2023 to Oct 21, 2024 | 169,827 | 8,087 | sampled, 20 healthy per failure |
| Calibration | Nov 1 to Dec 20, 2024 | 297,009 | 328 | 1 in 905 (true rate) |
| Test | Jan 1 to Dec 15, 2025 | 3,521,973 | 3,722 | 1 in 946 (true rate) |

We split the table by time, as shown above. Before sampling, the training period had about 1 failure for every 722 windows. Failures were so rare that a model would learn to predict "healthy" for almost everything, so we kept every failed window and 20 healthy windows for each one. This sampling makes the model's predicted probabilities too high, which is why the calibration split exists: it is left at the true failure rate and is used to correct those probabilities. It sits at the end of the training period so that its failure rate (1 in 905) is close to the test year's (1 in 946). Calibrating on all of 2023 and 2024 would have carried the higher 2023 failure rate into every prediction. Finally, a window is kept only if the 30 days it predicts fall in the same split, so no information crosses a boundary between training, calibration and testing.

### 4.3 Why We Trust It

We've determined the data is trustworthy for several reasons. The first of which is because the data is collected by Backblaze, a company which owns multiple data centers and hundreds of thousands of hard drives. The data is not recorded by hand, removing manual data entry as a source of error. Every day, a snapshot of every working drive is taken automatically. Failures are recorded by the company that actually runs and replaces the drives, not by customers or manufacturers. Furthermore, Backblaze has published this data publicly and consistently since 2013.[^backblaze_drivestats] This data has been used by outside researchers such as Aussel et al. (mentioned above).[^aussel2017] We ran a cross check on the numbers Backblaze reported to validate the data. Backblaze published that the 2025 totals are 115,638,676 drive days with 4,317 failures.[^backblaze_drivestats] Our cleaned 2025 data holds 116,161,686 drive days, which is within 0.5% of theirs (this gap is unexplained but insignificant with the size of the data). Additionally, Backblaze reports a 2025 failure rate of 1.36%, in line with the roughly 1.3% we cite in Section 1. Backblaze's reputation and published numbers aligning with our own findings gives us confidence that we are working with high quality data.

We also checked the data ourselves before using it. Before choosing any columns, we measured how often each column was filled across all twelve quarters, which is how we found the 35% coverage that ruled out SMART 187 and 188. In the modeling table, no drive appears twice in the same window in any split, and the three splits do not overlap in time. The labels behave like real failures: 99.96% of failures in the training split fall in the drive's last window, so a drive that fails stays failed. The readings are physically plausible: temperatures range from 13 to 59 °C, power-on hours on a typical drive advance by 24 for every calendar day, and no raw counter is negative. Missing data is low and has known causes. The worst column, SMART 197, is missing on 2.2% of training rows, all from two Toshiba models that do not report it. The full audit is in our EDA notebook (eda/EDA_HDD_Failure.ipynb).

The data also has limits. It comes from one company's fleet, so the drive models it contains reflect what Backblaze chose to buy, and our results may not carry over to other data centers' hardware. Backblaze's dataset page does not define exactly when a drive counts as failed, so we rely on its failure flag as given. SMART readings are not reported consistently across manufacturers, whether in scale, in encoding, or in which counters are reported at all (see Sections 2 and 5.4). About 0.2% of rows show counters that should only increase going down, likely from firmware resets or reused serial numbers, which is too few to affect our results. Lastly, 23 training rows list capacity as unknown. We keep these as missing values rather than dropping them, because 5 of the 23 are failures.

## 5. Exploratory Data Analysis

The exploratory data analysis was carried out in the `EDA_HDD_Failure.ipynb` file, where within class comparisons were carried out. Training data has 8,087 failures and the 20:1 down sampling removed healthy windows at random making the SMART attributes in each class unbiased. Most instances of SMART attributes are zero for most drives, to handle this we used χ² test of independence, Spearman correlation, Kruskal–Wallis, Wilcoxon signed-rank, Wilson intervals and Poisson intervals to analyse the data. The test split (2025) is held out until final evaluation. Real-world failure rates use the calibration split, which keeps the natural failure rate. 

### 5.1 Class Imbalance and the Prior Shift Between Train and the Natural-Rate Fleet

We examined the failure rate in each split with the 95% Wilson confidence interval overall for each window. As the failures are very rare in the original data, the train set was rebalanced. A model trained on the 1:20 ratio over-predicts failure and gives out a lot of false positives. Also, a model that predicted every drive to be healthy would get an accuracy of about 99.9% on the natural-rate data, which is misleading.

As a result we came to the conclusion that there is a severe imbalance. The train has 1 failure : 20 healthy (4.76%). Calib is about 1 : 905 (0.110%), a 43× gap. After undoing the down-sampling (each kept healthy window stands for about 36 real ones), the train-period rate is 0.139%, close to calib’s 0.110%, so most of the gap comes from the sampling. A classifier trained on this data will over predict failure. To counter this we need to take into account PR-AUC or set a false alarm rate and recalibrate the predicted probabilities on the calibration split.

| Split | Period | Drive-windows | Failures | Failure rate (95% Wilson CI) | Healthy : failed |
|---|---|---|---|---|---|
| Train | Jan 2023 – Oct 2024 | 169,827 | 8,087 | 4.762% (4.662–4.864%) | 20 : 1 |
| Calibration | Nov – Dec 2024 | 297,009 | 328 | 0.110% (0.099–0.123%) | 905 : 1 |
| Test | Jan – Dec 2025 | 3,521,973 | held out | held out | held out |

### 5.2 Analysis 2: Who Fails? Manufacturer, Model and Age

In this analysis we calculate annual failure rate (AFR) for all the manufacturers, and for the 15 most common drive models. We use the calibration split, which keeps the natural failure rate (1 in 905); the test split is held out until final evaluation. We also check if failure is independent of the model and plot AFR against drive age. This will help us determine whether failure depends on the drive model. If it does, a model could learn the drive's brand or model name instead of its health, which the manufacturer-bias audit in §8.3 checks for.

The results show that HGST drives fail at 2.61% per year, about 3× WDC’s 0.85%, and HGST’s confidence interval does not overlap with any other vendor’s. Across the 15 models with at least 5,000 windows, a χ² test of independence rejects "failure does not depend on the model" (χ² = 113.9, dof = 14, p ≈ 10⁻¹⁷). However, Cramér’s V is only 0.020, a small effect, so the tiny p-value mostly reflects the large sample.

We also determined that age does not follow the classic reliability curve, as AFR is 0.92% in the first and second year, rises to 3.56% at 5–6 years, and then falls to 1.48% from 7 up to 8 years and 0.88% from 8 up to 10. Another observation is that capacity also has a hand in drive failure. The older 12 TB drives fail most often (2.21%) and 16 TB drives least (0.83%).

  | Capacity | 8 TB | 12 TB | 14 TB | 16 TB | 22 TB |
  |---|---|---|---|---|---|
  | AFR | 1.46% | 2.21% | 1.67% | **0.83%** | 1.27% |

### 5.3 Analysis 3: SMART Signatures of Failing vs Healthy Drives

In this analysis we check how different the failing values of the 14 SMART attributes are to the healthy ones. We check the % of non-zero values by class and the odds ratio of failure with non-zero values. This will help tell us which attributes carry a signal and whether it is the presence or the size of the value that matters.

The following table shows the attributes, what percentage of the failed drives had a non-zero value for that attribute and the 95% confidence interval.

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
| S10 Spin Retry Count | 0.0% | 0.0% | N/A |

S5, S197, S198 are seen to be the three most dominant precursors. A non-zero value for these three attributes significantly raises the odds of failure. However they are not sufficient on their own because about half of the failing drives have S5 = 0. Drives that fail suddenly, for example due to electronics, motor or head failure, give no warning in these counters, which caps the recall that SMART alone can achieve.

### 5.4 Analysis 4: Raw vs Normalized SMART Values (What Normalization Does)

Every SMART attribute has a RAW and a NORMALIZED value. The RAW value is the physical value of the drive while the normalized value is a 1–253 score that the vendor's firmware derives from the raw value using a formula the vendor does not publish. The purpose of normalization is to put every attribute on a common "health" scale, where 100 (or 200) means healthy and a falling value means degradation. In this section we test whether that normalization helps or hurts prediction. This will let us determine which of the SMART columns to keep and how to scale them.

The raw values have up to about 72,000 different values, while the normalized values have fewer than 130. This results in a significant amount of detail getting thrown away. For S5, the normalized value stays at 100 until there are thousands of reallocated sectors. The early warning we saw previously is invisible on the normalized scale. For S9, Toshiba's normalized value hits the floor of 1 at about 40,000 h (4.6 years), so every older Toshiba drive looks the same.
![Image 5.4A](documents/images/5.4A.png)

Normalization has compressed large numbers of raw values into a few levels:
- S1: 72,495 raw values → 80 normalized levels
- S7: 72,332 → 48
- S9: 53,344 → 100

In the case of temperature: Seagate's normalized value is the temperature in °C (median 32). HGST uses a falling curve (median 176). Toshiba reports a constant 100. WDC reports about 59 on its own scale. Even though the actual temperatures are almost the same (32–35 °C). S199's normalized baseline is 100 for WDC and 200 for all other vendors. Through this analysis we conclude that training the model on raw SMART values will lead to better results. We need to keep vendor as an explicit feature and drop the normalized values that are duplicates or are confounded with vendor.

### 5.5 Analysis 5: Correlation, Redundancy and Degradation

This analysis has 2 parts; (1) a spearman rank correlation, (2) whether the change during a window adds signal beyond the window.

Correlated features waste model capacity and make linear coefficients unstable. The table shows the most redundant attributes:

| Pair | Spearman ρ | Meaning |
|---|---|---|
| S4 Start/Stop ↔ S12 Power Cycles | **+0.997** | Effectively the same variable; keep one |
| S1 Read Error ↔ S7 Seek Error | +0.901 | Both Seagate-encoded composites (vendor artefact) |
| S9 Power-On Hours ↔ Capacity | **−0.845** | Bigger drives are newer, so age and capacity are confounded |
| S197 Pending ↔ S198 Uncorrectable | +0.803 | Related but not identical; keep both |
| S3 Spin-Up ↔ S7 / S1 / S193 | −0.74 to −0.76 | Vendor encoding again |

We can see clear correlation between S4 and S12 so we can drop one. S1 and S7 also have a high correlation and their correlation with other attributes is similar thus one of them could also be dropped. S197 and S198 are strongly related but their correlation with other attributes is not identical, so both stay.

The following table shows the attribute and the degradation it has during the final 30 days.

| Attribute | AUC of level | AUC of change | % failed with an increase | % healthy with an increase | Lift |
|---|---|---|---|---|---|
| S5 Reallocated | 0.725 | 0.656 | 32.6% | 0.6% | **54×** |
| S197 Pending | 0.702 | 0.594 | 25.4% | 0.3% | **82×** |
| S198 Uncorrectable | 0.651 | 0.574 | 17.1% | 0.2% | **97×** |
| S193 Load/Unload | 0.602 | 0.567 | 80.0% | 69.8% | 1.1× |
| S9 Power-On Hours | 0.632 | 0.511 | 99.9% | 99.9% | 1.0× |

This table shows that many failing drives gain error counters in their final 30 days, while very few healthy drives do. On its own, the change is slightly weaker than the level (S5: 0.656 vs 0.725). Many failing drives already had errors at the start of the window. S9 rises in almost every window for both classes. 

## 6. Baselines

Both baselines are built in `baselines/baseline_models.ipynb` and scored on the calibration split, which keeps the natural failure rate of about 1 in 905. The test split stays closed until final evaluation.

### 6.1 Operational Threshold Baseline

The first baseline is the rule operators use today: flag a drive if it has any reallocated sectors (`smart_5_raw_last > 0`). Nothing is trained. On calibration the rule flags about 42 of every 1,000 drives and catches 50.3% of the drives that fail in the next 30 days, but only 1.3% of the drives it flags actually fail, about 1 in 75. Because the rule gives a yes/no answer rather than a ranking, the operator cannot choose how many drives to replace; the data decides that.

### 6.2 Random or Null-Hypothesis Baseline

The second reference point is a model built on no information: it flags drives at random. Its precision is the failure rate (0.11%) at any budget, its recall is the share of drives flagged (1% at 10 per 1,000), and its PR-AUC is the failure rate, 0.0011. We will use this baseline to determine if future models have actually learned the patterns leading to drive failures.

### 6.3 Baseline Evaluation Metrics

Accuracy is not used, since predicting "healthy" for every drive scores about 99.9% (§9.1). The primary metric is precision and recall at a fixed replacement budget: rank drives by risk, replace the top N per 1,000, and measure what share of those were about to fail (precision) and what share of all failures were caught (recall). PR-AUC summarizes the ranking over all budgets. F1 at a single threshold is reported as a secondary figure.

The rule flags more drives than any budget below, so its figures at a budget assume N of its flagged drives are picked at random: precision stays the same and recall scales by N / 42.

| Calibration split | PR-AUC | Precision @ 1 / 1k | Precision @ 10 / 1k | Recall @ 1 / 1k | Recall @ 10 / 1k | F1 |
|---|---|---|---|---|---|---|
| SMART 5 rule | 0.0073 | 1.3% | 1.3% | 1.2% | 12.1% | 0.026 |
| Random | 0.0011 | 0.11% | 0.11% | 0.1% | 1.0% | n/a |

The rule is about 12 times better than random at picking failing drives, but almost every drive it flags is healthy. The trained model in §7 is compared against these figures.

## 7. Best Model So Far

### 7.1 Model Description

The best model evaluated so far is Logistic Regression, the first machine learning model implemented for predicting hard drive failures. Logistic Regression is a supervised classification algorithm that estimates the probability of a drive failing within the next 30 days based on its SMART telemetry, drive characteristics, and changes in health indicators over time.

The model provides a relatively simple and interpretable approach for assessing whether historical telemetry can distinguish drives at elevated risk of failure. Its predicted probabilities can be used to rank drives from highest to lowest estimated failure risk, supporting a fixed-budget replacement strategy.

### 7.2 Training and Validation Setup

The model was trained using the Backblaze hard drive dataset covering January 1, 2023, through October 21, 2024. The training dataset was downsampled to approximately 20 healthy observation windows for every failure window, resulting in 169,827 rows, including 8,087 failure windows.

A separate calibration dataset covering November 1 through December 20, 2024, was retained at its natural failure prevalence. It contains 297,009 rows, including 328 failure windows, corresponding to a failure prevalence of approximately 0.11%.

The test dataset covers January 1 through December 15, 2025, and contains 3,521,973 rows, including 3,722 failure windows. This dataset was held out to provide an independent evaluation of the model’s performance.

Because Logistic Regression cannot directly process missing feature values, missing numerical values are handled using median imputation, with missingness indicators included to preserve information about unavailable telemetry. The training data’s downsampled failure distribution also means that predicted probabilities may require calibration before being interpreted as real-world failure probabilities.

### 7.3 Evaluation Metrics

The model is evaluated using metrics suited to the highly imbalanced nature of hard drive failure prediction.

- **Precision at a fixed replacement budget:** Measures the proportion of selected drives that actually fail within the prediction window. This reflects the efficiency of replacing drives when resources are limited.
- **Recall at a fixed replacement budget:** Measures the proportion of all failures identified by selecting the highest-risk drives within the available replacement budget.
- **Precision–Recall AUC (PR-AUC):** Evaluates the model’s ability to distinguish failure cases from healthy cases across different classification thresholds.
- **F1-score:** Provides a supplementary measure balancing precision and recall at a selected threshold.

Accuracy is not used as the primary metric because the overwhelming majority of observation windows represent non-failures. A model that predicts every drive as healthy could achieve high accuracy while failing to identify drives requiring attention.

### 7.4 Results

For the results below, the model was refit on all of train and scored on the calibration split, which keeps the true failure rate of about 1 in 905. Drives are ranked by predicted risk and the top N per 1,000 are flagged, the same budget setup as §6.3.

| Budget (per 1,000) | LR precision | LR recall | SMART 5 rule precision | SMART 5 rule recall | Random precision | Random recall |
|---|---|---|---|---|---|---|
| 1 | 15.8% | 14.3% | 1.3% | 1.2% | 0.11% | 0.1% |
| 2 | 11.6% | 21.0% | 1.3% | 2.4% | 0.11% | 0.2% |
| 5 | 7.2% | 32.6% | 1.3% | 6.0% | 0.11% | 0.5% |
| 10 | 5.0% | 44.8% | 1.3% | 12.1% | 0.11% | 1.0% |
| 41.7 (the rule's own) | 1.8% | 66.2% | 1.3% | 50.3% | 0.11% | 4.2% |

Rule rows below its own budget of 41.7 are random draws from the drives it flags (§6.3), so its precision stays flat. Random precision equals the failure rate at every budget, and random recall equals the share of drives flagged.

PR-AUC is 0.082 for logistic regression, against 0.0073 for the SMART 5 rule and 0.0011 for random. At a budget of 1 per 1,000, about 1 in 6 flagged drives goes on to fail, against about 1 in 75 for the rule. At the rule's own budget of about 42 per 1,000, the model catches 66.2% of failures where the rule catches 50.3%.

To choose a threshold and recalibrate the probabilities without scoring them on the data they were fit to, calibration was split 50/50 by drive. Half A chose the threshold (0.917) and fit Platt scaling; half B checked both. On half B the model reaches 11.3% precision, 23.5% recall and an F1 of 0.153, against 0.027 for the rule on the same half. Before recalibration the model's average predicted risk was 28 times the actual failure rate; after Platt scaling it is 1.1 times.

### 7.5 Comparison with Baselines

The project uses two baseline approaches to assess the usefulness of machine learning for hard drive failure prediction.

The SMART 5 rule flags drives with a nonzero final raw value for SMART attribute 5, which tracks reallocated sectors. It provides a simple and interpretable approach to identifying potentially unhealthy drives. However, it cannot capture every failure pattern because some drives fail without exhibiting this warning sign.

The random baseline represents performance without meaningful predictive information. Because drive failures are rare, random selection has low expected precision and does not prioritize drives according to their likelihood of failure.

On the calibration split, the model and both baselines compare as follows:

| Evaluation metric | Logistic regression | SMART 5 rule | Random baseline |
|---|---|---|---|
| PR-AUC | 0.082 | 0.0073 | 0.0011 |
| Precision at 1 per 1,000 | 15.8% | 1.3% | 0.11% |
| Precision at 10 per 1,000 | 5.0% | 1.3% | 0.11% |
| Recall at 1 per 1,000 | 14.3% | 1.2% | 0.1% |
| Recall at 10 per 1,000 | 44.8% | 12.1% | 1.0% |
| F1-score | 0.153 | 0.026 | Not applicable |

The logistic regression F1 is at the 0.917 threshold on calibration half B (§7.4); the rule's F1 is on the full calibration split.

These results demonstrate that the SMART 5 rule performs better than random selection, particularly in PR-AUC and recall at a replacement budget of 10 drives per 1,000. However, its precision remains low, highlighting the difficulty of identifying future failures in a highly imbalanced dataset.

Logistic Regression extends these approaches by combining multiple telemetry features into a single risk estimate. Rather than relying exclusively on SMART attribute 5, the model can account for relationships among different SMART indicators, changes in their values over time, and drive characteristics. This broader feature-based approach supports more informed replacement prioritization. Its PR-AUC is about 11 times the rule's, and at 10 per 1,000 its precision and recall are each nearly four times the rule's.

### 7.6 Interpretation and Limitations

The initial findings support the use of SMART telemetry for identifying elevated hard drive failure risk. Exploratory analysis shows that SMART attributes 5, 197, and 198 are strongly associated with failure.

For example, nonzero SMART 197 values occur in approximately 41.5% of failed observation windows, compared with 1.2% of healthy windows. Similarly, nonzero SMART 5 values occur in approximately 47.9% of failed windows, compared with 3.4% of healthy windows. These differences indicate that the attributes provide useful warning signals, although they do not identify every failure.

Several limitations must be considered:

- **Class imbalance:** Failure windows represent a small proportion of the dataset, making precision and recall at practical replacement budgets more informative than accuracy.
- **Sampling bias:** The training dataset was downsampled to a 20:1 healthy-to-failure ratio, while the calibration and test datasets retain their observed prevalence. This difference can affect the interpretation of predicted probabilities.
- **Missing telemetry:** Some SMART attributes contain missing values, which may reflect device-specific reporting behavior rather than random data loss.
- **Drive and manufacturer differences:** Telemetry behavior varies across drive models and manufacturers. Nine of the 72 drive models never appear in the training split, so the model may meet hardware in 2025 that it has not seen before, creating a potential generalization challenge.
- **Limited model comparison:** Logistic Regression is the only machine learning model evaluated so far. Additional models can be explored in future work to determine whether alternative approaches improve failure detection.

Overall, Logistic Regression establishes the initial supervised-learning approach for the project. By combining multiple telemetry features, it provides a foundation for ranking drives according to estimated failure risk and supporting data-driven replacement decisions. Future work will focus on evaluating additional models, refining feature selection, improving probability calibration, and assessing performance across different drives and time periods.

## 8. Future Work

### 8.1 Remaining Modeling Tasks

In the next step we train 6 models and compare them against the baseline models. All 6 models will have the same inputs chosen from the EDA:

1. raw values and 30 day changes for S5, S197, S198
2. drive age
3. wear counters (S193, and one of S4 or S12, since those two are nearly identical)
4. temperature
5. manufacturer

We leave out vendor normalized values; S10: always zero and S199: no signal. Missing S197 values are kept as missing rather than filled in; models that cannot take missing values (logistic regression, SVM) get the median plus a "not reported" indicator column, as in the baseline (§9.2).

We picked six models to run from simple to complex. This would help test whether the extra complexity results in better predictions.

| Model | What it does, in plain terms | Why it fits this problem |
|---|---|---|
| **Logistic regression** | Gives each input a weight and adds up the evidence into a single risk score. | Simple, fast, and easy to explain. It shows how much each warning sign raises the risk. It needs the very skewed counters log-scaled first (§5.4), so it also tests whether that scaling helps. |
| **Decision tree** | A flowchart of yes/no questions, such as “Does it have any reallocated sectors?” and “Is it older than five years?” | Matches what the EDA found: any non-zero error count is a red flag. Operators can read the rules directly. On its own, it can memorise the training data, so we limit how deep it grows. |
| **Random forest** | Hundreds of decision trees, each built on a different random slice of the data, then averaged. | More stable than a single tree. It copes with skewed values and drive-to-drive differences without any rescaling. |
| **XGBoost** | Builds trees one after another, with each new tree focused on the mistakes of the trees before it. | Usually the strongest method on table-shaped data like ours. It handles missing values (such as S197 on two Toshiba models) by itself, and it picks up combinations like “old drive *and* rising pending sectors.” |
| **Support vector machine (SVM)** | Finds the boundary that separates failing from healthy drives with the widest possible gap. | A different way of drawing the line from the tree models, which makes it a useful check. It is slow on hundreds of thousands of rows and needs rescaled inputs, so we will train it on a sample. Its scores also need converting into probabilities. |
| **LightGBM** *(our sixth pick)* | Works like XGBoost, but groups values into bins so it trains much faster. | Built for millions of rows, which matters when the model is retrained on the full fleet. It can take manufacturer directly as a category, so it doesn’t have to be turned into yes/no columns. It is also a direct check on whether XGBoost’s results hold up. |

### 8.2 Model Tuning and Probability Calibration

Tuning: Each model's setting such as tree depth and penalty on complexity will be tuned on the training split. Cross validation will be split in such a way that no model is scored on months that came before the months it was trained on.

Rare Failure: Failures will be given extra weight in training so that the models do not learn to simply predict "healthy" every time.

### 8.3 Manufacturer-Bias Audit

The EDA shows us that failure rates differ by manufacturer (HGST is about 3× WDC), and that different SMART attributes mean different things for some manufacturers. A model could therefore end up learning “HGST drives are risky” instead of reading the actual health signals. To check for these we will:
1. Report results separately for each manufacturer and for the largest drive models.
2. Compare the model with and without the manufacturer feature, as a result if the performance drops the model is leaning on the brand rather than drive health.
3. Check drives that are missing an attribute and see if they are not unfairly flagged.

### 8.4 Final Evaluation and Error Analysis

After the final model and its calibrations are locked, we will use the test split to report precision and recall at 1 and 10 replacements per 1,000 drives, PR-AUC, and the F1-score.

The results will be stored and compared with the SMART 5 rule and random guessing. We will look at the missed failures, false alarms, and how the results change with drive age, manufacturer, and models that are not in the training split. Additionally we will measure how much the 2025 fleet differs from 2023–24, to explain any drop in performance between calibration and test.

### 8.5 Timeline and Deliverables

| Step | Work | Deliverable | Target date |
|---:|---|---|---|
| 1 | Feature set and pipeline from the EDA | `features` notebook | Sun 25 Oct |
| 2 | Train and tune the six models | `models` notebook, comparison table | Sun 15 Nov |
| 3 | Probability calibration on the calibration split | Calibrated models, reliability plots | Fri 20 Nov |
| 4 | Manufacturer-bias audit | Per-vendor results table | Wed 25 Nov |
| 5 | One-time test evaluation and error analysis | Final results, error analysis | Mon 30 Nov |
| 6 | Final report and presentation | Report PDF, slides | First week of December |

## 9. Problems and Challenges

### 9.1 Class Imbalance

In the natural-rate calibration data, about 1 in 905 drive windows ends in failure. This led to four major problems:
1. Misleading Metrics: Accuracy can not be used to test how good the model is. If the model guessed healthy for all the drives then it would get an accuracy of about 99.9%. We therefore use precision recall curves to test how good the model is.

2. Prior Shift Between Train and the Natural-Rate Fleet: We down sampled the train set to a 1:20 ratio, which led to a 4.76% positive rate, 43 times the calibration prevalence. A model trained on this data produces an inflated failure rate.

3. Cost of False Positives: The EDA shows how hard precision will be. S5 is non-zero for 47.9% of failing windows but also for 3.4% of healthy ones. At the natural rate of about 905 healthy windows per failure, a simple "S5 is non-zero" rule would be right only about 1.3% of the time (§6.1). Thus the threshold we choose must be explicit and not a default value.

4. Limited Data for some groups. Some models have insufficient failures in the data set for the model to truly understand them. The failure rate estimates are near 0% if normal approximation is used, so we use Poisson confidence intervals to estimate their failure rate.

### 9.2 Missing and Manufacturer-Dependent SMART Attributes

S197 is missing for 2.2% of training rows. Every missing value comes from two Toshiba variants (MG08ACA16TEY, MG07ACA14TEY) that do not report the attribute. As this missingness is not random but tied to the model, mean or median imputation will result in false healthy readings, so we keep these values as 'NaN'. Logistic regression cannot take missing values, so the baseline imputes the median and adds a separate "not reported" indicator column, which keeps the missingness visible to the model.

Another issue we observed is the Vendor specific encoding on the SMART attributes. SMART is only loosely standardised. Seagate stores S1 (read error rate) and S7 (seek error rate) as 48-bit composite values in the tens of millions, while other vendors use different encodings, so the raw values are not comparable across manufacturers. The normalized temperature is the actual °C for Seagate, a falling curve for HGST and a constant 100 for Toshiba. Thus some attributes partly encode the manufacturer rather than the health of the drive.

### 9.3 Temporal Distribution Shift and Unseen Drive Models

The training set covers Jan 2023 to Oct 2024 and the test set covers 2025, so evaluation reflects real-world deployment on future data. Train contains 63 of the dataset's 72 drive models, and 67% of the drives in the test set never appear in train, largely because down-sampling removed most healthy windows from train. Capacity is also strongly tied to age (ρ = −0.845): newer drives are bigger. Taking all this into account we decided to use vendor and capacity features rather than raw model identity, and to consider age relative to each model's population.

### 9.4 Challenges Encountered and Workarounds

| Challenge | Why it was a problem | Workaround |
|---|---|---|
| Down-sampled training data | Failure rates computed on train are inflated about 43× | Real-world rates (AFR by vendor, model, age and capacity) computed on the natural-prevalence calibration split. Where train was needed (risk by bucket), negatives re-weighted ×36 |
| Rare events near 0% | Normal-approximation confidence intervals produced impossible negative bounds for small windows (e.g. 1 failure in 258 rows gives −0.37% to 1.15%) | Wilson score intervals for proportions; exact Poisson intervals for annualised rates |
| Zero-inflated, heavy-tailed counters | Means, Pearson correlation and t-tests dominated by outliers | Non-parametric tests (Spearman, Kruskal–Wallis, Wilcoxon signed-rank), odds ratios, log-scale plots |
| Odds ratios for counters that are always non-zero | "Odds of failure if non-zero" is undefined when nearly every drive is non-zero (e.g. S9, S194) | Reported "n/a" for those attributes and relied on univariate ROC-AUC instead |
| Vendor-encoded attributes | Apparent signal in S1, S3, S7 and normalized S194/S199 reflects manufacturer, not health | Within-vendor AUC computed alongside pooled AUC; vendor-confounded attributes flagged |

## 10. Conclusion

Drive replacement today is reactive. The rule operators rely on, flagging any drive with reallocated sectors, catches about half of the drives that fail in the next 30 days, but only about 1 in 75 of the drives it flags actually fails. Our first trained model, logistic regression on SMART readings, their 30-day changes and drive characteristics, ranks drives far better: its PR-AUC is 0.082, against 0.0073 for the rule and 0.0011 for random selection. At a budget of 1 replacement per 1,000 drives, about 1 in 6 drives it flags goes on to fail. For an operator with a fixed weekly budget of spare drives and technician hours, that is the difference between a list that is mostly noise and one worth acting on.

These results come from the calibration split. The 2025 test year has not been touched and will be scored once, after the final model is locked. The results also have a ceiling: about half of failing drives show no warning in their SMART counters, so no model built on these readings alone will catch every failure. The rest of the project trains and tunes six models, audits them for manufacturer bias, and reports final test results.

## AI Use Disclosure

This course allows AI tools as long as every use is documented. Uses are listed below by team member. Every number in AI-assisted text was checked against the notebooks' saved outputs or the pipeline's output, and each of us can explain the work listed under our name.

### Tyler Katz

Tool: Claude (Anthropic), used through Claude Code.

- **Code:** Claude helped write `scripts/build_dataset.py`, `scripts/build_modeling_table.py` and `documents/data_card.md` at my request, to requirements I set. I reviewed the output.
- **Report, written by me:** sections 1, 2 and 4.1, and the first paragraph of 4.3. Claude checked them for accuracy and typos.
- **Report, edits by Claude at my request:** corrected sections 5 and 9 to match the fixed EDA notebook; formatted Mrgaj's section 7 text as markdown; wrote the logistic regression results in 7.4 and 7.5 and the note under the 7.4 table from the saved outputs of `baselines/baseline_models.ipynb` (not re-run); made sections 3, 8.1 and 9.2 consistent; trimmed the opening of 7.4; corrected typos and one figure in 9.1 to match 6.1.
- **Review:** Claude reviewed the EDA notebook and the baseline notebook against the rules in WORKPLAN.md. I sent the resulting fix lists to Hashim and Mrgaj.
- **Slides:** Claude generated the first draft of the slide deck (`midterm_slides.pptx`) from this report's content, including the suggested speaker notes. The team reviewed and revised it.

### Hashim Khan

-Tool: Claude (Anthropic), used through Claude Code.

- **EDA Notebook**: Claude helped debug code and helped make the notbook look aesthetically better. It helped make the graphs look more organized and color coded them. It was also used to drive meaningful information from the results.

- **Report, written by me**: It proof read my part to make sure english language was followed, no grammatical error or spelling mistakes were made.

### Mrgaj Iyer

- _To be added by Mrgaj._

## References

[^backblaze_durability]: Backblaze. "Resiliency, Durability, and Availability." *Backblaze B2 Cloud Storage Documentation*. Accessed October 15, 2026. https://www.backblaze.com/docs/cloud-storage-resiliency-durability-and-availability

[^backblaze_drivestats]: Backblaze. "Hard Drive Reliability Test Data." *Backblaze Drive Stats*, Q1 2023 through Q4 2025 quarterly archives. Accessed October 15, 2026. https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data

[^pinheiro2007]: Pinheiro, E., Weber, W.-D. and Barroso, L. A. "Failure Trends in a Large Disk Drive Population." *Proceedings of the 5th USENIX Conference on File and Storage Technologies (FAST '07)*, 2007. https://www.usenix.org/legacy/event/fast07/tech/full_papers/pinheiro/pinheiro.pdf

[^schroeder2007]: Schroeder, B. and Gibson, G. A. "Disk Failures in the Real World: What Does an MTTF of 1,000,000 Hours Mean to You?" *Proceedings of the 5th USENIX Conference on File and Storage Technologies (FAST '07)*, 2007. https://www.usenix.org/legacy/event/fast07/tech/schroeder/schroeder.pdf

[^klein2016]: Klein, A. "What SMART Stats Tell Us About Hard Drives." *Backblaze Blog*, October 6, 2016. https://www.backblaze.com/blog/what-smart-stats-indicate-hard-drive-failures/

[^murray2005]: Murray, J. F., Hughes, G. F. and Kreutz-Delgado, K. "Machine Learning Methods for Predicting Failures in Hard Drives: A Multiple-Instance Application." *Journal of Machine Learning Research*, 6, 2005, pp. 783-816. https://jmlr.org/papers/v6/murray05a.html

[^li2014]: Li, J., Ji, X., Jia, Y., Zhu, B., Wang, G., Li, Z. and Liu, X. "Hard Drive Failure Prediction Using Classification and Regression Trees." *2014 44th Annual IEEE/IFIP International Conference on Dependable Systems and Networks (DSN)*, 2014, pp. 383-394. https://doi.org/10.1109/DSN.2014.44

[^botezatu2016]: Botezatu, M. M., Giurgiu, I., Bogojeska, J. and Wiesmann, D. "Predicting Disk Replacement towards Reliable Data Centers." *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 2016, pp. 39-48. https://doi.org/10.1145/2939672.2939699

[^aussel2017]: Aussel, N., Jaulin, S., Gandon, G., Petetin, Y., Fazli, E. and Chabridon, S. "Predictive Models of Hard Drive Failures Based on Operational Data." *16th IEEE International Conference on Machine Learning and Applications (ICMLA)*, 2017, pp. 619-625. https://doi.org/10.1109/ICMLA.2017.00-92

[^lu2020]: Lu, S., Luo, B., Patel, T., Yao, Y., Tiwari, D. and Shi, W. "Making Disk Failure Predictions SMARTer!" *18th USENIX Conference on File and Storage Technologies (FAST '20)*, 2020, pp. 151-167. https://www.usenix.org/conference/fast20/presentation/lu

[^amram2021]: Amram, M., Dunn, J., Toledano, J. J. and Zhuo, Y. D. "Interpretable Predictive Maintenance for Hard Drives." arXiv:2102.06509, 2021. https://arxiv.org/abs/2102.06509
