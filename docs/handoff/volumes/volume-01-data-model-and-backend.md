# Cilt 1 — Veri Modeli, Backend Sınırları ve API Sözleşmeleri

**Durum:** Onaylanmış teknoloji standardına uygun mantıksal veri modeli ve API taslağı — iş kuralları ve alan/endpoint sözleşmeleri implementasyon öncesi tamamlanmalıdır  
**Bağlı ciltler:** Cilt 0, Cilt 2, Cilt 3, Cilt 4, Cilt 5, Cilt 6, Cilt 7, Cilt 8  
**Hedef:** Üretim, parçalama, satış, stok, lot izlenebilirliği ve AI modüllerinin aynı kavramları ve sözleşmeleri kullanmasını sağlamak.

> **LLM talimatı:** Bu cildi ve Cilt 0'ı okumadan veri tabanı veya API kodu üretme. Bu dokümanda `[TBD]` bulunan bir konuyu kendi başına kesin karara dönüştürme. Şema ile yarışma gereksinimi arasında çelişki görürsen kod yazmadan önce bildir.

## Onaylanmış teknoloji standardı — bağlayıcı

Proje sahibi bu teknoloji yığınını 22 Ekim 2026'da onaylamıştır. Bu ciltteki tasarım ve kodlama işleri aşağıdaki standartları kullanacaktır.

| Katman | Kesinleşen teknoloji |
|---|---|
| Android | Kotlin + Jetpack Compose |
| Yerel veritabanı | **SQLite zorunludur**; SQLite erişim/persistence katmanı olarak Room kullanılacaktır |
| Android API istemcisi | Retrofit + OkHttp + Kotlin Coroutines |
| Backend | Python + FastAPI + Pydantic |
| ORM ve migration | SQLAlchemy 2.x + Alembic |
| MySQL sürücüsü | PyMySQL |
| Merkezi veritabanı | MySQL 8.4 LTS |
| Web paneli | React + TypeScript + Vite + Tailwind CSS |
| Web veri yönetimi/grafikleri | TanStack Query + Recharts |
| ML | pandas + NumPy + scikit-learn + joblib |
| ML dağıtımı | İlk sürümde FastAPI backend içinde ayrı ML modülü; bağımsız mikroservis yok |
| Test ve geliştirme | Git/GitHub + Docker Compose + pytest + JUnit + Vitest + React Testing Library |
| API sözleşmesi | REST + JSON + OpenAPI |
| Android çalışma modeli | Online-first; ilk sürümde çevrimdışı satış yok |

### SQLite ile MySQL arasındaki kesin sınır

- SQLite, Android uygulaması için zorunlu yerel veritabanıdır. Room, SQLite'ın yerine geçen farklı bir veritabanı değildir; SQLite üzerinde entity/DAO ve migration katmanı sağlar.
- MySQL, merkezi iş kayıtlarının esas kaynağıdır. Android ve web paneli MySQL'e doğrudan bağlanmaz.
- SQLite/Room yerel referans verileri, son API yanıtlarından oluşan önbellek ve gerekli sınırlı uygulama durumunu tutabilir.
- Satış ancak backend API'si tarafından doğrulanıp kabul edilirse tamamlanır. Backend; lot blokajını, yeterli stoğu, idempotency ve eşzamanlı istek güvenliğini kontrol eder.
- Bağlantı yokken ilk sürümde satış kabul edilmez ve çevrimdışı satış kuyruğu/senkronizasyonu uygulanmaz.
- Yerel SQLite'taki stok veya lot bilgisi, merkezi stok ve geri çağırma durumunun yerine geçmez.
- SQLite'ta tutulacak kesin tablolar, önbellek yenileme ve geçersizleştirme politikası Cilt 4'te ayrıntılandırılacaktır. Bu, SQLite kullanılıp kullanılmayacağına dair açık bir karar değildir; SQLite kullanımı kesindir.

### Açık kararların anlamı

