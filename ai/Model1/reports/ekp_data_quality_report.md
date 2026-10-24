# EKP synthetic dataset data-quality and leakage report

**All 1,000 records are synthetic/simulated. No factory performance or real production data quality is established by this report.**

- Dataset: data/raw/sucuk_uretim_1000_simule_parti.csv, 1000 rows × 42 columns.
- SHA-256: 5c4fbd9c4897d6b5f1d6a8fcdb113e551122a7862f6a65ce844358e3afe1850e.
- Missing cells: 0; duplicate rows: 0; duplicate batch IDs: 0.
- Non-finite numeric cells: 0; negative numeric cells: 0.
- Every row carries the synthetic/simulated source label: True.
- Simulation date field: 2026-09-01 to 2026-10-22 (52 distinct dates). The dates are generated metadata, not verified production chronology.

## Column types and distinct values

| Field | CSV dtype | Distinct values | Missing |
|---|---|---:|---:
| Parti_ID | object | 1000 | 0 |
| Tarih_simulasyon | object | 52 | 0 |
| Bolge | object | 7 | 0 |
| Recete_profili | object | 2 | 0 |
| Isleme_modeli | object | 2 | 0 |
| Veri_sinifi | object | 1 | 0 |
| Et_girdi_kg | float64 | 999 | 0 |
| Kuyruk_yagi_girdi_kg | float64 | 996 | 0 |
| Baharat_girdi_kg | float64 | 975 | 0 |
| Tuz_girdi_kg | float64 | 953 | 0 |
| Diger_kucuk_girdi_kg | float64 | 838 | 0 |
| Karisim_girdi_toplam_kg | float64 | 999 | 0 |
| Kilif_metre | float64 | 1000 | 0 |
| Et_fiyat_TL_kg | float64 | 903 | 0 |
| Kuyruk_yagi_fiyat_TL_kg | float64 | 934 | 0 |
| Baharat_fiyat_TL_kg | float64 | 3 | 0 |
| Tuz_fiyat_TL_kg | float64 | 1 | 0 |
| Kilif_fiyat_TL_m | float64 | 1 | 0 |
| Fason_birim_bedel_TL_kg_girdi | float64 | 921 | 0 |
| Kuruma_kaybi_pct | float64 | 723 | 0 |
| Ayiklama_fire_pct | float64 | 151 | 0 |
| Net_sucuk_ciktisi_kg_simule | float64 | 999 | 0 |
| Et_maliyeti_TL | float64 | 1000 | 0 |
| Yag_maliyeti_TL | float64 | 1000 | 0 |
| Baharat_maliyeti_TL | float64 | 989 | 0 |
| Tuz_diger_girdi_maliyeti_TL | float64 | 998 | 0 |
| Kilif_maliyeti_TL | float64 | 1000 | 0 |
| Direkt_malzeme_toplam_TL | float64 | 1000 | 0 |
| Iscilik_saati | float64 | 851 | 0 |
| Iscilik_maliyeti_TL_saat | float64 | 1 | 0 |
| Elektrik_kWh | float64 | 982 | 0 |
| Elektrik_fiyati_TL_kWh | float64 | 1 | 0 |
| Ambalaj_TL_kg_net_urun | float64 | 82 | 0 |
| Fason_hizmet_TL | float64 | 339 | 0 |
| Kurum_ici_isleme_TL | float64 | 662 | 0 |
| Paketleme_maliyeti_TL | float64 | 993 | 0 |
| Genel_gider_TL | float64 | 1000 | 0 |
| Toplam_parti_maliyeti_TL | float64 | 1000 | 0 |
| EKP_TL_kg | float64 | 975 | 0 |
| Et_maliyet_payi_pct | float64 | 462 | 0 |
| Referans_kodlari | object | 1 | 0 |
| Notlar | object | 1 | 0 |

## Units and formula reconciliation

Observed column naming and the workbook dictionary use ingredient/output kg, casing m, unit prices and costs in TL, labor hours and TL/hour, energy kWh and TL/kWh, loss percentages, and EKP in TL/net kg. These conventions are not independently confirmed against a factory ledger or calibrated scale.

| Check | Maximum absolute difference | Meaning |
|---|---:|---|
| Ingredient sum vs reported mix | 0.0000000000 kg | Reconciles at CSV precision |
| Calculated mass balance vs net output | 0.00049995 kg | Synthetic yield formula only |
| Component sum vs direct material | 0.0200 TL | Small CSV rounding difference |
| Total cost reconciliation | 0.0200 TL | Direct materials + processing + packaging + overhead |
| Total cost / net kg vs EKP | 0.015946 TL/kg | Ratio target rounding difference |
| Fason rate vs service cost | 0.0050 TL | Simulated Fason rows only |

