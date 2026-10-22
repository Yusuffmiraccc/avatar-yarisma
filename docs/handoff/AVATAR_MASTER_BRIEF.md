# AVATAR — Tek Kaynak Proje Brifingi (LLM Başlangıç Dosyası)

**Sürüm:** 1.45  
**Tarih:** 22 Ekim 2026  
**Amaç:** 43 ciltlik dokümantasyonu her görevde yeniden okutmak yerine, proje hedefini, bağlayıcı kararları, açık blokajları ve uygulama sırasını tek bir kısa dosyada toplamak.

> **LLM talimatı:** Normal kodlama görevlerinde önce yalnızca bu dosyayı oku. Bir iş alanının ayrıntısı gerekiyorsa aşağıdaki “İhtiyaç halinde açılacak kaynaklar” bölümünden yalnızca ilgili dosyayı oku. Tüm arşivi baştan sona okuma. Kaynaklar arasında çelişki varsa varsayım yapma; çelişkiyi ve etkilenen alanı bildir. Backend ve veritabanı mimarisi için kanonik kapanış belgesi `BACKEND_DATABASE_ARCHITECTURE_CLOSURE.md` dosyasıdır. Bu dosya ile birlikte kullan; arşivin tamamını rutin görevlerde okutma.

## 1. Projenin amacı ve zorunlu kapsam

AVATAR, gıda işletmesinde hammadde girişinden üretime, parçalamaya, maliyete, satış/sevkiyata ve lot geri çağırmaya kadar kayıtların izlenmesini sağlayan bir sistemdir. Web yönetim paneli, Android satış uygulaması, merkezi backend/veritabanı ve iki zorunlu ML özelliği bulunur.

### Yarışma görevleri

1. **Dış hizmetle üretim maliyeti:** Hammadde, baharat, kılıf ve hizmet maliyetlerini üretim emrine bağla; gerçek tüketim ve bitmiş ürün miktarıyla birim maliyet (EKP), satış fiyatı (VKP), brüt kâr ve marjı hesapla. Örnek: 100 kg et × €9,70 = €970; 2 kg baharat × €24 = €48; 5 kg kılıf × €11,60 = €58; 85 paket × €5,50 hizmet = €467,50; toplam €1.543,50; yaklaşık €18,16/paket. Maliyet ve stok hareketleri geçmişe dönük denetlenebilir olmalı.
2. **Kuzu parçalama:** Girdi ağırlığı, satılabilir kesimler, yan ürünler ve fireyi kaydet; ağırlık ve maliyet dağılımını uzlaştır. Kaynak örnekte 25 kg × €11,50 = €287,50 iken €351 verilmiş ve kesim ağırlıkları 22 kg ediyor. Tutarsızlığı göster; neden uydurma.
3. **Lot izlenebilirliği/geri çağırma:** `ET-2026-001` 100 kg → `URT-2026-045` → `SUC-2026-045` 85 paket → Market A/B/C sevkiyatları 30/25/30. İleri/geri izleme miktar bazında çalışmalı. Etkilenen lot bloke edilmeli; müşteri/market miktarı ve bildirim durumu gösterilmeli. İkinci seviye dağıtımı ancak kayıt varsa göster. Geri çağrılmış lot satılamaz.

### Zorunlu AI

- Üretim verilerinden üretim verimi ve EKP tahmini; tahmin-gerçekleşen karşılaştırması, hata metriği, baseline ve veri azsa sınırlılık açıklaması.
- Hayvan türü/girdi ağırlığı/geçmiş veriden parçalama çıktı ağırlığı tahmini; tahmin-gerçekleşen ve hata ölçümü.
- AI çıktısı hiçbir zaman stok/lot/geri çağırma için doğruluk kaynağı değildir; gerçek operasyon kayıtları otoritedir.
- Fatura/irsaliye alan çıkarımı ve anomali uyarıları isteğe bağlıdır; çıkarılan veriler insan onayı gerektirir.

## 2. Onaylı teknoloji ve mimari

- **Android:** Kotlin, Jetpack Compose, Room/SQLite, Retrofit/OkHttp, Coroutines, DataStore.
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PyMySQL.
- **Merkezi DB:** MySQL 8.4 LTS.
- **Web:** React, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts.
- **ML:** pandas, NumPy, scikit-learn, joblib; ilk sürümde FastAPI içinde modül.
- **Test/çalıştırma:** Git/GitHub, Docker Compose, pytest, JUnit, Vitest + React Testing Library.
- **API:** REST/JSON/OpenAPI.
- Backend/MySQL tek doğruluk kaynağıdır. Web ve Android MySQL'e doğrudan bağlanmaz. Android online-first; SQLite yerel cache/state içindir, ilk sürümde çevrimdışı satış kuyruğu yoktur. Token'lar düz metin saklanmaz.

