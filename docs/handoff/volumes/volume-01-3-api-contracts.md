# Cilt 1.3 — REST API Endpoint Sözleşmeleri


> **Normatif güncelleme — 22 Ekim 2026 (Cilt 1.32):** Bu belgedeki daha eski ve çelişen taslak ifadeler için `volume-01-32-approved-decisions-and-cross-check.md` ile Cilt 1.31'in onay kaydı önceliklidir. Bu not doküman sözleşmesini günceller; migration veya veritabanı değişikliği izni değildir.

**Durum:** İlk bağlayıcı API sözleşmesi  
**Tarih:** 22 Ekim 2026  
**Bağlı belgeler:** Cilt 0, Cilt 1, Cilt 1.2, DEC-001, ADR-001  
**API standardı:** REST + JSON + OpenAPI, prefix `/api/v1`  
**Backend:** Python + FastAPI + Pydantic + SQLAlchemy 2.x + Alembic + PyMySQL  
**İstemciler:** Kotlin/Android ve React/TypeScript  
**Amaç:** Farklı LLM'lerin API uçlarını aynı istek/yanıt, yetki ve transaction kurallarıyla uygulamasını sağlamak.

> **Bağlayıcı kurallar:** JSON alan adları `snake_case`; enum değerleri `UPPER_SNAKE_CASE`; hassas para/miktar alanları JSON string; zaman anları UTC ISO 8601 (`Z`); tarih alanları `YYYY-MM-DD`. Backend, stok/maliyet/lot kurallarının otoritesidir. Android ve web paneli MySQL'e doğrudan bağlanmaz.

## 1. Ortak HTTP kuralları

### 1.1 Base path ve içerik türü

- Tüm iş endpoint'leri `/api/v1` altında bulunur.
- İstek ve yanıt gövdeleri JSON'dur; isteklerde `Content-Type: application/json`.
- Kimlik doğrulama gerektiren isteklerde `Authorization: Bearer <access_token>`.
- Liste endpoint'leri sayfalama parametreleri kullanır: `page` (varsayılan 1), `page_size` (varsayılan 20, üst sınır 100), isteğe bağlı `sort`, filtre parametreleri.
- Tarih aralıkları için `from` ve `to` parametreleri kullanılır; timestamp bekleyen endpoint'lerde UTC ISO 8601 gönderilir.
- Başarılı `POST` kaynak oluşturma için `201 Created`; başarılı okuma `200 OK`; işlem kuyruğu gerektirmeyen senkron komutlar `200 OK` veya kaynak oluşturuyorsa `201 Created`; gövdesiz başarılı silme/iptal olmayan işlemlerde gerekirse `204 No Content`.
- `PATCH` yalnızca belgelenmiş alanları değiştirir. Kritik işlem kayıtları hard delete ile silinmez.

### 1.2 Ortak liste yanıtı

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

`total` filtre uygulanmış toplam kayıt sayısıdır. `items` içindeki para ve miktarlar JSON string biçimindedir.

### 1.3 Ortak hata yanıtı

```json
{
  "error": {
    "code": "LOT_BLOCKED",
    "message": "The selected lot is blocked and cannot be sold.",
    "details": {
      "lot_code": "SUC-2026-045"
    },
    "request_id": "server-generated-request-id"
  }
}
```

`request_id` her yanıtta bulunması önerilen izleme kimliğidir; hata nesnesinde DEC-001'deki `requestId` alanının JSON snake_case karşılığı olarak `request_id` kullanılır. API hata sözleşmesinde alan adı tüm endpoint'lerde aynı olmalıdır.

### 1.4 Ortak hata kodları

| HTTP | `error.code` | Kullanım |
|---:|---|---|
| 400 | `VALIDATION_ERROR` | Alan veya iş isteği doğrulaması başarısız |
| 401 | `UNAUTHENTICATED` | Token eksik/geçersiz |
| 403 | `FORBIDDEN` | Kullanıcı rolü işlem için yetkisiz |
| 404 | `RESOURCE_NOT_FOUND` | Kaynak bulunamadı |
| 409 | `CONFLICT` | Durum/unique/işlem çakışması |
| 409 | `IDEMPOTENCY_KEY_REUSED` | Aynı anahtar farklı istek gövdesiyle gönderildi |
| 409 | `INSUFFICIENT_STOCK` | Kullanılabilir stok yetersiz |
| 409 | `LOT_BLOCKED` | Lot aktif blokaj altında |
| 409 | `INVALID_STATE_TRANSITION` | Kaynak mevcut durumdan hedef duruma geçirilemez |
| 422 | `BUSINESS_RULE_VIOLATION` | Yapısal olarak geçerli istek iş kuralını ihlal ediyor |
| 429 | `RATE_LIMITED` | İstek sınırı aşıldı (uygulanırsa) |
| 500 | `INTERNAL_ERROR` | Beklenmeyen hata; iç stack trace istemciye dönülmez |

