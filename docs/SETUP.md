# AVATAR — Kurulum ve Çalıştırma Kılavuzu (SETUP)

Bu belge, AVATAR Yapay Zekâ Yarışması projesinin yerel geliştirme (Windows 11) ve Docker orkestrasyonu ortamlarında baştan sona nasıl kurulacağını, çalıştırılacağını ve test edileceğini açıklar.

---

## 1. Ön Gereksinimler

- **İşletim Sistemi:** Windows 10/11, macOS veya Linux
- **Python:** 3.11, 3.12 veya 3.14 (sanal ortam ile)
- **Node.js:** v18+ veya v20+ ve `npm` / `pnpm`
- **Docker & Docker Compose:** Docker Desktop (isteğe bağlı, konteynerleştirilmiş çalıştırma için)
- **Android:** Android Studio Jellyfish/Koala veya JDK 17 + Android SDK (API 35)

---

## 2. Hızlı Başlangıç (Docker ile Tek Komutla)

Docker Compose ile veritabanı (MySQL 8.4), önbellek (Redis 7), API sunucusu (FastAPI), Web yönetim paneli (Nginx + React SPA) ve idempotent `demo-seed` servisi tek komutla ayağa kaldırılabilir:

```powershell
# Proje kök dizininde
docker compose up -d --build
```

> [!NOTE]
> `demo-seed` servisi başlangıçta otomatik olarak veritabanı şemasını hazırlar (`alembic upgrade head`), ardından referans ve demo verilerini yükler ve başarıyla sonlanır. Seed işlemi tamamen **idempotent**'tir; yani tekrar çalıştırıldığında mükerrer kayıt üretmez. `ENVIRONMENT != "local"` olduğunda ise üretim güvenliği gereği otomatik olarak atlanır.

Servislerin adresleri:
- **Web Yönetim Paneli:** [http://localhost:5173](http://localhost:5173)
- **Backend REST API Dokümantasyonu (Swagger):** [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **Sağlık Durumu Endpoint'i:** [http://localhost:8000/health/ready](http://localhost:8000/health/ready)
- **MySQL Veritabanı:** `localhost:3307` (Kullanıcı: `avatar`, Şifre: `change-me-local-only`)
- **Redis:** Yalnızca Docker iç ağı (`avatar_default`) üzerinde izole (Dış porta kapalıdır).

> [!CAUTION]
> **Veri Güvenliği Uyarısı:** Servisleri durdururken kesinlikle `-v` (`--volumes`) parametresi **kullanmayın**! `-v` parametresi veritabanı volume'larını silerek veri kaybına yol açar.
>
> Güvenli durdurma komutu:
> ```powershell
> docker compose down
> ```

---

## 3. Bileşen Bazlı Manuel Kurulum (Windows)

### 3.1 Backend & REST API Kurulumu

```powershell
cd backend

# 1. Sanal ortamı oluşturun ve aktifleştirin
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Bağımlılıkları kurun
pip install -r requirements.txt

# 3. Ortam dosyasını kopyalayın
Copy-Item .env.example .env

# 4. Veritabanı migration'larını uygulayın (MySQL veya SQLite fallback)
alembic upgrade head

# 5. Tekrarlanabilir demo verilerini yükleyin
python -m scripts.seed_demo

# 6. API sunucusunu başlatın
uvicorn app.main:app --reload --port 8000
```

### 3.2 Web Yönetim Paneli Kurulumu

```powershell
cd web

# 1. Bağımlılıkları kurun
npm install

# 2. Birim testlerini çalıştırın (11 test)
npm test

# 3. Prodüksiyon derlemesini test edin
npm run build

# 4. Geliştirme sunucusunu başlatın
npm run dev
# Panel: http://localhost:5173 (Varsayılan olarak localhost:8000 API'sine bağlanır)
```

### 3.3 Android Mobil Satış Uygulaması

> [!NOTE]
> Android uygulaması Kotlin ve Jetpack Compose ile geliştirilmiş yerel bir mobil uygulamadır. Linux/Docker ortamında değil; doğrudan fiziksel bir Android telefonda veya Android Studio emülatöründe çalıştırılır. Bu nedenle Docker Compose mimarisinden ayrı olarak derlenir ve kurulur.

```powershell
cd android

# 1. Birim testlerini çalıştırın (BigDecimal, Barkod, Offline Auth, Idempotency)
.\gradlew.bat testDebugUnitTest

# 2. Debug APK oluşturun
.\gradlew.bat assembleDebug

# 3. Bağlı cihaza veya emülatöre yükleyin
.\gradlew.bat installDebug

# Not: Android emülatöründen host makinedeki backend'e erişirken 10.0.2.2 adresi kullanılır.
# Fiziksel cihaz için ters vekil (reverse proxy):
adb reverse tcp:8000 tcp:8000
```

APK Çıktı Konumu:
`android/app/build/outputs/apk/debug/app-debug.apk`

---

## 4. Demo Kullanıcı Bilgileri

Tüm kullanıcı hesaplarının parolası: **`Avatar-Demo-2026!`**

| Rol | E-Posta | Açıklama ve İzin Kapsamı |
|---|---|---|
| **Yönetici (Admin)** | `admin@avatar.demo` | Tam yetki: EKP ve karkas maliyetleri, ayarlar, kullanıcılar, audit logları. |
| **Operatör** | `operator@avatar.demo` | Üretim, parçalama, stok hareketleri, fire kayıtları ve ML çalıştırma. |
| **Saha Satış** | `sales@avatar.demo` | Android satış uygulaması, liste fiyatlı satış, sevkiyat; **maliyetler gizlidir**. |
| **İzlenebilirlik** | `trace@avatar.demo` | Şecere izleme, geri çağırma (recall) aktivasyonu, lot blokajı. |
| **İzleyici** | `viewer@avatar.demo` | Salt-okunur operasyonel izleme; **maliyetler gizlidir**. |

---

## 5. Doğrulama ve Test Komutları

Backend testlerinin tamamını çalıştırmak için:
```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_costing.py backend/tests/test_standalone_flows.py -v
```

Web testlerini çalıştırmak için:
```powershell
cd web && npm test
```

Yapay zekâ değerlendirme raporunu yeniden üretmek için:
```powershell
cd backend && python -m scripts.ai_report
```

OpenAPI sözleşmesini dışa aktarmak için:
```powershell
cd backend && python -m scripts.export_openapi
```
