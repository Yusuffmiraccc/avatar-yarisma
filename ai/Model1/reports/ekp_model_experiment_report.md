# EKP Model Deneyleri — Senaryo A

- Veri dosyası: `D:\Coding\projectDebugging\avatar-yarisma\ai\Model1\data\raw\sucuk_uretim_1000_simule_parti.csv`
- Veri türü: **sentetik**
- Geçerli kayıt: 1000; eğitim: 800; test: 200
- Hedef: `EKP_TL_kg`
- Özellikler: üretim öncesi mevcut olduğu varsayılan 18 alan.
- Dışarıda bırakılanlar: gerçekleşmiş maliyet/çıktı ve kuruma/ayıklama kaybı; olası hedef sızıntısını azaltmak için.
- Bölme: `train_test_split(test_size=0.2, random_state=42)`; tüm adaylarda aynı test kümesi.

## Test sonuçları

| Model | MAE (TL/kg) | RMSE (TL/kg) | R² |
|---|---:|---:|---:|
| RandomForest_LogTarget | 49.6850 | 61.4448 | 0.1006 |
| RandomForest | 50.0357 | 61.5045 | 0.0988 |
| ExtraTrees_LogTarget | 50.7050 | 62.8899 | 0.0578 |
| ExtraTrees | 51.1201 | 63.1629 | 0.0496 |
| DummyMedian | 51.5712 | 67.5646 | -0.0875 |

## En iyi aday: RandomForest_LogTarget
- Medyan referans MAE: 51.5712 TL/kg
- En iyi aday MAE: 49.6850 TL/kg
- Referansa göre MAE değişimi: %3.66 (pozitif = iyileşme).
- Aday dosyası: `D:\Coding\projectDebugging\avatar-yarisma\ai\Model1\models\candidates\ekp_best_candidate.joblib`

## Yorum

Bu deney yalnızca sentetik veri üzerindedir. Daha düşük test MAE'si, gerçek üretimde başarı kanıtı değildir. Aday model üretim modelinin üzerine yazılmamıştır. Üretime geçmeden önce anonimleştirilmiş gerçek parti kayıtlarında zamansal/bağımsız test, kalibrasyon ve veri kalitesi kontrolü gerekir.

Harici yayımlanmış maliyet payları bu deneyin eğitim satırlarına eklenmemiştir; toplulaştırılmış oranlar parti bazlı EKP hedefi değildir.