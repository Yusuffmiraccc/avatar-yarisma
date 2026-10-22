# Cilt 1.13 — Revizyon Sonrası Çapraz Kontrol ve Blokaj Raporu

**Tarih:** 22 Ekim 2026  
**Durum:** Belge içi kontroller yapıldı; kritik sözleşme uyuşmazlıkları bulundu.  
**Migration durumu:** Alembic dosyası oluşturulmadı. MySQL kurulmadı/değiştirilmedi.  
**Önemli:** Bu rapor metin ve çapraz referans incelemesidir; gerçek OpenAPI üretimi, ORM metadata diff'i veya otomatik DB şema diff'i değildir.

## 1. Yönetici özeti

Cilt 1.12, birçok kuralı ek açıklamalarla belgelere taşımış; ancak eski normatif tabloların tümü yeni kurallara göre değiştirilmediği için dokümanlar henüz tek bir uygulama sözleşmesi oluşturmuyor. Özellikle API izin matrisi ile güvenlik ciltleri, satış/sevkiyat stok etkisi, token/health davranışı ve durum enumları arasında kalan çelişkiler çözülmeden migration üretmek güvenli değildir.

**Sonuç: Migration kapısı KAPALI.** Önce aşağıdaki P0 maddeleri ana tabloların içinde düzeltilmeli; yalnızca sona eklenen notlarla yetinilmemelidir.

## 2. P0 — Kodlama/migration öncesi kapatılması gerekenler

### P0-01 — Endpoint rol matrisi eski izinleri hâlâ içeriyor
- **Kanıt:** Cilt 1.3 `POST /shipments` ve `POST /shipments/{id}/dispatch` için `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER` gösteriyor.
- **Kanonik öneri:** Cilt 1.9 ve Cilt 1.12 günlüğü `ADMIN`, `SALES` öneriyor.
- **Gerekli işlem:** Cilt 1.3 ana endpoint satırlarını ve üst seviye rol matrisini `ADMIN`/`SALES` ile güncelle; Cilt 1.8 ana matrisiyle aynılaştır. Sadece ek not bırakma.

### P0-02 — Genel stok düzeltme izni çelişkili
- **Kanıt:** Cilt 1.3 üst seviye matrisi `ADMIN`/`OPERATOR`; Cilt 1.9/Cilt 1.12 `ADMIN`-only öneriyor.
- **Kanonik öneri:** `inventory:adjust` yalnızca `ADMIN`; normal üretim/alış/dispatch işlemleri kendi izinleriyle stok hareketi üretebilir.
- **Gerekli işlem:** Cilt 1.3, 1.8, 1.9 ve 1.4 negatif testlerini tekleştir.

### P0-03 — Satış ve dispatch ikisi de OUT oluşturuyor
- **Kanıt:** Cilt 1.2 satış bölümünde `OUT/SALE` hareketi; sevkiyat bölümünde `OUT/SHIPMENT` hareketi tanımlı. Cilt 1.3 satış ve dispatch transaction açıklamaları da stok düşümünü ayrı ayrı tarif ediyor. Cilt 1.5 ise dispatch'in tek sahip olmasını yalnızca önerilen varsayılan olarak yazıyor.
- **Önerilen tek davranış:** Fiziksel market teslimini temsil eden `dispatch` tek `OUT/SHIPMENT` hareketini oluşturur. Satış kaydı ticari kayıttır ve aynı miktar için ikinci `OUT` üretmez. Demo verisinde satış ile sevkiyat bağının nasıl kurulacağı ERD/API'de açıkça tanımlanmalı.
- **Gerekli işlem:** Bu kuralı Cilt 1.2/1.3/1.4/1.5/1.6/1.7'nin normatif bölümlerine uygula; sale-line'ın stoktan düşen kaynak olduğu varsayımını kaldır.
- **Karar notu:** Bu seçim Cilt 1.11'de önerilen varsayılan olarak belirtilmiş olsa da Cilt 1.10 CC-03'te kullanıcı adına kesin seçim yapılmamıştı. Kullanıcıya son çapraz kontrolde açıkça teyit ettirilmeli.

