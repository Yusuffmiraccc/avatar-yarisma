# Cilt 1.31 — Birleştirilmiş Karar Önerisi ve Uygulamaya Hazırlık

**Tarih:** 22 Ekim 2026  
**Durum:** PROJE SAHİBİ TARAFINDAN TOPLU ONAYLANDI (22 Ekim 2026). Migration/veritabanı değişikliği onayı değildir.  
**Amaç:** Cilt 1'de kalan kararları tek belgede, uygulanabilir varsayılanlarla sunmak. Bu belge önerileri netleştirir; kullanıcının önceki “onaylamadığım kararları kapatma” talebi nedeniyle kullanıcı onayı olmadan OPEN kayıtlarını CLOSED yapmaz.

## 1. Bu belge nasıl kullanılmalı?

Her madde için:
- **Önerilen karar**: MVP için uygulanabilir varsayılan.
- **Gerekçe**: Neden bu seçeneğin önerildiği.
- **Etkisi**: Hangi modüller ve belgeler değişir.
- **Onay durumu**: Bu belge yazıldığı anda `PENDING_USER_APPROVAL`.

Proje sahibi 22 Ekim 2026'da SEC-01–SEC-09, API-01–API-03 ve DATA-01–DATA-06 önerilerini topluca onayladı. Bu onay, önerilerin proje için normatif karar olarak kabul edildiği anlamına gelir; mevcut ERD/DTO/OpenAPI/ORM ile teknik tutarlılık doğrulamasının yapıldığı veya migration/veritabanı değişikliğine izin verildiği anlamına gelmez. Teknik çelişki bulunursa karar sessizce değiştirilmez; blokaj raporlanır.

## 2. Web authentication ve deployment

### SEC-01 — Web token taşıma
**Önerilen karar:** Tek origin altında reverse proxy; web session/access credential `HttpOnly` cookie ile taşınır. HTTPS ortamında `Secure`; `SameSite=Lax` başlangıç değeri, cookie `Path=/` ve host-only cookie (Domain niteliği yok). Gerçek deployment topolojisiyle test edilmeden production-ready sayılmaz.

**Gerekçe:** Tek origin, CORS yüzeyini azaltır. HttpOnly, token'ın JavaScript ile doğrudan okunmasını önler. `SameSite=Lax` yaygın gezinme akışlarıyla uyumlu başlangıçtır; CSRF'nin tek savunması değildir.

**Ek şart:** Tüm state-changing isteklerde CSRF token doğrulaması; `Origin` kontrolü ek savunma olarak uygulanır. CORS, auth/CSRF yerine geçmez.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

### SEC-02 — CSRF yöntemi
**Önerilen karar:** Backend tarafından üretilen, session'a bağlanmış synchronizer CSRF token. Authenticated web API isteklerinde token özel header ile gönderilir; state-changing isteklerde zorunlu olur. Login akışında login-CSRF riski ayrıca ele alınır. Token değerleri loglanmaz.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

### SEC-03 — Android token saklama
**Önerilen karar:** Access/refresh token varsa Android Keystore ile korunan şifreli depoda tutulur. Düz DataStore içinde plaintext token tutulmaz. Logout'ta yerel token materyali temizlenir.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

### SEC-04 — Token yaşam döngüsü
**Önerilen karar:** MVP'de 15 dakikalık access token + 7 günlük refresh token; refresh token rotation ve server-side hashed token/session kaydı; logout refresh oturumunu iptal eder. Refresh tekrar kullanımı tespit edilirse ilgili token ailesi iptal edilir. Token süreleri konfigüre edilebilir; production öncesi gözden geçirilir.

**Gerekçe:** Access token'ın kısa ömrü çalınma etkisini sınırlar; refresh oturumu kullanıcı deneyimini iyileştirir. Bu yaklaşım biraz daha fazla backend state ve test gerektirir.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

