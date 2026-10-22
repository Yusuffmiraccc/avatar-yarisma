# Cilt 1.32 — Onaylı Kararlar ve Çapraz Kontrol Defteri

**Tarih:** 22 Ekim 2026  
**Durum:** Karar onayı kaydedildi; dokümanlar arası statik kontrol başlatıldı. Cilt 1 henüz kapalı değildir.  
**Migration / veritabanı:** YASAK/KAPALI — kullanıcı bu işlem için onay vermemiştir.

## 1. Kullanıcı onayı

Proje sahibi Cilt 1.31 önerilerini topluca onayladı. Onay kapsamı:
- `SEC-01`–`SEC-09`: web auth, CSRF, Android token saklama, token yaşam döngüsü, kullanıcı devre dışı/rol değişimi, parola ve ilk giriş, login rate limit, izin matrisi kaynağı, health endpoint'leri.
- `API-01`–`API-03`: audit transaction davranışı, idempotency kapsamı, ortak hata sözleşmesi.
- `DATA-01`–`DATA-06`: son tüketim tarihi politikası, BY_WEIGHT maliyet dağıtımı, BY_VALUE maliyet dağıtımı, ağırlık toleransı/birim, fire nedenleri, çoklu input lotları ve yuvarlama artığı.

Bu kararlar normatiftir. Ancak teknik çapraz kontrol, uygulanabilirlik ve mevcut belgelerdeki tüm eski ifadelerin giderildiği anlamına gelmez.

## 2. Onaylı kararların normatif özeti

| ID | Normatif karar | Uygulama kontrolü |
|---|---|---|
| SEC-01 | Web tek-origin reverse proxy arkasında; credential HttpOnly cookie; HTTPS'te Secure; SameSite=Lax; host-only, Path=/ | Gerçek proxy/origin ayarı ve cookie davranışı entegrasyon testinde doğrulanacak |
| SEC-02 | Session'a bağlı synchronizer CSRF token; state-changing web isteklerinde özel header; Origin ek savunma | Login-CSRF ve token yenileme akışı test edilecek |
| SEC-03 | Android tokenları Android Keystore ile korunan şifreli depoda; plaintext token DataStore'a yazılmaz | Seçilen kütüphane ve Android testleri doğrulanacak |
| SEC-04 | Access 15 dakika; refresh 7 gün; refresh rotation; server-side hash/session; logout revoke; reuse'da token ailesini iptal | Token modeli ve revocation kontrolü ERD/API ile karşılaştırılacak |
| SEC-05 | Her yetkili istekte aktif kullanıcı ve token/session durumu doğrulanır; disable/parola reset refresh session'larını iptal eder | Cache ve rol değişimi davranışı açık testle kanıtlanacak |
| SEC-06 | Güncel parola hash'i (Argon2id önerisi); ilk girişte parola değişimi; geçici admin parolası; e-posta reset MVP dışı | Endpoint ve kullanıcı durum makinesi ile karşılaştırılacak |
| SEC-07 | Başlangıç limitleri: hesap başına 5 başarısız deneme/15 dk; IP başına 30/15 dk; enumeration engeli; yalnız güvenilir proxy IP'si | Çok instance rate-limit store ihtiyacı dağıtımda kontrol edilecek |
| SEC-08 | Cilt 1.9 endpoint izin matrisi tek canonical kaynak; her endpoint için auth, izin, roller, scope, deny status ve test ID | Cilt 1.3/1.4/1.9/1.20 satır satır karşılaştırılacak |
| SEC-09 | `/health/live` anonim, DB sorgusuz 200; `/health/ready` anonim, dependency hazırsa 200, değilse 503; hassas bilgi yok; yollar kökte | Eski `/api/v1` health tanımları bulunursa belgeler düzeltilmeli |
| API-01 | Kritik iş kaydı ve zorunlu audit aynı DB transaction'ında; audit insert başarısızsa rollback | Her kritik workflow transaction tablosu ile eşleştirilecek |
| API-02 | Satış ve endpoint matrisinde işaretli retry-riskli kritik POST'larda Idempotency-Key; aynı key/body ilk sonucu döndürür, farklı body 409 | Cilt 1.21 idempotency kayıt modeli ve endpoint kapsamı doğrulanacak |
| API-03 | Ortak hata zarfı `error.code`, `error.message`, isteğe bağlı `error.details`, `request_id`; snake_case; secret/stack trace yok | Cilt 1.21 ve OpenAPI örnekleriyle doğrulanacak |
| DATA-01 | Ürün kartı `requires_expiry_date`; true ise lotta expiry zorunlu, false ise null; geçmiş lotlar ürün politikasındaki değişiklikle otomatik değişmez | Cilt 1.2 alan varlığı, DTO ve lot doğrulaması kontrol edilecek |
| DATA-02 | BY_WEIGHT paydasında CUT + stoklu BYPRODUCT + WASTE ölçülmüş ağırlıklarının tamamı; deterministik residual son allocation satırına; maliyet toplamı tam uzlaşır | Cilt 1.17/1.23 ve Cilt 1.2/1.3 şeması/DTO kontrol edilecek |
| DATA-03 | BY_VALUE'da WASTE `allocated_cost=0`; toplam satın alma maliyeti değer taşıyan stok çıktıları arasında dağıtılır; fire ağırlık dengesi/audit için tutulur | Finansal gösterim ve alan kısıtlarıyla çelişki kontrolü yapılacak |
| DATA-04 | Kanonik ağırlık kg; g ve kg kabul edilir, dönüşüm kg'a yapılır; varsayılan tolerans 0 kg; fark sessiz kabul edilmez, ret veya yetkili açıklamalı variance | API birim alanı ve variance workflow'ları kontrol edilecek |
| DATA-05 | Fire reason codes: `TRIMMING_LOSS`, `BONE_WASTE`, `CONTAMINATION`, `SPOILAGE`, `PROCESS_LOSS`, `OTHER`; OTHER için açıklama zorunlu | Enum/DTO/DB kısıtları kontrol edilecek |
| DATA-06 | Her output/waste satırı tek kaynak lota bağlı; birden çok input lot için ayrı satırlar; residual deterministik son allocation satırında | ERD FK/unique/index ve allocation testleri kontrol edilecek |

