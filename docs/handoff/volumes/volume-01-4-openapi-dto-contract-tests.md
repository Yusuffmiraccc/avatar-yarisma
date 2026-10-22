# Cilt 1.4 — OpenAPI Örnekleri, Ortak DTO'lar ve Contract Test Planı


> **Normatif güncelleme — 22 Ekim 2026 (Cilt 1.32):** Bu belgedeki daha eski ve çelişen taslak ifadeler için `volume-01-32-approved-decisions-and-cross-check.md` ile Cilt 1.31'in onay kaydı önceliklidir. Bu not doküman sözleşmesini günceller; migration veya veritabanı değişikliği izni değildir.

**Durum:** Uygulama öncesi sözleşme ve doğrulama planı  
**Tarih:** 22 Ekim 2026  
**Bağlı belgeler:** Cilt 0, Cilt 1, Cilt 1.2, Cilt 1.3, DEC-001, ADR-001  
**Amaç:** Backend, Android ve web panelinin aynı API şekillerini kullanmasını sağlamak; kritik akışları otomatik testlerle doğrulamak.

> **Öncelik kuralı:** Cilt 1.2 veri şeması ve Cilt 1.3 endpoint sözleşmesi normatiftir. Bu cilt yeni iş kuralı icat etmez; örnekler, istemci eşlemesi ve test yaklaşımı sağlar. Çelişki bulunursa sessizce tahmin yürütülmez; ilgili sözleşmeler birlikte güncellenir.

## 1. Bu cildin çıktıları

1. API'de kullanılan ortak JSON kalıpları ve tip kuralları.
2. Kritik istek/yanıt örnekleri.
3. Python, TypeScript ve Kotlin tarafındaki DTO eşleme kuralları.
4. OpenAPI üretimi ve sözleşme kontrolü için süreç.
5. Birim, entegrasyon ve uçtan uca test senaryoları.
6. Cilt 1.2 ile Cilt 1.3 arasındaki uygulama öncesi kontrol noktaları.

## 2. Ortak JSON sözleşmesi

### 2.1 İsimlendirme ve tipler

| Kavram | API gösterimi | Kural |
|---|---|---|
| İç kimlik | JSON integer | Pozitif `BIGINT` kimliği; istemciler 64-bit güvenli tür kullanır |
| İş kodu | JSON string | İnsan tarafından okunur, ör. `ET-2026-001` |
| Para | JSON string | `DECIMAL(19,4)`; ör. `"18.1600"` |
| Ağırlık/miktar | JSON string | `DECIMAL(19,6)`; ör. `"85.000000"` |
| Para birimi | JSON string | ISO benzeri üç harfli kod; demo `EUR` |
| Tarih | JSON string | `YYYY-MM-DD` |
| Zaman anı | JSON string | UTC ISO 8601, `Z` son eki |
| Durum/enum | JSON string | `UPPER_SNAKE_CASE` |
| Eksik opsiyonel alan | Alan atlanabilir veya sözleşme `null` diyorsa `null` | Her alan için tek davranış OpenAPI'de tanımlanmalı |
| Boolean | JSON boolean | String olarak gönderilmez |

Para ve miktarların string olmasının nedeni kayan nokta yuvarlama hatalarını önlemektir. Backend bu alanları `Decimal` olarak parse eder; `float` ile iş hesabı yapmaz. Android tarafında `BigDecimal`, web tarafında decimal string korunur. UI'da sayısal gösterim için parse edilse bile API'ye geri gönderirken kesin decimal gösterimi korunmalıdır.

### 2.2 Başarılı liste yanıtı

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

- `page` ve `page_size` pozitif integer olmalıdır.
- `page_size` en fazla 100 olabilir.
- `total`, uygulanan filtrelerden sonraki toplam kayıttır.
- İstemci `items` boş olduğunda bunu hata olarak yorumlamaz.

### 2.3 Hata zarfı

```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "The requested quantity exceeds available stock.",
    "details": {
      "lot_code": "SUC-2026-045",
      "available_quantity": "12.000000",
      "requested_quantity": "15.000000"
    }
  },
  "request_id": "req-demo-0001"
}
```

`details` boş veya yok olabilir. `request_id` hata yanıtında ve mümkünse başarılı yanıtların response header'ında izleme amacıyla taşınır. İstemci kullanıcıya `message` gösterebilir; hata yönetimini `code` üzerinden yapmalıdır. İç hata ayrıntıları, SQL, stack trace, parola veya token yanıt içine konulmaz.

