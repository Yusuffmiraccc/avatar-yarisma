# Cilt 1.8 — Kimlik Doğrulama, Rol/İzin Matrisi ve Güvenlik Sözleşmesi


> **Normatif güncelleme — 22 Ekim 2026 (Cilt 1.32):** Bu belgedeki daha eski ve çelişen taslak ifadeler için `volume-01-32-approved-decisions-and-cross-check.md` ile Cilt 1.31'in onay kaydı önceliklidir. Bu not doküman sözleşmesini günceller; migration veya veritabanı değişikliği izni değildir.

**Durum:** Güvenlik sözleşmesi taslağı; rol/izin matrisi uygulama öncesi doğrulanmalıdır  
**Tarih:** 22 Ekim 2026  
**Teknoloji:** FastAPI, Pydantic, SQLAlchemy 2.x, MySQL 8.4 LTS  
**Bağlı belgeler:** Cilt 0, Cilt 1.2, Cilt 1.3, Cilt 1.4, Cilt 1.5, Cilt 1.6, Cilt 1.7, DEC-001, ADR-001

## 1. Amaç ve güvenlik ilkeleri

Bu cilt, AVATAR uygulamasında kimlik doğrulama, rol tabanlı erişim, kullanıcı/rol yönetimi, parola saklama, JWT access token davranışı, hassas operasyonların yetkilendirilmesi ve güvenlik denetimini tanımlar.

Temel ilkeler:

1. **Varsayılan ret:** Açıkça izin verilmemiş her korumalı işlem reddedilir.
2. **Backend yetki kaynağıdır:** Android ve React arayüzündeki butonları gizlemek yetkilendirme değildir. Her endpoint backend'de izin kontrolü yapar.
3. **En az ayrıcalık:** Kullanıcı yalnızca işi için gerekli izinlere sahip olur.
4. **Kimlik ve rol ayrıdır:** Token kullanıcıyı tanımlar; güncel izin kararı backend tarafından verilir.
5. **İşletme verisi korunur:** Hassas operasyonel kayıtlar sıradan kullanıcılar tarafından silinemez.
6. **Audit güvenliği destekler:** Kritik işlemler aktör, zaman, hedef ve sonuçla ilişkilendirilir; loglara parola/token yazılmaz.
7. **Yetkilendirme hatası iş etkisi doğurmaz:** `401`/`403` alan istek stok, maliyet veya iş durumu değiştirmez.
8. **AI rol yetkilerini aşamaz:** AI tahmini, kullanıcı adına satış/üretim/recall işlemi yapmaz.
9. **Onaylanmış kimlik doğrulama sözleşmesi (Cilt 1.31/1.32):** access token 15 dakika; refresh token 7 gün ve rotation; logout sunucu tarafında refresh session'ını iptal eder; refresh token reuse tespitinde token ailesi iptal edilir. Güvenli admin bootstrap CLI ile yapılır.

## 2. Kimlik doğrulama ve JWT

### 2.1 Access token

Önerilen ilk sürüm modeli:

- Kullanıcı email/login ve parola ile giriş yapar.
- Backend parolayı güvenli hash ile doğrular.
- Başarılı girişte imzalı JWT access token döndürür.
- Korunan endpoint'ler token imzasını, süre sonunu ve gerekli claim'leri doğrular.
- Token içindeki kullanıcı kimliği güvenilir claim'den okunur; request body içindeki `user_id` aktör kimliği olarak kabul edilmez.
- Token, parola veya imza anahtarı loglara yazılmaz.

JWT claim önerisi:
- `sub`: kullanıcı ID'si (string olarak serialize edilebilir).
- `iss`: uygulamanın yapılandırılmış issuer değeri.
- `aud`: bu API için tanımlanmış audience.
- `iat`: oluşturulma zamanı.
- `exp`: sona erme zamanı.
- `jti`: token ID'si; yalnızca revoke/denetim yaklaşımı bunu kullanıyorsa.
- `role` veya `roles`: rol bilgisinin token'da bulunup bulunmayacağı uygulama kararıdır. Yetki değişikliklerinin hemen etkili olması isteniyorsa her istekte güncel rol/izin DB'den veya güvenilir cache'ten kontrol edilmelidir.

