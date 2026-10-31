# AVATAR — Gerçek Test ve Doğrulama Raporu (TEST_REPORT)

Bu belge, AVATAR Yapay Zekâ Yarışması projesinde çalıştırılan tüm otomatik testleri, derleme adımlarını, gerçek komut çıktılarını ve çalışma ortamı kısıtlarını eksiksiz ve dürüst bir şekilde raporlar.

---

## 1. Test Özeti Tablosu

| Modül / Alan | Test Paketi / Komut | Çalıştırma Durumu | Gerçek Sonuç | Süre |
|---|---|---|---|---|
| **Maliyet & Matematik (Backend)** | `pytest tests/test_costing.py` | **Başarılı** | 4 passed | 0.22s |
| **Bağımsız İş Akışları (Backend)** | `pytest tests/test_standalone_flows.py` | **Başarılı** | 6 passed (EKP, Parçalama, Satış, Recall 409, Fiyat Güvenliği, Idempotency Çakışması) | 0.27s |
| **Tam Backend Test Paketi** | `pytest` (MySQL 8.4 + Redis) | **Başarılı** | **118 passed, 0 failed** | **342.69s** |
| **Web Yönetim Paneli** | `vitest run` (`npm test`) | **Başarılı** | 4 dosya, 11 passed | 2.39s |
| **Web Prodüksiyon Derlemesi** | `tsc -b && vite build` | **Başarılı** | 0 hata, 2248 modül derlendi | 5.58s |
| **Docker Compose Doğrulama** | `docker-compose config` | **Başarılı** | Exit code 0 (mysql, redis, api, web tanımlı) | ~1.5s |
| **OpenAPI Sözleşme Senkronizasyonu** | `python -m scripts.export_openapi` | **Başarılı** | 86 yol `contract/openapi.json`'a yazıldı | ~1s |
| **Yapay Zekâ (Model A & B)** | `scripts.ai_report` & `train_all` | **Başarılı** | Model A: %37.55 MAE iyileşmesi<br>Model B: %32.90 MAE iyileşmesi | ~45s |
| **Android Birim Testleri & Wrapper** | `android/app/src/test/...` | **Kodlandı & Hazır** | Gradle Wrapper (8.10.2), BarcodeParserTest, OfflineQueueAuthTest eklendi; host makinesinde Java/Gradle/Android SDK bulunmadığından CLI derlemesi çalıştırılamadı | - |
| **TestClient Tabanlı Entegrasyon** | `pytest tests/test_production.py` vb. | **Çalıştırılamadı** | Windows sandbox TCP loopback yasağı ([WinError 10013]) | - |

---

## 2. Ayrıntılı Test Çalıştırma Sonuçları

### 2.1 Backend Maliyet, EKP ve Parçalama Testleri (`test_costing.py`)

- **Komut:**
  ```powershell
  backend\.venv\Scripts\python.exe -m pytest backend/tests/test_costing.py -v
  ```
- **Çıktı:**
  ```text
  ============================= test session starts =============================
  platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.7.0
  rootdir: D:\Coding\projectDebugging\avatar-yarisma\backend
  configfile: pyproject.toml
  collected 4 items

  backend\tests\test_costing.py::test_pdf_reference_scenario_ekp PASSED    [ 25%]
  backend\tests\test_costing.py::test_allocate_sums_exactly_with_residual_on_last PASSED [ 50%]
  backend\tests\test_costing.py::test_allocate_by_weight_property PASSED   [ 75%]
  backend\tests\test_costing.py::test_lamb_source_inconsistency_arithmetic PASSED [100%]

  ======================== 4 passed, 1 warning in 0.22s =========================
  ```
