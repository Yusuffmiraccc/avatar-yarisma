# API Özeti

Üretim: `python -m scripts.gen_docs`. Ayrıntılı şema: `contract/openapi.json` ve `/api/v1/docs`.
Para ve miktarlar JSON **string**; zaman UTC ISO-8601 `Z`; hata zarfı `{error:{code,message,details}, request_id}`.
`Idempotency-Key` başlığı: `POST /sales`, `POST /shipments/{id}/dispatch` için zorunlu.

## Roller ve izinler

- **ADMIN** (32): `ai:read`, `ai:run`, `alerts:manage`, `alerts:read`, `audit:read`, `butchering:approve_variance`, `butchering:manage`, `butchering:read`, `catalog:manage`, `catalog:read`, `corrections:manage`, `costs:read`, `documents:manage`, `inventory:adjust`, `inventory:read`, `lots:read`, `lots:receive`, `lots:unblock`, `production:manage`, `production:read`, `recalls:manage`, `recalls:read`, `recalls:resolve`, `reports:read`, `sales:create`, `sales:override_price`, `sales:read`, `sales:void`, `shipments:manage`, `shipments:read`, `traceability:read`, `users:manage`
- **OPERATOR** (19): `ai:read`, `ai:run`, `alerts:read`, `butchering:manage`, `butchering:read`, `catalog:read`, `costs:read`, `documents:manage`, `inventory:adjust`, `inventory:read`, `lots:read`, `lots:receive`, `production:manage`, `production:read`, `recalls:read`, `reports:read`, `sales:read`, `shipments:read`, `traceability:read`
- **SALES** (8): `catalog:read`, `inventory:read`, `lots:read`, `reports:read`, `sales:create`, `sales:read`, `shipments:manage`, `shipments:read`
- **TRACEABILITY_MANAGER** (18): `ai:read`, `alerts:manage`, `alerts:read`, `audit:read`, `butchering:approve_variance`, `butchering:read`, `catalog:read`, `inventory:read`, `lots:read`, `lots:unblock`, `production:read`, `recalls:manage`, `recalls:read`, `recalls:resolve`, `reports:read`, `sales:read`, `shipments:read`, `traceability:read`
- **VIEWER** (12): `ai:read`, `alerts:read`, `butchering:read`, `catalog:read`, `inventory:read`, `lots:read`, `production:read`, `recalls:read`, `reports:read`, `sales:read`, `shipments:read`, `traceability:read`

## Endpoint'ler

