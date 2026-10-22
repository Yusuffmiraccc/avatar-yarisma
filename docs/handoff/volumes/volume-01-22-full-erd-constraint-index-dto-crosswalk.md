# Cilt 1.22 — Full ERD / Constraint / Index / DTO Crosswalk

**Tarih:** 22 Ekim 2026  
**Durum:** Tasarım denetimi; migration veya veritabanı değişikliği değildir.  
**Amaç:** Cilt 1.2 ERD'si, Cilt 1.3 API sözleşmeleri, Cilt 1.4 DTO/test sözleşmeleri, Cilt 1.16 alan eşleştirmesi ve Cilt 1.17 fire kararları arasında uygulama öncesi izlenebilir bir kontrol matrisi oluşturmak.

> **Önemli:** Bu cilt statik doküman incelemesine dayanır. Henüz ORM metadata, OpenAPI çıktısı veya MySQL DDL üzerinden otomatik schema diff çalıştırıldığı anlamına gelmez. Bu nedenle `DOCUMENTED` ile `VERIFIED` aynı şey değildir. Gerçek migration oluşturulmadan önce aşağıdaki blokajlar kapatılmalıdır.

## 1. Normatif ilkeler

1. DEC-001 ve proje sahibinin açık onayları bağlayıcıdır.
2. Cilt 1.2 tablo/kolon tasarımının ana kaynağıdır; Cilt 1.3 endpoint/API davranışını, Cilt 1.4 DTO ve sözleşme testlerini, Cilt 1.16 alan bazlı eşleştirmeyi tanımlar.
3. Cilt 1.17 ile `butchering_waste_records` ayrı tablo kararı bağlayıcıdır. Fire satırı `butchering_outputs` içinde saklanmaz.
4. Para `DECIMAL(19,4)`, miktar/ağırlık `DECIMAL(19,6)`; API'de decimal değerler JSON string olarak taşınır. Hesaplamalarda binary float kullanılmaz.
5. DB `NULL`, request alanının atlanması, sıfır, boş string, bilinmiyor ve uygulanamaz birbirinden farklıdır.
6. Uygulama katmanında doğrulanması gereken kural, DB constraint'i olarak uygulanabilirliği incelenmeden yalnızca dokümanla DB garantisi verilmiş sayılmaz.
7. Bu ciltteki öneri veya açık maddeler proje sahibi onayı olmadan bağlayıcı karara dönüştürülemez.

## 2. Durum etiketleri

- `DOCUMENTED`: Kaynak belgede tarif edilmiş; gerçek kod/DDL ile henüz doğrulanmış değil.
- `CROSSCHECK_REQUIRED`: En az iki kaynak arasında karşılaştırma veya daha kesin kural gerekli.
- `BLOCKER`: Migration veya kodlama devri öncesinde çözülmeli.
- `DECIDED`: Proje sahibi tarafından açıkça onaylanmış karar.
- `NOT_APPLICABLE`: Bu varlık/alan için ilgili kural uygulanmaz.

## 3. Tablo envanteri

Aşağıdaki tablo Cilt 1.2'de görülen ana varlıkları kapsar. Bu liste, SQLAlchemy metadata'dan çıkarılmış makine-doğrulanmış bir envanter değildir.

