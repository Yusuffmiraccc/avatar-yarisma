# Cilt 1.6 — Backend Uygulama Planı ve Modül Sınırları

**Durum:** Geliştirme planı; bağlı kararlar onaylı, açık kararlar ayrıca işaretlidir  
**Tarih:** 22 Ekim 2026  
**Teknoloji:** Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PyMySQL, MySQL 8.4 LTS  
**Bağlı belgeler:** Cilt 0, Cilt 1, Cilt 1.2, Cilt 1.3, Cilt 1.4, Cilt 1.5, DEC-001, ADR-001

## 1. Amaç ve kapsam

Bu cilt, onaylanmış gereksinimleri ve API/iş akışı sözleşmelerini FastAPI backend'inde uygulanabilir modül sınırlarına ve sıralı geliştirme adımlarına dönüştürür.

Backend'in sorumlulukları:

- Android ve web istemcilerine REST/JSON API sağlamak.
- MySQL üzerinde merkezî iş verisini ve stok hareketlerini yönetmek.
- Yetkilendirme, iş kuralları, veri doğrulama ve audit davranışını uygulamak.
- Üretim, parçalama, satış, sevkiyat ve recall süreçlerini tutarlı transaction sınırlarında yürütmek.
- AI tahminlerini operasyonel doğruluk kaynağından ayrı sunmak.
- OpenAPI ve contract testleriyle istemciler arasındaki sözleşmeyi doğrulamak.

Backend'in sorumluluğunda olmayanlar:

- Android arayüzü veya web paneli bileşenleri.
- Android ya da web istemcisinin doğrudan MySQL'e bağlanması.
- AI tahmininin stok bakiyesi, lot genealogy veya recall kapsamını belirlemesi.
- İlk sürümde çevrimdışı satış kuyruğu ve sonradan senkronizasyon.
- Kaydı olmayan ikinci-tier market satışlarının varsayılması.

## 2. Mimari kurallar

1. **İstemci → FastAPI → MySQL.** İstemciler MySQL'e doğrudan erişemez.
2. **İnce API katmanı.** Endpoint fonksiyonları HTTP/JSON, kimlik doğrulama, şema ve yanıt dönüşümüyle sınırlı kalır; iş kuralları endpoint içine dağılmaz.
3. **Servis katmanı iş kurallarının sahibidir.** Stok ve maliyet kuralları tek bir yerde uygulanır.
4. **Repository katmanı opsiyonel ve amaçlıdır.** Sadece SQLAlchemy erişimini soyutlamak gerçekten okunabilirlik veya tekrar kullanım sağlıyorsa eklenir. Her tabloya mekanik bir repository oluşturmak zorunlu değildir.
5. **Transaction sınırı use-case/servis komutundadır.** Birden çok servisin aynı iş işlemini oluşturduğu durumda transaction sahibi açıkça belirlenir.
6. **MySQL transaction'ları kısa tutulur.** Ağ çağrısı, ML tahmini veya uzun hesaplama DB kilitleri tutulurken yapılmaz.
7. **Tüm kritik doğrulamalar backend'de tekrar yapılır.** İstemci tarafındaki kontroller yalnızca kullanıcı deneyimi içindir.
8. **Hassas iş kayıtları fiziksel olarak silinmez.** İptal, ters kayıt veya düzeltme kullanılır.
9. **Para ve miktarlar float ile hesaplanmaz.** Python tarafında `Decimal`; MySQL'de DECIMAL; JSON'da string temsili kullanılır.
10. **Enum ve hata sözleşmesi ortak kaynaktan yönetilir.** Cilt 1.3 ve 1.4 ile uyuşmayan bağımsız bir enum veya error code icat edilmez.

## 3. Önerilen dizin yapısı

Aşağıdaki yapı ilk sürüm için yeterince modülerdir; aşırı katmanlı veya mikroservis tabanlı bir yapı önerilmez.

