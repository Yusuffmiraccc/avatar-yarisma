# AVATAR — Yapay Zeka Çalışması Değerlendirme Raporu

_Otomatik üretildi: `python -m scripts.ai_report` · 2026-10-23 · tüm sayılar bu çalıştırmada ölçüldü._

## 0. Önemli not: veri sentetiktir

Gerçek üretici verisi yoktur. Eğitim verisi `app/ml/synthetic.py` ile üretilen **sentetik DEMO** kayıtlardır (`is_demo=true`). Üreteç, üretim verimini girdi bileşimi, mevsim ve tedarikçiye; parça oranlarını hayvan türüne ve ağırlığa **bilerek** bağlar. Bu nedenle aşağıdaki iyileşme yüzdeleri *yöntemin ve değerlendirme hattının çalıştığını* gösterir, gerçek işletmede elde edilecek kazancı **garanti etmez**. Model, gerçek kayıtlarla yeniden eğitildiğinde aynı hat aynı ölçümleri üretir. Bölüm 4'teki deneyler bu iddianın sınırını gösterir.

## 1. Veri

| Küme | Kayıt | Hedef | Not |
|---|---|---|---|
| Üretim emri (A) | 121 | verim oranı (çıktı paket / girdi kg); EKP türetilir | referans emir dahil |
| Parçalama emri (B) | 151 | her parça ve fire için ağırlık oranı | 3 hayvan türü |

## 2. Model A — üretim verimi ve EKP

Yaklaşım: aday modeller **Ridge** ve **GradientBoosting**; özellikler: toplam girdi kg, ana girdi payı, diğer girdi oranı, kg başına maliyet, ay, tedarikçi. **Baseline:** eğitim kümesinin ortalama verimi. Doğrulama: 5-katlı çapraz doğrulama (out-of-fold) + son %20 zaman sıralı holdout. Seçilen: **RIDGE**.

### 2.1 Çapraz doğrulama (out-of-fold)

| Model | Çıktı MAE (paket) | Çıktı RMSE | Çıktı MAPE % | EKP MAE (€) | EKP MAPE % |
|---|---|---|---|---|---|
| BASELINE_MEAN | 3.96 | 5.08 | 3.74 | 0.4728 | 2.60 |
| RIDGE | 2.46 | 3.16 | 2.35 | 0.2978 | 1.64 |
| GRADIENT_BOOSTING | 2.54 | 3.27 | 2.40 | 0.3046 | 1.68 |

Seçilen modelin baseline'a göre MAE iyileşmesi: çıktı **%37.94**, EKP **%37.01**.

### 2.2 Zaman sıralı holdout (son %20, model hiç görmeden)

|  | Çıktı MAE | Çıktı MAPE % | EKP MAE (€) |
|---|---|---|---|
| Model | 2.47 | 2.35 | 0.3165 |
| Baseline | 3.73 | 3.05 | 0.4025 |

Holdout örnek sayısı: 25. %95 aralığın holdout kapsama oranı: **%84.0** (hedef ≈ %95). Aralık hedefin belirgin altında kalıyorsa gösterilen %95 aralığına tam güvenilmemeli; sigma, çapraz doğrulama hatalarının standart sapmasından alınır ve holdout küçüktür.

## 3. Model B — parçalama verimi

Yaklaşım: hayvan türü ve giriş ağırlığından her parça ve fire için ağırlık **oranı** tahmin edilir, kg'a çevrilir. Adaylar **Ridge** ve **RandomForest**. **Baseline:** hayvan türüne göre geçmiş ortalama oranlar. 5-katlı çapraz doğrulama. Seçilen: **RANDOM_FOREST**.

| Model | Genel MAE (kg / parça) | wMAPE % |
|---|---|---|
| BASELINE_ANIMAL_MEAN | 1.446 | 10.58 |
| RIDGE | 1.098 | 8.04 |
| RANDOM_FOREST | 0.997 | 7.29 |