| Alan | İlgili tablo(lar) | Kontrol odağı | Durum |
|---|---|---|---|
| Kimlik ve rol | `users`, `roles`, `user_roles` | email normalizasyonu/benzersizliği, rol ilişkisi, aktif kullanıcı ve token davranışı | CROSSCHECK_REQUIRED |
| Katalog ve ölçü | `products`, `units`, `unit_conversions` | base unit FK, dönüşüm yönü, hassasiyet, izin verilen birimler | BLOCKER: dönüşüm kuralları |
| İş ortakları | `suppliers`, `customers` | opsiyonel iletişim alanları, hard-delete yerine pasifleştirme/koruma | CROSSCHECK_REQUIRED |
| Fiyat | `product_prices` | geçerlilik aralığı çakışması, para birimi ve fiyat tarihi | CROSSCHECK_REQUIRED |
| Lot ve stok | `lots`, `inventory_balances`, `stock_movements`, `lot_blocks` | lot kodu, son tüketim tarihi, pozitif hareket miktarı, tek ledger kaydı, blokaj tutarlılığı | BLOCKER: expiry ölçütü ve blokaj kaynağı |
| Üretim | `production_orders`, `production_inputs`, `production_outputs`, `production_service_costs` | state/timestamp, girdi tüketimi, çıktı lotu, hizmet maliyeti ve EKP | CROSSCHECK_REQUIRED |
| Parçalama | `butchering_orders`, `butchering_inputs`, `butchering_outputs`, `butchering_waste_records` | giriş/çıktı/fire ağırlık dengesi, tahsis yöntemi, toplam maliyet mutabakatı | BLOCKER: BY_VALUE fire formülü ve tolerans |
| Genealogy | `lot_genealogy_edges` | çoktan çoğa ilişkiler, kaynak/hedef lot, miktar ve birim | CROSSCHECK_REQUIRED |
| Satış | `sales`, `sale_lines`, `idempotency_records` | idempotency, lot seçimi, stok çıkışı, iptal/ters kayıt | CROSSCHECK_REQUIRED |
| Sevkiyat | `shipments`, `shipment_lines` | satıştan ayrım, dispatch'in tek stok OUT sahibi olması | DECIDED in prior docs; regression test required |
| Geri çağırma | `recalls`, `recall_lots`, `recall_customer_impacts` | aktif blokaj, etkilenen miktarlar, iletişim durumları, çözüm ve yeniden satış izni | BLOCKER: ilişkisel bütünlük/state crosscheck |
| Audit ve AI | `audit_events`, `ml_predictions` | actor/request_id, hassas veri dışlama, prediction-type koşullu alanlar | CROSSCHECK_REQUIRED |

## 4. Alan tipi ve nullable eşleştirme standardı

| Alan sınıfı | DB standardı | API standardı | Kontrol |
|---|---|---|---|
| İç kimlik | `BIGINT UNSIGNED` (DEC-001) | JSON integer | İstek gövdesinden server-owned ID kabul edilmemeli |
| İş kodu | Alan bazında `VARCHAR` + unique kuralı | string | Büyük/küçük harf ve normalizasyon kuralı her kod tipi için belirlenmeli |
| Para | `DECIMAL(19,4)` | JSON string | Yuvarlama yöntemi ve toplam farkının son kaleme uygulanması açıkça belirlenmeli |
| Miktar/ağırlık | `DECIMAL(19,6)` | JSON string | Birim dönüşümü ve ağırlık toleransı açıkça belirlenmeli |
| Tarih | `DATE` | `YYYY-MM-DD` | Saat dilimi dönüşümü uygulanmaz |
| Zaman damgası | `DATETIME(6)` saklama yaklaşımı kaynak belgede netleştirilmeli | ISO-8601 UTC `Z` | DB sürücü/session timezone davranışı test edilmeli |
| Nullable FK | Alan bazında | integer veya null | `null` sadece ilişkinin gerçekten yok/uygulanamaz olduğu durumda |
| Opsiyonel metin | Alan bazında `NULL` | string veya null | Boş string otomatik olarak null sayılmaz; normalize etme kuralı tanımlanmalı |
| Enum/state | DB enum veya kontrollü string; seçimi ERD'de kesinleşmeli | `UPPER_SNAKE_CASE` | Cilt 1.19 registry ile birebir eşleşmeli |

## 5. Koşullu bütünlük kuralları matrisi

