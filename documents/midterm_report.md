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

### 5.1 Analysis 1: Class Distribution and Failure Prevalence

We examined the failure rate in each split with the 95% Wilson confidence interval on each window. As the failures are very rare in the original data, the train set was rebalanced. A model trained on the 1:20 ratio gives out a lot of false negatives, and if a model was to predict a drive not to fail for all test data that it would get an accuracy of 99%, which is misleading. 

As a result we came to the conclusion that there is a severe imbalance. The train has 1 failure : 20 healthy (4.76%). Calib and test are about 1 : 900 (0.11%). A classifier trained on this data will over predict failure. To counter this we need to take into account PR-AUC or set a false alarm rate.

| Split | Period | Drive-windows | Failures | Failure rate (95% Wilson CI) | Healthy : failed |
|---|---|---|---|---|---|
| Train | Jan 2023 – Oct 2024 | 169,827 | 8,087 | 4.762% (4.662–4.864%) | 20 : 1 |
| Calibration | Nov – Dec 2024 | 297,009 | 328 | 0.110% (0.099–0.123%) | 905 : 1 |
| Test | Jan – Dec 2025 | 3,521,973 | 3,722 | 0.106% (0.102–0.109%) | 945 : 1 |

### 5.2 Analysis 2: SMART 5 — Reallocated Sectors

### 5.3 Analysis 3: SMART 197 — Current Pending Sectors

### 5.4 Analysis 4: SMART 198 — Offline Uncorrectable Sectors

### 5.5 Analysis 5: Changes in SMART Values Over the 30-Day Window

### 5.6 Additional EDA Findings

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

### 9.2 Missing and Manufacturer-Dependent SMART Attributes

### 9.3 Data Volume and Processing

### 9.4 Temporal Distribution Shift and Unseen Drive Models

### 9.5 Challenges Encountered and Workarounds

## 10. Conclusion

## References

[^pinheiro2007]: Pinheiro, E., Weber, W.-D. and Barroso, L. A. "Failure Trends in a Large Disk Drive Population." *Proceedings of the 5th USENIX Conference on File and Storage Technologies (FAST '07)*, 2007. https://www.usenix.org/legacy/event/fast07/tech/full_papers/pinheiro/pinheiro.pdf

[^schroeder2007]: Schroeder, B. and Gibson, G. A. "Disk Failures in the Real World: What Does an MTTF of 1,000,000 Hours Mean to You?" *Proceedings of the 5th USENIX Conference on File and Storage Technologies (FAST '07)*, 2007. https://www.usenix.org/legacy/event/fast07/tech/schroeder/schroeder.pdf
