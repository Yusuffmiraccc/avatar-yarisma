# Cilt 1.24 — End-to-End Acceptance Tests & External LLM Handoff Pack


> **Normatif güncelleme — 22 Ekim 2026 (Cilt 1.32):** Bu belgedeki daha eski ve çelişen taslak ifadeler için `volume-01-32-approved-decisions-and-cross-check.md` ile Cilt 1.31'in onay kaydı önceliklidir. Bu not doküman sözleşmesini günceller; migration veya veritabanı değişikliği izni değildir.

**Tarih:** 22 Ekim 2026  
**Durum:** Taslak devir sözleşmesi; açık kararlar nedeniyle uygulama/migration onayı değildir.  
**Amaç:** Database/backend kodunu yazacak harici LLM'ye kapsamı, normatif kaynakları, kabul senaryolarını, teslim formatını ve blokaj bildirme kurallarını tek bir giriş noktasıyla vermek.

## 1. Bu belgenin bağlayıcılığı

Bu cilt, mevcut belgeleri tekrar yazmaz; uygulama LLM'sinin hangi kaynakları hangi öncelikle izleyeceğini ve işi nasıl doğrulayacağını tanımlar. Belge tek başına açık kararları kapatmaz.

- Yarışma PDF'sindeki gereksinimler ve aritmetik tutarsızlıklar aynen korunur; tutarsızlıklar sessizce düzeltilmez.
- Proje sahibinin açıkça onayladığı kararlar bağlayıcıdır.
- Diğer ciltlerdeki birbiriyle çelişen tanımlar için LLM kendi seçimini yapamaz; `BLOCKED` raporu oluşturur.
- Proje sahibinin ayrıca açık onayı olmadan Alembic migration dosyası üretilmez ve veritabanı oluşturulmaz/değiştirilmez.
- Bu cilt, bütün `OPEN/BLOCKED` maddeler kapanmadan kodlamaya hazır olduğumuzu iddia etmez.

## 2. Normatif kaynak sırası

1. `AVATAR_Assessment.pdf` — yarışma gereksinimleri ve örnek değerler.
2. Onaylanmış karar kayıtları: `decisions/DEC-001-data-api-contracts-proposal.md`, `decisions/ADR-001-android-online-first.md` ve proje sahibinin açık onayları.
3. `volume-01-2-erd-and-data-schema.md`, `volume-01-3-api-contracts.md`, `volume-01-4-openapi-dto-contract-tests.md` — yalnızca karşılıklı tutarlı oldukları ölçüde.
4. `volume-01-5-workflows-state-machines.md` ve `volume-01-19-canonical-workflow-ids-state-registry.md`.
5. `volume-01-15-canonical-registries.md`, `volume-01-16-erd-dto-field-crosswalk.md`, `volume-01-22-full-erd-constraint-index-dto-crosswalk.md`.
6. `volume-01-17-waste-expiry-cost-decisions.md` ve `volume-01-23-expiry-waste-cost-weight-unit-decisions.md`.
7. Güvenlik, yanıt/hata ve readiness belgeleri: Cilt 1.18, 1.20 ve 1.21.

Kaynaklar çelişiyorsa öncelik sırası, açık proje sahibi onayını geçersiz kılmak için kullanılamaz. Çelişki kayıt altına alınmalı ve karar istenmelidir.

## 3. Harici LLM'nin görev kapsamı

### Dahil
- FastAPI REST API, Pydantic DTO'ları, SQLAlchemy 2.x modelleri ve servis katmanı.
- MySQL 8.4 LTS bağlantısı; Alembic yalnızca açık migration onayı sonrası.
- JWT ve rol bazlı erişim; ortak hata/yanıt sözleşmeleri.
- Stok hareket defteri ve güncel lot bakiyesinin aynı transaction içinde tutarlı tutulması.
- Üretim, kasaplık, satış, sevkiyat, lot izlenebilirliği ve geri çağırma iş mantığı.
- Testler, OpenAPI sözleşmesi, seed/demo verisi ve kurulum belgeleri.

### Hariç / sınırlamalar
- Android ve web istemcilerinin kodunu bu backend görevi içinde yazma; istemciler için API sözleşmesi sağla.
- İlk sürümde offline satış kuyruğu veya SQLite–MySQL satış senkronizasyonu tasarlama. Mimari online-first'tır; MySQL'e yalnızca backend erişir.
- AI tahminini stok, maliyet, lot soy ağacı veya geri çağırma için gerçek kayıt kaynağı olarak kullanma.
- Onaylanmamış iş kurallarını, enum'ları, toleransları, fiyat/değerleme anahtarlarını veya izinleri varsayma.

## 4. Zorunlu uçtan uca kabul senaryoları

Her senaryo otomatik testle mümkün olduğunca doğrulanmalı; testte kullanılan sabitler ve beklenen sonuçlar belgelenmelidir. Açık iş kuralına bağlı senaryo, kural onaylanana kadar `BLOCKED` olarak raporlanır.

### AT-01 — Dış hizmetle üretim ve gerçek birim maliyet

