# Cilt 1.18 — Database & Backend Readiness Audit ve Kodlama LLM Devir Sözleşmesi

**Tarih:** 22 Ekim 2026  
**Durum:** Dokümantasyon denetimi / uygulama öncesi hazırlık  
**Amaç:** Database ve backend kodunu yazacak harici LLM'nin kendi başına karar uydurmasını önlemek; tüm bağlayıcı kararları, açık kararları, kanıtları ve teslim koşullarını tek yerde göstermek.  
**Migration durumu:** Bu cilt migration üretmez ve veritabanını oluşturma/değiştirme yetkisi vermez.

## 1. Kapsam ve çalışma biçimi

Proje sahibi bu aşamada uygulama kodunu yazmayacaktır. Kodlama, ayrı bir LLM tarafından yürütülecektir. Bu nedenle bu doküman kod üretmek için değil, kod üretimine geçişin güvenli olup olmadığını denetlemek ve dış LLM'ye verilecek bağlayıcı sözleşmeyi tarif etmek için hazırlanmıştır.

Hedef “hiç soru işareti kalmaması”dır. Bir karar kaynaklarda bulunmuyorsa uygulayıcı LLM'nin tahmin etmesi kabul edilmez. İlgili madde `BLOCKED` olarak işaretlenir, önerilen seçenekler ve etkileri açıklanır, proje sahibinden karar alınır ve karar tüm etkilenen ciltlere işlenir.

## 2. Normatif kaynakların öncelik sırası

Çelişki görüldüğünde uygulayıcı aşağıdaki sırayı izler:

1. Yarışma PDF'sindeki açık gereksinimler ve örnek veriler; PDF'deki aritmetik tutarsızlıklar sessizce düzeltilmez.
2. Proje sahibinin açıkça onayladığı karar kayıtları (`DEC-001`, `ADR-001` ve açık kullanıcı onayları).
3. Cilt 1.2 ERD/veri şeması, Cilt 1.3 API sözleşmeleri ve Cilt 1.4 DTO/test sözleşmeleri — yalnızca birbiriyle tutarlı oldukları ölçüde.
4. Cilt 1.5 iş akışları ve durum makineleri.
5. Cilt 1.15 kanonik kayıtlar ve Cilt 1.16 ERD–DTO alan eşleştirmesi.
6. Cilt 1.17 fire/son tüketim tarihi/maliyet kararları.
7. Cilt 1.18'deki denetim listesi.

Daha düşük öncelikli bir belgede üstteki kaynaklarla çelişen eski ifade bulunursa uygulayıcı eski ifadeyi izlememeli; çelişkiyi raporlamalı ve dokümantasyon revizyonu istemelidir. Bu öncelik sırası eksik bir iş kuralını kendiliğinden belirleme yetkisi vermez.

## 3. Sabit teknoloji ve mimari kararları

| Katman | Bağlayıcı seçim |
|---|---|
| Android istemcisi | Kotlin, Jetpack Compose, Room/SQLite, Retrofit/OkHttp, Coroutines, DataStore |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PyMySQL |
| Merkezi veritabanı | MySQL 8.4 LTS |
| Web istemcisi | React, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts |
| AI/ML | Python, pandas, NumPy, scikit-learn, joblib; ilk sürümde FastAPI içinde ayrı modül, ayrı mikroservis değil |
| API | REST/JSON, `/api/v1`, OpenAPI |
| Test | Backend: pytest; Android: JUnit; web: Vitest + React Testing Library |
| Yerel geliştirme | Git/GitHub ve Docker Compose |

Merkezi MySQL'e yalnızca backend erişir. Android ve web istemcileri MySQL'e doğrudan bağlanmaz. İlk sürüm online-first'tir; offline satış kuyruğu ve senkronizasyon kapsam dışıdır. Android Room/SQLite, merkezi veritabanının yerine geçmez.

## 4. Bağlayıcı veri/API kuralları

