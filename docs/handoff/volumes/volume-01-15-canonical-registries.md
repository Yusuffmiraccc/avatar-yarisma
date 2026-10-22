# Cilt 1.15 — Kanonik Sözlükler ve API/Şema Eşlemesi

**Tarih:** 22 Ekim 2026  
**Durum:** Dokümantasyon normatifleştirme turu; migration öncesi kontrol sürüyor.  
**Kapsam:** Permission, enum, error, side-effect ve DTO sözlükleri için tek referans noktası.

> Bu belge uygulama sözleşmesini birleştirir; gerçek OpenAPI üretimi, ORM metadata diff'i veya DB diff'i yapıldığı anlamına gelmez. Bir alanın ERD tipi/nullable davranışı ilgili tablo tanımıyla ayrıca karşılaştırılmalıdır.

## 1. Permission registry

| Endpoint/işlem | Permission | İzinli roller | Negatif test |
|---|---|---|---|
| Login | public | Public | Yanlış kimlik bilgisi `401` |
| Katalog okuma | `catalog:read` | Tüm roller | Auth yoksa `401` |
| Katalog yönetimi | `catalog:manage` | ADMIN | Diğer roller `403` |
| Stok kabulü | `inventory:receive` | ADMIN, OPERATOR | SALES/TM/VIEWER `403` |
| Genel stok düzeltme/ters kayıt | `inventory:adjust` | ADMIN | ADMIN dışı `403` |
| Üretim/parçalama yönetimi | `production:manage`, `butchering:manage` | ADMIN, OPERATOR | Diğer roller `403` |
| Satış oluşturma | `sales:manage` | ADMIN, SALES | OPERATOR/TM/VIEWER `403` |
| Sevkiyat taslağı oluşturma | `shipments:manage` | ADMIN, SALES | OPERATOR/TM/VIEWER `403` |
| Sevkiyat dispatch | `shipments:dispatch` | ADMIN, SALES | OPERATOR/TM/VIEWER `403` |
| Traceability okuma | `traceability:read` | ADMIN, OPERATOR, SALES, TRACEABILITY_MANAGER, VIEWER (read-only) | Auth yoksa `401` |
| Recall activate/resolve | `recalls:activate`, `recalls:resolve` | ADMIN, TRACEABILITY_MANAGER | Diğer roller `403` |
| AI tahmini başlatma | `ai:predict` | ADMIN, OPERATOR | SALES/TM/VIEWER `403` |
| AI tahmin sonucu/metrik okuma | `ai:metrics:read` | ADMIN, OPERATOR, TRACEABILITY_MANAGER, VIEWER | SALES `403` |
| Audit okuma | `audit:read` | ADMIN, TRACEABILITY_MANAGER | Diğer roller `403` |
| Liveness | public | Public | Response'ta dependency/DB ayrıntısı yok |
| Readiness | internal veya `health:read` | Internal network / ADMIN | Yetkisiz dış istek reddedilir |

## 2. Shipment state registry

MVP durum enumu: `DRAFT`, `SHIPPED`, `CANCELLED`, `RETURNED`.

- `DRAFT → SHIPPED`: dispatch transaction'ı başarıyla tamamlandığında; tek `OUT/SHIPMENT` oluşturulur.
- `DRAFT → CANCELLED`: stok hareketi oluşturmadan iptal.
- `SHIPPED → RETURNED`: yalnızca kayıtlı iade/ters stok hareketi akışıyla.
- `DELIVERED` kullanılmaz; MVP teslim kanıtı tutmaz.
- `DISPATCHED` komut/işlem fiilidir, DB enum değeri değildir.
- `PREPARED` kalıcı enum değildir; mevcut ERD'de hazırlık için ayrı kalıcı alan tanımlanmadığından durum olarak kullanılmaz.

## 3. Error registry — MVP temel sözlük

| HTTP | `error.code` | Koşul |
|---:|---|---|
| 400 | `VALIDATION_ERROR` | Alan/şema doğrulaması başarısız |
| 401 | `UNAUTHENTICATED` | Kimlik doğrulama yok/geçersiz |
| 403 | `FORBIDDEN` | Rol/izin yetersiz |
| 404 | `NOT_FOUND` | Kaynak yok veya erişim kapsamı dışında |
| 409 | `CONFLICT` | Özel kod tanımlanmamış genel durum çakışması |
| 409 | `IDEMPOTENCY_KEY_REUSED` | Aynı key farklı request hash ile kullanıldı |
| 409 | `INSUFFICIENT_STOCK` | Kullanılabilir stok yetersiz |
| 409 | `LOT_BLOCKED` | Lot aktif blokaj/recall nedeniyle işlem göremez |
| 409 | `INVALID_STATE_TRANSITION` | Kaynağın mevcut durumundan geçiş yapılamaz |
| 500 | `INTERNAL_ERROR` | Beklenmeyen hata; iç ayrıntı/log dışarı verilmez |

Kural: Uygun özel kod varsa onu kullan; aynı olayı bazen `CONFLICT`, bazen özel kodla rastgele yanıtlamak yasaktır. Response envelope: `error: {code, message, details?}`, `request_id`.

## 4. Token, logout ve health sözleşmesi