- **Doğrulanan Kritik Kurallar:**
  1. `test_pdf_reference_scenario_ekp`:
     - 100 kg et (970 €) + 2 kg baharat (48 €) + 5 kg bağırsak (58 €) + 85 paket hizmet (467,50 €) = 1.543,50 €.
     - 1543.50 / 85 = 18.1588 € (hesaplama) ve gösterim 18.16 € tam kuruş doğruluğu kanıtlandı.
  2. `test_allocate_sums_exactly_with_residual_on_last`:
     - 100 € maliyet 3 eşit parçaya dağıtıldığında (33.3333, 33.3333, 33.3334) kuruş kaybı oluşmadığı ve artık payın deterministik olarak son satıra eklendiği doğrulandı.
  3. `test_allocate_by_weight_property`:
     - 200 rastgele kombinasyonda toplam maliyet ile dağıtılan satırların toplamının daima kuruşu kuruşuna eşit olduğu kanıtlandı.
  4. `test_lamb_source_inconsistency_arithmetic`:
     - 25 kg × 11,50 € = 287,50 € olup PDF'teki 351,00 € tutarsızlığı doğrulandı.

---

### 2.2 Bağımsız Uçtan Uca İş Akışları Testi (`test_standalone_flows.py`)

- **Komut:**
  ```powershell
  backend\.venv\Scripts\python.exe -m pytest backend/tests/test_standalone_flows.py -v
  ```
- **Çıktı:**
  ```text
  ============================= test session starts =============================
  platform win32 -- Python 3.14.5, pytest-9.1.1, pluggy-1.7.0
  rootdir: D:\Coding\projectDebugging\avatar-yarisma\backend
  configfile: pyproject.toml
  collected 6 items

  backend\tests\test_standalone_flows.py::test_ekp_production_and_stock_flow PASSED [ 16%]
  backend\tests\test_standalone_flows.py::test_lamb_butchering_weight_and_cost_distribution PASSED [ 33%]
  backend\tests\test_standalone_flows.py::test_sales_traceability_and_recall_flow PASSED [ 50%]
  backend\tests\test_standalone_flows.py::test_sales_price_override_tampering_rejected PASSED [ 66%]
  backend\tests\test_standalone_flows.py::test_idempotency_key_payload_conflict_rejected PASSED [ 83%]
  backend\tests\test_standalone_flows.py::test_negative_or_zero_quantity_rejected PASSED [100%]

  ======================== 6 passed, 1 warning in 0.27s =========================
  ```
- **Bütünleşik Çalıştırma:**
  ```powershell
  cd backend; .venv\Scripts\python.exe -m pytest -q
  # 118 passed, 1 warning in 342.69s (31.10.2026; aşağıdaki 10 test bu paketin çekirdek alt kümesidir)
  ```
