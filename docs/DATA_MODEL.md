# Veri Modeli

Bu belge `backend/app/models` ORM metadata'sından üretilir (`python -m scripts.gen_docs`). İş kuralları için `SOZLESME.md`.

Toplam tablo: **38**

## `anomaly_alerts`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `alert_type` | VARCHAR(40) | hayır |  |
| `severity` | VARCHAR(12) | hayır |  |
| `entity_type` | VARCHAR(80) | hayır |  |
| `entity_id` | BIGINT | hayır |  |
| `message` | VARCHAR(500) | hayır |  |
| `details` | JSON | evet |  |
| `acknowledged_at` | DATETIME | evet |  |
| `created_at` | DATETIME | hayır |  |

## `audit_events`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `actor_user_id` | BIGINT | evet | FK → users.id |
| `action` | VARCHAR(80) | hayır |  |
| `entity_type` | VARCHAR(80) | hayır |  |
| `entity_id` | BIGINT | hayır |  |
| `occurred_at` | DATETIME | hayır |  |
| `request_id` | VARCHAR(80) | evet |  |
| `details` | JSON | evet |  |

Kısıtlar/indeksler: `INDEX ix_audit_events_entity_type (entity_type)`

## `butchering_inputs`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `butchering_order_id` | BIGINT | hayır | FK → butchering_orders.id |
| `lot_id` | BIGINT | hayır | FK → lots.id |
| `product_id` | BIGINT | hayır | FK → products.id |
| `quantity` | NUMERIC(19, 6) | hayır |  |
| `unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `cost_snapshot` | NUMERIC(19, 4) | hayır |  |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `CHECK quantity > 0`; `INDEX ix_butchering_inputs_butchering_order_id (butchering_order_id)`; `INDEX ix_butchering_inputs_lot_id (lot_id)`

## `butchering_orders`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `order_code` | VARCHAR(80) | hayır | UNIQUE |
| `status` | VARCHAR(24) | hayır |  |
| `animal_type` | VARCHAR(40) | hayır |  |
| `input_weight` | NUMERIC(19, 6) | hayır |  |
| `input_unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `total_purchase_cost` | NUMERIC(19, 4) | hayır |  |
| `declared_unit_price` | NUMERIC(19, 4) | evet |  |
| `currency_code` | VARCHAR(3) | hayır |  |
| `allocation_method` | VARCHAR(24) | hayır |  |
| `weight_difference` | NUMERIC(19, 6) | evet |  |
| `started_at` | DATETIME | evet |  |
| `completed_at` | DATETIME | evet |  |
| `notes` | VARCHAR(1000) | evet |  |
| `is_demo` | BOOLEAN | hayır |  |
| `reversed_at` | DATETIME | evet |  |
| `reversed_by` | BIGINT | evet | FK → users.id |
| `reversal_reason` | VARCHAR(500) | evet |  |
| `created_at` | DATETIME | hayır |  |
| `created_by` | BIGINT | evet | FK → users.id |

Kısıtlar/indeksler: `CHECK total_purchase_cost >= 0`; `CHECK input_weight > 0`