| Yöntem | Yol | İzin |
|---|---|---|
| POST | `/api/v1/ai/butchering-output/predict` | ai:run |
| GET | `/api/v1/ai/models` | ai:read |
| POST | `/api/v1/ai/models/train` | ai:run |
| GET | `/api/v1/ai/predictions` | ai:read |
| GET | `/api/v1/ai/predictions/{prediction_id}` | ai:read |
| POST | `/api/v1/ai/production-yield/predict` | ai:run |
| POST | `/api/v1/ai/synthetic-data` | ai:run |
| GET | `/api/v1/alerts` | alerts:read |
| POST | `/api/v1/alerts/scan` | alerts:manage |
| POST | `/api/v1/alerts/{alert_id}/acknowledge` | alerts:manage |
| GET | `/api/v1/audit-events` | audit:read |
| POST | `/api/v1/auth/login` | herkese açık |
| POST | `/api/v1/auth/logout` | herkese açık |
| GET | `/api/v1/auth/me` | AUTHENTICATED |
| POST | `/api/v1/auth/refresh` | herkese açık |
| GET | `/api/v1/butchering-orders` | butchering:read |
| POST | `/api/v1/butchering-orders` | butchering:manage |
| GET | `/api/v1/butchering-orders/{order_id}` | butchering:read |
| POST | `/api/v1/butchering-orders/{order_id}/cancel` | butchering:manage |
| POST | `/api/v1/butchering-orders/{order_id}/complete` | butchering:manage |
| POST | `/api/v1/butchering-orders/{order_id}/inputs` | butchering:manage |
| POST | `/api/v1/butchering-orders/{order_id}/reverse` | corrections:manage |
| POST | `/api/v1/butchering-orders/{order_id}/start` | butchering:manage |
| POST | `/api/v1/butchering-orders/{order_id}/waste-records` | butchering:manage |
| GET | `/api/v1/butchering-recipes/{animal_type}` | butchering:read |
| PUT | `/api/v1/butchering-recipes/{animal_type}` | butchering:manage |
| GET | `/api/v1/customers` | catalog:read |
| POST | `/api/v1/customers` | catalog:manage |
| PATCH | `/api/v1/customers/{cid}` | catalog:manage |
| GET | `/api/v1/documents` | documents:manage |
| POST | `/api/v1/documents/extract` | documents:manage |
| POST | `/api/v1/documents/extract-file` | documents:manage |
| GET | `/api/v1/documents/{doc_id}` | documents:manage |
| POST | `/api/v1/documents/{doc_id}/approve` | documents:manage |
| POST | `/api/v1/documents/{doc_id}/reject` | documents:manage |
| POST | `/api/v1/inventory/adjustments` | inventory:adjust |
| GET | `/api/v1/inventory/movements` | inventory:read |
| POST | `/api/v1/inventory/transfers` | inventory:adjust |
| GET | `/api/v1/lots` | lots:read |
| GET | `/api/v1/lots/by-code/{lot_code}` | lots:read |
| POST | `/api/v1/lots/receipts` | lots:receive |
| GET | `/api/v1/lots/{lot_id}` | lots:read |
| POST | `/api/v1/lots/{lot_id}/unblock` | lots:unblock |
| GET | `/api/v1/production-orders` | production:read |
| POST | `/api/v1/production-orders` | production:manage |
| GET | `/api/v1/production-orders/{order_id}` | production:read |
| POST | `/api/v1/production-orders/{order_id}/cancel` | production:manage |
| POST | `/api/v1/production-orders/{order_id}/complete` | production:manage |
| POST | `/api/v1/production-orders/{order_id}/inputs` | production:manage |
| POST | `/api/v1/production-orders/{order_id}/reverse` | corrections:manage |
| POST | `/api/v1/production-orders/{order_id}/service-costs` | production:manage |
| POST | `/api/v1/production-orders/{order_id}/start` | production:manage |
| GET | `/api/v1/products` | catalog:read |
| POST | `/api/v1/products` | catalog:manage |
| GET | `/api/v1/products/{product_id}` | catalog:read |
| PATCH | `/api/v1/products/{product_id}` | catalog:manage |
| GET | `/api/v1/products/{product_id}/prices` | catalog:read |
| POST | `/api/v1/products/{product_id}/prices` | catalog:manage |
| GET | `/api/v1/recalls` | recalls:read |
| POST | `/api/v1/recalls` | recalls:manage |
| GET | `/api/v1/recalls/{recall_id}` | recalls:read |
| POST | `/api/v1/recalls/{recall_id}/activate` | recalls:manage |
| POST | `/api/v1/recalls/{recall_id}/cancel` | recalls:manage |
| PATCH | `/api/v1/recalls/{recall_id}/impacts/{impact_id}` | recalls:manage |
| POST | `/api/v1/recalls/{recall_id}/resolve` | recalls:resolve |
| GET | `/api/v1/recalls/{recall_id}/simulation` | recalls:read |
| GET | `/api/v1/reports/dashboard` | reports:read |
| GET | `/api/v1/reports/ledger-integrity` | reports:read |
| GET | `/api/v1/reports/production-costs` | reports:read |
| GET | `/api/v1/reports/recalls/{recall_id}/notification-list` | recalls:read |
| GET | `/api/v1/reports/stock-valuation` | reports:read |
| GET | `/api/v1/rework-orders` | production:read |
| POST | `/api/v1/rework-orders` | production:manage |
| GET | `/api/v1/sales` | sales:read |
| POST | `/api/v1/sales` | sales:create |
| GET | `/api/v1/sales/{sale_id}` | sales:read |
| POST | `/api/v1/sales/{sale_id}/void` | sales:void |
| GET | `/api/v1/shipments` | shipments:read |
| POST | `/api/v1/shipments` | shipments:manage |
| GET | `/api/v1/shipments/{shipment_id}` | shipments:read |
| POST | `/api/v1/shipments/{shipment_id}/cancel` | shipments:manage |
| POST | `/api/v1/shipments/{shipment_id}/dispatch` | shipments:manage |
| POST | `/api/v1/shipments/{shipment_id}/return` | shipments:manage |
| GET | `/api/v1/suppliers` | catalog:read |
| POST | `/api/v1/suppliers` | catalog:manage |
| PATCH | `/api/v1/suppliers/{sid}` | catalog:manage |
| GET | `/api/v1/sync/catalog` | catalog:read |
| GET | `/api/v1/traceability/lots/by-code/{lot_code}/backward` | traceability:read |
| GET | `/api/v1/traceability/lots/by-code/{lot_code}/forward` | traceability:read |
| GET | `/api/v1/traceability/lots/{lot_id}/backward` | traceability:read |
| GET | `/api/v1/traceability/lots/{lot_id}/forward` | traceability:read |
| GET | `/api/v1/traceability/lots/{lot_id}/graph` | traceability:read |
| GET | `/api/v1/units` | catalog:read |
| GET | `/api/v1/users` | users:manage |
| POST | `/api/v1/users` | users:manage |
| PATCH | `/api/v1/users/{user_id}` | users:manage |
| POST | `/api/v1/users/{user_id}/reset-password` | users:manage |
| GET | `/health/live` | herkese açık |
| GET | `/health/ready` | herkese açık |
