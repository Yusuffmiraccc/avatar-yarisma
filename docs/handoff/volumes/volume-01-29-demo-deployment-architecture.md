# Cilt 1.29 — Demo Deployment Mimarisi ve Web Auth Karar Taslağı


> **Normatif güncelleme — 22 Ekim 2026 (Cilt 1.32):** Bu belgedeki daha eski ve çelişen taslak ifadeler için `volume-01-32-approved-decisions-and-cross-check.md` ile Cilt 1.31'in onay kaydı önceliklidir. Bu not doküman sözleşmesini günceller; migration veya veritabanı değişikliği izni değildir.

**Tarih:** 22 Ekim 2026  
**Durum:** Önerilen mimari; kullanıcı genel yaklaşımı onayladı, ancak bu belge ayrıntıların nihai onayı yerine geçmez.  
**İlgili karar:** REG-125-08  
**Kapsam:** Yarışma demosu için yerel, tekrarlanabilir kurulum ve web/API origin yaklaşımı.  
**Kapsam dışı:** REG-125-09–REG-125-15 kararlarını kapatmak, Alembic migration üretmek veya veritabanı oluşturmak/değiştirmek.

## 1. Onaylanan yön ve sınırlar

Kullanıcı, önerilen yaklaşımla ilerlemeyi kabul etti. Bu cilt aşağıdaki yönü önerilen çalışma temeli olarak kaydeder:

- Öncelik: yerel ortamda yeniden üretilebilir demo.
- Kurulum: Docker Compose ile servislerin çalıştırılması; kesin servis listesi repo uygulama planında netleştirilecek.
- Teslimat: public GitHub repo, README, örnek veri ve test talimatları; en fazla 15 dakikalık demo videosu.
- Web/API: mümkünse tek origin altında reverse proxy; uygulama ve proxy konfigürasyonu doğrulandıktan sonra nihai hale getirilecek.
- Web auth: HttpOnly cookie + CSRF, tek-origin yaklaşımı üzerinde değerlendirilecek; henüz kesinleştirilmiş değil.
- Production/public hosting: yarışma metninde açıkça zorunlu değil; ihtiyaç oluşmadıkça canlı deployment varsayılmayacak.

Bu onay REG-125-08'in bütün alt kararlarını otomatik olarak kapatmaz. Özellikle cookie ayarları, CSRF token/validation yöntemi, logout ve token yaşam döngüsü ayrı kararlardır.

## 2. Önerilen topoloji

```text
Browser
  |
  | http(s)://<single-demo-origin>/
  v
Reverse proxy / web entrypoint
  |-- /              -> React web build
  |-- /api/v1/...    -> FastAPI backend
  |
  v
FastAPI
  |-- MySQL 8.4 LTS (backend-only access)
  |-- ML module / prediction endpoints
```

Bu şema hedef topolojidir; mevcut repoda Dockerfile, proxy config ve frontend build yapısı görülmeden uygulandı veya test edildi sayılmaz.

### İlk geliştirme ortamı
- Docker Compose, servisleri tek komutla başlatmayı hedefler.
- Reverse proxy, `/api/v1` isteklerini FastAPI'ye aktarır.
- React statik build'i aynı origin üzerinden sunulur.
- MySQL yalnızca backend ağından erişilebilir olacak şekilde yapılandırılır.
- Gerekli ortam değişkenleri `.env.example` içinde isimleriyle belgelenir; gerçek secret'lar repoya eklenmez.
- Geliştirme ortamında TLS kullanımı/yerel HTTP istisnası ayrıca belgelenir; HTTP üzerinde `Secure` cookie testleri gerçek HTTPS davranışını doğrulamaz.

## 3. Web authentication yönü

### Önerilen başlangıç
- Oturum token'ı `HttpOnly` cookie ile taşınsın.
- Üretim/HTTPS ortamında `Secure` etkin olsun.
- `SameSite` seçimi topoloji ve gerekli istek akışlarına göre belirlenip test edilsin; burada sabit bir değer dayatılmıyor.
- State-changing endpoint'ler için CSRF koruması tasarlansın; sadece CORS'a güvenilmesin.
- Credential içeren CORS yapılandırmasında wildcard origin kullanılmasın.
- Cookie domain'i gereksiz yere geniş tutulmasın.
- Token/cookie değeri loglara yazılmasın.

### Hâlâ karar gerektiren ayrıntılar
1. CSRF yöntemi (ör. synchronizer token veya double-submit yaklaşımı) ve doğrulama yeri.
2. Cookie adı, path ve domain.
3. `SameSite` değeri ve gerekçesi.
4. Login/logout endpoint davranışı ve yanıt kodları.
5. Access token ve refresh token olup olmayacağı, süreleri ve iptal davranışı.
6. Yerel demo HTTP/HTTPS yaklaşımı ve gerçek HTTPS test ortamı.
7. Reverse proxy forwarded header'larının güvenilir proxy sınırları.