## `butchering_outputs`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `butchering_order_id` | BIGINT | hayır | FK → butchering_orders.id |
| `product_id` | BIGINT | hayır | FK → products.id |
| `lot_id` | BIGINT | hayır | FK → lots.id |
| `output_type` | VARCHAR(24) | hayır |  |
| `actual_weight` | NUMERIC(19, 6) | hayır |  |
| `unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `expected_weight` | NUMERIC(19, 6) | evet |  |
| `allocation_weight` | NUMERIC(19, 6) | evet |  |
| `allocation_value` | NUMERIC(19, 4) | evet |  |
| `allocated_cost` | NUMERIC(19, 4) | hayır |  |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `CHECK actual_weight >= 0`; `CHECK allocated_cost >= 0`; `INDEX ix_butchering_outputs_butchering_order_id (butchering_order_id)`; `INDEX ix_butchering_outputs_lot_id (lot_id)`

## `butchering_recipe_lines`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `animal_type` | VARCHAR(40) | hayır |  |
| `product_id` | BIGINT | hayır | FK → products.id |
| `output_type` | VARCHAR(24) | hayır |  |
| `expected_ratio` | NUMERIC(19, 6) | hayır |  |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `CHECK expected_ratio >= 0 AND expected_ratio <= 1`; `INDEX ix_butchering_recipe_lines_animal_type (animal_type)`

## `butchering_waste_records`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `butchering_order_id` | BIGINT | hayır | FK → butchering_orders.id |
| `input_lot_id` | BIGINT | hayır | FK → lots.id |
| `actual_weight` | NUMERIC(19, 6) | hayır |  |
| `unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `reason_code` | VARCHAR(40) | hayır |  |
| `notes` | VARCHAR(1000) | evet |  |
| `allocated_cost` | NUMERIC(19, 4) | hayır |  |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `CHECK allocated_cost >= 0`; `CHECK actual_weight >= 0`; `INDEX ix_butchering_waste_records_butchering_order_id (butchering_order_id)`

## `customers`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `code` | VARCHAR(64) | hayır | UNIQUE |
| `name` | VARCHAR(160) | hayır |  |
| `customer_type` | VARCHAR(32) | hayır |  |
| `phone` | VARCHAR(40) | evet |  |
| `email` | VARCHAR(254) | evet |  |
| `is_active` | BOOLEAN | hayır |  |
| `created_at` | DATETIME | hayır |  |
| `updated_at` | DATETIME | evet |  |

## `document_extractions`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `doc_type` | VARCHAR(24) | hayır |  |
| `source_name` | VARCHAR(200) | evet |  |
| `raw_text` | TEXT | hayır |  |
| `proposed` | JSON | hayır |  |
| `status` | VARCHAR(24) | hayır |  |
| `reviewed_by` | BIGINT | evet | FK → users.id |
| `reviewed_at` | DATETIME | evet |  |
| `review_note` | VARCHAR(500) | evet |  |
| `resulting_lot_ids` | JSON | evet |  |
| `created_by` | BIGINT | evet | FK → users.id |
| `created_at` | DATETIME | hayır |  |

## `idempotency_records`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `scope_key` | VARCHAR(160) | hayır |  |
| `idempotency_key` | VARCHAR(128) | hayır |  |
| `request_hash` | VARCHAR(64) | hayır |  |
| `response_status` | SMALLINT | hayır |  |
| `response_body` | JSON | hayır |  |
| `created_at` | DATETIME | hayır |  |
| `expires_at` | DATETIME | evet |  |

Kısıtlar/indeksler: `UNIQUE (scope_key, idempotency_key)`

## `inventory_balances`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `lot_id` | BIGINT | hayır | PK, FK → lots.id |
| `on_hand_quantity` | NUMERIC(19, 6) | hayır |  |
| `reserved_quantity` | NUMERIC(19, 6) | hayır |  |
| `updated_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `CHECK on_hand_quantity >= 0`; `CHECK reserved_quantity >= 0`

## `lot_blocks`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `lot_id` | BIGINT | hayır | FK → lots.id |
| `reason_code` | VARCHAR(40) | hayır |  |
| `reason_text` | VARCHAR(500) | evet |  |
| `source_type` | VARCHAR(32) | hayır |  |
| `source_id` | BIGINT | hayır |  |
| `blocked_at` | DATETIME | hayır |  |
| `blocked_by` | BIGINT | evet | FK → users.id |
| `unblocked_at` | DATETIME | evet |  |
| `unblocked_by` | BIGINT | evet | FK → users.id |
| `unblock_reason` | VARCHAR(500) | evet |  |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `INDEX ix_lot_blocks_active (lot_id, unblocked_at)`

## `lot_genealogy_edges`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `source_lot_id` | BIGINT | hayır | FK → lots.id |
| `target_lot_id` | BIGINT | hayır | FK → lots.id |
| `process_type` | VARCHAR(24) | hayır |  |
| `process_id` | BIGINT | hayır |  |
| `source_quantity` | NUMERIC(19, 6) | hayır |  |
| `source_unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `target_quantity` | NUMERIC(19, 6) | hayır |  |
| `target_unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `UNIQUE (source_lot_id, target_lot_id, process_type, process_id)`; `CHECK source_quantity >= 0 AND target_quantity >= 0`; `CHECK source_lot_id <> target_lot_id`; `INDEX ix_lot_genealogy_edges_target_lot_id (target_lot_id)`; `INDEX ix_genealogy_process (process_type, process_id)`; `INDEX ix_lot_genealogy_edges_source_lot_id (source_lot_id)`

## `lots`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `lot_code` | VARCHAR(80) | hayır | UNIQUE |
| `product_id` | BIGINT | hayır | FK → products.id |
| `supplier_id` | BIGINT | evet | FK → suppliers.id |
| `received_at` | DATETIME | evet |  |
| `expiry_date` | DATE | evet |  |
| `initial_quantity` | NUMERIC(19, 6) | hayır |  |
| `unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `lot_origin_type` | VARCHAR(24) | hayır |  |
| `status` | VARCHAR(24) | hayır |  |
| `unit_cost` | NUMERIC(19, 4) | evet |  |
| `location_code` | VARCHAR(40) | hayır |  |
| `is_demo` | BOOLEAN | hayır |  |
| `created_at` | DATETIME | hayır |  |
| `created_by` | BIGINT | evet | FK → users.id |

