# Cilt 1.30 — Cilt 1 Kapanış Planı ve LLM Okunabilirliği

**Tarih:** 22 Ekim 2026  
**Durum:** Kapanış kontrolü / normatif belge  
**Amaç:** Cilt 1'i kod yazacak LLM için tek anlamlı, çelişkisiz ve takip edilebilir bir giriş paketi haline getirmek. Bu belge eksik kararları kapatmaz; bunları görünür hale getirir ve kapanış sırasını tanımlar.

## 1. Temel ilke: LLM için tek doğru kaynak

LLM'nin her cildi ayrı ayrı okuyup kendi yorumuyla çelişkileri çözmesi beklenmemelidir. Cilt 1 kapanırken aşağıdaki kaynak önceliği uygulanmalıdır:

1. Kullanıcının açıkça onayladığı karar kayıtları.
2. Güncel canonical registry / karar sicili.
3. Güncel ERD, DTO/API sözleşmeleri ve iş akışları.
4. Bunlarla uyumlu uygulama planı, testler ve teslimat rehberi.
5. Eski revizyon günlükleri yalnızca değişiklik geçmişi içindir; eski değerler güncel normatif kural yerine geçmez.

Eğer iki normatif belge çelişirse LLM birini sessizce seçmemelidir. Çelişkiyi raporlamalı, ilgili karar ID'sini belirtmeli ve o alanda kod üretimini durdurmalıdır.

## 2. LLM için zorunlu okuma sırası

Kod yazacak LLM'ye tüm klasörü gelişigüzel vermek yerine aşağıdaki sıralı giriş paketi verilmelidir:

1. `README.md` — proje amacı, cilt haritası ve en güncel belgeler.
2. `decisions/DEC-001-data-api-contracts-proposal.md` — onaylanmış temel API/veri sözleşmesi.
3. `decisions/ADR-001-android-online-first.md` — Android online-first kararı.
4. `volumes/volume-01-2-erd-and-data-schema.md` — ERD ve tablo/alan modeli.
5. `volumes/volume-01-3-api-contracts.md` — endpoint sözleşmeleri.
6. `volumes/volume-01-4-openapi-dto-contract-tests.md` — DTO ve sözleşme testleri.
7. `volumes/volume-01-5-workflows-state-machines.md` — iş akışları ve durum makineleri.
8. `volumes/volume-01-15-canonical-registries.md` ve `volume-01-19-canonical-workflow-ids-state-registry.md` — kanonik kimlikler ve kayıtlar.
9. `volumes/volume-01-16-erd-dto-field-crosswalk.md` ve `volume-01-22-full-erd-constraint-index-dto-crosswalk.md` — alan/constraint/indeks çapraz kontrolü.
10. `volumes/volume-01-21-error-idempotency-response-registry.md` — hata ve idempotency sözleşmesi.
11. `volumes/volume-01-23-expiry-waste-cost-weight-unit-decisions.md` — expiry/fire/ağırlık kararları ve açık noktalar.
12. `volumes/volume-01-24-end-to-end-acceptance-tests-llm-handoff.md` — kabul testleri ve handoff sınırları.
13. Güncel güvenlik kararları: Cilt 1.26, 1.27, 1.28 ve 1.29.
14. `volumes/volume-01-30-volume-1-closure-and-llm-readability.md` — bu kapanış planı.

**Not:** Okuma sırası belgelerin birbirinin yerine geçtiği anlamına gelmez. Canonical registry ve açık karar sicili son durumu belirler; detay belgeleri sözleşme ayrıntılarını sağlar.

## 3. LLM'nin kod üretmeden önce sunması gereken rapor

LLM şu çıktıları üretmeden uygulama koduna başlamamalıdır:

- Okuduğu dosyaların listesi ve sürüm/tarih bilgisi.
- Kanonik tablo ve alanların özeti.
- Her endpoint için method/path/auth/permission/request/response/error/transaction özeti.
- Her iş akışı için ön koşul, durum geçişi, atomik işlem, stok hareketi ve rollback özeti.
- Tüm `OPEN`, `TBD`, `PROPOSED`, `BLOCKED` kararların listesi.
- Çelişen alanların kaynak belgeleri ve etkisi.
- Migration gerektiren değişikliklerin listesi — ancak migration dosyası üretmeden.
- Çalıştırılacak test katmanları ve beklenen sonuçlar.
- Kodlamaya başlanabilecek ve başlatılamayacak alanlar.

LLM, belgelere dayanarak çözülemeyen bir noktada varsayım üretmemelidir. Soruyu karar kaydı formatında sormalı ve etkilenen dosyaları belirtmelidir.

## 4. Cilt 1 kapanışı için kontrol grupları

### G1 — Veri modeli / API / workflow tutarlılığı
- [ ] ERD alanları ile DTO alanları arasında birebir çapraz kontrol tamam.
- [ ] FK, unique, check, index ve nullable kararları birbirini tutuyor.
- [ ] API endpoint'leri gerçek workflow durumlarıyla eşleşiyor.
- [ ] Her stok işlemi ledger ve balance güncellemesini aynı transaction içinde yapıyor.
- [ ] Lot genealogy çoktan çoğa ve miktar bilgili; izlenebilirlikte kaynak gerçek kayıtlar.
- [ ] Satış, sevkiyat ve ikinci seviye dağıtım ayrımları korunuyor.
- [ ] Fire kayıtları `butchering_waste_records` içinde; stok çıkışı ve maliyet uzlaştırması açık.
- [ ] Expiry politikası ve BY_VALUE formülü için karar var.
- [ ] Ağırlık toleransı, birim dönüşümü, reason code, multi-input lot ve rounding kararları var.

