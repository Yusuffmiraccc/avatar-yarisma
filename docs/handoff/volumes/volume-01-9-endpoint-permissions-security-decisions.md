# Cilt 1.9 — Endpoint Yetkilendirme Matrisi ve Güvenlik Kararları


> **Normatif güncelleme — 22 Ekim 2026 (Cilt 1.32):** Bu belgedeki daha eski ve çelişen taslak ifadeler için `volume-01-32-approved-decisions-and-cross-check.md` ile Cilt 1.31'in onay kaydı önceliklidir. Bu not doküman sözleşmesini günceller; migration veya veritabanı değişikliği izni değildir.

**Durum:** Cilt 1.3 endpoint'leri üzerinden hazırlanmış güvenlik eşleştirme çalışması; aşağıdaki öneriler kullanıcı onayı gerektirir  
**Tarih:** 22 Ekim 2026  
**Bağlı belgeler:** Cilt 1.3, Cilt 1.4, Cilt 1.5, Cilt 1.6, Cilt 1.7, Cilt 1.8, DEC-001, ADR-001

## 1. Amaç

Cilt 1.8'deki genel rol/izin modelini, Cilt 1.3'te gerçekten tanımlanmış endpoint'lerle eşleştirir. Amaç, API router'ları geliştirilirken hangi rolün hangi işlemi yapabileceğinin tahmin edilmesini önlemek ve açık güvenlik kararlarını tek yerde görünür kılmaktır.

**Önemli:** Bu belge, önerilen izin matrisidir; rol/izin kararları kullanıcı tarafından onaylanana kadar nihai politika sayılmaz. Cilt 1.3'te tanımlanmamış yeni endpoint eklemez.

## 2. İzin ve rol anahtarları

Roller:
- `ADMIN`
- `OPERATOR`
- `SALES`
- `TRACEABILITY_MANAGER`
- `VIEWER`

İzin adları Cilt 1.8'deki izin sözlüğünü kullanır. Endpoint'e erişim için hem kimlik doğrulama hem de gerekli izin gerekir; public endpoint'ler istisnadır.

Kısaltmalar:
- `PUB`: Public, token gerektirmez.
- `ALL`: Beş rolün tamamı, ilgili kaynak kapsamı kontrolleriyle.
- `A`: `ADMIN`
- `O`: `OPERATOR`
- `S`: `SALES`
- `T`: `TRACEABILITY_MANAGER`
- `V`: `VIEWER`
- `A+O`: yalnızca ADMIN ve OPERATOR
- `A+T`: yalnızca ADMIN ve TRACEABILITY_MANAGER

## 3. Endpoint bazlı önerilen yetkilendirme matrisi

### 3.1 Auth ve kullanıcı erişimi

| Method + path | Auth | Önerilen rol/izin | Ek güvenlik kuralı |
|---|---|---|---|
| `POST /api/v1/auth/login` | PUB | — | Rate limit; genel kimlik bilgisi hatası; parola loglanmaz |
| `GET /api/v1/auth/me` | Evet | Tüm aktif roller / `auth:read_self` | Token subject aktif kullanıcıyla eşleşmeli |
| `POST /api/v1/auth/logout` | Evet | Tüm aktif roller | Token-only logout ile server-side revoke ayrımı SEC-03 kararıyla netleşmeli |

Cilt 1.3'te kullanıcı yönetimi endpoint'leri listelenmediğinden bu ciltte yeni `users` endpoint'leri tanımlanmamıştır. Admin bootstrap bir CLI/kurulum işlemi olarak ayrı ele alınır.

### 3.2 Katalog