Girdiler:
- Et: 100 kg × €9.70 = €970.00
- Baharat: 2 kg × €24.00 = €48.00
- Bağırsak: 5 kg × €11.60 = €58.00
- Hizmet: 85 paket × €5.50 = €467.50

Beklenenler:
- Toplam maliyet = €1,543.50.
- Kabul edilen mamul = 85 paket.
- Birim maliyet = €1,543.50 / 85 ≈ €18.1588235; görüntüleme kuralına göre €18.16.
- Malzeme tüketimi, dış hizmet maliyeti, mamul kabulü, lot ilişkileri ve audit kayıtları tutarlı olmalı.
- Gerçek maliyet ile tahmin sonucu birbirinden ayrı tutulmalı.

### AT-02 — Kasaplık ağırlık ve maliyet dengesi

- Girdi ağırlığı, stokta izlenen kesimler, stokta izlenen yan ürünler, fire ve onaylı/açıklanmış fark ile uzlaştırılmalı.
- Maliyet dağıtımı tamamlandığında çıktı maliyetleri + fire maliyeti = girdi satın alma maliyeti olmalı.
- Fire satılabilir ürün veya stok girişi yaratmamalı.
- `BY_WEIGHT` onaylı kuralına göre ölçülen ağırlık kategorileri maliyet payı almalı.
- `BY_VALUE` formülü ve fire değerlemesi onaylanana kadar bu alt senaryonun bağlayıcı beklenen rakamları `BLOCKED` olmalı.
- Yarışma PDF'sindeki örnek tutarsızlığı raporlanmalı: 25 kg × €11.50 = €287.50; görselde belirtilen €351.00 ile uyuşmaz ve listelenen kesim ağırlıkları 22 kg'dır. Nedeni uydurulmamalı.

### AT-03 — Lot soy ağacı ve geri çağırma

Zorunlu senaryo:
- Hammadde lotu `ET-2026-001`: 100 kg.
- Üretim emri `URT-2026-045`.
- Mamul lotu `SUC-2026-045`: 85 paket.
- Market A: 30; Market B: 25; Market C: 30 paket.

Beklenenler:
- Sevk edilen toplam 85 paket olmalı.
- Hammadde lotundan mamul lotlarına ileriye izleme, mamul lotundan girdilere geriye izleme miktar bazında çalışmalı.
- Geri çağırma ilgili lotu bloke etmeli; bloke lotun satışı reddedilmeli.
- Sevkiyat/market miktarları, iletişim durumu ve bilinen alıcılar gösterilmeli.
- İkinci kademe dağıtım kaydedilmediyse varmış gibi gösterilmemeli.
- Her fiziksel stok çıkışı yalnızca bir `OUT` hareketi üretmeli; satış ve sevkiyat aynı çıkışı iki kez düşmemeli.

### AT-04 — Stok hareketi atomikliği

- İşlem ledger kaydı ile lot balance değişikliği tek transaction içinde yapılmalı.
- Herhangi bir adım hata verirse ikisi de rollback olmalı.
- Stok yetersizliği negatif bakiye oluşturmamalı.
- İptal/düzeltme, geçmiş hareketi silmek yerine kaynak harekete bağlı ters/düzeltme kaydı üretmeli.

### AT-05 — Idempotency ve tekrar istekleri

- Satışta aynı `Idempotency-Key` + aynı body tekrar gönderildiğinde ilk sonuç dönmeli ve ikinci satış/stok hareketi oluşmamalı.
- Aynı key farklı body ile kullanılırsa `409 Conflict` olmalı.
- Satış dışındaki kritik komutların tekrar davranışı Cilt 1.21'de kesinleştirilmiş sözleşmeye göre test edilmeli; sözleşme eksikse tahmin edilmemeli.

### AT-06 — Yetki ve güvenlik

- Kimlik doğrulaması gerektiren endpoint'ler anonim istekleri reddetmeli.
- Rolü olmayan kullanıcı ilgili işlemi yapamamalı.
- Süresi dolmuş/değiştirilmiş token reddedilmeli.
- Kritik işlem endpoint'lerinde izin kontrolü servis işlemi başlamadan uygulanmalı.
- Hata yanıtları parola, token, DB bağlantı bilgisi veya stack trace sızdırmamalı.
- Web token taşıma ve CSRF yöntemi Cilt 1.20'de onaylanana kadar ilgili istemci entegrasyonu `BLOCKED` olarak belirtilmeli.

### AT-07 — Decimal, tarih ve API sözleşmesi

- Para `DECIMAL(19,4)`, ağırlık/miktar `DECIMAL(19,6)` hassasiyetini korumalı; hesaplamada binary float kullanılmamalı.
- JSON para ve miktar alanları sözleşmede kararlaştırıldığı gibi decimal string olmalı.
- Zaman anları ISO 8601 UTC `Z`; tarih-only alanlar `YYYY-MM-DD` olmalı.
- Hata zarfı `error.code`, `error.message`, isteğe bağlı `error.details`, `request_id` alanlarını kullanmalı.
- API prefix `/api/v1`; alanlar `snake_case`, enum'lar `UPPER_SNAKE_CASE`, endpoint yolları lowercase kebab-case olmalı.