Kısıtlar/indeksler: `CHECK initial_quantity >= 0`

## `ml_predictions`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `prediction_type` | VARCHAR(40) | hayır |  |
| `model_version` | VARCHAR(80) | hayır |  |
| `status` | VARCHAR(16) | hayır |  |
| `input_reference_type` | VARCHAR(40) | evet |  |
| `input_reference_id` | BIGINT | evet |  |
| `input_summary` | JSON | evet |  |
| `predicted_value` | NUMERIC(19, 6) | evet |  |
| `predicted_cost` | NUMERIC(19, 4) | evet |  |
| `baseline_value` | NUMERIC(19, 6) | evet |  |
| `baseline_cost` | NUMERIC(19, 4) | evet |  |
| `actual_value` | NUMERIC(19, 6) | evet |  |
| `actual_cost` | NUMERIC(19, 4) | evet |  |
| `metric_name` | VARCHAR(40) | evet |  |
| `error_value` | NUMERIC(19, 6) | evet |  |
| `detail` | JSON | evet |  |
| `limitations_note` | VARCHAR(1000) | evet |  |
| `created_at` | DATETIME | hayır |  |
| `created_by` | BIGINT | evet | FK → users.id |

## `product_prices`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `product_id` | BIGINT | hayır | FK → products.id |
| `price_type` | VARCHAR(24) | hayır |  |
| `amount` | NUMERIC(19, 4) | hayır |  |
| `currency_code` | VARCHAR(3) | hayır |  |
| `unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `valid_from` | DATETIME | hayır |  |
| `valid_to` | DATETIME | evet |  |
| `created_at` | DATETIME | hayır |  |
| `created_by` | BIGINT | evet | FK → users.id |

Kısıtlar/indeksler: `CHECK amount >= 0`; `INDEX ix_product_prices_lookup (product_id, price_type, valid_from)`

## `production_inputs`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `production_order_id` | BIGINT | hayır | FK → production_orders.id |
| `product_id` | BIGINT | hayır | FK → products.id |
| `lot_id` | BIGINT | hayır | FK → lots.id |
| `quantity` | NUMERIC(19, 6) | hayır |  |
| `unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `unit_cost` | NUMERIC(19, 4) | hayır |  |
| `total_cost` | NUMERIC(19, 4) | hayır |  |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `CHECK unit_cost >= 0 AND total_cost >= 0`; `CHECK quantity > 0`; `INDEX ix_production_inputs_production_order_id (production_order_id)`; `INDEX ix_production_inputs_lot_id (lot_id)`

