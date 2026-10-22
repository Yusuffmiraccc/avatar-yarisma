# Cilt 1.25 — Açık Kararlar Kapanış Sicili

**Tarih:** 22 Ekim 2026  
**Durum:** Birleştirilmiş karar sicili; kararlar otomatik kapatılmamıştır.  
**Amaç:** Cilt 1.18–1.24 ve önceki sözleşmelerdeki açık noktaları tek kayıt altında toplamak; her madde için etki alanını, kapanış kanıtını ve sıradaki işlemi belirlemek.

## 1. Kullanım kuralları

1. Bu sicil, önceki belgelerde açık kalan maddeleri birleştirir; tek başına yeni iş kuralı onaylamaz.
2. Bir öneri, kullanıcı açıkça onaylamadıkça `PROPOSED` kalır.
3. Kaynaklar çelişirse kod yazan LLM seçim yapmaz; ilgili karar `BLOCKED` olur.
4. Her karar kapatıldığında bu dosya ve etkilenen ERD, API, DTO/OpenAPI, workflow, security ve test belgeleri birlikte güncellenir.
5. **Migration kapısı:** Cilt 1.2 ERD ile ilgili sözleşmelerin çapraz kontrolü ve WF-01–WF-10 açık iş akışı kararlarının çözülmesi öncesinde Alembic migration dosyası oluşturulmaz ve veritabanı oluşturulmaz/değiştirilmez. Sonrasında da proje sahibinin ayrıca açık onayı gerekir.

## 2. Durum sözlüğü

- `OPEN`: Karar gerekiyor.
- `PROPOSED`: Seçenek/öneri mevcut; proje sahibi onayı yok.
- `BLOCKED`: Bu karar verilmeden ilgili davranış güvenle uygulanamaz.
- `CLOSED`: Proje sahibi kararı onayladı ve ilgili belgeler/testler güncellendi.
- `OUT_OF_SCOPE_APPROVED`: Proje sahibi açıkça MVP kapsamı dışında bıraktı; kapsam dışı davranış yine de belgelenir.

## 3. Önceliklendirme

- **P0 — Veri bütünlüğü / güvenlik / yarışma kabul akışı:** Kapanmadan etkilenen backend davranışı ve nihai handoff engellenir.
- **P1 — Kritik API veya iş kuralı:** İlgili endpoint/iş akışı bloke edilir.
- **P2 — Dokümantasyon/operasyonel kesinlik:** Nihai handoff öncesinde kapanmalı; bağımsız ve etkilenmeyen işler ayrıca değerlendirilebilir.

## 4. Birleştirilmiş sicil