```text
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── deps.py
│   │   ├── router.py
│   │   └── v1/
│   │       ├── router.py
│   │       ├── auth.py
│   │       ├── catalog.py
│   │       ├── suppliers.py
│   │       ├── inventory.py
│   │       ├── production.py
│   │       ├── butchering.py
│   │       ├── sales.py
│   │       ├── shipments.py
│   │       ├── traceability.py
│   │       ├── recalls.py
│   │       ├── ai_predictions.py
│   │       └── audit.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── errors.py
│   │   ├── logging.py
│   │   └── permissions.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── health.py
│   ├── models/
│   │   ├── user.py
│   │   ├── catalog.py
│   │   ├── lot.py
│   │   ├── stock_movement.py
│   │   ├── production.py
│   │   ├── butchering.py
│   │   ├── sale.py
│   │   ├── shipment.py
│   │   ├── recall.py
│   │   ├── genealogy.py
│   │   ├── audit.py
│   │   └── ai_prediction.py
│   ├── schemas/
│   │   ├── common.py
│   │   ├── auth.py
│   │   ├── catalog.py
│   │   ├── inventory.py
│   │   ├── production.py
│   │   ├── butchering.py
│   │   ├── sales.py
│   │   ├── shipments.py
│   │   ├── traceability.py
│   │   ├── recalls.py
│   │   └── ai_predictions.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── inventory_service.py
│   │   ├── production_service.py
│   │   ├── butchering_service.py
│   │   ├── sales_service.py
│   │   ├── shipment_service.py
│   │   ├── traceability_service.py
│   │   ├── recall_service.py
│   │   ├── costing_service.py
│   │   ├── audit_service.py
│   │   └── ai_prediction_service.py
│   ├── ml/
│   │   ├── loader.py
│   │   ├── features.py
│   │   ├── prediction.py
│   │   └── metrics.py
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       ├── integration/
│       ├── contract/
│       └── e2e/
└── scripts/
    ├── seed_demo_data.py
    └── create_admin.py
```

### 3.1 Dizin yapısı için notlar

- Bu ağaç bir başlangıç önerisidir; mevcut Cilt 1.2 veri modeliyle birebir aynı dosya sayısını gerektirmez.
- `models/` SQLAlchemy kalıcılık modellerini, `schemas/` Pydantic API DTO'larını ifade eder. Bunlar birbirinin yerine kullanılmamalıdır.
- İş alanı sayısı arttığında paketler `domains/inventory/` gibi dikey dilimlere taşınabilir; ilk aşamada basit yapı yeterlidir.
- `scripts/` içindeki seed verisi sadece demo/test amaçlıdır. Üretim veritabanına otomatik örnek veri yüklenmemelidir.
- Gerçek sırlar `.env` dosyasına yazılsa bile Git'e eklenmemelidir; `.env.example` yalnızca değişken adları ve sahte örnekler içerir.

## 4. Katmanların sorumlulukları

| Katman | Sorumluluk | Yapmaması gereken |
|---|---|---|
| API/router | HTTP status, request/response DTO, dependency ve permission çağrısı | Maliyet/lot/stock iş kuralını kendi içinde hesaplamak |
| Pydantic schemas | Alan tipi, format, aralık ve DTO doğrulaması | Veritabanı transaction'ı veya stok bakiyesi güncellemek |
| Services/use cases | İş kuralı, geçiş doğrulaması, transaction koordinasyonu | HTTP request nesnesine gereksiz bağımlılık |
| SQLAlchemy models | Tablo, ilişki ve DB seviyesindeki kısıtlar | API yanıtı olarak doğrudan dışarı sızmak |
| DB/session | Engine, session ve transaction yaşam döngüsü | İş kurallarını sahiplenmek |
| Core/security | JWT, parola hash, izinler, hata zarfı, config/logging | Domain'e özel hesaplamaları barındırmak |
| ML module | Feature dönüşümü, model yükleme, tahmin ve metrik | Stok hareketi/recall/gerçek maliyet yazmak |
| Tests | İş kuralları ve entegrasyon sözleşmelerini doğrulamak | Üretim kodunun gizli bir kopyasını oluşturmak |

