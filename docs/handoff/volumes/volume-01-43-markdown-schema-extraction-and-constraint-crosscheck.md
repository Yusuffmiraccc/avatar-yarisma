# Cilt 1.43 — Markdown Şema Ayrıştırma ve Constraint Cross-check

**Tarih:** 22 Ekim 2026  
**Önceki cilt:** Cilt 1.42 — ERD Şema Envanteri ve Fiziksel Şema Kanıtı  
**Durum:** Kaynak doküman statik ayrıştırması; migration veya DB değişikliği izni değildir.  
**Karar:** Migration readiness **NOT READY**.

## 1. Amaç

Cilt 1.42'de belirlenen sonraki adım, Cilt 1.2 içindeki tablo/alan/tip/nullability/PK/FK/index/kısıt açıklamalarını kaynak bağlamında daha sistematik biçimde çıkarmaktı. Cilt 1.43 bu amaçla Markdown tablo bloklarını, başlık/inline tablo adaylarını ve kısıt ifadelerini ayrı manifestlere ayırır.

Bu çıktı bir SQL şeması veya ORM modeli değildir. Ayrıştırma, kaynak metinde görülen ifadeleri işaretler; bunların fiziksel MySQL şemasına birebir karşılık geldiğini tek başına kanıtlamaz.

## 2. Statik ayrıştırma özeti

- Markdown tablo bloğu sayısı: **9**
- Markdown tablo satırı sayısı: **74**
- ERD entity listesi ve şema metninden izlenen tablo adayı: **29**
- PK/FK/UNIQUE/CHECK/INDEX/DEFAULT kategorilerinde bulunan metinsel aday ifade: **135**

Bu sayılar doküman ayrıştırma ölçümleridir; fiziksel tablo, kolon veya DB constraint sayısı değildir.

## 3. Oluşturulan manifestler

### 3.1 `schema-markdown-table-row-inventory-v1.43.csv`

Cilt 1.2 içindeki Markdown tablolarının satırlarını kaynak başlığı, yaklaşık satır numarası ve orijinal hücrelerin JSON gösterimiyle listeler. Her satır `MARKDOWN_TABLE_ROW; NOT AUTOMATICALLY A DB COLUMN` olarak işaretlidir; çünkü dokümandaki her tablo satırı veritabanı sütunu olmayabilir.

### 3.2 `schema-table-detail-crosscheck-v1.43.csv`

Cilt 1.2 başlıkları ve satır içi şema tanımlarından çıkarılan tablo adı adaylarını listeler. `physical_table_verified=NO` kalır; fiziksel tablo adı, kolon listesi ve constraint eşleştirmesi manuel onay bekler.

### 3.3 `schema-constraint-candidates-v1.43.csv`

PK, FK, UNIQUE, CHECK, INDEX ve DEFAULT gibi kısıt ifadelerinin kaynak satırlarını listeler. Bu manifest bir DDL üretmek için doğrudan kullanılmamalıdır: metinsel bir `FK` ifadesi gerçek foreign key constraint'i olarak tanımlanmış olsa bile, hedef tablo/kolon, nullable davranışı ve silme/güncelleme kuralı ayrıca doğrulanmalıdır.

### 3.4 `schema-markdown-extraction-summary-v1.43.json`

Ayrıştırma sayıları ve doğrulama sınırlarını makine tarafından okunabilir biçimde kaydeder.

## 4. Cross-check yöntemi

Her tablo adayı için aşağıdaki doğrulama adımları gerekir:

1. Kaynak başlığının gerçekten fiziksel tablo tanımı olup olmadığını doğrula.
2. Alan adını, MySQL tipini, NULL/NOT NULL, default ve açıklamayı tek bir satıra çıkar.
3. `id`, bileşik PK veya doğal anahtar gibi PK davranışını doğrula.
4. Her FK için kaynak kolon, hedef tablo/kolon ve `ON DELETE`/`ON UPDATE` davranışını doğrula; kaynakta yoksa tahmin etme.
5. UNIQUE, CHECK ve indeksleri ayrı kaydet; uygulama katmanı kuralıyla DB kısıtını karıştırma.
6. Aynı tablo/alanın Cilt 1.3 DTO'ları, Cilt 1.5 workflow'ları, Cilt 1.9 izinleri ve Cilt 1.21 error/idempotency kurallarıyla tutarlı olup olmadığını kontrol et.
7. Her uyuşmazlıkta kanonik karar kaydına bağlan; yeni karar gerekiyorsa kullanıcı onayı iste.

## 5. Önemli açık konular

- Cilt 1.2'deki tüm şema tanımlarının eksiksiz ve tek anlamlı bir tablo/kolon envanterine dönüştürülmesi henüz doğrulanmadı.
- Bazı ilişkiler ERD'de kavramsal olarak gösterilir; bunların fiziksel FK kolonları ve referential actions ile eşleşmesi ayrıca doğrulanmalı.
- SQLAlchemy metadata, gerçek MySQL schema ve migration çıktısı ile karşılaştırma yapılmadı.
- Endpoint/DTO/workflow/test parity ve Cilt 1.41'deki `waste-records` izin onayı açık kalıyor.
- WF-01–WF-10 kararlarının tümü kapatılmış değil.

## 6. Migration öncesi kapı

Migration oluşturulabilmesi için en az:
- kaynakla doğrulanmış fiziksel tablo ve kolon envanteri,
- PK/FK/UNIQUE/CHECK/index/default kayıtları,
- DTO–DB ve workflow–constraint crosswalk,
- açık yetki ve iş akışı kararlarının çözümü,
- proje sahibinin ayrı ve açık migration onayı

gereklidir.

## 7. Sonuç

Cilt 1.43, Cilt 1.2'deki yapısal metni daha denetlenebilir manifestlere ayırır. Otomatik çıkarımlar **aday** statüsündedir; gerçek şema olarak sunulmaz.

**Migration readiness: NOT READY.** Bu ciltte Alembic migration dosyası oluşturulmadı ve veritabanı değiştirilmedi.
