# Cilt 1.34 — Kanonik Sözleşmelerin Revizyonu

**Tarih:** 22 Ekim 2026  
**Durum:** Doküman düzeyinde revizyon turu oluşturuldu; runtime doğrulaması ve Cilt 1 kapanışı tamamlanmadı.  
**Kapsam:** Auth/token, health paths, expiry policy, butchering waste/cost allocation, unit/tolerance/reason codes.  
**Migration/DB:** Oluşturulmadı ve çalıştırılmadı. Veritabanı değiştirilmedi.

## 1. Kaynak önceliği

1. Proje sahibinin açıkça onayladığı Cilt 1.31 karar paketi.
2. Cilt 1.32 onay ve çapraz kontrol defteri.
3. Bu revizyon belgesi ve aşağıda listelenen güncellenmiş sözleşmeler.
4. İlgili eski ciltler; yalnızca onaylı kararla çelişmediği ölçüde.

Çelişki varsa eski metin uygulanmaz. Şema veya workflow belirsizse implementasyon varsayım üretmez; `BLOCKED`/`VERIFY` olarak raporlar.

## 2. Bu sürümde somut olarak güncellenen belgeler

| Belge | Revizyon |
|---|---|
| `volume-01-2-erd-and-data-schema.md` | Normatif ek: expiry policy, waste reason codes, weight/cost allocation, rounding, source-lot rules. `requires_expiry_date` fiziksel şemada mevcut mu sorusu açıkça VERIFY olarak bırakıldı. |
| `volume-01-3-api-contracts.md` | Auth sözleşmesi 15m access + 7d refresh/rotation olarak güncellendi; health yolları `/health/live` ve `/health/ready` oldu; eski health/auth summary normatif sözleşmeyle değiştirildi. |
| `volume-01-4-openapi-dto-contract-tests.md` | Auth DTO/contract test gereksinimleri refresh/revoke/reuse ve health paths'e göre güncellendi. |
| `volume-01-23-expiry-waste-cost-weight-unit-decisions.md` | Önceki açık/karar bekliyor etiketlerinin yerini toplu onay sonrası normatif karar tablosu aldı; fiziksel şema doğrulaması ayrı bırakıldı. |
| `volume-01-9-endpoint-permissions-security-decisions.md` | Health/auth için Cilt 1.34 normatif override eklendi. |
| `volume-01-20-auth-permissions-health-reconciliation.md` | Health/auth için Cilt 1.34 normatif override eklendi. |
| `volume-01-27-web-deployment-origin-discovery.md` | Health/auth/origin için Cilt 1.34 normatif override eklendi. |
| `volume-01-29-demo-deployment-architecture.md` | Health/auth/origin için Cilt 1.34 normatif override eklendi. |

## 3. Kanonik auth/API davranışı

### Access/refresh
- Access token: 15 dakika; response alanı `expires_in` saniye olarak `900`.
- Refresh token: 7 gün; refresh her kullanımda rotation.
- Server tarafında refresh token'ın kendisi yerine güvenli hash/session kaydı tutulur.
- Logout refresh session'ını iptal eder.
- Eski refresh token tekrar kullanılırsa token ailesi iptal edilir.
- Disabled user, parola reset ve yetki değişimi davranışları Cilt 1.31 SEC-05/SEC-06 kararlarına uygun uygulanır.
- Android: token plaintext DataStore'a yazılmaz; Android Keystore ile korunan şifreli depolama kullanılır.
- Web: tek origin/reverse proxy; HttpOnly cookie; HTTPS altında Secure; SameSite=Lax; host-only Path=/; state-changing isteklerde session'a bağlı synchronizer CSRF token.

### Health
- `GET /health/live`: anonim; DB/dependency sorgusu yapmaz; süreç canlıysa 200.
- `GET /health/ready`: anonim; gerekli bağımlılıklar hazırsa 200, değilse 503.
- Her iki response da secret, connection string, SQL hata ayrıntısı veya stack trace içermez.
- Bu yollar `/api/v1` altında değildir.

### Error/idempotency
- Error envelope Cilt 1.21 ile aynı kalır: `error.code`, `error.message`, optional `error.details`, `request_id`.
- Satış ve endpoint matrisinde retry-riskli olarak işaretlenen kritik POST işlemleri `Idempotency-Key` kullanır. Aynı key+aynı request body ilk sonucu tekrar verir; aynı key+farklı body 409 döndürür.
- Her kritik workflow'da audit kaydı iş işlemiyle aynı DB transaction'ında yazılır; audit insert başarısızsa işlem rollback olur.
- Bu sürüm idempotency kapsamındaki tüm endpoint'lerin tam sayımını yapmış değildir; Cilt 1.35'te endpoint-by-endpoint matrisi kapatılmalıdır.

## 4. Kanonik butchering/waste kuralları

