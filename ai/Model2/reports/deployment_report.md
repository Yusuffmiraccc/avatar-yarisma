# Model 2 (Karkas Parçalama) Dağıtım ve Çalıştırma Raporu

**Tarih:** 01.11.2026  
**Servis Adı:** `avatar-model2-api`  
**İmaj:** `avatar-model2-api:local`  
**Mimari:** Bağımsız FastAPI Python 3.12 Mikroservisi  
**Bağlantı Noktası:** `127.0.0.1:8002:8000`

---

## 1. Dağıtım Mimarisi ve Konfigürasyonu

Model 2, AVATAR ana backend'inden bağımsız olarak çalışabilen, yüksek güvenlikli konteyner mimarisine sahiptir:

```
[ İstemci / Saha Kullanıcısı ]
               │
               ▼  HTTP Port 8002
┌────────────────────────────────────────────────────────┐
│ Konteyner: avatar-model2-api                           │
│  - Salt Okunur Kök Dosya Sistemi (read_only: true)     │
│  - Yetki Yükseltme Koruması (no-new-privileges: true)  │
│  - Tüm Linux Yetkileri Kaldırılmış (cap_drop: ALL)    │
│  - /tmp tmpfs alanı                                    │
│                                                        │
│  Uygulama: FastAPI (Uvicorn 0.54)                      │
│                                                        │
│  Salt Okunur Hacim:                                    │
│    ./models -> /app/Model2/models:ro                   │
│                                                        │
│  Kalıcı Veri Hacmi:                                    │
│    model2_audit_data -> /app/Model2/var                │
│    (SQLite: model_b_audit.sqlite3)                     │
└────────────────────────────────────────────────────────┘
```

---

## 2. Ortam Değişkenleri (.env.example)

| Değişken Adı | Varsayılan / Örnek Değer | Açıklama |
|---|---|---|
| `APP_ENV` | `production` | Çalışma ortamı (`production`, `development`, `test`). |
| `API_KEY` | `change-this-to-a-strong-secret-key` | API erişimini koruyan gizli anahtar. Üretimde zorunludur. |
| `MODEL_B_DIR` | `/app/Model2/models` | Model artefaktı ve manifest dosyalarının konumu. |
| `MODEL_B_AUDIT_DB` | `/app/Model2/var/model_b_audit.sqlite3` | Tahmin ve gerçekleşen ölçümlerin kaydedildiği SQLite dosyası. |
| `PYTHONDONTWRITEBYTECODE` | `1` | Salt okunur dosya sisteminde .pyc yazılmasını engeller. |
| `PYTHONPATH` | `/app` | Python modül çözümleme kökü. |

---

## 3. Dağıtım Adımları

### 3.1. Docker İmajını Derleme
```powershell
docker compose -f ai/Model2/docker-compose.yml build model2-api
```

### 3.2. Servisi Başlatma
```powershell
$env:API_KEY = "guclu-bir-anahtar-belirleyin"
docker compose -f ai/Model2/docker-compose.yml up -d
```

### 3.3. Servis Sağlık Durumunu İzleme
```powershell
docker ps -f "name=avatar-model2-api"
Invoke-RestMethod -Uri "http://127.0.0.1:8002/health"
Invoke-RestMethod -Uri "http://127.0.0.1:8002/v1/models/status"
```

### 3.4. Servisi Durdurma
```powershell
$env:API_KEY = "guclu-bir-anahtar-belirleyin"
docker compose -f ai/Model2/docker-compose.yml down
```

---

## 4. Uç Nokta Davranış Tablosu

| Uç Nokta | Metot | Kimlik Doğrulama | Model Durumu | Beklenen Yanıt Kodu |
|---|---|---|---|---|
| `/health` | GET | Hayır | Bağımsız | `200 OK` |
| `/v1/models/status` | GET | Hayır | Model 2 | `200 OK` |
| `/v1/predict/carcass-cuts` | POST | Evet (`x-api-key`) | Üretim (Measured) | `503` (Mevcut durumda measured model yok) |
| `/v1/predict/carcass-cuts/experimental` | POST | Evet (`x-api-key`) | Pilot (Synthetic) | `200 OK` (`experimental: true`) |
| `/v1/actual/carcass-cuts` | POST | Evet (`x-api-key`) | Bağımsız | `200 OK` |
| `/v1/evaluate/carcass-cuts/{id}` | GET | Evet (`x-api-key`) | Bağımsız | `200 OK` |

---

## 5. Doğrulama Özeti

Tüm uç noktalar ve güvenlik mekanizmaları hem Docker konteyneri üzerinde hem de 16 birim/entegrasyon testi ile `%100` başarıyla doğrulanmıştır.
