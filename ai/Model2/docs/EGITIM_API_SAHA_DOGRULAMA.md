# Model B eğitim, API ve saha doğrulama prosedürü

## Eğitim ve değerlendirme

Python 3.12 ortamında, `ai/` repo dizininden:

```powershell
python -m Model2.training.train_model_b
python -m pytest -v
```

Veri sürümü `model-b-synthetic-v1`; özellikler `hayvan_turu`, `karkas_agirligi_kg`'dir. Hedefler, kayıt kimliği, toplam çıkış, denge farkı, oran ve post-process alanları girdi değildir. Preprocessing yalnız train'de fit edilir. Tür-bazlı ortalama verim oranı baseline'ı, Ridge ve Random Forest validation'da kıyaslanır. Validation'da baseline'a normalize hedef MAE oranı en iyi olan estimator seçilir; test seti fit/seçimde kullanılmaz ve bir kez raporlanır.

Artefakt `models/model_b_synthetic_candidate.joblib`; eğitim SHA-256 içeren `models/model_b_synthetic_candidate.manifest.json` sidecar'ını üretir. Metrik `reports/synthetic_evaluation/model_b_candidate_metrics.json` ve `.csv` dosyalarındadır. Bundle `source_type=synthetic`, `production_ready=false`. API adayı servis etmez.

## API ve kayıt akışı

Mevcut FastAPI uygulaması `ai/Model1/app/main.py` içindedir. Model B izlenebilirliği için Python stdlib SQLite ve `ai/Model2/sql/001_model_b_audit.sql` migration kullanılır; yol uygulama dosyasının konumundan AI köküne göre belirlenir. Veritabanı `MODEL_B_AUDIT_DB` ile değişir.

- `GET /v1/models/status`: model dosya geçerliliği, üretim durumu ve sürüm.
- `POST /v1/predict/carcass-cuts`: tür ve parçalama öncesi karkas kg alır; sadece `model_b_production.joblib` adlı, `production_ready=true`, `source_type=measured`, doğru şema/sürümde artefakt ve eşleşen, gerçek dosyanın SHA-256 özetiyle doğrulanan JSON manifestla çalışır. Eksik veya eski hash'siz manifest fail-closed olarak reddedilir. Gerçek saha artefaktı yoksa HTTP 503.
- Tahmin başarılı olduğunda input/output/model-veri sürümü ve UTC kayıt zamanı `model_b_predictions` tablosuna ayrı prediction ID ile yazılır.
- `POST /v1/actual/carcass-cuts`: prediction ID, tüm sekiz çıktı ağırlığı ve saat dilimi içeren gerçek `measured_at_utc` zamanıyla sonuçları ayrı `model_b_actuals` tablosuna yazar. API ayrıca kayıt zamanını kaydeder. Bilinmeyen ID 404; aynı tahmin için yinelenen gerçek kayıt 409.
- `GET /v1/evaluate/carcass-cuts/{prediction_id}`: tahmin ve sonraki gerçek kayıt mevcutsa her hedef için kg tahmin/gerçek/fark döndürür. Fark = tahmin - gerçekleşen; pozitif fazla, negatif düşük tahmin.

Tahmin, actual kaydı ve değerlendirme uçlarının tümü mevcut `_authorize` korumasını kullanır (değerlendirme ucu GET'tir): API_KEY ayarlıysa `x-api-key` gerekir; development/test dışı ortamda anahtar yoksa 503. SQLite DB hassas operasyon verisi içerebilir; Git dışında tutulmalı, erişimi sınırlandırılmalı ve yedekleme/saklama politikası tanımlanmalıdır. API kullanıcı tarafından iletilen gerçek ölçümü fiziksel olarak doğrulayamaz; `measured` akışı yalnız tartım sonrası kullanılmalıdır.

Üretim manifesti `model_version`, `data_version`, `source_type`, `production_ready`, `feature_columns`, `target_columns` ve 64 karakter hexadecimal `artifact_sha256` içermelidir. API manifest hash'ini kontrol etmeden joblib deserialize etmez; tahmin sırasında hash'i açılmış aynı dosya tanıtıcısından yeniden hesaplayıp o tanıtıcı üzerinden yükler. SHA-256 yalnızca manifestin beyan ettiği dosya byte'larının bütünlüğünü sağlar. Manifest ve joblib aynı güvenilmeyen kaynakta birlikte değiştirilebiliyorsa bu güven kökü değildir; imzalı veya erişimi ayrıca korunan dağıtım/manifest kanalı gerekir. Hash'siz eski production manifestleri otomatik olarak onarılmaz, 503 ile reddedilir.

Swagger `GET /docs`, sağlık `GET /health`. Örnek tahmin isteği:

```json
{"hayvan_turu":"kuzu","karkas_agirligi_kg":18.2}
```

Mevcut üretim artefaktı yoktur; beklenen tahmin cevabı 503'tür. Sentetik candidate dosyasını production filename ile değiştirmeyin.

## Saha doğrulama prosedürü

Genişletilmiş kayıt alanları için boş `templates/field_data/model_b_saha_verisi_v3.csv` dosyasını kullanın. Eski şablonlar geriye dönük uyumluluk için korunur. V3'te her ölçümün aşaması ve zaman damgası, tartım standardı, terazi kalibrasyonu, kategori tanımı, anonim kaynak/onay ve kalite kontrol durumu ayrı sütunlardadır.

1. Gerçek bireysel satırları `data/raw/measured/` içine yalnız kullanım hakkı/gizlilik onayı sonrası kaydedin.
2. Aynı anonim stabil animal ID ile karkas girdisini işlem öncesi, her hedef çıktıyı işlem sonrası tartın; her ölçümün fiziksel zamanı, aşaması, kg birimi, cihaz ve kalibrasyon bilgisini tutun.
3. Canlı/karkas ağırlığını ayırın; karkas sıcak/soğuk ve kemikli/kemiksiz tanımını verin.
4. Kesim standardı ve çıktı gruplarının sınır/örtüşme tanımını işletme ile onaylayın. Kütle dengesi ancak kategoriler aynı sınırda, aynı aşamada ve birbirini dışlayacak biçimde tartıldığında fiziksel kontroldür.
5. Aynı hayvanı bölmeler arasında dağıtmayın; gerçek hayvan/grup veya zaman/tesis bazlı bağımsız holdout kurun. Model seçimini train/validation ile yapın.
6. Gerçek testte baseline/Ridge/RF için hedef bazlı MAE/RMSE/R² ve örnek sayısı raporlayın; modelin sürüm ve veri kökenini saklayın. Bağımsız saha doğrulaması ve sorumlu onayı olmadan production artifact hazırlamayın.
