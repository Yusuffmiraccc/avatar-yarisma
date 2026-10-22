# Cilt 1.7 — Migration Planı, Veritabanı Kısıtları ve Seed/Test Verisi

**Durum:** Uygulama öncesi veritabanı uygulama planı  
**Tarih:** 22 Ekim 2026  
**Veritabanı:** MySQL 8.4 LTS  
**ORM/migration:** SQLAlchemy 2.x + Alembic  
**Bağlı belgeler:** Cilt 0, Cilt 1, Cilt 1.2, Cilt 1.3, Cilt 1.4, Cilt 1.5, Cilt 1.6, DEC-001, ADR-001

> **Önemli sınır:** Bu belge, Cilt 1.2 ERD'sini migration planına dönüştürmek için uygulama kurallarını ve sıralamayı tanımlar. Cilt 1.2'deki her tablo/kolon için kesin DDL'nin yerine geçmez. Mevcut belgelerde çelişki veya açık karar varsa migration kodu yazılmadan önce o karar kapatılmalıdır. Bu belge, onaylanmamış WF-01–WF-10 kararlarını sessizce kesinleştirmez.

## 1. Amaç

- Veritabanının yeni bir ortamda tekrarlanabilir biçimde kurulmasını sağlamak.
- Şema değişikliklerini Alembic revision'larıyla izlemek.
- FK, unique, check ve index kısıtlarıyla kritik bütünlüğü DB seviyesinde korumak.
- Seed verisini test/demo başlangıç verisinden ayırmak.
- Migration ve seed işlemlerinin stok hareketi, lot genealogy ve recall kurallarını ihlal etmesini önlemek.

## 2. Migration ilkeleri

1. **Migration tek doğruluk kaynağıdır.** Geliştirici veritabanında elle tablo değiştirip bunu migration dışında bırakamaz.
2. **Her migration sürümlenir.** Alembic revision dosyası, önceki revision'a bağlı ve Git'te izlenebilir olmalıdır.
3. **Migration tekrar üretilebilir olmalıdır.** Aynı revision zinciri boş MySQL 8.4 veritabanına uygulandığında aynı şemayı oluşturmalıdır.
4. **Şema ve seed ayrıdır.** Migration yalnızca zorunlu şema/metadata değişikliklerini yapar. Demo işletme verisi ayrı komutla yüklenir.
5. **Yıkıcı değişiklikler açıkça ele alınır.** Kolon drop/rename, tip daraltma veya veri kaybı yaratabilecek değişiklikler otomatik ve habersiz yapılmaz.
6. **FK'ler rastgele kapatılmaz.** `FOREIGN_KEY_CHECKS=0` genel migration çözümü olarak kullanılmaz.
7. **Para/miktar türleri sabittir.** Para `DECIMAL(19,4)`, ağırlık/miktar `DECIMAL(19,6)`; API'de string temsili.
8. **Zaman standardı tutarlıdır.** Anlık zamanlar UTC; date-only alanlar `DATE`. MySQL `DATETIME` timezone saklamadığından UTC yazma/okuma politikası uygulama katmanında açık olmalıdır.
9. **Hareket geçmişi korunur.** Stock movement, audit ve kritik iş kayıtları sıradan migration veya seed temizliğiyle silinmez.
10. **Migration transaction davranışı incelenir.** MySQL DDL işlemlerinin tümü uygulama transaction'ı gibi geri alınabilir varsayılmaz; migration başarısızlığında ortamın durumu kontrol edilir.

## 3. Revision planı

Aşağıdaki sıra öneridir. Kesin revision dosyaları Cilt 1.2 ERD ve WF kararları kapatıldıktan sonra üretilmelidir.