FastAPI/Pydantic'in varsayılan doğrulama yanıtı doğrudan dışarı verilmemeli; ortak hata şekline dönüştürülmelidir.

## 2. Yetki modeli

Roller: `ADMIN`, `OPERATOR`, `SALES`, `TRACEABILITY_MANAGER`, `VIEWER`.

| İşlem grubu | ADMIN | OPERATOR | SALES | TRACEABILITY_MANAGER | VIEWER |
|---|---:|---:|---:|---:|---:|
| Katalogları okuma | ✓ | ✓ | ✓ | ✓ | ✓ |
| Katalog yönetimi | ✓ | — | — | — | — |
| Lot/stock görüntüleme | ✓ | ✓ | ✓ | ✓ | ✓ |
| Stok kabulü/giriş | ✓ | ✓ | — | — | — |
| Genel stok düzeltme/ters kayıt (`inventory:adjust`) | ✓ | — | — | — | — |
| Üretim ve dış hizmet emri | ✓ | ✓ | — | — | — |
| Parçalama emri | ✓ | ✓ | — | — | — |
| Satış oluşturma/geçmişi (ticari kayıt; stok hareketi üretmez) | ✓ | — | ✓ | — | Yetki verilmiş okuma |
| Sevkiyat oluşturma/dispatch (tek fiziksel stok OUT sahibi) | ✓ | — | ✓ | — | — |
| İleri/geriye izlenebilirlik | ✓ | ✓ | ✓ | ✓ | Yetki verilmiş okuma |
| Recall başlatma/kapatma | ✓ | — | — | ✓ | — |
| Kullanıcı/rol yönetimi | ✓ | — | — | — | — |
| AI tahmini çalıştırma/görüntüleme | ✓ | ✓ | — | ✓ | Yetki verilmiş okuma |

Bu matris başlangıç sözleşmesidir. Uygulama, her endpoint'te backend tarafında kontrol yapmalıdır; UI'da buton gizlemek yetkilendirme değildir. Her endpoint için rol tablosundaki izin açıkça yazılmıştır.

## 3. Kimlik doğrulama

### `POST /api/v1/auth/login`
**Yetki:** Public.  
**Amaç:** E-posta ve parolayla giriş.

İstek:
```json
{
  "email": "operator@example.test",
  "password": "demo-password"
}
```

Yanıt `200`:
```json
{
  "access_token": "opaque-or-jwt-token",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": 10,
    "email": "operator@example.test",
    "display_name": "Demo Operator",
    "roles": ["OPERATOR"]
  }
}
```

Not: Gerçek token/parola örneği değildir. Parolalar güvenli hash ile saklanır; loglara yazılmaz. Onaylı auth sözleşmesi: access token 15 dakika, refresh token 7 gün; refresh rotation zorunludur. Refresh token sunucuda yalnız hash/session kaydıyla ilişkilendirilir; logout refresh session'ını iptal eder. Refresh token reuse tespitinde token ailesi iptal edilir.

Normatif kaynak: Cilt 1.31 onay kaydı ve Cilt 1.32. Eski token örnekleri bu sözleşmeye göre revize edilmelidir.

### `GET /api/v1/auth/me`
**Yetki:** Giriş yapmış kullanıcı.  
**Yanıt `200`:** Giriş yapan kullanıcının `id`, `email`, `display_name`, `roles`, `is_active` alanları.

### `POST /api/v1/auth/logout`
**Yetki:** Giriş yapmış kullanıcı.  
**Yanıt `204`:** İstemci token'ı siler. Stateless JWT kullanılıyorsa sunucu tarafında token iptali ayrıca tasarlanmadıkça logout yalnızca istemci oturumunu kapatır; bu sınırlama dokümante edilmelidir.

## 4. Katalog endpoint'leri

### `GET /api/v1/products`
**Yetki:** Tüm roller.  
**Filtreler:** `product_type`, `is_active`, `search`, `page`, `page_size`.  
**Yanıt:** Ortak liste formatı; her item `id`, `code`, `name`, `product_type`, `base_unit_code`, `is_lot_tracked`, `is_active`.

### `POST /api/v1/products`
**Yetki:** `ADMIN`.  
İstek:
```json
{
  "code": "SUCUK-001",
  "name": "Sucuk 500 g",
  "product_type": "FINISHED_GOOD",
  "base_unit_code": "PACK",
  "is_lot_tracked": true
}
```
Yanıt `201`: Oluşturulan ürün. `code` benzersiz olmalıdır.

### `GET /api/v1/products/{product_id}`
**Yetki:** Tüm roller.  
**Yanıt:** Ürün detayı.

