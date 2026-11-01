CREATE TABLE IF NOT EXISTS model_b_predictions (
    prediction_id TEXT PRIMARY KEY,
    model_version TEXT NOT NULL,
    data_version TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('measured', 'synthetic')),
    hayvan_turu TEXT NOT NULL CHECK (hayvan_turu IN ('kuzu', 'koyun', 'dana')),
    karkas_agirligi_kg REAL NOT NULL CHECK (karkas_agirligi_kg > 0),
    predicted_cuts_kg_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    is_experimental INTEGER NOT NULL DEFAULT 0 CHECK (is_experimental IN (0, 1))
);

CREATE TABLE IF NOT EXISTS model_b_actuals (
    prediction_id TEXT PRIMARY KEY REFERENCES model_b_predictions(prediction_id),
    actual_cuts_kg_json TEXT NOT NULL,
    actual_source_type TEXT NOT NULL CHECK (actual_source_type = 'measured'),
    measured_at_utc TEXT NOT NULL,
    recorded_at_utc TEXT NOT NULL
);
