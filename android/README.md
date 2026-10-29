# AVATAR Android Satış ve Operasyon Uygulaması

Bu klasör, AVATAR Yapay Zekâ Yarışması değerlendirme belgesi gereksinimlerine uygun olarak geliştirilmiş Kotlin, Jetpack Compose, Material 3, Room (SQLite), Retrofit ve WorkManager tabanlı mobil uygulamayı içerir.

---

## 1. Mimari ve Temel İlkeler

- **Dil ve UI:** Kotlin 2.1, Jetpack Compose, Material 3.
- **Yerel Veritabanı:** Room / SQLite (`AppDatabase`).
  - Uygulamanın tek yerel okuma ve bekleyen işlem kuyruğu kaynağıdır.
  - Para ve miktarlar için kesinlikle `Double` kullanılmaz; `BigDecimal` ve Room'da `TEXT` saklanır.
- **Ağ ve API Entegrasyonu:** Retrofit + OkHttp + Kotlinx Serialization.
  - `contract/openapi.json` sözleşmesiyle birebir uyumlu DTO'lar.
  - `TokenAuthenticator`: 401 Unauthorized durumunda tek uçuşlu kilitle (`synchronized`) serileştirilmiş token yenileme (`POST /auth/refresh`).
- **Idempotency & Çift Kayıt Engeli:**
  - Satış oluşturulurken yerelde üretilen UUID `client_uuid` olarak kaydedilir.
  - Sunucuya `Idempotency-Key` başlığıyla gönderilir. Ağ kesintilerinde aynı anahtar ile tekrar denenir.
- **Bloke Lot ve Geri Çağırma (Recall) Koruması:**
  - Hem yerel arayüzde engellenir hem de sunucu `409 LOT_BLOCKED` yanıtı verdiğinde satış `REJECTED` olarak işaretlenir.
- **Stok Hareketi İzlenebilirliği:**
  - Satış satırları `lot_id`, `lot_code`, `quantity`, `unit_price`, `line_total` ve sunucudan dönen `stock_movement_id` değerini kalıcı olarak saklar (PDF kuralı).

---

## 2. Paket Yapısı

```
android/app/src/main/java/com/avatar/app/
├── AvatarApp.kt                     # Application sınıfı, DI ve periyodik senkron planlayıcı
├── MainActivity.kt                  # Ana Compose Shell ve NavHost
├── data/
│   ├── local/
│   │   ├── AppDatabase.kt           # Room veritabanı tanımı
│   │   ├── converter/Converters.kt  # BigDecimal ve Instant dönüştürücüler
│   │   ├── dao/
│   │   │   ├── LotDao.kt            # Satılabilir ve bloke lot işlemleri
│   │   │   ├── ProductCustomerDaos.kt # Ürün ve müşteri işlemleri
│   │   │   └── SaleDaos.kt          # Satış başlık, satır ve senkron durumu
│   │   └── entity/
│   │       ├── LotEntities.kt       # SellableLotEntity, BlockedLotEntity
│   │       ├── ProductCustomerEntities.kt # ProductEntity, CustomerEntity
│   │       └── SaleEntities.kt      # PendingSaleEntity, PendingSaleLineEntity, SyncStateEntity
│   ├── remote/
│   │   ├── api/
│   │   │   ├── ApiClient.kt         # OkHttp, TokenManager, TokenAuthenticator
│   │   │   └── ApiServices.kt       # AuthApi, CatalogApi, SaleApi
│   │   └── dto/Dtos.kt              # OpenAPI uyumlu DTO sınıfları
│   ├── repository/
│   │   ├── CatalogAuthRepositories.kt # AuthRepository, CatalogRepository
│   │   └── SalesRepository.kt       # Satış oluşturma, iyimser düşüm, kuyruk gönderimi
│   └── sync/
│       └── Workers.kt               # SalesUploadWorker, CatalogSyncWorker
├── domain/
│   └── validator/SaleValidator.kt   # Miktar, bloke lot, fiyat ve satır birleştirme kuralları
└── ui/
    ├── screens/
    │   ├── CatalogScreen.kt         # Satılabilir ve bloke lot listeleri
    │   ├── HomeScreen.kt            # Senkron şeridi, göstergeler, hızlı eylemler
    │   ├── LoginScreen.kt           # Giriş ekranı (sales@avatar.demo)
    │   ├── NewSaleScreen.kt         # Müşteri ve lot seçimi, sabit fiyat, hesaplama
    │   ├── SalesHistoryScreen.kt    # Satış durumu, satır detayları, stok hareketi kimliği
    │   └── SettingsScreen.kt        # Sunucu adresi ve güvenli oturum kapatma
    └── theme/Theme.kt               # Material 3 renk paleti ve temalar
```

---

## 3. Senkronizasyon Akışı (SQLite ↔ MySQL)

1. **Aşağı Akış (Sunucu → SQLite):**
   - `GET /sync/catalog?updated_after=<last_server_time>` çağrısı yapılır.
   - Tek Room transaction'ında ürün ve müşteriler artımlı güncellenir.
   - `sellable_lots` ve `blocked_lots` tabloları **tamamen yenilenir** (silinen veya bloke olan lot anında stoktan düşer).
   - `last_server_time` güncellenir.

2. **Yukarı Akış (SQLite → Sunucu):**
   - Kullanıcı satışı onayladığında UUID üretilir, `pending_sales` tablosuna `PENDING` olarak yazılır.
   - Yerel `sellable_lots.on_hand_quantity` alanından **iyimser düşüm** yapılır.
   - `SalesUploadWorker` sırayla `POST /sales` isteği atar (`Idempotency-Key: client_uuid`).
   - Başarılı olursa durum `SYNCED` yapılır, sunucu `sale_code` ve satır başına `stock_movement_id` kaydedilir.
   - Bloke lot veya yetersiz stokta durum `REJECTED` yapılır, kullanıcıya net sebep gösterilir.

---

## 4. Testler ve Derleme

```bash
# Android projesini derleme
cd android
./gradlew :app:assembleDebug

# Birim testlerini çalıştırma (BigDecimal, Validator, Idempotency, Error Mapping)
./gradlew :app:testDebugUnitTest
```

---

## 5. Cihaz ve Ağ Yapılandırması

- **Android Emülatörü:** `http://10.0.2.2:8000/api/v1/` adresini kullanır.
- **Fiziksel Cihaz:** USB ile bağlandıktan sonra `adb reverse tcp:8000 tcp:8000` komutu çalıştırılır; uygulama `http://127.0.0.1:8000/api/v1/` adresine bağlanır.
- **Güvenlik Politikası:** Cleartext (düz HTTP) izni yalnızca debug derlemesinde `10.0.2.2` ve `localhost` için geçerlidir (`network_security_config.xml`). Release sürümünde kapatılmıştır.
- **Demo Kullanıcısı:** `sales@avatar.demo` / `Avatar-Demo-2026!`
