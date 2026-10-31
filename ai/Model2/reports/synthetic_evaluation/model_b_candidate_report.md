# Model B sentetik aday karşılaştırma raporu

Koşu: 24.10.2026; Python 3.12.10 / scikit-learn 1.9.1. Veri sürümü `model-b-synthetic-v1`, split hash `22131f7dcaff44a062b7ef6624f1455e22dd0ddddcaca80c5d87e7d5239993e5`.

Veri tümüyle sentetik/simüledir. Kullanılan özellikler `hayvan_turu`, `karkas_agirligi_kg`; sekiz çıktı hedefi kg'dır. Baseline oranları yalnız train'den hesaplandı. Kategorik kodlama/ölçekleme yalnız model pipeline içindedir. Aday seçimi validation setinde normalize hedef MAE'si ile yapılmıştır; Ridge seçildi. Test seti fit/seçim için kullanılmadı. Testte baseline, Ridge ve Random Forest metrikleri karşılaştırma amacıyla bir kez hesaplandı.

## Test seti toplu karşılaştırma

| Model | MAE kg (tüm hedef değerleri) | RMSE kg (tüm hedef değerleri) | R² (uniform average) | Ortalama normalize hedef MAE / baseline |
|---|---:|---:|---:|---:|
| Tür bazlı ortalama verim oranı baseline | 1,8283 | 3,4431 | 0,9027 | 1,0000 |
| Ridge (validation'da seçilen) | 1,8439 | 3,4556 | 0,9022 | 1,0079 |
| Random Forest | 1,9412 | 3,6900 | 0,8942 | 1,0523 |

Bu holdoutta hiçbir ML adayı baseline'ı geçmedi. Bu yüzden Ridge yalnızca sentetik teknik aday olarak kaydedildi; API'de üretim modeli değildir. Yeni pooled metrics, paketteki mevcut `ModelB_sentetik_model_degerlendirme.csv` ve `ModelB_hedef_bazli_metrikler.csv` dosyalarına da aynı koşudan tekrar yazıldı.

## Hedef bazlı ölçümler

Her hedef/model için test örnek sayısı (n=180), MAE, RMSE ve R² `model_b_candidate_metrics.csv` dosyasındadır. Aynı sayılar ve validation ölçümleri `model_b_candidate_metrics.json` dosyasındadır. MAE ortalama mutlak hata; RMSE büyük hatalara daha çok ağırlık veren hata; R² açıklanan varyans oranıdır. Hata birimi kg'dır.

Train artefaktı ve JSON rapor iki ardışık koşuda byte düzeyinde aynı SHA-256 değerini verdi. Random Forest tek worker (`n_jobs=1`) kullanır; seed 20261024'tür.

## Kullanım ve sınırlama

Artefakt `models/model_b_synthetic_candidate.joblib` olarak ayrı yazılır ve `source_type=synthetic`, `production_ready=false` taşır; eğitim SHA-256 içeren `model_b_synthetic_candidate.manifest.json` sidecar'ını üretir. Mevcut API `model_b_production.joblib` ve eşleşen JSON manifest arar; status hash'i kontrol eder, model pickle dosyasını açmaz. Tahmin route'u API anahtarı kontrolünden sonra manifest ve artifact byte hash'ini doğrular ve aynı açık dosya tanıtıcısından joblib'i yükler; yalnız `source_type=measured`/`production_ready=true` eşleşen bundle kabul edilir. Hash tek başına dosyanın güvenilir kaynaktan geldiğini veya bilimsel/saha doğruluğunu ispatlamaz; aynı güvenilmeyen kaynağın manifest ve modeli birlikte değiştirmesine karşı imza/attestation gerekir. Üretim artefaktı yoktur. Gerçek veriyle bağımsız hayvan/grup ayrımlı test ve kesim hedefi/ölçüm standardı teyidi olmadan bu metrikler sahaya taşınamaz.