| ID | Kural | DB katmanı | API/service katmanı | Test gereği | Durum |
|---|---|---|---|---|---|
| XW-001 | `planned_quantity` ve `planned_unit_code` ikisi birlikte null veya ikisi dolu | Mümkünse CHECK | DTO + service | Her iki geçerli/iki geçersiz kombinasyon | CROSSCHECK_REQUIRED |
| XW-002 | `OUTSOURCED` üretimde `supplier_id` zorunlu; `IN_HOUSE` için dış üretici ilişkisi olmamalı | CHECK mümkün değilse service | DTO + service | İki tür için pozitif/negatif test | CROSSCHECK_REQUIRED |
| XW-003 | `BY_WEIGHT` tahsisinde pozitif `allocation_weight`; `BY_VALUE` tahsisinde pozitif `allocation_value` | CHECK adayı | DTO + service | Yöntem/alan kombinasyon matrisi | BLOCKER: kesin alan semantiği |
| XW-004 | `WASTE` sadece `butchering_waste_records` içinde | FK/şema ayrımı | Endpoint ve service | Fire lot/stock IN yaratmamalı | DECIDED; schema diff gerekli |
| XW-005 | Fire ağırlığı kütle dengesine dahil; stokta satılabilir çıktı oluşturmaz | Sayısal CHECK her şeyi kapsamayabilir | Tek transaction + service | girdi = çıktı + fire + izinli fark | BLOCKER: tolerans ve formül |
| XW-006 | Tahsis edilmiş çıktı maliyeti + fire maliyeti = toplam giriş maliyeti | CHECK genelde toplu toplamı garanti edemez | Transaction içinde Decimal hesabı | BY_WEIGHT ve BY_VALUE örnekleri | BLOCKER: BY_VALUE formülü |
| XW-007 | `expiry_date` yalnızca uygulanabilir ürün/lot için zorunlu | DB tek kolonla ifade edemez | Policy/validation | zorunlu ve uygulanamaz ürün testleri | BLOCKER: uygulanabilirlik ölçütü |
| XW-008 | `SHIPPED` ise `shipped_at` dolu; `DRAFT` ise null | CHECK adayı | state transition service | tüm durum geçişleri | CROSSCHECK_REQUIRED |
| XW-009 | Recall `ACTIVE` ise başlangıç zamanı dolu; `CLOSED` ise kapanış zamanı dolu | CHECK adayı | state service | active/close/cancel testleri | CROSSCHECK_REQUIRED |
| XW-010 | `input_reference_type` ve `input_reference_id` ikisi birlikte null veya dolu | CHECK adayı | DTO + service | null/partial/full kombinasyonları | CROSSCHECK_REQUIRED |
| XW-011 | `prediction_type` belirli tahmin ve gerçek değer alanlarını zorunlu kılar | DB CHECK karmaşık olabilir | type-specific DTO/service | her prediction type | BLOCKER: alan matrisi |
| XW-012 | Recall customer contact status ile `contacted_at` uyumlu | CHECK adayı | state service | `PENDING`, `CONTACTED`, `ACKNOWLEDGED`, `UNREACHABLE` | CROSSCHECK_REQUIRED |
| XW-013 | İnsan kaynaklı kritik işlemde authenticated actor kaydı bulunmalı | FK tek başına yeterli değil | auth/service/audit | actor null olduğunda red/rollback | CROSSCHECK_REQUIRED |
| XW-014 | Her fiziksel stok çıkışı için tek `OUT` hareketi | Unique constraint yalnız başına yeterli olmayabilir | workflow transaction | sale/dispatch çifte OUT negatif testi | DECIDED; regression test required |
| XW-015 | Aynı idempotency key + aynı request body ilk sonucu döndürür; farklı body 409 | unique key + kayıt | middleware/service | replay ve body mismatch testleri | DECIDED for sales; other commands open |

## 6. İndeks ve benzersizlik kontrol matrisi

Aşağıdaki maddeler indeks tasarımı için kontrol gereksinimidir; tümü onaylı DDL kararı sayılmaz.