| Sıra | Revision konusu | İçerik | Bağımlılık |
|---|---|---|---|
| M001 | Kimlik ve referans verileri | users/roles/permissions gerekliyse; products, units, categories, suppliers, services gibi temel kataloglar | Onaylı ERD |
| M002 | Lot ve stok temeli | lots, lot receipts/acceptances, stock movements, lot balances, blokaj alanları/ilişkileri | M001 |
| M003 | Üretim ve maliyet | production orders, input/output satırları, external service cost, cost snapshot alanları | M001–M002 |
| M004 | Parçalama | butchering orders, cut/byproduct/waste satırları, weight balance, allocation data | M001–M002 |
| M005 | Genealogy | lot genealogy bağlantıları ve miktar/birim alanları | M002–M004 |
| M006 | Satış ve sevkiyat | sales, sale lines, shipments, shipment lines, idempotency records | M001–M002 |
| M007 | Recall ve aksiyonlar | recalls, affected lots/records, communication/action logs | M002, M005, M006 |
| M008 | Audit ve AI | audit events, prediction records/model version metadata | Modül gereksinimleri |
| M009 | Performans ve arama indexleri | sorgu planı/testiyle doğrulanmış ikincil indexler | Önceki migration'lar |

**Dikkat:** Bu liste, Cilt 1.2'deki kesin tablo isimlerini değiştirme kararı değildir. Tablo adları ve ilişkiler ERD ile aynı olmalıdır. Bir tablonun birden fazla migration'a bölünmesi gerekirse bunu revision dosyası ve açıklamasıyla belgelendir.

## 4. SQLAlchemy ve Alembic yapılandırması

### 4.1 SQLAlchemy model kuralları

- SQLAlchemy 2.x typed declarative mapping (`Mapped[...]`, `mapped_column`) kullan.
- Para ve miktar kolonlarında `Numeric(precision=19, scale=4/6, asdecimal=True)` benzeri açık tanım kullan; gerçek kolon hassasiyetini alanın anlamına göre seç.
- Tarih-saat kolonlarında UTC standardını belgeleyen tutarlı tip/serializer kullan.
- FK davranışlarını açıkça belirle; kritik geçmiş kayıtlarını silen cascade davranışlarından kaçın.
- Unique constraint ve index isimlerini okunabilir, tutarlı ve deterministik seç.
- DB modelini Pydantic DTO olarak doğrudan döndürme.
- MySQL'e özgü tip/constraint davranışlarını integration testte doğrula.

### 4.2 Alembic env

- `target_metadata` tüm SQLAlchemy modellerini içermelidir.
- `DATABASE_URL` environment/config üzerinden alınır; sırlar dosyaya sabit yazılmaz.
- Migration autogenerate çıktısı gözden geçirilmeden kabul edilmez.
- Autogenerate'in her constraint, rename, index veya veri dönüşümünü doğru anlayacağı varsayılmaz.
- Migration CI adımı temiz DB'ye upgrade'i ve mümkünse desteklenen önceki revision'dan upgrade'i test eder.

### 4.3 Revision yazım kuralları

Her revision şunları içerir:
- Tek ve anlaşılır değişiklik amacı.
- `revision` ve `down_revision`.
- `upgrade()` ve uygun olduğunda `downgrade()`.
- Veri dönüşümü gerekiyorsa ön koşul, batch/işlem stratejisi ve doğrulama.
- Yıkıcı değişiklik varsa neden ve geri dönüş planı.
- İlgili test veya doğrulama komutu.

`downgrade()` veri kaybına yol açacaksa bunun güvenli olmadığı açıkça belgelenir; sadece formalite olsun diye veri silen bir downgrade yazılmaz.

## 5. DB bütünlük kısıtları

Aşağıdaki kısıtlar kavramsal gereksinimdir; kesin isim ve alanlar ERD'deki alanlara göre uygulanır.

### 5.1 Primary key ve business code

- İç ID'ler `BIGINT`; iş kodları ayrı, insan tarafından okunabilir unique alanlardır.
- `ET-2026-001`, `URT-2026-045`, `SUC-2026-045` gibi kodlar primary key değildir.
- İş kodlarının unique kapsamı (global mi, tenant/işletme bazlı mı) ERD'de açıkça belirlenmelidir. Mevcut kapsam tanımlı değilse tenant varsayımı eklenmez.