## 3. Bağlayıcı veri/API kararları (DEC-001)

1. İç ID `BIGINT`; kullanıcıya gösterilen kodlar ayrı, benzersiz iş kodlarıdır.
2. MySQL para `DECIMAL(19,4)`, miktar/ağırlık `DECIMAL(19,6)`; API'de para ve miktar JSON string olarak taşınır. `currency_code` kullanılır; demo para birimi EUR.
3. Zaman anları ISO 8601 UTC `Z`; yalnız tarih `YYYY-MM-DD`.
4. Değiştirilemez stok hareket defteri ve güncel lot bakiyesi vardır; ikisi aynı transaction'da güncellenir.
5. Stok hareket miktarı pozitif; yön `IN`/`OUT` alanıyla belirtilir.
6. Lot genealogy miktar bilgili çoktan-çoğadır.
7. Satış ve sevkiyat ayrı kavramlardır; kayıtsız ikinci seviye satış icat edilmez.
8. JWT access token + rol/izin kontrolü. Roller: `ADMIN`, `OPERATOR`, `SALES`, `TRACEABILITY_MANAGER`, `VIEWER`.
9. Kritik operasyon kayıtları hard-delete edilmez; iptal/düzeltme/ters kayıt kullanılır.
10. Satışta `Idempotency-Key` zorunlu: aynı anahtar+aynı gövde ilk sonucu döndürür; aynı anahtar+farklı gövde `409 Conflict` döndürür.
11. Ortak hata zarfı `error.code`, `error.message`, isteğe bağlı `error.details`, `request_id`.
12. API öneki `/api/v1`; sayfalama/filtreleme tutarlı olmalı.
13. DB/API JSON alanları `snake_case`; enumlar `UPPER_SNAKE_CASE`; endpoint yolları küçük harf/kebab-case.

### Stok ve iş akışı için teyitli kurallar

- **WF-01:** Parçalama çıktıları `butchering_outputs` içinde ürün/lot ile stoklanır. Fire ayrı `butchering_waste_records` içindedir; ürün/çıktı lotu veya stok `IN` hareketi yaratmaz.
- **WF-02:** İlk sürümde stok rezervasyonu yoktur. `IN_PROGRESS` stok düşmez. Üretim tamamlanırken gerçek tüketim `OUT`, bitmiş ürün `IN`, genealogy, maliyet ve audit tek transaction'da yazılır; hata tümünü rollback eder.
- **WF-03 (onaylı):** Dispatch fiziksel stok çıkışının tek sahibidir. Satış ticari kayıt olarak kalır ve aynı miktar için stok düşmez. Aynı dispatch tekrarlandığında ikinci hareket oluşmaz.
- **WF-04:** Recall aktivasyonu MVP'de senkron/atomiktir; `ACTIVATING` yoktur. Recall `RESOLVED` olduğunda lot blokajı kendiliğinden kalkmaz; ayrı yetkili ve audit'li release/unblock gerekir.
- **WF-05:** Kaynak ağırlık toleransı sayısal belirlemez; yapılandırılabilir/TBD kalır. Fark sessizce silinmez ve neden uydurulmaz.
- **WF-06:** Tamamlanmış kayıt silinmez veya geçmişi sessizce güncellenmez; bağlı düzeltme/ters kayıt, ters stok hareketleri ve audit aynı transaction'da olur.
- **WF-07:** Satışta idempotency zorunludur. Diğer kritik komutlar için endpoint bazında idempotency veya deterministik uygun conflict/invalid-state yanıtı belirlenir.

## 4. Açık konular ve uygulama davranışı

Dokümanlarda kalan farklar `KNOWN_GAPS.md` içinde listelenmiştir. Kodlama LLM'i rutin teknik kararlar için kullanıcıdan tekrar tekrar onay istememelidir: `BACKEND_DATABASE_ARCHITECTURE_CLOSURE.md` v1.45'te kapanmış kararları uygular; henüz kapanmamış konularda en dar güvenli davranışı seçer, kararı ve testi kaydeder. Gerçek ticari/izlenebilirlik verisi uydurulmaz.

Önemli notlar:

1. **ERD/şema parity:** 29 kavramsal varlık listesi tek başına tam fiziksel şema değildir. Tablo/kolon/PK/FK/unique/check/index/nullability/ORM/OpenAPI eşlemesi kodlama sırasında testlerle kanıtlanmalıdır.
2. **Maliyet/fire:** `BY_WEIGHT` ve rounding kuralları kapanış belgesindeki şekliyle uygulanır. `BY_VALUE` güvenilir fire değerlemesi olmadan fail-closed olur.
3. **Expiry:** `products.requires_expiry_date` default `false`; true ise `lots.expiry_date` zorunludur.
4. **Ağırlık toleransı:** Evrensel kaynak değeri yok; yapılandırılabilir, demo default `0.000 kg`, fark sessizce normalize edilmez.
5. **Güvenlik ve izin:** Kapanış belgesindeki auth/session ve endpoint permission kararları uygulanır. Waste endpoint'i `ADMIN`/`OPERATOR` + `butchering:manage` kullanır.
6. **Şema ve güvenlik parity:** Eski manifestlerdeki sayımlar yalnızca denetim kanıtıdır; gerçek ORM/OpenAPI/permission testlerinin yerine geçmez.