| ID | Öncelik | Karar alanı | Mevcut durum | Etkilenen alanlar | Kapanış için gereken kanıt |
|---|---|---|---|---|---|
| REG-125-01 | P0 | Ürün/lot son tüketim tarihi uygulanabilirliği | OPEN | ERD, ürün kartı, lot DTO, validation, test, seed | Uygulanabilirlik kuralı; `NULL`/zorunlu davranış; API ve test örnekleri; yeni kolon gerekiyorsa ayrıca onay |
| REG-125-02 | P0 | `BY_VALUE` maliyet dağıtımı ve fire maliyeti | BLOCKED | Kasaplık, maliyet servisleri, outputs/waste, raporlar, test | Tam formül; sıfır/değersiz çıktı davranışı; fireye ayrı maliyet ayrılması; yuvarlama örneği; toplam maliyet uzlaşması |
| REG-125-03 | P1 | Fire `reason_code` kanonik sözlüğü | OPEN | DB/DTO/validation, raporlar, test | Kod, açıklama ve aktif/pasif davranışı içeren tek liste; bilinmeyen kod testleri |
| REG-125-04 | P0 | Ağırlık dengesi toleransı | OPEN | Kasaplık iş akışı, validation, test | Toleransın sabit/konfigüre edilebilir oluşu, birimi, sınır davranışı ve gerekçesi |
| REG-125-05 | P1 | Ağırlık birimleri ve dönüşüm | OPEN | DTO, servis, DB canonical unit, test | İzin verilen birimler; kanonik birim; dönüşüm katsayıları; hassasiyet ve bilinmeyen birim davranışı |
| REG-125-06 | P1 | Fire kaydının birden fazla girdi lotuyla ilişkisi | OPEN | ERD, genealogy, fire DTO, maliyet dağıtımı | Her fire satırının tek lota bağlanması veya dağıtım tablosu seçimi; çoklu lot kabul testi |
| REG-125-07 | P1 | Maliyet/ağırlık dağıtımında yuvarlama ve kalan fark | PROPOSED | Kasaplık maliyeti, DECIMAL hesapları, test | Deterministik yuvarlama kuralı ve residual'ın hangi satıra atanacağı; sayısal test |
| REG-125-08 | P0 | Web istemcisinde token taşıma, saklama ve CSRF | OPEN | Web auth, FastAPI auth, CORS/CSRF, test | Tek model; cookie/header davranışı, SameSite/Secure/HttpOnly gerekiyorsa; CSRF koruması ve negatif testler |
| REG-125-09 | P1 | Android access token saklama | OPEN | Android auth, cihaz güvenliği | Kullanılacak güvenli saklama yaklaşımı ve logout/temizleme davranışı; istemci entegrasyon testi |
| REG-125-10 | P1 | JWT yaşam süresi, refresh ve logout | OPEN | Auth API, Android/web, test | Access token süresi; refresh olup olmayacağı; logout sonrası davranış; tekrar kullanım testi |
| REG-125-11 | P0 | Kullanıcı devre dışı bırakıldığında mevcut token | OPEN | Auth middleware, kullanıcı durumu, test | Her istekte kullanıcı aktiflik kontrolü veya onaylı alternatif; beklenen gecikme ve negatif test |
| REG-125-12 | P1 | Parola politikası ve ilk girişte parola değiştirme | OPEN | Kullanıcı yaşam döngüsü, auth DTO/UI sözleşmesi | Minimum gereklilikler, ilk giriş zorunluluğu ve parola değişiminden sonraki token davranışı |
| REG-125-13 | P1 | Login rate limit / brute-force koruması | OPEN | Auth endpoint, yapılandırma, test | Limit penceresi/eşiği, kilitleme veya gecikme yaklaşımı, hata yanıtı ve konfigürasyon varsayılanları |
| REG-125-14 | P0 | Endpoint başına tekil permission matrisi | OPEN | API, servis, OpenAPI, test | Her endpoint için permission key, rol listesi ve izin/ret testi; eski tabloların çelişkileri giderilmiş olmalı |
| REG-125-15 | P1 | Health liveness/readiness sözleşmesi | OPEN | Operasyon, auth, deployment, test | Endpoint yolları, anonim erişim kararı, status code ve minimal response; DB erişilemez test sonucu |
| REG-125-16 | P0 | Audit kaydı yazılamazsa kritik işlem davranışı | OPEN | Transaction, audit, satış/üretim/sevkiyat/recall | Atomiklik veya onaylı alternatif; failure injection testi ve gerekçesi |
| REG-125-17 | P1 | Kritik POST endpoint'lerinde idempotency | OPEN | API, DB unique key, servisler, test | Endpoint listesi; key zorunluluğu veya state-conflict kuralı; aynı/farklı body tekrar testi |
| REG-125-18 | P1 | Başarılı yanıt `request_id` standardı | OPEN | Middleware, response DTO, OpenAPI, test | Header/body konumu ve isim; tüm başarılı/hatalı yanıtlar için tek standart ve test |
| REG-125-19 | P1 | Ortak başarı/ hata response sözleşmesi | OPEN | Bütün endpoint DTO'ları, OpenAPI, istemciler | Başarı zarfı kullanımı veya endpoint bazlı açık kural; hata kodu/status eşlemesi ve contract test |
| REG-125-20 | P0 | Recall unblock/kaldırma işlemi | OPEN | Recall API, permission, audit, stok satışı | Endpoint/payload/rol; yalnızca yetkili onayla kaldırma; blokaj yokken davranış; idempotency ve audit testi |
| REG-125-21 | P0 | Tamamlanmış kayıtların iptal/düzeltme/ters kayıt kuralları | OPEN | Ledger, üretim, parçalama, sevkiyat, maliyet, audit | Kaynak bağlantısı, ters hareketler, maliyet etkisi, durum geçişi ve tekrar çağırma davranışı |
| REG-125-22 | P1 | Nullable alanların tam envanteri | OPEN | ERD, ORM, DTO, validation | Her alan için NULL anlamı, DB nullable, API nullable/omission ve testin eşleştirildiği tablo |
| REG-125-23 | P0 | ERD–ORM–constraint–index–DTO çapraz kontrolü | BLOCKED | ERD, SQLAlchemy, MySQL, DTO, OpenAPI | Her tablo/alan için tür/precision/nullability; PK/FK/UNIQUE/CHECK/index matrisi; gerçek metadata/OpenAPI karşılaştırması |
| REG-125-24 | P1 | Canonical state ve enum registry uyumu | OPEN | Üretim, satış, sevkiyat, recall, butchering, DTO | Tek enum listesi ve izinli geçiş tablosu; eski adların taraması; geçersiz geçiş testleri |
| REG-125-25 | P1 | Error-code registry | OPEN | API hata yanıtları, istemci davranışı, test | HTTP status + `error.code` + koşul + ilgili endpoint örneği; genel/özel kod sınırı |
| REG-125-26 | P1 | Sevkiyat–stok sahipliği ve çift düşümün önlenmesi | OPEN / cross-check gerekli | Dispatch, sales, stock ledger, traceability | Her fiziksel OUT hareketinin tek kaynağı; satış/sevkiyat akışlarının ayrımı; çift düşüm negatif testi |
| REG-125-27 | P1 | WF-01–WF-10 iş akışı kararları | OPEN | Cilt 1.5, API, state registry, test | Her WF için karar sahibi, önkoşul, transaction sınırı, başarısızlık/rollback, tekrar davranışı ve kabul testi |
| REG-125-28 | P2 | Seed/demo verisi ve beklenen sonuçların son kontrolü | OPEN | Seed, E2E testleri, yarışma demosu | PDF örnekleri, bilinen aritmetik tutarsızlıklar ve beklenen sonuçlar kayıtlı; test verisi ile belgeler aynı |
| REG-125-29 | P0 | Migration ve DB değişikliği için açık onay | BLOCKED — onay kapısı | Alembic, MySQL, deploy | Önce ERD/API/DTO/workflow çapraz kontrolü; WF-01–WF-10 çözümü; değişiklik planı; proje sahibinin ayrı ve açık onayı |