Baseline'a göre MAE iyileşmesi: **%31.06**. %95 aralığın (out-of-fold) kapsama oranı: **%97.7**.

Parça bazında MAE (kg):

| Parça | Model | Baseline |
|---|---|---|
| BUT | 1.488 | 1.894 |
| FIRE | 2.242 | 4.309 |
| KABURGA | 0.543 | 0.696 |
| KIYMA | 0.663 | 0.750 |
| OMUZ | 0.975 | 1.130 |
| SIRT | 0.798 | 0.947 |
| YANURUN | 0.268 | 0.394 |

## 4. Dürüstlük deneyleri

Aşağıdaki sayılar her satırda 3 farklı rastgele alt örnek/gürültü tohumunun ortalamasıdır.

### 4.1 Veri miktarı arttıkça (öğrenme eğrisi) — baseline'a göre MAE iyileşmesi %

| Model | Kayıt sayısı | İyileşme % (çıktı / parça) | İyileşme % (EKP) |
|---|---|---|---|
| A (çıktı / EKP) | 30 | 34.1 | 33.5 |
| A (çıktı / EKP) | 60 | 38.3 | 36.0 |
| A (çıktı / EKP) | 90 | 37.9 | 37.2 |
| A (çıktı / EKP) | 120 | 38.5 | 37.7 |
| B (parça kg) | 30 | 15.5 | - |
| B (parça kg) | 60 | 22.6 | - |
| B (parça kg) | 90 | 27.8 | - |
| B (parça kg) | 150 | 30.6 | - |

30 kayıt altında sistem modeli eğitmez, baseline kullanır ve bunu `limitations` alanında bildirir.

### 4.2 Gürültü arttıkça — baseline'a göre MAE iyileşmesi %

| Model | Eklenen gürültü σ | İyileşme % (çıktı / parça) | İyileşme % (EKP) |
|---|---|---|---|
| A (verim oranına ek σ) | 0.0 | 37.9 | 37.0 |
| A (verim oranına ek σ) | 0.02 | 23.4 | 23.6 |
| A (verim oranına ek σ) | 0.05 | 5.3 | 6.2 |
| A (verim oranına ek σ) | 0.1 | -2.4 | -1.8 |
| B (oranlara ek σ) | 0.0 | 31.1 | - |
| B (oranlara ek σ) | 0.01 | 20.9 | - |
| B (oranlara ek σ) | 0.03 | 7.9 | - |
| B (oranlara ek σ) | 0.06 | 2.7 | - |

Gürültü arttıkça kazanç küçülür; kazanç, verideki gerçek sinyalin gücüne bağlıdır. Gerçek veride sinyal zayıfsa model baseline'ı geçemeyebilir; bu durumda yeniden eğitim aktif modeli korur (`app/ml/service.py::_promote`).

## 5. Anomali tespiti — IsolationForest ve kural tabanlı z-skoru

Etiketli gerçek anomali yoktur. Değerlendirme: mevcut kayıtların %5'ine bilinen anomaliler **enjekte edilir** (20 farklı tohum, ortalama). Üretimde üç tür: düşük verim (×0,78), maliyet sıçraması (×1,35) ve verim–maliyet ilişkisinin bozulması (verim +2σ ve EKP +2σ; normalde verim artınca EKP düşer, her değer tek başına 2,5σ eşiğinin altında kalır). Parçalamada: iki parçanın oranı kaymış bileşim; tek değişkenli kural her parça oranına ayrı ayrı iki yönlü bakar. Üretimde kural, serviste kullanılan tek değişkenli z-skorudur (|z| > 2.5); IsolationForest ise tüm özelliklere birlikte bakar (contamination=0.03).

### 5.1 Üretim (verim + EKP)

| Yöntem | Precision | Recall | F1 |
|---|---|---|---|
| Kural: z-skoru (>2,5σ) | 0.97 | 0.67 | 0.79 |
| IsolationForest | 1.00 | 0.67 | 0.80 |