### P0-04 — Token ve logout sözleşmesi aynı değil
- **Kanıt:** Cilt 1.3/1.4 ek notları access token 30 dakika, refresh token yok diyor; Cilt 1.8 ana bölümü hâlâ süre ve invalidation kararını açık bırakıyor. Cilt 1.9 logout için client-only davranışı öneriyor.
- **Kanonik öneri:** Access token 30 dakika; MVP'de refresh token yok; logout istemcide token'ı siler ve sunucu tarafı iptal iddiası taşımaz. Backend her istekte kullanıcı aktifliğini kontrol edecekse bu ayrıca sözleşmeye yazılmalı.
- **Gerekli işlem:** Cilt 1.8 ana metnini güncelle; logout endpoint'inin mevcut olup olmayacağını, yanıtını ve aktif token davranışını Cilt 1.3/1.4'te tekleştir.

### P0-05 — Health endpoint tasarımı uygulanabilir düzeyde kesin değil
- **Kanıt:** Cilt 1.3'te endpoint erişim biçimi açık değil; Cilt 1.8/1.9 minimal liveness ile internal/authorized detailed health ayrımını öneriyor.
- **Kanonik öneri:** `GET /api/v1/health/live` minimal liveness; `GET /api/v1/health/ready` dependency readiness, dış kullanıcıya hassas DB/host ayrıntısı döndürmez ve internal/authorized erişimle sınırlandırılır. Bu endpoint adları öneridir; Cilt 1.3'te sabitlenmeden uygulama koduna geçilmemeli.
- **Gerekli işlem:** Endpoint isimleri, erişim, response schema ve testler tek tabloda tanımlansın.

### P0-06 — Fire ve output modelinde nullable kuralı, alan modellemesiyle eşleştirilmeli
- **Kanıt:** Cilt 1.2 ek notu yalnızca fire ölçüm satırında `product_id`/`lot_id` nullable olabilir diyor; ana `production_outputs`/`butchering_outputs` tablolarında kolon NULL kuralı ve satır türü ayrımı ayrı ayrı doğrulanmalı.
- **Gerekli işlem:** Her tablo için alan/NULL envanteri çıkar; eğer mevcut tablolar bu ayrımı yapamıyorsa `output_kind`/ayrı fire ölçüm modeli gibi seçenekleri ERD'de öner ve migration öncesi onay kapısına taşı. Varsayımsal kolonları sessizce kesinleştirme.

## 3. P1 — API/DTO/test eşlemesi gerekenler

### P1-01 — Error-code registry tamamlanmalı
Cilt 1.3'te genel `CONFLICT` ve özel `IDEMPOTENCY_KEY_REUSED`, `INSUFFICIENT_STOCK`, `LOT_BLOCKED`, `INVALID_STATE_TRANSITION` birlikte bulunuyor. Cilt 1.4 testleri bu kodların tüm örneklerde registry'den geldiğini doğrulamalı. Her özel durumun genel `CONFLICT` ile mi yoksa özel kodla mı yanıtlanacağı endpoint tablosunda belirtilmeli; ikisi rastgele kullanılmamalı.

### P1-02 — Kritik POST idempotency tablosu eksik
Satışta `Idempotency-Key` zorunlu. Diğer stok/maliyet etkili komutlar için ya key + aynı gövde replay standardı ya da tamamlanmış durumdan deterministik `409 INVALID_STATE_TRANSITION` standardı her endpoint için açıkça seçilmeli. Cilt 1.4'te hâlâ “endpoint bazında sabitlenmelidir” diyen eski metinler var.

### P1-03 — Enum ve state sözlüğü ana belgelerde tek değil
Cilt 1.5'te sevkiyat için `DRAFT → PREPARED → DISPATCHED → DELIVERED`, başka bölümlerde `SHIPPED` kullanılıyor. Tek MVP enum'u seçilmeli. Teslim kanıtı tutulmayacaksa `DELIVERED` kullanılmamalı; `DISPATCHED`/`SHIPPED` arasında tek ad seçilmeli ve API/DB/testler aynı olmalı.

### P1-04 — Recall release/unblock veri ve yetki sözleşmesi tamamlanmalı
Cilt 1.2 `lot_blocks.unblocked_at/unblocked_by` alanlarını tanımlıyor; Cilt 1.9 ayrı `lots:unblock`/eşdeğer permission öneriyor. Cilt 1.3'te release endpoint'i, payload, rol ve idempotency davranışı tam normatif olarak tanımlanmalı. `RESOLVED` durumunun otomatik unblock yapmadığı korunmalı.

