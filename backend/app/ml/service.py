"""ML ↔ DB entegrasyonu: veri seti çıkarma, eğitim, tahmin kaydı, gerçekleşenle karşılaştırma.

ML hataları operasyonu (stok/lot/recall) etkilemez: bu modül yalnızca okur ve ml_predictions'a yazar.
"""

import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.ml import modeling
from app.models import (ButcheringOrder, ButcheringOutput, ButcheringWasteRecord, MlPrediction, Product,
                        ProductionInput, ProductionOrder, ProductionServiceCost)
from app.models.types import utcnow

MASS_TO_KG = {"KG": 1.0, "G": 0.001}
KIND_FILE = {"production_yield": "production_yield.joblib", "butchering_output": "butchering_output.joblib"}
_cache: dict[str, tuple[float, dict]] = {}


def _dir() -> Path:
    p = Path(get_settings().ml_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def artifact(kind: str) -> dict | None:
    path = _dir() / KIND_FILE[kind]
    if not path.exists():
        return None
    m = path.stat().st_mtime
    hit = _cache.get(kind)
    if hit and hit[0] == m:
        return hit[1]
    art = modeling.load(str(path))
    _cache[kind] = (m, art)
    return art


# ---- veri setleri ---------------------------------------------------------------------------------------------
def _order_features(db: Session, order: ProductionOrder) -> dict | None:
    inputs = db.scalars(select(ProductionInput).where(ProductionInput.production_order_id == order.id)).all()
    kg = {i.id: float(i.quantity) * MASS_TO_KG.get(i.unit_code, 0.0) for i in inputs}
    total_kg = sum(kg.values())
    if total_kg <= 0:
        return None
    main = max(kg.values())
    input_cost = float(sum((i.total_cost for i in inputs), Decimal("0")))
    svc = db.scalars(select(ProductionServiceCost).where(ProductionServiceCost.production_order_id == order.id)).all()
    unit_prices = [float(s.unit_price) for s in svc if s.unit_price is not None]
    if unit_prices:
        svc_unit = sum(unit_prices)
    elif svc and order.planned_quantity:
        svc_unit = float(sum((s.amount for s in svc), Decimal("0"))) / float(order.planned_quantity)
    else:
        svc_unit = 0.0
    when = order.completed_at or order.started_at or utcnow()
    return {"total_input_kg": total_kg, "main_share": main / total_kg,
            "other_ratio": (total_kg - main) / main if main else 0.0, "cost_per_kg": input_cost / total_kg,
            "month": when.month, "supplier_id": order.supplier_id or 0, "input_cost": input_cost,
            "service_unit_price": svc_unit}


def production_frame(db: Session) -> pd.DataFrame:
    rows = []
    for o in db.scalars(select(ProductionOrder).where(ProductionOrder.status == "COMPLETED")
                        .order_by(ProductionOrder.completed_at)):
        f = _order_features(db, o)
        if f is None or not o.actual_output_quantity or o.unit_cost_ekp is None:
            continue
        qty = float(o.actual_output_quantity)
        rows.append({**f, "order_id": o.id, "output_qty": qty, "yield_ratio": qty / f["total_input_kg"],
                     "ekp": float(o.unit_cost_ekp), "completed_ts": (o.completed_at or utcnow()).timestamp()})
    return pd.DataFrame(rows)


def _target(code: str) -> str:
    return code.split("-", 1)[1] if "-" in code else code


def _butchering_row(db: Session, o: ButcheringOrder) -> dict | None:
    w = float(o.input_weight)
    outs = db.execute(select(ButcheringOutput, Product).join(Product, Product.id == ButcheringOutput.product_id)
                      .where(ButcheringOutput.butchering_order_id == o.id)).all()
    wastes = db.scalars(select(ButcheringWasteRecord).where(ButcheringWasteRecord.butchering_order_id == o.id)).all()
    if not outs:
        return None
    row = {"order_id": o.id, "animal_type": o.animal_type, "input_weight": w}
    for out, prod in outs:
        row[f"r_{_target(prod.code)}"] = row.get(f"r_{_target(prod.code)}", 0.0) + float(out.actual_weight) / w
    row["r_FIRE"] = float(sum((x.actual_weight for x in wastes), Decimal("0"))) / w
    return row


def butchering_frame(db: Session) -> tuple[pd.DataFrame, list[str]]:
    rows = [r for o in db.scalars(select(ButcheringOrder).where(ButcheringOrder.status == "COMPLETED")
                                  .order_by(ButcheringOrder.id)) if (r := _butchering_row(db, o))]
    df = pd.DataFrame(rows)
    if df.empty:
        return df, []
    ratio_cols = sorted(c for c in df.columns if c.startswith("r_"))
    df[ratio_cols] = df[ratio_cols].fillna(0.0)
    return df, [c[2:] for c in ratio_cols]


# ---- eğitim ---------------------------------------------------------------------------------------------------
def train_all(db: Session) -> dict:
    out = {}
    pdf = production_frame(db)
    art = modeling.train_production(pdf)
    modeling.save(art, str(_dir() / KIND_FILE["production_yield"]))
    out["production_yield"] = summary(art)
    bdf, targets = butchering_frame(db)
    art = modeling.train_butchering(bdf, targets)
    modeling.save(art, str(_dir() / KIND_FILE["butchering_output"]))
    out["butchering_output"] = summary(art)
    _cache.clear()
    return out


def summary(art: dict | None) -> dict | None:
    if art is None:
        return None
    return {"kind": art["kind"], "version": art["version"], "trained_at": art["trained_at"],
            "n_samples": art["n_samples"], "model_name": art["model_name"], "metrics": art["metrics"],
            "limitations": art["limitations"]}


# ---- tahmin ----------------------------------------------------------------------------------------------------
def _dec(x: float, places: str = "0.000001") -> Decimal:
    return Decimal(str(x)).quantize(Decimal(places))


def predict_production(db: Session, order: ProductionOrder, user_id: int) -> MlPrediction:
    art = artifact("production_yield")
    f = _order_features(db, order)
    pred = MlPrediction(prediction_type="PRODUCTION_YIELD_EKP", model_version=art["version"] if art else "none",
                        input_reference_type="production_order", input_reference_id=order.id, created_by=user_id)
    try:
        if art is None:
            raise RuntimeError("Model henüz eğitilmedi.")
        if f is None:
            raise ValueError("Emirde kütle birimli (KG/G) girdi yok; tahmin yapılamaz.")
        r = modeling.predict_production(art, f)
        pred.status = "SUCCEEDED"
        pred.input_summary = {k: round(v, 6) if isinstance(v, float) else v for k, v in f.items()}
        pred.predicted_value, pred.predicted_cost = _dec(r["model"]["output_quantity"]), _dec(r["model"]["ekp"], "0.0001")
        pred.baseline_value, pred.baseline_cost = _dec(r["baseline"]["output_quantity"]), _dec(r["baseline"]["ekp"], "0.0001")
        pred.detail = {"yield_ratio": r["model"]["yield_ratio"], "baseline_yield_ratio": r["baseline"]["yield_ratio"],
                       "interval_95_output_quantity": r["interval_95_output_quantity"], "used_model": r["used_model"],
                       "model_name": art["model_name"]}
        pred.limitations_note = "; ".join(art["limitations"])[:1000]
    except Exception as e:  # ML hatası operasyonu bozmaz; kayıt FAILED olarak tutulur
        pred.status, pred.detail = "FAILED", {"error": str(e)}
    db.add(pred)
    db.flush()
    refresh_actual(db, pred)
    return pred


def predict_butchering(db: Session, animal_type: str, input_weight: Decimal, order: ButcheringOrder | None,
                       user_id: int) -> MlPrediction:
    art = artifact("butchering_output")
    pred = MlPrediction(prediction_type="BUTCHERING_OUTPUT_WEIGHT", model_version=art["version"] if art else "none",
                        input_reference_type="butchering_order" if order else None,
                        input_reference_id=order.id if order else None, created_by=user_id)
    try:
        if art is None:
            raise RuntimeError("Model henüz eğitilmedi.")
        r = modeling.predict_butchering(art, animal_type, float(input_weight))
        parts = r["parts"]
        pred.status = "SUCCEEDED"
        pred.input_summary = {"animal_type": animal_type, "input_weight": str(input_weight),
                              "animal_type_known": r["animal_type_known"]}
        pred.predicted_value = _dec(sum(p["predicted_weight"] for t, p in parts.items() if t != "FIRE"))
        pred.baseline_value = _dec(sum(p["baseline_weight"] for t, p in parts.items() if t != "FIRE"))
        pred.detail = {"parts": parts, "used_model": r["used_model"], "model_name": art["model_name"]}
        notes = list(art["limitations"])
        if not r["animal_type_known"]:
            notes.append(f"'{animal_type}' eğitim verisinde yok: genel ortalama baseline kullanıldı.")
        pred.limitations_note = "; ".join(notes)[:1000]
    except Exception as e:
        pred.status, pred.detail = "FAILED", {"error": str(e)}
    db.add(pred)
    db.flush()
    refresh_actual(db, pred)
    return pred


def refresh_actual(db: Session, pred: MlPrediction) -> None:
    """Emir tamamlandıysa gerçekleşeni ve sapmayı doldurur (tahmin–gerçek birlikte gösterim)."""
    if pred.status != "SUCCEEDED" or pred.actual_value is not None or not pred.input_reference_id:
        return
    if pred.prediction_type == "PRODUCTION_YIELD_EKP":
        o = db.get(ProductionOrder, pred.input_reference_id)
        if o and o.status == "COMPLETED" and o.actual_output_quantity is not None:
            pred.actual_value, pred.actual_cost = o.actual_output_quantity, o.unit_cost_ekp
            err = abs(pred.predicted_value - pred.actual_value)
            pred.metric_name, pred.error_value = "ABS_ERROR_QUANTITY", err
            pred.detail = {**(pred.detail or {}),
                           "deviation_quantity": float(pred.actual_value - pred.predicted_value),
                           "deviation_percent": float((pred.actual_value - pred.predicted_value) / pred.actual_value * 100),
                           "ekp_deviation": float(pred.actual_cost - pred.predicted_cost),
                           "baseline_abs_error_quantity": float(abs(pred.baseline_value - pred.actual_value))}
    else:
        o = db.get(ButcheringOrder, pred.input_reference_id)
        if o and o.status == "COMPLETED":
            row = _butchering_row(db, o) or {}
            w = float(o.input_weight)
            parts = (pred.detail or {}).get("parts", {})
            total_abs, base_abs, actual_total = 0.0, 0.0, 0.0
            for t, p in parts.items():
                actual = row.get(f"r_{t}", 0.0) * w
                p["actual_weight"] = actual
                p["deviation_weight"] = actual - p["predicted_weight"]
                total_abs += abs(p["deviation_weight"])
                base_abs += abs(actual - p["baseline_weight"])
                if t != "FIRE":
                    actual_total += actual
            pred.actual_value = _dec(actual_total)
            pred.metric_name, pred.error_value = "MAE_KG_PER_PRODUCT", _dec(total_abs / max(len(parts), 1))
            pred.detail = {**pred.detail, "parts": parts, "baseline_mae_kg_per_product": base_abs / max(len(parts), 1)}
    db.flush()
