# Model 2 ? Sentetik Test Raporu

- Model s?r?m?: model-b-ridge-20261024-synthetic-v1
- Veri s?r?m?: model-b-synthetic-v1
- Test k?mesi: 180 kay?t
- Ayr?nt?l? ?rnek: 10 kay?t
- Veri kayna??: SENTETIK_SIMULASYON
- ?retim onay?: YOK

## Genel metrikler ? tam test k?mesi

- MAE: 1.8439 kg
- RMSE: 3.4556 kg
- R? (uniform average): 0.9022
- Mutlak hata ? 1 kg: %63.06
- Mutlak hata ? 2 kg: %75.49

## Hedef baz?nda metrikler

| hedef              |   test_kayit_sayisi |   tam_test_MAE_kg |   tam_test_RMSE_kg |   tam_test_R2 |   10_ornek_MAE_kg |   10_ornek_RMSE_kg |   tam_test_mutlak_hata_1kg_veya_altinda_pct |   tam_test_mutlak_hata_2kg_veya_altinda_pct |
|:-------------------|--------------------:|------------------:|-------------------:|--------------:|------------------:|-------------------:|--------------------------------------------:|--------------------------------------------:|
| but_kg             |                 180 |            2.2415 |             4.0674 |        0.9647 |            1.9025 |             2.7636 |                                     57.7778 |                                     75.5556 |
| sirt_kg            |                 180 |            1.9175 |             3.4497 |        0.9433 |            2.8988 |             4.9379 |                                     60.5556 |                                     71.1111 |
| omuz_kg            |                 180 |            1.8232 |             3.1187 |        0.9525 |            2.7065 |             3.9499 |                                     62.2222 |                                     75.0000 |
| kaburga_kg         |                 180 |            2.4258 |             4.4268 |        0.9342 |            2.9774 |             4.5136 |                                     59.4444 |                                     71.6667 |
| kiyma_kg           |                 180 |            2.7486 |             4.7508 |        0.9830 |            3.4150 |             4.7965 |                                     53.8889 |                                     68.3333 |
| yan_urun_kg        |                 180 |            1.6257 |             3.0474 |        0.9090 |            1.5520 |             2.6493 |                                     65.0000 |                                     77.2222 |
| kemik_yag_sinir_kg |                 180 |            1.0097 |             1.7939 |        0.7416 |            0.9919 |             1.5020 |                                     71.1111 |                                     81.6667 |
| fire_kg            |                 180 |            0.9590 |             1.6399 |        0.7891 |            1.8470 |             2.7871 |                                     74.4444 |                                     83.3333 |

## 10 ?rne?in par?a tahminleri