### SEC-05 — Kullanıcı devre dışı bırakma ve rol değişimi
**Önerilen karar:** Her yetkili istek kullanıcı hesabının aktif durumunu ve token/session iptal durumunu doğrular. Kullanıcı devre dışı bırakıldığında veya güvenlik nedeniyle parolası sıfırlandığında aktif refresh oturumları iptal edilir. Yetki kontrolü başarısızsa istek güvenli biçimde reddedilir.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

### SEC-06 — Parola ve ilk giriş
**Önerilen karar:** Parolalar Argon2id gibi güncel parola hash algoritmasıyla salt'lı saklanır; düz metin veya geri çözülebilir parola saklanmaz. İlk girişte parola değiştirme zorunludur. Parola değişimi tamamlanana kadar kullanıcıya yalnızca parola değiştirme endpoint'i ve logout gibi izin verilen auth işlemleri açılır. MVP'de e-posta tabanlı parola sıfırlama kapsam dışı; admin tarafından resetlenen geçici parola/force-change akışı belgelenir.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

### SEC-07 — Login rate limit
**Önerilen karar:** Hesap tanımlayıcısı ve IP bazlı limit. Başlangıç eşiği: hesap başına 5 başarısız deneme / 15 dakika; IP başına 30 başarısız deneme / 15 dakika; artan bekletme uygulanabilir. Hesap var/yok bilgisi yanıtla sızdırılmaz. Reverse proxy arkasında yalnızca güvenilir proxy'den gelen forwarded IP başlıkları kullanılır. Çok instance'lı deployment varsa rate-limit state paylaşılır.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

## 3. Permission matrisi ve health endpoint'leri

### SEC-08 — Yetki kaynağı
**Önerilen karar:** Cilt 1.9 endpoint-permission matrisi tek canonical permission kaynağı olur. Her endpoint için `method`, `path`, `permission_key`, `allowed_roles`, `auth_required`, object-scope rule, deny status ve test ID zorunlu. Endpoint matrisi ile test listesi tam kapsama ulaşmadan security handoff tamamlanmaz.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required; mevcut Cilt 1.9 ile satır satır çapraz kontrol yapılmalı.

### SEC-09 — Health
**Önerilen karar:**
- `GET /health/live`: anonim; süreç canlıysa `200`, DB sorgusu yapmaz.
- `GET /health/ready`: anonim; gerekli bağımlılıklar hazırsa `200`, değilse `503`; MySQL bağlantısı kontrol edilir.
- Response yalnızca `status`, `checks` gibi secrets içermeyen alanlar sunar; connection string, host secret, stack trace göstermez.
- API prefix standardı gereği bu yolların `/api/v1` altında mı yoksa kökte mi olacağı tek yerde kararlaştırılır. **Öneri:** altyapı health endpoint'leri kökte (`/health/live`, `/health/ready`), iş API'si `/api/v1` altında.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

## 4. Audit, idempotency ve error davranışı

### API-01 — Audit kayıt hatası
**Önerilen karar:** Kritik iş işlemi audit kaydı gerektiriyorsa audit insert aynı transaction içinde yapılır. Audit insert başarısız olursa iş işlemi de rollback olur. Güvenlik logları ve uygulama telemetrisi ayrı kanallardır; bunlar DB audit kaydının yerine geçmez.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

### API-02 — Idempotency kapsamı
**Önerilen karar:** Satış oluşturma için `Idempotency-Key` zorunlu; aynı key + aynı canonical request body ilk yanıtı döndürür, aynı key + farklı body `409 Conflict`. Ek olarak stok/finansal etkisi olan ve istemci retry'siyle çift kayıt yaratabilecek kritik POST endpoint'leri endpoint bazında işaretlenir ve idempotency zorunluluğu açıkça tanımlanır. Tüm POST'lara gelişigüzel zorunlu kılınmaz.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required; endpoint listesiyle çapraz kontrol gerekir.

