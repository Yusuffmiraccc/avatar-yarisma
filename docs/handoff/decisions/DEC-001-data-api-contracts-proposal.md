# DEC-001 — Veri ve API Sözleşmesi Kararları

**Durum:** ONAYLANDI — 22 Ekim 2026'da proje sahibi 13 kararın tamamını kabul etti  
**Tarih:** 22 Ekim 2026  
**Bağlı belgeler:** Cilt 0, Cilt 1, ADR-001  
**Amaç:** Cilt 1'deki veri/API belirsizliklerini tek tek görünür kılmak ve implementasyondan önce tutarlı kararlar almak.

> **Bağlayıcı karar:** Ana teknoloji yığını daha önce onaylanmıştır. Proje sahibi bu belgedeki 13 kararın tamamını 22 Ekim 2026'da kabul etmiştir. Cilt 0, Cilt 1, sonraki ciltler ve tüm LLM görevleri bu kararlara uymalıdır. Değişiklik yalnızca gerekçeli yeni karar kaydıyla yapılabilir.

## Karar 1 — Dahili kimlikler ve iş kodları

**Öneri:** Her ana tabloda dahili `BIGINT` auto-increment primary key kullanılsın; kullanıcıların gördüğü iş kodları (`ET-2026-001`, `URT-2026-045`, `SUC-2026-045`) ayrı, benzersiz `VARCHAR` alanlarında saklansın.

**Gerekçe**
- MySQL foreign key ilişkileri ve sorgular kolay anlaşılır.
- Demo ve raporlarda iş kodları okunabilir kalır.
- İş kodunun değişmesi dahili ilişkileri bozmaz.
- Tek uygulama/veritabanı ölçeğinde UUID zorunluluğu yaratmaz.

**Etkisi:** Tüm MySQL tabloları, API kaynak kimlikleri ve Android Room entity ilişkileri.

**API kuralı:** Kaynak URI'lerinde dahili ID kullanılabilir; insan tarafından girilen lot kodu için ayrıca `lotCode` ile arama endpoint'i sağlanır.

## Karar 2 — Para, ağırlık ve API JSON gösterimi

**Öneri:**
- MySQL parasal değerleri `DECIMAL(19,4)`; ağırlık/miktar değerleri `DECIMAL(19,6)` olarak saklansın.
- API'de parasal ve hassas ondalık miktarlar **JSON string** olarak taşınsın; ör. `"1543.5000"`, `"18.160000"`.
- Kotlin'de para için `BigDecimal`, TypeScript'te hassas hesap gerektiren alanlar için decimal string korunup backend hesaplaması esas alınsın. İstemciler maliyet toplamlarını otoritatif olarak yeniden hesaplamasın.
- Her parasal kayıt `currency_code` taşısın; ilk demo için EUR kullanılsın. Çoklu para birimi dönüşümü ilk sürüm kapsamında olmasın.
- Yuvarlama kuralı iş kuralı ciltlerinde açıkça yazılsın; ara adımlarda erken yuvarlama yapılmasın.

**Gerekçe:** JSON sayıları birçok istemcide ikili kayan nokta olarak işlenebilir. Ondalıkları string olarak taşımak parasal hassasiyetin yanlışlıkla kaybolmasını azaltır.

**Etkisi:** Pydantic şemaları, SQLAlchemy modelleri, Android DTO'ları, TypeScript tipleri, maliyet raporları ve testler.

## Karar 3 — Tarih/saat ve tarih alanları

**Öneri:**
- Zaman anları API'de ISO 8601 ve UTC `Z` ile taşınsın; ör. `2026-10-22T12:30:00Z`.
- Veritabanında zaman anları UTC yaklaşımıyla saklansın.
- Son kullanma tarihi gibi yalnızca takvim günü ifade eden alanlar `YYYY-MM-DD` biçiminde date olarak saklansın; saat dilimine dönüştürülmesin.
- Arayüz yerel saat diliminde görüntüleme yapabilir; backend'e gönderilen zaman anı UTC standardına uymalıdır.

**Etkisi:** Tüm kayıt zamanları, son kullanma tarihi, raporlar ve test seed verisi.

## Karar 4 — Stok hareketleri ve güncel bakiye

**Öneri:** Stok hareketlerini denetlenebilir ledger olarak saklayalım ve performans/kolaylık için aynı transaction içinde güncellenen bir lot bakiyesi tablosu kullanalım.