## 5. Bağımlılık sırası

1. **İş kuralı ve veri bütünlüğü:** REG-125-01–07, REG-125-16, REG-125-20–23, REG-125-26–27.
2. **Güvenlik ve API standardı:** REG-125-08–15, REG-125-17–19, REG-125-24–25.
3. **Kabul verisi ve nihai doğrulama:** REG-125-28.
4. **Migration kapısı:** REG-125-29; tüm önkoşullar tamamlanmadan açılamaz.

Bu sıra pratik bir çalışma önerisidir; aynı seviyedeki her maddenin bağımlılığı doğrulanmadan paralel uygulamaya geçilmez.

## 6. Karar oturumu formatı

Her açık madde için aşağıdaki kayıt tutulmalıdır:

- **ID ve soru:** Tek, karar verilebilir cümle.
- **Kaynakta bulunan gerçek:** Belge/PDF'de açıkça yazan bilgi.
- **Eksik bilgi/çelişki:** Kaynakların desteklemediği veya çeliştiği nokta.
- **Seçenekler:** En az iki uygulanabilir seçenek; her birinin etkisi.
- **Öneri:** Yalnızca öneri olarak işaretlenir, onay sayılmaz.
- **Proje sahibi kararı:** Açık onay metni veya `OPEN`.
- **Etkilenen belgeler:** Dosya adları ve güncellenecek bölümler.
- **Doğrulama:** Somut test/örnek ve beklenen sonuç.
- **Durum/tarih:** Yalnızca kanıt tamamlandığında `CLOSED`.

## 7. Henüz kapatılmayan önemli konuların özeti

- Kullanıcı, Cilt 1.23 kapsamında `BY_WEIGHT` dağıtımında ölçülen bütün ağırlık kategorilerinin (fire dahil) maliyet payı almasını onaylamıştır.
- Kullanıcı, `BY_VALUE` altında fireye ayrı maliyet payı verilebilmesi ilkesini onaylamıştır; ancak **değer tabanı ve tam formül açık değildir**.
- Fire için ayrı `butchering_waste_records` tablosu kararı verilmiştir.
- Son tüketim tarihi yalnızca uygulanabilir ürün/lotlarda zorunludur; uygulanabilirliği belirleyen kural henüz kesin değildir.
- Kullanıcının “sıradaki kısma geçelim” demesi açık kalan bu alt kararları kapatmış sayılmaz.
- Cilt 1.24'teki “EXTERNAL LLM HANDOFF NOT READY” durumu devam eder.

## 8. Migration öncesi zorunlu kapı

**Şu anda migration üretme veya veritabanını oluşturma/değiştirme yetkisi yoktur.** Migration öncesinde:

- [ ] Cilt 1.2 ERD, Cilt 1.3 API, Cilt 1.4 DTO/OpenAPI, Cilt 1.5 WF-01–WF-10, Cilt 1.16 ve Cilt 1.22 çapraz kontrol edildi.
- [ ] Bu sicilde migration'ı etkileyen P0/P1 kararlar kapatıldı veya proje sahibi tarafından açıkça MVP dışı bırakıldı.
- [ ] ORM metadata, constraint/index envanteri ve DTO/OpenAPI alanları eşleşiyor.
- [ ] Seed ve kabul testleri güncellendi.
- [ ] Değişiklik planı ve geri dönüş riski proje sahibine sunuldu.
- [ ] Proje sahibinden ayrıca açık migration/DB değişikliği onayı alındı.

Kutucuklar mevcut durumda tamamlandı olarak işaretlenmemiştir.

## 9. Sonraki çalışma adımı

Bir sonraki oturumda kayıtlar tek tek kapatılmalıdır. Önerilen ilk karar oturumu, kullanıcı güvenliği ve erişim davranışlarını birlikte ele alan **REG-125-08–REG-125-15** kümesidir. Ancak bu belge herhangi bir kümeyi otomatik olarak onaylamaz; kararlar proje sahibinden alınır, sonra kaynak ciltlere işlenir.

**Genel durum: OPEN DECISIONS REMAIN — HANDOFF NOT READY — MIGRATION NOT AUTHORIZED.**