- Dahili kimlikler `BIGINT`; kullanıcıya gösterilen iş kodları ayrı ve benzersizdir.
- Para `DECIMAL(19,4)`, ağırlık/miktar `DECIMAL(19,6)` kullanır. JSON'da ondalık değerler string olarak taşınır. İlk demo para birimi EUR; `currency_code` alanı korunur.
- Zaman anları UTC ISO 8601 (`Z`); tarih-only değerler `YYYY-MM-DD` biçimindedir.
- Stok hareket defteri değiştirilemez/append-only kayıttır; lot bakiyesi aynı transaction içinde güncellenir.
- Stok hareketi miktarı daima pozitiftir; yön `IN` veya `OUT` ile belirtilir.
- Lot genealogy çoktan çoğa ve miktar bilgili olmalıdır.
- Satış ile sevkiyat ayrı kavramlardır. **Dispatch tek fiziksel stok çıkışının sahibidir**: dispatch her sevkiyat satırı için tek `OUT/SHIPMENT` hareketi oluşturur; satış aynı fiziksel miktarı ikinci kez düşmez.
- İkinci kademe market satışı, sisteme kaydedilmediyse uydurulmaz.
- Roller: `ADMIN`, `OPERATOR`, `SALES`, `TRACEABILITY_MANAGER`, `VIEWER`; gerçek endpoint izinleri Cilt 1.8/1.9 ile Cilt 1.3'te tek matriste eşleşmelidir.
- Kritik operasyonel kayıtlar hard-delete edilmez; iptal/düzeltme/ters kayıt kullanılır.
- Satışta `Idempotency-Key` zorunludur. Aynı key + aynı gövde ilk sonucu tekrar verir; aynı key + farklı gövde `409 Conflict` üretir.
- Hata zarfı: `error.code`, `error.message`, isteğe bağlı `error.details`, `request_id`.
- DB/API JSON alanları `snake_case`; enum'lar `UPPER_SNAKE_CASE`; endpoint path'leri lowercase kebab-case.

## 5. Kesinleşmiş iş kuralları

### 5.1 Üretim tüketimi

İlk sürümde stok rezervasyonu yoktur. `IN_PROGRESS` durumuna geçmek tek başına stok düşürmez. Üretim tamamlanırken gerçek girdi tüketimleri için `OUT`, bitmiş ürünler için `IN`, lot genealogy, maliyet ve audit etkileri tek transaction'da yazılır. Herhangi bir kritik adım başarısızsa transaction bütünüyle rollback olur.

### 5.2 Parçalama ve fire

- `butchering_outputs` yalnızca stokta izlenen `CUT` ve `BYPRODUCT` çıktıları içerir; bunlarda ürün ve lot zorunludur.
- `WASTE`, ayrı `butchering_waste_records` tablosunda tutulur; fire satırı satılabilir ürün/lot veya stok `IN` hareketi oluşturmaz.
- Ağırlık dengesi girdi ağırlığını kesimler, stokta izlenen yan ürünler, fire ve gerekçelendirilmiş/izin verilen farkla uzlaştırır.
- Stok çıktılarının tahsis edilmiş maliyeti ile fire maliyet paylarının toplamı giriş maliyetine eşit olmalıdır.
- Tahsis maliyetleri istemciden güvenilir veri olarak kabul edilmez; backend hesaplar.

### 5.3 Satış, sevkiyat ve lot recall

- Satış ticari kaydıdır; dispatch fiziksel teslim ve stok çıkışını kaydeder.
- Aynı dispatch tekrar edildiğinde ikinci stok hareketi oluşmaz.
- Recall aktivasyonu MVP'de senkron ve atomiktir; `ACTIVATING` ara durumu kullanılmaz.
- Recall `RESOLVED` olduğunda blokaj otomatik kalkmaz. Ayrı, yetki denetimli ve audit kaydı oluşturan release/unblock komutu gerekir.
- AI sonuçları stok, maliyet, genealogy veya recall için kaynak gerçek değildir.

## 6. Açık kararlar — kod üretimini bloke edenler

Aşağıdaki maddeler dokümanlarda açıkça çözümlenmeden uygulayıcı LLM kendi varsayımını bağlayıcı kural olarak kodlamamalıdır.