**Bağlayıcı MVP kararı:** Access token ömrü 30 dakikadır (`expires_in=1800`); refresh token kullanılmaz. Süre dolunca yeniden giriş gerekir. Logout istemcide tokenı temizler; sunucu tarafında revoke/blacklist yoktur ve logout tokenı anında geçersiz kıldığı iddia edilmez. Token claim’lerinde hassas kullanıcı verisi bulunmaz.

### 2.2 Token imzalama ve algoritma

- İzin verilen imzalama algoritması sunucu yapılandırmasında sabitlenir; token header'ından rastgele algoritma seçilmez.
- Secret/private key güvenli ortam değişkeni veya uygun secret yönetimi üzerinden sağlanır.
- Geliştirme ve üretim anahtarları ayrılır.
- Anahtar rotasyonu planı ve anahtar değişiminde mevcut token'ların davranışı dokümante edilir.
- `alg=none` veya yapılandırmada izin verilmeyen algoritmalar reddedilir.
- Token imzası geçersiz, süresi dolmuş veya issuer/audience yanlışsa `401` döner.

### 2.3 Refresh ve logout

MVP için refresh/logout davranışı onaylanmıştır ve aşağıdaki seçenekler karar bekleyen seçenekler değildir:

- **MVP kararı:** Access-token-only; refresh token yoktur. Token süresi dolunca kullanıcı tekrar giriş yapar. Logout endpoint’i `204` döndürür ve istemci token’ı temizler. Server-side revoke/blacklist olmadığı için mevcut token süresi dolana kadar teknik olarak geçerli kalabilir; logout anında token iptal edildiği iddia edilmez.

### 2.4 Android token saklama

- Access token uygulamanın güvenli depolama yaklaşımına uygun biçimde saklanır; düz metin loglara veya dışa açık dosyalara yazılmaz.
- DataStore, sır saklama garantisi olan şifreli depolama yerine otomatik olarak kabul edilmez. Token için platformun güvenli saklama imkânı değerlendirilmelidir.
- Logout sonrasında yerel token ve kullanıcıya ait geçici hassas durum temizlenir.
- Token URL query parametresine eklenmez; korumalı isteklerde `Authorization: Bearer <token>` başlığı kullanılır.

## 3. Kullanıcı yaşam döngüsü

Önerilen kullanıcı durumları:

`PENDING` → `ACTIVE` → `DISABLED`

- `PENDING`: kullanıcı hesabı açılmış ancak yetkili onayı/aktivasyonu bekliyor.
- `ACTIVE`: giriş yapabilir.
- `DISABLED`: giriş yapamaz; geçmiş iş kayıtları korunur.

Bu durumlar Cilt 1.3 veri modelinde bulunmuyorsa tablo/enum değişikliği olarak ayrıca onaylanmalıdır. İlk admin hesabının nasıl oluşturulacağı da ayrı bootstrap kararıdır.

Kurallar:
- `DISABLED` kullanıcı için yeni access token verilmez.
- Kullanıcı devre dışı bırakıldığında mevcut token'ların hemen geçersiz olup olmayacağı, token doğrulamasında güncel kullanıcı durumunun kontrol edilmesine veya token revoke listesine bağlıdır.
- Kullanıcı hard-delete edilmez; tarihsel audit ve operasyon kayıtları korunur.
- Email/login normalizasyonu ve unique davranışı tutarlı biçimde tanımlanmalıdır.
- Parola değişikliği, rol değişikliği ve hesabı devre dışı bırakma audit edilmelidir.

## 4. Roller ve izin matrisi

### 4.1 Roller

DEC-001'de belirlenen ilk rol kümesi:

- `ADMIN`
- `OPERATOR`
- `SALES`
- `TRACEABILITY_MANAGER`
- `VIEWER`

Aşağıdaki matris, Cilt 1.3'teki endpoint kapsamıyla eşleştirilmesi gereken **önerilen başlangıç matrisi**dir. Bu tablo, henüz onaylanmamış endpoint permission'larının otomatik olarak kesinleştiği anlamına gelmez.

### 4.2 İzin sözlüğü