| kayit_id       | hayvan_turu   |   karkas_agirligi_kg | hedef              |   referans_kg |   tahmin_kg |   hata_kg |   mutlak_hata_kg |
|:---------------|:--------------|---------------------:|:-------------------|--------------:|------------:|----------:|-----------------:|
| SYN-KOYUN-0158 | koyun         |               30.650 | but_kg             |         6.358 |       6.166 |    -0.192 |            0.192 |
| SYN-KOYUN-0158 | koyun         |               30.650 | sirt_kg            |         2.632 |       3.477 |     0.845 |            0.845 |
| SYN-KOYUN-0158 | koyun         |               30.650 | omuz_kg            |         4.841 |       4.453 |    -0.388 |            0.388 |
| SYN-KOYUN-0158 | koyun         |               30.650 | kaburga_kg         |         5.447 |       5.049 |    -0.398 |            0.398 |
| SYN-KOYUN-0158 | koyun         |               30.650 | kiyma_kg           |         4.947 |       6.362 |     1.415 |            1.415 |
| SYN-KOYUN-0158 | koyun         |               30.650 | yan_urun_kg        |         3.806 |       3.178 |    -0.628 |            0.628 |
| SYN-KOYUN-0158 | koyun         |               30.650 | kemik_yag_sinir_kg |         1.128 |       0.889 |    -0.239 |            0.239 |
| SYN-KOYUN-0158 | koyun         |               30.650 | fire_kg            |         1.491 |       1.057 |    -0.434 |            0.434 |
| SYN-DANA-0325  | dana          |              270.460 | but_kg             |        43.283 |      50.461 |     7.178 |            7.178 |
| SYN-DANA-0325  | dana          |              270.460 | sirt_kg            |        37.066 |      31.176 |    -5.890 |            5.890 |
| SYN-DANA-0325  | dana          |              270.460 | omuz_kg            |        24.385 |      32.260 |     7.875 |            7.875 |
| SYN-DANA-0325  | dana          |              270.460 | kaburga_kg         |        34.229 |      39.290 |     5.061 |            5.061 |
| SYN-DANA-0325  | dana          |              270.460 | kiyma_kg           |        92.785 |      81.668 |   -11.117 |           11.117 |
| SYN-DANA-0325  | dana          |              270.460 | yan_urun_kg        |        17.935 |      20.940 |     3.005 |            3.005 |
| SYN-DANA-0325  | dana          |              270.460 | kemik_yag_sinir_kg |         9.663 |       6.482 |    -3.181 |            3.181 |
| SYN-DANA-0325  | dana          |              270.460 | fire_kg            |        11.114 |       8.122 |    -2.992 |            2.992 |
| SYN-KOYUN-0059 | koyun         |               24.910 | but_kg             |         3.991 |       5.024 |     1.033 |            1.033 |
| SYN-KOYUN-0059 | koyun         |               24.910 | sirt_kg            |         2.683 |       2.903 |     0.220 |            0.220 |
| SYN-KOYUN-0059 | koyun         |               24.910 | omuz_kg            |         3.403 |       3.798 |     0.395 |            0.395 |
| SYN-KOYUN-0059 | koyun         |               24.910 | kaburga_kg         |         3.708 |       4.268 |     0.560 |            0.560 |
| SYN-KOYUN-0059 | koyun         |               24.910 | kiyma_kg           |         6.279 |       4.674 |    -1.605 |            1.605 |
| SYN-KOYUN-0059 | koyun         |               24.910 | yan_urun_kg        |         2.976 |       2.716 |    -0.260 |            0.260 |
| SYN-KOYUN-0059 | koyun         |               24.910 | kemik_yag_sinir_kg |         1.306 |       0.785 |    -0.521 |            0.521 |
| SYN-KOYUN-0059 | koyun         |               24.910 | fire_kg            |         0.564 |       0.895 |     0.331 |            0.331 |
| SYN-KOYUN-0002 | koyun         |               26.250 | but_kg             |         6.254 |       5.290 |    -0.964 |            0.964 |
| SYN-KOYUN-0002 | koyun         |               26.250 | sirt_kg            |         2.441 |       3.037 |     0.596 |            0.596 |
| SYN-KOYUN-0002 | koyun         |               26.250 | omuz_kg            |         4.543 |       3.951 |    -0.592 |            0.592 |
| SYN-KOYUN-0002 | koyun         |               26.250 | kaburga_kg         |         3.927 |       4.450 |     0.523 |            0.523 |
| SYN-KOYUN-0002 | koyun         |               26.250 | kiyma_kg           |         4.658 |       5.068 |     0.410 |            0.410 |
| SYN-KOYUN-0002 | koyun         |               26.250 | yan_urun_kg        |         2.813 |       2.824 |     0.011 |            0.011 |
| SYN-KOYUN-0002 | koyun         |               26.250 | kemik_yag_sinir_kg |         0.707 |       0.809 |     0.102 |            0.102 |
| SYN-KOYUN-0002 | koyun         |               26.250 | fire_kg            |         0.907 |       0.933 |     0.026 |            0.026 |
| SYN-DANA-0324  | dana          |              270.200 | but_kg             |        51.898 |      50.410 |    -1.488 |            1.488 |
| SYN-DANA-0324  | dana          |              270.200 | sirt_kg            |        45.096 |      31.150 |   -13.946 |           13.946 |
| SYN-DANA-0324  | dana          |              270.200 | omuz_kg            |        35.821 |      32.230 |    -3.591 |            3.591 |
| SYN-DANA-0324  | dana          |              270.200 | kaburga_kg         |        28.526 |      39.254 |    10.728 |           10.728 |
| SYN-DANA-0324  | dana          |              270.200 | kiyma_kg           |        77.136 |      81.592 |     4.456 |            4.456 |
| SYN-DANA-0324  | dana          |              270.200 | yan_urun_kg        |        13.598 |      20.919 |     7.321 |            7.321 |
| SYN-DANA-0324  | dana          |              270.200 | kemik_yag_sinir_kg |         5.363 |       6.477 |     1.114 |            1.114 |
| SYN-DANA-0324  | dana          |              270.200 | fire_kg            |        12.762 |       8.114 |    -4.648 |            4.648 |
| SYN-DANA-0139  | dana          |              273.240 | but_kg             |        52.104 |      51.015 |    -1.089 |            1.089 |
| SYN-DANA-0139  | dana          |              273.240 | sirt_kg            |        29.017 |      31.454 |     2.437 |            2.437 |
| SYN-DANA-0139  | dana          |              273.240 | omuz_kg            |        39.431 |      32.577 |    -6.854 |            6.854 |
| SYN-DANA-0139  | dana          |              273.240 | kaburga_kg         |        44.804 |      39.668 |    -5.136 |            5.136 |
| SYN-DANA-0139  | dana          |              273.240 | kiyma_kg           |        74.745 |      82.486 |     7.741 |            7.741 |
| SYN-DANA-0139  | dana          |              273.240 | yan_urun_kg        |        23.599 |      21.164 |    -2.435 |            2.435 |
| SYN-DANA-0139  | dana          |              273.240 | kemik_yag_sinir_kg |         7.373 |       6.532 |    -0.841 |            0.841 |
| SYN-DANA-0139  | dana          |              273.240 | fire_kg            |         2.167 |       8.200 |     6.033 |            6.033 |
| SYN-KUZU-0122  | kuzu          |               19.000 | but_kg             |         4.249 |       3.901 |    -0.348 |            0.348 |
| SYN-KUZU-0122  | kuzu          |               19.000 | sirt_kg            |         2.891 |       2.153 |    -0.738 |            0.738 |
| SYN-KUZU-0122  | kuzu          |               19.000 | omuz_kg            |         2.188 |       2.795 |     0.607 |            0.607 |
| SYN-KUZU-0122  | kuzu          |               19.000 | kaburga_kg         |         3.136 |       3.143 |     0.007 |            0.007 |
| SYN-KUZU-0122  | kuzu          |               19.000 | kiyma_kg           |         3.289 |       3.895 |     0.606 |            0.606 |
| SYN-KUZU-0122  | kuzu          |               19.000 | yan_urun_kg        |         1.641 |       1.983 |     0.342 |            0.342 |
| SYN-KUZU-0122  | kuzu          |               19.000 | kemik_yag_sinir_kg |         0.982 |       0.483 |    -0.499 |            0.499 |
| SYN-KUZU-0122  | kuzu          |               19.000 | fire_kg            |         0.624 |       0.671 |     0.047 |            0.047 |
| SYN-KOYUN-0370 | koyun         |               31.370 | but_kg             |         5.088 |       6.309 |     1.221 |            1.221 |
| SYN-KOYUN-0370 | koyun         |               31.370 | sirt_kg            |         4.630 |       3.549 |    -1.081 |            1.081 |
| SYN-KOYUN-0370 | koyun         |               31.370 | omuz_kg            |         3.680 |       4.535 |     0.855 |            0.855 |
| SYN-KOYUN-0370 | koyun         |               31.370 | kaburga_kg         |         6.035 |       5.146 |    -0.889 |            0.889 |
| SYN-KOYUN-0370 | koyun         |               31.370 | kiyma_kg           |         6.941 |       6.574 |    -0.367 |            0.367 |
| SYN-KOYUN-0370 | koyun         |               31.370 | yan_urun_kg        |         3.061 |       3.236 |     0.175 |            0.175 |
| SYN-KOYUN-0370 | koyun         |               31.370 | kemik_yag_sinir_kg |         0.617 |       0.902 |     0.285 |            0.285 |
| SYN-KOYUN-0370 | koyun         |               31.370 | fire_kg            |         1.318 |       1.077 |    -0.241 |            0.241 |
| SYN-DANA-0265  | dana          |              300.300 | but_kg             |        52.500 |      56.398 |     3.898 |            3.898 |
| SYN-DANA-0265  | dana          |              300.300 | sirt_kg            |        36.351 |      34.162 |    -2.189 |            2.189 |
| SYN-DANA-0265  | dana          |              300.300 | omuz_kg            |        41.349 |      35.664 |    -5.685 |            5.685 |
| SYN-DANA-0265  | dana          |              300.300 | kaburga_kg         |        37.451 |      43.348 |     5.897 |            5.897 |
| SYN-DANA-0265  | dana          |              300.300 | kiyma_kg           |        94.280 |      90.446 |    -3.834 |            3.834 |
| SYN-DANA-0265  | dana          |              300.300 | yan_urun_kg        |        22.428 |      23.342 |     0.914 |            0.914 |
| SYN-DANA-0265  | dana          |              300.300 | kemik_yag_sinir_kg |        10.155 |       7.021 |    -3.134 |            3.134 |
| SYN-DANA-0265  | dana          |              300.300 | fire_kg            |         5.786 |       8.960 |     3.174 |            3.174 |
| SYN-KOYUN-0394 | koyun         |               22.250 | but_kg             |         2.881 |       4.495 |     1.614 |            1.614 |
| SYN-KOYUN-0394 | koyun         |               22.250 | sirt_kg            |         1.591 |       2.637 |     1.046 |            1.046 |
| SYN-KOYUN-0394 | koyun         |               22.250 | omuz_kg            |         3.717 |       3.495 |    -0.222 |            0.222 |
| SYN-KOYUN-0394 | koyun         |               22.250 | kaburga_kg         |         4.481 |       3.906 |    -0.575 |            0.575 |
| SYN-KOYUN-0394 | koyun         |               22.250 | kiyma_kg           |         6.490 |       3.891 |    -2.599 |            2.599 |
| SYN-KOYUN-0394 | koyun         |               22.250 | yan_urun_kg        |         2.073 |       2.502 |     0.429 |            0.429 |
| SYN-KOYUN-0394 | koyun         |               22.250 | kemik_yag_sinir_kg |         0.740 |       0.737 |    -0.003 |            0.003 |
| SYN-KOYUN-0394 | koyun         |               22.250 | fire_kg            |         0.277 |       0.821 |     0.544 |            0.544 |

