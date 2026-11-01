# AVATAR — Yapay Zeka Çalışması Değerlendirme Raporu

_Otomatik üretildi: `python -m scripts.ai_report` · 2026-10-29 · tüm sayılar bu çalıştırmada ölçüldü._

## 0. Önemli not: veri sentetiktir

Gerçek üretici verisi yoktur. Eğitim verisi `app/ml/synthetic.py` ile üretilen **sentetik DEMO** kayıtlardır (`is_demo=true`). Üreteç, üretim verimini girdi bileşimi, mevsim ve tedarikçiye; parça oranlarını hayvan türüne ve ağırlığa **bilerek** bağlar. Bu nedenle aşağıdaki iyileşme yüzdeleri *yöntemin ve değerlendirme hattının çalıştığını* gösterir, gerçek işletmede elde edilecek kazancı **garanti etmez**. Model, gerçek kayıtlarla yeniden eğitildiğinde aynı hat aynı ölçümleri üretir. Bölüm 4'teki deneyler bu iddianın sınırını gösterir.

## 1. Veri

| Küme | Kayıt | Hedef | Not |
|---|---|---|---|
| Üretim emri (A) | 120 | verim oranı (çıktı paket / girdi kg); EKP türetilir | referans emir dahil |
| Parçalama emri (B) | 150 | her parça ve fire için ağırlık oranı | 3 hayvan türü |

## 2. Model A — üretim verimi ve EKP

Yaklaşım: aday modeller **Ridge** ve **GradientBoosting**; özellikler: toplam girdi kg, ana girdi payı, diğer girdi oranı, kg başına maliyet, ay, tedarikçi. **Baseline:** eğitim kümesinin ortalama verimi. Doğrulama: 5-katlı çapraz doğrulama (out-of-fold) + son %20 zaman sıralı holdout. Seçilen: **GRADIENT_BOOSTING**.

### 2.1 Çapraz doğrulama (out-of-fold)

| Model | Çıktı MAE (paket) | Çıktı RMSE | Çıktı MAPE % | EKP MAE (€) | EKP MAPE % |
|---|---|---|---|---|---|
| BASELINE_MEAN | 4.04 | 5.18 | 3.81 | 0.4824 | 2.65 |
| RIDGE | 2.61 | 3.30 | 2.49 | 0.3158 | 1.74 |
| GRADIENT_BOOSTING | 2.53 | 3.23 | 2.39 | 0.3030 | 1.67 |

Seçilen modelin baseline'a göre MAE iyileşmesi: çıktı **%37.55**, EKP **%37.19**.

### 2.2 Zaman sıralı holdout (son %20, model hiç görmeden)

|  | Çıktı MAE | Çıktı MAPE % | EKP MAE (€) |
|---|---|---|---|
| Model | 2.94 | 2.61 | 0.3489 |
| Baseline | 3.71 | 3.05 | 0.4023 |

Holdout örnek sayısı: 24. %95 aralığın holdout kapsama oranı: **%95.8** (hedef ≈ %95). Aralık hedefin belirgin altında kalıyorsa gösterilen %95 aralığına tam güvenilmemeli; sigma, çapraz doğrulama hatalarının standart sapmasından alınır ve holdout küçüktür.

## 3. Model B — parçalama verimi

Yaklaşım: hayvan türü ve giriş ağırlığından her parça ve fire için ağırlık **oranı** tahmin edilir, kg'a çevrilir. Adaylar **Ridge** ve **RandomForest**. **Baseline:** hayvan türüne göre geçmiş ortalama oranlar. 5-katlı çapraz doğrulama. Seçilen: **RANDOM_FOREST**.

| Model | Genel MAE (kg / parça) | wMAPE % |
|---|---|---|
| BASELINE_ANIMAL_MEAN | 1.434 | 10.44 |
| RIDGE | 1.086 | 7.90 |
| RANDOM_FOREST | 0.962 | 7.01 |

Baseline'a göre MAE iyileşmesi: **%32.9**. %95 aralığın (out-of-fold) kapsama oranı: **%94.7**.

Parça bazında MAE (kg):

| Parça | Model | Baseline |
|---|---|---|
| BUT | 1.470 | 1.883 |
| FIRE | 2.142 | 4.317 |
| KABURGA | 0.528 | 0.666 |
| KIYMA | 0.631 | 0.727 |
| OMUZ | 0.967 | 1.120 |
| SIRT | 0.731 | 0.944 |
| YANURUN | 0.265 | 0.382 |

## 4. Dürüstlük deneyleri

Aşağıdaki sayılar her satırda 3 farklı rastgele alt örnek/gürültü tohumunun ortalamasıdır.

### 4.1 Veri miktarı arttıkça (öğrenme eğrisi) — baseline'a göre MAE iyileşmesi %

| Model | Kayıt sayısı | İyileşme % (çıktı / parça) | İyileşme % (EKP) |
|---|---|---|---|
| A (çıktı / EKP) | 30 | 20.0 | 19.7 |
| A (çıktı / EKP) | 60 | 29.4 | 27.7 |
| A (çıktı / EKP) | 90 | 37.7 | 36.7 |
| A (çıktı / EKP) | 120 | 36.3 | 35.6 |
| B (parça kg) | 30 | 19.5 | - |
| B (parça kg) | 60 | 23.9 | - |
| B (parça kg) | 90 | 29.1 | - |
| B (parça kg) | 150 | 32.1 | - |