Önerilen model:
- `stock_movements`: değişmez hareket geçmişi; miktar her zaman pozitif, yön `IN` veya `OUT` ayrı alanda.
- `inventory_balances`: `lot_id` başına fiziksel eldeki miktar ve gerekirse ayrılmış miktar.
- Kullanılabilir miktar, tanımlanan kurala göre `on_hand - reserved` olarak hesaplanır.
- Her stok hareketi ile bakiye güncellemesi aynı MySQL transaction'ında yapılır.
- Hata durumunda ikisi de rollback edilir.
- Normal akışta geçmiş hareketler düzenlenmez veya silinmez; hata düzeltmeleri ters/düzeltme hareketiyle yapılır.
- Blokaj stok miktarını fiziksel olarak azaltmaz. Bloke lotun satılabilir miktarı sıfır kabul edilir; lot blokajı ayrı kayıtta tutulur.

**Gerekçe:** Salt hareketlerden her ekran açılışında toplam hesaplamak basit olsa da rapor ve satış kontrolünde karmaşıklık yaratabilir. Bakiye tablosu performans sağlar; hareket ledger'ı denetim ve izlenebilirliği korur.

**Etkisi:** Satış, üretim, parçalama, sevkiyat, iade, fire, geri çağırma, raporlar ve eşzamanlılık testleri.

## Karar 5 — Stok hareketi işaret kuralı

**Öneri:** `stock_movements.quantity` sıfırdan büyük bir mutlak miktar olsun; `direction` yalnızca `IN` veya `OUT` değerlerinden birini alsın. Kaynak belge türü ve kaynak ID zorunlu olsun; mümkün olduğunda kaynak satır ID'si de saklansın.

**Gerekçe:** Pozitif ve negatif miktarları farklı modüllerin farklı biçimde yorumlamasını önler.

**Etkisi:** Tüm stok hareketi üreticileri ve stok raporları.

## Karar 6 — Lot köken ilişkisi

**Öneri:** Kaynak lotlar ve hedef lotlar arasındaki ilişki, `lot_genealogy_edges` benzeri ayrı bir tabloda çoktan çoğa olarak saklansın. Her kenar şu bilgileri taşısın:
- kaynak lot ID,
- hedef lot ID,
- süreç türü (`PRODUCTION`, `BUTCHERING`, `REWORK`),
- süreç ID,
- kaynak lotundan tüketilen miktar ve birim,
- hedef lotuna üretilen miktar ve birim,
- oluşturulma zamanı.

**Kural:** Aynı süreçte birden çok kaynak lot ve birden çok hedef lot desteklenir. Girdi ve çıktı miktarları farklı ürün/birimlere ait olabileceğinden birbiriyle aynı ölçüymüş gibi toplanmaz.

**Gerekçe:** İleri ve geriye izleme sorgularının güvenilir olması için miktarlı bağlantı gerekir. Yalnızca `parent_lot_id` yeterli değildir.

**Etkisi:** Üretim, parçalama, yeniden işleme, geri çağırma ve izlenebilirlik API'leri.

## Karar 7 — Satış, sevkiyat ve son tüketici satışı ayrımı

**Öneri:**
- `sales` ve `sale_lines`, POS/işletme satışlarını temsil etsin.
- `shipments` ve `shipment_lines`, işletmeden market veya müşteriye yapılan sevkiyatı temsil etsin.
- Bir sevkiyat, otomatik olarak son tüketici satış kaydı üretmesin.
- Her satış satırında ürün, lot, miktar, birim, birim satış fiyatı, para birimi ve satır toplamı saklansın.
- Her sevkiyat satırında ürün, lot, miktar, birim, müşteri ve sevkiyat tarihi bulunsun.
- Marketlerin son tüketici satışları ayrıca sisteme kaydedilmedikçe ikinci kademe dağıtım raporlanmış gibi gösterilmesin.

**Etkisi:** Satış, sevkiyat, izlenebilirlik ve geri çağırma raporları.

## Karar 8 — Kimlik doğrulama ve roller

**Öneri:** İlk sürümde backend tarafında JWT access token ve rol bazlı yetkilendirme kullanılsın. Önerilen başlangıç rolleri:
- `ADMIN`: kullanıcı/ayar yönetimi ve tüm operasyonlar.
- `OPERATOR`: üretim, parçalama, stok giriş/çıkış ve lot işlemleri.
- `SALES`: satış ve satış geçmişi.
- `TRACEABILITY_MANAGER`: izlenebilirlik ve geri çağırma başlatma/raporlama.
- `VIEWER`: yalnızca izin verilmiş okuma ve raporlama.

Bir kullanıcıya birden fazla rol verilip verilmeyeceği ve son yetki matrisi Cilt 0/Cilt 7'de netleştirilmelidir. API her yazma isteğinde yetki kontrolü yapmalıdır; yalnızca arayüzde buton gizlemek güvenlik kontrolü sayılmaz.

