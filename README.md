# AVATAR — Üretim, Gerçek Maliyet (EKP), Satış ve Lot İzlenebilirliği

AVATAR, et ve et ürünleri üretim süreçlerini; hammadde takibi, fason üretim, gerçek birim maliyet (EKP) hesaplama, karkas parçalama, stok ve satış yönetimi, çok kademeli lot şeceresi ve geri çağırma (recall) operasyonları üzerinden dijitalleştiren kurumsal bir üretim ve izlenebilirlik yazılımıdır.

Proje; React web yönetim paneli, FastAPI REST API, MySQL 8.4 merkezi veritabanı, Redis önbellek/rate-limit katmanı, Kotlin/Jetpack Compose Android saha satış uygulaması ve scikit-learn makine öğrenmesi karar destek servislerinden oluşur.

> [!NOTE]
> **Proje Durumu ve Değerlendirme Beyanı:** Bu doküman kurulum ve değerlendirme rehberidir. Özelliklerin üretime hazır olduğu veya bütün testlerin geçtiği varsayılmamalıdır. Doğrulanmış test sonuçları, gerçek sistem metrikleri ve bilinen sınırlamalar bu dokümanda açıkça sunulmuştur.

---

## İçindekiler
- [1. Proje Hedefleri](#1-proje-hedefleri)
- [2. Teknoloji Yığını ve Mimari](#2-teknoloji-yığını-ve-mimari)
- [3. Gereksinimler](#3-gereksinimler)
- [4. Kurulum ve Çalıştırma](#4-kurulum-ve-çalıştırma)
- [5. Ortam Değişkenleri ve Yapılandırma](#5-ortam-değişkenleri-ve-yapılandırma)
- [6. Demo Kullanıcıları](#6-demo-kullanıcıları)
- [7. Yarışma Senaryoları ve Doğrulama](#7-yarışma-senaryoları-ve-doğrulama)
- [8. Yapay Zekâ Modelleri (Model 1 ve Model 2)](#8-yapay-zekâ-modelleri-model-1-ve-model-2)
- [9. Android Uygulaması ve APK](#9-android-uygulaması-ve-apk)
- [10. Test Komutları ve Gerçek Çıktılar](#10-test-komutları-ve-gerçek-çıktılar)
- [11. API ve Mevcut Teknik Dokümantasyon](#11-api-ve-mevcut-teknik-dokümantasyon)
- [12. Güvenlik ve Bilinen Sınırlamalar](#12-güvenlik-ve-bilinen-sınırlamalar)
- [13. Katkı ve Lisans](#13-katkı-ve-lisans)

---

## 1. Proje Hedefleri

AVATAR sisteminin temel hedefleri şunlardır:
- **Hammadde Kabul ve Stok Takibi:** Hammadde giriş lotlarını, birim alış fiyatlarını ve tedarikçi faturalarını kayıt altına almak.
- **Fason Üretim ve Gerçek EKP:** Dış hizmet faturası, tüketilen hammadde maliyetleri ve ek masrafları birleştirerek sağlam mamul başına kuruşu kuruşuna Gerçek Birim Maliyeti (EKP) hesaplamak.
- **Karkas Parçalama ve Fire Yönetimi:** Bütün hayvan (kuzu/dana) karkas girişinden elde edilen parça ürünleri kaydetmek, fire ve tartım farklılıklarını şeffafça belgelemek (`BY_WEIGHT` yöntemi).
- **Kırılmaz Lot Şeceresi:** Hammadde $\rightarrow$ Üretim Emri $\rightarrow$ Mamul Lotu $\rightarrow$ Sevkiyat $\rightarrow$ Müşteri zincirinde iki yönlü (ileri ve geri) tam izlenebilirlik sağlamak.
- **Geri Çağırma (Recall) ve Fail-Closed Koruma:** Kalite sorunu tespit edilen lotları sistem genelinde kilitlemek; hem Android istemcisinde satışı engellemek hem de sunucu tarafında bloke satışları `409 LOT_BLOCKED` statüsüyle kesin olarak reddetmek.
- **Çevrimdışı Android Saha Satışı:** Ağ kesintilerinde yerel SQLite/Room üzerinde satış yapabilmek, UUID tabanlı `Idempotency-Key` ile mükerrer siparişleri önlemek ve bağlantı sağlandığında sunucuyla senkronize olmak.
- **Yapay Zekâ Karar Desteği:** Üretim verimi ve karkas parçalama çıktıları için geçmiş veriye dayalı öngörüler üretmek; bunu yaparken finansal ve operasyonel muhasebe kayıtlarının yerine asla yapay zekâ tahminlerini geçirmemek.

---

## 2. Teknoloji Yığını ve Mimari

| Bileşen | Teknoloji | Konum | Doğrulanmış Durum |
| :--- | :--- | :--- | :--- |
| **Backend & REST API** | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 | `backend/` | Tam Entegre & 116 Test Geçti |
| **Önbellek & Rate-Limit** | Redis 7.4-alpine (Parola Korumalı, Atomik Token Bucket) | Docker (`redis`) | Çalışıyor (Dahili port 6379) |
| **Web Yönetim Paneli** | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query | `web/` | Tam Entegre & 11/11 Test Geçti |
| **Android Mobil Uygulama** | Kotlin 2.1, Jetpack Compose, Material 3, Room, Retrofit | `android/` | Tam Entegre & Birim Testleri Geçti |
| **Merkezi Veritabanı** | MySQL 8.4 (InnoDB, UTF8mb4, Tek Doğruluk Kaynağı) | `database/` | Port 3307 (Local), Şema & Seed Hazır |
| **API Sözleşmesi** | OpenAPI 3.1 Şeması | `contract/openapi.json` | Birebir Uyumlu |
| **Yapay Zekâ Modelleri** | Python, scikit-learn, pandas, joblib, HMAC-SHA256 | `backend/app/ml/`, `ai/` | Model 1 Canlı; Model 2 Pilot (Fail-Closed) |
| **Dağıtım & Orkestrasyon**| Docker Desktop, Docker Compose v2 | `docker-compose.yml` | Tek Komutla Başlatılabilir |

### Temel Sistem Mimarisi
```text
┌────────────────────────┐         ┌────────────────────────┐
│   Web Yönetim Paneli   │         │   Android Uygulaması   │
│ (React + Vite, :5173)  │         │ (Kotlin, Room SQLite)  │
└───────────┬────────────┘         └───────────┬────────────┘
            │                                  │
            │ HTTP / JSON                      │ HTTP / JSON (Idempotency-Key)
            ▼                                  ▼
┌───────────────────────────────────────────────────────────┐
│               FastAPI Backend (Port :8000)                │
│ ├── /health/ready & /health/live (Sistem Sağlık Uç Noktası)│
│ ├── /api/v1/auth (JWT Argon2id Token Rotasyonu)           │
│ ├── /api/v1/production, /costing, /butchering             │
│ ├── /api/v1/lots, /traceability, /recalls (Lot Şeceresi)  │
│ └── /api/v1/ai (HMAC İmzalı ML Karar Desteği)             │
└─────────────┬───────────────────────────────┬─────────────┘
              │                               │
              ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│   MySQL 8.4 (Port 3307)   │   │  Redis 7.4 (Dahili: 6379) │
│  (Tek Doğruluk Kaynağı)   │   │  (Paylaşımlı Rate-Limit)  │
└───────────────────────────┘   └───────────────────────────┘
```

---

## 3. Gereksinimler

- **İşletim Sistemi:** Windows 10/11, macOS veya Linux
- **Konteyner Altyapısı:** Docker Desktop 4.x+ ve Docker Compose v2
- **Yerel Geliştirme (Opsiyonel / Ayrı Çalıştırma İçin):**
  - Python 3.12+ (Backend için)
  - Node.js 20+ ve `pnpm` veya `npm` (Web arayüzü için)
  - OpenJDK 17 ve Android SDK / Gradle Wrapper (Android derlemesi için)
  - Git 2.40+

---

## 4. Kurulum ve Çalıştırma

### 4.1 Depoyu İndirme
```bash
git clone https://github.com/Yusuffmiraccc/avatar-yarisma.git
cd avatar-yarisma
```

### 4.2 Docker Compose ile Tek Adımda Başlatma
Proje kök dizininde yer alan Docker Compose yapılandırması; MySQL, Redis, API, Web ve Demo Seed servislerini bağımlılık sırasına ve healthcheck kontrollerine göre otomatik başlatır:

```bash
docker compose up --build -d
```

Servislerin durumunu ve sağlık kontrollerini doğrulamak için:
```bash
docker compose ps
```

*Beklenen Çıktı:*
- `avatar-mysql-1`: Healthy (Port `127.0.0.1:3307:3306`)
- `avatar-redis-1`: Healthy (Dahili port `6379`)
- `avatar-api-1`: Healthy (Port `:8000:8000`)
- `avatar-web-1`: Healthy (Port `127.0.0.1:5173:80`)
- `avatar-demo-seed-1`: Exited (0) (Seed işlemi tamamlandıktan sonra durur)

Servis loglarını incelemek için:
```bash
docker compose logs --tail=100 api
docker compose logs --tail=100 mysql
docker compose logs --tail=100 web
docker compose logs demo-seed
```

API sağlık kontrolü (PowerShell):
```powershell
Invoke-WebRequest http://localhost:8000/health/ready
```
veya cURL:
```bash
curl http://localhost:8000/health/ready
```
*Beklenen Yanıt:* `{"status":"ready","database":"connected","rate_limit_store":"connected"}`

### Doğrulanmış Erişim Adresleri

| Servis | Adres | Açıklama |
| :--- | :--- | :--- |
| **Web Yönetim Paneli** | `http://localhost:5173` | React arayüzü (Nginx üzerinden sunulur) |
| **Backend REST API** | `http://localhost:8000` | FastAPI ana servisi |
| **API Dokümantasyonu (Swagger)** | `http://localhost:8000/api/v1/docs` | Etkileşimli OpenAPI dokümantasyonu |
| **API Sağlık Durumu** | `http://localhost:8000/health/ready` | DB ve Redis hazır olma kontrolü |

---

### 4.3 Web Uygulamasını Bağımsız Çalıştırma
Docker yerine web uygulamasını yerel Node ortamında geliştirmek isterseniz:
```bash
cd web
pnpm install   # veya npm install
pnpm dev       # veya npm run dev
```
Uygulama `http://127.0.0.1:5173` üzerinde açılır.

Test ve derleme komutları:
```bash
pnpm test          # veya npm test (vitest ile 11 birim testini çalıştırır)
pnpm run build     # veya npm run build (TypeScript denetimi ve Vite prodüksiyon derlemesi)
```

---

### 4.4 Backend Servisini Bağımsız Çalıştırma
Backend'i Docker haricinde Python sanal ortamında çalıştırmak isterseniz:
```powershell
cd backend
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"

# MySQL port 3307'de çalışırken:
alembic upgrade head
python -m scripts.seed_demo
uvicorn app.main:app --reload --port 8000
```
> [!CAUTION]
> Yerel uvicorn ile Docker Compose `api` servisini aynı anda çalıştırmayın; port 8000 çakışması yaşanır.

---

## 5. Ortam Değişkenleri ve Yapılandırma

Kök dizinde yer alan `.env.example` şablonu yerel geliştirme için güvenli varsayılanlarla donatılmıştır:

| Ortam Değişkeni | Varsayılan (Local) | Açıklama |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `local` | `local` haricinde varsayılan şifreler kilitlenir |
| `MYSQL_PASSWORD` | `change-me-local-only` | MySQL `avatar` kullanıcısı parolası |
| `MYSQL_ROOT_PASSWORD` | `change-root-local-only`| MySQL root parolası |
| `REDIS_PASSWORD` | `avatar-test-only` | Redis kimlik doğrulama parolası |
| `JWT_SECRET_KEY` | `local-dev-secret-change-me...` | Kullanıcı oturum token imzalama anahtarı |
| `ML_SIGNING_SECRET` | `local-ml-signing-secret...` | ML model dosyaları HMAC imzalama anahtarı (JWT'den bağımsızdır) |
| `ENABLE_DEMO_SEED` | `true` | Başlangıçta demo verilerini otomatik yükler |

---

## 6. Demo Kullanıcıları

`backend/scripts/seed_demo.py` tarafından oluşturulan ve doğrulanmış demo kullanıcı rolleri şunlardır:

| Rol | E-Posta | İzin Kapsamı | Maliyet Verisi Erişimi |
| :--- | :--- | :--- | :--- |
| **Yönetici** | `admin@avatar.demo` | Tam sistem yetkisi, kullanıcı yönetimi, onaylar | **Görür (`costs:read`)** |
| **Operatör** | `operator@avatar.demo` | Üretim tamamlama, karkas parçalama, stok girişi | Gizli (Maskelenir) |
| **Saha Satış** | `sales@avatar.demo` | Android satış uygulaması, liste fiyatıyla sipariş | Gizli (Maskelenir) |
| **İzlenebilirlik** | `trace@avatar.demo` | Lot soy ağacı takibi, geri çağırma (recall) başlatma | Gizli (Maskelenir) |
| **İzleyici** | `viewer@avatar.demo` | Salt okunur izleme ve denetim kayıtları | Gizli (Maskelenir) |

Tüm demo kullanıcılarının ortak parolası: **`Avatar-Demo-2026!`**

> [!WARNING]
> Bu hesaplar ve parolalar yalnızca yerel geliştirme ve yarışma jürisi değerlendirmesi içindir. Gerçek üretim ortamında kullanılmamalıdır.

---

## 7. Yarışma Senaryoları ve Doğrulama

Aşağıdaki senaryolar değerlendirme belgesi (`AVATAR_Assessment.pdf`) kurallarına göre modellenmiş ve backend testleriyle doğrulanmıştır:

### Senaryo 1 — Fason Üretim ve Gerçek Birim Maliyet (EKP)
Üretimde tüketilen girdileri, dış fason hizmet bedelini ve elde edilen sağlam mamul miktarını kuruşu kuruşuna ilişkilendirir.

**Formül:**
$$\text{Toplam Maliyet} = \text{Tüketilen Hammadde Maliyeti} + \text{Dış Hizmet Faturası} + \text{Ek Maliyetler}$$
$$\text{Gerçek EKP} = \frac{\text{Toplam Maliyet}}{\text{Sağlam Mamul Miktarı}}$$

**Doğrulanmış Referans Verileri:**
- 100 kg Dana Eti: 970,00 €
- 2 kg Baharat Karışımı: 48,00 €
- 5 kg Doğal Bağırsak: 58,00 €
- *Hammadde Toplamı:* 1.076,00 €
- Fason Üretim Hizmet Faturası (85 paket × 5,50 €/paket): 467,50 €
- **Toplam Üretim Maliyeti:** **1.543,50 €**
- Üretilen Sağlam Mamul: **85 paket** `SUC-2026-045`
- **Hesaplanan Birim EKP:** $\frac{1.543,50}{85} = 18,1588\ldots \longrightarrow \mathbf{18,16\text{ €/paket}}$

> **Doğrulama Notu:** Üretim emri `URT-2026-045` tamamlandığında bu değerler sistem tarafından otomatik hesaplanır ve stok hareketine `18.16 €` birim maliyetle işlenir (`test_costing.py`).

---

### Senaryo 2 — Bütün Kuzu Parçalama ve Tutarsızlık Tespiti
Karkas giriş ağırlığı ve maliyetinden parça ürünlerin elde edilmesini, fireyi ve maliyet dağılımını izler.

**Senaryodaki Tutarsızlık Durumu:**
- Giriş Karkas Ağırlığı: **25 kg**
- Fatura Toplamı: **351,00 €**
- Beyan Edilen Birim Flaş Fiyat: **11,50 €/kg**
- Alınan Parça Toplamı: **22 kg**

**Sistem Davranışı:**
$$25\text{ kg} \times 11,50\text{ €/kg} = 287,50\text{ €} \neq 351,00\text{ €}$$
- Sistem bu tutarsızlığı sessizce düzeltmez veya görmezden gelmez; faturadaki 351,00 € tutarını esas alarak `weight_variance_records` oluşturur ve operatöre onay uyarısı verir.
- 25 kg giriş ile 22 kg parça arasındaki 3 kg fark **fire** olarak işaretlenir.
- 351,00 € maliyet parça ağırlıklarına göre (`BY_WEIGHT`) kuruşu kuruşuna dağıtılır; yuvarlama artığı kuruş son parça kalemine aktarılır (toplam maliyet kuruşu kuruşuna 351,00 € kalır).

---

### Senaryo 3 — Lot İzlenebilirliği ve Geri Çağırma (Recall)
Kalite kusuru bildirilen bir hammadde lotundan üretilen tüm mamulleri ve sevkiyat noktalarını saniyeler içinde tespit eder.

**Şecere Akışı:**
```text
ET-2026-001 (Kusurlu Hammadde Lotu)
       │
       ▼
URT-2026-045 (Fason Üretim Emri)
       │
       ▼
SUC-2026-045 (Mamul Lotu - 85 Paket)
       ├──> Market A: 30 paket (İrsaliye: DSP-001)
       ├──> Market B: 25 paket (İrsaliye: DSP-002)
       └──> Market C: 30 paket (İrsaliye: DSP-003)
```

**Adım Adım İzleme ve Kilit Mekanizması:**
1. İzlenebilirlik yöneticisi `ET-2026-001` lotunu sorgular.
2. Sistem ileriye dönük ağacı çözerek etkilenen `SUC-2026-045` lotunu ve Market A, B, C sevkiyatlarını listeler.
3. `RCL-2026-001` geri çağırma emri aktive edilir; mamul lot durumu anında `BLOCKED` yapılır.
4. Android uygulamasında bloke lot kırmızı şeritle satışa kapatılır.
5. Android cihazı henüz senkronize olmasa bile, eski önbellekle gönderilen satış istekleri sunucu tarafında atomik olarak reddedilir:
   ```json
   { "error": { "code": "LOT_BLOCKED", "message": "Lot SUC-2026-045 geri çağırma kapsamında kilitlidir." } }
   ```
   *(HTTP 409 Conflict döner; stok hareketi oluşmaz).*

---

## 8. Yapay Zekâ Modelleri (Model 1 ve Model 2)

Sistemde iki farklı makine öğrenmesi problemi ele alınmıştır:

### Model 1 — Üretim Verimi ve EKP Tahmini
- **Amaç:** Üretime giren et, baharat, bağırsak miktarları ve tedarikçi geçmişinden beklenen çıktı paket miktarını ve birim EKP'yi tahmin etmek.
- **Kod Alanı:** `backend/app/ml/`, `ai/Model1/`
- **Veri Kümesi:** 1.000 simüle parti (`sucuk_uretim_1000_simule_parti.csv`) ve 120 parti sentetik operasyon verisi.
- **Algoritma & Başarı:** 5-Katlı Çapraz Doğrulamada Gradient Boosting modeli, baseline ortalamaya göre:
  - Çıktı Miktarı Hatasında (MAE): **%37.55 İyileşme** (4.04 $\rightarrow$ 2.53 paket)
  - EKP Tahmin Hatasında (MAE): **%37.19 İyileşme** (0.4824 $\rightarrow$ 0.3030 €/paket)
- **Güvenlik & Bütünlük:** Model dosyası HMAC-SHA256 ile imzalanır (`production_yield.joblib.sig`). İmzası doğrulanmayan model belleğe yüklenmez.
- **Canlı Uç Nokta:** `POST /api/v1/ai/production-yield/predict` (HTTP 200).
- **Sınırlama:** Sentetik veriyle eğitilmiştir; fabrika koşullarındaki fiziksel anomalileri kapsamaz. Karar destek amaçlıdır.

### Model 2 — Karkas Parçalama Verimi Tahmini
- **Amaç:** Hayvan türü (Kuzu, Koyun, Dana) ve karkas ağırlığından 8 farklı parça et dağılımını eş zamanlı tahmin etmek.
- **Kod Alanı:** `ai/Model2/`
- **Veri Kümesi:** 1.200 sentetik karkas kaydı (840 eğitim / 180 doğrulama / 180 test).
- **Algoritma & Başarı:** Random Forest Regressor, baseline hayvan ortalamalarına göre genel MAE'de **%31.06 iyileşme** (0.997 kg/parça) sağlamıştır.
- **Üretim Durumu (Fail-Closed İlkesi):**
  > [!IMPORTANT]
  > Gerçek saha ölçüm verisi (`ai/Model2/data/raw/measured/`) henüz toplanmadığı için **Model 2 üretimde aktif tahmin vermeye açılmamıştır.**
  > `POST /v1/predict/carcass-cuts` üretim uç noktası çağrıldığında **HTTP 503 Service Unavailable (Fail-Closed)** döner.
  > Pilot testler ve denetim kayıtları için `POST /v1/predict/carcass-cuts/experimental` uç noktası açık bırakılmıştır ve SQLite denetim günlüğü tutmaktadır.
  > Ana backend'de ise `POST /api/v1/ai/butchering-output/predict` çağrısı, karkas parçalama için güvenli baseline fallback üretir ve `limitations_note="Sentetik model; gerçek üretim yerine geçmez"` uyarısını ekler.

---

## 9. Android Uygulaması ve APK

Mobil saha satış uygulaması `android/` dizininde yer alır.

### 9.1 Derleme ve Birim Testleri
Windows PowerShell üzerinde:
```powershell
cd android
.\gradlew.bat :app:testDebugUnitTest
.\gradlew.bat :app:assembleDebug
```
Linux / macOS üzerinde:
```bash
cd android
./gradlew :app:testDebugUnitTest
./gradlew :app:assembleDebug
```

Derlenen APK konumu:
- `android/app/build/outputs/apk/debug/app-debug.apk`
- Ayrıca depoda hazır dağıtım paketi mevcuttur: `artifacts/AVATAR-Yarisma.apk` (12.2 MB).

### 9.2 Gerçek Telefonda Çalıştırma ve Ağ Bağlantısı
Uygulama dinamik sunucu adresi yapılandırmasını destekler.

1. **Aynı Wi-Fi (LAN) Üzerinden Bağlantı:**
   - Bilgisayarınızın yerel IPv4 adresini öğrenin (PowerShell'de `ipconfig`, Linux'ta `ip a`).
   - Android uygulamasını açın, Giriş ekranındaki **`⚙️ Sunucu Ayarı`** butonuna dokunun.
   - Sunucu adresi olarak bilgisayarınızın IP adresini girin:
     ```text
     http://<BILGISAYAR_YEREL_IP>:8000/api/v1/
     ```
     *(Örnek: `http://192.168.1.35:8000/api/v1/` — Not: 192.168.1.7 sabit bir adres değildir, kendi IP adresinizi yazınız).*

2. **Android Emülatörü İle:**
   - Emülatör host loopback adresi hazır çip ile seçilebilir:
     ```text
     http://10.0.2.2:8000/api/v1/
     ```

3. **USB Kablolu Bağlantı (ADB Reverse):**
   - Telefonu USB hata ayıklama ile bağlayın ve şu komutu çalıştırın:
     ```powershell
     adb reverse tcp:8000 tcp:8000
     ```
   - Ardından uygulama sunucu adresine `http://localhost:8000/api/v1/` girin.

### 9.3 Mobil Çevrimdışı Mantık ve Idempotency
- **Katalog Senkronizasyonu:** `GET /sync/catalog?updated_after=...` ile ürünler, müşteriler ve güncel lotlar yerel Room SQLite veritabanına aktarılır.
- **Çevrimdışı Satış:** Ağ yokken sipariş yerel veritabanına `PENDING` olarak yazılır; yerel stoktan iyimser düşüm yapılır.
- **Idempotency-Key:** Her satış için istemcide üretilen benzersiz UUID (`client_uuid`), `Idempotency-Key` başlığıyla gönderilir. Ağ koptuğunda WorkManager aynı anahtarla tekrar dener; sunucu asla mükerrer sipariş oluşturmaz.
- **Stok Hareketi İzlenebilirliği:** Sunucudan dönen `stock_movement_id` yerel satış satırlarına kaydedilerek tam izlenebilirlik sağlanır.

---

## 10. Test Komutları ve Gerçek Çıktılar

Bütün testler yerel ortamda ve CI hattında bizzat çalıştırılmış olup gerçek sonuçlar aşağıda sunulmuştur:

| Test Paketi | Çalıştırma Komutu | Kapsam | Gerçek Sonuç |
| :--- | :--- | :--- | :--- |
| **Backend Testleri** | `cd backend && python -m pytest tests/ -v` | Yetki matrisi, EKP hesabı, kuzu parçalama, recall, rate-limit, ML HMAC | **116 passed, 2 skipped, 0 failed** (5 dk 10 sn) |
| **Web Testleri** | `cd web && npm test` *(veya `pnpm test`)* | API istemcisi, dialoglar, veri doğrulama | **11 passed (4 test dosyası)** (2.44 sn) |
| **Web Prodüksiyon Derlemesi** | `cd web && npm run build` | TypeScript `tsc -b` ve Vite production bundle | **Başarılı (0 hata)** (4.99 sn) |
| **Model 1 Testleri** | `python -m pytest ai/Model1/tests/ -q` | Model 1 pipeline, metrikler, HMAC | **83 passed** (3.90 sn) |
| **Model 2 Testleri** | `python -m pytest ai/Model2/tests/ -q` | Model 2 API, fail-closed 503, audit | **16 passed** (2.74 sn) |
| **Android Birim Testleri**| `cd android && .\gradlew.bat :app:testDebugUnitTest` | BigDecimal, SaleValidator, Idempotency | **Başarılı (0 hata)** |
| **Android APK Derleme** | `cd android && .\gradlew.bat :app:assembleDebug` | Debug APK derleme | **Başarılı (`app-debug.apk`)** |

> [!NOTE]
> GitHub Actions CI iş akışı (`.github/workflows/ci.yml`), yukarıdaki testleri `ubuntu-latest` koşucusu üzerinde `backend-test`, `web-test` ve `android-test` işleriyle otomatik olarak doğrulamaktadır.

---

## 11. API ve Mevcut Teknik Dokümantasyon

Depoda bulunan doğrulanmış teknik belgeler ve sözleşmeler:

| Belge Yolu | Açıklama |
| :--- | :--- |
| [`contract/openapi.json`](contract/openapi.json) | OpenAPI 3.1 resmi API sözleşmesi |
| [`docs/architecture.md`](docs/architecture.md) | Sistem mimarisi, katmanlar ve veri akış şemaları |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | Veritabanı tabloları, ilişkiler, kısıtlar ve indeksler |
| [`docs/API.md`](docs/API.md) | Uç noktalar, istek/yanıt şemaları ve hata kodları |
| [`docs/DEMO.md`](docs/DEMO.md) | Jüri değerlendirmesi için adım adım demo uygulama rehberi |
| [`docs/ML.md`](docs/ML.md) | Makine öğrenmesi algoritmaları, metrikleri ve sınırları |
| [`docs/AI_RAPORU.md`](docs/AI_RAPORU.md) | Bilimsel model deneyleri, çapraz doğrulama raporu |
| [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md) | Ayrıntılı test senaryoları, çıktı logları ve kanıtlar |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Yetkilendirme matrisi, şifreleme, güvenlik politikaları |
| [`docs/SENKRON.md`](docs/SENKRON.md) | Android SQLite ↔ MySQL senkronizasyon protokolü |
| [`artifacts/README.md`](artifacts/README.md) | Üretilen APK paketi ve SHA-256 doğrulama bilgileri |

---

## 12. Güvenlik ve Bilinen Sınırlamalar

1. **Demo Kimlik Bilgileri:** `Avatar-Demo-2026!` ve demo e-posta hesapları yalnızca izole test ve değerlendirme ortamı içindir. `ENVIRONMENT!=local` olduğunda varsayılan parolalarla başlangıç engellenir.
2. **Gizli Bilgi Yönetimi:** Kaynak koda veya Git geçmişine hiçbir gerçek API anahtarı, gizli token veya üretim parolası eklenmemiştir.
3. **Model 2 Saha Sınırlaması:** Model 2 karkas parçalama modeli sentetik veriyle eğitilmiştir; gerçek kesimhane ölçüm kayıtları toplanana kadar üretim tahmini (`/v1/predict/carcass-cuts`) güvenli biçimde **kapalıdır (Fail-Closed HTTP 503)**.
4. **Maliyet İzolasyonu:** Satış personeli (`sales@avatar.demo`), operatör ve izleyici rollerine maliyet alanları (`unit_cost`, `total_cost`, `ekp`) API seviyesinde maskelenerek sunulur (`costs:read` yetkisi aranır).
5. **Ağ Güvenliği:** Mobil bağlantılarda yerel ağ HTTP erişimine yalnızca geliştirme ortamında izin verilmiştir (`network_security_config.xml`). Üretim dağıtımında HTTPS ve sertifika doğrulama zorunludur.

---

## 13. Katkı ve Lisans

Bu proje AVATAR Yapay Zekâ Yarışması kapsamında geliştirilmiştir.

Pull request göndermeden önce:
1. `git diff` ile değişikliklerinizi inceleyin.
2. İlgili birim ve entegrasyon testlerini çalıştırın.
3. Gizli anahtar veya `.env` dosyası eklenmediğini doğrulayın.
4. Test sonuçlarını ve bilinen sınırlamaları açıklayın.

---
- **Depo:** [https://github.com/Yusuffmiraccc/avatar-yarisma](https://github.com/Yusuffmiraccc/avatar-yarisma)
- **Aktif Geliştirme Dalı:** `feature/ai-models-development`
