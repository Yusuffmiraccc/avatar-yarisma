# AVATAR — Backend ve Veritabanı Mimarisinin Kapanış Planı

**Sürüm:** 1.45  
**Tarih:** 22 Ekim 2026  
**Durum:** Mimari kararların uygulanabilir hâle getirilmesi için kanonik çalışma belgesi. Bu belge gerçek MySQL veritabanı üzerinde işlem yapıldığı anlamına gelmez.

## 1. Karar

Projenin backend/veritabanı mimarisi aşağıdaki mimariyle sabitlenmiştir. Yeni teknoloji seçimi yapılmayacak:

- FastAPI + Pydantic
- SQLAlchemy 2.x
- Alembic
- PyMySQL
- MySQL 8.4 LTS
- REST/JSON, `/api/v1`, OpenAPI
- pytest ile unit/integration/contract testleri

İstemciler MySQL'e bağlanmaz. İş kuralları servis katmanında; transaction sınırları kullanım senaryosu servislerinde olur. Router katmanı HTTP doğrulaması, yetkilendirme bağımlılıkları ve yanıt eşlemesiyle sınırlıdır.

## 2. Kanonik katmanlar

```text
Android / Web
      |
      v
FastAPI routers (/api/v1)
      |
      v
Authentication + Permission dependencies
      |
      v
Application services / use cases  <--- transaction boundary
      |
      +--> Domain calculations (costing, weight balance, traceability)
      |
      +--> SQLAlchemy repositories/queries
                 |
                 v
             MySQL 8.4
```

### Sorumluluklar

- `api/`: router, request/response DTO, dependency ve HTTP mapping.
- `core/`: settings, logging, security helpers, error envelope.
- `db/`: SQLAlchemy base, session, transaction configuration.
- `models/`: ORM tabloları ve ilişkiler.
- `schemas/`: Pydantic request/response modelleri.
- `services/`: use-case orchestration, iş kuralları, transaction sınırları.
- `repositories/`: yalnızca tekrar kullanılabilir veya karmaşık sorgular için; her tabloya zorunlu repository yok.
- `domain/`: maliyet, ağırlık dengesi, lot genealogy gibi saf ve test edilebilir hesaplamalar.
- `ml/`: üretim ve parçalama tahmin pipeline'ları; operasyonel kayıtların doğruluk kaynağı değildir.
- `tests/`: unit, integration, API contract, concurrency ve end-to-end testleri.

## 3. Veritabanı kuralları

1. İç kimlikler `BIGINT UNSIGNED`; iş kodları ayrı benzersiz alanlar.
2. Para `DECIMAL(19,4)`, miktar/ağırlık `DECIMAL(19,6)`; Python `Decimal` kullanılır.
3. API para/miktar değerleri ondalık string taşır.
4. Tüm timestamp'ler UTC; API'de ISO 8601 `Z`; tarih-only alanları `YYYY-MM-DD`.
5. `stock_movements` append-only hareket defteridir. Hareket miktarı daima pozitif, yön `IN`/`OUT`.
6. `inventory_balances` ile hareket defteri aynı DB transaction'ında güncellenir; bakiye doğrudan düzenlenmez.
7. Lot genealogy miktarlı çoktan-çoğa ilişki taşır.
8. Tamamlanmış operasyonlar silinmez; düzeltme/ters kayıt ve audit kullanılır.
9. JSON alan adları `snake_case`, enumlar `UPPER_SNAKE_CASE`.
10. Stok veya maliyet etkileyen tüm komutlar servis katmanında tek atomik transaction içinde yürür.

## 4. Kanonik workflow kararları

Aşağıdaki eşleştirme, Cilt 1.5'in sonundaki Revizyon 1.11 başlıklarına göre kullanılır. Belgenin eski 13. bölümündeki WF tablosu tarihsel içeriktir; oradaki WF numaraları güncel numaralandırma olarak kullanılmamalıdır.

| Workflow | Kanonik kural | Uygulama etkisi |
|---|---|---|
| WF-01 | Butchering outputs stokta izlenen ürün/lot gerektirir; waste ayrı kayıttır ve stok IN yaratmaz. | Ayrı DTO/model/servis doğrulaması. |
| WF-02 | Üretimde rezervasyon yok; `IN_PROGRESS` stok düşmez; tamamlama anında gerçek OUT/IN, genealogy, maliyet ve audit tek transaction. | Tamamlama servisi atomik. |
| WF-03 | Dispatch fiziksel stok OUT hareketinin tek sahibidir; sale aynı miktarı tekrar düşmez. | Dispatch idempotent; satış ticari kayıt. |
| WF-04 | Recall aktivasyonu MVP'de senkron/atomik; `ACTIVATING` yok; `RESOLVED` blokajı kendiliğinden kaldırmaz. | Ayrı yetkili release/unblock komutu. |
| WF-05 | Ağırlık toleransı kaynakta sayısal verilmemiştir; konfigüre edilebilir, sessiz sıfırlama yok. | Ayar ve gerekçe/audit; değeri ortam konfigürasyonunda tutulur. |
| WF-06 | Tamamlanmış işlem silinmez; bağlı ters kayıt/düzeltme ve audit aynı transaction. | Kaynak kayıt referansı ve ters hareketler. |
| WF-07 | Satış `Idempotency-Key` zorunlu; diğer kritik komutlar deterministik idempotency veya state conflict koruması kullanır. | Unique idempotency kayıtları ve retry testleri. |