| Method + path | Auth | Önerilen rol/izin | Ek güvenlik kuralı |
|---|---|---|---|
| `GET /api/v1/products` | Evet | `ALL` / `catalog:read` | Pasif ürünler filtreyle veya rol politikasına göre görünür |
| `POST /api/v1/products` | Evet | `A` / `catalog:manage` | `code` unique; geçmiş işlemler değiştirilmez |
| `GET /api/v1/products/{product_id}` | Evet | `ALL` / `catalog:read` | Kaynak kapsamı kontrolü |
| `PATCH /api/v1/products/{product_id}` | Evet | `A` / `catalog:manage` | Sadece izin verilen alanlar |
| `GET /api/v1/units` | Evet | `ALL` / `catalog:read` | Sözlük okuma |
| `GET /api/v1/suppliers` | Evet | `A`, `O`, `T` / `catalog:read` | `SALES` ve `VIEWER` için erişim verilmesi ayrı ürün kararı |
| `POST /api/v1/suppliers` | Evet | `A` / `catalog:manage` | Unique/validasyon |
| `GET /api/v1/customers` | Evet | `A`, `O`, `S`, `T` / `catalog:read` | `VIEWER` erişimi Cilt 1.3'te net değil; varsayılan olarak yok |
| `POST /api/v1/customers` | Evet | `A` / `catalog:manage` | Audit |

### 3.3 Lot ve stok

| Method + path | Auth | Önerilen rol/izin | Ek güvenlik kuralı |
|---|---|---|---|
| `GET /api/v1/lots` | Evet | `ALL` / `inventory:read` | Tedarikçi gibi alanlar gerekirse rol bazlı azaltılır |
| `GET /api/v1/lots/{lot_id}` | Evet | `ALL` / `inventory:read` | Kaynak kapsamı kontrolü |
| `GET /api/v1/lots/by-code/{lot_code}` | Evet | `ALL` / `inventory:read` | Lot kodu üzerinden aynı erişim politikası |
| `GET /api/v1/inventory/balances` | Evet | `ALL` / `inventory:read` | Güncel bakiye; audit kaynağı movement ledger |
| `GET /api/v1/inventory/movements` | Evet | `A`, `O`, `T`; `S` yalnızca kendi satış hareketleri / `inventory:read` veya kapsamlı satış okuma | Satış hareketlerinin scope filtresi backend'de uygulanır |
| `POST /api/v1/inventory/receipts` | Evet | `A`, `O` / `inventory:receive` | Lot + IN movement + balance + audit tek transaction |
| `POST /api/v1/inventory/adjustments` | Evet | `A` / `inventory:adjust` | Onaylı: yalnızca ADMIN; gerekçe zorunlu |

**Önceki uyuşmazlık — Revizyon 1.11 ile kapatıldı:** Stok düzeltme yalnızca ADMIN yetkisindedir; OPERATOR normal kabul/üretim hareketlerini yürütür.

### 3.4 Üretim emirleri

| Method + path | Auth | Önerilen rol/izin | Ek güvenlik kuralı |
|---|---|---|---|
| `POST /api/v1/production-orders` | Evet | `A`, `O` / `production:manage` | Taslak/plan oluşturur |
| `GET /api/v1/production-orders` | Evet | `A`, `O`, `T`, `V` / `production:read` | SALES varsayılan olarak yok |
| `GET /api/v1/production-orders/{order_id}` | Evet | `A`, `O`, `T`, `V` / `production:read` | Aynı kapsam kuralı |
| `POST /api/v1/production-orders/{order_id}/inputs` | Evet | `A`, `O` / `production:manage` | Lot kullanılabilirliği tamamlamada tekrar kontrol edilir |
| `POST /api/v1/production-orders/{order_id}/service-costs` | Evet | `A`, `O` / `production:manage` | Maliyet girdisi audit edilir |
| `POST /api/v1/production-orders/{order_id}/outputs` | Evet | `A`, `O` / `production:manage` | Çıktı miktarı pozitif ve birim uyumlu |
| `POST /api/v1/production-orders/{order_id}/complete` | Evet | `A`, `O` / `production:complete` | Stok, genealogy, maliyet ve durum atomik |
| `POST /api/v1/production-orders/{order_id}/cancel` | Evet | `A`, `O` / `production:manage` | Yalnızca iş etkisi oluşmadan; aksi halde düzeltme akışı |