### `PATCH /api/v1/products/{product_id}`
**Yetki:** `ADMIN`.  
**Amaç:** Yalnızca belgelenmiş katalog alanlarını güncellemek; geçmiş işlemlerin snapshot maliyetlerini değiştirmez.

### `GET /api/v1/units`
**Yetki:** Tüm roller.  
**Yanıt:** Birim kodu, adı ve boyutu.

### `GET /api/v1/suppliers`
**Yetki:** `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`; diğer roller için gerekirse sadece güvenli okuma.  
**Yanıt:** Tedarikçi listesi.

### `POST /api/v1/suppliers`
**Yetki:** `ADMIN`.  
**Amaç:** Tedarikçi oluşturma.

### `GET /api/v1/customers`
**Yetki:** `ADMIN`, `OPERATOR`, `SALES`, `TRACEABILITY_MANAGER`.  
**Yanıt:** Müşteri/market listesi.

### `POST /api/v1/customers`
**Yetki:** `ADMIN`.  
**Amaç:** Müşteri/market oluşturma.

## 5. Lot ve stok endpoint'leri

### `GET /api/v1/lots`
**Yetki:** Tüm roller; hassas tedarikçi ayrıntıları rol bazlı azaltılabilir.  
**Filtreler:** `lot_code`, `product_id`, `product_code`, `status`, `expiry_before`, `blocked`, `page`, `page_size`.  
**Yanıt item alanları:** `id`, `lot_code`, `product_id`, `product_code`, `product_name`, `supplier_id`, `received_at`, `expiry_date`, `initial_quantity`, `unit_code`, `status`, `on_hand_quantity`, `reserved_quantity`, `available_quantity`, `is_blocked`.

### `GET /api/v1/lots/{lot_id}`
**Yetki:** Tüm roller.  
**Yanıt:** Lot ayrıntısı, bakiye ve aktif blokaj bilgisi.

### `GET /api/v1/lots/by-code/{lot_code}`
**Yetki:** Tüm roller.  
**Amaç:** İnsan tarafından bilinen lot koduyla lotu bulma.

### `GET /api/v1/inventory/balances`
**Yetki:** Tüm roller.  
**Filtreler:** `product_id`, `lot_id`, `blocked`, `page`, `page_size`.  
**Yanıt:** Lot bazında on-hand, reserved, available miktarı.

### `GET /api/v1/inventory/movements`
**Yetki:** `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`; `SALES` kendi satış hareketlerini görebilir.  
**Filtreler:** `lot_id`, `product_id`, `movement_type`, `source_type`, `source_id`, `from`, `to`, sayfalama.  
**Yanıt:** Stok hareketi geçmişi; hareketler değiştirilemez.

### `POST /api/v1/inventory/receipts`
**Yetki:** `ADMIN`, `OPERATOR`.  
**Amaç:** Satın alma/açılış stok kabulü.  
İstek:
```json
{
  "product_id": 100,
  "lot_code": "ET-2026-001",
  "supplier_id": 20,
  "quantity": "100.000000",
  "unit_code": "KG",
  "received_at": "2026-10-22T10:00:00Z",
  "expiry_date": "2026-11-10"
}
```
Yanıt `201`: Lot + IN/RECEIPT hareketi + bakiye kaydı. Lot oluşturma, hareket ve bakiye tek transaction'da yapılır. `Idempotency-Key` başlığı desteklenir.

### `POST /api/v1/inventory/adjustments`
**Yetki:** `ADMIN`.  
**Amaç:** Denetim gerektiren stok düzeltmesi; diğer roller `403 FORBIDDEN` alır.  
İstek:
```json
{
  "lot_id": 101,
  "direction": "OUT",
  "quantity": "1.000000",
  "unit_code": "KG",
  "reason_code": "COUNT_VARIANCE",
  "reason_text": "Physical count difference"
}
```
**Kural:** Düzeltme geçmiş hareketi değiştirmez; yeni ADJUSTMENT hareketi yazar. Her düzeltme audit event üretir. Negatif bakiye oluşamaz.

## 6. Üretim endpoint'leri

### `POST /api/v1/production-orders`
**Yetki:** `ADMIN`, `OPERATOR`.  
İstek:
```json
{
  "order_code": "URT-2026-045",
  "production_type": "OUTSOURCED",
  "planned_quantity": "85.000000",
  "planned_unit_code": "PACK",
  "supplier_id": 30,
  "notes": "Outsourced production batch"
}
```
Yanıt `201`: Taslak üretim emri.

### `GET /api/v1/production-orders`
**Yetki:** `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`; diğer roller için salt okuma politikası ayrıca uygulanabilir.  
**Filtreler:** `status`, `production_type`, `from`, `to`, `page`, `page_size`.

### `GET /api/v1/production-orders/{order_id}`
**Yetki:** `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`.  
**Yanıt:** Emir, girdiler, hizmet maliyetleri, çıktılar ve hesaplanan maliyet özeti.

