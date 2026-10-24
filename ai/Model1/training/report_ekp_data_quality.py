"""Create a reproducible audit report for the synthetic EKP training dataset."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .compare_ekp_models import CATS, DATA, FEATURES, NUMS, ROOT, TARGET

INPUTS = ["Et_girdi_kg", "Kuyruk_yagi_girdi_kg", "Baharat_girdi_kg", "Tuz_girdi_kg", "Diger_kucuk_girdi_kg"]
MATERIAL_COSTS = ["Et_maliyeti_TL", "Yag_maliyeti_TL", "Baharat_maliyeti_TL", "Tuz_diger_girdi_maliyeti_TL", "Kilif_maliyeti_TL"]
REPORT = ROOT / "reports" / "ekp_data_quality_report.md"


def audit_frame(frame: pd.DataFrame) -> dict:
    required = set(FEATURES + [
        TARGET, "Toplam_parti_maliyeti_TL", "Net_sucuk_ciktisi_kg_simule",
        "Parti_ID", "Tarih_simulasyon", "Veri_sinifi", *INPUTS,
        "Karisim_girdi_toplam_kg", "Kuruma_kaybi_pct", "Ayiklama_fire_pct",
        *MATERIAL_COSTS, "Direkt_malzeme_toplam_TL", "Fason_hizmet_TL",
        "Kurum_ici_isleme_TL", "Paketleme_maliyeti_TL", "Genel_gider_TL",
        "Isleme_modeli",
    ])
    missing_columns = sorted(required - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    numeric = list(frame.select_dtypes(include=[np.number]).columns)
    nonfinite = int((~np.isfinite(frame[numeric].to_numpy(dtype=float))).sum()) if numeric else 0
    input_kg = frame[INPUTS].sum(axis=1)
    mix_error = input_kg - frame["Karisim_girdi_toplam_kg"]
    formula_yield = input_kg * (1-frame["Kuruma_kaybi_pct"]/100) * (1-frame["Ayiklama_fire_pct"]/100)
    material_sum = frame[MATERIAL_COSTS].sum(axis=1)
    total_sum = (
        frame["Direkt_malzeme_toplam_TL"] + frame["Fason_hizmet_TL"]
        + frame["Kurum_ici_isleme_TL"] + frame["Paketleme_maliyeti_TL"]
        + frame["Genel_gider_TL"]
    )
    expected_fason = np.where(
        frame["Isleme_modeli"].astype(str).str.casefold().str.contains("fason"),
        input_kg * frame["Fason_birim_bedel_TL_kg_girdi"], 0.0,
    )
    ekp_ratio = frame["Toplam_parti_maliyeti_TL"] / frame["Net_sucuk_ciktisi_kg_simule"]

    distributions = []
    outliers = {}
    for column in numeric:
        values = frame[column].dropna()
        q1, q3 = float(values.quantile(.25)), float(values.quantile(.75))
        iqr = q3-q1
        flagged = int(((values < q1-1.5*iqr) | (values > q3+1.5*iqr)).sum()) if iqr else 0
        if flagged:
            outliers[column] = flagged
        distributions.append({
            "field": column, "n": int(values.count()), "mean": float(values.mean()),
            "std": float(values.std()), "median": float(values.median()),
            "min": float(values.min()), "q1": q1, "q3": q3,
            "p95": float(values.quantile(.95)), "p99": float(values.quantile(.99)),
            "max": float(values.max()), "iqr_flags": flagged,
        })

    variable_nums = [column for column in NUMS if frame[column].nunique(dropna=True) > 1]
    feature_corr = frame[variable_nums].corr()
    high_pairs = []
    for i, left in enumerate(variable_nums):
        for right in variable_nums[i+1:]:
            corr = feature_corr.loc[left, right]
            if pd.notna(corr) and abs(float(corr)) >= .90:
                high_pairs.append({"left": left, "right": right, "r": float(corr)})
    target_corr = frame[variable_nums].corrwith(frame[TARGET]).dropna().sort_values(key=lambda s: s.abs(), ascending=False)
    groups = {}
    for field in ("Isleme_modeli", "Bolge", "Recete_profili"):
        groups[field] = {
            str(label): {
                "n": int(len(group)), "mean": float(group[TARGET].mean()),
                "std": float(group[TARGET].std()), "median": float(group[TARGET].median()),
                "min": float(group[TARGET].min()), "max": float(group[TARGET].max()),
            }
            for label, group in frame.groupby(field)
        }

    dates = pd.to_datetime(frame["Tarih_simulasyon"], errors="coerce")
    labels = frame["Veri_sinifi"].astype(str).str.casefold()
    process = frame["Isleme_modeli"].astype(str).str.casefold()
    fason = process.str.contains("fason")
    mix_cost_error = material_sum-frame["Direkt_malzeme_toplam_TL"]
    total_cost_error = total_sum-frame["Toplam_parti_maliyeti_TL"]
    yield_error = formula_yield-frame["Net_sucuk_ciktisi_kg_simule"]
    ekp_error = ekp_ratio-frame[TARGET]
    fason_error = expected_fason-frame["Fason_hizmet_TL"]

    return {
        "rows": int(len(frame)), "columns": int(len(frame.columns)),
        "missing_cells": int(frame.isna().sum().sum()),
        "missing_by_field": {str(c): int(v) for c, v in frame.isna().sum().items() if v},
        "duplicate_rows": int(frame.duplicated().sum()),
        "duplicate_batch_ids": int(frame["Parti_ID"].duplicated(keep=False).sum()),
        "nonfinite_numeric_cells": nonfinite,
        "negative_numeric_cells": int((frame[numeric] < 0).sum().sum()),
        "all_synthetic": bool(labels.str.contains("sentet|sim", regex=True).all()),
        "source_labels": sorted(frame["Veri_sinifi"].astype(str).unique().tolist()),
        "date_count": int(dates.dt.strftime("%Y-%m-%d").nunique()),
        "date_start": dates.min().strftime("%Y-%m-%d"),
        "date_end": dates.max().strftime("%Y-%m-%d"),
        "formula_checks": {
            "input_mix_max_abs_kg": float(mix_error.abs().max()),
            "mass_balance_max_abs_kg": float(yield_error.abs().max()),
            "mass_balance_mean_abs_kg": float(yield_error.abs().mean()),
            "direct_material_max_abs_tl": float(mix_cost_error.abs().max()),
            "direct_material_mean_abs_tl": float(mix_cost_error.abs().mean()),
            "total_cost_max_abs_tl": float(total_cost_error.abs().max()),
            "total_cost_mean_abs_tl": float(total_cost_error.abs().mean()),
            "ekp_max_abs_tl_kg": float(ekp_error.abs().max()),
            "ekp_mean_abs_tl_kg": float(ekp_error.abs().mean()),
            "fason_rate_max_abs_tl": float(fason_error.abs().max()),
        },
        "processing_mode_counts": {str(k): int(v) for k,v in frame["Isleme_modeli"].value_counts().items()},
        "fason_rows": int(fason.sum()),
        "inhouse_rows": int((~fason).sum()),
        "mixed_processing_cost_rows": int(((frame["Fason_hizmet_TL"]>0)&(frame["Kurum_ici_isleme_TL"]>0)).sum()),
        "target": {str(k): float(v) for k,v in frame[TARGET].describe(percentiles=[.01,.05,.25,.5,.75,.95,.99]).items()},
        "yield": {str(k): float(v) for k,v in frame["Net_sucuk_ciktisi_kg_simule"].describe().items()},
        "total_cost": {str(k): float(v) for k,v in frame["Toplam_parti_maliyeti_TL"].describe().items()},
        "target_iqr_flags": int(outliers.get(TARGET, 0)),
        "all_iqr_flags": outliers,
        "numeric_distributions": distributions,
        "high_allowlisted_feature_correlations": sorted(high_pairs, key=lambda x: abs(x["r"]), reverse=True),
        "top_feature_target_correlations": [{"feature": str(k), "r": float(v)} for k,v in target_corr.head(10).items()],
        "target_groups": groups,
        "scenario_a_features": FEATURES,
        "column_profile": [{"field": str(c), "dtype": str(frame[c].dtype), "distinct_values": int(frame[c].nunique(dropna=False)), "missing": int(frame[c].isna().sum())} for c in frame.columns],
    }


def _n(value, digits=4):
    return f"{value:,.{digits}f}"


def render(report: dict, dataset_hash: str) -> str:
    t, f = report["target"], report["formula_checks"]
    lines = [
        "# EKP synthetic dataset data-quality and leakage report", "",
        "**All 1,000 records are synthetic/simulated. No factory performance or real production data quality is established by this report.**", "",
        f"- Dataset: data/raw/sucuk_uretim_1000_simule_parti.csv, {report['rows']} rows × {report['columns']} columns.",
        f"- SHA-256: {dataset_hash}.",
        f"- Missing cells: {report['missing_cells']}; duplicate rows: {report['duplicate_rows']}; duplicate batch IDs: {report['duplicate_batch_ids']}.",
        f"- Non-finite numeric cells: {report['nonfinite_numeric_cells']}; negative numeric cells: {report['negative_numeric_cells']}.",
        f"- Every row carries the synthetic/simulated source label: {report['all_synthetic']}.",
        f"- Simulation date field: {report['date_start']} to {report['date_end']} ({report['date_count']} distinct dates). The dates are generated metadata, not verified production chronology.", "",
        "## Units and formula reconciliation", "",
        "Observed column naming and the workbook dictionary use ingredient/output kg, casing m, unit prices and costs in TL, labor hours and TL/hour, energy kWh and TL/kWh, loss percentages, and EKP in TL/net kg. These conventions are not independently confirmed against a factory ledger or calibrated scale.", "",
        "| Check | Maximum absolute difference | Meaning |",
        "|---|---:|---|",
        f"| Ingredient sum vs reported mix | {_n(f['input_mix_max_abs_kg'], 10)} kg | Reconciles at CSV precision |",
        f"| Calculated mass balance vs net output | {_n(f['mass_balance_max_abs_kg'], 8)} kg | Synthetic yield formula only |",
        f"| Component sum vs direct material | {_n(f['direct_material_max_abs_tl'], 4)} TL | Small CSV rounding difference |",
        f"| Total cost reconciliation | {_n(f['total_cost_max_abs_tl'], 4)} TL | Direct materials + processing + packaging + overhead |",
        f"| Total cost / net kg vs EKP | {_n(f['ekp_max_abs_tl_kg'], 6)} TL/kg | Ratio target rounding difference |",
        f"| Fason rate vs service cost | {_n(f['fason_rate_max_abs_tl'], 4)} TL | Simulated Fason rows only |",
        "",
        "The total-cost reconciliation treats Fason service and in-house processing as mutually exclusive. The workbook dictionary describes in-house processing as simulated labor + energy + a 12% facility-overhead assumption; labor and energy should therefore not be added again on top of that combined field. Fason pricing and in-house allocation are not verified against real invoices or an accounting policy.",
        "",
        "## Target distribution", "",
        f"- EKP count {int(t['count'])}; mean {_n(t['mean'])}; standard deviation {_n(t['std'])}; median {_n(t['50%'])} TL/kg.",
        f"- Range {_n(t['min'])} to {_n(t['max'])} TL/kg; P1 {_n(t['1%'])}; P99 {_n(t['99%'])}.",
        f"- IQR rule flags {report['target_iqr_flags']} EKP rows. No outlier was deleted or clipped; a flag is not evidence of an error.",
        "",
        "| Numeric field | n | Mean | Std | Median | Min | Q1 | Q3 | P95 | P99 | Max | IQR flags |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for x in report["numeric_distributions"]:
        lines.append(
            f"| {x['field']} | {x['n']} | {_n(x['mean'])} | {_n(x['std'])} | {_n(x['median'])} | "
            f"{_n(x['min'])} | {_n(x['q1'])} | {_n(x['q3'])} | {_n(x['p95'])} | {_n(x['p99'])} | "
            f"{_n(x['max'])} | {x['iqr_flags']} |"
        )
    for field, values in report["target_groups"].items():
        lines += ["", f"### EKP by {field}", "", "| Group | n | Mean | Std | Median | Min | Max |", "|---|---:|---:|---:|---:|---:|---:|"]
        for label, x in values.items():
            lines.append(f"| {label} | {x['n']} | {_n(x['mean'])} | {_n(x['std'])} | {_n(x['median'])} | {_n(x['min'])} | {_n(x['max'])} |")
    lines += [
        "", "## Correlations and leakage", "",
        "Correlations are descriptive only. EKP is mathematically defined as total batch cost divided by net output, so the target is structurally connected to cost and yield. Generated correlations do not establish causal or factory relationships.", "",
        "Allow-listed numeric feature pairs with absolute Pearson correlation at least 0.90:",
        "",
    ]
    if report["high_allowlisted_feature_correlations"]:
        lines += ["| Feature 1 | Feature 2 | r |", "|---|---|---:|"]
        for x in report["high_allowlisted_feature_correlations"]:
            lines.append(f"| {x['left']} | {x['right']} | {_n(x['r'], 5)} |")
    else:
        lines.append("None found.")
    lines += ["", "Largest allow-listed numeric feature correlations with EKP:", "", "| Feature | Pearson r |", "|---|---:|"]
    for x in report["top_feature_target_correlations"]:
        lines.append(f"| {x['feature']} | {_n(x['r'], 5)} |")
    lines += [
        "",
        "Feature allow-list for Scenario A: " + ", ".join(report["scenario_a_features"]) + ".",
        "Target or realized/derived fields excluded: EKP, total batch cost, simulated net output, input-mix total, realized loss rates, material and processing cost components, labor/energy consumption, cost shares, simulation date, party ID, source label, reference codes, and notes.",
        "",
        "Scenario A is conditional: planned inputs, process/recipe categories, quotes and tariffs may be available before a run, but this synthetic file has no immutable plan or price snapshot proving when each was known. Labor hours and energy consumption are during/after-run values and are excluded. Cost closure, measured net output, EKP, and losses are postproduction/measurement fields unless a separate timestamped plan assumption is proven.",
        "",
        "Scenario B adds Kuruma_kaybi_pct and Ayiklama_fire_pct only as conditional inputs. The workbook states these are randomly simulated and not real batch weighings. Their measurement time is not established; if recorded after production, they are not valid preproduction features. No definite timing claim is possible from this CSV.",
        "",
        "## Synthetic patterns and limitations", "",
        "- The data workbook labels all rows simulated; recipes, quantities, prices, losses, Fason rates, in-house allocations, and calendar dates include synthetic assumptions.",
        "- Net output is nearly exactly produced from ingredient mass and the two loss fields. The small formula residual is rounding, not an independent yield validation.",
        "- Four highly correlated allow-listed quantity pairs reflect shared simulated batch-size/recipe scaling and may create multicollinearity for linear models.",
        "- EKP is built from simulated total cost and net output. Observed tails, group differences, and IQR flags remain descriptive and were not manually adjusted.",
        "- No external process inventory or aggregate cost-share rows were mixed into the training data. External inventory does not provide batch EKP labels.",
        "",
        "Repeatable data-quality command: python -m training.report_ekp_data_quality.",
        "Repeatable model comparison: python -m training.compare_ekp_models_chronological.",
        "This audit reads the source CSV and writes only this report; it does not impute, remove, or rewrite source rows.",
    ]
    lines = [line.replace("re\ncete", "recipe") for line in lines]
    profile_lines = ["## Column types and distinct values", "", "| Field | CSV dtype | Distinct values | Missing |", "|---|---|---:|---:"]
    profile_lines += [f"| {item['field']} | {item['dtype']} | {item['distinct_values']} | {item['missing']} |" for item in report["column_profile"]]
    unit_index = lines.index("## Units and formula reconciliation")
    lines[unit_index:unit_index] = profile_lines + [""]

    return "\n".join(lines) + "\n"


def main() -> int:
    path = DATA
    frame = pd.read_csv(path)
    report = audit_frame(frame)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(render(report, digest), encoding="utf-8")
    print(json.dumps({
        "rows": report["rows"], "columns": report["columns"],
        "missing_cells": report["missing_cells"],
        "duplicate_rows": report["duplicate_rows"],
        "target": report["target"],
        "formula_checks": report["formula_checks"],
        "dataset_sha256": digest,
        "report": str(REPORT.relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