Bu ciltteki `[TBD]` etiketleri teknoloji seçimini değil; alan tipleri, para gösterimi/yuvarlama, rol matrisi, stok bakiye stratejisi, durum geçişleri ve API şema ayrıntıları gibi iş/veri sözleşmesi kararlarını ifade eder. Bir LLM, onaylanmış teknoloji yığınını değiştiremez ve `[TBD]` konularını proje sahibinin kararı olmadan sessizce kesinleştiremez.


---

## 1. Tasarım hedefleri

1. Tek bir merkezi MySQL veri modeli üretim, parçalama, satış ve geri çağırmayı desteklemeli.
2. Her stok değişimi izlenebilir bir hareket kaydı üretmeli.
3. Lot ilişkileri miktarlarıyla saklanmalı; yalnızca metin alanlarına veya ürün adına güvenilmemeli.
4. Para ve miktar değerleri için hassasiyet kaybı önlenmeli.
5. Android ve React uygulamaları iş kurallarını kopyalamamalı; backend API'sini kullanmalı.
6. Aynı satış isteğinin tekrar gönderilmesi ikinci satış oluşturmamalı.
7. AI tahminleri operasyonel gerçeklerden ayrı tutulmalı.
8. Testler, yarışma PDF'sindeki sabit senaryoları tekrarlanabilir biçimde doğrulamalı.

## 3. Mimari sınırlar

### 2.1 İstemciler
- Kotlin Android: Jetpack Compose arayüzü; Retrofit/OkHttp ile REST API istemcisi; Room üzerinden zorunlu SQLite yerel veritabanı.
- React + TypeScript web paneli: TanStack Query ve standart fetch istemcisiyle REST API istemcisi.
- İstemciler doğrudan MySQL'e bağlanmaz ve kritik stok/lot kararlarını tek başına vermez.

### 2.2 Backend
**Onaylanmış standart:** Python + FastAPI. İstek/yanıt doğrulaması Pydantic, ORM SQLAlchemy 2.x, migration Alembic, MySQL sürücüsü PyMySQL olacaktır.
Backend sorumlulukları:
- Girdi doğrulama ve yetkilendirme.
- İş kurallarının uygulanması.
- İşlem sınırlarının/transaction'ların yönetilmesi.
- Stok hareketi üretimi.
- Üretim ve parçalama maliyet hesaplarının çağrılması.
- Lot ileri/geriye izleme ve geri çağırma.
- ML tahmin API'lerinin çağrılması.
- Tutarlı hata yanıtları ve denetlenebilir kayıt.

### 2.3 Veritabanı
**[PDF]** Merkezi veritabanı MySQL. Tablolar, foreign key'ler, unique constraint'ler ve gerekli indeksler kullanılarak veri bütünlüğü mümkün olduğunca veritabanında da korunmalıdır.

---

## 4. Veri modelleme ilkeleri

### 3.1 Kimlikler ve kodlar
- Her tablo için dahili, değişmez `BIGINT UNSIGNED` primary key kullanılır (DEC-001 kararı).
- İnsanların gördüğü `ET-2026-001`, `URT-2026-045`, `SUC-2026-045` gibi iş kodları ayrı alanlarda saklanmalı ve uygun kapsamda benzersiz olmalıdır.
- İş kodu primary key olarak kullanılmamalıdır; dahili PK `BIGINT UNSIGNED`, iş kodu ise ayrı benzersiz alandır.
- Zorunlu yarışma kodları demo verisinde aynen korunmalıdır.

### 3.2 Para, miktar ve tarih
- Parasal alanlar için MySQL `DECIMAL` gibi kesin ondalık türler tercih edilmelidir; `FLOAT`/`DOUBLE` ile parasal toplamlar hesaplanmamalıdır.
- Ağırlık/miktar alanlarında ihtiyaca uygun `DECIMAL` hassasiyeti kullanılmalıdır.
- Para ve hassas miktarlar MySQL'de DECIMAL ile saklanır ve API'de JSON string olarak taşınır (DEC-001 kararı; ayrıntı Cilt 1.2).
- Zaman damgaları için veritabanında UTC saklama ve API'de ISO 8601 biçimi önerilir; yerel tarih gösterimi arayüz sorumluluğudur.
- Para birimi `currency_code` ile saklanır; ilk demo EUR kullanır. İlk sürümde kur dönüşümü kapsam dışıdır (DEC-001 kararı).