### API-03 — Hata sözleşmesi
**Önerilen karar:** Mevcut ortak hata zarfı korunur: `error.code`, `error.message`, isteğe bağlı `error.details`, `request_id`. `request_id` her yanıtla ilişkilendirilir; response field isimleri snake_case; kullanıcıya dönen mesajlar secret/stack trace içermez. Validation, auth, permission, conflict, not-found, business-rule ve internal error senaryoları contract testleriyle doğrulanır.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required; Cilt 1.21 ile eşleştirilmelidir.

## 5. Veri ve iş kuralı açık kararları

### DATA-01 — Son tüketim tarihi
**Önerilen karar:** Ürün kartında `requires_expiry_date` boolean alanı. `true` ise lot oluşturma/kabul işleminde `expiry_date` zorunlu; `false` ise `NULL` kabul edilir. Bu alan ürün seviyesinde yönetilir; ürünün politikası değiştiğinde geçmiş lotların verisi otomatik değiştirilmez. Alanın mevcut ERD'de bulunup bulunmadığı migration öncesi doğrulanır.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

### DATA-02 — Butchering BY_WEIGHT maliyet dağıtımı
**Önerilen karar:** CUT, stok takipli BYPRODUCT ve WASTE dahil bütün ölçülmüş ağırlık kategorileri payda olur. Kategori maliyeti = toplam satın alma maliyeti × kategori ağırlığı / toplam ölçülmüş ağırlık. Örnek: €100, 8 kg CUT, 1 kg BYPRODUCT, 1 kg WASTE → €80, €10, €10. Yuvarlama artığı deterministik olarak son allocation satırına atanır; toplam tam olarak toplam maliyete eşit olmalıdır.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22. BY_WEIGHT ilkesi ve bu belgedeki deterministik residual kuralı onaylandı; teknik çapraz kontrol gerekir.

### DATA-03 — Butchering BY_VALUE maliyet dağıtımı
**Önerilen karar:** Kullanılabilir satış/değer referansı bulunan CUT ve stok takipli BYPRODUCT için değer tabanlı pay hesaplanır. WASTE için bağımsız satış değeri yoksa WASTE'nin ayrı maliyeti, değer taşıyan stok çıktılarının değer payları toplamı üzerinden kalan maliyetin dağıtılmasıyla hesaplanır mı, yoksa ayrı bir değer/standart kayıp maliyeti mi kullanılır sorusu iş kuralını değiştirir.

**Önerilen MVP kararı:** `BY_VALUE` modunda WASTE'nin `allocated_cost` değeri sıfır kabul edilir; toplam satın alma maliyeti yalnızca değer taşıyan stok çıktıları arasında dağıtılır. Waste kaydı ağırlık dengesi ve audit için tutulur, fakat cost allocation totaline eklenmez. Bu, kullanıcının önceki “fire ayrı maliyet dağıtımı olabilir ama satılabilir stok çıktısı maliyeti gibi gösterilmesin” ilkesinin en basit uygulanabilir yorumudur; finansal raporlamada fire maliyetini ayrı göstermek isteniyorsa farklı formül gerekir.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required — özellikle finansal anlamı nedeniyle onaysız uygulanmaz.

### DATA-04 — Ağırlık toleransı ve birimler
**Önerilen karar:** Canonical weight unit `kg`; gramdan kilogram dönüşümü backend'de yapılır. `g` ve `kg` kabul edilir; saklama canonical kg. Tolerans konfigüre edilebilir; varsayılan `0 kg` (tam denge). Tolerans dışı fark için işlem bloke olur veya yetkili kullanıcı açıklamalı variance kaydı girer; sessiz fark kabul edilmez.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

### DATA-05 — Waste reason codes
**Önerilen başlangıç listesi:** `TRIMMING_LOSS`, `BONE_WASTE`, `CONTAMINATION`, `SPOILAGE`, `PROCESS_LOSS`, `OTHER`. `OTHER` seçilirse açıklama zorunlu. Liste konfigürasyon/registry üzerinden yönetilir; keyfi serbest metin kodu kabul edilmez.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