### 3.5 Parçalama emirleri

| Method + path | Auth | Önerilen rol/izin | Ek güvenlik kuralı |
|---|---|---|---|
| `POST /api/v1/butchering-orders` | Evet | `A`, `O` / `butchering:manage` | Girdi lotu ve maliyet temeli doğrulanır |
| `GET /api/v1/butchering-orders` | Evet | `A`, `O`, `T`, `V` / `butchering:read` | SALES varsayılan olarak yok |
| `GET /api/v1/butchering-orders/{order_id}` | Evet | `A`, `O`, `T`, `V` / `butchering:read` | Aynı kapsam kuralı |
| `POST /api/v1/butchering-orders/{order_id}/inputs` | Evet | `A`, `O` / `butchering:manage` | Girdi lotu blokaj ve miktar kontrolü |
| `POST /api/v1/butchering-orders/{order_id}/outputs` | Evet | `A`, `O` / `butchering:manage` | WF-01 fire nullability kararı uygulanmalı |
| `POST /api/v1/butchering-orders/{order_id}/complete` | Evet | `A`, `O` / `butchering:complete` | Ağırlık dengesi, maliyet tahsisi ve stok etkileri atomik |

### 3.6 Satış

| Method + path | Auth | Önerilen rol/izin | Ek güvenlik kuralı |
|---|---|---|---|
| `POST /api/v1/sales` | Evet | `A`, `S` / `sales:create` | `Idempotency-Key`, stok/lot blokajı, atomic ledger update |
| `GET /api/v1/sales` | Evet | `A`, `S`, `T`, `V` / `sales:read` | `T`/`V` erişimi kapsam ve alan minimizasyonuna tabi |
| `GET /api/v1/sales/{sale_id}` | Evet | `A`, `S`, `T`, `V` / `sales:read` | Aynı kapsam kuralı |
| `POST /api/v1/sales/{sale_id}/void` | Evet | `A` / `sales:correct` | Completed sale hard-delete edilmez; ters kayıt ve gerekçe |

### 3.7 Sevkiyat

| Method + path | Auth | Önerilen rol/izin | Ek güvenlik kuralı |
|---|---|---|---|
| `POST /api/v1/shipments` | Evet | `A`, `S` / `shipments:manage` | Onaylı: OPERATOR ve TRACEABILITY_MANAGER yazamaz |
| `POST /api/v1/shipments/{shipment_id}/dispatch` | Evet | `A`, `S` / `shipments:dispatch` | Onaylı WF-03: tek `OUT/SHIPMENT`; satış OUT üretmez |
| `GET /api/v1/shipments` | Evet | `A`, `O`, `S`, `T`, `V` / `shipments:read` | Gerekli alanları role göre sınırla |
| `GET /api/v1/shipments/{shipment_id}` | Evet | `A`, `O`, `S`, `T`, `V` / `shipments:read` | Aynı kapsam kuralı |

### 3.8 İzlenebilirlik ve recall

| Method + path | Auth | Önerilen rol/izin | Ek güvenlik kuralı |
|---|---|---|---|
| `GET /api/v1/traceability/lots/{lot_id}/backward` | Evet | `ALL` / `traceability:read` | Miktarlı genealogy; olmayan bağlantı tahmin edilmez |
| `GET /api/v1/traceability/lots/{lot_id}/forward` | Evet | `ALL` / `traceability:read` | Kayıtlı müşteri/market bilgisi scope'a tabi |
| `GET /api/v1/traceability/lots/by-code/{lot_code}/summary` | Evet | `ALL` / `traceability:read` | Recall'a esas veri deterministik kayıtlar |
| `POST /api/v1/recalls` | Evet | `A`, `T` / `recalls:manage` | Taslak oluşturma ve gerekçe |
| `POST /api/v1/recalls/{recall_id}/activate` | Evet | `A`, `T` / `recalls:activate` | Lot blokajı ve audit; atomik/outbox kararı WF-05 |
| `GET /api/v1/recalls` | Evet | `ALL` / `recalls:read` | Hassas müşteri alanları role göre sınırlanabilir |
| `GET /api/v1/recalls/{recall_id}` | Evet | `ALL` / `recalls:read` | Aynı kapsam kuralı |
| `POST /api/v1/recalls/{recall_id}/close` | Evet | `A`, `T` / `recalls:resolve` | Çözüm notu/aksiyonlar; blokaj otomatik kalkmaz |
| `PATCH /api/v1/recalls/{recall_id}/customer-impacts/{impact_id}` | Evet | `A`, `T` / `recalls:manage` | İletişim durumu ve audit |

