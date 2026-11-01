# AVATAR — Üretim, Gerçek Maliyet (EKP), Satış ve Lot İzlenebilirliği

Dış hizmetle üretimin gerçek maliyetini (EKP) hesaplayan, bütün kuzu parçalamayı kaydeden, hammaddeden markete lot izlenebilirliği ve geri çağırma (recall) sağlayan, Android'den çevrimdışı satış alan bir sistem. İki yapay zekâ modeli (üretim verimi/EKP ve parçalama çıktısı) backend'e entegredir.

Bu belge projeyi sıfırdan çalıştırmak içindir. Tek komutla her şey ayağa kalkar (Bölüm 2). Bileşenleri ayrı ayrı çalıştırmak için ilgili bölüme bakın.

## İçindekiler

1. [Gereksinimler](#1-gereksinimler)
2. [Tek komutla çalıştırma (Docker)](#2-tek-komutla-çalıştırma-docker)
3. [Backend'i Docker'sız çalıştırma](#3-backendi-dockersız-çalıştırma)
4. [Web paneli](#4-web-paneli)
5. [Android uygulaması](#5-android-uygulaması)
6. [Yapay zekâ modelleri](#6-yapay-zekâ-modelleri)
7. [Testler](#7-testler)
8. [Sorun giderme](#8-sorun-giderme)
9. [Klasör yapısı ve belgeler](#9-klasör-yapısı-ve-belgeler)
10. [Projenin mantığı](#10-projenin-mantığı)

## 1. Gereksinimler

| Ne için | Gerekenler |
|---|---|
| Tek komutla çalıştırma | Docker Desktop (Compose v2) |
| Backend'i yerelde çalıştırma | Python 3.12 |
| Web geliştirme | Node.js 20 ve npm |
| Android | JDK 17 ve Android SDK (API 35), ya da Android Studio |

Docker ile çalıştırmak için başka hiçbir şey kurmanız gerekmez.

## 2. Tek komutla çalıştırma (Docker)

Depo kök dizininde:

```powershell
docker compose up -d --build
```

Bu komut MySQL 8.4, Redis, API, web paneli ve demo verisini kurar. İlk derleme birkaç dakika sürer. `demo-seed` servisi veritabanı şemasını oluşturur, demo verisini yükler ve iki yapay zekâ modelini eğitir. İşi bitince kendiliğinden kapanır, bu normaldir. Ortam değişkeni ayarlamanız gerekmez, varsayılanlar yerel kullanım içindir.

| Adres | Ne |
|---|---|
| http://localhost:5173 | Web paneli |
| http://localhost:8000/api/v1/docs | API dokümantasyonu (Swagger) |
| http://localhost:8000/health/ready | Sağlık kontrolü, `{"status":"ok"}` dönmeli |

Hazır olduğunu şöyle doğrulayın:

```powershell
docker compose ps          # mysql, redis, api, web: healthy; demo-seed: Exited (0)
```

**Demo kullanıcıları.** Parola hepsinde `Avatar-Demo-2026!` (yalnızca yerel demo içindir).

| Rol | E-posta | Ne yapabilir |
|---|---|---|
| Yönetici | `admin@avatar.demo` | Her şey, maliyetleri görür |
| Operatör | `operator@avatar.demo` | Üretim, parçalama, stok, maliyetleri görür |
| Saha satış | `sales@avatar.demo` | Satış ve sevkiyat, maliyetleri görmez |
| İzlenebilirlik | `trace@avatar.demo` | Lot izleme, geri çağırma |
| İzleyici | `viewer@avatar.demo` | Salt okunur, maliyetleri görmez |

**Durdurma ve sıfırlama.**

```powershell
docker compose down            # durdurur, veri kalır
docker compose down -v         # veritabanını da siler
docker compose up -d --build   # sıfırdan, temiz demo verisiyle kurar
```

Demo verisi yalnızca `ENVIRONMENT=local` iken yüklenir. Kök dizindeki `.env.example` değiştirilebilir değerleri gösterir.

### 2.1 Demo akışı

Web panelinde `trace@avatar.demo` ile:

1. **Lot izlenebilirliği** sayfasında `ET-2026-001` aranır. Sonuç: `URT-2026-045` → `SUC-2026-045` (85 paket) → Market A 30, Market B 25, Market C 30.
2. **Geri çağırma** sayfasında `RCL-2026-001` önce simüle edilir, sonra etkinleştirilir. Lot bloke olur.
3. `sales@avatar.demo` ile bloke lotu satmak (Android veya `POST /api/v1/sales`) `409 LOT_BLOCKED` ile reddedilir.
4. `admin@avatar.demo` ile üretim, parçalama ve yapay zekâ sayfalarında EKP, maliyet dağılımı ve tahminler görülür.

Demo veritabanını yeniden kullanmak için geri çağırmayı etkinleştirdikten sonra `docker compose down -v` ile sıfırlayın.

## 3. Backend'i Docker'sız çalıştırma

MySQL ve Redis yine Docker'da çalışır, API yerelde.

```powershell
# 1. MySQL (3307) ve host'tan erişilen Redis (16379)
docker compose up -d mysql
docker compose -f backend/docker-compose.test-redis.yml up -d

# 2. Python ortamı
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"

# 3. Ayarlar
Copy-Item .env.example .env         # Linux/macOS: cp .env.example .env
```

`.env` içinde şunları yapın:

- `REDIS_URL=redis://:avatar-test-only@localhost:16379/0` olarak değiştirin.
- `JWT_SECRET_KEY` ve `ML_SIGNING_SECRET` için en az 32 karakterlik, birbirinden farklı değerler girin. Yerelde kısa değerlerle de çalışır, `ENVIRONMENT=local` dışında zorunludur.

```powershell
# 4. Şema, demo verisi ve sunucu
alembic upgrade head
python -m scripts.seed_demo
uvicorn app.main:app --reload --port 8000
```

API http://localhost:8000/api/v1/docs adresinde açılır. Docker yığını çalışıyorsa önce `docker compose stop api web demo-seed` ile durdurun, 8000 portu çakışır.

## 4. Web paneli

Docker yığını web panelini zaten http://localhost:5173 adresinde sunar. Geliştirme modu için:

```powershell
docker compose stop web            # 5173 portunu boşaltır
cd web
npm install
npm run dev                        # http://127.0.0.1:5173
```

Panel API'ye varsayılan olarak `http://127.0.0.1:8000/api/v1` ile bağlanır. Başka adres için `web/.env.example` dosyasını `.env.local` olarak kopyalayıp `VITE_API_BASE_URL` değerini değiştirin.

```powershell
npm test                           # 11 birim test
npm run build                      # üretim derlemesi
npx playwright test                # uçtan uca senaryo (önce npm run dev açık olmalı, Edge gerekir)
npm run typegen                    # ../contract/openapi.json'dan API tiplerini üretir
```

Playwright testi API'yi tarayıcı katmanında taklit eder, backend gerektirmez.

## 5. Android uygulaması

Kotlin, Jetpack Compose, Room (SQLite), Retrofit, WorkManager. Android 8.0 (API 26) ve üstü.

**Önce backend çalışmalı** (Bölüm 2).

```powershell
cd android
.\gradlew.bat assembleDebug         # Linux/macOS: ./gradlew
.\gradlew.bat installDebug          # bağlı cihaza veya açık emülatöre kurar
.\gradlew.bat testDebugUnitTest     # 19 birim test
```

APK: `android/app/build/outputs/apk/debug/app-debug.apk`. Gradle, Android SDK'yı `ANDROID_HOME` ortam değişkeninden ya da `android/local.properties` içindeki `sdk.dir` satırından bulur. Android Studio ile `android/` klasörünü açmak da yeterlidir.

**Sunucu adresi.**

| Nerede çalışıyor | Adres |
|---|---|
| Android emülatörü | `http://10.0.2.2:8000/api/v1/` (varsayılan, ayar gerekmez) |
| USB'li gerçek cihaz | `adb reverse tcp:8000 tcp:8000` çalıştırın, uygulamada `http://127.0.0.1:8000/api/v1/` girin |
| Aynı Wi-Fi'deki gerçek cihaz | `docker-compose.yml` içindeki `127.0.0.1:8000:8000` satırını `8000:8000` yapın, uygulamada `http://<bilgisayar-IP>:8000/api/v1/` girin |

Adres, giriş ekranındaki sunucu düğmesinden veya Ayarlar ekranından değiştirilir ve cihazda saklanır. Düz HTTP yalnızca debug derlemesinde açıktır, release derlemesi HTTPS ister.

**Dene.** `sales@avatar.demo` ile girin, katalogdan bir lot seçip satış oluşturun. Uçak modunda da satış kaydedilir ve kuyruğa girer, bağlantı gelince otomatik gönderilir. Bloke bir lot (`SUC-2026-045`, geri çağırma etkinleştirildikten sonra) satılamaz.

## 6. Yapay zekâ modelleri

### 6.1 Resmî hat: `backend/app/ml`

İki model backend'e entegredir ve ayrıca bir şey çalıştırmak gerekmez, Docker yığını modelleri eğitir.

| Model | Ne tahmin eder | Uç nokta |
|---|---|---|
| AI-A | Üretim verimi ve beklenen EKP | `POST /api/v1/ai/production-yield/predict` |
| AI-B | Parçalama çıktısı (parça başına kg) | `POST /api/v1/ai/butchering-output/predict` |

Diğer uç noktalar: `GET /api/v1/ai/models` (aktif sürümler), `GET /api/v1/ai/predictions` (geçmiş tahminler), `POST /api/v1/ai/models/train` (yeniden eğitim, yönetici yetkisi ister). Hepsi `admin@avatar.demo` ile giriş yapılarak Swagger'dan (`/api/v1/docs`, Authorize düğmesi) denenebilir.

Eğitim verisi sentetiktir. Her model bir baseline ile, çapraz doğrulama ve zaman sıralı holdout ile karşılaştırılır. Sonuçlar `docs/AI_RAPORU.md` içindedir. Raporu yeniden üretmek için (seed edilmiş veritabanı gerekir, dosyanın üzerine yazar):

```powershell
cd backend
python -m scripts.ai_report
```

Model dosyaları HMAC ile imzalanır (`ML_SIGNING_SECRET`), imzası geçersiz dosya yüklenmez.

### 6.2 Ek araştırma servisleri: `ai/Model1`, `ai/Model2`

Ürüne bağlı olmayan, kendi API'sini sunan iki ayrı servis. Backend, web ve Android bunları çağırmaz. Python 3.12 ve `ai/Model1/requirements.txt` gerekir.

```powershell
python -m venv ai/.venv
.\ai\.venv\Scripts\Activate.ps1
pip install -r ai/Model1/requirements.txt
```

**Model1 — sucuk üretimi (TL).** Eğitilmiş model dosyası depoda yoktur, önce eğitilir:

```powershell
cd ai/Model1
$env:PYTHONPATH = ".."
python -m training.train_production           # models/ altına *_candidate.joblib yazar
Copy-Item models/yield_model_candidate.joblib models/yield_model.joblib
Copy-Item models/ekp_model_candidate.joblib   models/ekp_model.joblib
python -m uvicorn app.main:app --port 8001    # http://127.0.0.1:8001/docs
```

**Model2 — karkas parçalama.**

```powershell
cd ai
python -m Model2.training.train_model_b       # sentetik adayı yeniden eğitir
cd Model2
$env:PYTHONPATH = ".."
python -m uvicorn app.main:app --port 8002    # http://127.0.0.1:8002/docs
```

Model2'nin aday modeli baseline'ı geçemediği için üretim uç noktası (`/v1/predict/carcass-cuts`) bilerek `503` döner. Pilot amaçlı `/v1/predict/carcass-cuts/experimental` çalışır ve yanıtı `experimental: true` ile işaretler. Her iki servis de `API_KEY` ortam değişkeni doluysa anahtar ister.

Her iki servis için Docker seçeneği `ai/` klasöründen çalışır:

```powershell
$env:API_KEY = "yerel-test-anahtari"
docker compose -f Model1/docker-compose.yml up -d --build   # 127.0.0.1:8001
docker compose -f Model2/docker-compose.yml up -d --build   # 127.0.0.1:8002
```

Model1'in compose'u model dosyalarını salt okunur bağladığı için önce eğitim adımını yapın.

## 7. Testler

```powershell
# Backend: MySQL (3307) ve Redis (16379) gerekir
docker compose up -d mysql
docker compose -f backend/docker-compose.test-redis.yml up -d
cd backend
python -m pytest -q                       # 118 test, yaklaşık 5 dakika
python -m ruff check app tests scripts

# Web
cd ..\web; npm test; npm run build

# Android
cd ..\android; .\gradlew.bat testDebugUnitTest

# Ek araştırma servisleri
cd ..\ai\Model1; $env:PYTHONPATH = ".."; python -m pytest -q
cd ..\Model2;    $env:PYTHONPATH = "..\Model1;.."; python -m pytest -q tests
```

Backend testleri `avatar_test` veritabanını kendisi oluşturur. Model1'in iki testi, eğitilmiş model dosyası yoksa atlanır. GitHub Actions'ta (`.github/workflows/ci.yml`) backend, web ve Android işleri her push'ta koşar. Sonuçlar `docs/TEST_REPORT.md` içindedir.

## 8. Sorun giderme

| Belirti | Çözüm |
|---|---|
| `port is already allocated` (3307, 8000, 5173) | Portu kullanan başka süreci kapatın. Eski bir `avatar` yığını varsa `docker compose down` |
| `docker compose up` sonrası web boş veya API hata veriyor | `docker compose ps` ile `api` servisinin `healthy` olduğunu kontrol edin, `docker compose logs api` |
| Giriş yapılamıyor, demo kullanıcı yok | `docker compose logs demo-seed` bakın. Temiz başlamak için `docker compose down -v && docker compose up -d --build` |
| Çok fazla yanlış denemeden sonra `429 RATE_LIMITED` | 15 dakika bekleyin |
| Redis çalışmıyorsa girişte `503` | Bilerek böyledir (giriş sınırı kapalı başarısız olur). Redis'i başlatın |
| Backend testleri bağlanamıyor | MySQL ve test Redis konteynerlerinin çalıştığını doğrulayın (Bölüm 7) |
| Android derlemesi SDK bulamıyor | `ANDROID_HOME` ayarlayın veya `android/local.properties` içine `sdk.dir=...` yazın |
| Emülatörde bağlantı hatası | Backend'in 8000'de çalıştığını ve adresin `http://10.0.2.2:8000/api/v1/` olduğunu kontrol edin |
| Gerçek cihazda bağlantı reddedildi | `adb reverse tcp:8000 tcp:8000` veya Bölüm 5'teki Wi-Fi seçeneği |
| `playwright` Edge bulamıyor | Microsoft Edge kurulu olmalı, ya da `web/playwright.config.ts` içinde tarayıcıyı değiştirin |

## 9. Klasör yapısı ve belgeler

```
backend/     FastAPI uygulaması, Alembic migration'ları, testler, seed ve rapor betikleri
  app/ml/    Resmî yapay zekâ modelleri (AI-A, AI-B, anomali)
web/         React + TypeScript yönetim paneli
android/     Kotlin Android uygulaması
ai/          Ek araştırma servisleri (Model1: sucuk/TL, Model2: karkas parçalama)
contract/    OpenAPI sözleşmesi (openapi.json)
scripts/     Model imza anahtarı döndürme ve metrik doğrulama betikleri
docs/        Teslim belgeleri
docker-compose.yml   MySQL, Redis, API, web ve demo verisi
```

| Belge | İçerik |
|---|---|
| `docs/DATA_MODEL.md` | Veri modeli |
| `docs/API.md`, `contract/openapi.json` | API |
| `docs/SENKRON.md` | SQLite ↔ MySQL senkronizasyonu |
| `docs/AI_RAPORU.md` | Yapay zekâ modelleri, baseline'lar, hata metrikleri |
| `docs/TEST_REPORT.md` | Test sonuçları |

## 10. Projenin mantığı

**Görev 1 — Dış hizmetle üretim ve gerçek maliyet (EKP).** Hammadde lotları kabul edilir, üretim emri hammaddeyi tüketir, mamul lotu oluşur. Gerçek birim maliyet = (hammadde + baharat + bağırsak + ambalaj + fason bedeli) / mamul adedi. Referans senaryo: 1.543,50 € / 85 paket = 18,16 €/paket.

**Görev 2 — Bütün kuzu parçalama.** Karkas girişi, parça ve fire çıktıları ağırlık dengesiyle kaydedilir. Toplam maliyet ağırlık oranıyla parçalara dağıtılır. Kuruş yuvarlama artığı son satıra eklenir, toplam her zaman girdi maliyetine eşittir. Kaynak belgedeki tutarsızlık (25 kg × 11,50 € = 287,50 € ≠ 351,00 €, parçalar 22 kg) gizlenmez, uyarı olarak kaydedilir.

**Görev 3 — Lot izlenebilirliği ve geri çağırma.** Her lot çoktan çoğa bir şecere grafiğine bağlıdır: `ET-2026-001` → `URT-2026-045` → `SUC-2026-045` (85 paket) → Market A/B/C (30/25/30). Geri çağırma önce simüle edilir, sonra etkinleştirilir. Etkinleşince lot bloke olur ve satışı `409 LOT_BLOCKED` ile reddedilir.

**Stok defteri.** `stock_movements` yalnızca eklemelidir, sevkiyat stok çıkışının tek sahibidir. `POST /sales` ve sevkiyat `Idempotency-Key` ister, aynı istek iki kez stok düşmez.

**Android ↔ MySQL senkronizasyonu.** Sunucu tek doğruluk kaynağıdır. Android katalogu SQLite'ta önbelleğe alır (`GET /sync/catalog?updated_after=`) ve çevrimdışı satışları kuyruğa yazar. Her satışın kalıcı bir UUID'si vardır ve `Idempotency-Key` olarak gönderilir, ağ kesilirse aynı anahtarla yeniden denenir. İki yönlü birleştirme yapılmaz, çakışmada sunucu kazanır. Ayrıntı: `docs/SENKRON.md`.

**Yetkiler.** Roller: ADMIN, OPERATOR, SALES, TRACEABILITY_MANAGER, VIEWER (varsayılan olarak reddet). Maliyet alanları `costs:read` izni olmayan rollerde gizlenir.

**Yapay zekâ.** AI-A üretim verimini ve EKP'yi, AI-B parçalama çıktısını tahmin eder. Yapay zekâ muhasebe veya stok kaydına dokunmaz, yalnızca karar desteği ve anomali uyarısı verir. Eğitim verisi sentetiktir, sonuçlar yöntemin çalıştığını gösterir, gerçek işletme başarısını değil.

**Bilinen sınırlar.**

- Tüm yapay zekâ verisi sentetiktir, gerçek işletme doğruluğu iddia edilmez.
- `ai/Model1` ve `ai/Model2` ayrı araştırma servisleridir, ürüne bağlı değildir. Model2'nin parçalama adayı baseline'ı geçemediği için üretime hazır değildir.
- Release Android derlemesi HTTPS ister, canlı kullanım için TLS'li bir sunucu gerekir.