### G2 — Güvenlik / yetki
- [ ] Web token ve CSRF yaklaşımı kararlaştırıldı.
- [ ] Android güvenli token saklama kararlaştırıldı.
- [ ] Access/refresh/logout davranışı kararlaştırıldı.
- [ ] Disabled user ve mevcut token davranışı kararlaştırıldı.
- [ ] Parola/ilk giriş/sıfırlama davranışı kararlaştırıldı.
- [ ] Rate limit eşikleri ve dağıtık çalışma davranışı kararlaştırıldı.
- [ ] Endpoint bazlı permission matrisi bütün endpoint'leri kapsıyor.
- [ ] Liveness/readiness sözleşmesi kesin.
- [ ] Audit failure davranışı ve kritik POST idempotency kapsamı kesin.

### G3 — Sözleşme ve testler
- [ ] Error envelope, request_id ve status code davranışları tutarlı.
- [ ] OpenAPI şeması DTO ve gerçek endpoint'lerle eşleşiyor.
- [ ] API contract testleri endpoint ve error durumlarını kapsıyor.
- [ ] MySQL'e özgü davranışlar gerçek MySQL integration testleriyle doğrulanıyor.
- [ ] Satış idempotency ve conflict senaryoları test ediliyor.
- [ ] Recall sonrası satışı engelleme test ediliyor.
- [ ] Kabul senaryoları üç görevi uçtan uca kapsıyor.

### G4 — Teslimat / demo
- [ ] README temiz ortamda kurulum adımlarını içeriyor.
- [ ] Docker Compose yapılandırması ve `.env.example` güvenli.
- [ ] Seed/demo data deterministik ve yeniden kurulabilir.
- [ ] Test komutları ve beklenen sonuçlar belgeli.
- [ ] Public GitHub repo'da secrets veya gerçek kişisel veri yok.
- [ ] 15 dakikayı aşmayan demo akışı hazırlanmış.
- [ ] AI yöntemleri, baseline, metrik, örnek tahmin ve sınırlamalar açıklanmış.

## 5. Handoff için blocker politikası

Aşağıdaki kararlar kapanmadan ilgili kod alanı için “tamamlanmış sözleşme” iddiasında bulunulamaz:

- `BY_VALUE` butcher cost allocation formula.
- Expiry date applicability policy.
- Butchering weight tolerance and unit conversion.
- Waste reason code registry and multi-input lot rule.
- Web auth/cookie/CSRF, token lifecycle, disabled user.
- Password/first-login policy.
- Rate limit thresholds.
- Endpoint permission matrix and health endpoints.
- Audit failure semantics and idempotency scope for critical POSTs.
- ERD/DTO/OpenAPI/ORM final cross-check.

Kısmi ilerleme mümkün olabilir; ancak LLM bu alanları “BLOCKED — DECISION REQUIRED” olarak işaretlemeli ve ilişkili endpoint/migration davranışını tahmin etmemelidir.

## 6. Migration kapısı

**Kesin kural:** Cilt 1.2 ERD ve tablo/kolon listesi, Cilt 1.5 WF-01–WF-10 kararları, Cilt 1.16/1.22 çapraz kontrolleri ve güncel açık karar sicili bir arada gözden geçirilmeden Alembic migration dosyası üretilmeyecek ve veritabanı oluşturulmayacak/değiştirilmeyecektir.

Bu kontrol tamamlandığında dahi migration için kullanıcıdan ayrıca açık onay alınmalıdır. Bu belge migration izni değildir.

## 7. Kapanış kriteri

Cilt 1 ancak aşağıdaki koşulların tümü karşılandığında **CLOSED FOR IMPLEMENTATION** olarak işaretlenebilir:

1. Canonical registries tek güncel değer kaynağıdır.
2. Tüm açık kararlar ya kullanıcı tarafından kapatılmıştır ya da ilgili özellik açıkça MVP kapsamı dışına alınmıştır.
3. ERD ↔ DTO ↔ API ↔ workflow ↔ ORM/OpenAPI çapraz kontrolü yapılmıştır.
4. Kodlama LLM'si için tek giriş paketi ve açık blocker listesi vardır.
5. Kabul testleri kararları doğrulayacak şekilde tanımlanmıştır.
6. Migration kapısı ayrı onayla korunmaktadır.

Şu anki durum: **NOT CLOSED — OPEN DECISIONS REMAIN — MIGRATION NOT AUTHORIZED.**

## 8. Sonraki çalışma sırası

1. Güvenlik kararlarını (Cilt 1.26–1.29) endpoint sözleşmeleriyle karşılaştır.
2. Kararları kullanıcıyla tek tek kapat.
3. Cilt 1.23'teki expiry, BY_VALUE, ağırlık ve fire kararlarını tamamla.
4. Audit/idempotency/health/permission açıklarını kapat.
5. ERD–DTO–API–workflow–ORM/OpenAPI çapraz kontrolünü yap.
6. LLM handoff paketini ve test komutlarını son kez doğrula.
7. Migration için ayrı, açık kullanıcı onayı iste.