| İzin anahtarı | Anlam |
|---|---|
| `auth:read_self` | Kendi kullanıcı/oturum bilgilerini görüntüleme |
| `users:read` | Kullanıcıları görüntüleme |
| `users:manage` | Kullanıcı oluşturma, devre dışı bırakma, rol atama |
| `catalog:read` | Ürün/birim/tedarikçi/hizmet kataloglarını görüntüleme |
| `catalog:manage` | Katalog oluşturma ve düzenleme/pasifleştirme |
| `inventory:read` | Lot, bakiye ve hareketleri görüntüleme |
| `inventory:receive` | Lot kabulü ve stok girişi kaydı |
| `inventory:adjust` | Yetkili düzeltme/ters kayıt |
| `production:read` | Üretim emirlerini görüntüleme |
| `production:manage` | Üretim emri taslak/planlama işlemleri |
| `production:complete` | Üretim tamamlamak ve stok/maliyet etkisi oluşturmak |
| `butchering:read` | Parçalama kayıtlarını görüntüleme |
| `butchering:manage` | Parçalama emri oluşturma/düzenleme |
| `butchering:complete` | Parçalamayı tamamlamak ve stok/maliyet etkisi oluşturmak |
| `sales:read` | Satışları görüntüleme |
| `sales:create` | Satış kaydı oluşturma |
| `sales:correct` | Satış düzeltme/ters kayıt |
| `shipments:read` | Sevkiyatları görüntüleme |
| `shipments:manage` | Sevkiyat hazırlama/oluşturma |
| `shipments:dispatch` | Sevkiyatı gönderildi olarak işaretleme |
| `traceability:read` | İleri/geri lot izleme |
| `recalls:read` | Recall kayıtları ve kapsamını görüntüleme |
| `recalls:manage` | Recall taslağı oluşturma ve aksiyon yönetimi |
| `recalls:activate` | Recall'ı aktive etme ve lotları bloke etme |
| `recalls:resolve` | Recall çözümleme/kapama |
| `ai:predict` | AI tahmini isteme |
| `ai:metrics:read` | Model metriklerini ve tahmin-gerçek karşılaştırmasını görüntüleme |
| `audit:read` | Audit geçmişini görüntüleme |
| `reports:read` | Raporları görüntüleme |

### 4.3 Önerilen rol/izin matrisi

`✓` = önerilen izin, `—` = varsayılan olarak yok. İzinler Cilt 1.3 endpoint'lerine bağlanmalı ve testlerle doğrulanmalıdır.

| İzin alanı | ADMIN | OPERATOR | SALES | TRACEABILITY_MANAGER | VIEWER |
|---|:---:|:---:|:---:|:---:|:---:|
| Kendi oturum bilgisi | ✓ | ✓ | ✓ | ✓ | ✓ |
| Kullanıcı/rol yönetimi | ✓ | — | — | — | — |
| Katalog okuma | ✓ | ✓ | ✓ | ✓ | ✓ |
| Katalog yönetimi | ✓ | — | — | — | — |
| Stok okuma | ✓ | ✓ | ✓ | ✓ | ✓ |
| Lot kabulü | ✓ | ✓ | — | — | — |
| Stok düzeltme/ters kayıt | ✓ | — | — | — | — |
| Üretim okuma | ✓ | ✓ | — | ✓ | ✓ |
| Üretim yönetimi | ✓ | ✓ | — | — | — |
| Üretim tamamlama | ✓ | ✓ | — | — | — |
| Parçalama okuma | ✓ | ✓ | — | ✓ | ✓ |
| Parçalama yönetimi/tamamlama | ✓ | ✓ | — | — | — |
| Satış okuma | ✓ | — | ✓ | ✓ | ✓ |
| Satış oluşturma | ✓ | — | ✓ | — | — |
| Satış düzeltme | ✓ | — | — | — | — |
| Sevkiyat okuma | ✓ | ✓ | ✓ | ✓ | ✓ |
| Sevkiyat hazırlama | ✓ | — | ✓ | — | — |
| Sevkiyat dispatch | ✓ | — | ✓ | — | — |
| Traceability | ✓ | ✓ | ✓ | ✓ | ✓ |
| Recall okuma | ✓ | ✓ | ✓ | ✓ | ✓ |
| Recall yönetimi/aksiyonları | ✓ | — | — | ✓ | — |
| Recall aktivasyonu | ✓ | — | — | ✓ | — |
| Recall çözümleme | ✓ | — | — | ✓ | — |
| AI tahminleri | ✓ | ✓ | — | — | ✓ |
| AI metrikleri | ✓ | ✓ | — | ✓ | ✓ |
| Audit okuma | ✓ | — | — | ✓ | — |
| Rapor okuma | ✓ | ✓ | ✓ | ✓ | ✓ |