## `production_orders`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `order_code` | VARCHAR(80) | hayır | UNIQUE |
| `production_type` | VARCHAR(32) | hayır |  |
| `status` | VARCHAR(24) | hayır |  |
| `planned_quantity` | NUMERIC(19, 6) | evet |  |
| `planned_unit_code` | VARCHAR(16) | evet | FK → units.code |
| `started_at` | DATETIME | evet |  |
| `completed_at` | DATETIME | evet |  |
| `supplier_id` | BIGINT | evet | FK → suppliers.id |
| `total_input_cost` | NUMERIC(19, 4) | evet |  |
| `total_service_cost` | NUMERIC(19, 4) | evet |  |
| `total_cost` | NUMERIC(19, 4) | evet |  |
| `actual_output_quantity` | NUMERIC(19, 6) | evet |  |
| `unit_cost_ekp` | NUMERIC(19, 4) | evet |  |
| `notes` | VARCHAR(1000) | evet |  |
| `is_demo` | BOOLEAN | hayır |  |
| `reversed_at` | DATETIME | evet |  |
| `reversed_by` | BIGINT | evet | FK → users.id |
| `reversal_reason` | VARCHAR(500) | evet |  |
| `created_at` | DATETIME | hayır |  |
| `created_by` | BIGINT | evet | FK → users.id |
| `updated_at` | DATETIME | evet |  |

## `production_outputs`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `production_order_id` | BIGINT | hayır | FK → production_orders.id |
| `product_id` | BIGINT | hayır | FK → products.id |
| `lot_id` | BIGINT | hayır | FK → lots.id |
| `quantity` | NUMERIC(19, 6) | hayır |  |
| `unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `unit_cost` | NUMERIC(19, 4) | evet |  |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `CHECK quantity > 0`; `INDEX ix_production_outputs_production_order_id (production_order_id)`; `INDEX ix_production_outputs_lot_id (lot_id)`

## `production_service_costs`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `production_order_id` | BIGINT | hayır | FK → production_orders.id |
| `supplier_id` | BIGINT | evet | FK → suppliers.id |
| `description` | VARCHAR(200) | hayır |  |
| `quantity` | NUMERIC(19, 6) | evet |  |
| `unit_price` | NUMERIC(19, 4) | evet |  |
| `amount` | NUMERIC(19, 4) | hayır |  |
| `currency_code` | VARCHAR(3) | hayır |  |
| `occurred_at` | DATETIME | hayır |  |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `CHECK amount >= 0`; `INDEX ix_production_service_costs_production_order_id (production_order_id)`

## `products`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `code` | VARCHAR(64) | hayır | UNIQUE |
| `name` | VARCHAR(160) | hayır |  |
| `product_type` | VARCHAR(32) | hayır |  |
| `base_unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `is_lot_tracked` | BOOLEAN | hayır |  |
| `requires_expiry_date` | BOOLEAN | hayır |  |
| `is_active` | BOOLEAN | hayır |  |
| `created_at` | DATETIME | hayır |  |
| `updated_at` | DATETIME | evet |  |

