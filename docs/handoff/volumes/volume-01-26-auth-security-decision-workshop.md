# Cilt 1.26 — Kimlik Doğrulama ve Güvenlik Karar Atölyesi

**Tarih:** 22 Ekim 2026  
**Durum:** Karar çalışması; hiçbir öneri kullanıcı onayı olmadan kesinleştirilmiş değildir.  
**İlgili sicil:** Cilt 1.25, REG-125-08–REG-125-15  
**Amaç:** Web, Android ve backend kimlik doğrulama davranışlarını aynı sözleşmede toplamak; güvenlik açısından önemli seçenekleri proje sahibinin kararına sunmak.

## 1. Kapsam ve sınırlar

Bu cilt yalnızca karar vermeye yardımcı olur. Tek başına aşağıdakileri yapmaz:

- ERD veya veritabanı şemasını değiştirmez.
- Alembic migration oluşturulmasına izin vermez.
- Kimlik doğrulama davranışlarını `CLOSED` durumuna taşımaz.
- Kaynak belgelerde belirtilmeyen bir davranışı sessizce gerçek kabul etmez.

Teknoloji bağlamı: FastAPI backend, JWT tabanlı kimlik doğrulama, React/TypeScript web yönetim paneli, Kotlin Android uygulaması. Merkezi MySQL'e yalnızca backend erişir.

## 2. Karar oturumu özeti

| Karar ID | Konu | Önerilen başlangıç yaklaşımı | Proje sahibi kararı |
|---|---|---|---|
| REG-125-08 | Web token taşıma ve CSRF | HttpOnly, Secure, uygun SameSite cookie; CSRF savunması, deployment topolojisiyle birlikte netleştirilmeli | OPEN |
| REG-125-09 | Android token saklama | Platformun güvenli saklama mekanizması; düz metin DataStore'da token saklama varsayılmamalı | OPEN |
| REG-125-10 | Access token, refresh ve logout | Kısa ömürlü access token; refresh gerekiyorsa ayrı yaşam döngüsü ve iptal politikası tanımlanmalı | OPEN |
| REG-125-11 | Devre dışı kullanıcı token'ı | Her yetkili istekte güncel kullanıcı durumu kontrol edilmeli veya eşdeğer iptal mekanizması açıkça seçilmeli | OPEN |
| REG-125-12 | Parola ve ilk giriş | İlk giriş parola değiştirme zorunluluğu açık bir kullanıcı durumu/yanıt sözleşmesine bağlanmalı | OPEN |
| REG-125-13 | Login rate limit | IP ve hesap odaklı sınırlama, gizli bilgi sızdırmayan hata yanıtı; sayısal eşikler kararlaştırılmalı | OPEN |
| REG-125-14 | Endpoint permission matrisi | Tek kanonik endpoint-permission tablosu; her kritik endpoint için izin/ret testi | OPEN |
| REG-125-15 | Liveness/readiness | Ayrı liveness ve readiness semantiği; DB erişimi readiness için değerlendirilir | OPEN |

Yukarıdaki “önerilen başlangıç yaklaşımı” ifadeleri bağlayıcı karar değildir.

## 3. REG-125-08 — Web istemcisinde token taşıma ve CSRF

### Kaynakta sabit olanlar
- Web paneli React + TypeScript ile geliştirilecektir.
- Backend FastAPI'dir.
- Kimlik doğrulamada JWT ve rol tabanlı yetkilendirme kararı daha önce onaylanmıştır.
- Token'ın web'de nasıl taşınacağı ve CSRF davranışı açık karardır.

### Seçenekler

**A — HttpOnly cookie**
- Token JavaScript tarafından doğrudan okunamaz; XSS ile token'ın okunup dışarı çıkarılması riski azaltılır.
- Cookie otomatik gönderildiği için CSRF savunması, `SameSite`, `Secure`, `HttpOnly`, origin/CORS politikası ve deployment topolojisi birlikte tasarlanmalıdır.
- Web uygulaması ile API farklı origin/site üzerinde çalışacaksa cookie ayarları ve CSRF akışı ayrıca doğrulanmalıdır.

**B — Bearer token'ı JavaScript erişimli depoda tutmak**
- API çağrılarında `Authorization: Bearer` kullanımı kolaydır.
- Token JavaScript tarafından okunabiliyorsa XSS, token'ın çalınması bakımından daha yüksek risk doğurabilir.
- `localStorage` içinde uzun ömürlü token tutmak önerilmez; tercih edilirse tehdit modeli ve XSS azaltımları açıkça belgelenmelidir.