## 3. Kritik API örnekleri

Aşağıdaki örneklerde ID'ler temsilidir; seed verisinin gerçek ID'leriyle birebir aynı olmak zorunda değildir.

### 3.1 Oturum açma

`POST /api/v1/auth/login`

```json
{
  "email": "operator@example.test",
  "password": "demo-password"
}
```

Başarılı yanıtın temel şekli:

```json
{
  "access_token": "example-token-not-for-production",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": 10,
    "email": "operator@example.test",
    "display_name": "Demo Operator",
    "roles": ["OPERATOR"],
    "is_active": true
  }
}
```

Parola asla düz metin saklanmaz veya loglanmaz. Onaylı sözleşme: access token 15 dakika (`expires_in: 900`), refresh token 7 gün, refresh rotation; logout sunucudaki refresh session'ını iptal eder ve refresh reuse token ailesini iptal eder. Android tokenı plaintext DataStore'a yazılmaz; Android Keystore ile korunan şifreli depoda tutulur. Web için HttpOnly cookie ve CSRF token gerekir.

### 3.2 Lot kabulü

`POST /api/v1/inventory/receipts`

```json
{
  "product_id": 100,
  "lot_code": "ET-2026-001",
  "supplier_id": 20,
  "quantity": "100.000000",
  "unit_code": "KG",
  "received_at": "2026-10-22T10:00:00Z",
  "expiry_date": "2026-11-10"
}
```

Beklenen davranış:

- Lot kodu benzersiz olmalıdır.
- Miktar sıfırdan büyük olmalıdır.
- Lot, tedarikçi, stok bakiyesi, `IN` hareketi ve audit kaydı tutarlı biçimde oluşturulmalıdır.
- Tekrar gönderme davranışı bu endpoint için ayrıca idempotency sözleşmesinde belirlenmelidir; istemci timeout aldı diye ikinci bir kabul kaydı yaratmamalıdır.
- Süre/son kullanma tarihi bilinmiyorsa alanın nullable olup olmadığı OpenAPI ve DB şemasında aynı olmalıdır.

### 3.3 Satış — idempotency anahtarı zorunlu

`POST /api/v1/sales`

Header:

```http
Idempotency-Key: sale-device-01-000045
Authorization: Bearer <access_token>
Content-Type: application/json
```

Gövde örneği:

```json
{
  "currency_code": "EUR",
  "lines": [
    {
      "product_id": 300,
      "lot_id": 900,
      "quantity": "2.000000",
      "unit_code": "PACK",
      "unit_price": "5.5000"
    }
  ]
}
```

Beklenen kurallar:

1. `Idempotency-Key` eksikse istek reddedilir.
2. Aynı kapsam + aynı anahtar + aynı normalize edilmiş istek gövdesi için ilk sonucun status/body'si yeniden döndürülür; yeni satış veya yeni stok hareketi oluşturulmaz.
3. Aynı kapsam + aynı anahtar + farklı gövde için `409 IDEMPOTENCY_KEY_REUSED` döner.
4. Satış, satış satırları, stok `OUT` hareketleri, lot bakiyesi, idempotency sonucu ve audit kaydı tek DB transaction'ında tutarlı olmalıdır.
5. Lot blokajlıysa satış reddedilir (`409 LOT_BLOCKED`). Stok yetersizse `409 INSUFFICIENT_STOCK` döner.
6. Satış satırında kullanılan lot zorunludur; satılan miktarın hangi lota ait olduğu kaybolamaz.

### 3.4 Üretim tamamlama

`POST /api/v1/production-orders/{order_id}/complete`

Bu komutun istek gövdesi gerekiyorsa (ör. tamamlanma notu), OpenAPI şemasında açıkça belirtilir; boş gövde kabul ediliyorsa bu da açıkça belirtilir. Tamamlama sırasında backend şunları doğrular:

- Emir geçerli bir durumdadır ve daha önce tamamlanmamıştır.
- Girdi tüketimleri kayıtlı ve miktarları kullanılabilir stokla uyumludur.
- Dış hizmet maliyetleri, varsa, emirle ilişkilidir.
- Üretilen miktar ve çıktı lotları kayıtlıdır.
- Gerçek birim maliyet, kayıtlı gerçek girdiler ve hizmet maliyetleri üzerinden hesaplanır; istemcinin gönderdiği bir maliyet değeri tek doğruluk kaynağı olamaz.
- Stok hareketleri, bakiye, lot genealogy, maliyet snapshot'ları, durum değişimi ve audit tek transaction'da yazılır.
- Aynı tamamlama komutu tekrar gelirse ikinci kez stok tüketimi/üretimi yapmaz. Tekrarlı komut için ya idempotency key ya da `INVALID_STATE_TRANSITION` ile güvenli ret standardı OpenAPI'de sabitlenir.

### 3.5 Parçalama çıktıları ve fire

`POST /api/v1/butchering-orders/{order_id}/outputs`

Kullanılabilir kesim örneği:

```json
{
  "outputs": [
    {
      "product_id": 401,
      "lot_code": "KABURGA-2026-001",
      "output_type": "CUT",
      "actual_weight": "8.500000",
      "unit_code": "KG",
      "allocation_weight": "8.500000"
    }
  ]
}
```

**Önceki belirsizlik Cilt 1.17 kararıyla çözüldü:** Fire ayrı `butchering_waste_records` tablosunda ve ayrı DTO ile tutulur. `butchering_outputs` yalnızca stokta izlenen `CUT`/`BYPRODUCT` içerir; `product_id` ve `lot_id` zorunludur. Aşağıdaki eski seçenek açıklaması artık tarihsel bağlamdır; normatif değildir.

- **Onaylanan:** `WASTE` ayrı tabloda tutulur; fire için ürün/çıktı lotu oluşturulmaz. Bu kural Cilt 1.2, 1.3 ve 1.4 için bağlayıcıdır.

Bu karar Cilt 1.2 ve Cilt 1.3'te aynı anda güncellenmeden şema/migration yazılmamalıdır.

Parçalama tamamlanırken:

- Girdi ağırlığı, çıktı ağırlıkları ve fark raporlanır.
- Sistem eksik ağırlığın nedenini tahmin ederek kayıt üretmez.
- Dağıtılan maliyetlerin toplamı, yuvarlama politikası uygulandıktan sonra girdi toplam maliyetine eşit olmalıdır.
- Kullanılabilir kesimler ve izlenen yan ürünler için lot genealogy bağlantısı yazılır.
- Fire kaydı stokta satılabilir miktar yaratmaz.

### 3.6 Recall başlatma ve etkinleştirme

Recall iki adımda yürür:

1. `POST /api/v1/recalls` — taslak recall ve başlangıç lotu/lotları oluşturur.
2. `POST /api/v1/recalls/{recall_id}/activate` — etkilenen alt lotları bulur, recall kapsamını kaydeder ve aktif blokajları uygular.

Etkinleştirme başarılı sayılmadan önce aynı transaction sınırları içinde veya güvenli, tekrar çalıştırılabilir bir orchestration yaklaşımıyla aşağıdakiler tutarlı olmalıdır:

- Başlangıç lotu ve kayıtlı genealogy üzerinden bulunan etkilenmiş lotlar.
- Lot blokajları.
- Mevcut stok miktarları.
- Kaydedilmiş satış/sevkiyatlar ve müşteriye/markete göre etkilenmiş miktarlar.
- Audit olayı ve recall durum değişimi.

Bir recall aktivasyonu kısmen başarısız kalıp lotları satılabilir durumda bırakmamalıdır. Aktivasyon tekrarı yeni müşteri etki satırları veya yinelenen blokajlar oluşturmamalıdır. İlgili lot için satış ve sevkiyat aynı anda başlatılırsa backend eşzamanlılık kontrolü yapmalıdır.

### 3.7 İleri/geriye izlenebilirlik

Örnek başlangıç lotu: `ET-2026-001`.

- Geriye izleme, lotun hangi girdilerden/tedarikçiden geldiğini ve hangi üretim/parçalama emirlerine bağlandığını gösterir.
- İleri izleme, lotun hangi hedef lotlara dönüştüğünü, ardından hangi satış/sevkiyatlarda yer aldığını gösterir.
- Miktarlı genealogy bağlantıları, aynı kaynak lotun birden çok hedef lota ve birden çok kaynağın tek hedef lota bağlanmasını destekler.
- Sonraki dağıtıcı veya marketin tüketiciye yaptığı satış, ayrıca kaydedilmedikçe sistem tarafından varsayılmaz.
- Traceability yanıtları, bulunmayan ikinci kademe veriyi açıkça `not_recorded`/uygun bir durumla ayırt etmelidir; boş listeyi “hiç dağıtılmadı” şeklinde yorumlatmamalıdır.