WF-08–WF-10 numaraları eski listelerde farklı içeriklerle kullanıldığından, eski numaraları kod sabiti olarak kullanmayın. İlgili konu adıyla referans verin: `ML prediction lifecycle`, `state transition registry`, `auth/session lifecycle`. Bu adlandırma karışıklığını önler.

## 5. Veri modeli — 29 kavramsal varlık

Aşağıdaki entity adları ERD'den alınmış kavramsal listedir. Cilt 1.2'deki ayrıntılı alan tabloları, fiziksel kolon sözleşmesi için esas alınır; bu listenin tek başına eksiksiz DDL olduğu iddia edilmez.

1. `users`
2. `sales`
3. `production_orders`
4. `butchering_orders`
5. `products`
6. `lots`
7. `suppliers`
8. `customers`
9. `shipments`
10. `product_prices`
11. `units`
12. `unit_conversions`
13. `inventory_balances`
14. `stock_movements`
15. `production_inputs`
16. `production_outputs`
17. `production_service_costs`
18. `butchering_inputs`
19. `butchering_outputs`
20. `butchering_waste_records`
21. `lot_genealogy_edges`
22. `sale_lines`
23. `shipment_lines`
24. `recalls`
25. `recall_lots`
26. `recall_customer_impacts`
27. `lot_blocks`
28. `audit_events`
29. `ml_predictions`

Cilt 1.2 ayrıca auth için `roles` ve `user_roles`, retry güvenliği için `idempotency_records` tanımlar. Bu nedenle uygulama şema envanteri, yalnız Mermaid ERD'deki 29 entity ile sınırlanmayacaktır.

## 6. Seçilen güvenli varsayılanlar

Bu proje sahibinin genel yetki devri kapsamında uygulama tutarlılığı için benimsenen başlangıç kararlarıdır. Yarışma kaynağında sayısal değer olmayan yerlerde gerçekmiş gibi değer uydurulmaz.

- **Expiry:** `products.requires_expiry_date` eklenir; true ise lotta `expiry_date` zorunludur. Varsayılan false. Ürün politikası değişikliği geçmiş lotları geriye dönük değiştirmez.
- **Weight tolerance:** evrensel sabit sayı kod içine gömülmez. Konfigürasyonla verilir; demo varsayılanı `0.000 kg`; fark bu değeri aşarsa gerekçe ve yetkili karar gerekir. Bu bir proje konfigürasyonudur, yarışma kaynağının değeri değildir.
- **BY_WEIGHT:** maliyet, tartılmış stok çıktıları ve ölçülmüş fire arasında ağırlık oranında dağıtılır. Fire maliyeti ayrı gösterilir, satılabilir stok maliyeti/stock output olarak sayılmaz.
- **BY_VALUE:** güvenilir ve onaylı fire değerleme girdisi yoksa parçalama emri tamamlanamaz. Otomatik `0` fire maliyeti veya otomatik BY_WEIGHT fallback yoktur. Demo için BY_WEIGHT varsayılan yöntemdir.
- **Rounding:** hesaplar `Decimal` ile yapılır; yuvarlama farkı deterministik olarak en son tahsis satırına uygulanır; toplam maliyet girdi maliyetine tam eşit olmalıdır. Fire ve stok çıktı satırları ayrı tutulur.
- **Waste source lot:** her fire kaydı tam bir `butchering_input`/kaynak girdi lotuyla ilişkilendirilir. Birden fazla kaynak varsa ayrı fire satırları yazılır.
- **Correction:** tamamlanmış operasyonlar için ters kayıt kaynağa bağlanır; yalnız yetkili roller; gerekçe zorunlu; audit ve ters hareketler tek transaction.
- **Recall concurrency:** satış/dispatch ve recall aktivasyonu aynı lot/balance/lot-block satırlarını tutarlı sırada kilitler; transaction commit sırasına göre recall aktif olduktan sonra başlayan çıkış reddedilir. Bu davranış integration test ile doğrulanır.
- **Auth:** access token 15 dakika, refresh 7 gün, refresh rotation; refresh token hash olarak saklanır. Logout refresh session'ını iptal eder. Access token invalidation gereksinimi için kısa ömür ve session/version kontrolü uygulanır; gerçek tokenlar loglanmaz.
- **Waste endpoint permission:** `POST /api/v1/butchering-orders/{order_id}/waste-records` `ADMIN` ve `OPERATOR` + `butchering:manage` gerektirir.
- **ML prediction:** model adı/sürümü, input referansı/snapshot özeti, tahmin, gerçek değer (varsa), hata metriği ve durum (`SUCCEEDED`/`FAILED`) kaydedilir. ML başarısızlığı stok/traceability işlemlerini engellemez.