The total-cost reconciliation treats Fason service and in-house processing as mutually exclusive. The workbook dictionary describes in-house processing as simulated labor + energy + a 12% facility-overhead assumption; labor and energy should therefore not be added again on top of that combined field. Fason pricing and in-house allocation are not verified against real invoices or an accounting policy.

## Target distribution

- EKP count 1000; mean 925.2728; standard deviation 65.5680; median 910.6100 TL/kg.
- Range 804.4500 to 1,147.9600 TL/kg; P1 819.4656; P99 1,106.1901.
- IQR rule flags 11 EKP rows. No outlier was deleted or clipped; a flag is not evidence of an error.

| Numeric field | n | Mean | Std | Median | Min | Q1 | Q3 | P95 | P99 | Max | IQR flags |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Et_girdi_kg | 1000 | 208.8197 | 95.3720 | 203.4285 | 42.2020 | 126.1870 | 291.2322 | 364.0484 | 389.3035 | 396.4300 | 0 |
| Kuyruk_yagi_girdi_kg | 1000 | 52.3619 | 26.2450 | 48.6835 | 8.3840 | 31.8465 | 68.7030 | 101.3649 | 107.5846 | 113.1320 | 0 |
| Baharat_girdi_kg | 1000 | 12.8998 | 5.8541 | 12.5595 | 2.5600 | 7.8673 | 18.2803 | 21.9310 | 23.3448 | 24.2780 | 0 |
| Tuz_girdi_kg | 1000 | 5.9409 | 3.0073 | 5.5745 | 0.9320 | 3.5890 | 7.9533 | 11.5086 | 12.4102 | 13.3070 | 0 |
| Diger_kucuk_girdi_kg | 1000 | 1.7477 | 1.6094 | 1.2855 | 0.0060 | 0.2762 | 3.0577 | 4.6473 | 5.2685 | 5.7590 | 0 |
| Karisim_girdi_toplam_kg | 1000 | 281.7700 | 126.7484 | 280.2000 | 60.2370 | 173.7555 | 394.7625 | 476.4473 | 494.8011 | 499.9450 | 0 |
| Kilif_metre | 1000 | 352.6498 | 160.9100 | 342.1550 | 71.0050 | 215.0523 | 493.5953 | 608.4524 | 639.9461 | 664.8610 | 0 |
| Et_fiyat_TL_kg | 1000 | 595.1899 | 12.5890 | 595.5450 | 566.5100 | 586.1700 | 603.8275 | 617.0895 | 621.6803 | 624.5800 | 0 |
| Kuyruk_yagi_fiyat_TL_kg | 1000 | 447.5449 | 21.5970 | 447.6300 | 409.2900 | 430.1725 | 466.7400 | 480.2715 | 482.3908 | 483.4900 | 0 |
| Baharat_fiyat_TL_kg | 1000 | 534.6384 | 110.9353 | 550.0000 | 400.0000 | 400.0000 | 669.9000 | 669.9000 | 669.9000 | 669.9000 | 0 |
| Tuz_fiyat_TL_kg | 1000 | 19.8800 | 0.0000 | 19.8800 | 19.8800 | 19.8800 | 19.8800 | 19.8800 | 19.8800 | 19.8800 | 0 |
| Kilif_fiyat_TL_m | 1000 | 43.7475 | 0.0000 | 43.7475 | 43.7475 | 43.7475 | 43.7475 | 43.7475 | 43.7475 | 43.7475 | 0 |
| Fason_birim_bedel_TL_kg_girdi | 1000 | 95.0997 | 17.4759 | 94.8500 | 65.0200 | 79.8250 | 110.5150 | 121.6940 | 124.3127 | 124.9800 | 0 |
| Kuruma_kaybi_pct | 1000 | 22.0211 | 4.7397 | 20.7150 | 15.5700 | 18.0875 | 25.5300 | 31.3070 | 33.3800 | 33.9500 | 0 |
| Ayiklama_fire_pct | 1000 | 1.0596 | 0.4254 | 1.0550 | 0.3000 | 0.6900 | 1.4300 | 1.7205 | 1.7800 | 1.8000 | 0 |
| Net_sucuk_ciktisi_kg_simule | 1000 | 217.6058 | 99.0817 | 214.6285 | 40.3970 | 133.8663 | 302.2285 | 372.9058 | 399.0345 | 411.2720 | 0 |
| Et_maliyeti_TL | 1000 | 124,341.7145 | 56,968.9553 | 121,383.6850 | 25,848.5600 | 74,939.6250 | 172,819.5825 | 216,675.1020 | 233,512.2728 | 241,345.5900 | 0 |
| Yag_maliyeti_TL | 1000 | 23,412.0291 | 11,763.1789 | 21,690.3300 | 4,029.4300 | 14,184.9175 | 31,047.4050 | 45,003.3830 | 49,575.8591 | 53,295.4800 | 0 |
| Baharat_maliyeti_TL | 1000 | 6,880.9482 | 3,460.1798 | 6,519.6000 | 1,079.2000 | 3,913.3625 | 9,241.7125 | 12,936.0045 | 15,135.4585 | 15,748.0100 | 0 |
| Tuz_diger_girdi_maliyeti_TL | 1000 | 1,049.5650 | 940.5421 | 718.7550 | 21.3300 | 242.8800 | 1,739.7025 | 2,889.6840 | 3,418.7165 | 4,031.2800 | 1 |
| Kilif_maliyeti_TL | 1000 | 15,427.5458 | 7,039.4120 | 14,968.4250 | 3,106.2900 | 9,407.9950 | 21,593.5550 | 26,618.2760 | 27,996.0399 | 29,086.0100 | 0 |
| Direkt_malzeme_toplam_TL | 1000 | 171,111.8026 | 77,288.6322 | 168,390.4400 | 36,444.5700 | 105,157.6800 | 238,900.4125 | 290,318.6000 | 306,736.7975 | 312,444.8800 | 0 |
| Iscilik_saati | 1000 | 14.8091 | 7.4324 | 14.1900 | 2.3800 | 8.5900 | 20.0950 | 28.8180 | 32.3816 | 34.3900 | 0 |
| Iscilik_maliyeti_TL_saat | 1000 | 174.3300 | 0.0000 | 174.3300 | 174.3300 | 174.3300 | 174.3300 | 174.3300 | 174.3300 | 174.3300 | 0 |
| Elektrik_kWh | 1000 | 98.4281 | 49.5963 | 93.7550 | 13.3000 | 56.2550 | 133.7900 | 188.5970 | 216.7687 | 233.1400 | 0 |
| Elektrik_fiyati_TL_kWh | 1000 | 4.8148 | 0.0000 | 4.8148 | 4.8148 | 4.8148 | 4.8148 | 4.8148 | 4.8148 | 4.8148 | 0 |
| Ambalaj_TL_kg_net_urun | 1000 | 5.5070 | 0.2370 | 5.5000 | 5.1000 | 5.3075 | 5.7200 | 5.8700 | 5.9000 | 5.9100 | 0 |
| Fason_hizmet_TL | 1000 | 9,499.4498 | 15,655.1812 | 0.0000 | 0.0000 | 0.0000 | 16,767.2900 | 45,123.5320 | 55,033.7761 | 61,699.2100 | 68 |
| Kurum_ici_isleme_TL | 1000 | 15,363.1873 | 13,934.0695 | 13,680.5000 | 0.0000 | 0.0000 | 27,706.2675 | 38,799.6240 | 41,541.5742 | 43,578.8200 | 0 |
| Paketleme_maliyeti_TL | 1000 | 1,198.5263 | 550.2219 | 1,167.7200 | 224.6000 | 740.8400 | 1,666.9900 | 2,090.0165 | 2,222.8424 | 2,410.0500 | 0 |
| Genel_gider_TL | 1000 | 3,422.2362 | 1,545.7726 | 3,367.8100 | 728.8900 | 2,103.1575 | 4,778.0075 | 5,806.3745 | 6,134.7379 | 6,248.9000 | 0 |
| Toplam_parti_maliyeti_TL | 1000 | 200,595.2021 | 90,922.6642 | 196,291.2300 | 42,548.7300 | 123,871.1425 | 281,645.6275 | 342,289.2440 | 357,633.6415 | 379,531.7700 | 0 |
| EKP_TL_kg | 1000 | 925.2728 | 65.5680 | 910.6100 | 804.4500 | 875.8425 | 967.4075 | 1,053.6920 | 1,106.1901 | 1,147.9600 | 11 |
| Et_maliyet_payi_pct | 1000 | 73.7140 | 1.5175 | 73.8700 | 68.8800 | 72.8400 | 74.7400 | 75.8705 | 76.6608 | 77.4800 | 23 |