| ID | Açık konu | Neden bloke ediyor | Kapatma ölçütü |
|---|---|---|---|
| OPEN-01 | Son tüketim tarihinin hangi ürün/lotlarda uygulanacağı | Kolon nullability tek başına yeterli değil; uygulanabilirlik kaynağı belli değil | Ürün/lot kuralı, API validation'ı, örnekler ve testler tanımlanmalı; yeni alan gerekiyorsa açıkça onaylanmalı |
| OPEN-02 | `BY_VALUE` altında fire maliyeti | Fire ayrı maliyet kaybı mı alacak, yoksa maliyet yalnızca değer taşıyan çıktılara mı dağıtılacak belirsiz | Formül, sayısal örnek, yuvarlama ve sıfır/değersiz çıktı davranışı tanımlanmalı |
| OPEN-03 | Fire `reason_code` sözlüğü | API ve DB'de serbest/uyumsuz değerler oluşabilir | Kanonik kodlar, açıklamalar ve validation/test listesi belirlenmeli |
| OPEN-04 | Ağırlık toleransı | Kaynak PDF sayısal tolerans vermiyor | Sabit, konfigürasyon veya sıfır tolerans kararı ve gerekçe tanımlanmalı; sayı uydurulmamalı |
| OPEN-05 | Çoklu girdi lotu ile fire ilişkilendirme | Fire ağırlığı/maliyeti yanlış lota bağlanabilir | Her fire kaydının tek `input_lot_id`'ye mi bağlanacağı veya dağıtım ilişkisi mi gerekeceği kesinleştirilmeli; çoklu lot örneği test edilmeli |
| OPEN-06 | Ağırlık birimi dönüşümü | Karışık birimler ağırlık dengesini bozar | İzin verilen birimler, dönüşüm kaynağı, hassasiyet ve bilinmeyen dönüşüm hatası tanımlanmalı |
| OPEN-07 | Token/logout ve token taşıma biçimi | Cilt 1.3/1.4 ile 1.8/1.9 arasında eski karar/metin çelişkileri raporlandı | Access token süresi, refresh olup olmadığı, logout, Android Bearer ve web taşıma biçimi, aktif kullanıcı kontrolü kesinleşmeli |
| OPEN-08 | Health endpoint sözleşmesi | Ad, erişim ve response şekli tam sabit değil | Liveness/readiness endpoint'leri, auth, response ve negatif testleri tanımlanmalı |
| OPEN-09 | Endpoint izin matrisi | Bazı eski tablolar farklı roller veriyor | Her endpoint için tek permission key, izinli roller ve negatif test eşleştirilmeli |
| OPEN-10 | Enum/state registry | Eski belgelerde `SHIPPED`/`DISPATCHED` gibi farklı adlar bulunabiliyor | Her entity için tek enum sözlüğü ve izinli state transition listesi oluşturulmalı |
| OPEN-11 | Error-code registry | Genel `CONFLICT` ve özel hata kodlarının kullanım sınırı tam tekleştirilmemiş | HTTP status + `error.code` + koşul + endpoint örneği tek tabloda belirtilmeli |
| OPEN-12 | Kritik komutların idempotency standardı | Satış dışındaki komutlarda key/replay davranışı endpoint bazında tam sabit değil | Her kritik POST için idempotency key veya deterministik state-conflict davranışı seçilmeli |
| OPEN-13 | Başarılı yanıtlarda `request_id` | Hata zarfı belli; başarılı yanıtlarda header/body konumu eski metinlerde açık | Tek standart seçilip OpenAPI ve testlere yazılmalı |
| OPEN-14 | Recall unblock endpoint'i | Blokaj kaldırma işlemi API/rol/tekrar davranışıyla tam tekleştirilmeli | Endpoint, payload, izin, audit, idempotency ve blokaj yokken davranış tanımlanmalı |
| OPEN-15 | Düzeltme/ters kayıt kuralları | Tamamlanmış maliyet/üretim/parçalama/dispatch kayıtlarının tersine çevrilmesi her endpoint için ayrıntılı değil | Kaynak kayıt bağlantısı, ters hareketler, maliyet etkisi ve tekrar çağırma davranışı tanımlanmalı |
| OPEN-16 | Success/error response sözleşmesi | Endpoint'ler arası response envelope tutarlılığı doğrulanmalı | Tüm endpoint DTO'ları ortak hata ve başarı standardıyla karşılaştırılmalı |
| OPEN-17 | Nullable alanların tam envanteri | NULL'un anlamı ve DTO davranışı her alan için tek tabloda değil | Her tablo/kolon için nullable, gerekçe, API karşılığı ve validation kaydı tamamlanmalı |
| OPEN-18 | Constraint/index envanteri | ERD ve gerçek ORM metadata eşleşmesi doğrulanmadı | PK/FK/UNIQUE/CHECK/index listesi ve alan tipi karşılaştırması yapılmalı |