## 7. Backend endpoint sözleşmesi için zorunlu işlem deseni

Her yazma use-case'i şu sırayı izler:

1. Kimlik doğrula ve aktif kullanıcıyı kontrol et.
2. Endpoint iznini backend'de doğrula.
3. İstek DTO'sunu doğrula; kullanıcı tarafından verilen maliyet toplamlarını otorite kabul etme.
4. DB transaction başlat.
5. Gerekli lot/balance/operasyon satırlarını tutarlı sırada `SELECT ... FOR UPDATE` ile kilitle.
6. İş kuralı ve stok yeterliliğini kilit altında tekrar doğrula.
7. Operasyon satırları, hareket defteri, bakiye, genealogy, idempotency sonucu ve audit'i yaz.
8. Commit et; hata olursa tümü rollback.
9. Ortak hata zarfı kullan: `error.code`, `error.message`, isteğe bağlı `error.details`, `request_id`.

Stok değiştiren bir serviste HTTP router'ın kendi başına hareket/bakiye yazması yasaktır.

## 8. API ve hata sözleşmesi

- Prefix: `/api/v1`.
- Liste yanıtları tek biçimli sayfalama kullanır (`items`, `page`, `page_size`, `total`).
- `401 UNAUTHENTICATED`, `403 FORBIDDEN`, `404 RESOURCE_NOT_FOUND`, `409 CONFLICT`, `409 IDEMPOTENCY_KEY_REUSED`, `409 INSUFFICIENT_STOCK`, `409 LOT_BLOCKED`, `409 INVALID_STATE_TRANSITION`, `422 BUSINESS_RULE_VIOLATION`, `500 INTERNAL_ERROR`.
- FastAPI'nin ham validation/internal traceback yanıtları dışarı sızdırılmaz.
- Kritik POST'larda body hash idempotency kaydında tutulur; aynı anahtar + aynı body ilk sonucu döndürür, farklı body `409`.

## 9. Kabul testleri — mimarinin bittiğini kanıtlayan koşullar

### 9.1 Stok
- Lot kabulü bir lot, `IN` hareketi ve balance oluşturur.
- Aynı kabul retry edildiğinde çift hareket oluşmaz.
- Eşzamanlı satış/dispatch toplamda mevcut bakiyeden fazlasını çıkaramaz.
- Bloke lot için satış ve dispatch reddedilir.
- Balance ile ledger toplamı mutabık kalır.

### 9.2 Üretim
- 100 kg et, 2 kg baharat, 5 kg kılıf, 85 paket ve hizmet maliyeti örneği toplam €1,543.50, EKP yaklaşık €18.16 verir.
- Tamamlama başarısız olursa stok, genealogy, maliyet ve audit etkileri rollback olur.

### 9.3 Parçalama
- Çıktı + fire ağırlığı girdiyle karşılaştırılır; tolerans üstü fark açıkça raporlanır.
- `BY_WEIGHT` maliyet toplamı girdi maliyetine eşittir.
- `BY_VALUE` gerekli değer girdisi eksikse tamamlanmaz.
- Fire hiçbir durumda satılabilir lot veya `IN` hareketi yaratmaz.

### 9.4 Recall
- `ET-2026-001` → `URT-2026-045` → `SUC-2026-045` genealogy zinciri ve 30/25/30 paketlik sevkiyat etkisi raporlanır.
- Recall aktivasyonu atomiktir; başarısız aktivasyonda kısmi blokaj kalmaz.
- Recall çözülünce blokaj kendiliğinden kalkmaz.
- Recall sonrası yeni satış/dispatch engellenir.

### 9.5 Güvenlik ve API
- Her endpoint için izin testi; VIEWER write yapamaz.
- Hatalar ortak zarfla döner; secret/stack trace loga/yanıta sızmaz.
- Migration boş MySQL 8.4 üzerinde yeniden üretilebilir; testler geçer.

## 10. Uygulama sırası — artık belge üretmek yerine ürün üret

1. Backend repo iskeleti, config, logging, error handling, health, test/CI.
2. SQLAlchemy modelleri ve ilişkiler.
3. İlk Alembic migration; önce test MySQL, sonra yerel geliştirme DB.
4. Auth/permission, catalog, lot receipt, stock ledger/balance, audit.
5. Production tamamlaması ve EKP maliyeti.
6. Butchering tamamlaması, fire ve maliyet tahsisi.
7. Sales + shipment/dispatch + idempotency.
8. Lot genealogy, recall, block/release, traceability.
9. ML prediction lifecycle.
10. OpenAPI contract + end-to-end senaryo ve demo seed.

## 11. Dürüst durum bildirimi

Bu belge, tasarım kararlarını tek yerde sabitleyen mimari kapanış belgesidir. Ancak burada fiziksel MySQL sunucusu üzerinde migration çalıştırıldığı, bütün testlerin geçtiği veya backend'in canlı çalıştığı iddia edilmez. Bu sonuçlar ancak gerçek kaynak kodu oluşturulup testler çalıştırıldığında raporlanabilir.