### EKP by Isleme_modeli

| Group | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| Fason | 338 | 937.2557 | 68.9690 | 924.8150 | 806.7100 | 1,147.9600 |
| Kurum içi | 662 | 919.1547 | 62.9402 | 906.6850 | 804.4500 | 1,122.7900 |

### EKP by Bolge

| Group | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| Akdeniz | 136 | 923.7471 | 65.5475 | 909.4400 | 815.0700 | 1,131.2400 |
| Doğu Anadolu | 136 | 919.5887 | 67.9190 | 901.3250 | 810.7500 | 1,147.9600 |
| Ege | 145 | 931.1523 | 63.8985 | 916.4700 | 810.5500 | 1,117.8200 |
| Güneydoğu Anadolu | 137 | 901.7872 | 57.5108 | 887.4800 | 804.4500 | 1,076.3400 |
| Karadeniz | 158 | 942.7321 | 70.6719 | 929.4250 | 820.4500 | 1,122.6000 |
| Marmara | 127 | 938.1070 | 59.7348 | 935.6100 | 840.6900 | 1,106.1700 |
| İç Anadolu | 161 | 918.7948 | 64.1991 | 908.1600 | 806.7100 | 1,098.2400 |

### EKP by Recete_profili

| Group | n | Mean | Std | Median | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| ERZURUM_CI | 421 | 939.3149 | 65.0967 | 923.8700 | 833.5700 | 1,147.9600 |
| MEB_STANDART | 579 | 915.0626 | 64.0569 | 900.8200 | 804.4500 | 1,122.6000 |