## 3. Bilinen çapraz kontrol alanları

Bu belge bir statik doküman incelemesi kaydıdır; çalışma zamanı veritabanı, SQLAlchemy metadata veya üretilmiş OpenAPI üzerinde test çalıştırıldığı iddiasında bulunmaz.

1. **Cilt 1.2 ERD ↔ Cilt 1.3 API ↔ Cilt 1.4 DTO/contract tests:** alanların varlığı, nullable, enum, ID ve quantity/cost tipleri doğrulanmalı.
2. **Cilt 1.5 WF-01–WF-10 ↔ Cilt 1.19 workflow registry:** workflow ID, state, transition ve yan etkiler aynı olmalı.
3. **Cilt 1.8 ↔ Cilt 1.9 ↔ Cilt 1.20:** auth, roles, permission key, deny status ve health endpoint sözleşmeleri aynı olmalı.
4. **Cilt 1.21 ↔ Cilt 1.3/1.4:** idempotency key scope, replay davranışı, conflict response ve error envelope aynı olmalı.
5. **Cilt 1.17/1.23 ↔ Cilt 1.2/1.3:** `butchering_waste_records`, expiry policy, weight units, reason codes, cost allocation alanları/DTO'ları aynı olmalı.
6. **Cilt 1.24 acceptance tests ↔ canonical registries:** her normatif karar için en az bir olumlu test ve uygun olumsuz test olmalı.
7. **Cilt 1.27/1.29 deployment ↔ SEC-01/SEC-02/SEC-07/SEC-09:** origin, proxy, secure cookie, CSRF, forwarded IP ve health paths uyumlu olmalı.

## 4. Migration öncesi zorunlu blokajlar

Aşağıdakiler bu ciltte kapatılmış sayılmaz:
- Cilt 1.2 ERD'nin tablo ve alan bazında tam karşılaştırması.
- Cilt 1.5 WF-01–WF-10 iş akışlarının Cilt 1.19 ile tam eşleştirilmesi.
- ORM metadata / OpenAPI schema / DTO ve örnek payload otomatik diff/testi.
- Kullanıcıdan migration oluşturmak için ayrı açık izin.
- Kullanıcıdan veritabanını oluşturma/değiştirme için ayrı açık izin (gerekirse migration izninden ayrıca sorulmalı).

**Kesin yasak:** Bu cilt veya Cilt 1.31 onayı migration üretme, migration çalıştırma, veritabanı oluşturma veya değiştirme yetkisi vermez.

## 5. Sıradaki somut işlem

Cilt 1.33'te kanonik dokümanları dosya düzeyinde tarayıp `PASS`, `CONFLICT`, `MISSING`, `NOT_RUNTIME_VERIFIED` durumlarıyla kanıtlı bir crosswalk üret. Yalnızca belge metinlerini güncelle; migration/DB yok. Çelişkili eski sözleşmeler varsa canonical kararı öne çıkarıp revizyon günlüğüne ekle; alan veya workflow anlamı belirsizse `BLOCKED` olarak tut.

## 6. Tamamlanma ölçütü

Cilt 1 ancak şu koşullarda kapanabilir:
- Tüm `CONFLICT` ve `MISSING` durumları ya giderilmiş ya da bilinçli, onaylı kapsam dışı olarak kaydedilmiş;
- WF-01–WF-10 ve ERD alan crosswalk'ı tam;
- OpenAPI/DTO ve kabul test matrisi aynı kararları kullanıyor;
- LLM handoff dosyası kanonik kaynak sırasını ve yasak varsayımları içeriyor;
- Migration kapısı açıkça kapalı tutuluyor; bu aşamada gerçek migration veya DB değişikliği yapılmıyor.