## 4. DTO sözleşmesi: üç istemcide eşleme

### 4.1 Backend (Python / Pydantic)

- Dış JSON alan adları `snake_case` kalır.
- Pydantic modelleri alanları açıkça tanımlar; kritik endpoint'lerde kontrolsüz `extra` alanlar kabul edilmez.
- Para/miktar girişleri `Decimal` olarak doğrulanır; API response serialization decimal değerleri string yapar.
- DB `BIGINT` kimlikleri Python `int` olabilir; API sözleşmesinde JSON integer olarak döner.
- Tarih `date`, zaman UTC-aware `datetime` olarak işlenir.
- İş kuralları router içinde dağınık kalmaz; service katmanında transaction ile uygulanır.

Örnek iskelet (uygulama örneğidir; bütün DTO'ların tam kodu değildir):

```python
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class SaleLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int
    lot_id: int
    quantity: Decimal = Field(gt=0)
    unit_code: str
    unit_price: Decimal = Field(ge=0)
```

JSON'dan gelen `quantity` ve `unit_price` alanlarının sözleşmesel tipi string olarak tanımlanacaksa Pydantic'in decimal parse davranışı test edilmelidir. Response modellerinde `Decimal` değerlerin string olarak serialize edildiği açıkça garanti edilmeli ve test edilmelidir.

### 4.2 Web (TypeScript)

- JSON'daki para ve miktarlar `string` olarak modellenir; bunları `number` türüne dönüştürüp API'ye geri yollamayın.
- ID'ler API'de JSON integer olsa da `BIGINT` sınırları nedeniyle istemci kullanımı tek standarda bağlanmalıdır. Tarayıcı güvenli integer sınırını aşma olasılığı varsa ID'leri API'de string yapmaya geçiş ayrıca kararlaştırılmalıdır; ilk sözleşme JSON integer'dır.
- DTO'lar API alanlarını aynen yansıtır; UI view model'leri ayrı olabilir.
- OpenAPI'den TypeScript tip üretimi tercih edilir veya elle yazılan DTO'lar contract testleriyle doğrulanır.

```ts
export type DecimalString = string;

export interface InventoryBalanceDto {
  lot_id: number;
  lot_code: string;
  product_id: number;
  product_code: string;
  on_hand_quantity: DecimalString;
  reserved_quantity: DecimalString;
  available_quantity: DecimalString;
  unit_code: string;
  is_blocked: boolean;
}
```

### 4.3 Android (Kotlin)

- Retrofit DTO alanları JSON `snake_case` ile eşleşir; seçilen JSON adapter'ı ve naming strategy test edilir.
- Decimal string alanları ilk aşamada `String` olarak taşınabilir; iş hesabı gerekiyorsa `BigDecimal` kullanılır.
- Tarihler için tek bir ISO 8601 parser/serializer standardı kullanılır.
- UI modeli ile API DTO'su birbirine karıştırılmaz; dönüşüm repository/data katmanında yapılır.
- API hataları HTTP kodu + `error.code` üzerinden ortak bir sealed/result modeliyle ele alınır.

```kotlin
data class InventoryBalanceDto(
    val lot_id: Long,
    val lot_code: String,
    val product_id: Long,
    val product_code: String,
    val on_hand_quantity: String,
    val reserved_quantity: String,
    val available_quantity: String,
    val unit_code: String,
    val is_blocked: Boolean
)
```

Kotlin örneğinde alan isimlerinin aynen kullanılabilmesi seçilen serializer ayarına bağlıdır. Projede `@SerialName` veya Moshi/Gson eşlemesi kullanılacaksa tek yaklaşım belirlenmeli ve test edilmelidir.

## 5. OpenAPI üretimi ve sürümleme

FastAPI uygulaması OpenAPI şemasını otomatik üretir. Üretilen şema, uygulamanın gerçek davranışına eşit olmalıdır; doküman ayrı elle yazılıp koddan kopmamalıdır.

Önerilen kalite kapıları:

1. Her endpoint'in request/response modeli ve HTTP status kodu açıkça tanımlıdır.
2. Her enum alanının izin verilen değerleri OpenAPI'de görünürdür.
3. `Decimal` alanları OpenAPI'de string formatında görünür; `number` olarak çıkarsa serializer/şema tanımı düzeltilir.
4. Nullable alanlar DB, Pydantic ve OpenAPI'de aynı kararı izler.
5. Hata yanıtları ortak zarfı kullanır; FastAPI varsayılan doğrulama yanıtı doğrudan dışarı sızmaz.
6. CI, OpenAPI şemasını üretip sürüm kontrolündeki beklenen şemayla farkları kontrol eder.
7. Geriye uyumsuz değişiklikler (alan silme/yeniden adlandırma, zorunlu alan ekleme, enum kaldırma) bilinçli sürümleme ve istemci güncellemesi olmadan birleştirilmez.

API prefix'i `/api/v1` olarak kalır. Gerçek OpenAPI JSON adresi uygulama yapılandırmasında `/openapi.json` olarak açık tutulmalı; demo ortamında erişim kısıtlaması gerekiyorsa ayrı ayarlanmalıdır.

## 6. Contract test stratejisi

### 6.1 Test katmanları

| Katman | Araç | Neyi kanıtlar? |
|---|---|---|
| Saf birim testleri | pytest | Maliyet, ağırlık dengesi, yetki yardımcıları, durum geçişleri |
| API contract testleri | pytest + FastAPI TestClient/httpx | Status kodu, JSON alanları, hata zarfı, decimal string biçimi |
| DB entegrasyon testleri | pytest + test MySQL | Foreign key, unique constraint, transaction rollback, kilitleme ve ledger |
| Android testleri | JUnit | DTO serileştirme, repository dönüşümü, hata eşleme |
| Web testleri | Vitest + React Testing Library | DTO tüketimi, yüklenme/boş/hata durumları, form doğrulama |
| E2E | Otomatik API akışı + demo kontrol listesi | Gerçek iş akışının uçtan uca doğrulanması |

SQLite ile backend entegrasyon testleri MySQL'in davranışını tam temsil etmez. Özellikle DECIMAL, kilitleme, transaction ve constraint testleri MySQL 8.4 test örneğinde çalıştırılmalıdır. Android Room testleri ise yerel SQLite kullanımını doğrular; merkezi backend testlerinin yerine geçmez.

### 6.2 Asgari contract testleri

- [ ] Login başarılı yanıtında `access_token`, `token_type`, `expires_in`, `user` vardır.
- [ ] Yetkisiz istek `401 UNAUTHENTICATED` ortak hata zarfı döner.
- [ ] Yetkisi olmayan rol `403 FORBIDDEN` döner.
- [ ] Bulunmayan kaynak `404 RESOURCE_NOT_FOUND` döner.
- [ ] Para/miktar alanları JSON string'dir; JSON float değildir.
- [ ] Tarih `YYYY-MM-DD`, zaman UTC `Z` biçimindedir.
- [ ] Liste yanıtında `items`, `page`, `page_size`, `total` bulunur.
- [ ] FastAPI/Pydantic validation hataları ortak hata zarfına dönüştürülür.
- [ ] Bilinmeyen/ek alanlar kritik komut isteklerinde reddedilir.
- [ ] API response'larında stack trace, SQL, token veya parola yoktur.

### 6.3 Stok ledger ve transaction testleri

- [ ] Bir `IN` hareketi lot bakiyesini aynı miktarda artırır.
- [ ] Bir `OUT` hareketi lot bakiyesini aynı miktarda azaltır.
- [ ] Hareket miktarı daima pozitif; yön yalnızca `IN`/`OUT` ile belirtilir.
- [ ] Stok yetersizliğinde hareket, satış ve bakiye değişikliği oluşmaz.
- [ ] Transaction ortasında hata verilirse tüm bağlı kayıtlar rollback olur.
- [ ] Aynı iş komutu tekrarlandığında ikinci kez stok hareketi oluşmaz.
- [ ] Lot bakiyesi ile ledger toplamı test verisi üzerinde uzlaşır.
- [ ] İptal/düzeltme, eski ledger satırını değiştirmek yerine ters kayıt/iptal kaydıyla izlenir.

### 6.4 Idempotency testleri

| Senaryo | Beklenen sonuç |
|---|---|
| Aynı key + aynı body, ilk istek | Yeni işlem oluşturulur |
| Aynı key + aynı body, tekrar | İlk status/body döner; yeni işlem yok |
| Aynı key + farklı body | `409 IDEMPOTENCY_KEY_REUSED` |
| Eşzamanlı iki aynı istek | Tek işlem; iki çağrı da tutarlı sonuç alır |
| İşlem transaction'ı rollback olur | Başarısız işlem başarı sonucu olarak kaydedilmez |

Satış için `Idempotency-Key` zorunludur. Üretim/parçalama tamamlama, sevkiyat dispatch ve recall activate için aynı güvenlik seviyesi sağlanmalı; bunun idempotency kaydıyla mı yoksa durum geçişi kontrolüyle mi sağlanacağı endpoint bazında sabitlenmelidir.

### 6.5 Üretim maliyeti testleri

- [ ] Girdi maliyeti = tüketilen miktar × o girdinin geçerli maliyet snapshot'ı.
- [ ] Dış hizmet maliyetleri emre eklenir.
- [ ] Gerçek toplam maliyet ve fiili çıktı miktarı kullanılarak EKP hesaplanır.
- [ ] Sıfır veya negatif fiili çıktı miktarında EKP bölme işlemi yapılmaz; tamamlanma reddedilir veya uygun iş kuralı hatası üretilir.
- [ ] Ürün fiyatı daha sonra değiştiğinde geçmiş üretim maliyeti değişmez.
- [ ] Örnek PDF verisinde toplam: `970.00 + 48.00 + 58.00 + 467.50 = 1543.50 EUR`; 85 paket için yaklaşık `18.1588 EUR/paket` (ekranda iş kuralına göre yuvarlanmış gösterim yapılabilir).
- [ ] Maliyet hesabının yuvarlama basamağı ve dağıtım politikası testte sabittir.

### 6.6 Parçalama testleri

- [ ] Çıktı sınıfları `CUT`, `BYPRODUCT`, `WASTE` ayrımını korur.
- [ ] Fire için ayrı `butchering_waste_records` DTO/endpoint kullanılır; stokta izlenen çıktı DTO’sunda ürün/lot zorunludur.
- [ ] Girdi ağırlığı, çıktı ağırlıkları ve fark raporlanır; sistem açıklanmamış farkı gizlemez.
- [ ] Maliyet dağıtımı toplamı girdi maliyetine tam eşittir; son satır yuvarlama düzeltmesi deterministik ve testlidir.
- [ ] Kullanılabilir çıktılara lot ve genealogy bağlantıları yazılır.
- [ ] PDF örneğindeki `25 kg × 11.50 EUR = 287.50 EUR`, ayrıca verilen `351.00 EUR` ve toplamı `22 kg` olan kesim ağırlıkları tutarsızlığı test/rapor olarak görünür; uygulama neden uydurmaz.

### 6.7 Recall ve lot izlenebilirliği testleri

- [ ] `ET-2026-001` geriye izlenebilirlikte tedarikçi ve kabul kaydına döner.
- [ ] `ET-2026-001` ileri izlenebilirlikte `URT-2026-045` ve `SUC-2026-045` lotuna bağlanır (seed kayıtları aynı ilişkiyi kurmalıdır).
- [ ] Örnek 85 paket sevkiyatı 30 + 25 + 30 = 85 olarak Market A/B/C ile uzlaşır.
- [ ] Recall kapsamı kayıtlı genealogy'den türetilir; serbest metin veya AI tahminiyle belirlenmez.
- [ ] Aktif recall lotundan satış ve sevkiyat engellenir.
- [ ] Recall müşteri etkileri sevkiyat ve lot üzerinden miktar bazında raporlanır.
- [ ] İkinci kademe dağıtım kaydı yoksa sistem marketin tüketiciye satışını varsaymaz.
- [ ] Recall activate ile eşzamanlı satış denemesinde yalnızca bir tutarlı sonuç oluşur; recall etkinleştikten sonra lot satılamaz.
- [ ] İletişim durumu (`PENDING`, `CONTACTED`, `ACKNOWLEDGED`, `UNREACHABLE`, `NOT_REQUIRED`) tarihçeli ve denetlenebilir tutulur.

### 6.8 AI testleri

- [ ] Model yoksa veya eğitim verisi yetersizse sistem uydurma tahmin üretmez; açık durum/uyarı döner.
- [ ] Tahmin yanıtı model sürümünü ve sınırlama notunu taşır.
- [ ] Üretim tahminleri için tahmin/gerçekleşen değer ve hata metriği raporlanır.
- [ ] Parçalama tahminleri için çıktı sınıfı bazında tahmin/gerçekleşen ağırlık karşılaştırması yapılır.
- [ ] Baseline ile ML modeli aynı test bölmesinde karşılaştırılır.
- [ ] Eğitim/test ayrımı veri sızıntısını engeller; aynı üretim emri hem eğitim hem test tarafında kullanılmaz.
- [ ] AI çıktısı stok, maliyet veya recall için doğrudan gerçek kayıt yaratmaz.

## 7. End-to-end demo senaryosu

Aşağıdaki akış yarışma demosunda baştan sona çalıştırılmalıdır:

1. Seed/arayüz üzerinden tedarikçi, hammadde ve birim kayıtlarını oluştur.
2. `ET-2026-001` lotuna 100 kg et kabul et; lot ve `IN` hareketini kontrol et.
3. `URT-2026-045` üretim emrini oluştur; hammadde ve diğer girdileri tüket, dış hizmet maliyetini kaydet.
4. 85 paket `SUC-2026-045` çıktısını kaydet; gerçek toplam maliyet ve EKP'yi doğrula.
5. Lot genealogy üzerinden kaynak et lotundan sucuk lotuna ileri/geriye izleme yap.
6. 30, 25 ve 30 paketlik üç ayrı market sevkiyatı oluştur; toplam 85 paket olduğunu doğrula.
7. `ET-2026-001` için recall oluşturup aktive et.
8. Recall ekranında etkilenen sucuk lotunu ve Market A/B/C miktarlarını göster.
9. Recall aktifken kalan ilgili lot için yeni satış/sevkiyat dene; backend'in reddettiğini doğrula.
10. Audit ve stok hareketleri ekranlarında her adımın değiştirilemez geçmişini göster.
11. AI tahmin modülünde tahmin, gerçekleşen değer, hata metriği ve veri sınırlamalarını göster.

Demo veri seti tekrar çalıştırılabilir olmalı. Seed script ikinci çalıştırmada duplicate lot, satış veya stok hareketi yaratmamalıdır; temizleme gerekiyorsa yalnızca test veritabanında güvenli reset komutu kullanılmalıdır.

## 8. Sözleşme tutarlılığı için uygulama öncesi açık kapılar

Aşağıdaki konular kod yazılmadan önce kapatılmalı veya ilgili belgelerde açıkça “ilk sürüm davranışı” olarak sabitlenmelidir.

| # | Konu | Mevcut durum | Yapılacak iş |
|---:|---|---|---|
| 1 | Fire çıktısı `product_id`/`lot_id` | Cilt 1.17 kararı: fire ayrı tabloda; `butchering_outputs` yalnızca `CUT`/`BYPRODUCT` | Cilt 1.2/1.3/1.4/1.16 eşleşmesi ve test doğrulaması gerekli |
| 2 | `expiry_date` uygulanabilirlik | Uygulanabilir ürün/lotlarda zorunlu, diğerlerinde NULL olabilir; uygulama ölçütü henüz belirlenmeli | Açık uygulama kuralı |
| 3 | Logout | Onaylı MVP: client-side logout; server-side revoke yok | Test istemci token temizleme sözleşmesini ve API `204` yanıtını doğrular |
| 4 | Idempotency kapsamı | Satış zorunlu; diğer kritik komutlarda koruma gerekiyor | Her kritik POST için key zorunluluğu veya güvenli tekrar davranışını endpoint tablosuna yaz |
| 5 | Decimal serialization | API string olarak belirlenmiş | OpenAPI ve response testleriyle `string` olarak garanti et |
| 6 | Başarılı yanıt `request_id` | `X-Request-ID` response header; hata body `request_id` aynı değeri taşır | OpenAPI ve middleware testleri header/envelope eşleşmesini doğrular |
| 7 | Traceability “kayıt yok” durumu | Boş sonuç yanlış yorumlanabilir | Response modelinde kayıtlı veri kapsamını/status alanını açıkça belirt |
| 8 | BIGINT ve web güvenli integer | İlk sözleşme JSON integer | Demo ID aralığını sınırla veya gelecekte string ID geçişi gerekirse ayrı ADR aç |

Bu tablo bilinçli olarak kararları sessizce değiştirmez. Bir değişiklik yapılırsa Cilt 1.2, Cilt 1.3, OpenAPI ve ilgili testler aynı değişiklik setinde güncellenir.

## 9. Definition of Done

Cilt 1.4 uygulama hazırlığı için tamamlandı sayılır, eğer:

- [ ] API DTO tipleri üç istemci için eşleme kurallarıyla belgelenmiştir.
- [ ] Ortak liste ve hata kalıpları testlerle doğrulanmıştır.
- [ ] Kritik endpoint'lerin request/response modelleri OpenAPI'de vardır.
- [ ] Decimal string ve UTC timestamp biçimleri otomatik test edilir.
- [ ] Fire ayrı tablo kararı Cilt 1.17 ile eşleştirilmiştir; `expiry_date` uygulanabilirlik ölçütü ve `BY_VALUE` altında fire maliyet payı için açık kurallar ayrıca tamamlanmalıdır.
- [ ] Stok ledger, idempotency, üretim maliyeti, parçalama ve recall test senaryoları CI'a bağlanmıştır.
- [ ] Demo seed akışı 100 kg → 85 paket → 30/25/30 sevkiyat → recall şeklinde doğrulanır.
- [ ] Backend hiçbir kritik stok/maliyet/recall kararını istemcinin beyanına güvenerek vermez.

## 10. Sonraki cilt

**Önerilen sonraki belge: Cilt 1.5 — İş akışları ve durum makineleri.** Bu belgede üretim, parçalama, satış, sevkiyat ve recall için durum geçişleri; geçersiz geçişler; transaction sınırları; tekrar deneme ve eşzamanlılık davranışları tek yerde kesinleştirilecektir.

## Revizyon 1.11 — DTO ve contract-test bağlayıcı ekleri

- API JSON alanları `snake_case`; enumlar `UPPER_SNAKE_CASE`; zaman anları UTC `Z`; tarih-only alanlar `YYYY-MM-DD` biçimindedir. Para ve hassas miktarlar JSON string olarak taşınır.
- Ortak hata zarfında `request_id` kullanılır. HTTP status ve `error.code` ayrı doğrulanır; error-code registry dışındaki kodlar örnek veya test fixture'larına eklenmez.
- Access token örnekleri `expires_in: 900` göstermelidir. Refresh token ömrü 7 gündür; rotation, logout revoke ve reuse sonrası token-family revoke test edilmelidir. Health contract: anonim `GET /health/live` DB sorgusuz 200; anonim `GET /health/ready` dependency hazırsa 200, değilse 503.
- Fire DTO'su ve stokta izlenen çıktı DTO'su ayrı endpoint/şema olarak tanımlanır. Stokta izlenen çıktıda ürün/lot zorunludur; fire kaydı ürün/çıktı lotu oluşturmadığı ve stok hareketi üretmediği test edilir.
- Her stok/maliyet etkili POST için tekrar isteği davranışı sözleşmede bulunur: ya idempotency replay testi ya da tamamlanmış durumdan deterministik conflict testi. Satışta `Idempotency-Key` zorunlu; aynı key+aynı body önceki yanıtı döndürür, aynı key+farklı body `409 IDEMPOTENCY_KEY_REUSED` döndürür.
- Üretim `IN_PROGRESS` durumuna geçerken stok düşülmediği; tamamlama transaction'ında gerçek tüketim miktarıyla bir kez `OUT` üretildiği test edilir. Sevkiyat dispatch için stok `OUT/SHIPMENT` tek kez üretilir; satış kaydı hiçbir zaman fiziksel stok `OUT` üretmez. Bu onaylanmış normatif kuraldır; testler dispatch başına tek hareket ve satış başına sıfır stok hareketi doğrular.
- Recall aktivasyonunun atomik olduğu, kısmi lot blokajı bırakmadığı ve `RESOLVED` durumunun tek başına lotu yeniden satışa açmadığı negatif testlerle doğrulanır.
- Rol negatif testleri: stok düzeltmede `ADMIN` dışındaki roller reddedilir; sevkiyat yazma işlemleri `ADMIN`/`SALES` dışındaki rollere reddedilir; AI tahmini başlatma ve okuma izinleri ayrı test edilir.
- Ağırlık toleransı için sayısal beklenen değer yazılmaz; testler tolerans konfigürasyonu yokken farkın sessizce kabul edilmediğini ve gerekçe/audit gereksinimini doğrular.
