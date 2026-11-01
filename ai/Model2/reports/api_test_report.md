# Model B (Model 2) API ve Uçtan Uca Doğrulama Raporu

**Doğrulama Tarihi:** 01.11.2026  
**Ortam:** Windows 11, Python 3.14 / Python 3.12 (Docker), Docker Desktop (Linux engine)  
**Hizmet Adı:** `avatar-model2-api`  
**Konteyner Portu:** `127.0.0.1:8002 -> 8000/tcp`  
**Saha Verisi Durumu:** Gerçek saha verisi yoktur. Tüm veriler (1.200 satır) sentetiktir. Üretim endpoint'i (`POST /v1/predict/carcass-cuts`) **HTTP 503 Fail-Closed** olarak korunmaktadır.

---

## 1. Birim ve Entegrasyon Testleri Özeti

Komut:
```powershell
$env:PYTHONPATH = "ai/Model2"
python -m pytest ai/Model2/tests/ -v
```

**Sonuç: 16 passed, 0 failed, 0 skipped in 3.06s**

### Test Listesi ve Kapsamı:
1. `test_health_and_status_are_model2_specific`: Liveness `/health` 200 döner, `/v1/models/status` yalnız Model 2 parametrelerini listeler (Model 1 anahtarları sızmaz).
2. `test_prediction_returns_503_without_measured_production_artifact`: Saha doğrulamalı measured artefakt yokken üretim endpoint'i 503 döner.
3. `test_prediction_requires_api_key`: `x-api-key` başlığı eksik veya geçersizken 401 Unauthorized döner.
4. `test_prediction_request_rejects_invalid_input[payload0-3]`: Geçersiz hayvan türü (`deve`), negatif ağırlık (`-1`), fazladan alan veya eksik alan 422 Unprocessable Entity ile reddedilir.
5. `test_prediction_rejects_hash_mismatch_before_deserialization`: Üretim manifestindeki SHA-256 hash'i dosya ile uyuşmazsa `joblib.load` çağrılmadan fail-closed (503) olur.
6. `test_synthetic_bundle_named_as_production_is_not_served`: Sentetik model adı üretim dosyası yapılsa dahi `source_type=synthetic` kontrolü ile deserialize edilmeden 503 döner.
7. `test_measured_prediction_actual_and_evaluation_flow`: Test fixture üretim modeliyle tam tahmin -> actual ölçüm -> sapma değerlendirme akışı.
8. `test_experimental_prediction_requires_api_key`: Deneysel uç nokta kimlik doğrulaması gerektirir (401).
9. `test_production_endpoint_still_fails_closed_when_candidate_is_present`: Sentetik aday modeli mevcutken dahi üretim endpoint'i (`/v1/predict/carcass-cuts`) kesinlikle 503 döner.
10. `test_experimental_prediction_with_real_candidate_model`: Sentetik aday modeli pilot uç noktada (`/v1/predict/carcass-cuts/experimental`) 200 döner; `experimental=True`, `production_ready=False`, `source_type="synthetic"` bayraklarını içerir.
11. `test_experimental_prediction_rejects_hash_mismatch`: Sentetik aday hash'i bozulduğunda deserialize edilmeden 503 döner.
12. `test_experimental_prediction_returns_503_when_no_candidate`: Aday manifesti veya artefaktı bulunamadığında 503 döner.
13. `test_experimental_prediction_actual_and_evaluation_flow`: Deneysel tahmin -> fiili tartım kaydı -> değerlendirme akışı SQLite audit tablosuna `is_experimental=1` olarak kaydedilir ve sapmalar doğru hesaplanır.

---

## 2. Canlı Docker Konteyner Doğrulaması

Konteyner: `avatar-model2-api` (`avatar-model2-api:local`)  
Port: `127.0.0.1:8002`  
Çalıştırma Komutu:
```powershell
$env:API_KEY = "test-pilot-key-12345"
docker compose -f ai/Model2/docker-compose.yml up -d
```

### 2.1. GET /health
```json
{
  "status": "ok",
  "service": "avatar-model2-api"
}
```
*HTTP 200 OK*

### 2.2. GET /v1/models/status
```json
{
  "service": "avatar-model2-api",
  "model_b_production_ready": false,
  "model_b_model_version": null,
  "model_b_data_version": null,
  "model_b_source_type": null,
  "model_b_candidate_available": true,
  "model_b_candidate_model_version": "model-b-ridge-20261024-synthetic-v1",
  "model_b_candidate_data_version": "model-b-synthetic-v1",
  "model_b_candidate_source_type": "synthetic",
  "model_b_candidate_production_ready": false,
  "model_b_feature_columns": ["hayvan_turu", "karkas_agirligi_kg"],
  "model_b_target_columns": [
    "but_kg", "sirt_kg", "omuz_kg", "kaburga_kg", "kiyma_kg",
    "yan_urun_kg", "kemik_yag_sinir_kg", "fire_kg"
  ],
  "model_notice": "Saha doğrulamalı measured üretim artefaktı mevcut değil. Sentetik aday üretim tahmin uç noktasında (predict/carcass-cuts) yüklenmez. Pilot/deneysel testler için /v1/predict/carcass-cuts/experimental kullanılabilir."
}
```
*HTTP 200 OK*

