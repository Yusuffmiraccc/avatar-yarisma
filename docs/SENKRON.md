# AVATAR — SQLite (Room) ile MySQL Arasında Tutarlı Senkronizasyon Mimarisi

Bu belge, AVATAR Yapay Zekâ Yarışması Değerlendirme Belgesi Bölüm 6'da talep edilen **"SQLite ve MySQL arasında tutarlı senkronizasyon yaklaşımı"** gereksiniminin teknik mimarisini, veri akışını, çakışma çözümleme mekanizmasını ve tutarlılık güvencelerini tanımlar.

---

## 1. Temel İlke ve Mimarî Roller

```
┌─────────────────────────────────┐               ┌─────────────────────────────────┐
│     Merkezi Sunucu (MySQL)      │               │   Mobil İstemci (Android/Room)  │
│                                 │               │                                 │
│   • TEK DOĞRULUK KAYNAĞI        │ ◄── REST API ─►   • YEREL OKUMA ÖNBELLEĞİ       │
│   • Nihai stok bakiye defteri   │   (JSON/HTTPS)│   • Çevrimdışı işlem kuyruğu    │
│   • Kesin satış & sevkiyat      │               │   • İyimser (optimistic) stok   │
│   • Blokaj & geri çağırma       │               │   • Idempotent UUID üretimi     │
└─────────────────────────────────┘               └─────────────────────────────────┘
```

1. **Sunucu Tarafı (MySQL 8.4):** Sistemin **tek doğruluk kaynağıdır (single source of truth)**. Stok defteri append-only (yalnızca eklemeli) çalışır; fiziksel stok düşüşünün tek sahibi sevkiyat (dispatch) hareketidir.
2. **İstemci Tarafı (Android SQLite / Room):** Sunucu verilerinin **yerel önbelleği (cache)** ve henüz sunucuya ulaşmamış satışların **bekleyen işlem kuyruğudur (offline write queue)**.
3. **Çift Yönlü Birleştirme (Two-Way Merge) Yapılmaz:** Mobil cihaz sunucu veritabanına doğrudan bağlanmaz; istemci ve sunucu kayıtları karmaşık kurallarla "merge" edilmez. Çakışma durumunda son söz daima sunucunundur.

---

## 2. Aşağı Yönlü Senkronizasyon (Sunucu → SQLite)

Mobil cihaz açıldığında, ön plana geldiğinde, satış ekranı açıldığında veya periyodik WorkManager tetiklendiğinde `GET /api/v1/sync/catalog` endpoint'i çağrılır.

### 2.1 İstek ve Yanıt Yapısı

- **İstek:**
  ```http
  GET /api/v1/sync/catalog?updated_after=2026-10-29T08:30:00Z
  Authorization: Bearer <access_token>
  ```
  *(İlk açılışta `updated_after` parametresi gönderilmez; tam katalog istenir.)*

- **Sunucu Yanıtı:**
  ```json
  {
    "server_time": "2026-10-29T09:00:00Z",
    "products": [ ... ],
    "customers": [ ... ],
    "sellable_lots": [
      {
        "id": 145,
        "lot_code": "SUC-2026-045",
        "product_id": 12,
        "product_code": "SUCUK",
        "product_name": "Narin Sucuk 1 kg",
        "on_hand_quantity": "85.000000",
        "unit_code": "PACK",
        "sale_price": "24.00"
      }
    ],
    "blocked_lots": [
      {
        "id": 101,
        "lot_code": "ET-2026-001",
        "reason_code": "QUALITY",
        "reason_text": "Kalite güvence sorunu"
      }
    ]
  }
  ```

### 2.2 Yerel Uygulama Adımları (Tek Room Transaction)

1. **Artımlı Güncelleme (Upsert):** `products` ve `customers` tabloları gelen kayıtlarla güncellenir (`OnConflictStrategy.REPLACE`).
2. **Tam Yenileme (Replace All):** `sellable_lots` ve `blocked_lots` tabloları **tamamen silinip baştan doldurulur**.
   - *Gerekçe:* Sunucuda tükenmiş, silinmiş veya bloke edilmiş bir lot yerel tabloda artık yer alamaz.
3. **Zaman Damgası:** `sync_state` tablosuna `last_server_time = server_time` kaydedilir. Cihazın yerel saati yerine sunucu saati kullanılarak saat sapması (clock skew) engellenir.

---

## 3. Yukarı Yönlü Senkronizasyon (SQLite → Sunucu)

Saha satış personeli satış yaptığında akış aşağıdaki adımlarla işler:

### 3.1 Adım 1: Yerel Satışın Kaydedilmesi ve İyimser Düşüm

1. Kullanıcı müşteri ve lotları seçip satışı onaylar.
2. Android uygulaması benzersiz bir UUID üretir: `client_uuid = UUID.randomUUID().toString()`.
3. Tek Room transaction'ında:
   - `pending_sales` tablosuna durum `PENDING` ve `clientUuid` ile başlık yazılır.
   - `pending_sale_lines` tablosuna satırlar kaydedilir.
   - **İyimser Stok Düşümü (Optimistic Deduction):** Satılan miktar kadar yerel `sellable_lots.on_hand_quantity` bakiyesinden düşülür:
     ```sql
     UPDATE sellable_lots 
     SET onHandQuantity = onHandQuantity - :qty 
     WHERE id = :lotId AND onHandQuantity >= :qty;
     ```
   - *Amaç:* Çevrimdışı ortamda personelin aynı lotu eldeki stoktan fazla mükerrer satmasını engellemek.