### `POST /api/v1/production-orders/{order_id}/inputs`
**Yetki:** `ADMIN`, `OPERATOR`.  
İstek:
```json
{
  "product_id": 100,
  "lot_id": 101,
  "quantity": "100.000000",
  "unit_code": "KG",
  "unit_cost": "9.7000",
  "total_cost": "970.0000"
}
```
**Kural:** Taslak veya ilerleyen durumdaki emir için; lotun ürüne ait olduğu, stok ve birim uyumu doğrulanır. Girdi tüketimi emri tamamlanırken gerçekleşir; input satırı eklemek tek başına stoğu düşürmez.

### `POST /api/v1/production-orders/{order_id}/service-costs`
**Yetki:** `ADMIN`, `OPERATOR`.  
İstek:
```json
{
  "supplier_id": 30,
  "description": "External processing",
  "amount": "467.5000",
  "currency_code": "EUR",
  "occurred_at": "2026-10-22T10:00:00Z"
}
```

### `POST /api/v1/production-orders/{order_id}/outputs`
**Yetki:** `ADMIN`, `OPERATOR`.  
İstek:
```json
{
  "product_id": 200,
  "lot_code": "SUC-2026-045",
  "quantity": "85.000000",
  "unit_code": "PACK",
  "expiry_date": "2026-11-10"
}
```
**Kural:** Çıktı taslağı tamamlamadan önce kaydedilebilir. Çıktı lotu ve stok IN hareketi tamamlanma transaction'ında oluşturulur.

### `POST /api/v1/production-orders/{order_id}/complete`
**Yetki:** `ADMIN`, `OPERATOR`.  
Başlık: `Idempotency-Key: <unique-key>`.  
**Yanıt:** `200` tamamlanmış emir ve maliyet özeti.  
**Transaction:** Girdi lotları için yeterli stok, lot blokajı gereklilikleri, maliyet ve çıktı miktarları doğrulanır; input OUT hareketleri/bakiyeler, çıktı lotları/output IN hareketleri, genealogy edges, audit ve durum değişikliği tek transaction içinde yazılır. İkinci tamamlama çağrısı ikinci kez stok düşürmez.

### `POST /api/v1/production-orders/{order_id}/cancel`
**Yetki:** `ADMIN`.  
**Kural:** Tamamlanmış emir doğrudan iptal edilmez; gerekiyorsa ayrı ters/düzeltme akışı gerekir.

## 7. Parçalama endpoint'leri

### `POST /api/v1/butchering-orders`
**Yetki:** `ADMIN`, `OPERATOR`.  
İstek:
```json
{
  "order_code": "PAR-2026-012",
  "animal_type": "LAMB",
  "input_weight": "25.000000",
  "input_unit_code": "KG",
  "total_purchase_cost": "287.5000",
  "currency_code": "EUR",
  "allocation_method": "BY_WEIGHT"
}
```
Yanıt `201`: Taslak parçalama emri.

### `GET /api/v1/butchering-orders`
**Yetki:** `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`; filtreler `status`, `animal_type`, tarih aralığı ve sayfalama.

### `GET /api/v1/butchering-orders/{order_id}`
**Yetki:** `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`.  
**Yanıt:** Girdi, kesim/yan ürün/fire çıktıları, ağırlık dengesi ve maliyet dağıtımı.

### `POST /api/v1/butchering-orders/{order_id}/inputs`
**Yetki:** `ADMIN`, `OPERATOR`.  
İstek: `lot_id`, `product_id`, `quantity`, `unit_code`, `cost_snapshot`. Girdi lotu ve emir input_weight tutarlılığı doğrulanır.

### `POST /api/v1/butchering-orders/{order_id}/outputs`
**Yetki:** `ADMIN`, `OPERATOR`.  
İstek:
```json
{
  "product_id": 300,
  "lot_code": "KESIM-2026-012-A",
  "output_type": "CUT",
  "actual_weight": "8.500000",
  "unit_code": "KG",
  "allocation_weight": "8.500000",
  "allocation_value": "120.0000"
}
```
Bağlayıcı karar (Cilt 1.17): `WASTE` bu `outputs` DTO’suna dahil edilmez. `CUT` ve stokta izlenen `BYPRODUCT` için `product_id` ve `lot_code` zorunludur. Fire ayrı `POST /api/v1/butchering-orders/{order_id}/waste-records` endpoint’iyle kaydedilir; ürün/çıktı lotu veya stok IN hareketi oluşturmaz.