### 3.3 Silme ve denetim
- Üretim, stok, satış ve geri çağırma kayıtları geçmişi kaybettirecek şekilde sessizce silinmemelidir.
- Hatalı işlemler için iptal/düzeltme hareketi veya durum geçişi tanımlanmalıdır.
- Kim tarafından, ne zaman oluşturulduğu/değiştirildiği gibi denetim alanları önemli kayıtlarda bulunmalıdır.
- Tam audit-log kapsamı ve kullanıcı rolleri `[TBD]`.

### 3.4 Stok modeli
**Öneri:** Stok miktarını yalnızca `products.current_stock` gibi tek bir alandan elle değiştirmeyin. Her stok hareketi kayıt altına alınmalı; güncel bakiye hareketlerden hesaplanabilir veya performans için hareketlerle tutarlı bir bakiye tablosunda tutulabilir. İkinci yaklaşım seçilirse bakiye güncellemesi ve hareket oluşturma aynı transaction içinde yapılmalıdır.

Her stok hareketi en azından:
- Ürün
- Lot (lot gerektiren ürünlerde zorunlu)
- Miktar ve birim
- Hareket türü
- Kaynak belge/işlem
- Hareket zamanı
- Giriş/çıkış yönü veya işaret kuralı
alanlarını içermelidir.

**[DEC-001 KARARI]** Değişmez stok hareketi ledger'ı ve transaction içinde güncellenen `inventory_balances` tablosu birlikte kullanılır.

---

## 5. Önerilen varlıklar ve ilişkiler

Aşağıdaki liste mantıksal taslaktır; Cilt 1'in ilk uygulama şeması oluşturulurken alanlar ve kısıtlar kesinleştirilecektir.

### 4.1 Ana kataloglar

#### `products` — Ürün kartları
Ürün, hammadde, yarı mamul veya mamul olabilir.

Önerilen alanlar:
- `id`
- `code` (benzersiz iş kodu)
- `name`
- `product_type` (raw_material / intermediate / finished_good / byproduct; değerler gözden geçirilecek)
- `base_unit`
- `is_lot_tracked`
- `is_active`
- `created_at`, `updated_at`

Not: Kategori ve ürün tipi kavramları ayrılmalı; bir ürünün hammadde veya mamul olması, ürünün hangi lotta bulunduğundan ayrı tutulmalıdır.

#### `units` ve `unit_conversions`
Ölçü birimlerini ve izin verilen dönüşümleri tanımlar.
- `units`: `code`, `name`, `dimension`
- `unit_conversions`: kaynak birim, hedef birim, dönüşüm katsayısı ve gerekiyorsa geçerlilik.
- Kütle ile adet gibi farklı boyutlar arasında dönüşüm, ürün bazlı bir kural olmadan yapılmamalıdır.

#### `suppliers`
Tedarikçi ve dış hizmet üreticisi bilgileri. Dış üretici ile hammadde tedarikçisi aynı varlık türü olabilir, ancak roller ayrılmalıdır.

#### `customers`
Market veya işletme müşterisi. Zorunlu senaryoda Market A/B/C kayıtları oluşturulabilir. İletişim alanları yalnızca gerekli olduğunda tutulmalıdır.

#### `product_prices` / fiyat geçmişi
Alış fiyatı, satış fiyatı ve geçerlilik zamanı için fiyat geçmişi ihtiyacı vardır. Tam fiyatlandırma modeli `[TBD]`; geçmiş maliyetin yeni fiyatla geriye dönük değişmemesi sağlanmalıdır.

### 4.2 Lot ve stok

#### `lots`
Lot/parti ana kaydı:
- `id`
- `lot_code` (uygun kapsamda benzersiz)
- `product_id`
- `supplier_id` (giriş lotları için gerekiyorsa)
- `received_at`
- `expiry_date` (uygunsa)
- `initial_quantity`
- `unit_code`
- `status` (ör. active / blocked / exhausted; kesin enum ve durum geçişleri TBD)
- `created_at`

Lot kodu örnekleri: `ET-2026-001`, `SUC-2026-045`.