### DATA-06 — Birden fazla input lot ve rounding
**Önerilen karar:** Her butchering waste/output satırı tek bir kaynak input lot ile ilişkilendirilir. Birden çok kaynak varsa ayrı satırlar oluşturulur; aynı işlemde lot bazında ağırlık ve maliyet payı korunur. Tüm maliyet allocation satırlarında sabit precision/rounding politikası kullanılır; toplamı eşitleyen residual, deterministik olarak sıralamadaki son allocation satırına eklenir.

**Durum:** APPROVED_BY_PROJECT_OWNER — 2026-10-22; technical cross-check required.

## 6. LLM'nin belge okuma ve kodlama protokolü

Kodlama LLM'sine şu protokol zorunlu olarak verilir:

1. README ve karar kayıtlarını oku; dosya manifestini çıkar.
2. Canonical registry'deki karar durumlarını çözümle.
3. ERD ↔ DTO ↔ API ↔ workflow ↔ ORM/OpenAPI crosswalk raporu hazırla.
4. `OPEN`, `PENDING_USER_APPROVAL`, `TBD`, `BLOCKED` kararları listele.
5. Çelişki gördüğünde kendi başına düzeltme yapma; ilgili kayıt ve etkilenen endpoint/tabloyu raporla.
6. Açık karar içermeyen, onaylanmış modüllerde kod yazmaya başlayabilir.
7. Açık kararların etkilediği alanlarda migration veya davranış uyduramaz.
8. Her kodlama turunda hangi belgeleri uyguladığını ve hangi testlerin geçtiğini raporlar.

## 7. Cilt 1 kapanış kapısı

Cilt 1 ancak aşağıdakiler tamamlanınca uygulamaya hazır sayılır:

- Bu paketteki kararlar onaylandı veya revize edildi.
- Canonical registry, ERD, API, DTO, workflow, security matrix ve testler aynı kararları yansıtıyor.
- Son çapraz kontrol raporu yeni çelişki bulmuyor.
- MySQL integration test planı hazır.
- Handoff manifesti ve kurulum/test komutları tamam.
- Kullanıcı ayrıca migration için açık onay verdi.

**Şu anki durum:** Bu belge birleştirilmiş karar önerisidir; onay bekliyor. Migration oluşturulmadı, veritabanı değiştirilmedi.

## 8. Proje sahibinden gereken yanıt

Lütfen aşağıdaki iki biçimden biriyle yanıt ver:

- **“Cilt 1.31 önerilerini topluca onaylıyorum.”** — önerileri onaylı karar olarak kayda geçirip ilgili canonical belgeleri güncelleyeceğim; migration için ayrıca onay isteyeceğim.
- **“Şu kararları değiştir: SEC-..., DATA-...”** — yalnızca belirtilen kararları revize edip kalanlarını ayrı ayrı pending bırakacağım.

Bu yanıt gelmeden önceki “diğer güvenlik kararlarını kapatma” kuralına uygun olarak hiçbir pending karar CLOSED işaretlenmez.


## 8. Onay kaydı — 22 Ekim 2026

Proje sahibi aşağıdaki karar önerilerinin tamamını topluca onayladı:
- SEC-01–SEC-09
- API-01–API-03
- DATA-01–DATA-06

Bu onay yalnızca kararları kapsar. Aşağıdakiler **onaylanmış değildir**:
1. Alembic migration dosyalarının oluşturulması,
2. MySQL veritabanının oluşturulması veya değiştirilmesi,
3. Cilt 1.2 ERD/tablo/alan tanımlarının ve Cilt 1.5 WF-01–WF-10 akışlarının migration öncesi kapıdan geçirilmesi.

Bir karar mevcut doküman/şema ile çelişirse mevcut şemayı sessizce değiştirme. Cilt 1.32 çapraz kontrol raporuna `BLOCKED` olarak yaz ve etkilediği kaynakları belirt.