### Öneri
Web için A seçeneğini başlangıç önerisi olarak değerlendir. Ancak API ve web'in gerçek deployment origin'leri, HTTPS ve domain düzeni bilinmeden cookie/CSRF yapılandırmasını kesinleştirme.

### Karar sorusu
Web paneli token yaklaşımı olarak hangisini onaylıyorsun?

- **A:** HttpOnly cookie + CSRF koruması (önerilen başlangıç)
- **B:** Authorization Bearer token; tarayıcı saklama biçimi ayrıca belirlenecek
- **C:** Önce deployment/origin yapısını tanımlayıp sonra seçelim

**Durum:** OPEN

## 4. REG-125-09 — Android token saklama

### Kaynakta sabit olanlar
Android tarafı Kotlin + Jetpack Compose, Room/SQLite, Retrofit/OkHttp ve DataStore kullanır. DataStore uygulama ayarları için kararlaştırılmıştır; bu, hassas token'ların düz metin olarak saklanmasının onaylandığı anlamına gelmez.

### Seçenekler
- **A — Android Keystore destekli şifreli saklama:** Token şifreli bir depoda tutulur; şifreleme anahtarı Android Keystore ile korunur. Uygulama yaşam döngüsü, yedekleme ve logout temizliği tanımlanır.
- **B — Harici güvenli depolama kütüphanesi:** Kütüphanenin bakım durumu, Android sürüm desteği, şifreleme ve yedekleme davranışı doğrulanır.
- **C — Kalıcı token saklamamak:** Daha basit güvenlik modeli; uygulama yeniden açıldığında yeniden login gerekebilir.

### Öneri
A yaklaşımını değerlendirmek; fakat kullanılacak somut uygulama ve anahtar yaşam döngüsünü ayrıca doğrulamak.

**Karar sorusu:** A, B veya C?  
**Durum:** OPEN

## 5. REG-125-10 — Access token, refresh ve logout

Bu karar tek bir “JWT süresi” değerinden ibaret değildir. Şu maddeler birlikte seçilmelidir:

1. Access token ömrü.
2. Refresh token kullanılıp kullanılmayacağı.
3. Refresh token'ın nerede ve nasıl saklanacağı.
4. Refresh token rotasyonu ve tekrar kullanım tespiti.
5. Logout'un yalnızca istemci token'ını silmesi mi, yoksa sunucu tarafında refresh oturumunu iptal etmesi mi gerektiği.
6. Parola değişimi, kullanıcı devre dışı bırakma ve rol değişiminde mevcut oturumların davranışı.

### Seçenekler
- **A — MVP için kısa ömürlü access token, refresh token yok:** Daha basit; kullanıcı daha sık yeniden login olur.
- **B — Access + refresh token:** Kullanılabilirlik artar; refresh saklama, rotasyon, iptal ve tekrar kullanım senaryoları tasarlanmalıdır.

### Öneri
Geliştirme basitliği için A, kullanıcı deneyimi önceliği varsa B değerlendirilebilir. Süre değerleri kullanıcı onayı olmadan sabitlenmez.

**Karar sorusu:** A mı B mi?  
**Durum:** OPEN

## 6. REG-125-11 — Kullanıcı devre dışı bırakıldığında mevcut token

### Seçenekler
- **A — Her yetkili istekte kullanıcı durumu kontrolü:** Kullanıcı pasifse token imzası geçerli olsa bile istek reddedilir. Basit ve anlaşılırdır; her istekte kullanıcı kaydı veya güvenilir bir cache kontrolü gerektirir.
- **B — Kısa token ömrü + iptal sürümü/oturum kaydı:** Uygulama ayrıntısı artar; iptal gecikmesi ve cache davranışı açıkça tanımlanmalıdır.

### Öneri
MVP'de A: yetkili her istekte kullanıcı aktiflik durumunu doğrula. Bu kontrolün hata vermesi durumunda güvenli biçimde reddet; pasiflik kontrolü başarısızken işlemi yetkilendirme.

**Durum:** OPEN — kullanıcı onayı gerekir.

## 7. REG-125-12 — Parola politikası ve ilk giriş

Aşağıdaki davranışlar belgelenmelidir:

- Minimum parola uzunluğu ve kabul edilen karakterler.
- Parolanın güvenli hash algoritmasıyla saklanması; düz metin/parolayı geri döndürülebilir biçimde saklama yasağı.
- İlk girişte parola değiştirme zorunluluğunun nasıl ifade edildiği.
- Parola değişimi başarılı olduğunda mevcut token'ların korunması veya iptali.
- Parola sıfırlama akışının MVP kapsamına dahil olup olmadığı.