30 kayıt altında sistem modeli eğitmez, baseline kullanır ve bunu `limitations` alanında bildirir.

### 4.2 Gürültü arttıkça — baseline'a göre MAE iyileşmesi %

| Model | Eklenen gürültü σ | İyileşme % (çıktı / parça) | İyileşme % (EKP) |
|---|---|---|---|
| A (verim oranına ek σ) | 0.0 | 37.5 | 37.2 |
| A (verim oranına ek σ) | 0.02 | 22.9 | 23.3 |
| A (verim oranına ek σ) | 0.05 | 5.3 | 6.4 |
| A (verim oranına ek σ) | 0.1 | -2.1 | -1.4 |
| B (oranlara ek σ) | 0.0 | 32.9 | - |
| B (oranlara ek σ) | 0.01 | 22.0 | - |
| B (oranlara ek σ) | 0.03 | 7.9 | - |
| B (oranlara ek σ) | 0.06 | 2.8 | - |

Gürültü arttıkça kazanç küçülür; kazanç, verideki gerçek sinyalin gücüne bağlıdır. Gerçek veride sinyal zayıfsa model baseline'ı geçemeyebilir; bu durumda yeniden eğitim aktif modeli korur (`app/ml/service.py::_promote`).

## 5. Anomali tespiti — IsolationForest ve kural tabanlı z-skoru

Etiketli gerçek anomali yoktur. Değerlendirme: mevcut kayıtların %5'ine bilinen anomaliler **enjekte edilir** (20 farklı tohum, ortalama). Üretimde üç tür: düşük verim (×0,78), maliyet sıçraması (×1,35) ve verim–maliyet ilişkisinin bozulması (verim +2σ ve EKP +2σ; normalde verim artınca EKP düşer, her değer tek başına 2,5σ eşiğinin altında kalır). Parçalamada: iki parçanın oranı kaymış bileşim; tek değişkenli kural her parça oranına ayrı ayrı iki yönlü bakar. Üretimde kural, serviste kullanılan tek değişkenli z-skorudur (|z| > 2.5); IsolationForest ise tüm özelliklere birlikte bakar (contamination=0.03).

### 5.1 Üretim (verim + EKP)

| Yöntem | Precision | Recall | F1 |
|---|---|---|---|
| Kural: z-skoru (>2,5σ) | 0.99 | 0.67 | 0.80 |
| IsolationForest | 1.00 | 0.67 | 0.80 |

Anomali türüne göre recall:

| Tür | z-skoru | IsolationForest |
|---|---|---|
| düşük verim | 1.00 | 0.95 |
| maliyet sıçraması | 1.00 | 0.95 |
| verim–maliyet ilişkisi bozuk | 0.00 | 0.10 |

### 5.2 Parçalama (bileşim kayması)

| Yöntem | Precision | Recall | F1 |
|---|---|---|---|
| Kural: z-skoru (>2,5σ) | 0.27 | 0.37 | 0.31 |
| IsolationForest | 0.23 | 0.16 | 0.19 |

**Sonuç: bu veride IsolationForest'ın z-skoruna belirgin bir üstünlüğü ölçülmedi.** Üretimde F1 benzer; verim–maliyet ilişkisi bozuk kayıtlarda ikisi de neredeyse hiç yakalamadı (contamination=0.03 yalnızca kayıtların ~%3'ünü işaretler, enjekte oran %5 olduğundan ve daha uç anomaliler önce sıralandığından recall sınırlı kalır); parçalamada daha kötüdür. Servis yalnızca z-skorunun işaretlemediği kayıtlara **ek**, düşük önemli (`MULTIVARIATE_ANOMALY`, INFO) uyarı üretir; tek başına karar verici değildir. Uyarılar insan incelemesi içindir; stok veya maliyet kaydını değiştirmez.

## 6. Örnek tahminler (referans senaryo)

Tahminler emir tamamlanmadan **önce** üretilmiş, modele o emir eğitimde gösterilmemiştir.

| Emir | Tahmin | Baseline | Gerçek | Sapma |
|---|---|---|---|---|
| URT-2026-045 | - | - | - | kayıtlı tahmin yok |
| PRC-2026-001 | - | - | - | kayıtlı tahmin yok |

Not: PDF'teki kuzu örneğinde (PRC-2026-001) yalnızca üç parça kayıtlıdır (12 + 6 + 4 = 22 kg), fire kaydı yoktur; sentetik veride ise kesim yedi kalemlidir. Parçalama satırlarındaki büyük sapmalar model hatasını değil, bu ürün karması farkını yansıtır; modelin genel hatası Bölüm 3'tedir.


## 7. Sınırlılıklar ve Şeffaflık Taahhüdü