**Gerekçe:** En azından demo için işlemlerin kimin tarafından yapıldığını ve hassas işlemlerin sınırlarını göstermek gerekir.

**Etkisi:** Kullanıcı modeli, auth endpoint'leri, API bağımlılıkları, denetim alanları ve web paneli.

## Karar 9 — Silme, iptal ve denetim

**Öneri:**
- Üretim, stok, satış, sevkiyat ve geri çağırma gibi işlem kayıtları hard delete ile silinmesin.
- Yanlış veya iptal edilen işlemler durum geçişi ve gerekiyorsa ters/düzeltme stok hareketiyle ele alınsın.
- Önemli kayıtlarda `created_at`, `created_by`, `updated_at`, gerektiğinde `updated_by` alanları bulunsun.
- Geri çağırma ve lot blokajı geçmişi korunmalı; blokajın kaldırılması eski blokaj kaydını silmemeli.

**Etkisi:** Denetim izi, API silme/iptal davranışı, stok tutarlılığı ve geri çağırma.

## Karar 10 — Satış idempotency ve transaction

**Öneri:**
- `POST /api/v1/sales` her istek için `Idempotency-Key` başlığını zorunlu kılsın.
- Backend anahtar + kullanıcı/istemci kapsamını benzersiz tutup istek özeti ve ilk sonucu kaydetsin.
- Aynı anahtar ve aynı içerik tekrar gelirse önceki sonuç dönsün; aynı anahtar farklı içerikle gelirse `409 Conflict` dönsün.
- Satış kaydı, satırları, stok hareketleri, lot bakiyesi güncellemesi ve idempotency sonucu tek transaction içinde yazılsın.
- Satışta lot blokajı ve bakiye doğrulaması sunucu tarafında, eşzamanlı isteklere dayanıklı biçimde yapılsın.
- Backend yanıtı başarı olmadan Android satış tamamlandı durumu göstermesin.

**Etkisi:** Android, API, satış servis katmanı, stok modeli ve testler.

## Karar 11 — API hata sözleşmesi

**Öneri:** Bütün hatalar aşağıdaki ortak şekli kullansın:

```json
{
  "error": {
    "code": "LOT_BLOCKED",
    "message": "The selected lot is blocked and cannot be sold.",
    "details": {
      "lot_code": "SUC-2026-045"
    },
    "request_id": "server-generated-request-id"
  }
}
```

- `code` sabit makine-okunur değer olmalı.
- `message` kullanıcıya gösterilebilir, ancak istemci kararlarını yalnızca mesaja göre vermemeli.
- `details` opsiyonel, endpoint'e özgü yapılandırılmış alan taşımalı.
- `request_id` loglarla hatayı eşleştirmeye yardım etmeli.
- Başarısız iş kuralı kontrollerinde uygun 4xx; beklenmeyen sunucu hatalarında 5xx kullanılmalı. Kesin kod eşlemesi OpenAPI'de listelenmeli.

**Etkisi:** FastAPI exception handler'ları, Android/web hata gösterimi ve testler.

## Karar 12 — API sürümleme, sayfalama ve liste filtreleri

**Öneri:**
- Tüm API yolları `/api/v1` ile başlasın.
- Liste endpoint'leri tutarlı `page`, `pageSize`, `sort`, filtre parametreleri kullansın.
- Yanıtlar `{ "items": [...], "page": 1, "pageSize": 20, "total": 123 }` benzeri ortak yapıda olsun.
- `pageSize` için makul bir üst sınır tanımlansın.
- API sözleşmesi OpenAPI ile yayımlansın; istemci DTO'ları bu sözleşmeyle eşleştirilsin.

**Etkisi:** Tüm liste endpoint'leri, web tabloları, Android listeleri ve entegrasyon testleri.

## Karar 13 — Önerilen veri adlandırma standardı

**Öneri:**
- MySQL tabloları ve sütunları `snake_case`, çoğunlukla çoğul tablo adı kullansın: `products`, `stock_movements`.
- API JSON alanları da `snake_case` kullansın; Android Kotlin DTO'ları ve TypeScript modelleri bu isimleri açıkça eşlesin.
- API endpoint path'leri küçük harf ve kebab-case olsun; ör. `/production-orders`.
- Enum değerleri büyük harfli sabit dizeler olsun; ör. `ACTIVE`, `BLOCKED`, `COMPLETED`.
- Dahili ID'ler JSON'da sayısal ID olarak verilsin; iş kodları ayrı alan olsun.