**Önemli:** Bir lotun durumu ve kullanılabilir stok miktarı aynı kavram değildir. Lot bloke olabilir ama fiziksel miktar hâlâ stokta bulunabilir.

#### `stock_movements`
Değişmez/denetlenebilir stok hareketleri:
- `id`
- `product_id`
- `lot_id` (lot izlenen stoklarda zorunlu)
- `movement_type`
- `quantity`
- `unit_code`
- `source_type`
- `source_id`
- `occurred_at`
- `created_by` (uygunsa)
- `idempotency_key` veya kaynak belge bazında tekrar önleme anahtarı

Hareket türleri için ilk adaylar:
- receipt
- production_issue
- production_receipt
- butchering_input
- butchering_output
- shipment
- sale
- return
- transfer_out / transfer_in
- rework_issue / rework_receipt
- waste
- recall_block / recall_release (stok miktarını değiştirmeyebilir; blokaj ayrı durum/rezervasyon modelinde tutulması daha doğru olabilir)

Bu liste kesin değildir. Blokajı stok hareketi olarak mı yoksa ayrı `lot_blocks` kaydı olarak mı temsil edeceğimiz `[TBD]`; fiziksel stok miktarıyla satılabilir miktar karıştırılmamalıdır.

### 4.3 Dış hizmet üretimi

#### `production_orders`
- `id`, `order_code`
- `service_provider_id`
- `status`
- `planned_at`, `completed_at`
- `notes`
- `created_at`

#### `production_order_inputs`
Üretim emrinde kullanılan her hammadde lotu için bir satır:
- `production_order_id`
- `product_id`
- `lot_id`
- `quantity`
- `unit_code`
- `unit_cost_at_issue`
- `total_cost_at_issue`

Bu ilişki bir üretim emrinin birden fazla lot kullanabilmesini sağlar.

#### `production_service_costs`
Dış üretim hizmeti maliyet satırları:
- `production_order_id`
- `description`
- `quantity`
- `unit_price`
- `currency`
- `total_cost`

#### `production_order_outputs`
Üretim emrinden çıkan her mamul lotu/mamul için satır:
- `production_order_id`
- `product_id`
- `lot_id`
- `quantity`
- `unit_code`
- maliyet atama sonucu/ilişkisi

Bir üretim emrinden birden fazla mamul lotu çıkabilmesi desteklenmelidir. Maliyet dağıtım kuralı Cilt 2'de tanımlanır.

### 4.4 Parçalama

#### `butchering_orders`
- `id`, `order_code`
- giriş hayvanı/parti lotu
- hayvan türü
- giriş ağırlığı
- alış maliyeti ve para birimi
- işlem zamanı
- durum

#### `butchering_recipe_lines`
Reçetede beklenen çıktı ürünleri ve isteğe bağlı hedef/dağıtım kuralları.