## `recall_customer_impacts`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `recall_id` | BIGINT | hayır | FK → recalls.id |
| `customer_id` | BIGINT | hayır | FK → customers.id |
| `lot_id` | BIGINT | hayır | FK → lots.id |
| `shipment_id` | BIGINT | evet | FK → shipments.id |
| `quantity` | NUMERIC(19, 6) | hayır |  |
| `unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `contact_status` | VARCHAR(24) | hayır |  |
| `contacted_at` | DATETIME | evet |  |
| `notes` | VARCHAR(1000) | evet |  |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `CHECK quantity > 0`; `INDEX ix_recall_customer_impacts_recall_id (recall_id)`

## `recall_lots`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `recall_id` | BIGINT | hayır | FK → recalls.id |
| `lot_id` | BIGINT | hayır | FK → lots.id |
| `role` | VARCHAR(24) | hayır |  |
| `blocked_at` | DATETIME | evet |  |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `UNIQUE (recall_id, lot_id)`; `INDEX ix_recall_lots_lot_id (lot_id)`

## `recalls`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `recall_code` | VARCHAR(80) | hayır | UNIQUE |
| `status` | VARCHAR(24) | hayır |  |
| `reason_code` | VARCHAR(40) | hayır |  |
| `reason_text` | VARCHAR(1000) | evet |  |
| `started_at` | DATETIME | evet |  |
| `closed_at` | DATETIME | evet |  |
| `created_at` | DATETIME | hayır |  |
| `created_by` | BIGINT | evet | FK → users.id |
| `updated_at` | DATETIME | evet |  |

## `refresh_sessions`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `user_id` | BIGINT | hayır | FK → users.id |
| `family_id` | VARCHAR(36) | hayır |  |
| `token_hash` | VARCHAR(64) | hayır | UNIQUE |
| `expires_at` | DATETIME | hayır |  |
| `revoked_at` | DATETIME | evet |  |
| `replaced_by_id` | BIGINT | evet | FK → refresh_sessions.id |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `INDEX ix_refresh_sessions_family_id (family_id)`

## `rework_orders`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `order_code` | VARCHAR(80) | hayır | UNIQUE |
| `status` | VARCHAR(24) | hayır |  |
| `input_lot_id` | BIGINT | hayır | FK → lots.id |
| `input_quantity` | NUMERIC(19, 6) | hayır |  |
| `output_lot_id` | BIGINT | hayır | FK → lots.id |
| `output_quantity` | NUMERIC(19, 6) | hayır |  |
| `unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `extra_cost` | NUMERIC(19, 4) | hayır |  |
| `reason` | VARCHAR(500) | hayır |  |
| `created_at` | DATETIME | hayır |  |
| `created_by` | BIGINT | evet | FK → users.id |

Kısıtlar/indeksler: `CHECK input_quantity > 0 AND output_quantity > 0`

## `roles`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `code` | VARCHAR(40) | hayır | UNIQUE |
| `name` | VARCHAR(100) | hayır |  |

## `sale_lines`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `sale_id` | BIGINT | hayır | FK → sales.id |
| `line_number` | INTEGER | hayır |  |
| `product_id` | BIGINT | hayır | FK → products.id |
| `lot_id` | BIGINT | hayır | FK → lots.id |
| `quantity` | NUMERIC(19, 6) | hayır |  |
| `unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `unit_price` | NUMERIC(19, 4) | hayır |  |
| `stock_movement_id` | BIGINT | evet | FK → stock_movements.id |
| `line_total` | NUMERIC(19, 4) | hayır |  |
| `currency_code` | VARCHAR(3) | hayır |  |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `UNIQUE (sale_id, line_number)`; `CHECK quantity > 0`; `CHECK unit_price >= 0 AND line_total >= 0`; `INDEX ix_sale_lines_lot_id (lot_id)`

## `sales`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `sale_code` | VARCHAR(80) | hayır | UNIQUE |
| `customer_id` | BIGINT | evet | FK → customers.id |
| `shipment_id` | BIGINT | evet | FK → shipments.id |
| `status` | VARCHAR(24) | hayır |  |
| `sold_at` | DATETIME | hayır |  |
| `currency_code` | VARCHAR(3) | hayır |  |
| `total_amount` | NUMERIC(19, 4) | hayır |  |
| `created_at` | DATETIME | hayır |  |
| `created_by` | BIGINT | evet | FK → users.id |

Kısıtlar/indeksler: `CHECK total_amount >= 0`

## `shipment_lines`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `shipment_id` | BIGINT | hayır | FK → shipments.id |
| `line_number` | INTEGER | hayır |  |
| `product_id` | BIGINT | hayır | FK → products.id |
| `lot_id` | BIGINT | hayır | FK → lots.id |
| `quantity` | NUMERIC(19, 6) | hayır |  |
| `unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `stock_movement_id` | BIGINT | evet | FK → stock_movements.id |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `UNIQUE (shipment_id, line_number)`; `CHECK quantity > 0`; `INDEX ix_shipment_lines_lot_id (lot_id)`

