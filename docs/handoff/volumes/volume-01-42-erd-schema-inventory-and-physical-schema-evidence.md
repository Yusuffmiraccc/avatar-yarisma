# Cilt 1.42 — ERD Şema Envanteri ve Fiziksel Şema Kanıtı

**Tarih:** 22 Ekim 2026  
**Önceki cilt:** Cilt 1.41 — Endpoint Sözleşme Kanıtı ve Yetki Boşluğu  
**Durum:** Statik dokümantasyon incelemesi; migration/DB izni değildir.  
**Karar:** Migration readiness **NOT READY**.

## 1. Amaç

Cilt 1.42'nin amacı, `volume-01-2-erd-and-data-schema.md` dosyasındaki kavramsal ERD içeriğini fiziksel veritabanı şeması gibi yanlış yorumlamamak; görülebilen varlık adlarını, olası alan/identifier adlarını ve çözülmemiş fiziksel şema kararlarını ayrı kayıtlara çıkarmaktır.

Bu çalışma yalnızca mevcut doküman metnini inceler. Çalışan backend, ORM metadata, MySQL veritabanı veya migration dosyaları üzerinde doğrulama yapılmamıştır.

## 2. Bulgular

### 2.1 ERD görünümü

Kaynak dosyadaki Mermaid ERD'de **29 kavramsal entity adı** görünür:

- `USERS`
- `SALES`
- `PRODUCTION_ORDERS`
- `BUTCHERING_ORDERS`
- `PRODUCTS`
- `LOTS`
- `SUPPLIERS`
- `CUSTOMERS`
- `SHIPMENTS`
- `PRODUCT_PRICES`
- `UNITS`
- `UNIT_CONVERSIONS`
- `INVENTORY_BALANCES`
- `STOCK_MOVEMENTS`
- `PRODUCTION_INPUTS`
- `PRODUCTION_OUTPUTS`
- `PRODUCTION_SERVICE_COSTS`
- `BUTCHERING_INPUTS`
- `BUTCHERING_OUTPUTS`
- `BUTCHERING_WASTE_RECORDS`
- `LOT_GENEALOGY_EDGES`
- `SALE_LINES`
- `SHIPMENT_LINES`
- `RECALLS`
- `RECALL_LOTS`
- `RECALL_CUSTOMER_IMPACTS`
- `LOT_BLOCKS`
- `AUDIT_EVENTS`
- `ML_PREDICTIONS`

Bunlar **kavramsal ERD entity adlarıdır**. Fiziksel MySQL tablo adları oldukları tek başına kanıtlanmış değildir. Kaynak dokümanın sonraki bölümlerinde bazı tablo alanları, tipler ve kısıtlar Markdown olarak tanımlanmıştır; bu nedenle “fiziksel şema yok” demek yerine, mevcut doküman şemasının tüm alan ve kısıtlarıyla sistematik biçimde çapraz kontrol edilmediğini söylüyoruz.

### 2.2 SQL şeması kanıtı

Kaynak dokümanda tablo alanlarının ve tiplerinin bir bölümü Markdown tabloları ve satır içi şema tanımlarıyla belgelenmiştir. Önceki Cilt 1.38 incelemesinde fenced SQL içinde `CREATE TABLE` tanımı bulunmadığı kaydedilmişti. Bu durum tek başına şemanın hiç tanımlanmadığı anlamına gelmez; ancak Markdown sözleşmesinin eksiksiz ve tutarlı bir fiziksel tablo/kolon/constraint envanterine dönüştürüldüğünü de kanıtlamaz. Bu cilt, belirsiz alanları tahmin ederek doldurmaz.

### 2.3 Identifier adayları

Kaynak dosyadaki backtick içindeki 239 benzersiz ifade ayrı manifestte listelenmiştir. Bunlar otomatik olarak sütun sayılmaz: bazıları alan, enum, tablo adı, API terimi, örnek veya teknik kavram olabilir. Her birinin sınıflandırılması kaynak bağlamı üzerinden elle doğrulanmalıdır.

### 2.4 Kritik alan kartları

Cilt 1.40'taki kritik alan kartları yeni bir kayıt dosyasına aktarıldı. Her satırın `physical_schema_proven=NO` durumu korunur. Alan kartının varlığı, alanın gerçek veritabanında bulunduğu anlamına gelmez.

