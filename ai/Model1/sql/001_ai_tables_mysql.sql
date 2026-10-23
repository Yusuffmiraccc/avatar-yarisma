-- AVATAR Model 1 AI tables for MySQL 8.0+ / InnoDB.
-- Run this migration in the central AVATAR database before starting the AI API.
-- Only completed, validated, actual production orders belong in ai_production_training_records.

CREATE TABLE IF NOT EXISTS ai_production_training_records (
    production_order_id VARCHAR(80) NOT NULL PRIMARY KEY,
    production_date DATE NOT NULL,
    recipe_variant VARCHAR(100) NOT NULL DEFAULT 'default',
    meat_kg DECIMAL(12,3) NOT NULL,
    spice_kg DECIMAL(12,3) NOT NULL DEFAULT 0,
    casing_kg DECIMAL(12,3) NOT NULL DEFAULT 0,
    package_weight_kg DECIMAL(10,3) NOT NULL DEFAULT 1.000,
    planned_material_cost_eur DECIMAL(14,4) NOT NULL DEFAULT 0,
    planned_service_cost_eur DECIMAL(14,4) NOT NULL DEFAULT 0,
    actual_package_count INT UNSIGNED NOT NULL,
    actual_material_cost_eur DECIMAL(14,4) NOT NULL DEFAULT 0,
    actual_service_cost_eur DECIMAL(14,4) NOT NULL DEFAULT 0,
    actual_ekp_eur DECIMAL(14,6) NOT NULL,
    production_status VARCHAR(20) NOT NULL DEFAULT 'completed',
    validation_status VARCHAR(20) NOT NULL DEFAULT 'validated',
    data_source VARCHAR(20) NOT NULL DEFAULT 'actual',
    recorded_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY ix_ai_training_recorded_at (recorded_at),
    KEY ix_ai_training_production_date (production_date),
    CONSTRAINT chk_ai_training_meat CHECK (meat_kg > 0),
    CONSTRAINT chk_ai_training_package_weight CHECK (package_weight_kg > 0),
    CONSTRAINT chk_ai_training_package_count CHECK (actual_package_count > 0),
    CONSTRAINT chk_ai_training_status CHECK (production_status = 'completed' AND validation_status = 'validated' AND data_source = 'actual')
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ai_production_predictions (
    prediction_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    production_order_id VARCHAR(80) NOT NULL,
    model_version VARCHAR(80) NOT NULL,
    input_snapshot JSON NOT NULL,
    predicted_output_quantity DECIMAL(14,4) NOT NULL,
    predicted_ekp_eur DECIMAL(14,6) NOT NULL,
    actual_package_count INT UNSIGNED NULL,
    actual_ekp_eur DECIMAL(14,6) NULL,
    quantity_error DECIMAL(14,4) NULL COMMENT 'Actual minus predicted packages',
    ekp_error_eur DECIMAL(14,6) NULL COMMENT 'Actual minus predicted EUR/package',
    predicted_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    actual_recorded_at DATETIME(6) NULL,
    KEY ix_ai_predictions_order (production_order_id),
    KEY ix_ai_predictions_model (model_version)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ai_model_registry (
    model_version VARCHAR(80) NOT NULL PRIMARY KEY,
    artifact_path VARCHAR(500) NOT NULL,
    algorithm VARCHAR(80) NOT NULL,
    trained_record_count INT UNSIGNED NOT NULL,
    trained_until DATE NOT NULL,
    metrics_json JSON NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    activated_at DATETIME(6) NULL,
    KEY ix_ai_model_active (is_active, activated_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ai_retraining_state (
    singleton_id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
    last_attempted_at DATETIME(6) NULL,
    last_successful_training_at DATETIME(6) NULL,
    total_records_at_last_success INT UNSIGNED NOT NULL DEFAULT 0,
    active_model_version VARCHAR(80) NULL,
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB;

INSERT INTO ai_retraining_state (singleton_id)
VALUES (1)
ON DUPLICATE KEY UPDATE singleton_id = VALUES(singleton_id);

CREATE TABLE IF NOT EXISTS ai_retraining_jobs (
    job_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    status ENUM('pending', 'running', 'promoted', 'rejected', 'failed') NOT NULL DEFAULT 'pending',
    trigger_reason VARCHAR(100) NOT NULL,
    records_total INT UNSIGNED NOT NULL,
    new_records_since_attempt INT UNSIGNED NOT NULL,
    model_version VARCHAR(80) NULL,
    metrics_json JSON NULL,
    error_message TEXT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    started_at DATETIME(6) NULL,
    finished_at DATETIME(6) NULL,
    KEY ix_ai_jobs_queue (status, job_id)
) ENGINE=InnoDB;