**İnceleme notları:**
- `VIEWER` yalnızca okuma izni alır; iş kaydı değiştiremez.
- `TRACEABILITY_MANAGER` recall ve izlenebilirlik işlerini yürütebilir, ancak satış veya stok miktarını doğrudan değiştiremez.
- `OPERATOR` üretim/parçalama/stok kabulü gibi operasyonları yürütür; satış düzeltmesi veya kullanıcı yönetimi yapmaz.
- `SALES` satış/sevkiyat akışını yürütür; stok düzeltme ve recall aktivasyonu yapamaz.
- `ADMIN` tüm izinleri kullanabilse de kritik işlemler audit edilir; admin yetkisi iş kurallarını atlama yetkisi değildir.
- Satır bazlı/işletme bazlı erişim sınırları varsa rol tek başına yeterli değildir; kaynak kapsamı ayrıca kontrol edilir.

## 5. Endpoint yetkilendirme kuralı

Her Cilt 1.3 endpoint'i şu metadata ile eşleştirilmelidir:

- HTTP method + path
- Authentication required? (evet/hayır)
- Gerekli permission key
- Kaynak kapsamı kontrolü (kendi kaydı, işletme, tüm sistem vb.)
- Hassas işlem mi?
- Audit gerekli mi?
- Beklenen `401`/`403` davranışı
- Test senaryosu

Örnek (temsili):

| Endpoint türü | Auth | Permission | Ek kontrol |
|---|---|---|---|
| Login | Hayır | — | Rate limit ve genel hata mesajı |
| Current user | Evet | `auth:read_self` | Token'daki kullanıcı mevcut/aktif olmalı |
| Catalog list | Evet | `catalog:read` | Pasif kayıtların gösterim politikası |
| Lot receipt | Evet | `inventory:receive` | Pozitif miktar, unique code, transaction |
| Sale create | Evet | `sales:create` | Idempotency, stok, lot blokajı |
| Recall activate | Evet | `recalls:activate` | Yetki, genealogy, atomik blokaj, audit |
| Audit list | Evet | `audit:read` | Sınırlı alanlar ve pagination |

Bu örnekler kesin endpoint listesi değildir. Cilt 1.3'teki tüm endpoint'ler için gerçek eşleme tablosu oluşturulmalıdır; tanımsız endpoint varsayılmamalıdır.

## 6. Parola ve hesap güvenliği

- Parola düz metin olarak saklanmaz veya loglanmaz.
- Modern parola hash algoritması ve güvenli parametreleri kullanılır (ör. Argon2id veya uygulama bağımlılıklarıyla uyumlu güvenli seçenek).
- Parola doğrulama hatası, kullanıcı hesabının var olup olmadığına dair bilgi sızdırmayacak genel bir mesaj döndürür.
- Login endpoint'i için rate limiting/brute-force koruması uygulanır veya dağıtım katmanında sağlandığı belgelenir.
- Başarısız login denemeleri, güvenlik gereksinimine uygun ölçüde kaydedilir; parola/token loglanmaz.
- İlk parola, admin bootstrap veya parola sıfırlama akışı için güvenli ve belgelenmiş süreç gerekir.
- Parola değişikliği sonrası mevcut token'ların davranışı belirlenmelidir.
- Admin bootstrap parolası kaynak kodda veya demo seed içinde gerçek sır olarak tutulmaz.

## 7. Audit ve güvenlik olayları

Aşağıdaki olaylar audit veya güvenlik olay kaydına uygun şekilde alınmalıdır:

- Login başarı/başarısızlığı (başarısız denemelerde kişisel veri minimizasyonu).
- Kullanıcı aktif/pasif duruma geçişi.
- Rol/izin değişikliği.
- Parola değişikliği/sıfırlama talebi (parolanın kendisi asla kaydedilmez).
- Stok kabulü, düzeltme/ters kayıt.
- Üretim/parçalama tamamlama.
- Satış oluşturma/düzeltme.
- Sevkiyat dispatch.
- Recall oluşturma, aktivasyon, aksiyon değişikliği ve çözümleme.
- Kritik katalog değişiklikleri.
- AI model sürümü ve tahmin kaydı, gerekiyorsa.