Bu ayrıntılar kararlaştırılmadan REG-125-08 “CLOSED” sayılmaz.

## 4. Güvenlik ilkeleri

- CORS, kimlik doğrulama veya CSRF korumasının yerine geçmez.
- HttpOnly cookie, JavaScript'in cookie değerini okumasını zorlaştırır; XSS'i ortadan kaldırmaz.
- Güvenli cookie ayarları, doğru backend yetkilendirmesinin yerini tutmaz.
- İstemcinin gönderdiği rol veya kullanıcı ID'si yetki kanıtı değildir.
- Kullanıcı devre dışı bırakma ve token iptali davranışı REG-125-11 altında ayrıca kararlaştırılacaktır.
- Android token saklama REG-125-09 altında açık kalacaktır.

## 5. Demo doğrulama senaryoları

- [ ] Temiz bir ortamda README adımlarıyla servisler başlatılabiliyor.
- [ ] Web paneli ve `/api/v1` aynı origin üzerinden erişilebiliyor.
- [ ] Proxy, API hatalarını ve frontend rotalarını doğru yönlendiriyor.
- [ ] Backend MySQL'e erişiyor; istemci doğrudan MySQL'e erişemiyor.
- [ ] Yetkisiz istekler backend tarafından reddediliyor.
- [ ] Cookie kullanılıyorsa ilgili nitelikler ve HTTPS davranışı doğrulanıyor.
- [ ] CSRF koruması gereken istek, eksik/yanlış CSRF kanıtıyla reddediliyor.
- [ ] CORS yalnızca gerçekten ihtiyaç duyulan origin'lere izin veriyor.
- [ ] Secret/token değerleri loglarda veya Git geçmişinde bulunmuyor.
- [ ] Seed/demo senaryosu tekrar çalıştırılabiliyor.
- [ ] Üç görev, özellikle `ET-2026-001` recall akışı, aynı demo ortamında gösterilebiliyor.

## 6. Karar durumu

| Kayıt | Durum | Not |
|---|---|---|
| Yerel, tekrarlanabilir demo | AGREED DIRECTION | Ayrıntılı Compose servisleri/konfigürasyonu henüz doğrulanmadı |
| Tek origin/reverse proxy | PROPOSED | Repo ve testlerle uygulanabilirliği doğrulanmalı |
| HttpOnly cookie + CSRF | PROPOSED | CSRF ayrıntıları ve cookie nitelikleri açık |
| REG-125-09 Android token storage | OPEN | Bu cilt kapatmaz |
| REG-125-10 access/refresh/logout | OPEN | Bu cilt kapatmaz |
| REG-125-11 disabled user/token | OPEN | Bu cilt kapatmaz |
| REG-125-12 password/first login | OPEN | Bu cilt kapatmaz |
| REG-125-13 rate limit | OPEN | Bu cilt kapatmaz |
| REG-125-14 endpoint permissions | OPEN | Bu cilt kapatmaz |
| REG-125-15 health endpoints | OPEN | Bu cilt kapatmaz |
| DB migration | NOT AUTHORIZED | Kullanıcıdan ayrıca açık onay gerektirir |

## 7. Sonraki adım

Bir sonraki ciltte web cookie/CSRF ayrıntılarını kesinleştirmeden önce mevcut API auth endpoint sözleşmesiyle çapraz kontrol yapılmalı. Cilt 1.8, 1.9, 1.20, 1.21 ve 1.26 ile çelişki bulunursa sessizce düzeltme yapılmamalı; farklar kayıt altına alınarak kullanıcı kararı istenmelidir.


### Cilt 1.34 normatif override — health/auth

- Health paths are `GET /health/live` and `GET /health/ready`, outside `/api/v1`.
- Both are anonymous. Liveness performs no database/dependency query and returns 200 when the process is alive. Readiness returns 200 only when required dependencies are ready; otherwise 503. Neither response leaks secrets or detailed connection errors.
- Auth contract: 15-minute access token, 7-day rotating refresh token, server-side refresh-session revocation on logout, refresh-token reuse revokes the token family.
- Web uses the approved single-origin reverse-proxy topology, HttpOnly cookie, SameSite=Lax, Secure under HTTPS, host-only Path=/ cookie, and synchronizer CSRF token for state-changing requests.
- This override changes documentation priority only; deployment and runtime tests remain required.
