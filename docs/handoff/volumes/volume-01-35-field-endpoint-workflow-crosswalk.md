# Cilt 1.35 — Alan, Endpoint ve İş Akışı Eşleştirme Denetimi

**Tarih:** 22 Ekim 2026  
**Durum:** Statik doküman denetimi tamamlandı; kapsamlı birebir eşleştirmede eksikler bulundu. Cilt 1 kapanmadı.  
**Girdi belgeleri:** Cilt 1.2 ERD, 1.3 API sözleşmeleri, 1.4 DTO/contract testleri, 1.5 iş akışları, 1.9 endpoint izinleri, 1.19 workflow registry, 1.21 error/idempotency registry, 1.24 acceptance testleri, 1.34 normatif revizyon.  
**Yöntem sınırı:** Markdown dosyaları incelendi. ORM metadata, gerçek MySQL şeması, üretilmiş OpenAPI, çalışan API veya test komutları çalıştırılmadı.

## 1. Sonuç özeti

- Workflow registry içinde WF-01–WF-10 kimlikleri bulunuyor; bu, her iş akışının tüm durum/geçiş/yan etki alanlarının birebir doğrulandığı anlamına gelmez.
- API sözleşmesi ve izin dokümanlarında 48'er benzersiz HTTP method/path imzası statik olarak bulundu. Sayıların eşitliği, setlerin eşit olduğu veya her endpoint için doğru izin/test bulunduğu anlamına gelmez.
- ERD belgesinde tablo ve alan adları kod biçiminde geçiyor; bu token'ları regex ile saymak tablo envanteri olarak güvenilir değildir. Bu nedenle Cilt 1.35 tam tablo/alan eşleştirmesini `NOT_COMPLETE` olarak kaydeder.
- Cilt 1.34'te güncellenen auth/health kuralları bazı tarihsel bölümlerde hâlâ eski ifadelerle birlikte bulunuyor. Tarihsel kayıtlar açıkça superseded olarak etiketlenmeli veya aktif sözleşme bölümlerinden kaldırılmalı.
- Cilt 1 henüz uygulamaya hazır kapalı sözleşme durumunda değildir.

## 2. Endpoint envanteri ve eşleştirme kuralı

Kaynaklar:
- API path kaynağı: `volume-01-3-api-contracts.md`
- Yetki matrisi: `volume-01-9-endpoint-permissions-security-decisions.md`
- DTO/OpenAPI/contract testleri: `volume-01-4-openapi-dto-contract-tests.md`
- Error/idempotency: `volume-01-21-error-idempotency-response-registry.md`
- Kabul testleri: `volume-01-24-end-to-end-acceptance-tests-llm-handoff.md`

Her endpoint için aşağıdaki sütunlar dolu olmadan `PASS` verilmez:
1. Method + path (tek canonical imza)
2. Authentication (anonymous/authenticated)
3. Permission key + role/scope
4. Request DTO/schema (veya `none`)
5. Response DTO/status code
6. Error codes (validation, not found, conflict, forbidden, unauthenticated, dependency failure)
7. Transaction boundary + audit side effect
8. Idempotency strategy (`Idempotency-Key`, deterministic state conflict, or not applicable)
9. Acceptance test ID(s), including denial and failure paths
10. API↔ORM/ERD field mapping

### Durum etiketleri
- `PASS`: belge kanıtı ile tüm alanlar mevcut ve uyumlu.
- `CONFLICT`: iki aktif normatif kaynak çelişiyor.
- `MISSING`: gereken alan/sözleşme/test yok.
- `VERIFY`: belge var ama fiziksel/çalışma zamanı doğrulaması gerekir.
- `NOT_RUNTIME_VERIFIED`: statik metin dışı kanıt gerektirir.
- `NOT_COMPLETE`: bu denetim turunda tüm kayıtlar satır satır çıkarılmadı.

## 3. Şu anki doğrulanabilir durum

| Alan | Gözlenen durum | Sonuç |
|---|---|---|
| Workflow kimlikleri | WF-01–WF-10 hem workflow tanımında hem registry'de geçiyor | `VERIFY` — ID varlığı kanıtlı; transition/side-effect parity tamam değil |
| API path imza sayısı | API belgesinde 48 benzersiz imza | `NOT_COMPLETE` — permission/test/DTO setleriyle tam karşılaştırma yapılmadı |
| Permission path imza sayısı | Permission belgesinde 48 benzersiz imza | `NOT_COMPLETE` — eşit sayı set eşitliği değildir |
| ERD tablo/alan listesi | Markdown'da backtick identifier'ları var | `NOT_COMPLETE` — regex sayımı güvenilir tablo envanteri değil |
| DTO/OpenAPI | Örnek payload ve test notları mevcut | `VERIFY` — generated OpenAPI ve Pydantic/DTO gerçek kodu yok/çalıştırılmadı |
| Cilt 1.34 auth/health | Normatif güncelleme eklendi | `CONFLICT/VERIFY` — bazı tarihsel metinlerde eski kurallar kalıyor |
| Idempotency | Registry mevcut | `VERIFY` — endpoint kapsamı ve persistence/response replay tam eşleştirilmedi |
| Audit transaction | Onaylı kural var | `VERIFY` — WF-01–WF-10 başına transaction/test kanıtı eksik |
| Migration/DB | Bu turda oluşturulmadı/değiştirilmedi | `NOT_STARTED_BY_DESIGN` |

## 4. Alan eşleştirmesi — zorunlu kritik alanlar

Aşağıdaki tablo, alanların onaylı kararla uyumlu olup olmadığını incelemek için başlangıç crosswalk'ıdır. `VERIFY` fiziksel alanın var olmadığını değil, yalnızca belgelerden tam kanıtlanmadığını ifade eder.