### Karar sorusu
İlk girişte parola değiştirme yarışma senaryosu için zorunlu olduğundan, bunu kullanıcı durumuyla ve auth yanıtlarıyla uygulamayı onaylıyor musun? Parola sıfırlama akışı MVP'de gerekli mi, yoksa kapsam dışı mı?

**Durum:** OPEN

## 8. REG-125-13 — Login rate limit / brute-force koruması

### Gereken karar alanları
- Limit anahtarı: IP, hesap adı/e-posta veya bunların birleşimi.
- Zaman penceresi ve eşik.
- Geçici bekletme/kilit davranışı.
- Birden fazla hatalı denemede hesap varlığını ifşa etmeyen yanıt.
- Proxy/load balancer arkasında güvenilir IP bilgisinin nasıl elde edileceği.
- Limitin deployment ortamında tek instance mı yoksa çok instance mı uygulanacağı.

### Öneri
Hesap ve IP tabanlı koruma kullan; kullanıcı var/yok bilgisini login hata mesajıyla açığa çıkarma. Sayısal eşikleri deployment ve test ihtiyacına göre ayrıca kararlaştır.

**Durum:** OPEN — eşik değerleri seçilmedi.

## 9. REG-125-14 — Endpoint başına permission matrisi

Cilt 1.8 ve 1.9'daki rol tanımları tek başına endpoint sözleşmesinin yerine geçmez. Her endpoint için aşağıdaki kayıtlar tek tabloda olmalıdır:

| Alan | Açıklama |
|---|---|
| `method` + `path` | Kanonik API endpoint'i |
| `permission_key` | Tekil, sabit permission anahtarı |
| `allowed_roles` | İzin verilen roller |
| `auth_required` | Anonim erişim olup olmadığı |
| `object_scope` | Kaynak/tenant/lot kapsamı kontrolü gerekiyorsa kural |
| `deny_status` | Kimlik doğrulama/yetki reddi HTTP davranışı |
| `audit_required` | İşlemin audit kaydı gerektirip gerektirmediği |
| `tests` | En az bir izinli ve bir reddedilen senaryo |

### Güvenlik kuralı
İstemcinin gönderdiği rol, tenant veya permission bilgisi tek başına yetki kanıtı sayılmaz. Yetki backend'de doğrulanmalıdır.

**Durum:** OPEN — endpoint listesiyle tam çapraz kontrol gerekir.

## 10. REG-125-15 — Liveness ve readiness

### Önerilen semantik
- **Liveness:** Uygulama sürecinin çalıştığını gösterir; DB sorgusunu zorunlu kılmamalıdır.
- **Readiness:** Uygulamanın istek almaya hazır olup olmadığını gösterir; gerekli bağımlılıklara, özellikle MySQL bağlantısına erişimi kontrol eder.
- Hassas yapılandırma, bağlantı dizesi, parola veya stack trace response'a eklenmez.
- Anonim erişim ve kesin endpoint yolları API sözleşmesinde kararlaştırılmalıdır.

**Durum:** OPEN — yol, status code, yanıt şeması ve anonim erişim onayı bekleniyor.

## 11. Bu ciltte kapatılmayan hususlar

Aşağıdakiler kullanıcı kararına bağlıdır ve açık kalır:

- Web token yaklaşımı ve deployment origin'leri.
- Android güvenli saklama uygulaması.
- Access/refresh token yaşam döngüsü.
- Devre dışı kullanıcı ve mevcut oturum davranışı.
- Parola politikası, ilk giriş ve parola sıfırlama kapsamı.
- Rate limit sayısal eşikleri.
- Endpoint bazında permission matrisi.
- Health endpoint yolları ve response sözleşmesi.

Her karar onaylandığında Cilt 1.25 sicili ve etkilenen güvenlik/API/test belgeleri güncellenecektir. Onay, tek başına migration yetkisi değildir.

## 12. Sonraki adım

Önce REG-125-08 için web token yaklaşımını seç. Seçim yapıldıktan sonra yalnızca o kararı kapatmak için gereken deployment bilgileri ve testler netleştirilecek; ardından REG-125-09'a geçilecek.

**Genel durum: SECURITY DECISIONS OPEN — EXTERNAL LLM HANDOFF NOT READY — MIGRATION NOT AUTHORIZED.**