## 5. Veri tabanı ve transaction standardı

### 5.1 Session yaşam döngüsü

- Her HTTP isteği için kontrollü SQLAlchemy session açılır ve kapatılır.
- Read-only endpoint'lerde gereksiz write transaction açılmaz.
- Yazma use-case'i transaction'ın sahibi olur.
- Transaction içinde exception oluşursa rollback zorunludur.
- Endpoint, service ve repository katmanlarının her biri bağımsız `commit()` çağırmaz. Commit kararı use-case sınırında tek noktada verilir.
- DB session nesnesi global değişkende paylaşılmaz.

### 5.2 Kritik yazma komutlarının transaction kapsamı

| Komut | Aynı transaction'da bulunması gereken etkiler |
|---|---|
| Lot kabulü | Lot/kabul kaydı, `IN` movement, lot balance, audit |
| Üretim tamamlama | Girdi `OUT`, çıktı `IN`, genealogy, maliyet snapshot'ı, balance, emir durumu, audit |
| Parçalama tamamlama | Girdi `OUT`, kesim/yan ürün `IN`, genealogy, maliyet tahsisi, ağırlık dengesi, durum, audit |
| Satış oluşturma | Idempotency kontrol/sonucu, satış ve satırları, audit; **stok movement/balance etkisi yok** |
| Sevkiyat dispatch | Sevkiyat durumu, tek `OUT/SHIPMENT` movement, balance azaltımı, audit ve idempotency sonucu |
| Recall aktivasyonu | Recall durumu, etkilenen lot blokajları veya güvenilir activation job/outbox, audit |
| Düzeltme/ters kayıt | Ters/düzeltme kaydı, karşı hareketler, balance, kaynak kayda bağlantı, audit |

Recall aktivasyonu senkron mu yoksa outbox/worker ile mi yapılacağı WF-05 kararı kesinleşene kadar açık tasarım noktasıdır.

### 5.3 Stok bakiyesi ve movement ledger

- Hareket geçmişi değiştirilemez; correction/reversal yeni kayıt olarak eklenir.
- Her movement miktarı pozitif, yönü `IN` veya `OUT` olur.
- Movement ve güncel bakiye aynı transaction'da güncellenir.
- Lot balance tablosu performans için kullanılabilir; ledger geçmişin denetim kaynağıdır.
- Bakiye doğrudan SQL update ile değiştirilmez; hareket oluşturan tek bir inventory service üzerinden değiştirilir.
- Eşzamanlı tüketim işlemleri aynı lot bakiyesini tutarlı biçimde kilitlemelidir.
- Bakiye ile ledger arasında mutabakat testi bulunmalıdır.

## 6. Modül sınırları ve bağımlılık yönü

Önerilen bağımlılık:

`API → Service/Use Case → Domain rules + DB access`

İş alanı servisleri gerektiğinde ortak inventory/costing/audit servislerini kullanır; ortak servisler production veya sales API router'ına bağımlı olmaz.

### 6.1 Modüller

**Auth & Permissions**
- Login, access token, current user, rol ve izin kontrolü.
- İlk roller: `ADMIN`, `OPERATOR`, `SALES`, `TRACEABILITY_MANAGER`, `VIEWER`.
- Rol adlarının izinleri Cilt 1.3 permission matrix ile eşleştirilmelidir.
- Refresh/logout davranışı Cilt 1.3'te açıkça tanımlanmamışsa burada yeni davranış varsayılmaz.

**Catalog**
- Ürün, kategori, birim, dönüşüm, hizmet ve tedarikçi gibi referans veriler.
- İşlem geçmişinde kullanılan birim/kodlar geriye dönük anlam değiştirecek biçimde düzenlenmemelidir.
- Silme yerine pasifleştirme, ilişkili kayıtların bütünlüğünü korumalıdır.