### 5.2 Foreign key ve silme politikası

- Sale line, production input/output, shipment line, genealogy edge ve recall action gibi detay satırları ana kayıtlarına FK ile bağlı olmalıdır.
- Tarihsel hareketler referans verdikleri lot ve kaynak iş kayıtları silinerek yetim bırakılmamalıdır.
- Kritik iş tablolarında genel `ON DELETE CASCADE` kullanılmamalıdır; ilişkili verinin otomatik silinmesi audit ve izlenebilirliği bozabilir.
- Katalog referansları kullanımdan sonra hard-delete yerine pasifleştirilir.
- Her FK için `ON DELETE` davranışı tasarım sırasında açıkça seçilir.

### 5.3 Unique constraints

ERD'ye göre uygulanması gereken örnekler:
- İş kodu unique (kapsamı tanımlanmış olmalı).
- Kullanıcı login/email alanı unique (normalize etme politikası belirlenmiş olmalı).
- Idempotency kaydı için kullanıcı/endpoint veya tanımlı scope + key unique.
- Genealogy edge için duplicate bağlantıyı engelleyen uygun unique anahtar veya uygulama kontrolü.
- Aynı dış belge referansının tekrar kaydı engellenecekse belge türü/tedarikçi/kod kombinasyonu unique olmalı; bu kural ürün gereksinimiyle doğrulanmalıdır.

### 5.4 Check constraints ve uygulama doğrulaması

DB seviyesinde mümkün olan kısıtlar:
- Stock movement quantity > 0.
- Hareket yönü yalnızca `IN` veya `OUT`.
- Miktar/ağırlık gibi ölçülerin geçerli pozitif veya sıfır aralığında olması.
- Durum ve enum değerlerinin izin verilen kümede olması (MySQL enum yerine string + CHECK tercih edilecekse bunun yaklaşımı standartlaştırılmalı).
- Tahsis oranı/yüzdesi tanımlı aralıkta olması.

Ancak iş kuralı karmaşıksa DB CHECK tek başına yeterli değildir. Örneğin:
- Lot bakiyesinin negatif olmaması, eşzamanlılık nedeniyle transaction/locking ile de korunmalıdır.
- Genealogy miktarlarının girdi/çıktı ile dengesi domain service ve testlerde doğrulanmalıdır.
- Bir üretim emrinin `COMPLETED` olma ön koşulları service katmanında kontrol edilir.
- Recall blokajlı lotun satışta kullanılması backend transaction içinde kontrol edilir.

### 5.5 DECIMAL, nullability ve default değerler

- Alanların `NULL` olup olmadığı iş anlamına göre kararlaştırılır; eksik bilgi ile sıfır aynı şey değildir.
- Bilinmeyen son kullanma tarihi `NULL` olabilir ancak bu, “süresi yok” anlamına geliyorsa farklı bir durum modeli gerekir.
- Fire satırının product/lot alanlarının nullable olup olmadığı WF-01 çözülmeden sabitlenmez.
- Default değerler yalnızca anlamı kesin olan alanlarda kullanılır; bilinmeyen maliyet, miktar veya tarih `0`/bugün olarak doldurulmaz.
- `DECIMAL(19,4)` ve `DECIMAL(19,6)` hassasiyetleri migration ve API contract testlerinde doğrulanır.

## 6. Index stratejisi

Önce iş sorgularını ve erişim örüntülerini belirle; her kolona otomatik index ekleme.

Beklenen sorgulara göre değerlendirilecek index grupları:
- Lot iş kodu ve lot durum/blokaj sorguları.
- Lot bazlı stock movement geçmişi, zaman sıralaması.
- Lot balance lookup.
- Üretim/parçalama emri business code ve durum filtreleri.
- Genealogy için parent/source lot ve child/output lot yönlü aramalar.
- Satış ve sevkiyat kayıtlarında tarih, market/customer ve durum filtreleri.
- Recall kaynak lotu ve etkilenen lot aramaları.
- Audit actor, entity type/id ve zaman aralığı.
- AI tahminlerinin model sürümü ve zaman bazlı raporlanması.