| Varlık/alan | Gerekçe | Kontrol/karar |
|---|---|---|
| `users.email` | login ve kullanıcı arama | case-insensitive normalizasyon + UNIQUE kesinleştirilmeli |
| İş kodları (`lots.lot_code`, ürün kodu, üretim/parçalama emri kodu) | kullanıcıların iş koduyla araması | Her tablo için unique scope ve case sensitivity tanımlanmalı |
| FK kolonları | join ve silme/koruma ilişkileri | MySQL indeks gereksinimleri ve ORM otomatik indeksleri kontrol edilmeli |
| `stock_movements(lot_id, created_at)` | lot hareket geçmişi | gerçek liste filtreleriyle sorgu planı eşleştirilmeli |
| `inventory_balances(lot_id, location/warehouse scope)` | lot bazlı bakiye | şemada konum alanı varsa unique bileşik anahtar; yoksa yeni alan eklenmemeli |
| `lot_genealogy_edges(source_lot_id, target_lot_id, relation_type)` | ileri/geri izleme | tekrar edge kuralı ve miktar satırlarının birleştirme semantiği belirlenmeli |
| `idempotency_records` | key tekrarlarını engelleme | key scope (actor + endpoint/operation) ve saklama süresi açıkça tanımlanmalı |
| `recall_lots(recall_id, lot_id)` | aynı recall içinde aynı lotu tekrarlamama | UNIQUE bileşik anahtar adayı |
| `product_prices(product_id, valid_from, valid_to)` | tarihli fiyat araması | aralık çakışması unique indeksle tek başına çözülemez; transaction/service doğrulaması gerekir |
| `audit_events(request_id, created_at)` | korelasyon ve inceleme | kullanım sıklığı ve retention ihtiyacıyla doğrulanmalı |

## 7. DTO alan eşleştirme kapsamı

Cilt 1.16 kritik nullable alanları listeler; bu ciltteki hedef her endpoint request/response alanının tamamının tablo kolonları ve iş kurallarıyla eşleşmesidir.

| DTO grubu | Kaynak endpoint grubu | Gerekli çapraz kontrol | Durum |
|---|---|---|---|
| Auth/user | `/auth/*` | token alanları, role alanları, aktiflik, parola alanlarının asla dönmemesi | Cilt 1.20 ile birlikte kontrol |
| Catalog | products, units, suppliers, customers, prices | writable alanlar, server-managed alanlar, nullable fields | CROSSCHECK_REQUIRED |
| Inventory/lots | lots, receipts, adjustments, balances, movements | decimal string, lot policy, movement direction, actor | BLOCKER: expiry/units |
| Production | orders, inputs, service costs, outputs, complete/cancel | state bazlı zorunlu alanlar ve transaction yanıtı | CROSSCHECK_REQUIRED |
| Butchering | orders, inputs, outputs, waste, complete | fire ayrı DTO/table; allocation method koşulları | BLOCKER: maliyet/tolerans |
| Sales | sales, sale lines, void | Idempotency-Key, lot qty, response replay | CROSSCHECK_REQUIRED |
| Shipments | shipments, lines, dispatch | dispatch tek OUT sahibi, satış ilişkisi | CROSSCHECK_REQUIRED |
| Traceability/recall | trace queries, recall start/close/unblock, customer impacts | genealogy miktarları, block/unblock ve contact state | BLOCKER: state/permission çapraz kontrol |
| Audit/AI | audit events, predictions | actor, request_id, prediction type fields, secret exclusion | CROSSCHECK_REQUIRED |

## 8. Açık kararlar ve blokaj kaydı

