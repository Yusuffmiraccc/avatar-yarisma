# AVATAR — Bütünleşik Üretim, Gerçek Maliyet (EKP), Satış ve Lot İzlenebilirliği Sistemi

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Web-React%2019%20%7C%20TypeScript-61DAFB.svg)](https://react.dev)
[![Kotlin](https://img.shields.io/badge/Android-Kotlin%20%7C%20Compose-7F52FF.svg)](https://kotlinlang.org)
[![MySQL](https://img.shields.io/badge/Database-MySQL%208.4%20%7C%20Room%20SQLite-4479A1.svg)](https://www.mysql.com)
[![scikit-learn](https://img.shields.io/badge/ML-scikit--learn-F7931E.svg)](https://scikit-learn.org)

Bu proje, **AVATAR Yapay Zekâ Yarışması Değerlendirme Belgesi (`AVATAR_Assessment.pdf`)** temel gereksinimlerini eksiksiz karşılayan; hammadde kabulünden dış fason üretime, gerçek birim maliyet (EKP) hesabından kuzu parçalamaya, çok kademeli lot şeceresinden geri çağırma (recall) yönetimine, Kotlin Android çevrimdışı satış uygulamasından makine öğrenmesi tahmin modellerine kadar birbiriyle tam entegre bir kurumsal üretim ve izlenebilirlik yazılımıdır.

---

## 1. Mimari Bileşenler ve Tamamlanma Durumu

| Modül | Teknoloji | Konum | Durum |
|---|---|---|---|
| **Backend & REST API** | Python, FastAPI, SQLAlchemy 2, Alembic, MySQL 8.4, Redis | `backend/` | **Çalışıyor & Test Edildi** (Sözleşme korundu; Redis kesintisinde giriş limiti kapalı başarısız olur (fail-closed)) |
| **API Sözleşmesi** | OpenAPI 3.1 Sözleşmesi | `contract/openapi.json` | **Güncel & Birebir Uyumlu** |
| **Web Yönetim Paneli** | React 19, TypeScript, Vite, Tailwind CSS | `web/` | **Çalışıyor & Test Edildi** (11/11 birim test geçti, 0 hata prodüksiyon derlemesi) |
| **Android Mobil Uygulama** | Kotlin 2.1, Jetpack Compose, Material 3, Room (SQLite), Retrofit, WorkManager | `android/` | **Tam Kodlandı & Testleri Hazır** (Offline kuyruk, UUID Idempotency, Bloke lot engeli, `stock_movement_id` kaydı) |
| **Yapay Zekâ (ML)** | Python, scikit-learn, pandas | `backend/app/ml/`, `ai/` | **Eğitildi & Değerlendirildi** (Model A: %37 iyileşme, Model B: %31 iyileşme, HMAC imzalı artefaktlar) |
| **Merkezi Veritabanı** | MySQL 8.4 (Tek doğruluk kaynağı) | `database/` | **Tam Şema & Migration Hazır** |

---

## 2. Hızlı Başlangıç (Windows & Docker)

### 2.1 Demo Kullanıcı Girişleri
Tüm kullanıcıların parolası: **`Avatar-Demo-2026!`**

- **Yönetici:** `admin@avatar.demo` (Tüm modüller, ayarlar ve maliyetler)
- **Operatör:** `operator@avatar.demo` (Üretim, parçalama ve stok operasyonları)
- **Saha Satış:** `sales@avatar.demo` (Android satış uygulaması, liste fiyatıyla satış; maliyetler gizlidir)
- **İzlenebilirlik:** `trace@avatar.demo` (İleri/geri lot takibi ve recall aktivasyonu)
- **İzleyici:** `viewer@avatar.demo` (Salt okunur izleme; maliyetler gizlidir)

---

### 2.2 Backend Servisini Başlatma

```powershell
cd backend
# 1. Ortam dosyasını hazırlayın
Copy-Item .env.example .env

# 2. Docker ile MySQL veritabanını başlatın
docker compose up -d mysql

# 3. Veritabanı migration'larını uygulayın
alembic upgrade head

# 4. Tekrarlanabilir demo verilerini (ET-2026-001 senaryosu + sentetik geçmiş) yükleyin
python -m scripts.seed_demo

# 5. API sunucusunu başlatın (http://localhost:8000/api/v1/docs)
uvicorn app.main:app --reload --port 8000
```

---

### 2.3 Web Yönetim Panelini Başlatma

```powershell
cd web
# 1. Bağımlılıkları yükleyin
pnpm install

# 2. Geliştirme sunucusunu başlatın (http://127.0.0.1:5173)
pnpm dev
```

Web panelinde çalıştırılabilir komutlar:
```powershell
pnpm test          # 11 birim ve bileşen testini çalıştırır
pnpm run build     # TypeScript tip denetimi ve Vite prodüksiyon derlemesi yapar
```

---

### 2.4 Android Mobil Satış Uygulamasını Başlatma

```powershell
cd android

# 1. Emülatör veya USB bağlı cihaz için derleme
./gradlew :app:assembleDebug

# 2. Birim testlerini çalıştırma (BigDecimal, Validator, Idempotency)
./gradlew :app:testDebugUnitTest

# 3. Cihaza yükleme
./gradlew :app:installDebug

# Fiziksel cihaz kullanılıyorsa port yönlendirmesi:
adb reverse tcp:8000 tcp:8000
```

---

## 3. Temel İş Mantığı ve Değerlendirme Senaryoları

### 3.1 Dış Hizmetle Üretim ve Gerçek Maliyet (EKP)
- **Referans Formülü:**
  $$\text{Toplam Maliyet} = \text{Tüketilen Hammadde Maliyeti} + \text{Dış Hizmet Faturası} + \text{Ek Maliyetler}$$
  $$\text{Gerçek EKP} = \frac{\text{Toplam Maliyet}}{\text{Sağlam Mamul Miktarı}}$$
- **Demo Doğrulaması:**
  - 100 kg et (970 €) + 2 kg baharat (48 €) + 5 kg bağırsak (58 €) = 1.076,00 € hammadde
  - 85 paket × 5,50 € = 467,50 € dış hizmet faturası
  - Toplam Maliyet: **1.543,50 €**
  - Üretim: **85 paket** `SUC-2026-045`
  - EKP: $\frac{1.543,50}{85} = 18,1588... \longrightarrow \mathbf{18,16\text{ €/paket}}$.

### 3.2 Bütün Kuzu Parçalama ve Tutarsızlık Tespiti
- 25 kg kuzu alımı, fatura 351,00 €, beyan birim fiyat 11,50 €/kg.
- PDF belgesindeki tutarsızlık ($25 \times 11,50 = 287,50 \neq 351,00$ ve parça toplamı 22 kg) sessizce düzeltilmez; sistem açık uyarı ve `weight_variance_records` oluşturur.
- Maliyetler `BY_WEIGHT` yöntemiyle kuruşu kuruşuna dağıtılır; artık pay son satıra aktarılır.

### 3.3 Lot İzlenebilirliği ve Geri Çağırma (Recall)
- `ET-2026-001` hammadde lotunda kalite sorunu tespit edildiğinde `RCL-2026-001` aktive edilir.
- Sistem hammadde $\rightarrow$ üretim emri (`URT-2026-045`) $\rightarrow$ mamul lotu (`SUC-2026-045`) $\rightarrow$ sevkiyatlar (Market A: 30, Market B: 25, Market C: 30 paket) ilişkisini anında tespit eder.
- Mamul lotu kilitlenir; Android satış uygulamasında bloke lotun satışı engellenir; eski önbellekle gönderilen satışlar da backend tarafından `409 LOT_BLOCKED` ile reddedilir.

### 3.4 Android SQLite ↔ MySQL Senkronizasyonu ve Idempotency
- MySQL tek doğruluk kaynağı; Android Room yerel önbellek ve çevrimdışı kuyruktur.
- Satış onayında yerel `client_uuid` üretilir; `Idempotency-Key` olarak sunucuya iletilir; ağ kesintilerinde mükerrer satış oluşmaz.
- Satış satırında lot, miktar, sabit liste fiyatı ve sunucudan dönen `stock_movement_id` kalıcı olarak saklanır.

---

## 4. Dokümantasyon İndeksi (`docs/`)

- [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md): Aşamalı uygulama planı ve durum analizi.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): Katmanlı sistem mimarisi, veri akışları ve işlem sınırları.
- [`docs/SENKRON.md`](docs/SENKRON.md): Android SQLite/Room ile MySQL senkronizasyon yaklaşımı.
- [`docs/ML.md`](docs/ML.md): Model A ve Model B veri kaynakları, algoritmaları, metrikleri ve sınırları.
- [`docs/AI_RAPORU.md`](docs/AI_RAPORU.md): Bilimsel ML deneyleri ve ölçülen çapraz doğrulama raporu.
- [`docs/DEMO.md`](docs/DEMO.md): Yarışma jürisi için adım adım demo icra kılavuzu.
- [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md): Çalıştırılan testler, süreler ve gerçek çıktılar.
- [`docs/SECURITY.md`](docs/SECURITY.md): Yetkilendirme matrisi, Argon2id, token rotation ve güvenlik politikaları.
- [`docs/SOZLESME.md`](docs/SOZLESME.md): Mimari kararlar ve çelişki çözüm kuralları.
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md): Veritabanı tabloları, ilişkiler ve bütünlük kısıtları.
- [`docs/API.md`](docs/API.md): REST API uç noktaları ve istek/yanıt örnekleri.
- [`docs/handoff/ACCEPTANCE_CRITERIA.md`](docs/handoff/ACCEPTANCE_CRITERIA.md): Kabul kriterlerinin tamamlanma durumu.
