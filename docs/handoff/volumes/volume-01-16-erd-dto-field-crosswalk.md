# Cilt 1.16 — ERD–DTO Alan Eşleştirme Matrisi ve Açık Kapılar

**Tarih:** 22 Ekim 2026  
**Durum:** Dokümantasyon çapraz kontrolü; migration onayı değildir.  
**Normatif kaynak sırası:** DEC-001 ve onaylanmış kararlar → Cilt 1.2 veri şeması → Cilt 1.3 endpoint sözleşmesi → bu eşleştirme matrisi → Cilt 1.4 DTO/test gereksinimleri. Çelişki görüldüğünde sessizce varsayım yapılmaz; bulgu bu belgede kaydedilir ve kaynak belgeler birlikte güncellenir.

## 1. Eşleştirme kuralları

- DB `NULL` izni ile JSON alanının istekte atlanabilmesi ayrı kavramlardır. Request alanı `required` olabilir ama `nullable` olabilir; bu, alanın mutlaka gönderilip `null` verilebilmesi demektir.
- Response DTO'sunda DB `NULL` alanı `string | null`, `number | null` yerine DEC-001'e göre hassas decimal alanlar için `string | null` olarak modellenir. Nullable olmayan DB alanı response'ta nullable gösterilmez.
- Para `DECIMAL(19,4)` ve miktar/ağırlık `DECIMAL(19,6)` olarak DB'de tutulur ve API'de JSON string olarak taşınır. ID'ler JSON integer olarak kalır; web tarafında güvenli integer sınırı aşılırsa bu ayrı ADR gerektirir.
- `NULL`, sıfır, boş string, bilinmiyor ve uygulanamaz anlamları birbirinin yerine kullanılmaz.
- Bu matris, mevcut Cilt 1.2'de tanımlı kolonları eşleştirir; ERD'de bulunmayan alanları migration'a ekleme yetkisi vermez.

## 2. Kritik alan eşleştirmeleri