| ID | Konu | Karar/kanıt ihtiyacı | Kodlama devri öncesi mi? |
|---|---|---|---|
| BL-01 | Son tüketim tarihi uygulanabilirlik ölçütü | Ürün tipi/ürün kartı konfigürasyonu veya başka onaylı policy; alan ekleme gerekiyorsa ayrıca karar | Evet |
| BL-02 | Fire `BY_VALUE` maliyet formülü | Fire maliyetinin açık zarar mı yoksa değere sahip çıktılara dağıtım mı olduğu; sayısal örnek | Evet |
| BL-03 | Ağırlık toleransı | Kabul edilebilir farkın sayısal değeri veya sıfır tolerans kararı ve gerekçe | Evet |
| BL-04 | Ağırlık birimleri | İzinli birimler, dönüşüm kaynağı, yuvarlama/hassasiyet ve bilinmeyen dönüşüm hatası | Evet |
| BL-05 | Çoklu input lot/fire ilişkisi | Fire kaydı tek input lota mı bağlanır, yoksa kaynak lotlara dağıtım tablosu gerekir mi? | Evet |
| BL-06 | Enum/state registry | Cilt 1.19'daki tüm durumlar, API DTO'ları ve ERD değerleriyle karşılaştırılmalı | Evet |
| BL-07 | Web/Android token politikası | Cilt 1.20 kararları: web taşıma/CSRF, Android secure storage, parola/rate limit, kullanıcı disable | Evet |
| BL-08 | Health contract | Liveness/readiness yolu, erişim, response ve dependency check ayrımı | Evet |
| BL-09 | Idempotency kapsamı | Satış dışındaki kritik POST'lar için key veya deterministik state-conflict seçimi | Evet |
| BL-10 | Başarı yanıtı `request_id` | Header/body standardı ve OpenAPI testleri | Evet |
| BL-11 | Recall unblock | Endpoint, permission, audit, replay ve lot satışa açılma kuralı | Evet |
| BL-12 | Düzeltme/ters kayıt | Her tamamlanmış operasyon için kaynak kayda bağlı reversal/correction kuralları | Evet |
| BL-13 | Constraint/index gerçek doğrulaması | ORM metadata ve üretilen DDL ile doküman fark raporu | Migration öncesi |

## 9. Gerçek çapraz kontrol çalıştırma planı (kodlama LLM'sine talimat)

Kodlama LLM'si, proje sahibi migration'a açık onay vermeden önce yalnızca dokümantasyon/analiz çıktısı üretebilir. Migration üretmeden önce:

1. Cilt 1.2 ve 1.16'daki tablo/kolonları makine tarafından okunabilir bir listeye dönüştür.
2. Cilt 1.3/1.4 request ve response DTO alanlarını OpenAPI schema ile karşılaştır.
3. SQLAlchemy metadata veya migration'sız schema representation üretip kolon tipi, nullability, FK, unique, check ve index'leri karşılaştır.
4. Her farkı `missing_in_erd`, `missing_in_dto`, `type_mismatch`, `nullable_mismatch`, `constraint_mismatch`, `enum_mismatch` gibi sabit kategorilerle raporla.
5. Kaynak belgeyle çelişen alanı otomatik değiştirme; kaynak kararını ve önerilen düzeltmeyi raporla.
6. Çıktıda dosya/başlık/alan referansı, etki, önerilen karar ve test gereksinimi bulunmalı.
7. BL-01–BL-13 kapanmadan ve proje sahibi nihai çapraz kontrol özetini onaylamadan migration dosyası oluşturma veya DB'ye bağlanarak şema değiştirme.

## 10. Kabul ölçütleri

- [ ] Cilt 1.2'nin bütün tabloları tam kolon envanteriyle listelenmiş.
- [ ] Cilt 1.3/1.4'teki tüm endpoint DTO'ları alan alan eşleştirilmiş.
- [ ] DB nullability ile request required/nullable semantiği ayrı ayrı belgelenmiş.
- [ ] Her FK, UNIQUE, CHECK ve index için gerekçe ve kaynak gösterilmiş.
- [ ] Cilt 1.19 state registry ile DB state alanları ve API enum'ları aynı.
- [ ] Fire, expiry, unit conversion, weight tolerance ve allocation formülleri için açık karar kalmamış.
- [ ] OpenAPI/ORM/DDL çapraz kontrol raporu üretilmiş; her fark çözülmüş veya açıkça onaylı kapsam dışı bırakılmış.
- [ ] Proje sahibine migration öncesi değişiklik ve risk özeti sunulmuş.
- [ ] Migration üretimi için ayrıca açık onay alınmış.

## 11. Bu cildin sonucu

**Durum: CROSSCHECK TASLAĞI HAZIR; TAM KAPSAMLI DOĞRULAMA VE KODLAMA DEVRİ İÇİN HENÜZ HAZIR DEĞİL.** Bu cilt var olan tasarımın açıklarını görünür kılar; gerçek OpenAPI/ORM/DDL fark kontrolü ve BL-01–BL-13 kararları hâlâ gereklidir.

**Migration veya veritabanı oluşturma/değiştirme yetkisi vermez.**
