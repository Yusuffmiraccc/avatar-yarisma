"""CLI prediction example for the prototype model."""
from __future__ import annotations
import argparse
from pathlib import Path
import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "production_quantity_model.joblib"


def main() -> int:
    parser = argparse.ArgumentParser(description="Model 1 prototip üretim miktarı tahmini")
    parser.add_argument("--planned-quantity", type=float, required=True)
    parser.add_argument("--product-id", required=True)
    parser.add_argument("--shift", required=True)
    parser.add_argument("--production-line", required=True)
    parser.add_argument("--product-category", default="Unknown")
    parser.add_argument("--standard-cost", type=float, default=float("nan"))
    parser.add_argument("--unit-price", type=float, default=float("nan"))
    parser.add_argument("--month", type=int, default=1)
    args = parser.parse_args()
    if not MODEL_PATH.exists():
        parser.error("Eğitilmiş model yok. Önce python src/train_production_model.py çalıştırın.")
    bundle = joblib.load(MODEL_PATH)
    row = pd.DataFrame([{
        "Planned_Quantity": args.planned_quantity,
        "Standard_Production_Cost": args.standard_cost,
        "Unit_Price": args.unit_price,
        "Production_Month": args.month,
        "Product_ID": args.product_id,
        "Product_Category": args.product_category,
        "Shift": args.shift,
        "Production_Line": args.production_line,
    }])[bundle["feature_columns"]]
    prediction = float(bundle["model"].predict(row)[0])
    print({"predicted_produced_quantity": round(max(0.0, prediction), 2), "model_context": "fan/heater manufacturing prototype; not validated for sausage production"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