## 10 ?rne?in a??rl?k dengesi

| kayit_id       | hayvan_turu   |   karkas_agirligi_kg |   referans_parca_toplami_kg |   tahmin_parca_toplami_kg |   tahmin_toplami_eksi_karkas_kg |
|:---------------|:--------------|---------------------:|----------------------------:|--------------------------:|--------------------------------:|
| SYN-KOYUN-0158 | koyun         |               30.650 |                      30.650 |                    30.629 |                          -0.021 |
| SYN-DANA-0325  | dana          |              270.460 |                     270.460 |                   270.399 |                          -0.061 |
| SYN-KOYUN-0059 | koyun         |               24.910 |                      24.910 |                    25.062 |                           0.152 |
| SYN-KOYUN-0002 | koyun         |               26.250 |                      26.250 |                    26.362 |                           0.112 |
| SYN-DANA-0324  | dana          |              270.200 |                     270.200 |                   270.147 |                          -0.053 |
| SYN-DANA-0139  | dana          |              273.240 |                     273.240 |                   273.095 |                          -0.145 |
| SYN-KUZU-0122  | kuzu          |               19.000 |                      19.000 |                    19.024 |                           0.024 |
| SYN-KOYUN-0370 | koyun         |               31.370 |                      31.370 |                    31.328 |                          -0.042 |
| SYN-DANA-0265  | dana          |              300.300 |                     300.300 |                   299.340 |                          -0.960 |
| SYN-KOYUN-0394 | koyun         |               22.250 |                      22.250 |                    22.483 |                           0.233 |

## Yorumlama s?n?rlar?

- MAE ve RMSE kilogram cinsinden hata ?l??leridir; d???k de?er daha iyidir.
- R? bir do?ruluk y?zdesi de?ildir.
- Tolerans oranlar?, tahminlerin referans de?erden belirtilen kg s?n?r?nda kalma oran?d?r.
- T?m de?erlendirme verileri sentetiktir; sonu?lar ger?ek saha ba?ar?s?n? g?stermez.
- Par?a toplam?n?n karkas a??rl???na e?it olmas? otomatik olarak garanti edilmez.