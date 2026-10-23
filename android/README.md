# AVATAR Android Satış ve Operasyon Uygulaması — Yol Haritası

Bu belge `android/` klasöründe yapılacak Kotlin uygulamasının kapsamını, mimarisini, çevrimdışı/senkron tasarımını, ekranlarını, iş sırasını ve kabul ölçütlerini tanımlar.
Henüz kod yoktur; bu bir planlama belgesidir. Backend hazırdır ve sözleşmesi `contract/openapi.json` dosyasındadır.

- Gereksinim kaynağı: `AVATAR_Assessment.pdf`.
  - Bölüm 6: "Android satış/operasyon uygulaması: **Kotlin**", "Yerel veri saklama: **SQLite**", "Merkezi veri saklama: **MySQL**".
  - Bölüm 6: "SQLite ve MySQL arasında tutarlı senkronizasyon yaklaşımı açıklanmalıdır."
  - Görev 2: "Oluşan ürünler lot bazında stoklanır ve Kotlin Android satış uygulamasından satılır."
  - Görev 3: "Kotlin satış uygulamasında her satış satırının lotu, miktarı ve ilgili stok hareketi saklanır; geri çağrılan lotların satışı engellenir."
  - Değerlendirme odağı: "**kullanılabilir Kotlin uygulaması**".
- Kararlar: `docs/SOZLESME.md`. API özeti: `docs/API.md`. Şema ayrıntısı: `contract/openapi.json`.
- Teslim son günü: 2026-11-01 23:59.

## 1. Amaç ve kapsam

Saha satış personelinin (rol `SALES`) ve depodaki operatörün (rol `OPERATOR`) kullandığı mobil uygulamadır. Ana iş: **lotlu stoktan, geçerli fiyatla, güvenli ve tekrar edilebilir (idempotent) satış yapmak; geri çağrılan veya bloke lotu satmamak; bağlantı kesilse de çalışmak.**

Uygulamanın ispatlaması gerekenler:

1. Satış her satırda **lot, miktar, fiyat** saklar ve sunucuda ilgili stok hareketine bağlanır.
2. Geri çağrılan/bloke lot ekranda satılamaz görünür, zorlanırsa sunucu da reddeder (`409 LOT_BLOCKED`).
3. Çevrimdışı alınan satış kaybolmaz, **çift kayıt oluşturmaz**, bağlantı gelince doğru sonuçla kapanır.
4. SQLite (Room) ↔ MySQL senkronizasyonu açıklanmıştır ve test edilmiştir (bölüm 5).