**Inventory**
- Lot kabulü, kullanılabilir miktar, movement ledger, balance ve lot blokajı.
- Stock movement üreten tek ortak servis olmalıdır.
- `OUT` öncesi stok, recall blokajı ve ürün-birim uyumu kontrol edilir.

**Production & Costing**
- Üretim emri durum geçişleri ve gerçek tüketim/çıktı kayıtları.
- EKP, satış fiyatı ve brüt kâr/marj hesaplamaları; formüller Cilt 1.2/1.3 ile aynı olmalıdır.
- Tahmin maliyeti ile gerçekleşen maliyet farklı alanlarda tutulur.

**Butchering**
- Girdi karkas, çıktı kesimler/yan ürün/fire, ağırlık dengesi ve maliyet tahsisi.
- Tahminler ile gerçek ağırlıklar ayrıdır.
- Fire DTO nullable uyuşmazlığı WF-01 çözülmeden kesinleştirilmemelidir.

**Sales**
- Satış ve satırları, lot bazlı miktar, fiyat ve idempotency.
- Stok hareketi inventory service üzerinden gerçekleşir.
- Recall blokajını her yazma işleminde kontrol eder.

**Shipments**
- Market/alıcı, sevkiyat satırları, durum ve sevkiyat izleri.
- Satıştan ayrı kayıt olarak kalır.
- **Onaylanmış WF-03:** dispatch tek `OUT/SHIPMENT` hareketinin sahibidir; satış ticari kayıt olarak kalır ve stok bakiyesini azaltmaz.

**Traceability**
- Lot genealogy grafiği ve ileri/geri izleme sorguları.
- Miktarlı bağlantıları döndürür; eksik bağlantıları tahmin etmez.
- İkinci-tier dağıtım sadece kayıt varsa raporlanır.

**Recalls**
- Taslak, aktivasyon, etkilenen lotlar, satış/sevkiyat geçmişi, aksiyon/iletişim ve çözümleme.
- Satış/sevkiyat blokajı backend'de uygulanır.
- Recall'ın kapatılması blokajı kendiliğinden kaldırmamalıdır; ayrı karar gerekir.

**AI/ML**
- Üretim verimi/EKP ve parçalama ağırlığı tahminleri.
- Model sürümü, özellikler, tahmin ve gerçek karşılaştırması.
- Operasyonel stok/maliyet/recall kayıtlarına yazma yetkisi yoktur.

**Audit**
- Kritik iş olayı, actor, zaman, hedef kayıt, action ve uygun değişiklik özeti.
- Parola, access token veya gereksiz kişisel veri loglanmaz.
- Audit kaydı, kritik iş transaction'ıyla aynı atomiklikte yazılmalıdır.

## 7. Ortak DTO, decimal ve tarih kuralları

- API sözleşmesindeki alan adları `snake_case`.
- Enum değerleri `UPPER_SNAKE_CASE`.
- Endpoint yolları küçük harf ve kebab-case.
- Para `DECIMAL(19,4)`, miktar/ağırlık `DECIMAL(19,6)` olarak saklanır.
- Para ve miktar API'de JSON string olarak temsil edilir; Python'da `Decimal` kullanılır, float'a çevrilmez.
- Tarih-saat anları ISO 8601 UTC `Z`; sadece tarih `YYYY-MM-DD`.
- Hata zarfı Cilt 1.4'te tanımlanan `error.code`, `error.message`, isteğe bağlı `error.details`, `request_id` yapısına uyar.
- Pagination/filtering Cilt 1.3'teki ortak sözleşmeyi izler.
- Pydantic DTO'ları SQLAlchemy modelinden ayrı tutulur; yanıta yalnızca açıkça tanımlanmış alanlar girer.

## 8. Güvenlik ve yapılandırma

### 8.1 Gizli bilgiler

- `DATABASE_URL`, JWT secret ve diğer gizli değerler environment/config üzerinden alınır.
- Gerçek sırlar repository'ye commit edilmez.
- `.env.example` sahte yer tutucu değerler içerir.
- Loglar parola, JWT, secret veya gereksiz hassas veri içermez.