Özellikle aşağıdaki alanlar fiziksel şema ve DTO/workflow kaynakları arasında doğrulanmalıdır:
- `products.requires_expiry_date`
- `lots.expiry_date`
- `butchering_waste_records.reason_code`
- `butchering_waste_records.allocated_cost`

Bunlar önceki ciltlerde işaretlenmiş doğrulama adaylarıdır; bu rapor yeni bir alan varlığı iddiasında bulunmaz.

## 3. Oluşturulan manifestler

1. `manifests/schema-table-candidate-register-v1.42.csv` — ERD'den görülebilen kavramsal entity adayları.
2. `manifests/schema-identifier-candidates-v1.42.csv` — backtick identifier adayları; sütun olarak doğrulanmamıştır.
3. `manifests/schema-critical-field-register-v1.42.csv` — Cilt 1.40 kritik alan kartlarının doğrulama durumuyla aktarımı.
4. `manifests/schema-open-gap-ledger-v1.42.csv` — fiziksel şemayı kapatmak için gerekli eksikler.

## 4. Migration öncesi kontrol matrisi

| Konu | Cilt 1.42 sonucu | Gerekli kanıt |
|---|---|---|
| Fiziksel tablo adları | OPEN | Kanonik fiziksel şema veya onaylı mapping |
| Sütunlar ve tipler | OPEN | Her tablo için alan/tip/nullability listesi |
| PK/FK | OPEN | Constraint register ve ilişkilerin doğrulanması |
| Unique/index/check | OPEN | Kısıt ve indeks listesi; iş kuralı gerekçesi |
| ORM–DB parity | NOT VERIFIED | SQLAlchemy metadata ve MySQL karşılaştırması |
| API DTO–DB parity | NOT VERIFIED | Request/response DTO ile alan bazlı crosswalk |
| Workflow–constraint parity | NOT VERIFIED | WF-01–WF-10 kuralları ile DB kısıtlarının eşleştirilmesi |
| Migration dry-run | NOT RUN | Onaylı şema sonrası boş ve test DB üzerinde uygulama |

## 5. Şema kararlarında güvenli yaklaşım

- Fiziksel tablo veya alan adı kaynakta kesin değilse tahmin ederek migration'a ekleme.
- Bir ERD ilişkisinden FK kolonunun adını otomatik olarak kesin kabul etme.
- Veri tipi, precision, nullability veya default değerini genel alışkanlıklara dayanarak uydurma.
- Kritik veriler için `ON DELETE CASCADE` gibi davranışları açık onay olmadan varsayma.
- Mevcut onaylı DEC-001 veri/API kararlarını koru; bu cilt onları yeniden açmaz.
- Kavramsal adlarla fiziksel SQL isimleri farklıysa, tek bir kanonik eşleme tablosu oluştur ve kod üretimini bu tablodan yap.

## 6. Migration engelleri

Cilt 1.42 itibarıyla en az şu engeller açık kalır:
- Tam fiziksel tablo/kolon/PK/FK/index/unique/check envanteri yok.
- Cilt 1.40 kritik alanları fiziksel şema ile doğrulanmış değil.
- `waste-records` endpoint'i için Cilt 1.9 izin satırı proje sahibi onayı bekliyor.
- DTO, workflow, transaction, audit ve idempotency parity tam kapanmış değil.
- Runtime OpenAPI, ORM metadata, MySQL constraint ve otomatik test raporu mevcut değil.

## 7. Açık karar sınırı

Bu cilt yalnızca envanter ve gap ledger üretir:
- Alembic migration oluşturulmadı.
- Veritabanı oluşturulmadı veya değiştirilmedi.
- Kaynakta bulunmayan tablo, kolon, FK veya index tanımları uydurulmadı.
- Cilt 1.41'deki rol önerisi onaylanmış sayılmadı.

**Sonuç:** Cilt 1.42, fiziksel şema kanıtı eksikliğini görünür kılar; migration readiness hâlâ **NOT READY**. Sonraki adım, her adayın kanonik kaynak bağlamını tek tek doğrulamak ve proje sahibinin onaylayacağı fiziksel şema envanterini üretmektir.