| Alan / kavram | Kanonik anlam | Kaynak belge | Durum | Gerekli kanıt |
|---|---|---|---|---|
| `products.requires_expiry_date` | Ürün kartı policy; true ise yeni lotta expiry zorunlu | Cilt 1.31/1.32/1.34 | `VERIFY` | ERD tablo tanımı + ORM field + DTO validation |
| `lots.expiry_date` | Uygun ürünlerde zorunlu, aksi halde NULL olabilir | Cilt 1.2 + Cilt 1.34 | `VERIFY` | nullable constraint ve create-lot testleri |
| `butchering_waste_records` | Ayrı fire tablosu; satılabilir output değildir | Cilt 1.2/1.17/1.34 | `VERIFY` | Tam kolon/FK/index/constraint listesi |
| `butchering_waste_records.reason_code` | Kontrollü sözlük; OTHER açıklama gerektirir | Cilt 1.31/1.32/1.34 | `VERIFY` | DB enum/check + DTO enum + validation test |
| `butchering_waste_records.allocated_cost` | BY_WEIGHT pay alır; BY_VALUE sıfır | Cilt 1.31/1.32/1.34 | `VERIFY` | Decimal field, calculation service, allocation tests |
| `butchering_outputs.allocated_cost` | Backend hesaplar; client değerine güvenilmez | Cilt 1.17/1.34 | `VERIFY` | request DTO'da yazılabilir olmadığının kanıtı |
| Weight canonical unit | kg; g/kg giriş dönüşümü kg'a | Cilt 1.31/1.32/1.34 | `VERIFY` | DTO unit semantics + conversion tests |
| Weight tolerance | default 0 kg; sessiz variance yok | Cilt 1.31/1.32/1.34 | `VERIFY` | config/field + authorized variance workflow |
| Refresh token/session | access 15m, refresh 7d rotation, hash/session/revoke/reuse | Cilt 1.31/1.32/1.34 | `VERIFY` | ORM model + endpoint schema + lifecycle tests |
| Health paths | `/health/live`, `/health/ready`, outside `/api/v1` | Cilt 1.31/1.32/1.34 | `CONFLICT/VERIFY` | active API/permission registry and generated OpenAPI |
| Error envelope | `error.code`, `error.message`, optional details, request_id | Cilt 1.21/1.31/1.34 | `VERIFY` | all error response schemas + tests |
| Idempotency key | same key/body replays original result; same key/different body 409 | Cilt 1.21/1.31/1.34 | `VERIFY` | DB uniqueness, canonical body hash, response persistence tests |

## 5. WF-01–WF-10 crosswalk

WF IDs are present in the source documents. The full state/transition/side-effect parity must be checked before a workflow is marked PASS.

| Workflow | Required comparison | Current status |
|---|---|---|
| WF-01 | Cilt 1.5 definition ↔ Cilt 1.19 registry ↔ API endpoint ↔ acceptance tests | `VERIFY` |
| WF-02 | Same comparison | `VERIFY` |
| WF-03 | Dispatch, lot stock ownership, movement and traceability links included | `VERIFY` |
| WF-04 | Same comparison | `VERIFY` |
| WF-05 | Same comparison | `VERIFY` |
| WF-06 | Same comparison | `VERIFY` |
| WF-07 | Same comparison | `VERIFY` |
| WF-08 | Same comparison | `VERIFY` |
| WF-09 | Same comparison | `VERIFY` |
| WF-10 | Same comparison | `VERIFY` |

Per workflow, Cilt 1.36 must extract the exact canonical name, allowed source states, target states, actor permission, transaction, stock movements, genealogy writes, audit event, idempotency policy, and test IDs. Do not infer workflow purpose from ID alone.

## 6. Security/permission coverage

Cilt 1.9 is the canonical endpoint permission matrix by approved SEC-08. The next pass must compare its exact `(method, path)` set with Cilt 1.3 and enumerate:
- API endpoint without permission row → `MISSING`.
- Permission row without API endpoint → `CONFLICT` or explicitly documented infra endpoint.
- Duplicate method/path with differing auth or roles → `CONFLICT`.
- No denial test ID for protected endpoint → `MISSING`.
- `/health/live` and `/health/ready` must be anonymous, outside `/api/v1`, and return only minimal health status.
- A permission matrix row must not imply authorization for second-tier distribution data that is not recorded.

## 7. Idempotency, audit and transaction crosswalk

Cilt 1.36 must produce one row per mutation endpoint with:
- `idempotency_policy`: `REQUIRED`, `STATE_CONFLICT_ONLY`, or `NOT_APPLICABLE`.
- `transaction_scope`: tables mutated together.
- `audit_event`: event written in same transaction.
- `rollback_case`: failure injection/test demonstrating rollback.
- `retry_test_id`: replay same request and conflicting body.
- `stock_effect_count`: ensure one logical request cannot duplicate stock movement.

Do not globally mark all POST endpoints idempotent without checking business semantics. User-approved rule requires sales and retry-risky critical POST endpoints to be safe on retry.

## 8. Current blocking issues

1. Full ERD table/column inventory is not normalized into a field-level manifest.
2. API↔permission set equality and per-endpoint DTO/test completeness are not proven.
3. WF-01–WF-10 transitions and side effects are not yet checked row-by-row against Cilt 1.19.
4. Cilt 1.34 current contract overrides coexist with historical stale statements in some docs.
5. Runtime ORM/MySQL/OpenAPI/test verification is not performed.
6. Therefore Cilt 1 closure is not justified.

## 9. Next concrete deliverable

Cilt 1.36 should be a normalized machine-readable (CSV/JSON) field and endpoint manifest generated from manually verified source definitions, plus a discrepancy ledger. It must not generate or execute migrations. Migration permission remains separately gated.