### 3.9 AI, audit ve health

| Method + path | Auth | Önerilen rol/izin | Ek güvenlik kuralı |
|---|---|---|---|
| `POST /api/v1/predictions/production-yield` | Evet | `A`, `O`, `V` önerilir / `ai:predict` | Tahmin stok/maliyet kaydı oluşturmaz |
| `POST /api/v1/predictions/butchering-yield` | Evet | `A`, `O`, `V` önerilir / `ai:predict` | Tahmin gerçek ağırlık yerine geçmez |
| `GET /api/v1/predictions/{prediction_id}` | Evet | `A`, `O`, `T`, `V` / `ai:metrics:read` veya prediction-read izni | Cilt 1.8 izin sözlüğüyle endpoint adı eşleştirilmeli |
| `GET /api/v1/audit-events` | Evet | `A`, `T` / `audit:read` | Hassas alanlar maskelenir; pagination zorunlu |
| `GET /health/live` | Hayır | Public minimal liveness | DB/host/secret bilgisi döndürmez |
| `GET /health/ready` | Hayır | Public readiness; 200 hazır / 503 hazır değil | Secret/DB ayrıntısı döndürmez |

## 4. Güvenlik kararları için önerilen varsayılanlar

Cilt 1.10 önerileri kullanıcı tarafından onaylandığından aşağıdaki satırlar MVP için bağlayıcı sözleşmedir; uygulanması tüm ciltlerde aynılaştırılmalıdır.

| ID | Konu | Önerilen karar | Gerekçe |
|---|---|---|---|
| SEC-01 | Access token ömrü | 30 dakika | Kısa ömür; kesin değer konfigüre edilir |
| SEC-02 | Refresh token | İlk MVP'de yok | İlk sürümü sade tutar; süresi dolunca yeniden login |
| SEC-03 | Logout | İstemci token'ı siler; server-side revoke yoksa bu açıkça belgelenir | Stateless JWT ile tutarlı |
| SEC-04 | Rol değişikliği | Her korumalı istekte aktif kullanıcı ve güncel rol/izin kontrolü | Rol değişikliği hızlı etki eder |
| SEC-05 | İlk admin | Güvenli CLI bootstrap; sabit parola yok | Seed credential riskini azaltır |
| SEC-06 | İlk girişte parola değiştirme | İlk MVP'de zorunlu değil; gerekirse kullanıcı state alanı ve akış eklenir | Mevcut yarışma kapsamı için sade |
| SEC-07 | Web token saklama | Tercihen HttpOnly, Secure, SameSite cookie; CSRF koruması ile | JS erişimli kalıcı token saklamanın XSS etkisini azaltır |
| SEC-08 | Rate limit | Login endpoint'i için uygulama veya reverse proxy katmanında zorunlu | Brute-force azaltma |
| SEC-09 | Audit hatası | Kritik iş transaction'ı audit yazılamıyorsa commit edilmez | Kritik işlemin denetimsiz kalmasını önler |
| SEC-10 | Permission matrix | Bu ciltteki endpoint matrisi Cilt 1.3 ile birlikte onaylanmalı | Tek sözleşme sağlar |
| SEC-11 | Stok düzeltme | İlk sürümde yalnızca ADMIN | OPERATOR yanlışlıkla doğrudan stok düzeltmesi yapmasın |
| SEC-12 | Sevkiyat oluşturma/dispatch | SALES yönetir; OPERATOR yalnızca stok/üretim | İş sorumluluklarını ayırır; işletme ihtiyacı farklıysa değiştirilebilir |

