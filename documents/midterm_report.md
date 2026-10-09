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

### 5.1 Analysis 1: Class Distribution and Failure Prevalence

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