Audit kaydı:
- Aktör, zaman, eylem, hedef kayıt tipi/ID ve sonuç gibi alanları içermelidir.
- Access token, refresh token, parola, secret veya tam ödeme/kişisel bilgi gibi gereksiz hassas verileri içermez.
- Kritik iş transaction'ıyla aynı transaction'da yazılır; audit yazılamıyorsa kritik işlem commit edilmemelidir (bu davranış ürün gereksinimiyle doğrulanmalıdır).

## 8. Güvenlik hata sözleşmesi

Cilt 1.4 ortak hata zarfı kullanılır: `error.code`, `error.message`, isteğe bağlı `error.details`, `request_id`.

Önerilen HTTP davranışı:

| Durum | HTTP | Örnek hata kodu | Not |
|---|---:|---|---|
| Token yok/geçersiz/süresi dolmuş | 401 | `UNAUTHENTICATED` | Kullanıcıya token ayrıntısı verilmez |
| Kullanıcı aktif değil | 401 veya 403 | `ACCOUNT_DISABLED` | API genelinde tek davranış seçilmelidir |
| Token geçerli, izin yok | 403 | `FORBIDDEN` | Gizli kaynaklarda 404 politikası ayrıca kararlaştırılabilir |
| Login bilgisi yanlış | 401 | `INVALID_CREDENTIALS` | Kullanıcı var/yok bilgisi sızdırılmaz |
| Login rate limit aşıldı | 429 | `RATE_LIMITED` | Retry davranışı tanımlanır |
| Idempotency çakışması | 409 | `IDEMPOTENCY_KEY_REUSED` | Cilt 1.4 ile aynı olmalı |
| İş durumu geçişi geçersiz | 409 | `INVALID_STATE_TRANSITION` | Güvenlik kontrolü geçilmiş olsa da iş kuralı ayrı kontrol edilir |

Kod isimleri Cilt 1.3/1.4'teki kesin error code listesiyle eşleştirilmelidir; bu tablo yeni bir hata sözleşmesini kendiliğinden onaylamaz.

## 9. Admin bootstrap ve rol yönetimi

İlk admin oluşturma yöntemi açıkça belirlenmelidir. Önerilen güvenli seçeneklerden biri:

- Yerel kurulum komutu: `python -m scripts.create_admin`, interaktif veya environment üzerinden sağlanan ilk kimlik bilgileriyle.
- Komut yalnızca açıkça belirtilen DB hedefinde çalışır.
- Parola komut satırı argümanı olarak shell history'ye düşecek biçimde kullanılmaz.
- İlk girişte parola değiştirme zorunluluğu isteniyorsa kullanıcı durum alanı ve API davranışı sözleşmeye eklenir.
- Seed verisi sabit ve bilinen bir admin parolası oluşturmaz.
- Komut ikinci kez çalıştığında var olan admin'i sessizce sıfırlamaz; açık bir reset prosedürü gerekir.

Admin rolü atanması audit edilir. Bir kullanıcının kendisine yetki yükseltmesi API seviyesinde engellenir; bu yetki yalnızca açıkça izinli admin akışıyla verilir.

## 10. Android ve web istemci davranışları

### Android (Kotlin)

- Access token yalnızca korumalı API çağrılarında Authorization header'ında gönderilir.
- `401` durumunda kullanıcı oturumu sonlandırılır veya onaylı refresh akışı çalıştırılır.
- `403` kullanıcıya yetki yetersizliği olarak gösterilir; otomatik tekrar denenmez.
- Token ve hassas kullanıcı bilgileri debug loglarında yazdırılmaz.
- Uygulama ekranları izinlere göre davranabilir ancak backend denetimini atlayamaz.

### Web (React + TypeScript)

- Token saklama yöntemi, XSS ve CSRF riskleri değerlendirilerek belirlenir. Browser `localStorage` otomatik olarak en güvenli seçenek sayılmaz.
- Eğer HttpOnly cookie yaklaşımı seçilirse CSRF koruması ve cookie ayarları açıkça yapılandırılır.
- Eğer bearer token yaklaşımı seçilirse token saklama, XSS risk azaltımı ve logout temizliği belgelenir.
- UI'da izin bazlı görünürlük yalnızca UX içindir.
- Sunucu tarafı veya API'deki gerçek izin kontrolü her zaman zorunludur.

## 11. Güvenlik test planı

### Unit testler
- Token signature/expiry/issuer/audience doğrulaması.
- İzin çözümleme ve varsayılan ret.
- Disabled user davranışı.
- Parola doğrulama ve hash kontrolü.
- Kullanıcının kendi rolünü yükseltememesi.
- Hata zarfı ve request ID.