### 8.2 Kimlik doğrulama ve yetkilendirme

- Access token doğrulaması ve rol/izin kontrolü her korumalı endpoint'te backend tarafında yapılır.
- Kullanıcı ID'sini request body'den alıp güvenilir kabul etme; actor kimliği doğrulanmış token/dependency üzerinden elde edilir.
- Kullanıcıya ait veya role göre sınırlı kaynaklara erişim kapsamı ayrıca kontrol edilir.
- Parolalar düz metin olarak saklanmaz; güncel güvenli parola hash algoritması kullanılır.
- JWT süreleri, token yenileme ve logout invalidation davranışı mevcut API sözleşmesinde tanımlı olduğu ölçüde uygulanır; tanımlanmayan davranış varsayılmaz.

### 8.3 Gözlemlenebilirlik

- Her istek için `request_id` oluşturulur veya gelen güvenilir request ID doğrulanarak ilişkilendirilir.
- Hata logları teknik teşhis için yeterli bağlamı taşır ancak sırları içermez.
- Health endpoint'i uygulama canlılığı ile DB bağlantı durumunu ayırt edebilmelidir.
- Kullanıcıya iç SQL exception veya stack trace dönülmez.

## 9. Test stratejisi

### 9.1 Unit test

- EKP, brüt kâr, marj ve maliyet tahsis formülleri.
- Decimal hassasiyeti ve yuvarlama.
- Geçersiz durum geçişleri.
- Ağırlık dengesi ve tahsis toplamı.
- Recall genealogy traversal kuralları.
- Permission kararları.
- ML feature dönüşümleri ve model çıktısı doğrulaması.

### 9.2 Integration test

Test veritabanı MySQL 8.4 ile aynı temel davranışları vermelidir; SQLite testleri, MySQL kilitleme ve DECIMAL davranışının tam yerine geçmez.

- Migration'ların boş veritabanına uygulanması.
- Unique/FK/check constraint'leri.
- Inventory movement + balance atomikliği.
- İki eşzamanlı satışın negatif stok yaratmaması.
- Idempotency anahtarının aynı/farklı body davranışı.
- Üretim/parçalama tamamlamasının rollback davranışı.
- Recall aktivasyonu ve satış engeli.
- Audit kaydının kritik transaction'la tutarlılığı.

### 9.3 Contract test

- Cilt 1.3 endpoint method/path/status ve request/response şemaları.
- Cilt 1.4 örnek DTO'ları.
- Decimal değerlerin JSON string olarak dönmesi.
- Hata zarfı ve `request_id`.
- Enum ve nullable alanların birebir uyumu.
- React/TypeScript ve Kotlin istemcilerinin OpenAPI sözleşmesine uyumu.

### 9.4 End-to-end test

Zorunlu senaryo: `ET-2026-001` → `URT-2026-045` → `SUC-2026-045` → Market A/B/C miktarları → recall aktivasyonu → etkilenen kayıtların gösterimi → aynı lotla yeni satışın reddi.

Her aşamada şu doğrulanır:
- Stock movement ve balance
- Lot genealogy miktarları
- EKP ve maliyet hesaplaması
- Audit trail
- Recall blokajı
- API hata sözleşmesi

## 10. Geliştirme sırası ve kabul ölçütleri

### Faz 0 — Sözleşme kapıları

- Cilt 1.2–1.5 arasındaki alan, enum, stok düşümü ve durum çelişkilerini listele.
- WF-01–WF-10 için `OPEN`, `APPROVED` veya `OUT_OF_SCOPE` durumu ata.
- Kesinleşmemiş alanlar için migration/API DTO kodlama başlamasın.

**Çıkış ölçütü:** Her kritik belirsizlik sahibi ve kararıyla belgelenmiş.

### Faz 1 — Proje iskeleti

- FastAPI uygulaması, config, logging, DB session, error handler.
- `/api/v1` router ve health endpoint'leri.
- Pydantic ortak hata/response şemaları.
- pytest, lint/type-check ve CI başlangıcı.