### P1-05 — Nullable alan envanteri ve DTO eşlemesi yok/eksik
Cilt 1.2'nin tüm tablolarındaki nullable alanlar için anlam (bilinmiyor/uygulanamaz/opsiyonel) ve API DTO karşılığı tek tabloya alınmalı. Alanları yalnızca birkaç örnek üzerinden kontrol etmek yeterli değil.

### P1-06 — Başarılı yanıt request ID standardı
Hata zarfında `request_id` kararlaştırılmıştır. Başarılı yanıtlar için bunun body'de mi header'da mı olacağı Cilt 1.4'te hâlâ açık soru olarak görünüyor. Hata gövdesindeki sözleşme korunarak success response için tek yaklaşım seçilmeli.

### P1-07 — Web auth taşıma/CSRF/CORS
HttpOnly/Secure/SameSite cookie kullanımı ile Bearer token yaklaşımı bir arada belirsiz bırakılmamalı. Web ve Android'in token taşıma biçimleri ayrılmalı; cookie seçilirse CSRF/CORS kuralları ve testleri tanımlanmalı. Bu karar koddan önce kesinleşmeli.

## 4. P2 — Şema ayrıntısı ve demo doğrulaması

- Tüm FK'ler, UNIQUE constraint'ler, CHECK'ler ve indeksler ERD alan envanteriyle tek tek eşleştirilmeli.
- `stock_movements.quantity > 0` ve yönün `IN/OUT` ile belirtilmesi kuralı DB/API/testte aynı olmalı.
- Lot bakiyesi ile immutable stock movement ledger'ın aynı transaction'da güncellenmesi test edilmeli.
- Market A/B/C için 30 + 25 + 30 = 85 paket senaryosu, stok düşümünün yalnızca bir kez oluştuğunu assert etmeli.
- Kaynak yarışma PDF'sindeki kuzu örneğinde 25 kg × €11.50 = €287.50 iken PDF'de €351 toplamı yazılması ve belirtilen kesim ağırlıklarının 22 kg etmesi ayrı veri doğrulama notu olarak korunmalı; sebep uydurulmamalı.

## 5. Normatif sözlükler — revizyonun teslim kriteri

Bir sonraki revizyon paketi şu ekleri içermelidir:
1. **Permission registry:** her endpoint → permission key → rol(ler) → negatif test.
2. **Enum registry:** entity/state → geçerli değerler → geçişler → API/DB eşlemesi.
3. **Error registry:** HTTP status → `error.code` → koşul → endpoint örneği.
4. **Nullable registry:** tablo/kolon → NULL? → gerekçe → DTO davranışı.
5. **Side-effect registry:** her command → ledger IN/OUT → balance → cost → genealogy → audit → idempotency/retry.
6. **Schema-to-DTO matrix:** her DB alanı ↔ DTO alanı ↔ JSON tipi ↔ nullable semantics.

## 6. Migration öncesi kapı

Migration üretimine geçmeden önce:
- [ ] P0-01–P0-06 normatif ana bölümlerde kapatıldı.
- [ ] P1-01–P1-07 karara bağlandı veya açıkça kapsam dışı/TBD gerekçesiyle ayrıldı.
- [ ] Registry'ler oluşturuldu ve Cilt 1.2–1.9 ile karşılaştırıldı.
- [ ] Alembic metadata diff'i / gerçek şema diff'i migration dosyası yazılmadan önce yapılabilecek ölçüde şema sözleşmesiyle eşleştirildi.
- [ ] Kullanıcıya tablo/kolon/constraint/DTO/endpoint/permission/enum/error-code özeti sunuldu.
- [ ] Migration dosyası üretimi için ayrıca açık onay alındı.

**Bu raporun sonucu:** Belgeler üzerinde ek bir normatif revizyon turu gerekiyor. Şu anda migration dosyası üretmeye hazır değiliz.

### Tarihsel kayıt uyarısı (Cilt 1.34)
Bu rapordaki eski token/health/BY_VALUE ifadeleri tarihsel bulgudur; güncel normatif sözleşme olarak kullanılmamalıdır. Cilt 1.31/1.32 onayları ve Cilt 1.34 revizyonları önceliklidir.
