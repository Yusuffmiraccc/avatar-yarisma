# Cilt 1.20 — Authentication, Permissions & Health Contract Reconciliation


> **Normatif güncelleme — 22 Ekim 2026 (Cilt 1.32):** Bu belgedeki daha eski ve çelişen taslak ifadeler için `volume-01-32-approved-decisions-and-cross-check.md` ile Cilt 1.31'in onay kaydı önceliklidir. Bu not doküman sözleşmesini günceller; migration veya veritabanı değişikliği izni değildir.

**Tarih:** 22 Ekim 2026  
**Durum:** Güvenlik sözleşmesi uzlaştırma cildi; uygulama öncesi açık maddeler içerir  
**Kapsam:** FastAPI kimlik doğrulama, JWT access token, kullanıcı aktifliği, endpoint yetkileri, Android/web token taşıma, health endpoint'leri ve güvenlik testleri  
**Bağlı belgeler:** Cilt 1.3, 1.4, 1.5, 1.8, 1.9, 1.18, 1.19; `ADR-001-android-online-first.md`; `DEC-001-data-api-contracts-proposal.md`

## 1. Amaç ve normatif kullanım

Bu cilt, daha önce farklı belgelerde bulunan kimlik doğrulama ve güvenlik kararlarını tek sözleşmede toplar. Bu ciltteki her madde şu etiketlerden biriyle değerlendirilir:

- **ONAYLI:** Proje sahibinin önceki açık onayı veya kaynak ciltlerde bağlayıcı olarak kaydedilmiş karar.
- **MEVCUT SÖZLEŞME:** Cilt 1.3 ve ilişkili ciltlerde mevcut API davranışı; çelişki kontrolüne tabidir.
- **AÇIK KARAR:** Kaynaklar kesin bir uygulama davranışını desteklemiyor. Kodlama LLM'si bunu kendisi seçemez.
- **ÖNERİ:** Değerlendirilmek üzere sunulan seçenek; proje sahibi onaylamadıkça bağlayıcı değildir.

Bu cilt gerçek kullanıcı/rol endpoint'leri eklemez ve ERD'de bulunmayan tablo/kolonları kendiliğinden onaylamaz. Herhangi bir güvenlik kararı yeni bir kolon, enum veya tablo gerektiriyorsa Cilt 1.2/1.3/1.4/1.16 güncellenmeden migration üretilemez.

## 2. Kanonik kimlik doğrulama sözleşmesi

| Konu | Kanonik sözleşme | Durum |
|---|---|---|
| Login | `POST /api/v1/auth/login`; email/login ve parola backend'de doğrulanır | MEVCUT SÖZLEŞME |
| Access token | İmzalı JWT; korumalı istekte `Authorization: Bearer <access_token>` | ONAYLI |
| Token süresi | 15 dakika; yanıt `expires_in: 900`; refresh 7 gün + rotation | ONAYLI — Cilt 1.31/1.32 |
| Refresh token | MVP'de yok | ONAYLI |
| Süresi dolan token | Korumalı endpoint `401` döndürür; kullanıcı yeniden giriş yapar | ONAYLI |
| Logout | `POST /api/v1/auth/logout`; `204`; istemci token'ı siler | ONAYLI |
| Server-side revoke | MVP'de blacklist/revoke mekanizması yok; logout token'ı anında geçersiz kıldığı iddia edilmez | ONAYLI |
| Aktör kimliği | `sub` gibi doğrulanmış token claim'inden alınır; request body'deki `user_id` aktör kimliği olamaz | ONAYLI |
| Token loglama | Token, parola, signing secret loglara yazılmaz | ONAYLI |
| Yetkilendirme | Backend'de her korumalı endpoint için kontrol edilir; varsayılan ret | ONAYLI |
| Algoritma | İzin verilen JWT algoritması server config ile sabitlenir; token header'ı algoritmayı seçemez | GÜVENLİK GEREKSİNİMİ |
| Issuer/audience | Yapılandırılmış değerler varsa doğrulanır; yanlış değer `401` üretir | Mevcut güvenlik taslağı; tam config değerleri açık |