#### `butchering_outputs`
Fiilî her çıktı için:
- `butchering_order_id`
- `product_id`
- `output_lot_id`
- `actual_quantity`
- `unit_code`
- `output_type` (ürün / yan ürün / fire vb.; değerler Cilt 3'te kesinleşecek)
- dağıtım ağırlığı ve tahsis edilen maliyet

Bir giriş lotundan çıkan her ürün lotuna ilişki kurulmalıdır. Ağırlık dengesi ve maliyet dağıtımı Cilt 3'te tanımlanır.

### 4.5 Sevkiyat ve satış

#### `shipments` ve `shipment_lines`
Market/müşteriye sevkiyat belgesi ve satırları:
- müşteri
- tarih
- ürün/lot
- miktar/birim
- kaynak stok hareketi

Sevkiyat ile satış kavramı karıştırılmamalıdır. PDF senaryosu marketlere sevkiyatı açıkça ister; her sevkiyatın son tüketici satışını bildiği varsayılmamalıdır.

#### `sales` ve `sale_lines`
- `sales`: işlem kimliği, tarih, durum, kanal/istemci referansı, toplamlar.
- `sale_lines`: ürün, lot, miktar, birim fiyat, uygulanmış maliyet referansı gerekiyorsa ve satır toplamları.

Her satış satırının lotu ve miktarı saklanmalıdır. Lot bazlı stok hareketi satışın kabul edildiği transaction içinde oluşturulmalıdır.

#### `idempotency_records` (öneri)
İstemcinin aynı işlemi yeniden göndermesi durumunda aynı sonucu geri döndürmek için benzersiz istek anahtarı ve işlem sonucu saklanabilir. Kesin tasarım API implementasyonunda yapılır.

### 4.6 Lot köken ilişkileri

#### `lot_genealogy`
Lotlar arasındaki dönüşüm/köken bağlantısı:
- `source_lot_id`
- `target_lot_id`
- `process_type` (production / butchering / rework vb.)
- `process_id`
- `input_quantity`
- `input_unit`
- `output_quantity` veya ilişkiyi doğru temsil eden miktar alanları
- oluşturulma zamanı

**Önemli modelleme uyarısı:** Girdi ve çıktı miktarları farklı ürün/birimler için her zaman doğrudan bire bir kıyaslanabilir değildir. Bu nedenle miktarların hangi lota ve hangi birime ait olduğu açıkça tutulmalıdır. Gerekirse giriş ve çıkış miktarları ayrı ilişki satırlarıyla modellenmelidir. Son şema Cilt 5'in ileri/geriye izleme sorgularıyla doğrulanmalıdır.

Lot kökeni hem üretim hem parçalama hem de yeniden işleme için çalışmalıdır. Yalnızca `parent_lot_id` alanı yeterli değildir; çoktan çoğa ilişkiler gereklidir.

### 4.7 Geri çağırma

#### `recalls`
- `id`, `recall_code`
- kaynak sorunlu lot
- sebep/açıklama
- durum (draft / active / closed gibi; kesin durum geçişleri TBD)
- başlatılma zamanı
- başlatan kullanıcı
- kapanış bilgileri

#### `recall_affected_lots`
Geri çağırmadan etkilenen mamul/ara ürün lotları ve neden ilişkisi.

#### `lot_blocks`
- lot
- geri çağırma kaydı
- blokaj durumu
- başlama/bitme zamanı
- gerekçe

Geri çağırma birden fazla lotu etkileyebilir. Bir lotun birden fazla blokaj gerekçesi olabileceği düşünülerek tek bir boolean alanla bütün geçmişin silinmemesi gerekir.

#### `recall_customer_impacts`
Raporlama için müşteri, sevkiyat, lot ve miktar bağlantısı. Bu kayıt mümkünse kaynak sevkiyat/satış kayıtlarından hesaplanmalı; kalıcı snapshot gerekiyorsa ne zaman üretildiği ve kaynağı belirtilmelidir.

### 4.8 AI tahminleri

#### `ml_predictions` (öneri)
- `id`
- `model_name`
- `model_version`
- `prediction_type`
- ilgili üretim/parçalama kaydı
- tahmin girdileri veya girdilerin denetlenebilir referansı
- tahmin çıktısı
- oluşturulma zamanı
- model/çalıştırma metadatası

Gerçek gerçekleşen değerler operasyonel kayıtlardan okunmalıdır; tahmin tablosu gerçek stok veya maliyet kaydının yerini almamalıdır. Model değerlendirme veri setleri ve metrik raporlarının saklanma biçimi Cilt 6'da belirlenir.

---

## 6. Kritik ilişki özeti

- Bir ürünün birden fazla lotu olabilir.
- Bir lot birçok stok hareketinde yer alabilir.
- Bir üretim emri birçok hammadde lotu kullanabilir.
- Bir hammadde lotu birçok üretim emrinde kullanılabilir.
- Bir üretim emri bir veya daha fazla mamul lotu oluşturabilir.
- Bir parçalama emri bir giriş lotundan birçok çıktı lotu oluşturabilir.
- Bir lot birçok sevkiyat/satış satırında bulunabilir.
- Bir lotun bir veya daha fazla köken/sonraki lot ilişkisi olabilir.
- Bir geri çağırma birçok lotu ve müşteriyi etkileyebilir.

Bu ilişkiler, miktarları ve birimleriyle saklanmalıdır.

---

## 7. REST API tasarım sözleşmesi

Aşağıdaki endpoint'ler önerilen kaynak sınırlarıdır. Kesin path, DTO alanları ve durum kodları OpenAPI şemasında sabitlenmeden Android/web kodlaması başlatılmamalıdır.

### 6.1 Genel kurallar
- API sürümlemesi önerisi: `/api/v1/...`.
- JSON istek/yanıtları.
- Backend her girişi doğrular.
- Liste endpoint'leri sayfalama ve filtreleme stratejisine sahip olmalıdır.
- Tutarlı hata şeması kullanılmalıdır.
- Satış/üretim/parçalama gibi kritik yazma işlemleri transaction içinde yapılmalıdır.
- Para ve miktarların JSON temsili bütün endpoint'lerde aynı olmalıdır.
- Kullanıcı kimlik doğrulaması/rolleri `[TBD]`; ancak bu karar API sözleşmesi onaylanmadan önce verilmelidir.

### 6.2 Önerilen kaynaklar

| Alan | Önerilen endpoint örnekleri | Amaç |
|---|---|---|
| Health | `GET /api/v1/health` | Servis erişilebilirliği |
| Ürünler | `GET /api/v1/products`, `GET /api/v1/products/{id}` | Ürün kartları |
| Lotlar | `GET /api/v1/lots`, `GET /api/v1/lots/{id}` | Lot ve durum bilgisi |
| Stok | `GET /api/v1/inventory`, `GET /api/v1/inventory/lots/{id}` | Güncel stok/bakiye |
| Üretim | `POST /api/v1/production-orders`, `GET /api/v1/production-orders/{id}` | Üretim emri ve detayları |
| Üretim tamamla | `POST /api/v1/production-orders/{id}/complete` | Çıktı ve maliyet kaydını atomik tamamlamak |
| Parçalama | `POST /api/v1/butchering-orders`, `POST /api/v1/butchering-orders/{id}/complete` | Parçalama ve çıktılar |
| Satış | `POST /api/v1/sales`, `GET /api/v1/sales/{id}` | Satış oluşturma ve görüntüleme |
| Sevkiyat | `POST /api/v1/shipments`, `GET /api/v1/shipments/{id}` | Market sevkiyatı |
| İzlenebilirlik | `GET /api/v1/traceability/lots/{lotCode}/forward`, `.../backward` | İleri/geriye izleme |
| Geri çağırma | `POST /api/v1/recalls`, `GET /api/v1/recalls/{id}`, `POST /api/v1/recalls/{id}/activate` | Geri çağırma yönetimi |
| ML tahminleri | `POST /api/v1/predictions/production-yield`, `POST /api/v1/predictions/butchering-yield` | İki zorunlu tahmin |
| Raporlar | `GET /api/v1/reports/...` | Yönetim ve değerlendirme raporları |

Bu tablo bir sözleşme taslağıdır, tamamlanmış OpenAPI belgesi değildir. Her endpoint için request/response örnekleri, hata kodları ve yetkiler API implementasyonundan önce eklenmelidir.

### 6.3 Satış endpoint'i için zorunlu mantık

`POST /api/v1/sales` aşağıdaki doğrulamaları yapmalıdır:

1. İstek yapısı ve satırları geçerli mi?
2. Her satırda ürün, lot, miktar ve birim doğru mu?
3. Lot ilgili ürüne ait mi ve satışa açık mı?
4. Lot geri çağırma nedeniyle bloke mi?
5. Satılabilir miktar yeterli mi?
6. Eş zamanlı satış nedeniyle stok değişmiş mi?
7. İdempotency anahtarı daha önce işlendi mi?
8. Satış kaydı, satırları ve stok hareketleri tek transaction içinde tutarlı biçimde yazılabiliyor mu?

Bir koşul başarısızsa işlem kısmi stok düşümü bırakmamalıdır. Başarılı işlemde satış ve stok hareketi birlikte commit edilmelidir.

### 6.4 Hata yanıtı önerisi

Örnek genel yapı:

```json
{
  "error": {
    "code": "LOT_BLOCKED",
    "message": "The selected lot is blocked and cannot be sold.",
    "details": {
      "lotCode": "SUC-2026-045"
    },
    "request_id": "server-generated-request-id"
  }
}
```

Gerçek sözleşmede mesajların dili, alan adları, hata kodları ve HTTP durum kodları tutarlı biçimde belirlenmelidir. İstemci yalnızca serbest metne göre karar vermemeli; kararlı `code` alanını kullanmalıdır.

---

## 8. Eş zamanlılık ve idempotency

Bu konu özellikle satış ve stokta zorunludur.

### 7.1 Yinelenen istek
İstemci aynı satış isteğini ağ hatası nedeniyle tekrar gönderirse:
- Aynı idempotency anahtarıyla ikinci satış yaratılmamalı.
- İlk işlem başarılıysa ilk işlemin sonucu geri döndürülmeli.
- Aynı anahtar farklı içerikle kullanılırsa istek reddedilmelidir.

### 7.2 Eş zamanlı satış
İki satış aynı lotun son stokunu eş zamanlı tüketmeye çalışırsa backend transaction/lock/atomik stok kontrolüyle yalnızca geçerli işlemi kabul etmelidir. Uygulama katmanında “önce oku, sonra düş” yaklaşımı tek başına yeterli değildir.

### 7.3 Geri çağırma ile yarış durumu
Lot blokajı ve satışın kabul edilmesi arasında yarış durumu oluşmamalıdır. Satış transaction'ı lotun güncel durumunu ve stok uygunluğunu doğrulamalıdır. Geri çağırma aktivasyonuyla satışların hangi sırada kesinleşeceği transaction ve kilitleme stratejisinde tanımlanmalıdır.

---

## 9. Gerekli ilk test senaryoları

Bu testler Cilt 8'de genişletilecek, ancak veri modeli/API tasarımı sırasında mümkün oldukları doğrulanmalıdır.

### 8.1 Üretim
- PDF örneğindeki maliyet toplamı 1.543,50 €.
- 85 paket için EKP yaklaşık 18,16 €.
- Üretim çıktısı 85 olarak kaydedilir; planlanan ve gerçekleşen miktar ayrı tutulur.
- Kullanılan hammaddeler ve hizmet maliyeti üretim emrine bağlanır.

### 8.2 Parçalama
- Dağıtılan maliyet toplamı, toplam maliyetle eşit.
- 25 × 11,50 = 287,50 hesabı doğru.
- Toplamı 22 kg olan örnek parça miktarları ile giriş ağırlığı arasındaki fark gizlenmez.
- Bilinmeyen fire veya yan ürün miktarı uydurulmaz.

### 8.3 Lot ve geri çağırma
- `ET-2026-001` -> `URT-2026-045` -> `SUC-2026-045` ilişkisi sorgulanabilir.
- Market A/B/C sevkiyat miktarları 30/25/30 ve toplam 85'tir.
- Geri çağırma sonrası etkilenen lotlar listelenir.
- Bloke lot satışı backend tarafından reddedilir.
- İkinci kademe dağıtım kaydı yoksa sistem son tüketici dağıtımını bildiğini iddia etmez.

### 8.4 API güvenilirliği
- Aynı idempotency anahtarıyla tekrar satış çift kayıt üretmez.
- Yetersiz stokta hareket yaratılmaz.
- Geçersiz ürün-lot eşleşmesi reddedilir.
- Backend bağlantı hatasında istemci başarılı satış göstermez.
- Eş zamanlı son-stok satış testi tutarlı sonuç verir.

---

## 9. LLM'ler için uygulama talimatı

Bu cildi uygulayacak LLM aşağıdaki sırayla çalışmalıdır:

1. Cilt 0 ve bu cildi okuyup belirsizlikleri listele.
2. Tablo/ilişkileri bir ERD veya Mermaid diyagramıyla öner.
3. Alan türleri, nullability, unique/FK/index kısıtlarını açıkla.
4. İlgili endpoint'ler için OpenAPI uyumlu request/response şemaları üret.
5. Migration stratejisini ve örnek seed verisini tanımla.
6. Kritik iş kuralları için test taslağı üret.
7. Belirsizlikleri çözülmeden “kesin karar” olarak kodlama.
8. Çıktıda değişen dokümanları, varsayımları, testleri ve kalan açık konuları raporla.

**Kabul edilmez:** Tek bir genel `transactions` tablosuyla üretim, sevkiyat, satış, parçalama ve lot kökenini ayrıntısız biçimde temsil etmek; lot ilişkilerini yalnızca virgülle ayrılmış metin olarak saklamak; geri çağırmayı yalnızca frontend'de engellemek; maliyetleri `float` ile hesaplamak.

---

## 10. Cilt 1'in tamamlanma kriterleri

Cilt 1'in veri ve API ayrıntıları, aşağıdaki kabul kriterleri tamamlandığında implementasyon sözleşmesi olarak onaylanabilir. Teknoloji yığını zaten onaylanmıştır:

- [ ] ERD, üretim ve parçalama dahil çoktan çoğa lot ilişkilerini gösteriyor.
- [ ] Stok hareketi ve güncel stok tutarlılığı yöntemi kararlaştırılmış.
- [ ] Para/miktar veri türleri ve API gösterimi kararlaştırılmış.
- [ ] Üretim, parçalama, satış, sevkiyat ve geri çağırma varlıkları ayrılmış.
- [ ] Satış idempotency ve eş zamanlı stok kontrolü tanımlanmış.
- [ ] Lot blokajı fiziksel stoktan ayrı ele alınmış.
- [ ] Her yazma endpoint'i için request/response ve hata şeması yazılmış.
- [ ] Kullanıcı rolleri ve gerekli yetkiler tanımlanmış.
- [ ] Zorunlu yarışma senaryolarını temsil eden seed veri planı mevcut.
- [ ] Kritik iş kuralları için testler tanımlanmış.
- [ ] Cilt 2–7 ile çelişki kontrolü yapılmış.

Bu doküman mantıksal tasarım ve uygulama sözleşmesi taslağıdır. Liste işaretlerinin tamamı test/şema kanıtıyla doğrulanmadan “tamamlandı” sayılmamalıdır.

## DEC-001 uyumluluğu — bağlayıcı kurallar

DEC-001 veri/API kararlarının tamamı proje sahibi tarafından onaylanmıştır. Bu ciltteki model ve endpoint'ler bu kurallarla uyumlu olmalıdır:

- Dahili PK/FK: `BIGINT`; iş kodları ayrı ve benzersiz.
- Para: `DECIMAL(19,4)`; miktar/ağırlık: `DECIMAL(19,6)`; hassas ondalık API alanları JSON string.
- Zaman anları UTC ISO 8601; takvim tarihi `YYYY-MM-DD`.
- Stok ledger hareketleri ve lot bakiyeleri aynı transaction içinde güncellenir; hareket miktarı pozitif, yön `IN`/`OUT`.
- Lot genealogy çoktan çoğa ve miktarlıdır.
- Satış ve sevkiyat ayrı iş kayıtlarıdır; ikinci kademe market dağıtımı kayıt olmadan varsayılmaz.
- JWT + rol bazlı erişim; önerilen başlangıç rolleri `ADMIN`, `OPERATOR`, `SALES`, `TRACEABILITY_MANAGER`, `VIEWER`.
- Kritik operasyon kayıtları hard delete edilmez.
- Satış `Idempotency-Key` gerektirir; aynı anahtar/farklı payload `409 Conflict` üretir.
- Hata yanıtı ortak `error.code`, `error.message`, `error.details`, `request_id` biçimindedir.
- API prefix `/api/v1`; liste uçları ortak sayfalama/filtreleme kullanır.
- DB/API JSON alanları `snake_case`; enum değerleri `UPPER_SNAKE_CASE`; endpoint path'leri kebab-case.

Bu kararlar teknoloji seçimi gibi yeniden tartışmaya açık öneriler değil, onaylanmış sözleşmelerdir. Alanların tablo bazında kesinleştirilmesi ve OpenAPI şemaları bir sonraki Cilt 1 ayrıntılandırma adımıdır.

---