Bu liste, her konunun mutlaka yeni özellik gerektirdiği anlamına gelmez. Örneğin refresh token kullanılmaması veya belirli bir endpoint'in kapsam dışı bırakılması da geçerli bir karardır; ancak bu karar tüm belgelerde aynı şekilde belirtilmelidir.

## 7. WF-01–WF-10 numaralandırma kontrolü

Cilt 1.5'in eski karar tablosu ile sonraki revizyon notlarında WF numaraları farklı konular için yeniden kullanılmış olabilir. Uygulayıcı LLM, WF numarasını tek başına referans kabul etmemelidir. Cilt 1.5 revize edilirken her workflow'a değişmez bir ID ve kanonik ad verilmelidir. Önerilen format: `WF-PROD-COMPLETE`, `WF-BUTCHERING-COMPLETE`, `WF-DISPATCH`, `WF-RECALL-ACTIVATE`, `WF-RECALL-RELEASE`, `WF-CORRECTION`, `WF-IDEMPOTENCY`. Eski WF numaraları yalnızca tarihsel çapraz referans olarak korunabilir.

## 8. Kodlama LLM'sine verilecek bağlayıcı talimatlar

Aşağıdaki metin, uygulama başladığında kodlama LLM'sine verilecek talimatların temelidir:

1. Yalnızca onaylanmış ve normatif işaretlenmiş kararları uygula.
2. Açık kararlar tablosundaki hiçbir davranışı tahmin ederek kesinleştirme. Önce blokaj raporu üret ve gerekli kararı iste.
3. Migration üretmeden önce Cilt 1.2 ERD/alan envanteri, Cilt 1.3 endpoint'leri, Cilt 1.4 DTO/test sözleşmeleri, Cilt 1.5 workflow'lar ve Cilt 1.16 crosswalk arasında otomatik/manuel çapraz kontrol raporu oluştur.
4. Proje sahibinin ayrıca açık onayı olmadan Alembic migration dosyası üretme, veritabanı oluşturma veya değiştirme.
5. MySQL'e Android/web istemcisinden doğrudan bağlantı kurma.
6. İş kurallarını yalnızca route handler içine yığma; endpoint, schema, service, repository/ORM ve test sorumluluklarını ayrıştır.
7. Stok ledger ve lot balance değişikliklerini, genealogy, maliyet ve audit etkilerini ilgili workflow'un tarif ettiği tek transaction içinde yürüt.
8. Para ve miktar hesaplarında `float` kullanma; onaylı Decimal hassasiyetini ve string JSON temsilini koru.
9. Hard-delete yapma; düzeltme/iptal/ters kayıt kurallarını uygula.
10. Her yeni/uyarlanmış endpoint için başarı testi, validation testi, yetki testi, hata testi ve tekrar çağırma testi yaz.
11. Yarışma PDF'sindeki sayısal tutarsızlıkları sessizce düzeltme; veri doğrulama notu olarak raporla.
12. AI çıktısını gerçek stok/maliyet/recall kayıtlarının yerine kullanma.
13. Her kodlama aşamasında değişen dosyaları, alınan kararları, çalıştırılan testleri, test sonuçlarını ve kalan blokajları raporla.
14. OpenAPI örnekleri ile gerçek response DTO'ları uyuşmuyorsa dokümantasyonu veya kodu sessizce seçme; farkı raporla ve normatif sözleşmeye göre düzelt.

## 9. Uygulama öncesi zorunlu teslimatlar

Migration onayına gelmeden önce dokümantasyon tarafında şu çıktılar hazır olmalıdır:

- [ ] Güncel ERD ve tam tablo/kolon/NULL/constraint/index envanteri.
- [ ] ERD–DTO alan eşleştirme matrisinin tüm tabloları kapsaması.
- [ ] Kanonik permission, enum/state, error-code, nullable ve side-effect registry'leri.
- [ ] Her kritik komut için transaction, stok etkisi, maliyet etkisi, genealogy, audit ve idempotency tablosu.
- [ ] API sözleşmelerinin endpoint endpoint request/response/error örnekleri.
- [ ] WF'lerin değişmez ID'lerle tekilleştirilmesi ve tüm state transition'ların tanımlanması.
- [ ] Açık kararların proje sahibi tarafından kapatılması veya açıkça MVP kapsamı dışında bırakılması.
- [ ] Çapraz kontrol raporu: her çelişki için kaynak, etki, düzeltme ve test.
- [ ] Migration öncesi tablo/kolon/constraint/DTO/endpoint/permission/enum/error-code özetinin proje sahibine sunulması.
- [ ] Proje sahibinden migration üretimi için ayrıca açık onay alınması.