Anomali türüne göre recall:

| Tür | z-skoru | IsolationForest |
|---|---|---|
| düşük verim | 1.00 | 0.95 |
| maliyet sıçraması | 1.00 | 1.00 |
| verim–maliyet ilişkisi bozuk | 0.00 | 0.05 |

### 5.2 Parçalama (bileşim kayması)

| Yöntem | Precision | Recall | F1 |
|---|---|---|---|
| Kural: z-skoru (>2,5σ) | 0.25 | 0.34 | 0.29 |
| IsolationForest | 0.23 | 0.16 | 0.19 |

**Sonuç: bu veride IsolationForest'ın z-skoruna belirgin bir üstünlüğü ölçülmedi.** Üretimde F1 benzer; verim–maliyet ilişkisi bozuk kayıtlarda ikisi de neredeyse hiç yakalamadı (contamination=0.03 yalnızca kayıtların ~%3'ünü işaretler, enjekte oran %5 olduğundan ve daha uç anomaliler önce sıralandığından recall sınırlı kalır); parçalamada daha kötüdür. Servis yalnızca z-skorunun işaretlemediği kayıtlara **ek**, düşük önemli (`MULTIVARIATE_ANOMALY`, INFO) uyarı üretir; tek başına karar verici değildir. Uyarılar insan incelemesi içindir; stok veya maliyet kaydını değiştirmez.

## 6. Örnek tahminler (referans senaryo)

Tahminler emir tamamlanmadan **önce** üretilmiş, modele o emir eğitimde gösterilmemiştir.

| Emir | Tahmin | Baseline | Gerçek | Sapma |
|---|---|---|---|---|
| URT-2026-045 (paket) | 85.0 | 85.0 | 85.0 | 0.0 |
| URT-2026-045 (EKP €) | 18.1627 | 18.1576 | 18.1588 | -0.0039 |
| PRC-2026-001 BUT (kg) | 6.51 | 6.56 | 12.00 | 5.49 |
| PRC-2026-001 FIRE (kg) | 4.62 | 4.49 | 0.00 | -4.62 |
| PRC-2026-001 OMUZ (kg) | 4.90 | 4.97 | 4.00 | -0.90 |
| PRC-2026-001 SIRT (kg) | 3.03 | 3.01 | 6.00 | 2.97 |
| PRC-2026-001 KIYMA (kg) | 1.98 | 2.00 | 0.00 | -1.98 |
| PRC-2026-001 KABURGA (kg) | 2.41 | 2.47 | 0.00 | -2.41 |
| PRC-2026-001 YANURUN (kg) | 1.55 | 1.51 | 0.00 | -1.55 |

Not: PDF'teki kuzu örneğinde (PRC-2026-001) yalnızca üç parça kayıtlıdır (12 + 6 + 4 = 22 kg), fire kaydı yoktur; sentetik veride ise kesim yedi kalemlidir. Parçalama satırlarındaki büyük sapmalar model hatasını değil, bu ürün karması farkını yansıtır; modelin genel hatası Bölüm 3'tedir.


## 7. Sınırlılıklar

- Veri sentetiktir (Bölüm 0); gerçek performans gerçek kayıtlarla yeniden ölçülmelidir.
- Tek tedarikçi/ürün ailesi (sucuk) ve üç hayvan türü; dışındaki ürünler için model yoktur.
- Kalite, ırk, yaş, beslenme gibi dış etkenler modelde yoktur.
- Aralıklar normal hata varsayımına dayanır; küçük örneklemde kapsama oranı hedeften sapabilir.
- Anomali değerlendirmesi enjekte edilmiş anomalilerle yapıldı; gerçek anomali dağılımı farklı olabilir.
- AI tahmini gerçek stok/lot bilgisinin yerine geçmez; izlenebilirlik ve geri çağırma kesin kayıtlara dayanır.