**Etkisi:** Backend, Android, web, OpenAPI ve seed data. Bu karar, API adlandırma biçiminin tüm modüllerde tek kalmasını sağlar.

## Onaylanmış kararların özeti

| # | Karar alanı | Önerilen varsayılan |
|---:|---|---|
| 1 | Dahili kimlik | BIGINT ID + ayrı benzersiz iş kodu |
| 2 | Para/miktar | MySQL DECIMAL; API'de ondalık string |
| 3 | Tarih/saat | ISO 8601 UTC; takvim tarihleri `YYYY-MM-DD` |
| 4 | Stok modeli | Değişmez ledger + transaction ile güncellenen lot bakiyesi |
| 5 | Hareket miktarı | Pozitif miktar + ayrı IN/OUT yönü |
| 6 | Lot kökeni | Miktarlı, çoktan çoğa genealogy edges |
| 7 | Satış/sevkiyat | Ayrı iş kavramları ve tablolar |
| 8 | Yetki | JWT + rol bazlı kontrol |
| 9 | Kayıt düzeltme | Hard delete yok; iptal/düzeltme hareketleri |
| 10 | Idempotency | Satışta zorunlu `Idempotency-Key` |
| 11 | Hata sözleşmesi | Ortak `error.code/message/details/request_id` |
| 12 | Liste API'si | Ortak sayfalama/filtreleme |
| 13 | Adlandırma | DB snake_case; API JSON snake_case; enum UPPER_SNAKE_CASE |

## Uygulama adımları

1. Bu kararlar Cilt 0 ve Cilt 1'e bağlayıcı olarak işlendi.
2. Cilt 1 için ERD ve tablo başına kesin alan/constraint listesi hazırlanacak.
3. API endpoint'leri için OpenAPI uyumlu request/response örnekleri hazırlanacak.
4. Seed data ve kabul testleri PDF'deki zorunlu senaryolarla eşleştirilecek.
5. Kararlar Cilt 2–8 ile çelişki kontrolünden geçirilecek.


## Revizyon 1.11 — Hata zarfı alan adı

Karar 11'deki örnek JSON'un `requestId` alanı, Karar 13'teki `snake_case` standardıyla uyumlu olacak şekilde `request_id` olarak normalize edilmiştir. Hata zarfının kanonik alanları `error.code`, `error.message`, isteğe bağlı `error.details` ve kök seviyede `request_id` şeklindedir. Bu dokümantasyon düzeltmesi 13 onaylı kararın anlamını değiştirmez.


## Karar 14 — Satış/sevkiyat stok çıkışı sahipliği (WF-03)

**Durum: ONAYLANDI — proje sahibi tarafından açıkça onaylandı.**

- `dispatch` fiziksel stok çıkışının tek sahibidir ve her sevkiyat satırı için tek `OUT/SHIPMENT` hareketi ile bakiye azaltımını aynı transaction içinde üretir.
- `sales` ve `sale_lines` ticari kaydı temsil eder; stok `OUT` hareketi oluşturmaz ve `inventory_balances` değerini azaltmaz.
- Fiziksel stok çıkışı gereken akış, dispatch kaydıyla ilişkilendirilmelidir. Aynı fiziksel miktar için satış ve dispatch üzerinden iki ayrı `OUT` hareketi kesinlikle oluşturulamaz.
- Dispatch idempotent olmalıdır; aynı sevkiyatın tekrar dispatch edilmesi ikinci stok hareketi yaratmaz. Transaction rollback olursa sevkiyat durumu, stok hareketi, bakiye, audit ve idempotency sonucu birlikte rollback edilir.
- Bu karar Cilt 1.2–1.9, ilgili DTO/OpenAPI sözleşmeleri, testler ve sonraki ciltler için normatiftir. Değişiklik ancak gerekçeli yeni karar kaydıyla yapılabilir.


## Ek karar kaydı: SEC/API/DATA karar paketi (22 Ekim 2026)

Proje sahibi Cilt 1.31'deki SEC-01–SEC-09, API-01–API-03 ve DATA-01–DATA-06 önerilerini topluca onaylamıştır. Bu ek karar paketi Cilt 1 için bağlayıcıdır; Cilt 1.31 ve Cilt 1.32 karar ayrıntılarını ve doğrulama durumunu içerir.

**Kapsam dışı açık izin:** Bu onay Alembic migration üretme, şema uygulama veya veritabanı oluşturma/değiştirme yetkisi vermez. Migration öncesinde Cilt 1.2 ERD/tablo/alanları ile Cilt 1.5 WF-01–WF-10 iş akışları ayrıca çapraz kontrol edilmeli ve proje sahibinden ayrı, açık izin alınmalıdır.
