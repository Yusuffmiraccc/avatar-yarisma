# EKP — Harici Maliyet Yapısı Kıyaslaması

**Tarih:** 2026-10-24

## Kaynak
Polat, M. & Cevger, Y. (2026), *Analysis of Factors Affecting the Production Costs of Red Meat Products in Türkiye*.
Kaynak: https://agrifoodscience.com/index.php/TURJAF/article/view/9152

Çalışma, 2014–2015 üretim dönemlerinde 15 işletmeden toplanan verileri inceler.

| Maliyet bileşeni | Toplam maliyetteki pay |
|---|---:|
| Hammadde | %75,11 |
| Yardımcı malzemeler | %9,47 |
| İşçilik | %5,08 |
| Enerji | %2,75 |
| Diğer giderler | %7,59 |
| **Toplam** | **%100.00** |

## Yorum ve sınırlılıklar
- Bu, tarihsel ve toplulaştırılmış maliyet benchmark'ıdır; parti bazlı eğitim verisi değildir.
- Maliyet varsayımlarına yönelik makullük kontrolü olarak kullanılabilir.
- Gerçek parti maliyeti ve ölçülmüş net çıktı içermediği için MAE, RMSE veya R² hesaplanamaz.
- Güncel TL/kg maliyetini veya bugünkü işletmeleri doğrudan temsil etmez.
- Bu satırları sentetik partilere ekleyerek gerçek parti sayısını artırmış gibi göstermeyin.

## Gerçek EKP doğrulaması
Gerçek EKP = gerçek toplam parti maliyeti / ölçülmüş net çıktı (kg). Anonimleştirilmiş gerçek partilerde girdi miktarları/fiyatları, toplam maliyet ve net çıktı bulunmalıdır. Medyan referans ve model aynı ayrılmış test kümesinde MAE, RMSE ve R² ile karşılaştırılmalıdır. Üretim sonu ölçülen fire/kuruma değerleri, üretim öncesi tahminde yalnızca önceden bilinen plan değerleri ise kullanılmalıdır.

**Durum:** Harici maliyet benchmark'ı hazırlandı; gerçek parti bazlı model doğrulaması değildir. `models/ekp_model.joblib` ve `models/yield_model.joblib` değiştirilmez.


## Swedish Meats hot-dog process-inventory benchmark — file status and source review

The task requested two pre-created files named swedish_meats_hotdog_process_inventory_external_benchmark.csv and swedish_meats_hotdog_process_inventory_summary.csv. They were not found in the repository, Downloads, Desktop, Documents, or the searched D:\Coding tree. A profile-wide filename search also returned no matching file before encountering access-denied locations under Code askpass and Windows Temp. The files were not recreated, downloaded as substitutes, or mixed into the EKP training data. The existing ekp_published_cost_structure_benchmark.csv is a different, aggregate cost-share source and is not either requested inventory file.

The source page itself was reviewed: https://cpmdatabase.cpm.chalmers.se/Scripts/sheet.asp?ActId=KI-2010-09-24-249. It describes “Sausage (Hot-Dog) production. ESA-DBP,” a gate-to-gate process at Swedish Meats in Örebro, Sweden, with a functional unit of 100 kg of Hot Dog. The source says facility data were mostly actual figures from 2004, the dataset was completed in 2005, and the associated thesis was published in 2010. The manufacturer did not provide its recipes; the Hot Dog recipe used for the study was an estimate. The record marks its flow data as “Derived, unspecified.”

The web record lists these flows for the activity:

| Flow | Quantity | Unit |
|---|---:|---|
| Beef | 3.9 | kg |
| Pork | 49.5 | kg |
| Biogas | 270 | MJ |
| District heating | 43 | MJ |
| Electricity | 198 | MJ |
| Heat oil | 12.8 | MJ |
| Nitrite salt | 1.8 | kg |
| Potato starch | 10 | kg |
| Water | 30.5 | kg |
| Water (second listed flow row) | 3.8 | kg |
| Hot Dog output | 100 | kg |

The page states that personnel aspects are not included, reports no allocation information, and notes that some preservatives were omitted. The two water rows are retained as separate source flows here because their distinct meanings are not explained on the page.

This is an old Swedish life-cycle inventory, not a Turkish batch-cost record: it has no batch total cost, price ledger, or EKP target. At most, a recovered original inventory may support process-input benchmarking after its flow names, system boundary, units, and recipe assumptions are checked. It must not be used as an EKP training label or presented as current factory evidence. The existing aggregate cost-share CSV is a different source and remains separate.