| DB tablo.alan | DB NULL? / tip | JSON/DTO alanı | JSON tipi / nullable | Kural ve doğrulama | Durum |
|---|---|---|---|---|---|
| `users.id` | Hayır, BIGINT UNSIGNED | `id` | integer / hayır | Sunucu üretir; create request'inde kabul edilmez | Eşleşti |
| `users.email` | Hayır, VARCHAR(254) | `email` | string / hayır | Normalize küçük harf; unique | Eşleşti |
| `users.updated_at` | Evet, DATETIME(6) | `updated_at` | ISO-8601 UTC string / evet | Değer yoksa `null`; boş string değil | Eşleşti |
| `products.base_unit_code` | Hayır, FK | `base_unit_code` | string / hayır | `units.code` içinde bulunmalı | Eşleşti |
| `suppliers.phone` / `email` | Evet, VARCHAR | `phone` / `email` | string / evet | Eksik iletişim bilgisi `null`; validasyon varsa yalnızca dolu değere uygulanır | Eşleşti |
| `customers.phone` / `email` | Evet, VARCHAR | `phone` / `email` | string / evet | Tedarikçiyle aynı nullable semantiği | Eşleşti |
| `product_prices.valid_to` | Evet, DATETIME(6) | `valid_to` | UTC string / evet | `null` = açık uçlu geçerlilik; aralık çakışmasını servis doğrular | Eşleşti |
| `product_prices.created_by` | Evet, FK users | `created_by` | integer / evet | Sistem tarafından oluşturulan fiyat kaydında null olabilir | Eşleşti |
| `lots.supplier_id` | Evet, FK suppliers | `supplier_id` | integer / evet | Üretim/parçalama kökenli lotta tedarikçi doğrudan olmayabilir; köken genealogy ile izlenir | Eşleşti; köken kuralı test edilmeli |
| `lots.received_at` | Evet, DATETIME(6) | `received_at` | UTC string / evet | Yalnızca fiili teslim alma zamanı biliniyorsa doldurulur; oluşturma zamanı yerine otomatik kopyalanmaz | Eşleşti |
| `lots.expiry_date` | Evet, DATE | `expiry_date` | `YYYY-MM-DD` string / evet | Cilt 1.2 “uygulanabiliyorsa” diyor; ürün/lot bazında hangi gıda lotlarında zorunlu olacağı henüz belirlenmedi | **Açık karar** |
| `lots.created_by` | Evet, FK users | `created_by` | integer / evet | Sistem/seed oluşturduysa null olabilir | Eşleşti |
| `inventory_balances.on_hand_quantity` | Hayır, DECIMAL(19,6) | `on_hand_quantity` | decimal string / hayır | `>= 0`; yalnızca backend transaction günceller | Eşleşti |
| `inventory_balances.reserved_quantity` | Hayır, DECIMAL(19,6) | `reserved_quantity` | decimal string / hayır | MVP'de rezervasyon kullanılmıyorsa `0.000000`; null değil | Eşleşti |
| `stock_movements.source_line_id` | Evet, BIGINT UNSIGNED | `source_line_id` | integer / evet | Hareket kaynak belgenin başlık düzeyindeyse null; doluysa kaynak satır servis katmanında doğrulanır | Eşleşti |
| `stock_movements.idempotency_key` | Evet, VARCHAR(128) | `idempotency_key` | string / evet | Ledger kaydı kritik komutla ilişkilendirilemiyorsa null olabilir; idempotency kuralının asıl otoritesi komut/işlem kaydıdır | Eşleşti; uygulama kararı korunmalı |
| `stock_movements.created_by` | Evet, FK users | `created_by` | integer / evet | Sistem kaynaklı hareketlerde null olabilir; audit `request_id` ile korelasyon sağlanır | Eşleşti |
| `production_orders.planned_quantity` | Evet, DECIMAL(19,6) | `planned_quantity` | decimal string / evet | Planlama miktarı henüz belirlenmemiş olabilir; tamamlanma gerçek miktarları zorunludur | Eşleşti |
| `production_orders.planned_unit_code` | Evet, FK units | `planned_unit_code` | string / evet | `planned_quantity` ile birlikte null olmalı veya ikisi de dolu olmalı | **DB CHECK / servis doğrulaması eklenmeli** |
| `production_orders.started_at` / `completed_at` | Evet, DATETIME(6) | aynı adlar | UTC string / evet | Taslakta ikisi null; `IN_PROGRESS` durumunda `started_at`; `COMPLETED` durumunda `completed_at` dolu olmalı | **State testleri gerekli** |
| `production_orders.supplier_id` | Evet, FK suppliers | `supplier_id` | integer / evet | Yalnızca dış üretici ilişkisi varsa dolu; `OUTSOURCED` için zorunluluk backend kuralı olarak test edilmeli | **Servis kuralı test edilmeli** |
| `production_orders.created_by` / `updated_at` | Evet | aynı adlar | integer / UTC string; nullable | Sistem kaydı ve güncellenmemiş kayıt anlamları korunur | Eşleşti |
| `production_service_costs.supplier_id` | Evet, FK suppliers | `supplier_id` | integer / evet | Hizmet maliyetinin tedarikçi faturasıyla ilişkisi yoksa null olabilir | Eşleşti |
| `butchering_orders.started_at` / `completed_at` | Evet, DATETIME(6) | aynı adlar | UTC string / evet | Durumla ilişkili zaman kuralları state machine testlerinde doğrulanmalı | **State testleri gerekli** |
| `butchering_orders.created_by` | Evet, FK users | `created_by` | integer / evet | Sistem/seed kaydında null olabilir | Eşleşti |
| `butchering_outputs.allocation_weight` | Evet, DECIMAL(19,6) | `allocation_weight` | decimal string / evet | Yalnızca `BY_WEIGHT` tahsisi için anlamlı; `BY_VALUE` için null olabilir | Eşleşti; koşullu validasyon gerekli |
| `butchering_outputs.allocation_value` | Evet, DECIMAL(19,4) | `allocation_value` | decimal string / evet | Yalnızca `BY_VALUE` tahsisi için anlamlı; `BY_WEIGHT` için null olabilir | Eşleşti; koşullu validasyon gerekli |
| `butchering_outputs.product_id` / `lot_id` | Cilt 1.2 alan listesinde zorunlu yazılmış | `product_id` / `lot_id` | integer / koşullu nullable | `CUT` ve stokta izlenen `BYPRODUCT` için zorunlu. `WASTE` için fiziksel lot/ürün yaratılmayan ayrı ölçüm DTO'su kullanılmalı; DB tablosunda nullable yapılıp yapılmayacağı gerçek şema kararıyla uyumlu hale getirilmeli | **ÖNEMLİ ŞEMA ÇELİŞKİSİ — migration blokajı** |
| `butchering_outputs.output_type` | Hayır, enum-like | `output_type` | string enum / hayır | `CUT`, `BYPRODUCT`, `WASTE`; koşullu alan kuralları bu değere göre uygulanır | Eşleşti |
| `lot_blocks.reason_text` | Evet, VARCHAR(500) | `reason_text` | string / evet | `reason_code` zorunlu; açıklama ek bilgi | Eşleşti |
| `lot_blocks.blocked_by` / `unblocked_by` | Evet, FK users | aynı adlar | integer / evet | Sistem olayı veya kullanıcı bilgisi yoksa null; kullanıcı aksiyonu varsa actor zorunlu olmalı | **Servis/audit doğrulaması gerekli** |
| `lot_blocks.unblocked_at` | Evet, DATETIME(6) | `unblocked_at` | UTC string / evet | null = aktif blokaj; dolu = kapatılmış blokaj | Eşleşti |
| `production/butchering/sales/shipments.created_by` | Şemaya göre bazı tablolarda nullable | `created_by` | integer / evet | Sistem seed/otomasyon kayıtları null olabilir; insan komutlarında actor zorunluluğu auth katmanında | Ortak kural |
| `shipments.shipped_at` | Evet, DATETIME(6) | `shipped_at` | UTC string / evet | `DRAFT` iken null; `SHIPPED` olduğunda dispatch zamanı dolu olmalı | **State testleri gerekli** |
| `shipments.notes` | Evet, VARCHAR(1000) | `notes` | string / evet | Not girilmemişse null | Eşleşti |
| `recalls.reason_text` | Evet, VARCHAR(1000) | `reason_text` | string / evet | `reason_code` zorunlu; açıklama opsiyonel | Eşleşti |
| `recalls.started_at` / `closed_at` | Evet, DATETIME(6) | aynı adlar | UTC string / evet | `ACTIVE` için started_at dolu; `CLOSED` için closed_at dolu olmalı | **State testleri gerekli** |
| `recall_lots.blocked_at` | Evet, DATETIME(6) | `blocked_at` | UTC string / evet | Recall activate atomik tamamlanmadan bu alan dolu sayılmamalı; mevcut tasarım ile `lot_blocks` kaydı tutarlılığı test edilmeli | **Şema/iş akışı bağlantısı test edilmeli** |
| `recall_customer_impacts.shipment_id` | Evet, FK shipments | `shipment_id` | integer / evet | Bilinen etki shipment'a bağlanır; yalnızca bilinen müşteri/lot etkisinde null olabilir; sevkiyat varmış gibi varsayılmaz | Eşleşti |
| `recall_customer_impacts.contacted_at` | Evet, DATETIME(6) | `contacted_at` | UTC string / evet | `CONTACTED`/`ACKNOWLEDGED` için zaman zorunlu olmalı; `PENDING` için null | **Servis validasyonu gerekli** |
| `audit_events.actor_user_id` | Evet, FK users | `actor_user_id` | integer / evet | Sistem işi null olabilir; insan aksiyonunda auth actor ile dolu | Eşleşti |
| `audit_events.request_id` | Evet, VARCHAR(80) | `request_id` | string / evet | Request context varsa header/envelope ile aynı değer; scheduled job'da null olabilir | Eşleşti |
| `audit_events.details` | Evet, JSON | `details` | object / evet | Secrets, parola, token veya gereksiz kişisel veri içermez | Eşleşti |
| `ml_predictions.input_reference_type/id` | Evet | aynı adlar | string/integer / nullable | İkisi birlikte null veya birlikte dolu olmalı | **CHECK/servis doğrulaması eklenmeli** |
| `ml_predictions.predicted_value`, `predicted_cost`, `actual_value`, `actual_cost` | Evet, decimal | aynı adlar | decimal string / nullable | Tahmin tipiyle ilgili alan zorunlu; tahmin öncesi actual null olabilir. Hangi alanın zorunlu olduğu `prediction_type` bazında tanımlanmalı | **Prediction-type validation gerekli** |
| `ml_predictions.metric_name`, `error_value`, `limitations_note` | Evet | aynı adlar | string/decimal string / nullable | Hata metriği ölçüm üretildiğinde; veri azlığı açıklaması gerektiğinde limitations_note kullanılır | Eşleşti; koşullu validasyon gerekli |