- **Sentetik Veri Bildirimi (`is_demo=True`):** Eğitim ve değerlendirme verileri sentetik jeneratör ile üretilmiştir (Bölüm 0). Üretim ortamında gerçek saha başarısı iddiasında bulunulamaz; model gerçek fabrika/kesimhane kayıtları ile yeniden eğitilmelidir.
- **$R^2$ Metriği Kısıtı:** Dar varyanslı veya homojen küçük veri alt kümelerinde $R^2$ negatif veya istatistiksel olarak yanıltıcı çıkabilmektedir. Bu nedenle model performansında birincil kabul kriteri olarak MAE ve MAPE esas alınmıştır.
- **Asgari Örneklem Eşiği ($N \ge 30$):** Kategori veya ürün bazında en az 30 tamamlanmış gerçek operasyonel kayıt oluşmadan makine öğrenmesi tahminleri aktif edilmez; sistem deterministik hareketli ortalama (baseline) modunda çalışır.
- **Finansal ve Muhasebesel Bağımsızlık:** EKP (Eşdeğer Karkas / Ürün Maliyeti), stok düşümü, kuzu parçalama maliyet dağılımı (ağırlık bazlı oranlama) ve kâr/zarar hesaplamaları **asla** ML model tahminlerine dayandırılmaz. Muhasebe ve envanter işlemleri tamamen deterministik formüller ve kesin işlem kayıtları üzerinden yürütülür. ML sadece anomali uyarısı (`MULTIVARIATE_ANOMALY`) ve operasyonel rehberlik sağlar.
- **Kapsam:** Tek tedarikçi/ürün ailesi (sucuk) ve üç hayvan türü mevcuttur; diğer ürün grupları için model eğitimi yapılmamıştır.
- **Dış Faktörler:** Hayvan ırkı, yaş, mevsimsel beslenme, karkas yağ oranı gibi çevresel değişkenler sentetik veri setinde yer almadığı için modele dâhil edilmemiştir.
- **Güven Aralığı:** Tahmin aralıkları normal hata dağılımı varsayımına dayanır; uç koşullarda kapsama sapması oluşabilir.
- **İzlenebilirlik ve Geri Çağırma Bağımsızlığı:** AI tahminleri hiçbir koşulda gerçek stok, lot ve geri çağırma blokajlarının yerine geçmez. Lot blokajı (`LOT_BLOCKED`, HTTP 409) deterministik güvenlik kuralıdır.

## 8. Resmî AI hattı ve ek araştırma (`ai/Model1`, `ai/Model2`)

**Resmî hat:** Yarışmanın AI-A (üretim verimi / EKP) ve AI-B (parçalama çıktısı) modelleri `backend/app/ml` içindedir. Bu modeller backend'e entegredir (`/api/v1/ai/*`); eğitim, baseline karşılaştırması, imzalı model saklama (HMAC) ve anomali uyarıları bu hatta yapılır. Bu raporun 1–7. bölümleri yalnızca bu hattı anlatır.

**Ek araştırma (ürüne bağlı değil):** `ai/Model1` (sucuk üretim, TL) ve `ai/Model2` (Model B parçalama) bağımsız FastAPI servisleridir. `backend/`, `web/` ve `android/` bu servisleri çağırmaz; ürün akışında kullanılmazlar. Aşağıdaki sayılar 31.10.2026'da temiz bir ortamda eğitim ve test koşularak ölçülmüştür.

| Hat | Hedef | Sonuç (test) | Baseline'a göre |
|---|---|---|---|
| `ai/Model1` verim | Net sucuk çıktısı (kg) | MAE 12,17 · R² 0,971 | %85,4 iyileşme |
| `ai/Model1` EKP | EKP (TL/kg) | MAE 49,87 · R² 0,107 | %3,49 iyileşme; servis "üretime hazır değil" der |
| `ai/Model2` Model B | 8 karkas çıktısı (kg) | Ridge 1,0079 · Random Forest 1,0523 (baseline = 1,0000, normalize MAE oranı) | Hiçbir ML adayı baseline'ı geçemedi; aday `production_ready=false`; `/v1/predict/carcass-cuts` 503 döner, `/v1/predict/carcass-cuts/experimental` adayı `experimental=true` işaretiyle yalnızca pilot için çalıştırır |

Notlar:
- Üç hat da sentetik/simüle veriyle çalışır. Metrikler gerçek işletme başarısı değildir.
- Model1 verim modelinin yüksek skoru, çıktının girdilerden büyük ölçüde hesaplanabilir olmasından gelir (sentetik formül); EKP modeli baseline'ı güçlükle geçer.
- Para birimi farkı: `backend/app/ml` € ile, `ai/Model1` TL ile çalışır. Sayılar birbiriyle karşılaştırılamaz.
- Model1 `models/` klasörü boştur (`.joblib` dosyaları `.gitignore`'dadır); servis, eğitimden sonra aday dosyalar elle `yield_model.joblib` ve `ekp_model.joblib` adına terfi ettirilince çalışır. Taze klonda iki Model1 testi bu yüzden düşer.
- Model B adayı, README'sinde belirtildiği gibi yalnızca saha doğrulamasından sonra üretime alınabilir.