### `POST /api/v1/butchering-orders/{order_id}/complete`
**Yetki:** `ADMIN`, `OPERATOR`.  
Başlık: `Idempotency-Key`.  
**Kural:** Girdi OUT, kullanılabilir kesim/yan ürün lotları ve IN hareketleri, ayrı fire kayıtları, genealogy edges, maliyet dağıtımı ve audit tek transaction içinde tamamlanır. Dağıtılan maliyet toplamı toplam girdi maliyetine eşit olmalıdır. Ağırlık farkı raporlanır; sessizce kayıp miktar uydurulmaz.

## 8. Satış ve sevkiyat endpoint'leri

### `POST /api/v1/sales`
**Yetki:** `ADMIN`, `SALES`.  
Başlık: `Idempotency-Key` zorunlu.  
İstek:
```json
{
  "sold_at": "2026-10-22T12:30:00Z",
  "currency_code": "EUR",
  "lines": [
    {
      "product_id": 200,
      "lot_id": 201,
      "quantity": "2.000000",
      "unit_code": "PACK",
      "unit_price": "22.0000"
    }
  ]
}
```
Yanıt `201`: Satış, satırları ve hesaplanan toplam.

**Backend zorunlu doğrulamaları**
1. Kullanıcı yetkili mi?
2. Her lot ilgili ürünle eşleşiyor mu?
3. Yeni ticari satış kaydı aktif recall/blokaj altındaki lot için yasak mı? (Kural uygulanır; tarihsel kayıtlar silinmez.)
4. Fiyat/miktar/para birimi geçerli mi?
5. Satır ve satış toplamları backend tarafından hesaplandı mı?
6. Aynı idempotency anahtarı daha önce kullanıldı mı?

Satış endpoint’i stok bakiyesi yeterliliği kontrol etmez ve bakiye kilitlemez; bu kontroller fiziksel stok çıkışının tek sahibi olan dispatch transaction’ında zorunludur.

Satış başlığı/satırları, audit ve idempotency yanıtı aynı transaction içinde olmalıdır. **Satış endpoint’i `OUT` hareketi üretmez ve stok bakiyesini azaltmaz. Fiziksel stok çıkışının tek sahibi `POST /api/v1/shipments/{shipment_id}/dispatch` endpoint’idir.**

### `GET /api/v1/sales`
**Yetki:** `ADMIN`, `SALES`; diğer roller için rol tablosuna göre kısıtlı okuma.  
**Filtreler:** `from`, `to`, `lot_id`, `product_id`, `sale_code`, sayfalama.

### `GET /api/v1/sales/{sale_id}`
**Yetki:** `ADMIN`, `SALES`.  
**Yanıt:** Başlık ve lot bazlı satırlar.

### `POST /api/v1/sales/{sale_id}/void`
**Yetki:** `ADMIN`.  
**Kural:** Tamamlanmış satış hard delete edilmez. İptal/iadede stok geri girişi ancak açık bir iade/düzeltme hareketiyle yapılır; satışın geçmişi korunur.

### `POST /api/v1/shipments`
**Yetki:** `ADMIN`, `SALES`.  
İstek:
```json
{
  "customer_id": 400,
  "notes": "Delivery to Market A",
  "lines": [
    {
      "product_id": 200,
      "lot_id": 201,
      "quantity": "30.000000",
      "unit_code": "PACK"
    }
  ]
}
```
Yanıt `201`: Taslak sevkiyat.

### `POST /api/v1/shipments/{shipment_id}/dispatch`
**Yetki:** `ADMIN`, `SALES`.  
Başlık: `Idempotency-Key` zorunlu.  
**Kural:** Lot blokajı ve stok kontrolü; her satır için tek `OUT/SHIPMENT` hareketi; bakiye güncellemesi; sevkiyat `SHIPPED` durumu; audit ve idempotency sonucu — hepsi aynı transaction içinde. Dispatch fiziksel stok çıkışının tek sahibidir. Satış kaydı aynı miktar için stok düşmez. Aynı sevkiyat iki kez stok düşüremez; hata durumunda tüm etkiler rollback edilir.

### `GET /api/v1/shipments`
**Yetki:** `ADMIN`, `OPERATOR`, `SALES`, `TRACEABILITY_MANAGER`, `VIEWER` (salt okuma; kaynak kapsamı kontrol edilir); filtreler `customer_id`, `lot_id`, `status`, tarih aralığı ve sayfalama.

### `GET /api/v1/shipments/{shipment_id}`
**Yetki:** Aynı rol grubu.  
**Yanıt:** Sevkiyat başlığı, müşteri ve lot bazlı satırlar.

## 9. İzlenebilirlik endpoint'leri

### `GET /api/v1/traceability/lots/{lot_id}/backward`
**Yetki:** `ADMIN`, `OPERATOR`, `SALES`, `TRACEABILITY_MANAGER`; `VIEWER` için yetki verilmiş salt okuma.  
**Yanıt:** Kaynak lotlar, tedarikçiler, girdi hareketleri, süreç belgeleri ve miktarlı genealogy ilişkileri.

