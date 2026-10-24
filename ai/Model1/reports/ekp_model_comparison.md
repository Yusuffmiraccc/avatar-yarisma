# EKP model comparison — chronological research evaluation

Data notice: All 1,000 rows are synthetic/simulated. No real factory evaluation was performed.

## Target and split

- Target: total batch cost TRY / simulated net output kg = TRY/kg.
- Dataset SHA-256: 5c4fbd9c4897d6b5f1d6a8fcdb113e551122a7862f6a65ce844358e3afe1850e.
- Train: 789 rows, 2026-09-01 to 2026-10-11.
- Holdout: 211 rows, 2026-10-12 to 2026-10-22; whole dates remain together.
- Model selection: 5 expanding date folds inside training dates only; holdout did not select estimators.
- The dates are generated simulation dates, not a real factory timeline.

## Comparison

CV values are mean ± fold standard deviation. Each candidate uses the same trailing-date holdout. Holdout change is model minus training-median baseline; positive means larger error. Improvement percentage is baseline-relative.

| Model | CV MAE | CV RMSE | CV R² | Holdout MAE | Holdout RMSE | Holdout R² | MAE improvement vs median |
|---|---:|---:|---:|---:|---:|---:|---:|
| huber_regressor | 48.4457 ± 2.6859 | 60.9184 ± 2.3710 | 0.1152 ± 0.0652 | 52.6041 | 66.2836 | 0.1075 | 6.08% |
| ridge | 48.9222 ± 2.0965 | 59.8865 ± 2.1527 | 0.1460 ± 0.0382 | 53.4674 | 64.9444 | 0.1432 | 4.54% |
| engineered_gradient_boosting_huber | 50.2956 ± 2.2927 | 61.9633 ± 2.1166 | 0.0841 ± 0.0711 | 51.5420 | 63.7507 | 0.1744 | 7.98% |
| hybrid_known_cost_plus_residual_over_predicted_yield_rf | 50.4496 ± 3.1197 | 63.8985 ± 4.7095 | 0.0187 ± 0.1734 | 57.6474 | 71.1637 | -0.0288 | -2.92% |
| gradient_boosting_huber | 50.5404 ± 1.7855 | 62.6673 ± 1.7270 | 0.0621 ± 0.0836 | 52.5768 | 65.5595 | 0.1269 | 6.13% |
| hist_gradient_boosting | 50.7605 ± 1.8366 | 62.5821 ± 2.7398 | 0.0648 ± 0.0919 | 53.6767 | 65.5101 | 0.1282 | 4.17% |
| extra_trees | 50.8886 ± 1.6086 | 62.8145 ± 2.0421 | 0.0578 ± 0.0860 | 52.6937 | 64.1450 | 0.1641 | 5.92% |
| random_forest_incumbent_architecture | 51.1207 ± 1.5302 | 62.7952 ± 2.2911 | 0.0590 ± 0.0784 | 54.2300 | 66.1888 | 0.1100 | 3.18% |
| median_baseline | 52.1479 ± 2.9987 | 66.6995 ± 2.7609 | -0.0590 ± 0.0455 | 56.0123 | 71.7718 | -0.0464 | 0.00% |
| predicted_cost_over_predicted_yield_rf | 52.7526 ± 3.4527 | 66.1288 ± 4.1896 | -0.0482 ± 0.1584 | 60.5867 | 74.9097 | -0.1399 | -8.17% |
| mean_baseline | 53.1705 ± 3.0527 | 65.0496 ± 2.9678 | -0.0063 ± 0.0102 | 57.1142 | 70.1840 | -0.0006 | -1.97% |

CV leader by MAE: huber_regressor; synthetic research ranking only.

## Methods and leakage controls

- Compared median and mean baselines, the incumbent Random Forest architecture, Extra Trees, Huber Gradient Boosting, HistGradientBoosting, Ridge, HuberRegressor, and the prior engineered Huber GradientBoosting architecture.
- Also compared predicted total cost / predicted net output and a planned known-cost subtotal plus predicted residual divided by predicted net output. Component estimators were fit on training rows only.
- Imputation, scaling, and one-hot encoding are in pipelines fit separately within each fold.
- Scenario A uses the 18 allow-listed input, category, and quote/tariff fields; their real preproduction timing is not verified.
- Scenario B loss rates are simulated and timing is unverified; they are not part of the candidate ranking.
- Target, realized net output, total cost, cost components, and loss percentages are excluded from Scenario A features.

## Existing artifacts

Production and saved candidate artifacts were not deserialized or changed. Their training date membership is unavailable, so their scores are not represented as unseen-date results. Hashes and reasons are in the JSON report.
Existing shuffled-split reports are retained as historical results and are not directly comparable to this split.

## Decision

No EKP model is recommended for production. Real factory data, verified feature timing, and an untouched site/time validation are still required.
Repeat from the Model1 directory: python -m training.compare_ekp_models_chronological.
Machine-readable reports: reports/ekp_model_comparison.json and reports/ekp_model_comparison.csv.
