# AVATAR — Doküman Dizini ve Kaynak Önceliği

## Kaynak önceliği

1. `LLM_HANDOFF.md`: kodlama LLM'ine çalışma talimatı.
2. `AVATAR_MASTER_BRIEF.md`: ürün kapsamı ve ana kararlar.
3. `BACKEND_DATABASE_ARCHITECTURE_CLOSURE.md`: en yeni backend/DB kararları ve 1.45 kapanışları.
4. İlgili alanın kanonik ciltleri (aşağıdaki tablo).
5. `manifests/` dosyaları: denetim, crosswalk ve envanter kanıtı; tek başına normatif karar değildir.
6. Revizyon logları/önceki ciltler: tarihçe; güncel kapanış kararıyla çelişirse güncel kapanış esas alınır.

## Göreve göre kaynaklar

| Görev | Önce açılacak kaynaklar | Amaç |
|---|---|---|
| Ürün kapsamı/teknoloji | `AVATAR_MASTER_BRIEF.md`, `volumes/volume-00-foundation.md` | Hedef, teknoloji ve kapsam |
| ORM/DB/ERD | `BACKEND_DATABASE_ARCHITECTURE_CLOSURE.md`, `volumes/volume-01-2-erd-and-data-schema.md`, `volumes/volume-01-22-full-erd-constraint-index-dto-crosswalk.md`, `volumes/volume-01-42-erd-schema-inventory-and-physical-schema-evidence.md`, `volumes/volume-01-43-markdown-schema-extraction-and-constraint-crosscheck.md` | Alanlar, ilişkiler, kısıtlar ve açık farklar |
| REST endpoint/DTO/OpenAPI | `volumes/volume-01-3-api-contracts.md`, `volumes/volume-01-4-openapi-dto-contract-tests.md`, `volumes/volume-01-35-field-endpoint-workflow-crosswalk.md` | İstek/yanıt sözleşmeleri |
| İş akışları ve durumlar | `BACKEND_DATABASE_ARCHITECTURE_CLOSURE.md`, `volumes/volume-01-5-workflows-state-machines.md`, `volumes/volume-01-19-canonical-workflow-ids-state-registry.md`, `volumes/volume-01-34-canonical-contract-revision.md` | Üretim, parçalama, dispatch, recall geçişleri |
| Servis katmanı ve geliştirme sırası | `volumes/volume-01-6-backend-implementation-plan.md`, `volumes/volume-01-30-volume-1-closure-and-llm-readability.md` | Modüler uygulama yaklaşımı |
| Migration/seed/constraint | `BACKEND_DATABASE_ARCHITECTURE_CLOSURE.md`, `volumes/volume-01-7-migration-constraints-seed-data.md` | Alembic, DB constraints, sentetik demo verisi; yalnız test DB |
| Auth/rol/izin | `volumes/volume-01-8-auth-roles-security.md`, `volumes/volume-01-9-endpoint-permissions-security-decisions.md`, `volumes/volume-01-20-auth-permissions-health-reconciliation.md`, `volumes/volume-01-26-auth-security-decision-workshop.md` | Token, roller, endpoint permissions |
| Hata zarfı/idempotency | `volumes/volume-01-21-error-idempotency-response-registry.md`, `decisions/DEC-001-data-api-contracts-proposal.md` | Error contract, retry/idempotency |
| Fire/expiry/ağırlık/maliyet | `volumes/volume-01-17-waste-expiry-cost-decisions.md`, `volumes/volume-01-23-expiry-waste-cost-weight-unit-decisions.md`, `BACKEND_DATABASE_ARCHITECTURE_CLOSURE.md` | Maliyet ve fire kuralları |
| Recall/traceability | `volumes/volume-01-5-workflows-state-machines.md`, `volumes/volume-01-14-wf03-dispatch-stock-ownership.md`, `volumes/volume-01-24-end-to-end-acceptance-tests-llm-handoff.md` | Lot genealogy, recall, shipment impact |
| E2E/acceptance tests | `volumes/volume-01-24-end-to-end-acceptance-tests-llm-handoff.md`, `ACCEPTANCE_CRITERIA.md` | Uçtan uca testler |
| Deployment/demo | `volumes/volume-01-28-competition-delivery-and-demo-deployment.md`, `volumes/volume-01-29-demo-deployment-architecture.md` | Demo dağıtımı ve sunum |

## Dosya grupları

- `backend/`: mevcut FastAPI başlangıç iskeleti; eksiksiz ürün değildir.
- `decisions/`: karar belgeleri/ADR.
- `volumes/`: ayrıntılı ciltler, sözleşmeler, denetimler ve revizyon kayıtları.
- `manifests/`: CSV/JSON envanter ve çapraz kontrol çıktıları.
- `LLM_HANDOFF.md`, `IMPLEMENTATION_PLAN.md`, `ACCEPTANCE_CRITERIA.md`, `KNOWN_GAPS.md`: kodlama için kısa ve doğrudan çalışma belgeleri.
