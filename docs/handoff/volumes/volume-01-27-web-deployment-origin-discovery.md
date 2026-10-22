# Cilt 1.27 — Web/API Deployment Origin Keşfi


> **Normatif güncelleme — 22 Ekim 2026 (Cilt 1.32):** Bu belgedeki daha eski ve çelişen taslak ifadeler için `volume-01-32-approved-decisions-and-cross-check.md` ile Cilt 1.31'in onay kaydı önceliklidir. Bu not doküman sözleşmesini günceller; migration veya veritabanı değişikliği izni değildir.

**Tarih:** 22 Ekim 2026  
**Durum:** Keşif belgesi; REG-125-08 kararı hâlâ OPEN.  
**Ön koşul:** Proje sahibi REG-125-08 için C seçeneğini seçti: önce deployment/origin yapısı netleştirilecek.  
**Kapsam dışı:** Diğer güvenlik kararlarını kapatmak, token yaklaşımını seçmek, migration üretmek veya DB değiştirmek.

## 1. Neden bu cilt gerekli?

Cookie ve CSRF ayarları web paneli ile API'nin gerçek dağıtım biçimine bağlıdır. “Aynı origin”, “cross-origin” ve “cross-site” birbirinin yerine kullanılamaz. Bu nedenle token yaklaşımını seçmeden önce şu bilgileri karara bağlamak gerekir:

- Web panelinin üretim ve geliştirme adresi.
- API'nin üretim ve geliştirme adresi.
- Web ve API'nin aynı origin, farklı origin ama aynı site, yoksa farklı site olup olmadığı.
- HTTPS ve reverse proxy kullanımı.
- Cookie domain/path/SameSite gereksinimleri.
- CORS ve CSRF koruma modeli.
- Yarışma demosunun internete açık mı, yerel ağda mı, tek bilgisayarda mı çalışacağı.

Bu bilgiler henüz kesin değilse “aynı origin olacak” diye varsayım yapılmamalıdır.

## 2. Kavramlar

- **Origin:** Şema + host + port birleşimi. Örneğin `https://app.example.test` ile `https://api.example.test` farklı origin'dir.
- **Site:** Tarayıcının SameSite cookie davranışında kullandığı site bağlamı; origin ile aynı kavram değildir.
- **CORS:** Tarayıcının farklı origin'ler arasındaki belirli istekleri JavaScript'e açıp açmayacağını kontrol eder.
- **CSRF:** Tarayıcının otomatik gönderdiği kimlik bilgileri kullanılarak kullanıcının istemediği bir işlem yaptırılması riskidir.
- **HttpOnly:** JavaScript'in cookie değerini doğrudan okumasını engeller; XSS'i ortadan kaldırmaz.
- **Secure:** Cookie'nin HTTPS üzerinden gönderilmesini sınırlar.
- **SameSite:** Cookie'nin cross-site isteklerde gönderilme davranışını sınırlar; tek başına tüm CSRF senaryolarını çözmez.

## 3. Deployment modelleri

### Model A — Aynı origin altında reverse proxy

Örnek şablon:
- Web: `https://<domain>/`
- API: `https://<domain>/api/`

Artıları:
- Tarayıcı tarafında CORS karmaşıklığı genellikle azalır.
- Cookie kapsamını yönetmek daha basit olabilir.
- Yarışma demosunda anlaşılır bir topoloji sağlar.

Açık noktalar:
- Reverse proxy yapılandırması ve `/api` yönlendirmesi.
- Cookie path/domain ayarları.
- HTTPS sertifikası ve proxy başlıklarının güvenli yönetimi.
- Yerel geliştirme ortamının üretimden farklı olup olmayacağı.

### Model B — Farklı origin, aynı site

Örnek şablon:
- Web: `https://app.<domain>`
- API: `https://api.<domain>`

Artıları:
- Web ve API dağıtımları ayrılabilir.
- İki host da aynı site altında ise cookie politikası cross-site modele göre daha kolay olabilir.

Açık noktalar:
- CORS allowlist'i kesin origin'lerle sınırlandırılmalı.
- Credential içeren isteklerde wildcard origin kullanılmamalı.
- CSRF savunması ve Origin/Referer doğrulama stratejisi belgelenmeli.
- Cookie domain kapsamı gereksiz geniş tutulmamalı.

### Model C — Farklı site

Örnek şablon:
- Web: `https://<web-provider-domain>`
- API: `https://<api-provider-domain>`

Risk/karmaşıklık:
- Üçüncü taraf cookie kısıtlamaları ve `SameSite=None; Secure` gereksinimleri gündeme gelebilir.
- Tarayıcı ve dağıtım ortamına bağlı farklı davranışlar olabilir.
- Cookie tabanlı oturum için test matrisi büyür.

Açık noktalar:
- Kullanılan tarayıcılar ve demo ortamı.
- Cross-site cookie davranışının desteklenip desteklenmediği.
- Alternatif token taşıma yaklaşımının gerekip gerekmediği.
- CORS ve CSRF'in birlikte test edilmesi.

