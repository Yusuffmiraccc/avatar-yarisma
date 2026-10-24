# EKP iyileştirme ve doğrulama karşılaştırması

## Karar

Verinin tamamı sentetik/simüledir; gerçek fabrika doğrulaması yoktur. Tahmin hatasını ölçtüm, hedef EKP değerlerini yapay olarak değiştirmedim. Üretim artefaktı korunmuş, yeni model üretime alınmamıştır.

## Formül ve veri

EKP = toplam parti maliyeti (TL) / net çıktı (kg), sonuç TL/kg'dır.
- 1.000 sentetik satır; EKP oran formülü maksimum farkı 0.015946 TL/kg.
- Fason hizmet formülü, 338 Fason satırında maksimum 0.005000 TL farkla doğrulandı.
- Tam tekrarlar: 0; tam aynı özellik imzalı satırlar: 0.
- Üretim öncesi senaryo A sadece girdi miktarları, kategori ve fiyat/tarife alanlarını kullanır. Fiyat/tarifelerin üretim öncesi zaman damgası sentetik kaynakta kanıtlanmadığından gerçek sistemde ayrıca doğrulanmalıdır.
- Senaryo B kayıp yüzdelerini içerir. Bunlar sentetik olup gerçek ölçüm/erişilebilirlik zamanı belli değildir; B üretim adayı değildir.

## 5 katlı çapraz doğrulama

Aynı karıştırılmış fold'lar kullanıldı; ön işleme her fold'un eğitim kısmında öğrenildi. MAE/RMSE TL/kg. Baseline farkı, fold bazlı medyan DummyRegressor'a göre hesaplandı.

| Model | CV MAE ort ± std | CV RMSE ort ± std | CV R² ort ± std | Medyan baseline'a göre MAE |
|---|---:|---:|---:|---:|
| engineered_gradient_boosting_huber | 48.9869 ± 2.8174 | 60.5653 ± 3.7470 | 0.1436 ± 0.0313 | %6.09 |
| gradient_boosting_huber | 49.0452 ± 3.4475 | 61.0058 ± 4.0758 | 0.1315 ± 0.0315 | %5.98 |
| huber_regressor | 49.2326 ± 3.5431 | 62.0082 ± 4.0871 | 0.1027 ± 0.0335 | %5.62 |
| random_forest_log_target | 49.4260 ± 3.3102 | 61.1683 ± 4.6223 | 0.1270 ± 0.0507 | %5.25 |
| random_forest_incumbent | 49.9314 ± 3.1800 | 61.2698 ± 4.4614 | 0.1240 ± 0.0469 | %4.28 |
| ridge | 50.0187 ± 3.2836 | 61.1063 ± 4.0177 | 0.1286 ± 0.0317 | %4.11 |
| hist_gradient_boosting | 50.4063 ± 2.6268 | 62.1092 ± 3.8281 | 0.0993 ± 0.0325 | %3.37 |
| extra_trees | 50.7125 ± 2.8797 | 62.7718 ± 3.4536 | 0.0799 ± 0.0149 | %2.78 |
| hybrid_known_cost_plus_residual_over_predicted_yield | 52.0567 ± 1.5599 | 64.9494 ± 1.7954 | 0.0116 ± 0.0626 | %0.21 |
| dummy_median | 52.1642 ± 3.6097 | 67.1315 ± 3.0199 | -0.0535 ± 0.0319 | %0.00 |
| predicted_cost_over_predicted_yield_rf | 53.2796 ± 3.1695 | 66.6023 ± 3.6657 | -0.0365 ± 0.0432 | %-2.14 |
| dummy_mean | 53.3292 ± 3.7109 | 65.4918 ± 3.2851 | -0.0019 ± 0.0011 | %-2.23 |

CV MAE lideri engineered_gradient_boosting_huber olarak belirlendi; bu sentetik aday sıralamasıdır, üretim seçimi değildir.

## Mimari ve daha önce kullanılan holdout

Bileşen yaklaşımı maliyet ve net çıktıyı ayrı tahmin edip böler. Hibrit yaklaşım doğrulanmış formül alt toplamlarını kullanıp kalan maliyeti ve net çıktıyı ayrı tahmin eder. Gerçekleşmiş maliyet veya net çıktı hiçbir tahmin girdisi değildir.
Sabit 800/200 holdout önceki deneylerde kullanıldığı için sonuçları keşifseldir ve bağımsız son test değildir.

| Model | Holdout MAE | Holdout RMSE | Holdout R² | Eğitim medyanına göre MAE farkı |
|---|---:|---:|---:|---:|
| huber_regressor | 47.7993 | 61.3317 | 0.1039 | %7.31 |
| gradient_boosting_huber | 47.9012 | 60.8500 | 0.1179 | %7.12 |
| ridge | 48.1409 | 60.2837 | 0.1342 | %6.65 |
| engineered_gradient_boosting_huber | 48.8140 | 61.1269 | 0.1098 | %5.35 |
| random_forest_log_target | 49.4607 | 61.1961 | 0.1078 | %4.09 |
| random_forest_incumbent | 49.8723 | 61.2236 | 0.1070 | %3.29 |
| hist_gradient_boosting | 50.5515 | 62.3621 | 0.0735 | %1.98 |
| extra_trees | 51.0926 | 63.1198 | 0.0509 | %0.93 |
| dummy_median | 51.5712 | 67.5646 | -0.0875 | %0.00 |
| dummy_mean | 51.6755 | 64.8796 | -0.0028 | %-0.20 |
| hybrid_known_cost_plus_residual_over_predicted_yield | 52.4509 | 65.8145 | -0.0319 | %-1.71 |
| predicted_cost_over_predicted_yield_rf | 53.5409 | 67.0657 | -0.0715 | %-3.82 |

Mevcut API üretim artefaktı: MAE 49.8723, RMSE 61.2236, R² 0.1070; SHA-256 aae0a3538e0c57dff7fc12bc8d20961f4802644b2f4a4cde40eb49d375e9b802.
Önceki log-target aday (aynı holdout ile seçildi): MAE 49.6850, RMSE 61.4448, R² 0.1006; yalnızca keşifseldir.

## Sonraki koşullar

EKP modeli gerçek üretim için hazır değildir. Gerçek plan girdilerinin zaman damgaları, ayrı planlanan/gerçekleşmiş kayıp oranları, net tartım ve maliyet mutabakatı toplanmalı; en yeni gerçek partiler dokunulmamış zaman bazlı testte değerlendirilmelidir.

Araştırma adayı ayrı dosyada: models/candidates/ekp_gradient_boosting_huber_engineered_20261024.joblib. Yalnızca eğitim bölmesinde fit edilmiştir; üretime hazır değildir.
Makinece okunabilir ayrıntılar: reports/ekp_improvement_comparison.json ve reports/ekp_improvement_comparison.csv.