## 5. Kodlama ve doğrulama stratejisi

1. Mevcut repo ve sözleşmeler için parity matrisi üret.
2. ORM modelleri, constraint'ler ve Alembic migration'ı hazırla.
3. Migration'ı yalnızca izole yerel/test MySQL 8.4 veritabanında çalıştır.
4. Servis, router, auth, stok, üretim, parçalama, sevkiyat, traceability/recall ve ML modüllerini `IMPLEMENTATION_PLAN.md` sırasıyla uygula.
5. Her fazda unit/integration/contract/concurrency testleri çalıştır; sonuçları raporla.

## 6. Migration ve veritabanı güvenlik sınırı

Proje sahibi 22 Ekim 2026 tarihinde genel teknik yetki devretmiştir. ORM/migration kaynak kodu üretmek ve bunları **izole lokal/test DB'sinde** çalıştırmak serbesttir. Gerçek/production DB'ye bağlanmak, kullanıcı verisini değiştirmek veya silmek yasaktır. Bu sınır `BACKEND_DATABASE_ARCHITECTURE_CLOSURE.md` ve `LLM_HANDOFF.md` ile birlikte okunmalıdır.

## 7. İhtiyaç halinde açılacak kaynaklar

- **Backend/DB mimarisi tek yerde:** `BACKEND_DATABASE_ARCHITECTURE_CLOSURE.md` (normalde bu brief ile birlikte yeterlidir).

LLM yalnızca görev alanına göre ilgili kaynakları açsın:

- **Veri modeli/alanlar:** `volumes/volume-01-2-erd-and-data-schema.md`
- **API ve DTO:** `volumes/volume-01-3-api-contracts.md`, `volumes/volume-01-4-openapi-dto-contract-tests.md`
- **İş akışları:** `volumes/volume-01-5-workflows-state-machines.md`
- **Backend mimarisi:** `volumes/volume-01-6-backend-implementation-plan.md`
- **Migration ve DB kısıtları (yalnızca izole test DB):** `volumes/volume-01-7-migration-constraints-seed-data.md`
- **Auth/roller:** `volumes/volume-01-8-auth-roles-security.md`, `volumes/volume-01-9-endpoint-permissions-security-decisions.md`
- **Hata/idempotency:** `volumes/volume-01-21-error-idempotency-response-registry.md`
- **Ağırlık/fire/expiry:** `volumes/volume-01-23-expiry-waste-cost-weight-unit-decisions.md`
- **Kabul testleri ve LLM devir:** `volumes/volume-01-24-end-to-end-acceptance-tests-llm-handoff.md`
- **Güvenlik ve deployment:** Cilt 1.26–1.29 dosyaları.
- **Son statik şema denetimi:** `volumes/volume-01-42-erd-schema-inventory-and-physical-schema-evidence.md`, `volumes/volume-01-43-markdown-schema-extraction-and-constraint-crosscheck.md`.

Cilt 1.11–1.43 ve manifest/CSV'ler **tarihçe ve denetim arşividir**; LLM'ye rutin görevlerde topluca verilmez. Bu dosya özet olsa da açık kararların yerini almaz.

## 8. LLM görev promptu şablonu

> Önce `LLM_HANDOFF.md` talimatlarını oku; sonra master brief, backend/DB closure ve ilgili ciltleri kullan. Güncel kapanış kararlarını uygula, `KNOWN_GAPS.md`'yi güncel tut. ORM/migration oluşturabilir ve yalnız izole test DB'de çalıştırabilirsin; gerçek/production DB'ye bağlanma veya veri silme. Her faz sonunda değişen dosyaları, çalıştırılan testleri ve gerçek sonuçları raporla.

## 9. Proje durumu

- **Proje hedefi ve teknoloji seçimi:** tanımlı.
- **Temel veri/API kararları:** DEC-001'de onaylı.
- **İş akışlarının bir bölümü:** onaylı; kalan kararlar yukarıda listeli.
- **Şema/API/ORM tam parity kanıtı:** tamamlanmış değil.
- **Migration/DB:** yapılmadı; açık izin yok.
- **Önerilen çalışma biçimi:** tek bu dosyadan başla, yalnızca ilgili ayrıntı dosyasını gerektiğinde aç, tekrar eden statik rapor döngüsünü bırakıp güvenli paralel geliştirmeye geç.