## 3. Zorunlu, nullable ve koşullu DTO örnekleri

### 3.1 Lot response

```json
{
  "id": 1201,
  "lot_code": "SUC-2026-045",
  "product_id": 301,
  "supplier_id": null,
  "received_at": "2026-10-22T09:00:00Z",
  "expiry_date": null,
  "initial_quantity": "85.000000",
  "unit_code": "PACK",
  "lot_origin_type": "PRODUCTION",
  "status": "ACTIVE"
}
```

Bu örnek `expiry_date` null olmasının her gıda lotu için doğru iş kuralı olduğunu kanıtlamaz; yalnızca mevcut şema nullable davranışını gösterir. Son tüketim tarihi zorunluluğu ayrı kararlaştırılmalıdır.

### 3.2 Parçalama output request — stokta izlenen kesim

```json
{
  "output_type": "CUT",
  "product_id": 410,
  "lot_code": "KESIM-2026-012-A",
  "actual_weight": "8.500000",
  "unit_code": "KG",
  "allocation_weight": "8.500000",
  "allocation_value": null
}
```

### 3.3 Parçalama output request — fire ölçüm satırı

```json
{
  "output_type": "WASTE",
  "product_id": null,
  "lot_code": null,
  "actual_weight": "0.350000",
  "unit_code": "KG",
  "allocation_weight": null,
  "allocation_value": null
}
```

