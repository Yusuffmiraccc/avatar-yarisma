# AVATAR — Üretim, Gerçek Maliyet (EKP), Satış ve Lot İzlenebilirliği

AVATAR, et ve et ürünleri üretim süreçlerini; hammadde takibi, fason üretim, gerçek birim maliyet (EKP) hesaplama, karkas parçalama, stok ve satış yönetimi, lot izlenebilirliği ve geri çağırma işlemleri üzerinden dijitalleştirmeyi amaçlayan bir yazılım projesidir.

Proje; web yönetim paneli, REST API, MySQL veritabanı, Android satış uygulaması ve makine öğrenmesi bileşenlerinden oluşur.

> [!NOTE]
> **Proje durumu:** Bu doküman kurulum ve değerlendirme rehberidir. Özelliklerin üretime hazır olduğu veya bütün testlerin geçtiği varsayılmamalıdır. Doğrulanmış test sonuçları ve bilinen sınırlamalar ilgili bölümlerde belirtilmiştir.

---

## İçindekiler
- [Proje Hedefleri](#proje-hedefleri)
- [Teknoloji ve Mimari](#teknoloji-ve-mimari)
- [Gereksinimler](#gereksinimler)
- [Kurulum ve Çalıştırma](#kurulum-ve-çalıştırma)
- [Demo Kullanıcıları](#demo-kullanıcıları)
- [Yarışma Senaryoları](#yarışma-senaryoları)
- [Yapay Zekâ Modelleri](#yapay-zekâ-modelleri)
- [Android Uygulaması](#android-uygulaması)
- [Testler ve Doğrulama](#testler-ve-doğrulama)
- [API ve Teknik Dokümantasyon](#api-ve-teknik-dokümantasyon)
- [Güvenlik ve Bilinen Sınırlamalar](#güvenlik-ve-bilinen-sınırlamalar)
- [Katkı ve Geliştirme](#katkı-ve-geliştirme)

---

## Proje Hedefleri
AVATAR'ın hedefleri şunlardır:
- Hammadde girişlerini ve üretim emirlerini izlemek.
- Fason üretim maliyetlerini ve gerçek birim maliyeti hesaplamak.
- Karkas parçalama sonucunda elde edilen ürünleri ve fireleri kaydetmek.
- Üretim, stok, sevkiyat ve satış kayıtları arasında lot ilişkilerini korumak.
- Kalite sorunu bulunan lotların etkilediği ürünleri ve sevkiyatları belirlemek.
- Android uygulamasında satış işlemlerini desteklemek ve bağlantı kesintilerinde bekleyen işlemleri senkronize etmek.
- Makine öğrenmesiyle üretim verimi, maliyet ve parçalama çıktıları hakkında karar desteği sağlamak.

---

## Teknoloji ve Mimari

| Bileşen | Teknoloji | Dizin |
| :--- | :--- | :--- |
| **Backend ve REST API** | Python, FastAPI, SQLAlchemy, Alembic | `backend/` |
| **Web Yönetim Paneli** | React, TypeScript, Vite | `web/` |
| **Android Uygulaması** | Kotlin, Jetpack Compose, Room, Retrofit, WorkManager | `android/` |
| **Merkezi Veritabanı** | MySQL 8.4 | `database/` |
| **API Sözleşmesi** | OpenAPI 3.1 | `contract/openapi.json` |
| **Makine Öğrenmesi** | Python, scikit-learn, pandas | `backend/app/ml/`, `ai/` |
| **Yerel Geliştirme Ortamı** | Docker Compose | `docker-compose.yml` |

### Temel Mimari
```text
Web Yönetim Paneli ─────┐
                        ├── REST API ─── MySQL (Merkezi Veri Kaynağı)
Android Uygulaması ─────┘       │
                                ├── Üretim ve maliyet işlemleri
                                ├── Stok, satış ve lot izlenebilirliği
                                └── Yapay zekâ tahmin servisleri

* Android Room / SQLite: Yerel katalog önbelleği ve bekleyen satış işlemleri
```
MySQL merkezi veri kaynağı olarak kullanılır. Android tarafındaki Room/SQLite veritabanı ise yerel veriler ve bekleyen işlemler için kullanılır.

---

## Gereksinimler
- Git
- Docker Desktop ve Docker Compose
- Python 3.12+ ve proje bağımlılıkları (manuel backend kurulumu için)
- Node.js 20+ ve pnpm / npm (web uygulamasını ayrı çalıştırmak için)
- JDK 17 ve Android Gradle Wrapper (Android uygulaması için)

> Sürümler ve bağımlılıklar için ilgili alt projelerin yapılandırma dosyaları (`pyproject.toml`, `package.json`, `build.gradle.kts`) esas alınmalıdır.

---

## Kurulum ve Çalıştırma

### 1. Depoyu İndirme
```bash
git clone https://github.com/Yusuffmiraccc/avatar-yarisma.git
cd avatar-yarisma
```

### 2. Docker Compose ile Servisleri Başlatma
Proje kök dizininde:
```bash
docker compose up --build -d
docker compose ps
```

Servislerin durumunu kontrol etmek için:
```bash
docker compose logs --tail=100 api
docker compose logs --tail=100 mysql
docker compose logs --tail=100 web
docker compose logs --tail=100 demo-seed
```

API sağlık kontrolü (PowerShell):
```powershell
Invoke-WebRequest http://localhost:8000/health/ready
```
veya cURL:
```bash
curl http://localhost:8000/health/ready
```

Servisler hazır olduğunda kullanılabilecek adresler:

| Servis | Adres |
| :--- | :--- |
| **Backend API** | `http://localhost:8000` |
| **API Dokümantasyonu (Swagger)** | `http://localhost:8000/api/v1/docs` |
| **Web Yönetim Paneli** | `http://localhost:5173` |

> [!TIP]
> API dokümantasyonu veya web paneli açılmıyorsa önce ilgili servisin `docker compose ps` ve log çıktıları kontrol edilmelidir.

### 3. Demo Verileri
Docker Compose yapılandırmasında `demo-seed` servisi, yerel ortamda `ENABLE_DEMO_SEED=true` olduğunda demo verilerini yüklemek üzere tanımlanmıştır.

Demo verilerinin yüklenmesi ve kullanıcıların oluşturulması tamamlanmadan giriş bilgilerinin çalıştığı varsayılmamalıdır. Veri yükleme durumunu kontrol etmek için:
```bash
docker compose logs demo-seed
```

### 4. Web Uygulamasını Ayrı Çalıştırma
Web uygulamasını Docker yerine geliştirme sunucusuyla çalıştırmak isterseniz:
```bash
cd web
pnpm install
pnpm dev
```

Test ve production build komutları:
```bash
pnpm test
pnpm run build
```
*(Alternatif olarak `npm ci`, `npm test` ve `npm run build` komutları da kullanılabilir).*

### 5. Backend'i Ayrı Çalıştırma
Backend'i Docker dışında çalıştırmak için:
```powershell
cd backend
Copy-Item .env.example .env
```
Ardından Python sanal ortamını, bağımlılıkları (`pip install -e ".[dev]"`) ve gerekli ortam değişkenlerini hazırlayın. Veritabanı hazır olduktan sonra:
```bash
alembic upgrade head
python -m scripts.seed_demo
uvicorn app.main:app --reload --port 8000
```
> [!CAUTION]
> Bu yöntem Docker Compose ile aynı servisleri eş zamanlı başlatmak için kullanılmamalıdır; port ve veritabanı ayarlarının çakışmadığından emin olun.

---

## Demo Kullanıcıları

Projede tanımlı demo rollerinin amaçları:

| Rol | Amaç |
| :--- | :--- |
| **Yönetici** | Genel yönetim ve yapılandırma |
| **Operatör** | Üretim, parçalama ve stok işlemleri |
| **Saha Satış** | Android satış uygulaması (maliyetler gizlidir) |
| **İzlenebilirlik** | Lot takibi ve geri çağırma |
| **İzleyici** | Salt okunur inceleme (maliyetler gizlidir) |

Repo dokümantasyonunda tanımlanan demo hesapları:

| Rol | Kullanıcı E-posta |
| :--- | :--- |
| **Yönetici** | `admin@avatar.demo` |
| **Operatör** | `operator@avatar.demo` |
| **Saha Satış** | `sales@avatar.demo` |
| **İzlenebilirlik** | `trace@avatar.demo` |
| **İzleyici** | `viewer@avatar.demo` |

Belgelenen demo parolası: **`Avatar-Demo-2026!`**

> [!WARNING]
> Bu hesapların kullanılabilirliği demo seed işlemi ve mevcut yapılandırma üzerinden doğrulanmalıdır. Demo parolalarını gerçek veya internete açık üretim ortamlarında asla kullanmayın.

---

## Yarışma Senaryoları

Aşağıdaki senaryolar değerlendirme sırasında adım adım gösterilmek üzere hazırlanmalıdır. Beklenen değerler, uygulamanın gerçek çıktısıyla karşılaştırılarak doğrulanmalıdır.

### Senaryo 1 — Fason Üretim ve Gerçek Birim Maliyet (EKP)
Amaç, üretimde tüketilen girdileri, hizmet maliyetini, elde edilen mamul miktarını ve birim maliyeti ilişkilendirmektir.

**Temel Hesap:**
$$\text{Toplam Maliyet} = \text{Hammadde Maliyeti} + \text{Hizmet Bedeli} + \text{Ek Maliyetler}$$

$$\text{EKP} = \frac{\text{Toplam Maliyet}}{\text{Sağlam Mamul Miktarı}}$$

**Örnek Senaryo Değerleri:**

| Kalem | Tutar |
| :--- | :--- |
| Et | 970,00 € |
| Baharat | 48,00 € |
| Bağırsak | 58,00 € |
| Fason Hizmet | 467,50 € |
| **Toplam Maliyet** | **1.543,50 €** |
| Sağlam Mamul | 85 paket |
| **Birim EKP** | **18,16 €/paket** |

**Hesaplama Detayı:**
$$\frac{1.543,50}{85} = 18,1588\ldots \approx 18,16\text{ €/paket}$$

> **Doğrulama:** Üretim emrini, tüketilen malzemeleri, hizmet faturasını, mamul miktarını ve sistemin hesapladığı EKP değerini ekranda gösterin. Bu örnek değerlerin uygulama tarafından gerçekten üretildiği backend testleriyle doğrulanmıştır (`test_costing.py`, `test_standalone_flows.py`).

---

### Senaryo 2 — Bütün Kuzu Parçalama
Amaç, bir karkasın giriş ağırlığı ve maliyetinden elde edilen parça ürünleri, fireyi ve maliyet dağılımını takip etmektir.

**Demo Dokümanındaki Örnek Değerler:**
- Giriş ağırlığı: **25 kg**
- Fatura tutarı: **351,00 €**
- Beyan edilen birim fiyat: **11,50 €/kg**
- Parça toplamı: **22 kg**

**Bu değerler arasında bilerek bırakılmış tutarsızlık vardır:**
$$25 \times 11,50 = 287,50\text{ €} \neq 351,00\text{ €}$$

Bu sonuç 351,00 € fatura tutarına eşit değildir. Ayrıca 25 kg giriş ile 22 kg parça toplamı arasındaki 3 kg farkın fire veya yan ürün olup olmadığı sistem tarafından açıklanmalıdır.

> **Doğrulama:** Sistemin bu tutarsızlıkları görünür kıldığını (`weight_variance_records` ve uyarı mekanizması), parça ağırlıklarını ve maliyet dağıtımını (`BY_WEIGHT`) kuruşu kuruşuna nasıl kaydettiğini gösterin. Kaynağı doğrulanmamış değerleri sessizce düzeltmeyin.

---

### Senaryo 3 — Lot İzlenebilirliği ve Geri Çağırma (Recall)
Amaç, kalite sorunu bulunan bir hammadde lotundan etkilenen üretim, mamul ve sevkiyat kayıtlarını bulmaktır.

**Demo Dokümanında Belirtilen Örnek İlişki:**
```text
ET-2026-001 (Hammadde Lotu)
       │
       ▼
URT-2026-045 (Üretim Emri)
       │
       ▼
SUC-2026-045 (Mamul Lotu)
       ├──> Market A: 30 paket
       ├──> Market B: 25 paket
       └──> Market C: 30 paket
(Toplam Sevkiyat Miktarı: 85 paket)
```

**Gösterilecek Adımlar:**
1. Hammadde lotunu (`ET-2026-001`) bulun.
2. Lotla ilişkili üretim emrini (`URT-2026-045`) ve mamul lotunu (`SUC-2026-045`) görüntüleyin.
3. Sevkiyatları ve müşterileri (Market A, B, C) belirleyin.
4. Geri çağırma işlemini etkinleştirin (`RCL-2026-001`).
5. Bloke edilen lotun satışa kapatıldığını doğrulayın.
6. Hem Android arayüzünde hem de sunucu tarafında bloke lot korumasını test edin.

> [!IMPORTANT]
> Geri çağırma koruması yalnızca istemci arayüzüne dayanmamalıdır; sunucu da geçersiz ve bloke satışları `409 LOT_BLOCKED` statüsüyle reddetmelidir.

---

## Yapay Zekâ Modelleri

Projede iki farklı tahmin problemi ele alınmaktadır:

### Model 1 — Üretim Verimi ve EKP
- **Amaç:** Üretim girdilerinden beklenen mamul miktarı ve birim maliyet hakkında karar desteği sağlamak.
- **Kod Alanı:** `backend/app/ml/` ve `ai/Model1/`
- **Veri:** Repo dokümantasyonunda 1.000 satırlık simüle üretim verisi (`sucuk_uretim_1000_simule_parti.csv`).
- **Sınırlama:** Simüle verideki performans, gerçek fabrikadaki performansın kanıtı değildir. Karar desteği sunar; muhasebe EKP yerine geçmez.

### Model 2 — Karkas Parçalama
- **Amaç:** Hayvan türü ve karkas ağırlığı gibi girdilerden parçalama çıktılarını tahmin etmek.
- **Kod Alanı:** `ai/Model2/`
- **Veri:** Dokümantasyonda 1.200 satırlık sentetik veri (`ModelB_*_sentetik.csv`).
- **Sınırlama:** Gerçek saha ölçümleriyle doğrulanmış üretim artefaktı bulunmadığında sistemin güvenli biçimde tahmin vermeyi reddetmesi (`HTTP 503 Fail-Closed`) korunmalıdır.

### Model Değerlendirme İlkeleri
Model raporlarında şu bilgiler ayrı ayrı sunulmalıdır:
1. Eğitim, doğrulama ve test veri kümelerinin nasıl ayrıldığı.
2. Verinin gerçek mi sentetik mi olduğu.
3. Kullanılan algoritmalar ve değerlendirme metrikleri.
4. Test kümesinde ölçülen hata değerleri.
5. Gerçek saha verisiyle doğrulama durumu.
6. Modelin üretimde kullanılmasına ilişkin bilinen sınırlamalar.

> [!NOTE]
> Tahmin edilen EKP, muhasebe sisteminin gerçek maliyet hesabının yerine geçmez. Model tahmini ile fiilî gerçekleşen sonuçlar ayrı tutulmalıdır.

---

## Android Uygulaması

Android uygulaması `android/` dizininde bulunur ve Kotlin, Jetpack Compose, Room/SQLite ve Retrofit teknolojilerini kullanır.

### Derleme ve Test (Windows PowerShell)
```powershell
cd android
.\gradlew.bat :app:assembleDebug
.\gradlew.bat :app:testDebugUnitTest
```

Başarılı debug APK dosyasının beklenen yolu:
`android/app/build/outputs/apk/debug/app-debug.apk` *(Ayrıca `artifacts/AVATAR-Yarisma.apk` altında mevcuttur).*

### Gerçek Telefonda Bağlantı
1. Backend'in bilgisayarda çalıştığını doğrulayın (`http://localhost:8000/health/ready`).
2. Telefonu ve bilgisayarı aynı Wi-Fi ağına bağlayın.
3. Android uygulamasındaki sunucu adresi ayarını açın.
4. Bilgisayarın yerel IP adresini kullanarak API adresini girin:
   ```text
   http://192.168.1.7:8000/api/v1/
   ```
   *(Not: `192.168.1.7` örnek geliştirme ortamına aittir; başka bir ağda bilgisayarın güncel IPv4 adresi kullanılmalıdır).*
5. **Android Emülatörü için:**
   ```text
   http://10.0.2.2:8000/api/v1/
   ```
6. **USB Bağlantısında (ADB Reverse):**
   ```powershell
   adb reverse tcp:8000 tcp:8000
   ```
   Ardından uygulamada:
   ```text
   http://localhost:8000/api/v1/
   ```

> [!CAUTION]
> Yerel HTTP adresleri yalnızca kontrollü geliştirme ortamında kullanılmalıdır. Üretim ortamında HTTPS ve uygun güvenlik yapılandırması gereklidir.

---

## Testler ve Doğrulama

Testleri çalıştırmak için ilgili alt projelerdeki komutları kullanın:

| Alan | Komut | Doğrulanmış Durum |
| :--- | :--- | :--- |
| **Backend Test Paketi** | `cd backend && python -m pytest tests/ -v` | **116 passed, 2 skipped, 0 failed** |
| **Web Birim Testleri** | `cd web && pnpm test` (veya `npm test`) | **11 passed (4 dosya)** |
| **Web Production Build** | `cd web && pnpm run build` (veya `npm run build`) | **Başarılı (0 hata)** |
| **Model 1 Test Paketi** | `python -m pytest ai/Model1/tests/ -q` | **83 passed** |
| **Model 2 Test Paketi** | `python -m pytest ai/Model2/tests/ -q` | **16 passed** |
| **Android Unit Testleri** | `cd android && .\gradlew.bat :app:testDebugUnitTest` | **Başarılı** |
| **Android APK Derleme** | `cd android && .\gradlew.bat :app:assembleDebug` | **Başarılı (`app-debug.apk`)** |

> [!NOTE]
> Test sonuçları, gerçekten çalıştırılan komutların çıktısına göre raporlanmalıdır. GitHub Actions üzerinde başarısız olan bir iş, başarılı olarak işaretlenmemelidir.

---

## API ve Teknik Dokümantasyon

| Belge | İçerik |
| :--- | :--- |
| [`contract/openapi.json`](contract/openapi.json) | API sözleşmesi |
| [`docs/architecture.md`](docs/architecture.md) | Sistem mimarisi |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | Veri modeli |
| [`docs/API.md`](docs/API.md) | API uç noktaları |
| [`docs/DEMO.md`](docs/DEMO.md) | Demo senaryoları |
| [`docs/ML.md`](docs/ML.md) | Makine öğrenmesi dokümantasyonu |
| [`docs/AI_RAPORU.md`](docs/AI_RAPORU.md) | Model deneyleri ve değerlendirmeleri |
| [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md) | Test sonuçları |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Güvenlik politikaları |
| [`docs/SENKRON.md`](docs/SENKRON.md) | Android ve merkezi veritabanı senkronizasyonu |

---

## Güvenlik ve Bilinen Sınırlamalar
- Demo hesapları yalnızca test amaçlıdır.
- Gizli anahtarlar ve parolalar kaynak koduna veya Git geçmişine eklenmemelidir.
- Gerçek saha verisiyle doğrulanmamış makine öğrenmesi modelleri üretime hazır kabul edilmemelidir.
- Hammadde ve mamul izlenebilirliği, gerçek kayıt ilişkilerine dayanmalıdır.
- Çevrimdışı satışlar senkronizasyon sırasında sunucu tarafında yeniden doğrulanmalıdır.
- CI başarısızlıkları ve çalıştırılmamış testler açıkça raporlanmalıdır.
- Yerel geliştirme yapılandırması doğrudan üretim ortamında kullanılmamalıdır.

---

## Katkı ve Geliştirme
Değişiklik yapmadan önce ilgili modülün dokümantasyonunu ve testlerini inceleyin. Pull request göndermeden önce:
1. Değişiklikleri gözden geçirin (`git diff`).
2. Etkilenen testleri çalıştırın.
3. Gizli bilgi ve hassas dosyaları kontrol edin.
4. Test sonuçlarını ve bilinen sınırlamaları açıklayın.

---
**Proje:** AVATAR Yarışması  
**Depo:** [https://github.com/Yusuffmiraccc/avatar-yarisma](https://github.com/Yusuffmiraccc/avatar-yarisma)