### `GET /api/v1/traceability/lots/{lot_id}/forward`
**Yetki:** Aynı rol grubu.  
**Yanıt:** Türetilen lotlar, üretim/parçalama süreçleri, kayıtlı satış ve sevkiyatlar; her müşteri/market için lot bazında miktarlar.

### `GET /api/v1/traceability/lots/by-code/{lot_code}/summary`
**Yetki:** Aynı rol grubu.  
**Yanıt:** Lot özeti, bakiye, aktif blokaj, geriye/ileri iz bağlantı sayıları ve ilişkili müşteri/marketler.

İzlenebilirlik yanıtı kayıtta olmayan dağıtımı tahmin etmez. Son tüketici satışları market tarafından paylaşılmıyorsa rapor yalnızca işletmenin kayıtlı sevkiyat noktasına kadar uzanır.

## 10. Recall endpoint'leri

### `POST /api/v1/recalls`
**Yetki:** `ADMIN`, `TRACEABILITY_MANAGER`.  
İstek:
```json
{
  "recall_code": "RCL-2026-001",
  "origin_lot_id": 101,
  "reason_code": "CONTAMINATION_SUSPECTED",
  "reason_text": "Traceability demo recall"
}
```
Yanıt `201`: Taslak recall veya aktifleşme öncesi hesaplanan kapsam. Başlatma davranışı ayrı endpoint'te açıkça ayrılır.

### `POST /api/v1/recalls/{recall_id}/activate`
**Yetki:** `ADMIN`, `TRACEABILITY_MANAGER`.  
Başlık: `Idempotency-Key` önerilir.  
**Kural:** Kaynak lotun ileri izi bulunur; etkilenen lotlar kaydedilir; aktif blokajlar oluşturulur; kayıtlı sevkiyatlara göre market/müşteri etkileri hazırlanır; audit yazılır. Kritik lot blokajları başarıyla uygulanmadan recall `ACTIVE` olmamalıdır.

### `GET /api/v1/recalls`
**Yetki:** `ADMIN`, `TRACEABILITY_MANAGER`; yetkili salt okuma rolleri için kısıtlı okuma.  
**Filtreler:** `status`, `from`, `to`, `page`, `page_size`.

### `GET /api/v1/recalls/{recall_id}`
**Yetki:** `ADMIN`, `TRACEABILITY_MANAGER`.  
**Yanıt:** Recall durumu, kaynak/etkilenen lotlar, blokajlar, sevkiyatlar, miktarlar ve müşteri iletişim durumu.

### `POST /api/v1/recalls/{recall_id}/close`
**Yetki:** `ADMIN`, `TRACEABILITY_MANAGER`.  
**Kural:** Kapatma, tarihsel kayıtları silmez. Blokajın kaldırılması ayrı ve açık bir işlem olmalı; yalnızca recall kapatıldı diye lot otomatik satılabilir hâle gelmemelidir.

### `PATCH /api/v1/recalls/{recall_id}/customer-impacts/{impact_id}`
**Yetki:** `ADMIN`, `TRACEABILITY_MANAGER`.  
**Amaç:** `contact_status`, `contacted_at`, `notes` güncellemek. Değişiklik audit edilir.

## 11. AI endpoint'leri

### `POST /api/v1/predictions/production-yield`
**Yetki:** `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`.  
İstek:
```json
{
  "production_order_id": 501
}
```
Yanıt:
```json
{
  "prediction_type": "PRODUCTION_YIELD_EKP",
  "model_version": "baseline-001",
  "predicted_yield_quantity": "85.000000",
  "predicted_unit_cost": "18.1600",
  "actual_yield_quantity": null,
  "actual_unit_cost": null,
  "metric_name": "MAE",
  "limitations_note": "Limited historical training data; prediction is advisory only."
}
```
Gerçek değer mevcutsa eklenir. Model yoksa açık `MODEL_NOT_AVAILABLE` veya `INSUFFICIENT_TRAINING_DATA` hatası dönülür; sahte tahmin üretilmez.

### `POST /api/v1/predictions/butchering-yield`
**Yetki:** `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`.  
İstek:
```json
{
  "animal_type": "LAMB",
  "input_weight": "25.000000",
  "input_unit_code": "KG"
}
```
Yanıt: Tahmin edilen kesim/yan ürün/fire ağırlıkları, model sürümü, mümkünse gerçek karşılaştırma alanları ve sınırlamalar. Model, her çıktı sınıfı için ayrı tahmin döndürebilir. Model yoksa sahte tahmin üretmez.

### `GET /api/v1/predictions/{prediction_id}`
**Yetki:** `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`; yetkili salt okuma.  
**Yanıt:** Kaydedilmiş tahmin, model sürümü, girdi referansı, varsa gerçek değer ve hata metriği.