- Access token ömrü 15 dakika (`expires_in=900`); refresh token 7 gün, rotation zorunlu; logout refresh session'ını iptal eder ve reuse token ailesini iptal eder (Cilt 1.31/1.32 onaylı).
- `POST /api/v1/auth/logout` `204` döner; istemci token'ı temizler. Server-side revoke/blacklist yoktur, token'ın anında iptal edildiği iddia edilmez.
- `GET /api/v1/health/live` public ve minimal liveness'tır.
- `GET /api/v1/health/ready` internal network veya ADMIN erişimiyle sınırlandırılır; dışarıya DB/host/connection/secret ayrıntısı dönmez.
- Genel `/api/v1/health` canonical endpoint değildir.
- Response correlation `X-Request-ID` header'ı üzerinden sağlanır; hata envelope'undaki `request_id` aynı değerdir.

## 5. Side-effect registry

| Komut | Stock ledger | Balance | Cost/genealogy | Audit | Retry/idempotency |
|---|---|---|---|---|---|
| Lot kabulü/alış girişi | `IN/RECEIPT` | Artar | Maliyet kaydı varsa bağlanır | Evet | Aynı iş belgesi ikinci giriş yaratmamalı |
| Üretim başlatma | Yok | Değişmez | Yok/plan bilgisi | Evet | State guard |
| Üretim tamamlama | Girdiler için `OUT/PRODUCTION`; çıktılar için `IN/PRODUCTION_OUTPUT` | Aynı transaction'da güncellenir | EKP + genealogy | Evet | Tamamlanmış emir ikinci kez etkilenmez |
| Parçalama tamamlama | Girdi `OUT/BUTCHERING`; çıktı lotları `IN/BUTCHERING_OUTPUT`; fire sınıfına göre ölçüm | Aynı transaction'da güncellenir | Tahsis + genealogy | Evet | Tamamlanmış emir ikinci kez etkilenmez |
| Satış oluşturma/tamamlama | **Hiçbir stok hareketi yok** | Değişmez | Ticari tutar | Evet | `Idempotency-Key` zorunlu; aynı key/body replay |
| Dispatch | Satır başına tek `OUT/SHIPMENT` | Azalır | Lot/sevkiyat genealogy veya trace link | Evet | Idempotent; aynı sevkiyat ikinci OUT üretemez |
| Recall activate | Ledger hareketi yok; lot blokajı | Kullanılabilir miktar satış/sevkiyat için engellenir | Etkilenen lot kapsamı kaydedilir | Evet | Atomik aktivasyon; retry aynı sonucu verir |
| Recall resolve/close | Otomatik `IN`/unblock yok | Blokaj ayrı yetkili aksiyon olmadan kalkmaz | Çözüm kaydı | Evet | İdempotent state guard |
| İade/ters kayıt | Açık ters/IN hareketi | Artar yalnızca fiziksel kabul gerçekleşirse | Orijinal belge/lot referansı | Evet | Orijinal işlem hard-delete edilmez |

## 6. Nullable registry ve schema-to-DTO kapısı

Cilt 1.2 tablo tanımları her kolon için authoritative kaynaktır; API DTO nullable işaretleriyle birebir eşleşme yapılmadan migration onaylanamaz. Nullable anlamı üç kategoriden biriyle açıklanmalı: (1) henüz bilinmiyor, (2) bu kayıt türünde uygulanamaz, (3) gerçekten opsiyonel. `NULL` ile boş string/0/`UNKNOWN` birbirinin yerine kullanılamaz.

Sonraki kontrol tablosu her kolon için şu sütunları doldurmalıdır: `table.column`, DB type, NULL?, gerekçe, FK/UNIQUE/CHECK, DTO field, JSON type, enum/validation, source document, test ID. Bu cilt ERD'de tanımlanmamış kolonları sessizce eklemez.

## 7. Migration öncesi doğrulama kapısı

- [ ] Cilt 1.2 tüm tablo/kolon/NULL/FK/UNIQUE/CHECK/index envanteri çıkarıldı.
- [ ] Cilt 1.3 endpoint ↔ permission registry eşleşmesi tamamlandı.
- [ ] Cilt 1.4 OpenAPI/DTO/error/idempotency testleri sözlüklerle eşleşti.
- [ ] Cilt 1.5 state machine enum registry ile aynı.
- [ ] Cilt 1.6 transaction side-effect tablosu side-effect registry ile aynı.
- [ ] Cilt 1.7 constraint/seed kuralları ERD ile karşılaştırıldı.
- [ ] Cilt 1.8/1.9 token, role, health ve permission sözleşmeleri aynı.
- [ ] Nullable registry ve schema-to-DTO matrisi tamamlandı.
- [ ] Gerçek OpenAPI/ORM metadata diff'i yapıldı ve raporlandı.
- [ ] Kullanıcıya son şema/API özeti sunuldu; migration dosyası üretimi için ayrıca açık onay alındı.

**Bu cilt migration yetkisi vermez.**


### Cilt 1.34 health/auth registry override
- Current canonical health paths are `GET /health/live` and `GET /health/ready` (not `/api/v1/health/*`).
- Both are anonymous; liveness does no DB query and returns 200 when process is alive; readiness returns 200/503 based on required dependency readiness.
- Current auth lifecycle: access 15m, refresh 7d with rotation, logout refresh-session revoke, reuse token-family revoke.