## `shipments`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `shipment_code` | VARCHAR(80) | hayır | UNIQUE |
| `customer_id` | BIGINT | hayır | FK → customers.id |
| `status` | VARCHAR(24) | hayır |  |
| `shipped_at` | DATETIME | evet |  |
| `returned_at` | DATETIME | evet |  |
| `return_reason` | VARCHAR(500) | evet |  |
| `currency_code` | VARCHAR(3) | hayır |  |
| `notes` | VARCHAR(1000) | evet |  |
| `created_at` | DATETIME | hayır |  |
| `created_by` | BIGINT | evet | FK → users.id |

## `stock_movements`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `product_id` | BIGINT | hayır | FK → products.id |
| `lot_id` | BIGINT | hayır | FK → lots.id |
| `direction` | VARCHAR(3) | hayır |  |
| `movement_type` | VARCHAR(32) | hayır |  |
| `quantity` | NUMERIC(19, 6) | hayır |  |
| `unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `source_type` | VARCHAR(32) | hayır |  |
| `source_id` | BIGINT | hayır |  |
| `source_line_id` | BIGINT | evet |  |
| `location_code` | VARCHAR(40) | evet |  |
| `reverses_movement_id` | BIGINT | evet | FK → stock_movements.id |
| `idempotency_key` | VARCHAR(128) | evet |  |
| `occurred_at` | DATETIME | hayır |  |
| `created_at` | DATETIME | hayır |  |
| `created_by` | BIGINT | evet | FK → users.id |

Kısıtlar/indeksler: `CHECK direction IN ('IN','OUT')`; `CHECK quantity > 0`; `INDEX ix_stock_movements_lot_time (lot_id, occurred_at)`; `INDEX ix_stock_movements_product_time (product_id, occurred_at)`; `INDEX ix_stock_movements_idem (idempotency_key)`; `INDEX ix_stock_movements_source (source_type, source_id)`

## `suppliers`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `code` | VARCHAR(64) | hayır | UNIQUE |
| `name` | VARCHAR(160) | hayır |  |
| `supplier_type` | VARCHAR(32) | hayır |  |
| `phone` | VARCHAR(40) | evet |  |
| `email` | VARCHAR(254) | evet |  |
| `is_active` | BOOLEAN | hayır |  |
| `created_at` | DATETIME | hayır |  |
| `updated_at` | DATETIME | evet |  |

## `unit_conversions`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `from_unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `to_unit_code` | VARCHAR(16) | hayır | FK → units.code |
| `factor` | NUMERIC(19, 9) | hayır |  |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `UNIQUE (from_unit_code, to_unit_code)`; `CHECK factor > 0`

## `units`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `code` | VARCHAR(16) | hayır | PK |
| `name` | VARCHAR(80) | hayır |  |
| `dimension` | VARCHAR(16) | hayır |  |
| `is_active` | BOOLEAN | hayır |  |

## `user_roles`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `user_id` | BIGINT | hayır | PK, FK → users.id |
| `role_id` | BIGINT | hayır | PK, FK → roles.id |
| `created_at` | DATETIME | hayır |  |

## `users`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `email` | VARCHAR(254) | hayır | UNIQUE |
| `password_hash` | VARCHAR(255) | hayır |  |
| `display_name` | VARCHAR(120) | hayır |  |
| `is_active` | BOOLEAN | hayır |  |
| `token_version` | INTEGER | hayır |  |
| `created_at` | DATETIME | hayır |  |
| `updated_at` | DATETIME | evet |  |

## `weight_variance_records`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| `id` | BIGINT | hayır | PK |
| `butchering_order_id` | BIGINT | hayır | FK → butchering_orders.id |
| `variance_weight` | NUMERIC(19, 6) | hayır |  |
| `tolerance_weight` | NUMERIC(19, 6) | hayır |  |
| `reason_text` | VARCHAR(500) | hayır |  |
| `allocated_cost` | NUMERIC(19, 4) | hayır |  |
| `approved_by` | BIGINT | hayır | FK → users.id |
| `created_at` | DATETIME | hayır |  |

Kısıtlar/indeksler: `INDEX ix_weight_variance_records_butchering_order_id (butchering_order_id)`