### 3.2 Adım 2: WorkManager ile Sıralı Gönderim (FIFO)

`SalesUploadWorker` ağ bağlantısı olduğunda tetiklenir:
1. `pending_sales` tablosundaki `PENDING` kayıtlar **oluşturma sırasına göre (`createdAt ASC`)** tek tek işlenir.
2. Satış başlığı `SENDING` yapılır ve sunucuya gönderilir:
   ```http
   POST /api/v1/sales
   Idempotency-Key: 3fa85f64-5717-4562-b3fc-2c963f66afa6
   Authorization: Bearer <access_token>
   Content-Type: application/json

   {
     "customer_id": 1,
     "sold_at": "2026-10-29T09:15:00Z",
     "lines": [
       { "lot_id": 145, "quantity": "10.000" }
     ]
   }
   ```
   *(Not: SALES rolü fiyat düzenleyemez; satırda `unit_price` gönderilmez, sunucudaki geçerli liste fiyatı uygulanır.)*

### 3.3 Adım 3: Sunucu Yanıtı ve Durum Eşlemesi

| HTTP Kodu | Sunucu Durumu / Hata | Android Davranışı | Açıklama |
|---|---|---|---|
| **201 Created** | Başarılı yeni satış | `status = SYNCED` | Sunucu `sale_code`, `serverSaleId` ve satır başına dönen `stock_movement_id` kaydedilir. |
| **200 / 201** | Aynı `Idempotency-Key` tekrarı | `status = SYNCED` | Daha önce işlenmiş satışın sonucu alınır; **çift kayıt oluşmaz**. |
| **409 Conflict** | `LOT_BLOCKED` | `status = REJECTED` | Lot geri çağrılmıştır/bloke edilmiştir. Satış reddedilir, kullanıcıya açık mesaj gösterilir. |
| **409 Conflict** | `INSUFFICIENT_STOCK` | `status = REJECTED` | Başka kanaldan stok tükenmiştir. Kullanıcı miktarı düzenleyebilir veya satışı silebilir. |
| **409 Conflict** | `IDEMPOTENCY_KEY_REUSED` | `status = REJECTED` | Aynı anahtar farklı içerikle gönderilmiştir. |
| **400 / 403 / 404** | Kalıcı doğrulama hatası | `status = REJECTED` | Hata mesajı kaydedilir; otomatik tekrar denenmez. |
| **401 Unauthorized** | Token süresi doldu | Yenile ve Tekrarla | `TokenAuthenticator` tek seferlik `POST /auth/refresh` yapar, isteği yineler. |
| **429 / 5xx / Timeout** | Ağ kesintisi veya geçici hata | `status = PENDING` | Durum `PENDING` olarak kalır, **aynı Idempotency-Key ile** üstel geri çekilerek (exponential backoff) tekrar denenir. |

### 3.4 Adım 4: Uzlaştırma (Reconciliation)

Her yükleme turunun ardından `CatalogRepository.syncCatalog()` otomatik tetiklenir. Böylece yerelde yapılan iyimser düşümler, MySQL'deki gerçek stok bakiyesiyle kesin olarak eşitlenir.

---

## 4. Kritik Tutarlılık ve Güvenlik Güvenceleri

1. **Mükerrer Satışın Önlenmesi (Idempotency):**
   - Mobil istemci tarafında üretilen UUID kalıcı olarak saklanır.
   - MySQL tarafında `idempotency_keys` tablosunda hash ve yanıt önbelleği tutulur.
   - Ağ kesintisinde telefon aynı isteği 10 kez tekrarlasa dahi sunucuda **yalnızca 1 adet satış ve 1 adet stok çıkışı** oluşur.

2. **Geri Çağrılan (Recall) Lotun Korunması:**
   - Senkronize olmuş telefonda bloke lot listeden çıkar veya kırmızı rozetle engellenir.
   - Telefon çevrimdışıyken eski önbellekle satış yapılsa dahi sunucu `409 LOT_BLOCKED` ile işlemi reddeder ve stok çıkışı yapmaz.

3. **Veri Kaybının Önlenmesi:**
   - Reddedilen (`REJECTED`) bir satış asla sessizce silinmez. Kullanıcı Satış Geçmişi ekranında hata sebebini görür; "Düzenle ve Yeniden Gönder" (yeni UUID ile) veya "Kuyruktan Sil" seçeneklerine sahiptir.
   - Kullanıcı oturumu kapatsa dahi bekleyen satışlar Room veritabanında silinmeden korunur; bir sonraki girişte gönderilmeye devam eder.

4. **Sayısal Hassasiyet:**
   - Tüm tutar ve miktarlar `BigDecimal` ile yönetilir; binary floating point (`Double`) kesinlikle kullanılmaz.