### 2.3. POST /v1/predict/carcass-cuts (Üretim Tahmin Uç Noktası)
İstek:
```json
{"hayvan_turu": "kuzu", "karkas_agirligi_kg": 22.5}
```
Yanıt:
```json
{"detail": "Model B saha doğrulamalı üretim artefaktı kullanıma hazır değil."}
```
*HTTP 503 Service Unavailable (Fail-closed prensibi kanıtlandı)*

### 2.4. POST /v1/predict/carcass-cuts/experimental (Deneysel Pilot Uç Noktası)
İstek:
```json
{"hayvan_turu": "kuzu", "karkas_agirligi_kg": 22.5}
```
Yanıt:
```json
{
  "predicted_cuts_kg": {
    "but_kg": 4.598,
    "sirt_kg": 2.503,
    "omuz_kg": 3.195,
    "kaburga_kg": 3.619,
    "kiyma_kg": 4.925,
    "yan_urun_kg": 2.265,
    "kemik_yag_sinir_kg": 0.546,
    "fire_kg": 0.769
  },
  "prediction_id": "190d0271-ac26-420b-a551-84f8bf668a89",
  "prediction_created_at_utc": "2026-11-01T08:20:10.289173+00:00",
  "model_version": "model-b-ridge-20261024-synthetic-v1",
  "data_version": "model-b-synthetic-v1",
  "source_type": "synthetic",
  "production_ready": false,
  "experimental": true,
  "model_notice": "DENEYSEL PİLOT TAHMİNİ: Saha ölçüm verisi toplanana kadar yalnızca test/pilot amaçlıdır. Ticari veya hukuki kararlar için üretimde kullanılamaz."
}
```
*HTTP 200 OK*

### 2.5. POST /v1/actual/carcass-cuts (Fiili Tartım Kaydı)
İstek:
```json
{
  "prediction_id": "190d0271-ac26-420b-a551-84f8bf668a89",
  "measured_at_utc": "2026-11-01T08:20:00+00:00",
  "actual_cuts_kg": {
    "but_kg": 4.600,
    "sirt_kg": 2.500,
    "omuz_kg": 3.200,
    "kaburga_kg": 3.600,
    "kiyma_kg": 4.900,
    "yan_urun_kg": 2.300,
    "kemik_yag_sinir_kg": 0.550,
    "fire_kg": 0.750
  }
}
```
Yanıt:
```json
{
  "prediction_id": "190d0271-ac26-420b-a551-84f8bf668a89",
  "recorded_at_utc": "2026-11-01T08:20:17.675672+00:00",
  "measured_at_utc": "2026-11-01T08:20:00+00:00",
  "actual_source_type": "measured"
}
```
*HTTP 200 OK*

### 2.6. GET /v1/evaluate/carcass-cuts/{id} (Sapma Kıyaslaması)
Yanıt:
```json
{
  "prediction_id": "190d0271-ac26-420b-a551-84f8bf668a89",
  "model_version": "model-b-ridge-20261024-synthetic-v1",
  "data_version": "model-b-synthetic-v1",
  "source_type": "synthetic",
  "is_experimental": true,
  "prediction_created_at_utc": "2026-11-01T08:20:10.289173+00:00",
  "actual_source_type": "measured",
  "actual_measured_at_utc": "2026-11-01T08:20:00+00:00",
  "actual_recorded_at_utc": "2026-11-01T08:20:17.675672+00:00",
  "comparison": {
    "but_kg": {"predicted_kg": 4.598, "actual_kg": 4.6, "deviation_kg": -0.002},
    "sirt_kg": {"predicted_kg": 2.503, "actual_kg": 2.5, "deviation_kg": 0.003},
    "omuz_kg": {"predicted_kg": 3.195, "actual_kg": 3.2, "deviation_kg": -0.005},
    "kaburga_kg": {"predicted_kg": 3.619, "actual_kg": 3.6, "deviation_kg": 0.019},
    "kiyma_kg": {"predicted_kg": 4.925, "actual_kg": 4.9, "deviation_kg": 0.025},
    "yan_urun_kg": {"predicted_kg": 2.265, "actual_kg": 2.3, "deviation_kg": -0.035},
    "kemik_yag_sinir_kg": {"predicted_kg": 0.546, "actual_kg": 0.55, "deviation_kg": -0.004},
    "fire_kg": {"predicted_kg": 0.769, "actual_kg": 0.75, "deviation_kg": 0.019}
  },
  "deviation_convention": "Fark = tahmin - gerçekleşen; pozitif değer fazla tahmini, negatif değer düşük tahmini gösterir."
}
```
*HTTP 200 OK*

---

## 3. Güvenlik ve Bütünlük Değerlendirmesi

1. **İki Aşamalı SHA-256 Denetimi:** Model dosyasının baytları diskten okunurken SHA-256 özet değeri çıkarılır ve manifestteki beklenen özet ile sabit zamanlı (`secrets.compare_digest`) karşılaştırılır. Uyuşmazlık veya eksiklik durumunda Python pickle/joblib deserialization motoru kesinlikle tetiklenmez.
2. **Konteyner Sertleştirme:**
   - `read_only: true` (kök dosya sistemi salt okunur)
   - `tmpfs: [/tmp]`
   - `security_opt: [no-new-privileges:true]`
   - `cap_drop: [ALL]`
   - `non-root` / izole volume (`model2_audit_data`)
3. **Fail-Closed Mimarisi:** Gerçek saha ölçümlü üretim modeli bulunmadığı müddetçe üretim endpoint'i 503 döner. Sentetik aday ise yalnızca açıkça `experimental: true` uyarısı taşıyan pilot uç noktasında denenebilir.