### Integration testler
- Her rol için korunan endpoint çağrıları.
- Token olmadan/bozuk token ile çağrı.
- Yetkisiz çağrıda DB iş etkisinin olmaması.
- Rol değişikliğinin token'a etkisi.
- Admin bootstrap tekrar çalıştırma davranışı.
- Recall aktivasyonunu yalnızca yetkili rolün yapabilmesi.
- Sales rolünün stok düzeltme yapamaması.
- Viewer rolünün hiçbir yazma komutu yapamaması.
- Audit olaylarının kritik işlemlerle tutarlılığı.

### Contract testler
- Cilt 1.3 endpoint method/path ve auth gereksinimleri.
- OpenAPI security scheme tanımı.
- `401`, `403`, `429` hata zarfı.
- Rol/izin isimlerinin tutarlılığı.
- Kotlin ve TypeScript istemci DTO'larının ortak sözleşmeyle uyumu.

## 12. Açık güvenlik kararları

| ID | Karar | Öneri | Durum |
|---|---|---|---|
| SEC-01 | Access token ömrü | Kısa ömür; kesin süre ürün kararı | AÇIK |
| SEC-02 | Refresh token | İlk prototipte access-token-only seçeneği daha basit | AÇIK |
| SEC-03 | Logout invalidation | Token-only veya server-side revoke davranışı tanımlanmalı | AÇIK |
| SEC-04 | Rol değişikliği etkisi | İsteklerde güncel izin kontrolü veya sürüm/revoke yaklaşımı | AÇIK |
| SEC-05 | İlk admin oluşturma | Güvenli CLI bootstrap; sabit seed parolası yok | AÇIK |
| SEC-06 | İlk girişte parola değiştirme | Gereksinim ve user state alanı netleştirilmeli | AÇIK |
| SEC-07 | Web token saklama | XSS/CSRF riskleri değerlendirilerek karar verilmeli | AÇIK |
| SEC-08 | Rate limiting | Uygulama veya reverse proxy katmanında sağlandığı belgelenmeli | AÇIK |
| SEC-09 | Audit yazma hatası | Kritik işlem audit yazılamazsa commit edilsin mi? Öneri: hayır | AÇIK |
| SEC-10 | Permission matrix | Bu ciltteki önerilen matris Cilt 1.3 endpoint'leriyle tek tek eşleştirilmeli | AÇIK |

## 13. Kabul ölçütleri

Bu cilt uygulamaya hazır sayılmadan önce:

- Cilt 1.3'teki her endpoint auth ve permission ile eşleştirilmiş olmalı.
- Rol/izin matrisi yetkili ekip tarafından onaylanmalı.
- JWT imza, süre, issuer ve audience davranışı tanımlanmalı.
- Refresh/logout ve rol değişikliği davranışı kesinleşmeli.
- İlk admin bootstrap ve parola politikası belirlenmeli.
- Web ve Android token saklama yaklaşımı belirlenmeli.
- `401`, `403`, `429` davranışları ortak hata sözleşmesiyle uyumlu olmalı.
- Kritik operasyonlar audit edilmeli ve secret'lar loglanmamalı.
- Yetkisiz isteklerin hiçbir stok/maliyet/recall etkisi olmadığı testle kanıtlanmalı.

## 14. Sonraki zorunlu kapı: migration öncesi çapraz kontrol

**Kullanıcının açık talebi:** Gerçek Alembic migration dosyaları yazılmadan veya veritabanı oluşturulup/değiştirilmeden önce bu kontrol adımını kullanıcıya yeniden hatırlat ve açık onay al.

Kontrol kapsamı:
1. Cilt 1.2 ERD'sindeki tüm tablo, kolon, veri tipi, nullable alan, FK, unique ve index kararlarını Cilt 1.3 API DTO/endpoint'leriyle birebir karşılaştır.
2. Cilt 1.5 WF-01–WF-10 kararlarını tek tek incele; her birini `APPROVED`, `REJECTED` veya `OUT_OF_SCOPE` durumuna getir ve gerekçesini karar kaydına yaz.
3. Özellikle fire alanlarının nullability'si, üretim girdisinin stoktan düşme zamanı, satış/sevkiyat stok düşümü sahipliği, recall aktivasyon modeli, recall sonrası lot blokajı, ağırlık toleransı ve tamamlanmış işlemlerin düzeltme kurallarını kontrol et.
4. Cilt 1.2–1.8 belgelerinde kalan enum, endpoint, DTO, error code veya tablo adı çelişkilerini raporla.
5. Düzeltilecek belgeleri ve planlanan migration listesini kullanıcıya sun.
6. **Ancak kullanıcı bu çapraz kontrol raporunu açıkça onayladıktan sonra** gerçek Alembic revision dosyaları yazımına veya veritabanı oluşturma/değiştirme adımlarına geç.