## 10. Demo ve kabul senaryoları

### 10.1 Dış kaynaklı üretim ve gerçek birim maliyet

- Girdi malzeme lotları ve miktarları kaydedilir.
- Gerçek tüketim ve fason hizmet maliyeti kaydedilir.
- Tamamlama transaction'ı tüketim `OUT`, bitmiş ürün `IN`, genealogy, maliyet ve audit kayıtlarını üretir.
- Gerçek toplam maliyet, birim maliyet, satış fiyatı, brüt kâr ve marj hesaplanır.
- İptal/tekrar/yarım kalmış işlem testleri stok veya maliyet çift kaydı üretmez.

### 10.2 Kuzu parçalama

- Girdi hayvan/lot maliyeti ve ağırlığı kaydedilir.
- Kesimler ve stokta izlenen yan ürünler lotlu çıktılar olarak kaydedilir.
- Fire ayrı tabloda kaydedilir; stokta ürün veya IN hareketi yaratmaz.
- Ağırlık dengesi ve maliyet uzlaştırması gösterilir.
- `BY_WEIGHT` ve `BY_VALUE` yöntemleri için onaylanmış formüller örneklerle test edilir.
- Yarışma PDF'sindeki 25 kg × €11.50 = €287.50 ile belirtilen €351 toplamı ve 22 kg kesim toplamı tutarsızlığı aynen raporlanır; sebep uydurulmaz.

### 10.3 Lot izlenebilirliği ve geri çağırma

- Kaynak `ET-2026-001` lotu, `URT-2026-045` üretim emri, `SUC-2026-045` bitmiş lotu ve Market A/B/C sevkiyatları bağlanır.
- Sevkiyat miktarları 30 + 25 + 30 = 85 paket olarak doğrulanır.
- Her fiziksel çıkış için yalnızca tek stok `OUT` hareketi bulunur.
- Kaynak lottan ileriye ve bitmiş lot/sevkiyattan geriye izlenebilirlik miktarlarla gösterilir.
- Recall ilgili lotu bloke eder; satış denemesi reddedilir; müşteri/market miktarları ve iletişim durumları gösterilir.

## 11. Audit sonucu ve sonraki çalışma sırası

**Şu anki sonuç: KODLAMA DEVİR PAKETİ HAZIR DEĞİL; MIGRATION KAPISI KAPALI.** Bunun nedeni kod yazacak kişinin teknoloji seçimini bilmemesi değil, bazı normatif iş kurallarının ve belgeler arası tekilliğin hâlâ tamamlanmamış olmasıdır.

Önerilen sonraki dokümantasyon ciltleri:

1. **Cilt 1.19 — Canonical Workflow IDs & State Registry:** WF numara çakışmalarını giderir; her akışın durumlarını, geçişlerini ve side-effect'lerini tekilleştirir.
2. **Cilt 1.20 — Authentication, Permissions & Health Contract Reconciliation:** token/logout, web/Android token taşıma, endpoint izinleri ve health endpoint çelişkilerini normatif olarak kapatır.
3. **Cilt 1.21 — Error, Idempotency & Response Contract Registry:** hata kodları, başarı yanıtı `request_id`, kritik POST tekrar davranışlarını tekleştirir.
4. **Cilt 1.22 — Full Nullable/Constraint/Index/DTO Crosswalk:** tam tablo/kolon eşleştirmesi ve DB constraint envanteri.
5. **Cilt 1.23 — Expiry, Waste Cost, Weight Tolerance & Unit Conversion Decisions:** Cilt 1.17'deki açık maliyet/son tüketim/fire kararlarını sayısal örneklerle kapatır.
6. **Cilt 1.24 — End-to-End Acceptance Tests & External LLM Handoff Pack:** kodlama LLM'sine verilecek nihai talimat, örnek payload'lar, kabul testleri ve blokaj raporlama şablonu.
7. **Migration öncesi final gate:** tüm ciltleri tekrar çapraz kontrol et, proje sahibine değişiklik özeti ver ve açık onay bekle.

Bu sıra, her şeyi tek dev belgeye sıkıştırmak yerine, uygulayıcı LLM'nin referans alabileceği küçük ve birbirine bağlı sözleşmeler üretir.