**Çıkış ölçütü:** Uygulama yerelde ayağa kalkıyor, config eksikse açık hata veriyor, health testleri geçiyor.

### Faz 2 — DB modelleri ve migration

- SQLAlchemy modellerini onaylı ERD'ye göre yaz.
- Alembic ilk migration ve ileri migration pratiği.
- FK/unique/check kısıtları ve index'ler.
- Demo seed komutu ve ayrı test DB config'i.

**Çıkış ölçütü:** Temiz MySQL 8.4 veritabanı migration ile oluşturulabiliyor; migration testleri geçiyor.

### Faz 3 — Auth, catalog, inventory temeli

- Login/current-user/permission.
- Ürün, birim, tedarikçi ve hizmet referans verileri.
- Lot kabulü, movement ledger ve balance.
- Audit ve stok mutabakat testleri.

**Çıkış ölçütü:** Lot kabulü `IN` hareketi ve bakiye oluşturuyor; hareket olmadan bakiye değiştirilemiyor.

### Faz 4 — Production ve costing

- Üretim emri durum geçişleri.
- Gerçek girdi/çıktı ve genealogy.
- EKP ve diğer maliyet metrikleri.
- Transaction rollback ve yetersiz stok testleri.

**Çıkış ölçütü:** 85 paket örneği için yaklaşık €18.16/paket EKP beklenen hesapla uyuşuyor; formül ve yuvarlama testle sabit.

### Faz 5 — Butchering

- Girdi karkas, çıktı kesimler/yan ürünler/fire.
- Ağırlık dengesi, tahsis yöntemi ve cost conservation.
- Tahmin/gerçek ağırlık kayıtları.

**Çıkış ölçütü:** Tahsis edilen maliyet toplamı girdi maliyetine eşit; farklar açıklanabilir ve testlidir.

### Faz 6 — Sales, shipments, traceability

- Idempotent satış.
- Sevkiyat durumu ve stok hareketi sahipliği.
- İleri/geri lot izleme.
- Eşzamanlı satış ve mükerrer hareket testleri.

**Çıkış ölçütü:** 85 paket toplamı ve 30/25/30 dağılımı çift düşüm olmadan izleniyor.

### Faz 7 — Recall

- Recall draft/activate/resolve akışı.
- Aşağı-akış lot ve müşteri/market sorgusu.
- Lot blokajı ve satış/sevkiyat engeli.
- İletişim/aksiyon kayıtları ve audit.

**Çıkış ölçütü:** `ET-2026-001` recall senaryosu kayıtlı genealogy üzerinden tamamlanıyor; bloke lot satılamıyor.

### Faz 8 — AI

- İlk baseline modelleri.
- Tahmin endpoint'i ve model sürümü.
- Tahmin-gerçek karşılaştırması ve metrikler.
- Model yok/az veri durumları.

**Çıkış ölçütü:** AI tahminleri ölçülebilir; ML hatası operasyonel akışları bozmaz.

### Faz 9 — Hardening ve teslim

- API contract testleri.
- Permission/security testleri.
- Demo veri ve tekrarlanabilir kurulum.
- Loglama, hata senaryoları ve README.
- E2E demo provası.

**Çıkış ölçütü:** Yeni ortamda proje kurulabiliyor, testler çalışıyor ve değerlendirme akışı baştan sona tekrarlanabiliyor.

## 11. Kod üretiminde LLM kullanımı için görev şablonu

Her modül başka bir LLM veya geliştiriciye verilecekse görev paketi şunları içermelidir:

1. İlgili cilt ve karar kayıtlarının tam dosyaları.
2. Modülün kapsamı ve açıkça kapsam dışı olanlar.
3. Kullanılacak tablo/DTO/endpoint isimleri.
4. Değiştirilebilecek dosyalar ve değiştirilemeyecek ortak sözleşmeler.
5. İş kuralları ve transaction sınırı.
6. Yetki ve hata kodları.
7. Zorunlu unit/integration/contract testleri.
8. Çalıştırılacak test komutları ve beklenen sonuçlar.
9. Tamamlandığında teslim edilecek dosya listesi.
10. Çözülemeyen belirsizlikler için kod içinde tahmin yürütmek yerine soru/karar kaydı açma talimatı.