Bu adım atlanmamalıdır. Cilt 1.7 migration planı, gerçek migration dosyalarının veya veritabanının oluşturulduğu anlamına gelmez.

## 15. Sonraki adım

Cilt 1.8 onaylandıktan sonra, kullanıcıyla açık güvenlik kararlarını kapatmak ve Cilt 1.3 endpoint'leriyle izin matrisini eşleştirmek gerekir. Ardından Cilt 1.2–1.8 çapraz kontrolü için ayrı bir inceleme raporu hazırlanır. Gerçek migration kodlamasına geçiş için kullanıcıdan ayrıca onay alınır.

## Revizyon 1.11 — Bağlayıcı güvenlik varsayılanları

Bu bölüm, önceki “öneri/karar bekliyor” ifadelerini aşağıdaki onaylanmış varsayılanlarla günceller.

- Access token ömrü **30 dakika** (`expires_in = 1800`). İlk MVP'de refresh token yoktur; süre dolunca yeniden giriş yapılır. Logout istemci token'ını temizler. Server-side revoke yoksa logout'un token'ı anında geçersiz kıldığı iddia edilmez.
- Android token'ı platforma uygun güvenli yerel saklamada tutar. Web token taşıma/cookie ve CSRF politikası web uygulamasıyla API CORS/CSRF ayarları birlikte tanımlanmadan implementasyona hazır sayılmaz.
- Genel stok düzeltme yalnızca `ADMIN` yetkisindedir. `OPERATOR` normal operasyon akışlarını yürütür, genel adjustment endpoint'ini çağıramaz.
- Sevkiyat oluşturma ve dispatch `ADMIN`/`SALES` içindir. `OPERATOR` ve `TRACEABILITY_MANAGER` sevkiyatı yalnızca okur.
- AI tahmin başlatma `ADMIN`/`OPERATOR`; tahmin sonucu okuma `ADMIN`/`OPERATOR`/`TRACEABILITY_MANAGER`/`VIEWER` içindir. `SALES` ilk sürümde bu izinlerin dışındadır.
- Recall resolve ile lot unblock ayrı izinli işlemlerdir. Unblock ve düzeltme/ters kayıt işlemleri audit edilir.
- `/api/v1/health/live` minimal liveness bilgisidir. Ayrıntılı DB/dependency health internal veya yetkili erişimle sınırlandırılır ve secret/connection detail döndürmez.
- Error envelope `request_id` kullanır; endpoint permission ve error registry testleri API contract testleriyle eşleşir.


## Cilt 1.34 — Güncel bağlayıcı auth/health sözleşmesi

Aşağıdaki kurallar, bu dosyadaki önceki access-token-only/30 dakika ifadelerinin yerine geçer. Önceki ifadeler tarihsel taslak olarak değerlendirilmelidir.

- Access token: 15 dakika (`expires_in=900`).
- Refresh token: 7 gün; rotation zorunlu.
- Refresh token'ın güvenli hash/session kaydı sunucuda tutulur; logout refresh session'ını revoke eder; eski refresh token reuse edilirse token ailesi revoke edilir.
- Disabled user ve parola reset/rol değişiminde Cilt 1.31 SEC-05 kuralları uygulanır.
- Web tek origin/reverse proxy; HttpOnly cookie; HTTPS altında Secure; SameSite=Lax; host-only `Path=/`; state-changing request için session'a bağlı synchronizer CSRF token.
- Android token plaintext DataStore'a yazılmaz; Android Keystore ile korunan şifreli depolama gerekir.
- `GET /health/live`: anonim, DB sorgusu yapmaz, süreç canlıysa 200.
- `GET /health/ready`: anonim; bağımlılıklar hazırsa 200, değilse 503. Secret/connection details response'a konmaz. Her iki health yolu da `/api/v1` dışında kalır.