Index tasarımında:
- Çok kolonlu index sırası gerçek `WHERE` ve `ORDER BY` örüntüsüne göre seçilir.
- Unique constraint zaten index oluşturuyorsa aynı kolonlar için gereksiz duplicate index eklenmez.
- Büyük tablo index değişikliği için MySQL migration süresi ve kilit etkisi göz önünde bulundurulur.
- Performans iddiası `EXPLAIN` ve temsili veri ile doğrulanır.

## 7. Seed verisi ve test verisi ayrımı

### 7.1 Üç ayrı veri katmanı

**A. Reference seed**
- İlk admin rol/izin kayıtları veya sabit sözlükler gibi uygulamanın çalışması için gereken minimum veriler.
- Tekrar çalıştırıldığında mükerrer kayıt oluşturmamalıdır.
- Gerçek parola veya üretim sırrı içermez.

**B. Demo seed**
- AVATAR sunum akışını göstermek için gereken sentetik tedarikçi, ürün, lot, üretim emri, market ve hareketler.
- Sadece açıkça seçilen demo/test veritabanına yüklenir.
- Demo verisi üretim ortamına otomatik yüklenmez.

**C. Automated test fixtures**
- Unit/integration/E2E testlerinin kendi transaction'ında veya izole DB'sinde oluşturduğu kayıtlar.
- Testler birbirine bağımlı değildir; sırası değişse de çalışmalıdır.
- Test cleanup'ı yalnızca test DB'sini etkiler; kullanıcı veya demo verisini silmez.

### 7.2 Demo veri standardı

- Demo senaryosu sentetik veridir; gerçek kişisel veri veya gerçek müşteri bilgisi kullanılmaz.
- Seed kayıtları gerçek sistemdeki kayıtlarla karışmaması için `DEMO` gibi açık bir işaretle ayırt edilebilir; bu alan ERD'de yoksa yeni kolon eklemek yerine demo namespace/DB veya kayıt açıklaması gibi onaylı yöntem kullanılır.
- Kodlar sabit ve tekrar üretilebilir olmalıdır.
- Seed komutu tekrar çalıştırıldığında duplicate üretmemeli; mevcut kayıtları kontrol ederek idempotent davranmalıdır.
- Seed, stock movement ve balance kayıtlarını tutarlı biçimde birlikte oluşturmalıdır; yalnızca balance sayısını doğrudan set etmemelidir.

### 7.3 AVATAR demo veri seti

Aşağıdaki iş verileri yarışma senaryosundan gelir; bunlar üretim/teslimat test akışında korunmalıdır:

- Girdi lotu: `ET-2026-001`, 100 kg.
- Üretim emri: `URT-2026-045`.
- Bitmiş ürün lotu: `SUC-2026-045`, 85 paket.
- Market dağılımı: Market A 30 paket, Market B 25 paket, Market C 30 paket.
- Üretim maliyeti örneği: €1,543.50 toplam; 85 pakete bölündüğünde yaklaşık €18.16/paket.

**Önemli:** Bu örneklerin her birinin tüm alanları kaynak PDF'de verilmiş değildir. Seed script, eksik tedarikçi adı, tarih, son kullanma tarihi, ürün içeriği veya ikinci-tier satış gibi değerleri gerçekmiş gibi uydurmamalıdır. Gerekli alanlar için `DEMO` olarak açıkça tanımlı sentetik değer kullanılabilir ve dokümante edilmelidir.

PDF'deki parçalama örneğinde:
- 25 kg × €11.50 = €287.50.
- PDF'de ayrıca €351 toplam gösterilmiştir.
- Listelenen kesim ağırlıkları toplamı 22 kg'dır.
Seed verisi bu tutarsızlığı koruyup test etmelidir; açıklanmamış farkı otomatik düzeltmemelidir.

## 8. Seed komutu davranışı

