# AVATAR — Üretim, Gerçek Maliyet (EKP), Satış ve Lot İzlenebilirliği

AVATAR Yapay Zekâ Yarışması değerlendirme belgesindeki üç görevi ve iki yapay zekâ modelini kapsayan çalışan bir prototiptir.

| Bileşen | Teknoloji | Klasör |
|---|---|---|
| Merkezi API | Python, FastAPI, SQLAlchemy, Alembic, MySQL 8.4, Redis | `backend/` |
| Web yönetim paneli | React, TypeScript, Vite, Tailwind | `web/` |
| Mobil satış uygulaması | Kotlin, Jetpack Compose, Room (SQLite), Retrofit, WorkManager | `android/` |
| Yapay zekâ (resmî hat) | scikit-learn, backend'e entegre | `backend/app/ml/` |
| API sözleşmesi | OpenAPI 3.1 | `contract/openapi.json` |
| Ek araştırma servisleri (ürüne bağlı değil) | FastAPI, scikit-learn | `ai/Model1`, `ai/Model2` |

## Projenin mantığı

**Görev 1 — Dış hizmetle üretim ve gerçek maliyet (EKP).** Hammadde lotları kabul edilir, üretim emri hammaddeyi tüketir, mamul lotu oluşur. Gerçek birim maliyet = (hammadde + baharat + bağırsak + ambalaj + fason bedeli) / mamul adedi. Referans senaryo: 1.543,50 € / 85 paket = 18,16 €/paket.

**Görev 2 — Bütün kuzu parçalama.** Karkas girişi, parça ve fire çıktıları ağırlık dengesiyle kaydedilir. Toplam maliyet ağırlık oranıyla parçalara dağıtılır; kuruş yuvarlama artığı son satıra eklenir, toplam her zaman girdi maliyetine eşittir. Kaynak belgedeki tutarsızlık (25 kg × 11,50 € = 287,50 € ≠ 351,00 €; parçalar 22 kg) gizlenmez, uyarı olarak kaydedilir.

**Görev 3 — Lot izlenebilirliği ve geri çağırma.** Her lot çoktan çoğa bir şecere grafiğine bağlıdır: `ET-2026-001` → `URT-2026-045` → `SUC-2026-045` (85 paket) → Market A/B/C (30/25/30). Geri çağırma önce simüle edilir, sonra etkinleştirilir. Etkinleşince lot bloke olur ve satışı `409 LOT_BLOCKED` ile reddedilir.

**Stok defteri.** `stock_movements` yalnızca eklemelidir; sevkiyat stok çıkışının tek sahibidir. `POST /sales` ve sevkiyat `Idempotency-Key` ister, aynı istek iki kez stok düşmez.

**Yapay zekâ.** AI-A üretim verimini ve EKP'yi, AI-B parçalama çıktısını tahmin eder. Her model bir baseline ile ve çapraz doğrulama + zaman sıralı holdout ile karşılaştırılır. Eğitim verisi sentetiktir (`is_demo`); sonuçlar yöntemin çalıştığını gösterir, gerçek işletme başarısını değil. ML hiçbir muhasebe veya stok kaydına dokunmaz, yalnızca karar desteği ve anomali uyarısı verir. Ayrıntı: `docs/AI_RAPORU.md`.

**Android ↔ MySQL senkronizasyonu.** Sunucu tek doğruluk kaynağıdır. Android yerel SQLite'ta katalogu önbelleğe alır (`GET /sync/catalog?updated_after=`) ve çevrimdışı satışları kuyruğa yazar. Her satışın kalıcı bir UUID'si vardır ve `Idempotency-Key` olarak gönderilir; ağ kesilirse aynı anahtarla yeniden denenir. İki yönlü birleştirme yapılmaz, çakışmada sunucu kazanır. Ayrıntı: `docs/SENKRON.md`.

**Yetkiler.** Roller: ADMIN, OPERATOR, SALES, TRACEABILITY_MANAGER, VIEWER (varsayılan olarak reddet). Maliyet alanları `costs:read` izni olmayan rollerde gizlenir.

## Çalıştırma

Gereksinimler: Docker Desktop. Android için ayrıca JDK 17+ ve Android SDK.