**Görev talimatı:** “Mevcut sözleşmelerde olmayan tablo, alan, endpoint, enum veya iş kuralı uydurma. Çelişki görürsen implementasyona başlamadan raporla. Kritik stok ve maliyet etkilerini endpoint içinde veya birden çok commit'e bölerek uygulama.”

## 12. Açık noktalar

Aşağıdaki noktalar Cilt 1.6 tarafından tek başına karara bağlanmaz; mevcut karar kayıtlarıyla çözülmelidir:

- WF-01: Fire için ürün/lot alanlarının nullable olup olmadığı.
- WF-02: Üretim girdilerinin stoktan düşme anı.
- WF-03: **KAPATILDI** — dispatch tek stok çıkışı sahibidir; satış OUT oluşturmaz.
- WF-05: Recall aktivasyonunun senkron veya outbox tabanlı olması.
- WF-06: Recall çözümünde lot blokajının kaldırılması.
- WF-07: Ağırlık farkı toleransı.
- WF-08: Tamamlanmış üretim/parçalama/satış düzeltme kuralları.
- WF-09: Kritik komutlarda satış dışı idempotency gereksinimi.
- WF-10: Ara durumların enumlara eklenmesi gerekip gerekmediği.
- Logout/token invalidation gibi auth davranışlarının Cilt 1.3'teki kesin kapsamı.
- Sevkiyatın fiziksel stok hareketi ile satış arasındaki kesin sorumluluk sınırı.

## 13. Sonraki adım

Bir sonraki belge önerisi: **Cilt 1.7 — Migration Planı, Veritabanı Kısıtları ve Seed/Test Verisi**. Bu belge, Cilt 1.2 ERD'sini gerçek MySQL migration sırasına ve demo verisi oluşturma kurallarına dönüştürür. Cilt 1.7'den önce WF kararları kapatılırsa migration'ları sonradan yeniden yazma riski azalır.

## Revizyon 1.11 — Servis/transaction uygulama sözleşmesi

- Domain/service katmanı her stok etkili komut için ledger hareketi, lot balance, genealogy, maliyet, audit ve idempotency sonuçlarının aynı transaction kapsamını tanımlar. Başarısız alt adımda tüm DB etkileri rollback olur.
- Üretim girdisi `IN_PROGRESS` geçişinde tüketilmez; gerçek miktarlarla tamamlama sırasında tüketilir. Rezervasyon ilk sürümde yoktur.
- Satış ve sevkiyat aynı fiziksel stok için çift `OUT` üretmemelidir. Dispatch'in tek `OUT` sahibi olması önerilen demo varsayılanıdır; nihai seçim son çapraz kontrol kapısında doğrulanır.
- Recall aktivasyonu MVP'de senkron ve atomiktir. `RESOLVED` lotu otomatik açmaz; ayrı unblock/release servisi role-check ve audit gerektirir.
- Satış `Idempotency-Key` zorunlu kullanır. Diğer kritik POST'lar için idempotency veya deterministik state-conflict seçimi endpoint bazında test edilir. DB unique constraint tek başına kullanıcıya doğru replay yanıtı üretme sözleşmesinin yerine geçmez.
- JWT access token 15 dakika, refresh token 7 gün ve rotation zorunludur. Logout refresh session'ını sunucu tarafında iptal eder; reuse tespitinde token ailesi iptal edilir.
- Liveness ve detaylı dependency/DB health ayrıdır; detaylı health internal/authorized erişime alınır ve hassas konfigürasyon döndürmez.
- Ortak hata registry, nullable-field mapping ve permission matrix contract testleri CI kapsamına eklenir. Error JSON `request_id` alanını kullanır.

