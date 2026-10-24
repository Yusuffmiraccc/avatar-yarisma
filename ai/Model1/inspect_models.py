from pathlib import Path
import joblib

root = Path(__file__).resolve().parent

for filename in ["ekp_model.joblib", "yield_model.joblib"]:
    path = root / "models" / filename
    obj = joblib.load(path)

    print(f"\n{'=' * 55}")
    print(filename)

    if isinstance(obj, dict):
        print("Model paketindeki anahtarlar:", list(obj.keys()))
        model = obj.get("model", obj.get("pipeline"))
        features = obj.get("feature_columns", obj.get("features"))
        print("Kayıtlı özellikler:", features)
    else:
        model = obj

    print("Model sınıfı:", type(model).__name__)

    if hasattr(model, "get_params"):
        print("Pipeline adımları:")
        for name, step in getattr(model, "steps", []):
            print(f"  {name}: {type(step).__name__}")
        if not getattr(model, "steps", None):
            print("  Pipeline değil; parametreler:")
            print(model.get_params(deep=False))