Önerilen komut: `python -m scripts.seed_demo_data --profile avatar-demo`

Kurallar:
1. Aktif DB hedefini ve profile açıkça göster.
2. Üretim ortamı gibi işaretlenmiş DB'de demo seed'i varsayılan olarak reddet.
3. Seed öncesi gerekli migration seviyesini doğrula.
4. Seed kayıtlarını business code veya tanımlı unique anahtarla bul.
5. Aynı kayıt zaten varsa tekrar oluşturma; seed'in güncelleme yapıp yapmayacağı açıkça tanımlı olsun.
6. Herhangi bir aşama başarısız olursa seed transaction'ı rollback edilir; MySQL DDL transaction'ı gibi varsayılmaz.
7. İşlem sonunda oluşturulan/önceden var olan kayıt sayısını ve hedef DB'yi raporla; secret yazdırma.
8. Seed komutu gerçek stok movement/balance/genealogy ilişkilerini tutarlı biçimde kurar.
9. Demo senaryosunu temizlemek gerekiyorsa yalnızca izole demo DB'si yeniden oluşturulur; kritik iş kayıtları uygulama içinden topluca silinmez.

## 9. Test verisi tasarımı

### 9.1 Unit fixtures

- Decimal testleri: `Decimal("1543.50") / Decimal("85")` ve yuvarlama.
- Geçersiz durum geçişi örnekleri.
- Pozitif movement miktarı ve `IN`/`OUT`.
- Ağırlık dengesi: tam denge, izin verilen tolerans ve tolerans dışı durum.
- Maliyet tahsisi toplamı eşitliği.
- Recall genealogy ileri/geri traversal.
- Idempotency key aynı gövde ve farklı gövde durumları.

### 9.2 Integration fixtures

- MySQL 8.4 test instance veya Docker Compose servis.
- Migration zincirinin temiz DB'de uygulanması.
- FK/unique/check constraint ihlallerinin beklenen hatayı üretmesi.
- Stock movement + balance aynı transaction'da.
- Yetersiz stokta rollback.
- İki eşzamanlı satışta yalnızca birinin stok limitine kadar başarılı olması.
- Recall aktivasyonundan sonra lot satışının reddi.

### 9.3 E2E fixture

1. Demo profile ile gerekli katalog ve kullanıcılar oluşturulur.
2. `ET-2026-001` kabul edilir veya izole senaryoda tutarlı kabul hareketleriyle seed edilir.
3. `URT-2026-045` üretim emri tamamlanır.
4. `SUC-2026-045` lotu 85 paket çıkarır.
5. Market A/B/C için 30/25/30 dağılımı kayıt edilir.
6. Recall aktive edilir.
7. Traceability raporu ve blokajlı satış testi çalışır.
8. AI tahminleri ayrı test edilir; tahmin sonucu stok miktarını değiştirmez.

## 10. Migration ve seed CI kontrol listesi

CI pipeline en azından şu adımları yürütmelidir:

1. Bağımlılıkları sabitlenmiş Python ortamını kur.
2. Lint/type-check (proje araçları seçildiyse) çalıştır.
3. Unit testleri çalıştır.
4. Temiz MySQL 8.4 test DB başlat.
5. `alembic upgrade head` uygula.
6. Migration sonrası şema/constraint doğrulamalarını çalıştır.
7. Reference seed'in tekrar çalıştırılabilirliğini test et.
8. Demo seed'i izole DB'de iki kez çalıştır ve duplicate/movement tutarlılığını doğrula.
9. Integration/contract testleri çalıştır.
10. E2E demo senaryosunu çalıştır.
11. Hata durumunda logları `request_id` veya test adıyla ilişkilendir; sırları çıktılamadan raporla.

Migration testlerinde yalnızca `alembic upgrade head` başarılı olması yeterli değildir. Temel constraint'ler ve servis davranışları da doğrulanmalıdır.

## 11. Kabul ölçütleri

Cilt 1.7 uygulamaya hazır sayılmadan önce:

- Tablo ve kolon isimleri Cilt 1.2 ERD ile eşleşiyor.
- WF-01–WF-10 gibi ilgili açık kararlar durumlarıyla listelenmiş.
- Migration zinciri temiz MySQL 8.4 ortamında uygulanabiliyor.
- Kritik FK, unique, check ve index'ler tanımlı ve testli.
- Stock movement ve balance tutarlılığı DB+service testleriyle korunuyor.
- Demo seed idempotent ve yalnızca hedeflenen test/demo DB'sinde çalışıyor.
- Parçalama örneğindeki kaynak tutarsızlıklar seed/testte görünür kalıyor.
- Decimal precision, nullable alanlar ve UTC zaman davranışı contract testlerinde doğrulanıyor.
- Seed veya test temizliği gerçek/kalıcı iş kayıtlarını silemiyor.
- Yeni ortamdan demo akışına kadar kurulum adımları tekrarlanabilir.

## 12. Sonraki adım

Önerilen sonraki belge: **Cilt 1.8 — Auth, Rol/İzin Matrisi ve Güvenlik Sözleşmesi**. Bu belge, JWT, rol kapsamı, endpoint bazında izinler, admin bootstrap, parola saklama, token ömrü, logout/invalidasyon ve audit gereksinimlerini kesinleştirir.

Cilt 1.8'den önce, WF-01–WF-10 açık kararları da karar kayıtlarına işlenerek kapatılmalıdır. Özellikle stok hareketi sahipliği, fire alanları ve recall blokajı gibi konular DB constraint'leri ve API DTO'larını doğrudan etkiler.

## Revizyon 1.11 — Migration üretimi ön koşulları (yalnızca plan)

**Bu belge gerçek Alembic revision içermez. Aşağıdaki maddeler planlama ve kontrol maddeleridir.**

### Ön koşul kontrol listesi
- [ ] Cilt 1.2 tablo/kolon/nullable/unique/FK/check/index listesi son ERD ile karşılaştırıldı.
- [ ] Fire ölçüm satırı ile stokta izlenen çıktı satırı ayrımı net; nullability DTO ile eşleşiyor.
- [x] Satış/sevkiyat stok sahipliği kararı (WF-03) kullanıcı tarafından onaylandı: dispatch tek `OUT/SHIPMENT` üretir; satış OUT üretmez.
- [ ] Enum, permission, error, nullable ve side-effect registry tabloları Cilt 1.2–1.9 ile son kez eşleştirildi.
- [ ] Üretim tüketiminin tamamlama anında yazıldığı, `IN_PROGRESS` sırasında stok düşülmediği doğrulandı.
- [ ] Düzeltme/ters kayıt ilişki alanları ve kaynak işlem bağlantısı son şemada onaylandı.
- [ ] Ağırlık toleransı sayısal olarak uydurulmadı; konfigürasyon/işletme kararı açıkça `TBD` veya onaylı değer.
- [ ] Her kritik komut için idempotency/state-conflict davranışı belirlendi.
- [ ] Error-code ve permission registry, endpoint/DTO sözleşmesiyle aynı.
- [ ] MySQL 8.4 desteklediği constraint/index davranışları hedef sürümde doğrulanacak.
- [ ] Temiz DB upgrade ve rollback/backup stratejisi migration tasarımıyla birlikte gözden geçirilecek.
- [ ] Proje sahibinden migration dosyası üretimi için ayrı, açık onay alındı.

### Seed/test veri beklentileri
Seed ve test senaryoları `ET-2026-001` → `URT-2026-045` → `SUC-2026-045` akışını, 85 paket çıktısını, Market A/B/C için 30/25/30 sevkiyatı, fire ölçüm satırını, recall blokajını, düzeltme/ters kayıt örneğini ve beklenen lot bakiyelerini içermelidir. Her senaryoda ledger toplamı ile balance eşitliği doğrulanır. PDF'deki kuzu maliyeti/ağırlık toplamı tutarsızlığı sessizce düzeltilmez; ayrı test/rapor notu olarak korunur.