**Önemli blokaj:** Cilt 1.2'nin `butchering_outputs` alan listesi `product_id` ve `lot_id` alanlarını zorunlu yazarken iş kuralı/DTO `WASTE` için null olmasına izin veriyor. Bu çelişki çözülmeden migration yazılamaz. Seçeneklerden biri (a) `product_id`/`lot_id` kolonlarını nullable yapıp CHECK/servis kuralıyla yalnızca `WASTE`'e izin vermek veya (b) fire ölçümlerini ayrı `butchering_waste_measurements` tablosuna taşımaktır. Karar, yeni şema tasarımıyla birlikte ayrıca onaylanmalıdır; bu belge sessizce birini seçmez.

## 4. Koşullu bütünlük kuralları

Aşağıdaki kurallar Pydantic DTO + service validation + test ile uygulanmalı; DB CHECK desteklenen kısımlarda ayrıca kullanılmalıdır:

1. `planned_quantity` ve `planned_unit_code` ikisi birlikte null veya ikisi birlikte dolu olmalı.
2. `lot_origin_type = PURCHASE` için supplier/received-at zorunluluğu işletmenin kabul sürecinde kesinleştirilmeli; mevcut şema her iki alanı nullable tuttuğu için API tek başına daha katı kuralı varsayamaz.
3. `production_type = OUTSOURCED` ise `supplier_id` zorunlu; `IN_HOUSE` için dış üretici supplier_id'si null olmalı.
4. `allocation_method = BY_WEIGHT` ise her stokta izlenen çıktı için `allocation_weight` dolu ve pozitif; `allocation_value` null olabilir. `BY_VALUE` ise `allocation_value` dolu ve pozitif; `allocation_weight` null olabilir.
5. Shipment `DRAFT` durumunda `shipped_at` null; `SHIPPED` durumunda dolu olmalı.
6. Recall `ACTIVE` durumunda `started_at` dolu; `CLOSED` durumunda `closed_at` dolu olmalı. `CANCELLED` için geçmiş zamanlar silinmez.
7. Recall customer impact `contact_status` `PENDING` ise `contacted_at` null; `CONTACTED`/`ACKNOWLEDGED` ise dolu. `UNREACHABLE` için zaman/deneme semantiği ayrıca tanımlanmalı.
8. `ml_predictions.input_reference_type` ve `input_reference_id` ikisi birlikte null veya birlikte dolu. `prediction_type` alanına göre tahmin/gerçek değer alanları doğrulanmalı.
9. `butchering_outputs` fire satırındaki nullable alan çelişkisi çözülmeden tablo DDL'si üretilmez.
10. Actor (`created_by`, `blocked_by`, `unblocked_by`, `actor_user_id`) null olabilirliği DB şemasında korunur; kullanıcı kaynaklı komutlarda authenticated actor kaydedilmesi API/service testleriyle zorunlu tutulur.