## 5. Önemli uyuşmazlıklar

Aşağıdaki farklılıklar dokümanlar arasında bulunduğu için çözülmeden implementation'a aktarılmamalıdır:

1. **Stok düzeltme:** Cilt 1.3 ADMIN+OPERATOR; Cilt 1.8 ADMIN öneriyor. Bu cilt ADMIN önerisini sunuyor.
2. **Sevkiyat oluşturma:** Cilt 1.3'ün üst seviye matrisi OPERATOR ve TRACEABILITY_MANAGER diyor; endpoint bazlı iş akışında sevkiyat rolü ayrıca net değil. Bu cilt SALES önerisini sunuyor.
3. **AI prediction read:** Cilt 1.3 üst matrisi AI erişimini ADMIN/OPERATOR/TRACEABILITY_MANAGER ve sınırlı VIEWER olarak ifade ediyor; Cilt 1.8 izin sözlüğü ile `GET prediction` izni tam adlandırılmamış.
4. **Health endpoint:** Cilt 1.3'te auth gereksinimi açıkça belirtilmemiş. Liveness ve detaylı dependency health ayrılmalı.
5. **Supplier/customer read:** Cilt 1.3 endpoint'lerinde rol kapsamı tutarlı değil. Bu cilt önerilen matrisi görünür kılıyor.
6. **Logout:** Cilt 1.3 istemci token'ının silindiğini ve server-side invalidation olmadığını belirtiyor; SEC-03 bunu ilk MVP önerisi olarak koruyor.
7. **Token süresi ve logout — KAPATILDI:** Access token 15 dakika (`expires_in: 900`); refresh token 7 gün + rotation; logout refresh session revoke; refresh reuse'da token-family revoke (Cilt 1.31/1.32 onaylı).
8. **Hata kodları:** Cilt 1.3 `CONFLICT` gibi genel kodlar tanımlıyor; Cilt 1.8'deki önerilerle çakışan adlar yeni bir hata kodu olarak eklenmeden önce normalize edilmelidir.

## 6. Onay kontrol listesi

Bu cilt onaylanırken kullanıcıdan aşağıdaki kararlar açıkça alınmalıdır:

- [ ] Endpoint izin matrisi genel olarak onaylandı mı?
- [ ] Stok düzeltme yalnızca ADMIN yetkisinde mi olmalı?
- [ ] Sevkiyat oluşturma ve dispatch sorumluluğu SALES rolünde mi olmalı?
- [ ] `VIEWER` AI tahmini başlatabilmeli mi, yoksa yalnızca tahmin sonuçlarını mı okuyabilmeli?
- [ ] Health liveness public, detaylı DB health korumalı/internal mı olmalı?
- [ ] Access token süresi 30 dakika olarak kabul ediliyor mu?
- [ ] MVP'de refresh token kullanılmaması kabul ediliyor mu?
- [ ] Logout yalnızca istemci token temizliği olarak mı kalacak?
- [ ] Web için HttpOnly Secure SameSite cookie + CSRF yaklaşımı kabul ediliyor mu?
- [ ] Kritik işlem audit kaydı yazılamazsa işlem rollback edilmeli mi?
- [ ] Login rate limiting ilk teslimde zorunlu mu? (Öneri: evet.)
- [ ] İlk girişte parola değiştirme zorunlu mu?

## 7. Sonraki zorunlu adım: şema ve iş akışı çapraz kontrolü

Bu cilt onaylandıktan sonra doğrudan Alembic migration dosyaları yazılmayacaktır. Önce ayrı bir çapraz kontrol raporu hazırlanmalıdır:

- Cilt 1.2 tablo/kolon/nullable/FK/unique/index alanları ile Cilt 1.3 endpoint DTO'ları karşılaştırılır.
- Cilt 1.5 WF-01–WF-10 kararları tek tek kapatılır.
- Cilt 1.2–1.9 arası enum, endpoint, izin, hata kodu ve transaction çelişkileri raporlanır.
- Gerekli doküman düzeltmeleri ve migration revision listesi önerilir.
- Kullanıcı raporu açıkça onaylamadan gerçek Alembic revision dosyaları oluşturulmaz ve veritabanı oluşturulup/değiştirilmez.

Bu onay kapısı kullanıcı tarafından özellikle istenmiştir ve atlanmamalıdır.

## 8. Sonraki belge

Bu endpoint matrisi ve güvenlik kararları onaylandıktan sonra yeni bir cilt yazmak yerine **Cilt 1.2–1.9 çapraz kontrol raporuna** geçmek önerilir. Bu raporun çıktısı, uygulama öncesi son sözleşme düzeltmeleri ve gerçek migration'a geçiş için kullanıcı onayı olacaktır.

## Revizyon 1.11 — Onaylanmış endpoint permission varsayılanları

Bu bölüm, önceki “önerilir/karar gereklidir” tablolarındaki ilgili rol çelişkilerini giderir. Permission key adları Cilt 1.3 ile aynı tutulmalıdır.

| İşlem | İzin verilen roller | Diğer roller |
|---|---|---|
| Genel stok düzeltme | `ADMIN` | Reddedilir |
| Sevkiyat oluşturma | `ADMIN`, `SALES` | Reddedilir; `OPERATOR` ve `TRACEABILITY_MANAGER` read-only |
| Sevkiyat dispatch | `ADMIN`, `SALES` | Reddedilir; `OPERATOR` ve `TRACEABILITY_MANAGER` read-only |
| AI tahmini başlatma | `ADMIN`, `OPERATOR` | Reddedilir |
| AI tahmin sonucunu okuma | `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`, `VIEWER` | `SALES` reddedilir |
| Recall çözme | Recall yönetim izni bulunan yetkili rol | Reddedilir; lot otomatik açılmaz |
| Lot unblock/release | Ayrı `lots:unblock`/eşdeğer açık permission ve audit; varsayılan `ADMIN` ile yetkili `TRACEABILITY_MANAGER` | Diğer roller reddedilir |

### Token ve health standardı
- Access token 30 dakika; refresh token yok. Logout istemci token'ını temizler; server-side revoke varsayılmaz.
- Liveness minimal yanıt verir; detaylı dependency/DB health internal veya yetkili erişime sınırlıdır.
- Web cookie/CSRF taşıma ayrıntıları web istemci entegrasyonundan önce açık sözleşmeye dönüştürülmelidir.

### Migration öncesi açık alt kararlar
- Satış/sevkiyat `OUT` hareketinin tek sahibi dispatch olarak önerilmiştir; nihai iş akışı kararı tüm ciltlere aynı anda işlenmelidir.
- Ağırlık toleransına sayısal değer atanmayacaktır; işletme kararı yoksa `TBD` kalır.
- Düzeltme/ters kayıt ve unblock için kesin permission key ve veri alanları son ERD/API cross-check sırasında tekleştirilmelidir.


### Cilt 1.34 normatif override — health/auth

- Health paths are `GET /health/live` and `GET /health/ready`, outside `/api/v1`.
- Both are anonymous. Liveness performs no database/dependency query and returns 200 when the process is alive. Readiness returns 200 only when required dependencies are ready; otherwise 503. Neither response leaks secrets or detailed connection errors.
- Auth contract: 15-minute access token, 7-day rotating refresh token, server-side refresh-session revocation on logout, refresh-token reuse revokes the token family.
- Web uses the approved single-origin reverse-proxy topology, HttpOnly cookie, SameSite=Lax, Secure under HTTPS, host-only Path=/ cookie, and synchronizer CSRF token for state-changing requests.
- This override changes documentation priority only; deployment and runtime tests remain required.