```powershell
# Tüm sistem: MySQL, Redis, API, web panel ve demo verisi
docker compose up -d --build
```

| Adres | Ne |
|---|---|
| http://localhost:5173 | Web panel |
| http://localhost:8000/api/v1/docs | API dokümantasyonu |
| http://localhost:8000/health/ready | Sağlık |

Demo verisini `demo-seed` servisi yükler. Tüm demo kullanıcılarının parolası `Avatar-Demo-2026!` (yalnızca yerel demo içindir):

| Rol | E-posta |
|---|---|
| Yönetici | `admin@avatar.demo` |
| Operatör | `operator@avatar.demo` |
| Saha satış | `sales@avatar.demo` |
| İzlenebilirlik | `trace@avatar.demo` |
| İzleyici | `viewer@avatar.demo` |

Durdurmak için `docker compose down`. Demo verisini sıfırdan yüklemek için `docker compose down -v && docker compose up -d --build` (veritabanını siler).

**Android.**

```powershell
cd android
.\gradlew.bat assembleDebug        # APK: app/build/outputs/apk/debug/app-debug.apk
.\gradlew.bat testDebugUnitTest
```

Emülatör API'ye `http://10.0.2.2:8000/api/v1/` ile bağlanır. Fiziksel cihazda `adb reverse tcp:8000 tcp:8000`. Düz HTTP yalnızca debug derlemesinde açıktır; release HTTPS ister.

**Backend'i Docker olmadan çalıştırmak.**

```powershell
docker compose up -d mysql
docker compose -f backend/docker-compose.test-redis.yml up -d   # host'tan erişilen Redis, port 16379
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env        # REDIS_URL=redis://:avatar-test-only@localhost:16379/0 yapın, gizli değerleri değiştirin
alembic upgrade head
python -m scripts.seed_demo
uvicorn app.main:app --reload --port 8000
```

**Web'i geliştirme modunda çalıştırmak.** `cd web; npm install; npm run dev`.

## Testler

```powershell
# Backend (MySQL 3307 ve test Redis 16379 gerekir)
docker compose up -d mysql
docker compose -f backend/docker-compose.test-redis.yml up -d
cd backend; .\.venv\Scripts\python.exe -m pytest -q     # 118 test

cd ..\web; npm test; npm run build; npx playwright test  # 11 birim test + 1 uçtan uca
cd ..\android; .\gradlew.bat testDebugUnitTest           # 19 birim test
```

Sonuçlar ve senaryo eşlemesi: `docs/TEST_REPORT.md`.

## Uçtan uca demo

`docker compose up -d --build` sonrası web panelde (`trace@avatar.demo`):

1. **Lot izlenebilirliği** sayfasında `ET-2026-001` aranır: `URT-2026-045` → `SUC-2026-045` (85 paket) → Market A 30, Market B 25, Market C 30.
2. **Geri çağırma** sayfasında `RCL-2026-001` önce simüle edilir, sonra etkinleştirilir; lot bloke olur.
3. Saha satış kullanıcısıyla (`sales@avatar.demo`, Android veya `POST /api/v1/sales`) bloke lot satışı `409 LOT_BLOCKED` ile reddedilir.
4. Yönetici (`admin@avatar.demo`) panelinde EKP (18,16 €/paket), kuzu parçalama maliyet dağılımı ve AI tahminleri görülür.

## Belgeler

| Belge | İçerik |
|---|---|
| `docs/DATA_MODEL.md` | Veri modeli |
| `docs/API.md`, `contract/openapi.json` | API |
| `docs/SENKRON.md` | SQLite ↔ MySQL senkronizasyonu |
| `docs/AI_RAPORU.md` | Yapay zekâ modelleri, baseline'lar, hata metrikleri |
| `docs/TEST_REPORT.md` | Test sonuçları |

## Bilinen sınırlar

- Tüm AI verisi sentetiktir; gerçek işletme doğruluğu iddia edilmez.
- `ai/Model1` ve `ai/Model2` ayrı araştırma servisleridir; backend, web ve Android onları çağırmaz. `ai/Model2`'nin parçalama adayı baseline'ı geçemediği için üretime hazır değildir.