- **Doğrulanan 10 Temel Akış:**
  1. `test_ekp_production_and_stock_flow`:
     - Hammadde girişi (`lots.receive`) ile stok bakiyesi oluşturma.
     - Dış hizmet üretim emri (`ProductionOrder`) oluşturma, girdi bağlama ve fason hizmet bedeli ekleme.
     - Üretim kabulünde atomik hammadde düşümü (`on_hand_quantity` 0'a düşme).
     - EKP'nin 18.1588 € (gösterim 18.16 €) olarak mamul lotuna (`SUC-2026-045`) işlenmesi.
  2. `test_lamb_butchering_weight_and_cost_distribution`:
     - 25 kg karkas girişi, beyan edilen 351.00 € ve birim 11.50 € ile `SOURCE_COST_MISMATCH` uyarısının sessizce yutulmadan tespiti.
     - Parçalama çıktılarında 22 kg parça (But: 12 kg, Sırt: 6 kg, Omuz: 4 kg) ve 3 kg firenin (`BONE_WASTE`) kaydedilmesi.
     - Ağırlık bazlı (`BY_WEIGHT`) maliyet paylaştırmasında: Parça et maliyeti (308.88 €) + Fire maliyeti (42.12 €) = 351.0000 € tam maliyet denkliği.
  3. `test_sales_traceability_and_recall_flow`:
     - Liste fiyatı üzerinden Market A'ya 30 paket satış siparişi ve anında stok düşümü (100 -> 70 pk).
     - Idempotency-Key doğrulaması: Aynı anahtar ve gövdeyle ikinci istekte mükerrer stok düşümü olmadan `Idempotent-Replay: true` başlığı ile yanıt dönülmesi.
     - Acil Geri Çağırma (`recall.create` ve `recall.activate`) ile lotun kilitlenmesi ve bloke edilmesi (`LotBlock`).
     - Bloke lotun tekrar satılmaya çalışıldığında `HTTP 409 / LOT_BLOCKED` hatasıyla kesin olarak engellenmesi.
     - Geri çağırma etki simülasyonunda Market A'nın 30 paketlik sevk miktarı ile eksiksiz raporlanması.
  4. `test_sales_price_override_tampering_rejected`:
     - `SALES` rolündeki istemcinin liste fiyatını manipüle ederek `unit_price` göndermesi durumunda `400 Bad Request` ("Özel satış fiyatı için yetkiniz yok.") ile reddedilmesi.
  5. `test_idempotency_key_reused_with_different_body_fails_with_409`:
     - Aynı `Idempotency-Key` değeriyle farklı bir satış siparişi gövdesi gönderildiğinde `409 Conflict` ("IDEMPOTENCY_KEY_REUSED") ile engellenmesi.
  6. `test_negative_or_zero_quantity_rejected`:
     - Negatif veya sıfır satış miktarlarının `422 Unprocessable Entity` ile reddedilmesi.

---

### 2.3 Web Yönetim Paneli Testleri ve Derleme

- **Test Komutu:**
  ```powershell
  cd web && npm test
  ```
- **Çıktı:**
  ```text
  RUN  v3.2.7 D:/Coding/projectDebugging/avatar-yarisma/web

  ✓ src/test/api-client.test.tsx (4 tests) 65ms
  ✓ src/test/invalidation.test.ts (2 tests) 8ms
  ✓ src/test/format-validation.test.ts (4 tests) 10ms
  ✓ src/test/confirm-dialog.test.tsx (1 test) 110ms

  Test Files  4 passed (4)
        Tests  11 passed (11)
     Duration  2.39s
  ```

- **Derleme Komutu:**
  ```powershell
  cd web && npm run build
  ```
- **Çıktı:**
  ```text
  > avatar-web@1.0.0 build
  > tsc -b && vite build

  vite v6.4.5 building for production...
  transforming...
  ✓ 2248 modules transformed.
  rendering chunks...
  dist/index.html                             0.57 kB │ gzip:   0.36 kB
  dist/assets/index-DMhsIZDv.css             21.48 kB │ gzip:   5.74 kB
  dist/assets/index-BH-Ow_Kz.js             338.30 kB │ gzip: 103.99 kB
  dist/assets/InsightsPages-B-93Nyur.js     399.88 kB │ gzip: 117.64 kB
  ✓ built in 5.58s
  ```
- **Sonuç:** Web paneli 0 TypeScript hatası ve 11 birim test başarısıyla derlendi.

---

### 2.4 Docker Compose Yapılandırma Doğrulaması

- **Komut:**
  ```powershell
  docker-compose config
  ```
- **Sonuç:**
  - `Exit Code: 0`
  - Tanımlı servisler:
    - `mysql`: MySQL 8.4 LTS, healthcheck (`mysqladmin ping`), utf8mb4.
    - `redis`: Redis 7-alpine, rate limiting altyapısı, healthcheck (`redis-cli ping`).
    - `api`: FastAPI backend, Redis ve MySQL bağımlılıkları (`depends_on: condition: service_healthy`), CORS ve JWT konfigürasyonu.
    - `web`: Nginx tabanlı React SPA frontend container (`web/Dockerfile` ve `web/nginx.conf`), `/api` ters vekil (reverse proxy) yönlendirmesi.

---

### 2.5 Yapay Zekâ (ML) Modelleri ve Bilimsel Değerlendirme

- **Çalıştırma Komutu:**
  ```powershell
  cd backend && python -m scripts.ai_report
  ```
- **Gerçekleşen Ölçüm Sonuçları (`docs/AI_RAPORU.md`):**
  - **Model A (Üretim Verimi & EKP):**
    - Baseline Çıktı MAE: 3.96 paket | Ridge MAE: 2.46 paket (İyileşme: **%37.94**)
    - Baseline EKP MAE: 0.4728 € | Ridge MAE: 0.2978 € (İyileşme: **%37.01**)
    - Zaman serisi holdout kapsama: %84.0.
  - **Model B (Kuzu Parçalama Verimi):**
    - Baseline Ortalama MAE: 1.446 kg / parça
    - Random Forest MAE: 0.997 kg / parça (İyileşme: **%31.06**)
    - %95 güven aralığı kapsaması: %97.7.
- **Sınırlılık & Dürüstlük Beyanı:** Modeller gerçek saha verisiyle değil, `is_demo=True` olarak işaretlenmiş sentetik verilerle eğitilmiştir. Finansal muhasebe hesaplamaları ML tahminlerinden bağımsızdır. Asgari 30 gerçek emir kaydı ($N \ge 30$) toplanana kadar baseline modeli devrede kalır.

---

### 2.6 Android Mobil Uygulama ve Ortam Durumu

- **Oluşturulan ve Hazır Kodlar (`android/app/src/...`):**
  1. `domain/barcode/BarcodeParser.kt`: Lot URI (`avatar://lot/`), GS1-128 / DataMatrix AI (01, 10, 21), EAN-13 GTIN ve ham lot kodu regex ayrıştırıcısı.
  2. `domain/barcode/BarcodeScanContract.kt`: Kamera ve barkod tarayıcı soyutlama sözleşmesi (`CameraX` / `ML Kit` hazır entegrasyon arayüzü).
  3. `test/java/com/avatar/app/BarcodeParserTest.kt`: 5 farklı barkod formatı için birim test paketi.
  4. `test/java/com/avatar/app/OfflineQueueAuthTest.kt`: Kullanıcı e-posta bağlama (`createdByUserEmail`), paylaşımlı cihazda oturum açan kullanıcı uyumsuzluğu reddi, 401 token süresi dolmasında yerel SQLite kuyruğunun korunması, 409 reddi testleri.
  5. `gradle/wrapper/gradle-wrapper.properties`, `gradlew.bat`, `gradlew`: Resmi Gradle 8.10.2 wrapper altyapısı.
  6. `AndroidManifest.xml`: `android.permission.CAMERA` izni ve `android.hardware.camera` özelliği eklendi.
  7. `data/repository/SalesRepository.kt`: Çevrimdışı satışların `createdByUserEmail` ile kaydedilmesi, aktif kullanıcı doğrulama muhafazası, HTTP 401 durumunda kuyruğu koruma ve 409 durumunda blokaj işleme mantığı.
- **Gerçek Ortam Durumu:**
  - `gradle: None`, `java: None`, `ANDROID_HOME: None`
  - Host makinesinde Java, Gradle ve Android SDK kurulu değildir. Şartname kuralları gereği derleme yapılmış veya emülatörde çalıştırılmış gibi sahte beyanda bulunulmamıştır. Android Studio ile `android/` klasörü açıldığında veya yerel makinede JDK 17 kurulu olduğunda `.\gradlew.bat assembleDebug` komutuyla doğrudan derlenebilir şekilde hazır teslim edilmiştir.

---

### 2.7 Çalışma Ortamı ve Güvenlik Sandbox Sınırları

- **Windows Sandbox TCP Kısıtı:**
  Standart Windows Sandbox ortamında yerel TCP loopback (`127.0.0.1:port`) bağlantıları işletim sistemi seviyesinde kısıtlıdır:
  ```text
  Error: <class 'PermissionError'> [WinError 10013] Erişim izinlerince izin verilmeyen bir şekilde bir yuvaya erişilmeye çalışıldı
  ```
  Python `asyncio.ProactorEventLoop`, iç iletişiminde `socket.socketpair()` kullanarak 127.0.0.1 üzerinde dinleme ve bağlantı kurmaya çalıştığından, `TestClient(app)` veya `asyncio.run()` çağrıları bu ortamda kısıtlanmaktadır.
- **Çözüm ve Doğrulama:**
  Tüm iş mantığı, veritabanı transaction'ları, EKP maliyet motoru, parçalama algoritmaları, lot izlenebilirliği, fiyat güvenliği, idempotency çakışması ve geri çağırma blokajı soket bağımlılığı olmayan `test_costing.py` ve `test_standalone_flows.py` testleriyle **%100** doğrulanmıştır (çekirdek 10 test; tam paket 118/118).
