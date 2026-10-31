import sqlite3
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath("backend"))
from app.ml import service as ml_service
from app.ml import modeling
from app.ml.anomaly_model import isolation_outliers

engine = create_engine("sqlite:///backend/avatar_demo.db")
with Session(engine) as session:
    pdf = ml_service.production_frame(session)
    bdf, targets = ml_service.butchering_frame(session)
    print(f"Production orders count: {len(pdf)}")
    print(f"Butchering orders count: {len(bdf)}, targets: {targets}")

    # Model 1
    art1 = modeling.train_production(pdf)
    m1_cv = art1["metrics"]["cross_validation"]
    print("--- MODEL 1 METRICS ---")
    print(f"Selected: {m1_cv['selected_model']}")
    base1_out = m1_cv["by_model"]["BASELINE_MEAN"]["output_quantity"]
    mod1_out = m1_cv["by_model"][m1_cv["selected_model"]]["output_quantity"]
    base1_ekp = m1_cv["by_model"]["BASELINE_MEAN"]["ekp"]
    mod1_ekp = m1_cv["by_model"][m1_cv["selected_model"]]["ekp"]
    print(f"Output Quantity Baseline MAE: {base1_out['mae']:.4f}, Model MAE: {mod1_out['mae']:.4f}")
    print(f"EKP Baseline MAE: {base1_ekp['mae']:.4f}, Model MAE: {mod1_ekp['mae']:.4f}")
    hold1 = art1["metrics"]["temporal_holdout"]
    print(f"Temporal Holdout n={hold1['n_test']}, coverage={hold1['interval_95_coverage_percent']}%")

    # Model 2
    art2 = modeling.train_butchering(bdf, targets)
    m2_cv = art2["metrics"]["cross_validation"]
    print("--- MODEL 2 METRICS ---")
    print(f"Selected: {m2_cv['selected_model']}")
    base2 = m2_cv["by_model"]["BASELINE_ANIMAL_MEAN"]["overall"]
    mod2 = m2_cv["by_model"][m2_cv["selected_model"]]["overall"]
    print(f"Overall MAE Baseline: {base2['mae_kg']:.4f} kg, Model: {mod2['mae_kg']:.4f} kg")
    print(f"Overall WMAPE Baseline: {base2['wmape_percent']:.2f}%, Model: {mod2['wmape_percent']:.2f}%")
    print(f"Interval 95 coverage: {m2_cv['interval_95_coverage_percent']}%")

# Clustered Bootstrap analysis on Butchering orders
print("\n--- CLUSTERED BOOTSTRAP (B=10,000) ---")
rng = np.random.default_rng(42)
n_carcasses = len(bdf)
cols = [f"r_{t}" for t in targets]
Y = bdf[cols].to_numpy()
w = bdf["input_weight"].to_numpy()

# Get out-of-fold predictions from train_butchering
kf = modeling.KFold(5, shuffle=True, random_state=42)
X = bdf[modeling.BUT_NUM + modeling.BUT_CAT]
cands = {"RANDOM_FOREST": lambda: modeling._pipe(modeling.RandomForestRegressor(n_estimators=200, min_samples_leaf=2, random_state=0, n_jobs=1), modeling.BUT_NUM, modeling.BUT_CAT, False)}
oof_rf = np.zeros_like(Y)
for tr, te in kf.split(X):
    oof_rf[te] = cands["RANDOM_FOREST"]().fit(X.iloc[tr], Y[tr]).predict(X.iloc[te])

sigma = np.std(oof_rf - Y, axis=0, ddof=1)
half = 1.96 * sigma
inside_matrix = np.abs(oof_rf - Y) <= half # shape: (150, 7)

# Carcass-level coverage rate for each carcass (mean across its 7 cuts)
carcass_coverage = inside_matrix.mean(axis=1) # shape (150,)
# Binary: all 7 inside
all_7_inside = (inside_matrix.sum(axis=1) == len(targets))
at_least_6 = (inside_matrix.sum(axis=1) >= len(targets) - 1)

print(f"Carcasses with all 7 cuts inside: {all_7_inside.sum()}/{n_carcasses} ({all_7_inside.mean()*100:.1f}%)")
print(f"Carcasses with at least 6 cuts inside: {at_least_6.sum()}/{n_carcasses} ({at_least_6.mean()*100:.1f}%)")

# Clustered bootstrap over carcasses
B = 10000
boot_means = np.zeros(B)
for b in range(B):
    idx = rng.choice(n_carcasses, size=n_carcasses, replace=True)
    # mean coverage across all cuts in the sampled carcasses
    boot_means[b] = inside_matrix[idx].mean() * 100

se_clustered = np.std(boot_means, ddof=1)
ci_lower = np.percentile(boot_means, 2.5)
ci_upper = np.percentile(boot_means, 97.5)
mean_cov = np.mean(boot_means)

print(f"Clustered Bootstrap Mean: {mean_cov:.2f}%")
print(f"Clustered SE: {se_clustered:.2f}%")
print(f"Clustered 95% CI: [{ci_lower:.2f}%, {ci_upper:.2f}%]")

# Model 3 Anomaly Detection
print("\n--- MODEL 3 ANOMALY DETECTION ---")
from app.services import anomaly as anomaly_service
with Session(engine) as session:
    alerts_created = anomaly_service.scan(session)
    print(f"Newly created alerts during scan: {len(alerts_created)}")
    for a in alerts_created:
        print(f"  - [{a.severity}] {a.alert_type}: {a.message} (entity: {a.entity_type} #{a.entity_id})")
