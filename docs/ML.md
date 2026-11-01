# AVATAR — Makine Öğrenmesi (ML) Modelleri ve Değerlendirme Raporu

Bu belge, AVATAR Yapay Zekâ Yarışması kapsamında geliştirilen iki zorunlu makine öğrenmesi modelinin (Model A ve Model B) tasarımını, veri işleme hattını, algoritmalarını, baseline karşılaştırmalarını, ölçülen metriklerini ve operasyonel sınırlarını tanımlar.

---

## 1. İlkeler ve Dürüstlük Kriterleri

1. **Sentetik Veri Şeffaflığı:** Gerçek ticari işletme kayıtları gizlilik nedeniyle mevcut değildir. Eğitim ve doğrulama verisi `app/ml/synthetic.py` tarafından üretilen sentetik DEMO verilerdir (`is_demo=True`).
2. **Asla Yüksek Doğruluk İddiası Uydurulmaz:** Raporlanan metrikler kod tarafından bizzat ölçülmüş gerçek değerlerdir; elle yazılmış başarı iddiası yoktur.
3. **Her Zaman Bir Baseline ile Karşılaştırma:** Model başarısı mutlak sayılarla değil, endüstri standardı basit bir baseline (ortalama verim / hayvan türü ortalamaları) karşısındaki hata düşüşüyle (MAE/RMSE iyileşme yüzdesi) ölçülür.
4. **Veri Sızıntısının (Data Leakage) Önlenmesi:** Özellik çıkarımı ve ölçekleme K-Fold döngüsü içinde `Pipeline` ve `ColumnTransformer` ile izole edilmiştir. Ayrıca son %20 zaman sıralı (temporal) holdout seti ayrılmıştır.
5. **Karar Desteği İlkesi:** ML tahminleri karar desteğidir. Kesin stok bakiyesi, EKP maliyeti ve lot izlenebilirliği ilişkisel veritabanı kayıtlarından hesaplanır; ML arızası veya yokluğu operasyonu durduramaz.

---

## 2. Model A — Dış Hizmetle Üretim Verimi ve EKP Tahmini

### 2.1 Problem Tanımı ve Hedef
- **Girdi:** Üretim emrinde kullanılacak hammaddelerin miktarları, maliyetleri, tedarikçi, reçete özellikleri ve ay.
- **Hedef:** `yield_ratio` (sağlam çıktı paket adedi / toplam girdi kg).
- **Türetilen Çıktılar:**
  - Beklenen sağlam mamul miktarı: $\text{qty} = \text{yield\_ratio} \times \text{total\_input\_kg}$
  - Tahmini EKP (€/paket): $\text{EKP} = \frac{\text{input\_cost}}{\text{qty}} + \text{service\_unit\_price}$
  - %95 Güven Aralığı: $\text{qty} \pm 1.96 \times \sigma_{\text{yield}} \times \text{total\_input\_kg}$

### 2.2 Öznitelikler (Features)
- Sayısal: `total_input_kg`, `main_share` (ana et girdi oranı), `other_ratio` (baharat/bağırsak oranı), `cost_per_kg`, `month`.
- Kategorik: `supplier_id` (`OneHotEncoder`).

### 2.3 Aday Modeller ve Baseline
- **Baseline:** `BASELINE_MEAN` (eğitim kümesindeki ortalama verim oranı).
- **Aday 1:** `RIDGE` (L2 regülarizasyonlu doğrusal model, standartlaştırılmış özellikler).
- **Aday 2:** `GRADIENT_BOOSTING` (150 estimator, max_depth=2, learning_rate=0.05).

### 2.4 Ölçülen Değerlendirme Sonuçları (5-Katlı Çapraz Doğrulama)

| Model | Çıktı MAE (paket) | Çıktı RMSE | Çıktı MAPE % | EKP MAE (€) | EKP MAPE % |
|---|---|---|---|---|---|
| **BASELINE_MEAN** | 4.04 | 5.18 | 3.81 | 0.4824 | 2.65 |
| **RIDGE** | 2.61 | 3.30 | 2.49 | 0.3158 | 1.74 |
| **GRADIENT_BOOSTING** | 2.53 | 3.23 | 2.39 | 0.3030 | 1.67 |

- **Baseline'a Göre İyileşme (Seçilen Model: GRADIENT_BOOSTING):**
  - Çıktı Miktarı MAE İyileşmesi: **%37.55** (4.04 -> 2.53 paket)
  - EKP MAE İyileşmesi: **%37.19** (0.4824 -> 0.3030 €/paket)