## Correlations and leakage

Correlations are descriptive only. EKP is mathematically defined as total batch cost divided by net output, so the target is structurally connected to cost and yield. Generated correlations do not establish causal or factory relationships.

Allow-listed numeric feature pairs with absolute Pearson correlation at least 0.90:

| Feature 1 | Feature 2 | r |
|---|---|---:|
| Kuyruk_yagi_girdi_kg | Tuz_girdi_kg | 0.99098 |
| Et_girdi_kg | Baharat_girdi_kg | 0.99052 |
| Baharat_girdi_kg | Kilif_metre | 0.98942 |
| Et_girdi_kg | Kilif_metre | 0.98253 |

Largest allow-listed numeric feature correlations with EKP:

| Feature | Pearson r |
|---|---:|
| Et_fiyat_TL_kg | 0.25073 |
| Fason_birim_bedel_TL_kg_girdi | 0.14950 |
| Diger_kucuk_girdi_kg | -0.14067 |
| Kuyruk_yagi_fiyat_TL_kg | 0.13734 |
| Baharat_fiyat_TL_kg | 0.11128 |
| Kuyruk_yagi_girdi_kg | -0.07112 |
| Tuz_girdi_kg | -0.06554 |
| Et_girdi_kg | 0.03256 |
| Baharat_girdi_kg | 0.01319 |
| Kilif_metre | 0.01080 |

Feature allow-list for Scenario A: Et_girdi_kg, Kuyruk_yagi_girdi_kg, Baharat_girdi_kg, Tuz_girdi_kg, Diger_kucuk_girdi_kg, Kilif_metre, Et_fiyat_TL_kg, Kuyruk_yagi_fiyat_TL_kg, Baharat_fiyat_TL_kg, Tuz_fiyat_TL_kg, Kilif_fiyat_TL_m, Fason_birim_bedel_TL_kg_girdi, Iscilik_maliyeti_TL_saat, Elektrik_fiyati_TL_kWh, Ambalaj_TL_kg_net_urun, Bolge, Recete_profili, Isleme_modeli.
Target or realized/derived fields excluded: EKP, total batch cost, simulated net output, input-mix total, realized loss rates, material and processing cost components, labor/energy consumption, cost shares, simulation date, party ID, source label, reference codes, and notes.

Scenario A is conditional: planned inputs, process/recipe categories, quotes and tariffs may be available before a run, but this synthetic file has no immutable plan or price snapshot proving when each was known. Labor hours and energy consumption are during/after-run values and are excluded. Cost closure, measured net output, EKP, and losses are postproduction/measurement fields unless a separate timestamped plan assumption is proven.

Scenario B adds Kuruma_kaybi_pct and Ayiklama_fire_pct only as conditional inputs. The workbook states these are randomly simulated and not real batch weighings. Their measurement time is not established; if recorded after production, they are not valid preproduction features. No definite timing claim is possible from this CSV.

## Synthetic patterns and limitations

- The data workbook labels all rows simulated; recipes, quantities, prices, losses, Fason rates, in-house allocations, and calendar dates include synthetic assumptions.
- Net output is nearly exactly produced from ingredient mass and the two loss fields. The small formula residual is rounding, not an independent yield validation.
- Four highly correlated allow-listed quantity pairs reflect shared simulated batch-size/recipe scaling and may create multicollinearity for linear models.
- EKP is built from simulated total cost and net output. Observed tails, group differences, and IQR flags remain descriptive and were not manually adjusted.
- No external process inventory or aggregate cost-share rows were mixed into the training data. External inventory does not provide batch EKP labels.

Repeatable data-quality command: python -m training.report_ekp_data_quality.
Repeatable model comparison: python -m training.compare_ekp_models_chronological.
This audit reads the source CSV and writes only this report; it does not impute, remove, or rewrite source rows.