### AT-08 — Health ve yapılandırma

- Liveness uygulama prosesinin ayakta olduğunu belirtmeli; DB bağımlılığıyla karıştırılmamalı.
- Readiness sözleşmesi ve erişimi Cilt 1.20'deki nihai kararla eşleşmeli.
- Gizli bilgiler kaynak koda yazılmamalı; environment/config üzerinden alınmalı.
- Başlangıç yapılandırması eksikse uygulama anlaşılır hata vermeli; sırları loglamamalı.

## 5. Zorunlu test katmanları

1. **Unit tests:** Maliyet, ağırlık dengesi, state transition, permission kararları ve DTO doğrulaması.
2. **Integration tests:** MySQL/SQLAlchemy transaction, foreign key, unique/check kısıtları, ledger ve lot balance.
3. **API/contract tests:** Endpoint status code, response body, error envelope, OpenAPI ve yetki matrisi.
4. **End-to-end tests:** AT-01–AT-08 kapsamı; karar bekleyen alt senaryolar `BLOCKED` etiketlenir.
5. **Regression tests:** Her hata düzeltmesinde ilgili hata senaryosu tekrarlanır.

Testlerin hangi DB motorunda çalıştığı açıkça raporlanmalı. SQLite üzerinde geçen bir test, MySQL'e özgü constraint/transaction davranışının kanıtı sayılmaz.

## 6. Harici LLM'nin teslimat biçimi

Her iterasyonda şu rapor verilmelidir:

- Yapılan değişikliklerin özeti.
- Değiştirilen/eklenen dosyaların listesi.
- Uygulanan normatif kararların referansları.
- Çalıştırılan komutlar ve test sonuçları.
- Başarısız testlerin kök nedenleri.
- `OPEN`, `BLOCKED`, `ASSUMPTION` listesi; varsayım üretmek yerine mümkünse blokaj açılmalı.
- API sözleşmesi veya veri modeli değiştiyse etkilenen ciltlerin güncelleme önerisi.
- Migration veya veri değişikliği gerekiyorsa yapılmadan önce beklenen etki ve onay talebi.

LLM hiçbir zaman test çalıştırmadığı halde testlerin geçtiğini, DB'yi kurmadığı halde kurulduğunu veya onay almadığı halde migration'ın onaylandığını söyleyemez.

## 7. Migration öncesi onay kapısı

Migration üretimi/DB değişikliği öncesinde proje sahibine şu maddeler sunulur:

- [ ] Cilt 1.2 ERD, Cilt 1.3 API, Cilt 1.4 DTO/test, Cilt 1.5 workflow, Cilt 1.16 crosswalk ve Cilt 1.22 matrisi çapraz kontrol raporu.
- [ ] Cilt 1.20 güvenlik kararlarının tamamlanması.
- [ ] Cilt 1.21 error/idempotency/response kayıtlarının tamamlanması.
- [ ] Cilt 1.23'te kalan maliyet, expiry, tolerance, unit, reason-code ve rounding kararlarının kapanması.
- [ ] Bütün açık kararlar için proje sahibi onayı veya açıkça MVP dışına çıkarma kararı.
- [ ] Seed/demo verisi ve beklenen sonuçların gözden geçirilmesi.
- [ ] Proje sahibinden ayrıca açık migration/DB değişikliği onayı.

**Bu kutucukların yazılı olması onay verildiği anlamına gelmez.** Her madde gerçek kontrol sonucu ile işaretlenmelidir.

## 8. Şu anda hâlâ açık olan önemli kararlar

Bu cilt, açık kararları saklamaz. En azından aşağıdakiler Cilt 1.20–1.23 karar oturumlarında kapanmalıdır:

- Web token saklama/taşıma ve CSRF modeli.
- Android token saklama yaklaşımı.
- Parola politikası, login rate limit ve kullanıcı devre dışı bırakıldığında token davranışı.
- Audit yazılamadığında kritik işlemin davranışı.
- Health readiness erişimi ve response sözleşmesi.
- Kritik POST'ların idempotency kapsamı ve başarı yanıtlarında `request_id` standardı.
- Ürün/lot bazında son tüketim tarihi politikası.
- `BY_VALUE` değerleme anahtarı ve fire maliyeti formülü.
- Ağırlık toleransı, birim dönüşümü, fire reason-code listesi ve çoklu lot ilişkilendirme ayrıntıları.
- Tam ERD–DTO–constraint–index eşleştirmesinin gerçek şema/OpenAPI ile doğrulanması.

## 9. Devir kararı

**Durum: EXTERNAL LLM HANDOFF NOT READY.** Bu belge, devir için gereken kapsamı ve testleri tanımlar; açık kararları kapatmaz ve migration izni vermez. Cilt 1.24'ün tamamlanması, diğer ciltlerin son çapraz kontrolü ve proje sahibinin açık onayı sonrasında nihai handoff paketi sürümlenebilir.