### 2.1 Login yanıtı

Cilt 1.3 örneğiyle uyumlu olarak en az `access_token`, `token_type: "Bearer"`, `expires_in: 900` ve kullanıcıya ilişkin güvenli `roles` bilgisi döndürülür. Gerçek parola veya gerçek token örneği dokümantasyona/seed dosyasına konmaz.

**AÇIK KARAR AUTH-01:** Login başarısızlığında kullanıcı bulunamaması ile parolanın yanlış olması dışarıya aynı genel kimlik bilgisi hatasıyla mı gösterilecek? Cilt 1.9 rate-limit önerisiyle birlikte Cilt 1.21 error registry'de kesinleştirilecek. Güvenlik önerisi: dış yanıt aynı olsun.

### 2.2 Kullanıcı aktifliği ve mevcut token

Cilt 1.8 kullanıcı durumlarını `PENDING`, `ACTIVE`, `DISABLED` olarak önerir; bu durumların veri modelinde kesin varlığı doğrulanmadan yeni enum/kolon oluşturulamaz. Mevcut güvenlik taslağı disabled kullanıcının yeni token alamayacağını belirtir; daha önce verilmiş token'ın davranışı ise açık kalmıştır.

**AÇIK KARAR AUTH-02:** Her korumalı istekte kullanıcının güncel `ACTIVE` durumunu veritabanından (veya açıkça tanımlanmış güvenilir cache'ten) kontrol etmek zorunlu mu? Öneri: MVP'de kullanıcı aktifliğini her korumalı istekte kontrol et; böylece disabled hesapların token süresi dolana kadar kullanılmaya devam etmesi engellenir. Bu karar performans/cache stratejisini etkiler; onaysız uygulanmış sayılmaz.

### 2.3 Admin bootstrap

Cilt 1.8, ilk admin hesabının güvenli CLI/kurulum komutuyla oluşturulmasını önerir. Public admin-registration endpoint'i mevcut sözleşmede tanımlı değildir ve eklenmeyecektir.

**AÇIK KARAR AUTH-03:** Bootstrap komutunun davranışı, ilk admin zaten varsa ne yapacağı, parola kaynağı ve tekrar çalıştırma güvenliği Cilt 1.24 devir paketinde operasyonel kabul kriterine bağlanacaktır. Öneri: tekrar çalıştırma mevcut admin parolasını/rolünü sessizce değiştirmesin; açık hata versin.

## 3. İstemci bazlı token taşıma ve saklama

### 3.1 Android

- Korumalı API isteklerinde `Authorization: Bearer <access_token>` başlığı kullanılır.
- Token URL query string'e, loglara veya açık dosyalara yazılmaz.
- Logout'ta yerel token ve geçici oturum durumu temizlenir.
- SQLite/Room'da token saklanmaz.
- **AÇIK KARAR AUTH-04:** ADR-001'de DataStore uygulama ayarları içindir; DataStore tek başına güvenli sır deposu sayılmaz. Android access token için şifreli/platform korumalı saklama yöntemi (ör. Android Keystore destekli çözüm) Cilt 4'te uygulanabilirlik ve bağımlılık seçimiyle kesinleştirilmeli. Bu cilt, token'ı düz metin DataStore'da saklamayı onaylamaz.

### 3.2 Web

- Access token URL, query string veya browser console log'una yazılmaz.
- API çağrılarında kimlik bilgileri yalnızca açıkça tanımlanmış güvenli taşıma yöntemiyle gönderilir.
- Cilt 1.9'da web için `HttpOnly; Secure; SameSite` cookie ve CSRF koruması önerilmiştir; ancak bu karar tüm belgelerde bağlayıcı bir web auth sözleşmesi olarak kapatılmamıştır.

**AÇIK KARAR AUTH-05:** Web oturumu için aşağıdaki iki seçenekten biri proje sahibi tarafından seçilmelidir:

1. **ÖNERİ A — HttpOnly cookie:** `Secure`, uygun `SameSite` politikası ve cookie tabanlı kimlik doğrulama kullanılır; state-changing isteklerde CSRF savunması ayrıca tanımlanır. Token JavaScript tarafından okunmaz.
2. **ÖNERİ B — Bearer token:** Token web istemci belleğinde tutulur ve `Authorization` başlığıyla gönderilir; kalıcı saklama ve XSS etkisi ayrıca değerlendirilir. `localStorage` içinde uzun ömürlü token saklamak önerilmez.

Seçim yapılmadan kodlama LLM'si iki yöntemi karıştıramaz ve web auth katmanını nihai kabul edemez. Bu karar Android Bearer sözleşmesini değiştirmez.

## 4. Kanonik roller ve yetkilendirme ilkeleri

Kanonik rol kümesi:

- `ADMIN`
- `OPERATOR`
- `SALES`
- `TRACEABILITY_MANAGER`
- `VIEWER`

Bağlayıcı ilkeler:

1. Varsayılan ret; açık izin yoksa korumalı işlem reddedilir.
2. UI'da buton gizlemek backend authorization yerine geçmez.
3. Rol, iş kurallarını atlama yetkisi vermez.
4. `401`/`403` alan istek stok, maliyet, durum, audit veya genealogy üzerinde kısmi iş etkisi bırakmaz.
5. Hassas okuma endpoint'lerinde de rol ve kaynak kapsamı kontrol edilir.
6. `VIEWER` değiştirici operasyon yapamaz.
7. Kullanıcı kimliği request body'den aktör olarak kabul edilmez.
8. Permission kontrolü ortak, test edilebilir katmanda uygulanır; router bazında unutulabilir dağınık kontroller tek yöntem sayılmaz.
9. Recall activation, recall resolution, lot unblock/release ve reversal/correction ayrı hassas eylemlerdir; uygun permission ve audit gerektirir.

### 4.1 Önceki revizyondan bağlayıcı endpoint izinleri

Cilt 1.9 revizyon 1.11'de onaylanmış olarak kaydedilen rol kararları:

| İşlem | İzinli roller / kural | Durum |
|---|---|---|
| Genel stok düzeltme | `ADMIN` | ONAYLI |
| Sevkiyat oluşturma | `ADMIN`, `SALES` | ONAYLI |
| Sevkiyat dispatch | `ADMIN`, `SALES` | ONAYLI; WF-03 stok sahipliğiyle uyumlu |
| AI tahmini başlatma | `ADMIN`, `OPERATOR` | ONAYLI |
| AI tahmin sonucunu okuma | `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`, `VIEWER`; `SALES` reddedilir | ONAYLI |
| Recall çözme | Recall yönetme/çözme izni bulunan yetkili rol; lot otomatik açılmaz | Temel kural ONAYLI; exact permission crosswalk gerekli |
| Lot unblock/release | Ayrı permission ve audit; önerilen roller `ADMIN` ve yetkili `TRACEABILITY_MANAGER` | Exact permission key/endpoint açık |

Cilt 1.8 ve 1.9'da kalan endpoint düzeyi rol farkları tek başına bu ciltte tahminle kapatılmamıştır. Tam endpoint–permission eşlemesi Cilt 1.22 çapraz kontrolünde, mevcut endpoint'ler üzerinden tamamlanmalıdır.

### 4.2 Permission registry gereksinimi

Her API endpoint'i için aşağıdaki alanlar tek bir kanonik matriste bulunmalıdır:

- `method`, `path`, operation ID
- public/authenticated/internal erişim türü
- required permission key
- izinli roller
- kaynak kapsamı/ownership kontrolü
- hassas veri alanları ve response minimization kuralı
- audit zorunluluğu
- olumlu ve olumsuz test kimlikleri

Cilt 1.3'te bulunmayan endpoint bu ciltte yeni API olarak eklenmez. Eksik izin anahtarı varsa `TBD` olarak raporlanır; mevcut endpoint'e yeni davranış eklenmesi ayrıca API cildine işlenir.

## 5. Health endpoint sözleşmesi

| Endpoint | Kimlik doğrulama | Amaç | Yanıt/yan etki | Durum |
|---|---|---|---|---|
| `GET /health/live` | Public | Sürecin istek karşılayabildiğini belirtmek | Sağlıklıysa `200`; DB host, credentials, stack trace veya altyapı ayrıntısı yok | MEVCUT SÖZLEŞME |
| `GET /health/ready` | Public | Gerekli bağımlılıkların hazır olup olmadığını belirtmek | Hassas dependency/DB ayrıntısı dış kullanıcıya gösterilmez | MEVCUT SÖZLEŞME; deploy erişim yöntemi açık |

Kurallar:

- Genel `/api/v1/health` endpoint'i kanonik değildir; eklenmez.
- Liveness kontrolü yalnızca uygulama sürecinin canlılığını ölçer; DB erişimini liveness'a bağlayıp restart döngüsü yaratmamalıdır.
- Readiness kontrolü gerekli bağımlılıkları kontrol edebilir; dışarıya yalnızca genel hazır/değil bilgisi döndürür.
- Health endpoint'leri stok, audit veya kullanıcı durumunu değiştirmez.
- Yanıt içinde secret, connection string, SQL hata metni, filesystem path veya stack trace bulunmaz.

**AÇIK KARAR HEALTH-01:** `/health/ready` için “internal network” korumasının hangi ortam/ters proxy/container yapılandırmasıyla sağlanacağı deployment belgesinde açıklanmalıdır. Internal network garantisi yoksa yalnızca `ADMIN` auth seçeneği uygulanabilir; iki mekanizma da yokken readiness public bırakılmaz.

**AÇIK KARAR HEALTH-02:** Readiness başarısızlığının HTTP status'u ve minimal response şeması OpenAPI/test sözleşmesine Cilt 1.21'de yazılmalıdır. Öneri: hazırsa `200`, gerekli bağımlılık hazır değilse `503`; response hassas hata ayrıntısı içermez.

## 6. Güvenlik ve audit davranışı

- Login başarısızlıkları parola veya token içermeyen güvenlik olayı olarak kaydedilebilir; hassas veriler loglanmaz.
- Parola düz metin saklanmaz; güvenli parola hash algoritması ve parametreleri backend uygulama standardında açıkça seçilir.
- İstek gövdesindeki rol/permission alanları kullanıcının kendi yetkisini yükseltmek için kabul edilmez.
- Kullanıcı/rol değişikliği, kritik stok/maliyet hareketi, recall activation/resolution, lot unblock ve correction/reversal işlemleri audit gerektirir.
- Audit olayları token, parola, signing secret veya gereksiz hassas kişisel veri taşımaz.

**AÇIK KARAR SEC-01:** Audit yazımı başarısız olursa hangi kritik işlemler rollback olmalıdır? Öneri: stok, maliyet, recall ve permission/user-management gibi güvenlik açısından kritik mutasyonlarda audit kaydı iş transaction'ının atomik parçası olsun; audit yazılamazsa iş transaction'ı da rollback olsun. Bu politika proje sahibi onayıyla Cilt 1.21/1.22'de bağlayıcı hale getirilecektir.

**AÇIK KARAR SEC-02:** Login rate limit Cilt 1.9'da önerilmiştir; sayısal limit, pencere, IP/kullanıcı anahtarı ve `429` response sözleşmesi henüz kesin değil. Kesin değer uydurulmayacak; Cilt 1.21 error/security registry'de karar verilecek. İlk sürümde brute-force koruması olmadan login endpoint'i tamamlandı sayılmaz.

**AÇIK KARAR SEC-03:** Parola politikası (minimum uzunluk, breached/common password yaklaşımı, ilk girişte parola değiştirme gereksinimi ve parola değişince mevcut token davranışı) mevcut ciltlerde tek bir bağlayıcı sözleşmede kapanmamıştır. Cilt 1.22 veya Cilt 1.24'te onaylı kurallar ve testler eklenmelidir. “İlk girişte parola değişimi” varmış gibi uygulama yapılmamalıdır.

## 7. Minimum güvenlik test matrisi

| ID | Senaryo | Beklenen sonuç | İş etkisi |
|---|---|---|---|
| AUTH-T01 | Token olmadan korumalı endpoint | `401` + kanonik error envelope | Hiçbir değişiklik yok |
| AUTH-T02 | Bozuk/imzası geçersiz JWT | `401` | Hiçbir değişiklik yok |
| AUTH-T03 | Süresi dolmuş JWT | `401` | Hiçbir değişiklik yok |
| AUTH-T04 | Yanlış issuer/audience veya izin verilmeyen algoritma | `401` | Hiçbir değişiklik yok |
| AUTH-T05 | Aktif olmayan kullanıcıyla login | Login reddedilir | Token üretilmez |
| AUTH-T06 | Yetkisi olmayan rol mutasyon endpoint'ine erişir | `403` | Stok/maliyet/durum değişmez |
| AUTH-T07 | Request body'de başka `user_id` gönderilir | Aktör doğrulanmış token subject'i olur; ayrıcalık kazanılmaz | Yetkisiz işlem yok |
| AUTH-T08 | Logout çağrısı | `204`; istemci token'ı temizler | Server-side revoke iddia edilmez |
| AUTH-T09 | Logout sonrası aynı token sunucuya tekrar gönderilir | Token süresi dolmamış ve başka kontroller geçerliyse stateless MVP sözleşmesine göre kabul edilebilir | UI'da oturum kapanır; server revoke yok |
| AUTH-T10 | `VIEWER` stok/üretim/satış mutasyonu dener | `403` | Hiçbir değişiklik yok |
| AUTH-T11 | `SALES` AI tahmini başlatır | `403` | Tahmin/iş kaydı yok |
| AUTH-T12 | `OPERATOR` dispatch veya genel stok düzeltme dener | `403` | Hiçbir stok hareketi yok |
| AUTH-T13 | Public liveness isteği | `200` ve minimal yanıt | Gizli altyapı verisi yok |
| AUTH-T14 | Yetkisiz public kullanıcı readiness ister | Reddedilir veya ağ seviyesinde erişemez | Dependency ayrıntısı sızmaz |
| AUTH-T15 | Auth/permission hatası oluşur | Kanonik hata yanıtı; request ID mevcut | İş transaction'ı başlamaz veya rollback olur |
| AUTH-T16 | Loglar auth isteği sırasında incelenir | Parola, token, secret bulunmaz | Gizli bilgi sızıntısı yok |

Not: AUTH-T09, logout'un server-side revoke yapmadığı bağlayıcı kararı görünür kılmak için kasıtlı bir negatif beklentidir. Ürün sahibi ileride server-side revoke isterse yeni ADR ve API değişikliği gerekir.

## 8. Açık karar kayıtları

| ID | Konu | Önerilen sonraki adım | Kapatılacak cilt |
|---|---|---|---|
| AUTH-01 | Login hata mesajlarının eşitlenmesi ve rate-limit hata davranışı | Genel kimlik bilgisi hatası ve error code kararı | 1.21 |
| AUTH-02 | Disabled kullanıcı mevcut token kullanımı | Öneri: her korumalı istekte aktiflik kontrolü | 1.22 |
| AUTH-03 | Admin bootstrap tekrar çalıştırma ve secret/parola kaynağı | Güvenli, idempotent olmayan bootstrap davranışını tanımla | 1.24 |
| AUTH-04 | Android token güvenli saklama yöntemi | Platform korumalı storage kararı | Cilt 4 / 1.24 handoff |
| AUTH-05 | Web token/cookie/CSRF yaklaşımı | ÖNERİ A veya B'yi proje sahibi seçer | Cilt 7 / 1.24 handoff |
| HEALTH-01 | Readiness erişim korumasının deployment yöntemi | Internal network veya ADMIN auth'u doğrula | 1.24 |
| HEALTH-02 | Readiness HTTP status ve response schema | Öneri `200`/`503`, minimal payload | 1.21 |
| SEC-01 | Audit yazılamadığında mutasyon davranışı | Kritik transaction ile atomiklik kararı | 1.21–1.22 |
| SEC-02 | Login rate-limit sayısal politikası | Limit/pencere/key/429 tanımla | 1.21 |
| SEC-03 | Parola politikası, ilk girişte değiştirme ve token davranışı | Proje sahibi kararı ve test | 1.22 / 1.24 |
| PERM-01 | Endpoint–permission tam matrisi | Cilt 1.3/1.9 tüm endpoint'lerini tek tek eşleştir | 1.22 |
| PERM-02 | Recall release/unblock permission key ve rol | Exact endpoint, key, audit, retry sözleşmesi | 1.22 |

## 9. Kodlama LLM'si için bağlayıcı talimatlar

1. Access token 30 dakika, refresh token yok ve logout `204` istemci tarafı temizliği olarak uygulanır; server-side revoke varmış gibi gösterilmez.
2. Token yalnızca korumalı API isteklerinde `Authorization: Bearer` başlığında taşınır; URL'ye veya loglara yazılmaz.
3. JWT algoritması server-side allowlist/config ile sabitlenir; imza, süre ve issuer/audience doğrulamaları uygulanır.
4. Endpoint izinlerini Cilt 1.9 revizyon 1.11 ile birlikte kullan; onaylanmış rol kararlarını geriye dönük olarak değiştirme.
5. `401` kimlik doğrulama eksik/geçersizliği, `403` kimliği doğrulanmış fakat yetkisiz erişim için kullanılır; ayrıntılı hata kodları Cilt 1.21 registry'siyle eşitlenir.
6. `GET /health/live` ve `GET /health/ready` anonimdir. Liveness DB sorgusu yapmaz; readiness hazırsa 200, değilse 503 döndürür. Hassas dependency ayrıntısı response'a eklenmez.
7. Web token taşıma yöntemi, Android token storage yöntemi, rate limit sayıları ve parola politikası açık kararlar kapanmadan nihai tamamlandı olarak raporlanmaz.
8. Açık kararlar için sessiz varsayım yapma. Etkilenen dosyaları ve seçenekleri içeren blokaj raporu ver.
9. Bu cilt migration üretme veya veritabanı değiştirme izni vermez.

## 10. Cilt 1.20 tamamlanma durumu

- [x] JWT access token 30 dakika, refresh token yok ve logout davranışı tek yerde kaydedildi.
- [x] Kanonik rol kümesi ve daha önce onaylanmış kritik endpoint izinleri kaydedildi.
- [x] Liveness/readiness ayrımı ve hassas bilgi sızdırmama kuralı kaydedildi.
- [x] Minimum güvenlik testleri tanımlandı.
- [ ] Web token taşıma yöntemi proje sahibi tarafından seçildi.
- [ ] Android token güvenli saklama yöntemi uygulama cildiyle kesinleştirildi.
- [ ] Tüm endpoint permission matrisi API/DTO ile birebir çapraz kontrol edildi.
- [ ] Password policy, login rate limit, audit-failure davranışı ve readiness response sözleşmesi kapatıldı.
- [ ] AUTH-01–SEC-03 ve PERM-01–02 açık kararları kapatıldı veya açıkça kapsam dışı bırakıldı.

**Sonuç:** Cilt 1.20 güvenlik sözleşmesini toparlar ve bilinen kararları tekleştirir; açık kararlar nedeniyle tek başına kodlama devri veya migration onayı değildir.


### Cilt 1.34 normatif override — health/auth

- Health paths are `GET /health/live` and `GET /health/ready`, outside `/api/v1`.
- Both are anonymous. Liveness performs no database/dependency query and returns 200 when the process is alive. Readiness returns 200 only when required dependencies are ready; otherwise 503. Neither response leaks secrets or detailed connection errors.
- Auth contract: 15-minute access token, 7-day rotating refresh token, server-side refresh-session revocation on logout, refresh-token reuse revokes the token family.
- Web uses the approved single-origin reverse-proxy topology, HttpOnly cookie, SameSite=Lax, Secure under HTTPS, host-only Path=/ cookie, and synchronizer CSRF token for state-changing requests.
- This override changes documentation priority only; deployment and runtime tests remain required.