## 12. Audit ve sistem sağlığı

### `GET /api/v1/audit-events`
**Yetki:** `ADMIN`; `TRACEABILITY_MANAGER` yalnızca izin verilen operasyon türlerini görebilir.  
**Filtreler:** `entity_type`, `entity_id`, `actor_user_id`, `action`, tarih aralığı ve sayfalama.

### `GET /health/live`
**Yetki:** Public; minimal liveness only.
**Yanıt:** `200` uygulama sürecinin istek karşılayabildiğini belirtir; DB host, bağlantı dizesi veya altyapı ayrıntısı döndürmez.

### `GET /health/ready`
**Yetki:** Internal ağ veya `ADMIN` ile sınırlandırılır.
**Yanıt:** Uygulamanın gerekli bağımlılıklarının hazır olup olmadığını bildirir; dış kullanıcıya hassas dependency/DB ayrıntısı verilmez.


## 13. Endpoint kapsam matrisi

| Modül | Asgari endpoint grubu | Kritik doğrulama |
|---|---|---|
| Auth | login, me, logout | Token ve rol |
| Katalog | products, units, suppliers, customers | Unique kod ve aktiflik |
| Stok | lots, balances, movements, receipts, adjustments | Lot, bakiye, audit |
| Üretim | orders, inputs, service-costs, outputs, complete | Transaction, maliyet snapshot, genealogy |
| Parçalama | orders, inputs, outputs, complete | Ağırlık dengesi, maliyet dağıtımı |
| Satış | create, list, detail, void | Ticari doğrulama, idempotency; fiziksel stok kontrolü/OUT dispatch işleminde |
| Sevkiyat | create, dispatch, list, detail | Lot bazlı stok çıkışı |
| İzlenebilirlik | backward, forward, summary | Genealogy ve kayıtlı dağıtım |
| Recall | create, activate, list, detail, close, customer impacts | Blokaj ve etkilenmiş müşteriler |
| ML | production-yield, butchering-yield, prediction detail | Model sürümü, baseline, sınırlamalar |
| Audit | audit events | Rol ve gizli veriyi maskeleme |

## 14. Uygulama notları ve açık düzeltme kapıları

Bu belge endpoint sözleşmesini sabitler; implementasyonda aşağıdaki noktalar ayrıca OpenAPI/şema testleriyle doğrulanmalıdır:

1. Cilt 1.17 kararıyla fire ayrı `butchering_waste_records` tablosu/DTO’sundadır; `butchering_outputs` yalnızca `CUT`/stokta izlenen `BYPRODUCT` kabul eder. X-02 kararı verilmiştir; migration öncesi gerçek ERD/DTO/ORM eşlemesi ve test gerekir.
2. Recall oluşturma ile aktive etme ayrı tutulur; aktif blokajların uygulanması başarısızsa recall aktif sayılmaz.
3. JWT logout sunucu tarafında iptal sağlamazsa bu durum dokümante edilir; gerekiyorsa token blacklist/short-lived token kararı ayrıca alınır.
4. Hata alan adı API genelinde `request_id` olarak kullanılır; DEC-001'in kavramsal `requestId` alanıyla aynı bilgiyi taşır.
5. API'deki örnek ID ve token'lar yalnızca örnektir; gerçek seed ID'leri seed script'inde tanımlanır.
6. Tüm POST işlemlerinin idempotency gereksinimi endpoint bazında açık olmalıdır. Satış, üretim tamamlama, parçalama tamamlama, sevkiyat dispatch ve recall activate için zorunlu veya güvenli tekrar koruması şarttır.
7. API sözleşmesi değiştiğinde Pydantic schema, OpenAPI, TypeScript DTO, Kotlin DTO ve contract testleri aynı değişiklikte güncellenmelidir.

## 15. Cilt 1.3 kabul kriterleri

- [ ] Her endpoint için method/path/rol belirtilmiş.
- [ ] JSON alanları `snake_case`; hassas para/miktar string.
- [ ] Hatalar ortak `error` zarfını kullanıyor.
- [ ] Satış, üretim, parçalama, sevkiyat ve recall için transaction kuralları tanımlı.
- [ ] Lot blokajı backend tarafında satış ve sevkiyat sırasında doğrulanıyor.
- [ ] Idempotency gerektiren endpoint'ler belirtilmiş.
- [ ] İleri/geriye izlenebilirlik kayıtlı lot genealogy'sini kullanıyor.
- [ ] AI endpoint'leri model yokken sahte tahmin üretmiyor.
- [ ] OpenAPI çıktısı ve örnek JSON'lar test edilebiliyor.
- [ ] Android ve web paneli MySQL'e doğrudan bağlanmıyor.

## 16. Sonraki belge

