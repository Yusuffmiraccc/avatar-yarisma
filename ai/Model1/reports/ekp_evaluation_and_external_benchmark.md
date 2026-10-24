# EKP Modeli — Değerlendirme ve Harici Benchmark Raporu

**Rapor tarihi:** 2026-10-24

## 1. Mevcut sentetik test sonuçları

Aşağıdaki değerler daha önce çalıştırılan `training/validate_models.py` raporundan alınmıştır. Bunlar sentetik test kümesi sonuçlarıdır; gerçek üretim performansı olarak sunulmamalıdır.

| EKP yaklaşımı | MAE (TL/kg) | RMSE (TL/kg) | R² | Medyan referansa göre MAE iyileşmesi |
|---|---:|---:|---:|---:|
| Medyan referans, Scenario A | 51.68 | — | — | — |
| Random Forest, Scenario A | 49.87 | 61.22 | 0.1070 | %3.49 |
| Extra Trees, Scenario A | 51.09 | 63.12 | 0.0509 | %1.13 kötüleşme |
| Random Forest, Scenario B* | 12.85 | 16.94 | 0.9316 | %75.14 |
| Extra Trees, Scenario B* | 10.47 | 14.24 | 0.9517 | %79.74 |

*Scenario B, kuruma kaybı ve ayıklama firesi alanlarını içerir. Bu alanlar gerçekleşmiş/üretim sonrası ölçümlerse üretim öncesi tahminde kullanımları veri sızıntısıdır. Bu yüzden Scenario B skorları üretime hazır model kanıtı değildir.*

## 2. Harici, tarihsel maliyet yapısı benchmark'ı

Kaynak dosya: `data/external/ekp_published_cost_structure_benchmark.csv`

| Maliyet bileşeni | Yayındaki pay |
|---|---:|
| Hammadde | %75.11 |
| Yardimci malzemeler | %9.47 |
| Iscilik | %5.08 |
| Enerji | %2.75 |
| Diger giderler | %7.59 |
| **Toplam** | **%100.00** |

Bu tablo toplulaştırılmış tarihsel maliyet paylarını içerir; parti bazında toplam maliyet ve net üretim miktarı yoktur. Bu nedenle buradan EKP MAE/RMSE/R² hesaplanamaz ve bu satırlar eğitim kayıtlarına eklenmemelidir.

## 3. Karar

- Mevcut üretim modelleri korunur; bu rapor onları değiştirmez.
- Scenario A, sentetik veride basit medyan referansına karşı yalnızca sınırlı iyileşme göstermiştir.
- Scenario B sonuçları, kayıp değişkenlerinin tahmin anında bilindiği kanıtlanmadan kabul edilmemelidir.
- Harici benchmark yalnızca maliyet bileşenlerinin makullük kontrolüdür; bağımsız tahmin doğrulaması değildir.

## 4. Gerçek veride test için gereken alanlar

Her anonimleştirilmiş üretim partisi için asgari alanlar:

- Parti/lot kimliği ve üretim tarihi
- Tahmin anında bilinen hammadde miktarları, birim fiyatlar ve reçete/proses bilgileri
- Gerçekleşen toplam parti maliyeti (TL)
- Ölçülmüş net sucuk çıktısı (kg)
- Kayıtlı gerçek EKP = toplam maliyet / net çıktı (TL/kg)

Testte gerçek EKP hedefi, aynı ayrılmış test partileri üzerinde medyan referans ve model tahminleriyle karşılaştırılmalı; MAE, RMSE ve R² raporlanmalıdır. Aynı partinin türev kayıtları eğitim ve test kümelerine dağıtılmamalıdır.

## 5. Lot izlenebilirliği ve geri çağırma

Lot ilişkileri yapay zekâ tahmininden bağımsız kesin kayıtlarla kurulmalıdır: hammadde lotu → üretim partisi → nihai ürün lotu → sevkiyat/müşteri. Geri çağırma kapsamı bu ilişkilerden sorgulanmalı; model skoru hiçbir zaman lot bağlantısının yerine geçmemelidir.

**Sonuç:** EKP modeli için sentetik test ve harici maliyet yapısı kontrolü mevcut; gerçek parti bazlı dış doğrulama henüz yoktur.