## 4. Karar için doldurulması gereken bilgiler

Aşağıdaki alanlar kullanıcı tarafından doldurulmalı veya dağıtım planı netleştirildikten sonra güncellenmelidir. Bilinmeyen değerler bilinmiyor olarak kalmalıdır.

| Alan | Şu anki durum | Neden gerekli |
|---|---|---|
| Web geliştirme URL'si | TBD | Yerel geliştirme origin ve cookie davranışı |
| API geliştirme URL'si | TBD | CORS ve CSRF testleri |
| Web üretim/demo URL'si | TBD | Gerçek tarayıcı origin'i |
| API üretim/demo URL'si | TBD | Gerçek API origin'i |
| Aynı origin mi? | TBD | CORS gereksinimi |
| Aynı site mi? | TBD | SameSite/cookie davranışı |
| HTTPS | TBD | Secure cookie ve taşıma güvenliği |
| Reverse proxy | TBD | Route, host ve forwarded header davranışı |
| Demo nerede çalışacak? | TBD | Yarışma gösterimi ve ağ varsayımları |
| Tarayıcı kapsamı | TBD | Test matrisi |

## 5. Karar kuralı

1. Web ve API'nin URL/topoloji bilgileri netleşmeden REG-125-08 için A veya B kesinleştirilmez.
2. Eğer aynı-origin reverse proxy modeli seçilirse HttpOnly cookie yaklaşımı ve CSRF koruması en az karmaşıklıkla değerlendirilebilir; yine de bu otomatik onay sayılmaz.
3. Eğer farklı origin veya farklı site modeli seçilirse CORS, credentials, cookie ayarları ve CSRF testleri birlikte tasarlanır.
4. Bearer token seçeneği ancak tehdit modeli, istemci saklama biçimi ve XSS riski değerlendirilerek ele alınır.
5. CORS, kimlik doğrulama veya CSRF'nin yerine geçmez.
6. İstemci tarafından gönderilen `Origin` tek başına güvenilir kimlik doğrulama kanıtı değildir.
7. Geliştirme ortamı için gevşetilen güvenlik ayarları üretim ayarlarına otomatik kopyalanmamalıdır.

## 6. Doğrulama/test gereksinimleri

Seçilecek topolojiye göre en az şu testler planlanmalıdır:

- İzin verilen web origin'inden API çağrısı başarılı olur.
- İzin verilmeyen origin'e CORS izni verilmez.
- Cookie kullanılıyorsa cookie'de `HttpOnly`, HTTPS için `Secure` ve seçilen `SameSite` davranışı doğrulanır.
- CSRF koruması gerektiren state-changing istek, koruma olmadan reddedilir.
- Kimlik bilgisi gerektiren endpoint anonim çağrıda reddedilir.
- CORS hatası, CSRF reddi ve auth reddi birbirine karıştırılmaz.
- Üretim/demo HTTPS ayarları ile yerel geliştirme ayarları ayrı test edilir.
- Cookie değerleri, access token veya secrets loglara yazılmaz.

## 7. Proje sahibinden gereken tek sonraki bilgi

**Web paneli ve FastAPI backend yarışma demosunda nerede ve nasıl çalışacak?**

Şimdilik aşağıdaki seçeneklerden en yakınını belirlemek yeterlidir:

- **A:** Tek makine/tek domain; reverse proxy ile web ve API aynı origin altında.
- **B:** Ayrı web ve API alt alan adları; aynı ana domain/site altında.
- **C:** Web ve API farklı hosting sağlayıcılarının farklı domainlerinde.
- **D:** Henüz belli değil; önce demo/hosting mimarisini kararlaştıralım.

Seçim URL'lerin kesinleştiği anlamına gelmez; yalnızca keşif yönünü belirler.

## 8. Durum

- REG-125-08: **OPEN**
- REG-125-09–REG-125-15: **OPEN**; bu cilt bunları kapatmaz.
- ERD/API/permission matrisi için nihai güvenlik çapraz kontrolü: bekliyor.
- Migration: **NOT AUTHORIZED**.
- Harici LLM kodlama devri: **NOT READY**.


### Cilt 1.34 normatif override — health/auth

- Health paths are `GET /health/live` and `GET /health/ready`, outside `/api/v1`.
- Both are anonymous. Liveness performs no database/dependency query and returns 200 when the process is alive. Readiness returns 200 only when required dependencies are ready; otherwise 503. Neither response leaks secrets or detailed connection errors.
- Auth contract: 15-minute access token, 7-day rotating refresh token, server-side refresh-session revocation on logout, refresh-token reuse revokes the token family.
- Web uses the approved single-origin reverse-proxy topology, HttpOnly cookie, SameSite=Lax, Secure under HTTPS, host-only Path=/ cookie, and synchronizer CSRF token for state-changing requests.
- This override changes documentation priority only; deployment and runtime tests remain required.