## 5. Güncellenen eski metinler

- Cilt 1.3'teki parçalama fire endpoint açıklaması artık onaylanmış DTO ayrımını ifade eder; eski “implementasyonda karar verilecek” cümlesi kaldırılmıştır.
- Cilt 1.3'te dispatch tek `OUT` sahibi kararı “öneri” değil bağlayıcı karar olarak işaretlenmiştir.
- Cilt 1.4'te fire nullable konusu “kararsız” olarak listelenmek yerine, DTO ayrımı onaylı; DB nullable tasarımı ise açık migration blokajı olarak ayrıştırılmıştır.

## 6. Açık kararlar — migration blokajları

| ID | Konu | Gerekli karar / kanıt | Durum |
|---|---|---|---|
| X-01 | `expiry_date` hangi lotlarda zorunlu? | Ürün/lot politikasını belirle; API validation ve test yaz | Açık |
| X-02 | `WASTE` alanları DB'de nullable mı, ayrı tablo mu? | Cilt 1.2 ERD + DTO + maliyet/ağırlık denge kuralını birlikte güncelle ve kullanıcı onayı al | **Blokaj** |
| X-03 | `planned_quantity` / `planned_unit_code` birlikte null kuralı | CHECK destekli şema veya service test kararı | Açık |
| X-04 | `OUTSOURCED` / `IN_HOUSE` supplier koşulu | Pydantic + service testleri | Açık |
| X-05 | `recall_lots.blocked_at` ile `lot_blocks` ilişkisi | Recall activate atomik transaction ve tek blokaj kaynağı belirle | Açık |
| X-06 | `ml_predictions` nullable alanlarının prediction_type bazlı zorunluluğu | Model türü başına DTO/validation matrisi | Açık |
| X-07 | `contacted_at` ve contact_status geçişleri | Durum geçiş tablosu ve test | Açık |

## 7. Migration öncesi kabul ölçütleri

- [ ] Cilt 1.2'deki her tablo/kolon için DB tipi, NULL, FK, UNIQUE, CHECK ve index envanteri makine tarafından çıkarıldı.
- [ ] Her endpoint request/response DTO'su alan alan Cilt 1.2 ile eşlendi; request required/nullable ayrımı açık.
- [ ] Cilt 1.3 ve Cilt 1.4'teki eski çelişkili cümleler arama ile kontrol edildi.
- [ ] `expiry_date` ve `WASTE` şema kararı açıkça kapatıldı.
- [ ] Her koşullu kural için Pydantic, service ve contract testleri tanımlandı.
- [ ] Gerçek OpenAPI üretimi ve ORM metadata/schema diff'i çalıştırıldı ve sonuç raporlandı.
- [ ] Kullanıcıya son ERD/API/DTO özetinin onayı sunuldu.
- [ ] Migration dosyaları için ayrıca açık kullanıcı onayı alındı.

**Bu cilt migration dosyası oluşturmaz ve migration üretimine izin vermez.**