Kapsam dışı (bilerek): kullanıcı kaydı, ödeme/fiş yazdırma, fiyat yönetimi, raporlama (web'dedir), bildirim (push), tablet düzeni.

Kapsam kademeleri:

- **P0 (zorunlu):** giriş, katalog/stok senkronu, satış akışı, çevrimdışı kuyruk, bloke lot engeli, satış geçmişi.
- **P1:** lot detayı ve mini izlenebilirlik, recall uyarı listesi, ayarlar.
- **P2 (zaman kalırsa):** operatör işleri: lot kabulü, depo transferi, barkod/QR ile lot okutma.

## 2. Teknik kararlar

| Konu | Karar | Gerekçe |
|---|---|---|
| Dil / arayüz | Kotlin, Jetpack Compose, Material 3 | PDF "Kotlin" ister; Compose hızlı ekran üretir. |
| Min / hedef SDK | minSdk 26, targetSdk güncel kararlı | Java 8 zaman API'si ve güvenli depolama için yeterli. |
| Mimari | MVVM + tek yönlü veri akışı; `ui` / `domain` / `data` katmanları; **Room tek doğruluk kaynağı** (arayüz yalnızca Room'u gözlemler) | Çevrimdışı çalışmanın temeli. |
| Yerel veritabanı | Room (SQLite) | PDF "SQLite" ister; Room SQLite üstündedir. |
| Ağ | Retrofit + OkHttp + `kotlinx.serialization` | Yalın, yaygın. |
| Bağımlılık enjeksiyonu | Hilt | Standart; test değiştirme kolaylığı. |
| Arka plan işi | WorkManager (ağ bağlıyken tek seferlik + periyodik) | Satış kuyruğu ve senkron güvenilir şekilde çalışır. |
| Güvenli depolama | `EncryptedSharedPreferences` (token'lar) | Yenileme token'ı düz dosyada tutulmaz. |
| Para/miktar | `java.math.BigDecimal`; Room'da **TEXT** olarak tutulur | API para ve miktarı string döner; `Double` kullanılmaz. |
| DTO'lar | Yalnızca kullanılan ~15 uç nokta için elle yazılır; sözleşme testi ile doğrulanır | Tam kod üretimi kurulum maliyeti getirir. |
| Test | JUnit5/Kotlin test, Room in-memory, MockWebServer, Compose UI testleri, tek cihaz üstü senaryo | Bkz. bölüm 8. |

### Paket yapısı (hedef)

```
android/app/src/main/java/.../avatar/
  data/
    local/        Room: AppDatabase, entity'ler, DAO'lar
    remote/       Retrofit servisleri, DTO'lar, hata çözümleyici, token yenileme (Authenticator)
    repository/   CatalogRepository, SalesRepository, AuthRepository
    sync/         SyncManager, SalesUploadWorker, CatalogSyncWorker
  domain/         SaleDraft, doğrulama kuralları (bloke lot, stok, fiyat)
  ui/             login, home, catalog, sale, history, lot, settings
  di/
```

## 3. Backend ile çalışma kuralları (herkesin bilmesi gerekenler)

Web README'sindeki bölüm 3 ile aynıdır; mobil için özet ve farklar:

1. **Adres:** emülatörde `http://10.0.2.2:8000/api/v1`. Backend yalnızca `127.0.0.1`'e bağlıdır; **fiziksel telefon** bağlanamaz. Fiziksel cihaz için: backend `docker-compose.yml` içinde API portunu LAN'a açmak (yalnızca demo ağında) veya `adb reverse tcp:8000 tcp:8000`. Önerilen: `adb reverse` (backend'i ağa açmaz). Üretim derlemesinde düz HTTP yasaktır; yalnızca debug derlemesinde `network_security_config` ile `10.0.2.2` ve `localhost` için izin verilir.
2. **Kimlik:** `POST /auth/login` → access (15 dk) + refresh (7 gün, **her kullanımda döner**). OkHttp `Authenticator` ile `401` → tek seferlik yenileme → isteği tekrarla. Yenileme istekleri tek uçuşlu kilitle serileştirilir; aksi halde eşzamanlı `401`'ler aynı token'ı iki kez kullanıp oturum ailesini iptal ettirir. Yenileme de `401` verirse oturum kapatılır (veri silinmez, bekleyen satışlar korunur; yeniden girişte gönderilir).
3. **Hata zarfı:** `{ "error": {"code","message","details"}, "request_id": ... }`. Kod → kullanıcı mesajı eşlemesi yapılır.
4. **Para/miktar JSON string** (`"24.00"`). `BigDecimal`; gösterim 2 hane, miktar 3 hane.
5. **Zaman:** UTC ISO-8601 `Z`; `java.time.Instant`.
6. **Idempotency-Key:** `POST /sales` için **zorunlu**. Anahtar, satış yerelde **oluşturulurken** üretilen UUID'dir ve satırla birlikte kalıcı saklanır; her yeniden denemede **aynı** anahtar gider. Aynı anahtar + aynı gövde ilk sonucu döner (çift kayıt yok); aynı anahtar + farklı gövde `409 IDEMPOTENCY_KEY_REUSED`.
7. **Maliyet alanları** (`unit_cost`, EKP…) SALES rolüne **hiç gelmez**. DTO'larda yok sayılır/opsiyoneldir; uygulama alış maliyetini göstermez ve saklamaz.
8. **Satış fiyatı sunucudadır.** `sellable_lots[].sale_price` ürünün geçerli liste fiyatıdır. Satır isteğinde `unit_price` **gönderilmez** (sunucu liste fiyatını uygular). Farklı fiyat göndermek `sales:override_price` yetkisi ve gerekçe ister; SALES rolünde bu yetki yoktur. Uygulamada fiyat düzenleme **olmayacaktır**.
9. **Satış, sevkiyatı da kapsar:** `POST /sales` bir sevkiyat oluşturur ve aynı işlemde sevk eder (stok çıkışının tek sahibi sevkiyattır). Kısmi başarı yoktur: ya satış + stok hareketi birlikte oluşur ya hiçbiri.
10. **Hız sınırı:** giriş için `429 RATE_LIMITED`; kullanıcıya bekleme gösterilir.

Demo hesabı: `sales@avatar.demo` (parola `backend/README.md`). Kapsam ve izinler: SALES yalnızca `catalog:read`, `inventory:read`, `lots:read`, `sales:create/read`, `shipments:read/manage`, `reports:read`.

## 4. Veri modeli (Room / SQLite)

Sunucu doğruluk kaynağıdır; yerel veritabanı **önbellek + bekleyen işlem kuyruğu**dur.

| Tablo | Amaç | Kaynak / not |
|---|---|---|
| `product` | Ürün kartı: id, kod, ad, birim, tür | `sync/catalog` → `products` (artımlı) |
| `customer` | Müşteri/market: id, kod, ad, telefon | `sync/catalog` → `customers` (artımlı) |
| `sellable_lot` | Satılabilir lotlar: `id`, `lot_code`, `product_id`/`product_code`/`product_name`, **`on_hand_quantity`**, `unit_code`, `expiry_date`, `location_code`, `sale_price` (liste fiyatı) | `sellable_lots` (**her senkronda tam yenilenir**) |
| `blocked_lot` | Bloke lot kimlikleri | `blocked_lot_ids` (tam yenilenir) |
| `pending_sale` | Bekleyen/geçmiş satış başlığı: `client_uuid` (= Idempotency-Key), müşteri, oluşturma zamanı, durum, sunucu `sale_code`, hata kodu/mesajı, deneme sayısı | Yerel |
| `pending_sale_line` | Satır: lot_id, lot kodu (gösterim için kopya), miktar, liste fiyatı kopyası, sunucudan dönen `stock_movement_id` (satır başına stok hareketi, PDF gereği) | Yerel + `POST /sales` yanıtı |
| `sync_state` | `last_server_time`, son başarılı senkron zamanı | Yerel |
| `auth` (şifreli depo) | access/refresh token, kullanıcı, izinler | EncryptedSharedPreferences |

Satış durumları: `DRAFT` → `PENDING` (kuyrukta) → `SENDING` → `SYNCED` | `REJECTED` (kalıcı hata; elle düzeltilir veya silinir).

Kurallar:
- Lot kodu ve ad gibi gösterim bilgileri satırda **kopyalanır**; böylece lot önbellekten düşse bile geçmiş ekranı çalışır.
- Para/miktar TEXT + `BigDecimal` `TypeConverter`.
- Room şema dışa aktarımı (`exportSchema = true`) ve migration testi.
- Şifre/refresh token ve ham yanıtlar log'a yazılmaz.

## 5. Senkronizasyon tasarımı (PDF'in istediği açıklama)

Prensip: **Sunucu (MySQL) tek doğruluk kaynağıdır; telefon (SQLite) okuma önbelleği ve yazma kuyruğudur.** İki yönlü birleştirme (merge) yapılmaz; çakışmayı sunucu çözer.

### 5.1 Aşağı yönlü (sunucu → telefon): `GET /sync/catalog`
- İstek: `?updated_after=<sync_state.last_server_time>` (ilk açılışta parametresiz).
- Yanıt: `server_time`, `products[]` ve `customers[]` (yalnızca değişenler), `sellable_lots[]` (**stokta olan ve bloke olmayan tüm lotlar**, `sale_price` ile), `blocked_lot_ids[]` (**tüm bloke lotlar**).
- Uygulama:
  1. Tek Room işleminde ürün/müşteri upsert eder.
  2. `sellable_lot` ve `blocked_lot` tablolarını **tamamen değiştirir** (silinmiş/bloke olmuş lot anında kaybolur).
  3. Başarı sonrası `last_server_time = yanıt.server_time` yazılır (cihaz saati kullanılmaz; saat sapması riski yok).
- Tetikleyiciler: giriş, uygulama ön plana gelişi, satış ekranı açılışı (stok tazeliği için), elle yenile, WorkManager periyodik (15 dk, ağ bağlıyken).
- Gösterge: "Son senkron: 14:32" ve bayat uyarısı (örn. 30 dk üzeri çevrimdışı ise "stok bilgisi eski olabilir").

### 5.2 Yukarı yönlü (telefon → sunucu): satış kuyruğu
1. Kullanıcı satışı onaylar → tek Room işleminde `pending_sale` + satırlar yazılır, yerel `sellable_lot.on_hand` düşülür (**iyimser düşüm**: aynı lot çevrimdışıyken iki kez fazla satılmasın).
2. `SalesUploadWorker` (ağ bağlıyken): `PENDING` kayıtları **oluşturma sırasıyla** tek tek `POST /sales` ile gönderir; başlık `Idempotency-Key: <client_uuid>`.
3. Sonuç eşlemesi:

| Sunucu yanıtı | Anlamı | Uygulama davranışı |
|---|---|---|
| `201` | Satış kaydedildi | `SYNCED`, `sale_code` yazılır |
| `200`/`201` + aynı anahtarın tekrarı | Daha önce işlenmiş | `SYNCED` (çift kayıt yok) |
| Zaman aşımı / bağlantı kopması / `5xx` / `429` | Sonuç belirsiz veya geçici | `PENDING`'e dön, **aynı anahtarla** üstel geri çekilmeyle yeniden dene |
| `401` | Token süresi doldu | Yenile, tekrarla; yenileme de başarısızsa kuyruk bekler, girişten sonra devam eder |
| `409 LOT_BLOCKED` | Lot geri çağrılmış/bloke | `REJECTED`, kullanıcıya açık mesaj, lot önbellekten çıkarılır |
| `409 INSUFFICIENT_STOCK` | Stok yetersiz (başka kanaldan satıldı) | `REJECTED`, "Stok yetersiz, miktarı düzenleyin" |
| `400 VALIDATION_ERROR`, `404`, `403` | Kalıcı hata | `REJECTED`, ayrıntı gösterilir, otomatik tekrar yok |
| `409 IDEMPOTENCY_KEY_REUSED` | İstemci hatası | `REJECTED`, kayıt hata olarak raporlanır (olmaması gerekir) |

4. `REJECTED` bir satış otomatik silinmez; kullanıcı "Düzenle ve yeniden gönder" (yeni `client_uuid` üretilir) veya "Sil" der. Böylece veri kaybı sessizce olmaz.
5. Her kuyruk işlemi sonrası katalog senkronu tetiklenir; iyimser düşümler sunucudaki gerçek bakiye ile düzelir.

### 5.3 Tutarlılık güvenceleri
- **Çift satış yok:** istemci tarafı UUID idempotency anahtarı + sunucu tarafı benzersiz anahtar kaydı.
- **Aşırı satış yok:** son söz sunucudadır (satır kilitleri ve negatif stok engeli); yerel kontrol yalnızca kullanıcı deneyimidir.
- **Geri çağrılan lot satılmaz:** yerel `blocked_lot` ile ekranda engellenir; çevrimdışı iken geri çağırma gelmişse sunucu yine `409 LOT_BLOCKED` ile reddeder ve kullanıcı bunu görür.
- **Sıra:** kuyruk FIFO'dur; bir satışın kalıcı hatası diğerlerini bloke etmez, geçici hatası aynı kaydı bekletir ve geri çekilir.
- **Saat:** sunucu zamanı `server_time` ile alınır; satış zamanı (`sold_at`) isteğe cihaz saatiyle eklenir ancak kayıt zamanı sunucuda belirlenir.
- **Kesinti dayanıklılığı:** uygulama satış sırasında kapanırsa işlem Room'da ya vardır ya yoktur (tek transaction).

Bu bölüm PDF'in "tutarlı senkronizasyon yaklaşımı açıklanmalıdır" maddesinin cevabıdır; `docs/` altına tek sayfalık bir `SENKRON.md` olarak da kopyalanacaktır.

## 6. Ekranlar

### 6.1 Giriş (P0)
E-posta/parola, hata ve hız sınırı mesajı, oturumu şifreli sakla, "oturum açık kal". Sunucu adresi ayarlardan değiştirilebilir (debug).

### 6.2 Ana ekran (P0)
- Üstte bağlantı/senkron durumu: çevrimiçi/çevrimdışı, son senkron zamanı, bekleyen satış sayısı (rozet), "Şimdi senkronla".
- Kısayollar: Yeni satış, Stok, Satış geçmişi, (P1) Uyarılar.
- Bekleyen ve reddedilen satış sayıları.

### 6.3 Stok / katalog (P0)
- Satılabilir lot listesi (`sellable_lot`): ürün adı, lot kodu, eldeki miktar, birim, liste fiyatı, son tüketim (yaklaşıyorsa vurgu). Arama (ürün/lot kodu).
- Bloke lotlar ayrı sekmede **kırmızı rozetle** ("Geri çağrıldı/bloke — satılamaz").
- Lot detayına git (P1).

### 6.4 Yeni satış (P0)
1. Müşteri/market seç (aranabilir liste).
2. Ürün/lot ekle: lot seçilir (veya P2: QR/barkod), miktar girilir; birim ve liste fiyatı görünür, satır tutarı hesaplanır. **Fiyat düzenlenemez.**
3. Satır doğrulamaları (anında): miktar > 0; miktar ≤ yerel eldeki miktar; lot bloke değil; aynı lot ikinci kez eklenirse birleştirilir.
4. Özet: satırlar, toplam, müşteri. "Satışı tamamla".
5. Çevrimiçiyse hemen gönderilir ve sonuç gösterilir (`sale_code`); çevrimdışıysa "Kuyruğa alındı, bağlantı gelince gönderilecek" mesajı çıkar.
- Çift dokunmaya karşı düğme kilidi. İşlem sırasında geri tuşu onay ister.

### 6.5 Satış geçmişi (P0)
- Yerel kayıtlar: durum rozeti (Bekliyor / Gönderiliyor / Kaydedildi / Reddedildi), müşteri, tutar, zaman, `sale_code`.
- Satır detayı: **lot, miktar, fiyat ve `stock_movement_id`** (PDF: "her satış satırının lotu, miktarı ve ilgili stok hareketi saklanır"). Sunucuya kaydedilmiş satırlar için `GET /sales/{id}` ile bu bilgi yenilenir.
- `REJECTED` satışlar için sebep, "Düzenle ve yeniden gönder", "Sil".

### 6.6 Lot detayı ve mini izlenebilirlik (P1)
- Lot bilgisi (`GET /lots/by-code/{kod}`), ileri/geri izleme özeti (`traceability:read` yoksa gizli; SALES rolünde yok, bu ekran yalnızca OPERATOR/VIEWER için).
- Bloke ise sebep ve recall kodu.

### 6.7 Uyarılar / geri çağırma listesi (P1)
- SALES rolünde yalnızca yerel `blocked_lot` bilgisi vardır (`recalls:read` yetkisi yok): bloke lot kodları ve "satılamaz" uyarısı. OPERATOR/VIEWER için ek olarak `GET /recalls` ile aktif recall'lar, etkilenen lot kodları ve nedeni gösterilir.

### 6.8 Ayarlar (P1)
Sunucu adresi (debug), hesap bilgisi, çıkış (bekleyen satış varsa uyarı: "Çıkış yaparsanız gönderilmemiş satışlar kaybolabilir; önce senkronlayın" — **çıkış bekleyen satışları silmez**, yalnızca oturumu kapatır; yeniden girişte kuyruk devam eder).

### 6.9 Operasyon işleri (P2)
- **Lot kabulü** (`POST /lots/receipts`, `lots:receive`): ürün, tedarikçi, lot no, miktar, birim, son tüketim; maliyet alanı yalnızca `costs:read` varsa görünür.
- **Depo transferi** (`POST /inventory/transfers`, `inventory:adjust`).
- Barkod/QR ile lot okutma (CameraX + ML Kit); lot kodu metin olarak aranabilir olduğundan P2'dir.
- Bu işler çevrimiçi çalışır (kuyruğa alınmaz); çevrimdışıyken devre dışı ve nedeni gösterilir.

## 7. İş sırası ve takvim (4–5 gün, 1 kişi)

| Gün | Çıktı | Kabul |
|---|---|---|
| 1 | Gradle projesi, Hilt, Compose navigasyon, Room şeması + DAO'lar, Retrofit servisleri/DTO'lar, `AuthRepository` + Authenticator (token yenileme), giriş ekranı | Emülatörden `sales@avatar.demo` ile giriş; `401`'de sessiz yenileme çalışır (MockWebServer testi) |
| 2 | `CatalogSyncWorker` + `GET /sync/catalog` artımlı senkron, stok listesi, bloke sekmesi, ana ekran durum şeridi | Telefon uçak modunda bile stok listesi açılır; bloke lot rozetle görünür |
| 3 | Yeni satış ekranı, doğrulamalar, `pending_sale` kuyruğu, iyimser stok düşümü, `SalesUploadWorker` (idempotent, geri çekilmeli), satış geçmişi | Çevrimdışı satış alınır; bağlantı gelince **tek** kayıt oluşur |
| 4 | Hata eşlemeleri (`LOT_BLOCKED`, `INSUFFICIENT_STOCK`, reddedilen satış akışı), lot detayı, uyarı listesi, ayarlar, uçtan uca senaryo | ET-2026 senaryosu: recall sonrası bloke lot satılamaz; sunucu da reddeder |
| 5 | P2 (lot kabulü/transfer, QR) veya cila, testler, `SENKRON.md`, README, ekran görüntüleri/GIF | Bölüm 9'daki demo betiği hatasız; testler geçer |

Web ile paralel çalışılacaksa Android'in **1–4. günleri** öncelikli, P2 kesilebilir.

## 8. Test stratejisi

- **Birim:** `BigDecimal` toplam/yuvarlama, satış doğrulama kuralları (bloke lot, miktar > stok, aynı lot birleştirme), hata kodu → mesaj eşlemesi.
- **Room:** in-memory DB ile DAO testleri; senkronun lotları **tam değiştirdiği** ve ürün/müşteriyi **artımlı** güncellediği; migration testi.
- **Ağ (MockWebServer):**
  - Eşzamanlı üç `401` → tek `refresh` isteği.
  - `POST /sales` zaman aşımı → aynı `Idempotency-Key` ile tekrar → çift satış oluşmaz.
  - `409 LOT_BLOCKED` ve `409 INSUFFICIENT_STOCK` → `REJECTED` ve doğru mesaj.
  - `5xx` → geri çekilmeyle yeniden deneme, kalıcı hata yok.
- **Sözleşme:** DTO'ların `contract/openapi.json` alanlarıyla uyumunu doğrulayan test (zorunlu alanlar mevcut, para/miktar string).
- **UI (Compose test):** satış akışı, bloke lot satırının eklenememesi, çevrimdışı rozeti.
- **Uçtan uca (elle, cihaz/emülatör + seed'li backend):** bölüm 9 betiği.
- Kabul listesi: `docs/handoff/ACCEPTANCE_CRITERIA.md` Bölüm G, H maddeleri ve Android senkron tasarımı.

## 9. Demo betiği (Android tarafı)

1. `sales@avatar.demo` ile giriş → katalog senkronu → `SUC-2026-045` (85 paket) stokta, ET-2026-001 türevi.
2. Market A'ya 10 paket sat → `sale_code` görünür, satış satırında lot `SUC-2026-045`, miktar 10, fiyat 24,00 €. Geçmişte stok hareketi bilgisi.
3. Uçak modu → Market B'ye 5 paket sat → "kuyruğa alındı"; ağı aç → tek kayıt oluşur, durum "Kaydedildi" (ağ kesikken tekrar tekrar dene: çift kayıt yok).
4. Web'den ET-2026-001 için recall'u **aktive et** → telefonda senkron → `SUC-2026-045` bloke rozetli, satılamaz.
5. Telefon çevrimdışıyken (eski önbellekle) aynı lotu satmayı dene → bağlantı gelince `409 LOT_BLOCKED` ile **reddedilir**, kullanıcı sebebi görür.
6. (P2) Operatör hesabıyla lot kabulü.

## 10. Kabul ölçütleri (Android "bitti" tanımı)

- [ ] Giriş, token yenileme ve çıkış çalışır; bekleyen satışlar çıkışta silinmez.
- [ ] Katalog/stok/bloke lot bilgisi Room'a yazılır, çevrimdışı okunabilir.
- [ ] Satış satırı **lot, miktar, fiyat** saklar; sunucuya gidince stok hareketi ile eşleşir.
- [ ] Çevrimdışı satış kuyruğa alınır, bağlantı gelince **tek kez** kaydedilir (idempotency testi geçer).
- [ ] Bloke/geri çağrılan lot ekranda satılamaz; sunucu reddi (`LOT_BLOCKED`) kullanıcıya doğru gösterilir.
- [ ] Para ve miktar hiçbir yerde `Double` değildir; fiyat düzenlenemez.
- [ ] Maliyet alanı saklanmaz/gösterilmez (SALES rolü).
- [ ] `docs/SENKRON.md` yazılmış, bu belgenin bölüm 5'i ile uyumlu.
- [ ] Birim, Room, MockWebServer ve temel UI testleri geçer; derleme uyarısızdır.
- [ ] README'de kurulum, `adb reverse`/emülatör adresi, demo hesabı ve bilinen sınırlamalar bulunur.

## 11. Riskler ve açık sorular

| Risk / soru | Önlem |
|---|---|
| Android Studio / SDK / emülatör kurulu mu? | **İlk iş olarak kontrol edilir** (Gün 1 başında); yoksa kurulum süresi takvime eklenir. |
| Fiziksel telefon API'ye ulaşamaz (`127.0.0.1` bağlama) | `adb reverse` önerilir; gerekirse demo ağında geçici LAN bağlama belgelenir. |
| İyimser stok düşümü sunucu gerçeğinden sapabilir | Her kuyruk işleminden sonra katalog senkronu; `sellable_lot` tam yenilenir. |
| Eşzamanlı yenileme çakışması oturumu düşürebilir | Authenticator'da tek uçuşlu kilit + MockWebServer testi. |
| Düz HTTP (cleartext) güvenliği | Yalnızca debug'ta ve yalnızca `10.0.2.2`/`localhost` için izin; sürümde kapalı. |
| Kapsam şişmesi (QR, transfer) | P2 olarak etiketli; Gün 4 sonunda kalan süreye göre karar verilir. |
| Açık: çevrimdışı lot kabulü gerekli mi? | Önerilen: gerekli değil (operasyon işleri çevrimiçi). Karar bekliyor. |
| Açık: satışta müşteri zorunlu mu? | Backend `customer_id` ister; önerilen: zorunlu, perakende için "Genel müşteri" kaydı seed'e eklenebilir. Karar bekliyor. |

## 12. Çalıştırma (hedef)

```bash
# 1) Backend: backend/README.md  (docker compose up -d; seed_demo)
# 2) Emülatör: uygulama http://10.0.2.2:8000 adresini kullanır.
#    Fiziksel cihaz:  adb reverse tcp:8000 tcp:8000   (uygulama http://127.0.0.1:8000)
cd android
./gradlew :app:assembleDebug
./gradlew :app:testDebugUnitTest :app:connectedDebugAndroidTest
```