- Fire kaydı `butchering_waste_records` tablosundadır; `butchering_outputs` içine waste satırı eklenmez.
- Waste satırı satılabilir lot, stok IN hareketi veya genealogy target oluşturmaz.
- Her waste satırı tek kaynak lota bağlıdır; birden çok kaynak lot varsa ayrı satırlar kullanılır.
- Controlled reason codes: `TRIMMING_LOSS`, `BONE_WASTE`, `CONTAMINATION`, `SPOILAGE`, `PROCESS_LOSS`, `OTHER`. `OTHER` için açıklama zorunlu.
- Kanonik ağırlık kg; g ve kg girişleri hesap öncesi kg'a dönüştürülür.
- Tolerans varsayılan 0 kg; fark sessizce kabul edilemez.
- BY_WEIGHT: `CUT + inventory-tracked BYPRODUCT + WASTE` ölçülmüş ağırlıkları maliyet paydasına girer; fire maliyet payı alır.
- BY_VALUE: `WASTE.allocated_cost = 0`; maliyet değer taşıyan stok çıktıları arasında dağıtılır. Değer anahtarı 0/eksikse işlem reddedilir; otomatik BY_WEIGHT fallback yok.
- Her iki yöntem için maliyet toplamı tam uzlaşır; yuvarlama artığı deterministik olarak son tahsis satırına eklenir.
- Allocation maliyetleri backend tarafından hesaplanır, client payload'ından kabul edilmez.

## 5. Bu sürümde çözülmeyen teknik doğrulamalar

| ID | Kontrol | Durum |
|---|---|---|
| C134-01 | `products.requires_expiry_date` fiziksel ERD/ORM'de mevcut mu? | VERIFY |
| C134-02 | `lots.expiry_date` nullability ve ürün politikasına göre API validation | VERIFY |
| C134-03 | `butchering_waste_records` tüm alanları, FK ve constraint'leri onaylı kararla uyumlu mu? | VERIFY |
| C134-04 | `reason_code` enum/check constraint ve OTHER açıklama validation | VERIFY |
| C134-05 | allocation algorithm decimal precision/rounding residual testleri | VERIFY |
| C134-06 | Access/refresh DTO ve OpenAPI response schemas | VERIFY |
| C134-07 | `/health/live` ve `/health/ready` endpoint'leri gerçek OpenAPI'de doğru path/auth/status ile var mı? | VERIFY |
| C134-08 | Cilt 1.9 permission matrix tüm endpoint'leri kapsıyor mu? | VERIFY |
| C134-09 | Her kritik workflow audit+business mutation'ı tek transaction'da yapıyor mu? | VERIFY |
| C134-10 | Idempotency endpoint scope ve DB uniqueness/response replay | VERIFY |
| C134-11 | Cilt 1.5 WF-01–WF-10 ile Cilt 1.19 registry tam eşleşiyor mu? | VERIFY |
| C134-12 | Runtime MySQL/SQLAlchemy/OpenAPI contract tests | NOT_RUNTIME_VERIFIED |

## 6. Gerekli testler (kabul kriterleri)

### Auth/health
- `expires_in == 900`.
- Refresh token yenilendiğinde önceki token tekrar kullanılamaz; reuse token ailesini iptal eder.
- Logout sonrasında refresh session kullanılamaz.
- Disabled user'ın authenticated isteği reddedilir.
- `GET /health/live` auth istemez, DB sorgusu yapmaz, canlı süreçte 200 verir.
- `GET /health/ready` auth istemez; DB/dependency unavailable iken 503 verir ve secret içermez.
- Web state-changing request CSRF token olmadan reddedilir.

### Expiry/waste/cost
- `requires_expiry_date=true` + `expiry_date=null` → validation error.
- `requires_expiry_date=false` + `expiry_date=null` → kabul.
- `OTHER` reason code açıklamasız → validation error.
- Çoklu kaynak lot, ayrı waste satırları oluşturur.
- BY_WEIGHT örneği: total cost €100, cuts 8 kg, byproduct 1 kg, waste 1 kg → maliyetler €80/€10/€10.
- BY_VALUE: waste cost 0; tüm cost value-bearing outputs'a dağıtılır; hiçbir value-bearing output yoksa tamamlanamaz.
- Tüm maliyet allocation'larında `outputs + waste == purchase_cost` exact decimal equality sağlanır.
- Ölçülen kütle `cuts + byproducts + waste` ile açıklanabilir variance/tolerance kuralına göre uzlaşır; sessiz kayıp kabul edilmez.

## 7. Migration gate

Cilt 1.31 toplu onayı migration izni değildir. Alembic dosyaları üretmeden veya DB'ye dokunmadan önce:
1. Cilt 1.2'deki tablo/alanları Cilt 1.16/1.22 crosswalk ile kontrol et.
2. Cilt 1.5 WF-01–WF-10'u Cilt 1.19 registry ile eşleştir.
3. Yukarıdaki VERIFY maddelerinin fiziksel şema/DTO/API/test karşılıklarını raporla.
4. Proje sahibine hangi tablo/alan/migration'ların gerektiğini özetle.
5. Migration üretmek için ayrı, açık onay al. Bu adımlar tamamlanmadan migration veya DB değişikliği yoktur.


## 8. Revizyon sonrası hızlı statik kontrol

Bu kontrol dosya metinlerini inceler; gerçek OpenAPI generator, ORM metadata veya DB testinin yerine geçmez.

| Kontrol | Sonuç |
|---|---|
| API auth açıklaması | Güncellendi: 15m access / 7d refresh |
| API örnek `expires_in` | Güncellendi: 900 |
| API health path başlıkları | Güncellendi: `/health/live`, `/health/ready` |
| DTO auth açıklaması ve checklist | Güncellendi |
| ERD normatif data rules | Eklendi |
| Cilt 1.23 karar durumları | Güncellendi |
| Eski auth/security/registry ifadeleri | Bazı tarihsel bölümlerde kalabilir; bu dosyanın Cilt 1.34 bölümü normatif override'dır |
| Gerçek ORM/OpenAPI/MySQL doğrulaması | Yapılmadı |