**Cilt 1.4 — OpenAPI örnekleri, ortak DTO'lar ve contract test planı.** Bu belge API sözleşmesini makine tarafından doğrulanabilir örneklerle ve istemci tip eşlemesiyle tamamlayacaktır.

## Revizyon 1.11 — API sözleşmesi için kanonik davranışlar

Bu bölüm, önceki örneklerdeki çelişkili/karar bekleyen ifadelerin yerine geçer.

### Kimlik doğrulama ve health
- Access token ömrü 15 dakikadır (`expires_in: 900`); refresh token 7 gündür ve rotation zorunludur. Logout refresh session'ını sunucu tarafında iptal eder; refresh reuse tespitinde token ailesi iptal edilir. Android tokenları Keystore ile korunan şifreli depoda tutulur; web HttpOnly cookie + CSRF koruması kullanır. Web tek-origin reverse proxy varsayımıyla çalışır.
- `/health/live` anonim ve DB sorgusuz 200 döndürür. `/health/ready` anonimdir; bağımlılıklar hazırsa 200, hazır değilse 503 döndürür; response secret veya ayrıntılı bağlantı bilgisi içermez. Bu yollar `/api/v1` prefix'i dışında kalır.
- Cilt 1.31/1.32 onaylı kararları bu dosyadaki eski çelişkili örneklere göre önceliklidir.okie/CSRF ayrıntıları platforma özgü güvenlik dokümanında tanımlanır.
- `/health/live` anonim ve DB sorgusuz liveness endpoint'idir; `/health/ready` anonim readiness endpoint'idir (hazırsa 200, değilse 503). Her ikisi `/api/v1` prefix'i dışındadır ve secret/dependency ayrıntısı döndürmez.

### Yetki matrisi için bağlayıcı varsayılanlar
- Genel stok düzeltme: yalnızca `ADMIN`. `OPERATOR`, normal kabul/üretim/parçalama akışları üzerinden stok hareketi oluşturabilir.
- Sevkiyat oluşturma ve dispatch: `ADMIN` ve `SALES`; `OPERATOR` ile `TRACEABILITY_MANAGER` yalnızca okur.
- AI tahmini başlatma: `ADMIN`, `OPERATOR`. Tahmin sonucu okuma: `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`, `VIEWER`; `SALES` ilk sürümde dışarıda.
- Recall çözmek, lot blokajını kaldırmaz. Lotu yeniden satışa açma ayrı yetkili, audit edilen komuttur.

### Stok etkileri ve tekrar istekler
- Üretim tüketimi `IN_PROGRESS` sırasında değil, tamamlanırken gerçek tüketim miktarıyla `OUT` olarak kaydedilir.
- Parçalama/üretim tamamlama, lot kabulü, stok düzeltme, sevkiyat dispatch ve recall aktivasyonu gibi stok/maliyet etkili komutlar ya `Idempotency-Key` kullanır ya da tamamlanmış durumdan tekrar çağrıldığında deterministik bir conflict ile reddedilir; endpoint tablosu her biri için yöntemi açıkça belirtmelidir. Satışta başlık zorunludur. Aynı anahtar + aynı istek önceki sonucu döndürür; aynı anahtar + farklı gövde `409 IDEMPOTENCY_KEY_REUSED` olur.
- Market sevkiyatında fiziksel stok `OUT` hareketinin tek sahibi dispatch işlemidir; satış kaydı aynı fiziksel miktarı tekrar düşmez. Bu onaylanmış normatif karardır (Cilt 1.14, DEC-001 Karar 14).

### Recall ve parçalama
- Recall aktivasyonu MVP'de senkron ve atomiktir; kısmi blokaj bırakılamaz. `ACTIVATING` ara durumu kullanılmaz.
- Recall `RESOLVED` durumu lot blokajını kaldırmaz; yeniden açma ayrı komuttur.
- Stokta izlenen parçalama çıktılarında ürün ve lot zorunlu; yalnızca fire ölçüm satırında bu alanlar nullable olabilir ve bu satır satılabilir stok yaratmaz.
- Ağırlık toleransı sayısal olarak `TBD`; sabit değer uydurulmaz.

### Ortak hata yanıtı
API JSON alan adlandırma standardı gereği hata zarfı `request_id` kullanır (camelCase `requestId` değil): `error.code`, `error.message`, isteğe bağlı `error.details`, `request_id`. HTTP status ile `error.code` ayrı kavramlardır. Tek kanonik registry, Cilt 1.4 ve test örnekleriyle birlikte tutulmalıdır. Genel `CONFLICT` yalnızca özel kod tanımlı olmayan genel çakışmalar için kullanılabilir; `IDEMPOTENCY_KEY_REUSED`, `INVALID_STATE_TRANSITION`, `LOT_BLOCKED` gibi özel kodlar sessizce `CONFLICT`'e dönüştürülmez.