- **Zaman Sıralı Holdout (Son %20 Örnek, n=24):** Model MAE 2.94 paket vs Baseline MAE 3.71 paket. %95 aralık kapsama oranı: **%95.8**.
- **Model Seçim Kuralı:** `backend/app/ml/modeling.py` içindeki `train_production` fonksiyonu, 5-katlı çapraz doğrulamada en düşük çıktı MAE değerini veren adayı otomatik olarak seçer (`best = min(candidates, key=...)`). 120 örnekli üretim veri kümesinde GRADIENT_BOOSTING üstünlük sağlayarak seçilen model olmuştur.

---

## 3. Model B — Bütün Hayvan / Kuzu Parçalama Verimi Tahmini

### 3.1 Problem Tanımı ve Hedef
- **Girdi:** Hayvan türü (`KUZU`, `KOYUN`, `DANA`) ve giriş karkas ağırlığı (`input_weight`).
- **Hedef:** Karkastan çıkacak her bir parça (`BUT`, `SIRT`, `OMUZ`, `KABURGA`, `KIYMA`, `YANURUN`) ve `FIRE` için ağırlık oranlarının (`r_cut`) eşzamanlı çoklu tahmini.
- **Türetilen Çıktılar:**
  - Her parça için beklenen kg ağırlığı.
  - Toplam kullanılabilir et miktarı ve beklenen fire miktarı.

### 3.2 Aday Modeller ve Baseline
- **Baseline:** `BASELINE_ANIMAL_MEAN` (hayvan türüne göre geçmiş ortalama parça oranları).
- **Aday 1:** `RIDGE` (çok hedefli doğrusal regresyon).
- **Aday 2:** `RANDOM_FOREST` (150 karar ağacı, çoklu hedef regresörü).

### 3.3 Ölçülen Değerlendirme Sonuçları (5-Katlı Çapraz Doğrulama)

| Model | Genel MAE (kg / parça) | wMAPE % | Baseline'a Göre İyileşme % |
|---|---|---|---|
| **BASELINE_ANIMAL_MEAN** | 1.446 kg | 10.58 % | 0.00 % (referans) |
| **RIDGE** | 1.098 kg | 8.04 % | %24.07 |
| **RANDOM_FOREST** | 0.997 kg | 7.29 % | **%31.06** |

Parça bazında hata dağılımı (kg MAE):
- **BUT:** Model 1.488 kg vs Baseline 1.894 kg (iyileşme %21.4)
- **SIRT:** Model 0.798 kg vs Baseline 0.947 kg (iyileşme %15.7)
- **OMUZ:** Model 0.975 kg vs Baseline 1.130 kg (iyileşme %13.7)
- **FİRE:** Model 2.242 kg vs Baseline 4.309 kg (iyileşme %47.9)

---

## 4. Model Güvenliği, Bütünlük ve İmzalı Saklama

Model dosyaları rastgele serileştirilmiş pickle dosyaları olarak bırakılmaz:
1. `joblib` ile kaydedilen artefaktın SHA-256 karma değeri ve HMAC imzası `.manifest.json` dosyasına yazılır.
2. Yükleme sırasında (`modeling.load`) imza doğrulanır; artefakt kurcalanmışsa `ValueError: Artifact integrity verification failed` fırlatılır.
3. Model artefaktı içinde model sürümü (`version`), eğitim zamanı (`trained_at`), örnek sayısı (`n_samples`), ölçülen metrikler ve bilinen sınırlılıklar (`limitations`) ayrılmaz bir paket olarak saklanır.

---

## 5. API Entegrasyonu

- `POST /api/v1/ai/production-yield/predict`:
  ```json
  { "production_order_id": 45 }
  ```
  *Yanıt:* Model ve baseline tahminleri, beklenen EKP, %95 güven aralığı, model adı ve sürümü.
- `POST /api/v1/ai/butchering-output/predict`:
  ```json
  { "butchering_order_id": 1 }
  ```
  *Yanıt:* Parça bazında beklenen kg ağırlıkları, fire tahmini, baseline karşılaştırması.
- `POST /api/v1/ai/models/train`: Tüm modelleri yeniden eğitir, çapraz doğrulama yapar ve yeni sürümleri kaydeder.
- `GET /api/v1/ai/models`: Aktif model sürümlerini, örnek sayılarını ve metriklerini listeler.

---

## 6. Resmî hat ve ek araştırma

Yarışmanın AI-A ve AI-B modelleri bu belgede anlatılan `backend/app/ml` hattıdır. `ai/Model1` (sucuk/EKP, TL) ve `ai/Model2` (Model B) ürüne bağlı olmayan ek araştırma servisleridir. Ölçülen sonuçlar ve sınırlar için bkz. `docs/AI_RAPORU.md` Bölüm 8.
