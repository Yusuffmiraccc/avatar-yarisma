# Model doğrulama ve EKP karşılaştırması

## Kapsam ve veri sınırı

`data/raw/sucuk_uretim_1000_simule_parti.csv` içindeki 1.000 kaydın tamamı sentetik/simüledir; gerçek fabrika partisi değildir. Aşağıdaki skorlar yalnızca bu veri üretim düzenini ölçer ve gerçek fabrika performansını kanıtlamaz.

Deney, 800 eğitim ve 200 test kaydıyla sabit `train_test_split(test_size=0.2, random_state=42)` bölmesini kullanır. Temizleme ve model ayarları test hedeflerine göre seçilmedi. RF ve ExtraTrees için parametreler önceden sabitlendi. Baseline, eğitim hedef ortalamasını her test kaydı için tahmin eder.

XLSX değişken sözlüğü kayıp oranlarını deneysel aralıklardan simüle edilmiş ve gerçek tartım olmayan değerler olarak tanımlar. Fiyatların/tarifelerin parti bazında hangi anda sisteme girdiğini gösteren zaman damgası yok. Senaryo B yalnızca ayrı bir **koşullu planlama senaryosu** olarak raporlanır; veri içindeki kayıp sütunları üretim öncesi sağlanmış gerçek plan değeri değildir ve yüksek skorları üretim öncesi başarı kanıtlamaz.

## Veri sızıntısı denetimi

Özellikleri açık izin listesiyle belirledik. `Toplam_parti_maliyeti_TL`, `Net_sucuk_ciktisi_kg_simule`, `EKP_TL_kg`, maliyet bileşenleri, hedeflerden türetilen `Et_maliyet_payi_pct`, karışım toplamı ve gerçekleşmiş işçilik saati/elektrik tüketimi hiçbir tahmin girdisine alınmadı. Eğitimde kullanılan kategorik alanlar `Bolge`, `Recete_profili`, `Isleme_modeli`; OneHotEncoder bilinmeyen kategorilerde hata vermeyecek şekilde kuruldu. API de yalnızca model paketindeki özellik sütunlarını modele verir.

## Senaryo A — üretim öncesi

Sadece üretim başlamadan önce bilinebilecek girdiler: planlanan malzeme miktarları, reçete/işleme/bölge bilgisi ve önceden bilinen birim fiyat/tarifeler. Tarife alanlarının zamanlaması veriyle ispatlanmış değildir. Kayıp yüzdeleri, gerçekleşmiş işçilik saati, kWh ve gerçekleşmiş maliyetler kullanılmadı.

| Aday | Hedef | MAE | RMSE | R² | Eğitim ortalaması baseline MAE | Baseline iyileşmesi | Test n |
|---|---|---:|---:|---:|---:|---:|---:|
| RandomForest | Net çıktı (kg) | 12.1671 | 16.4788 | 0.9711 | 83.1069 | %85.36 | 200 |
| ExtraTrees | Net çıktı (kg) | 11.5390 | 15.5195 | 0.9743 | 83.1069 | %86.12 | 200 |
| RandomForest | Toplam maliyet (TL) | 3.911,05 | 5.316,77 | 0.9964 | 76.995,32 | %94.92 | 200 |
| RandomForest | EKP (TL/kg) | 49.8723 | 61.2236 | 0.1070 | 51.6755 | %3.49 | 200 |
| ExtraTrees | EKP (TL/kg) | 51.0926 | 63.1198 | 0.0509 | 51.6755 | %1.13 | 200 |
| Tahmini toplam maliyet / tahmini net çıktı | EKP (TL/kg) | 53.5409 | 67.0657 | -0.0715 | 51.6755 | -%3.61 | 200 |

EKP oran yaklaşımı, toplam parti maliyetini yalnızca A özelliklerinden tahmin eder, net üretimi A RandomForest ile tahmin eder ve oranlar. Gerçek toplam maliyet, gerçek net üretim veya gerçek EKP tahmin girdisi değildir. Net çıktı tahmini pozitif değilse oran hesaplanmaz; bu testte geçersiz çıktı sayısı sıfırdır. Bileşen bazlı toplam maliyet tahmini için üretim öncesi ölçüm tanımları mevcut değil; bu yüzden maliyet bileşenleri tek tek tahmin ediliyormuş gibi davranılmadı.

Toplam maliyet regresörü sentetik testte MAE 3.911,05 TL, RMSE 5.316,77 TL ve R² 0,9964 verdi (eğitim ortalaması baseline MAE 76.995,32 TL). Bu, sentetik maliyet formülünü A girdilerinden iyi taklit ettiğini gösterir; gerçek fabrika maliyet tahmininin geçerliliğini göstermez. EKP oranı yine baseline'dan %3,61 kötü kaldı. Net üretimdeki formül paydasını doğru tahmin etmenin maliyet tahmini kadar kolay olmadığı bu testte ayrışıyor.

EKP RandomForest'ın MAE'si hedefin yaklaşık 50 TL/kg ölçeğinde baseline'dan yalnızca 2.28 TL/kg daha düşük ve R² 0.107'dir. Bu, üretim kararı için yeterli kanıt değildir. A senaryosunda hiçbir EKP modeli üretime hazır seçilmedi.

## Senaryo B — kayıp oranları planlama varsayımı

Scenario B RandomForest ve ExtraTrees'e `Kuruma_kaybi_pct` ile `Ayiklama_fire_pct` ekler. XLSX bunları gerçek ölçüm olarak değil simülasyon girdisi olarak açıklar. Yalnızca gelecekte gerçek API isteğinde üretim öncesi belirlenmiş planlama değerleri olarak ayrı bir kaynaktan sağlanırlarsa kullanılabilir; gerçekleşmiş değerlerle aynı ad altında tutulmamalıdır.

| Aday | Hedef | MAE | RMSE | R² | Eğitim ortalaması baseline MAE | Baseline iyileşmesi | Test n |
|---|---|---:|---:|---:|---:|---:|---:|
| RandomForest | Net çıktı (kg) | 5.6535 | 7.8324 | 0.9935 | 83.1069 | %93.20 | 200 |
| RandomForest | EKP (TL/kg) | 12.8485 | 16.9392 | 0.9316 | 51.6755 | %75.14 | 200 |
| ExtraTrees | EKP (TL/kg) | 10.4697 | 14.2401 | 0.9517 | 51.6755 | %79.74 | 200 |

ExtraTrees Scenario B sentetik test bölümünde en düşük EKP MAE'sini verdi. Bu sütunlar simüle olduğundan değer yalnızca koşullu bir deney sonucudur; Scenario B üretim adayı değildir. API varsayılan olarak Scenario A kullanır; opsiyonel kayıp oranlarını tahmine katmaz. Scenario B modeli API'de etkinleştirilmedi.

## Net üretim ve kütle dengesi

Net üretim formülü:

`girdi toplamı × (1 − kuruma kaybı / 100) × (1 − ayıklama firesi / 100)`

Gerçekleşmiş kayıp oranlarını kullanan formül aynı 200 test kaydında MAE 0.0003 kg, RMSE 0.0003 kg, R² yaklaşık 1.0000 verdi. Bu beklenen deterministik eşitliği doğrular; üretim öncesi tahmin başarısı değildir. Kayıp yüzdeleri önceden belirlenip güvenilir plan girdisi değilse, formüle onları koyarak bir tahmin iddia edilemez. Gerçekleşmiş kayıp değerleri formülün doğruluğunu denetlemeye yarar, tahmin girdisi olmaya değil.

Net çıktı RandomForest kütle dengesi formülünü pratik olarak taklit ediyor; hata kaynağı sentetik hedefteki küçük yuvarlama/ölçüm farkları. Gerçek zamanlı ve önceden bilinen kayıp varsayımlarıyla formül daha açıklanabilir bir referanstır. RF'nin formüle ek değeri gösterilmedi; gerçek veride bağımsız doğrulama olmadan model üstünlüğü iddia edilemez.

## Aday seçimi ve dosyalar

Üretim için yeni aday seçilmedi. EKP A senaryosu baseline'dan yeterince iyi değil; B senaryosu ise varsayımların ölçüm zamanı kanıtlanmadığı ve veri tamamen sentetik olduğu için etkinleştirilemez. Net üretim RF tekrar üretilebilir bir aday, ExtraTrees testte biraz daha iyi olsa da iki skor da sentetik hedefin formülünü öğreniyor. Mevcut API modelleri değiştirilmedi.

Yeni deney çıktıları `models/*_candidate.joblib` altındadır. Net çıktı RandomForest A paketi `yield_random_forest_candidate.joblib`, EKP A RF `ekp_random_forest_A_candidate.joblib`, EKP B ExtraTrees `ekp_extra_trees_B_candidate.joblib` içindedir. Paketler `feature_columns` metaverisiyle kaydedilir; API'deki tahmin kodu da paket metaverisi veya eğitimdeki sütun adları/sırasını kullanır. Adaylar canlı dosya adlarına terfi ettirilmedi.

## API ve güvenlik

`POST /v1/predict/production` API anahtarı kontrolünü korur ve sadece eğitim özelliklerini kullanır. İsteğe bağlı legacy kayıp yüzdeleri, işçilik saati ve elektrik tüketimi tahminde kullanılmaz. Model yanıtı EKP'nin üretime hazır olmadığını açıkça söyler. `/v1/evaluate/production` gerçekleşmiş net çıktı ve toplam maliyeti yalnızca sonuç karşılaştırması için alır; response tahmin, gerçekleşen çıktı, çıktı farkı, tahmin EKP, gerçekleşen toplam maliyet, gerçekleşen EKP ve EKP farkını ayrı verir. Her fark `tahmin - gerçekleşen` olup artı değer fazla tahmindir. Değerlendirme endpoint'i de API anahtarı kontrolünden geçer. Gerçek net çıktı sıfır veya gerçek maliyet sıfır olduğunda şema 422 döndürür. Model dosyası eksik/bozuksa 503 ve yollara ilişkin olmayan genel mesaj döner. `APP_ENV` geliştirme/test dışında ve `API_KEY` boşsa POST'lar fail-closed 503 verir. Fazladan/eksik alanlar, yanlış türler, negatif/sonlu olmayan sayılar doğrulama hatası verir.

## Test sonucu

Proje sanal ortamı: `ai/.venv` — Python 3.12.10, pytest 8.4.2.

`python -m pytest -v`: **15 passed**, 0 failed. Model anahtarı, production'da anahtar yokken fail-closed, eksik/bozuk model dosyası, mevcut joblib modellerinin gerçek yüklemesi ve tahmini dahil endpoint sınırı test edildi. Değerlendirme için kullanılan örnek değerler sentetik/test amaçlıdır. Yalnızca Starlette TestClient/httpx kullanımıyla ilgili bir deprecation uyarısı alındı. Tam test listesi `reports/api_test_report.md` içindedir.

## Gerçek veriye geçiş ve dış doğrulama

1. Gerçek üretim emri, üretim öncesi fiyat/tarife anlık görüntüsü, planlanan fire varsayımları ve gerçekleşmiş üretim çıktısı/maliyet/işçilik/kWh kayıtlarını zaman damgası ve parti kimliğiyle ayrı alanlarda toplayın.
2. Kayıtların sentetik olmadığını kaynak sistemiyle doğrulayın; yinelenen partileri, eksikleri ve maliyet mutabakatını denetleyin.
3. Eğitim ve test bölmesini zamana göre kurun; en yeni, model seçiminde hiç kullanılmamış gerçek partileri dış doğrulama seti olarak saklayın. Mümkünse farklı dönem/hatlarda da değerlendirin.
4. MAE/RMSE'yi TL/kg ve kg cinsinden raporlayın; baseline, hata dağılımı, rejim/ürün grubu kırılımları ve maliyet mutabakatıyla birlikte inceleyin.
5. EKP baseline'ı anlamlı ve kararlı biçimde geçmeden modeli karar veya muhasebe akışına bağlamayın. Önce gölge modda tahmin edip gerçek sonuçlarla karşılaştırın.



## Tekrarlanabilir doğrulama — 24.10.2026

`training.validate_models.main()` tekrar çalıştırıldı; çıktı geçici dizine yönlendirildi, bu nedenle mevcut üretim modelleri, aday dosyaları ve rapor artefaktları üzerine yazılmadı. Sabit 800/200 bölmesinde aşağıdaki A senaryosu metrikleri mevcut raporla eşleşti:

| Aday | MAE | RMSE | R² | Eğitim ortalaması baseline MAE |
|---|---:|---:|---:|---:|
| Net çıktı RandomForest A | 12,1671 kg | 16,4788 kg | 0,9711 | 83,1069 kg |
| Net çıktı ExtraTrees A | 11,5390 kg | 15,5195 kg | 0,9743 | 83,1069 kg |
| EKP RandomForest A | 49,8723 TL/kg | 61,2236 TL/kg | 0,1070 | 51,6755 TL/kg |
| EKP ExtraTrees A | 51,0926 TL/kg | 63,1198 TL/kg | 0,0509 | 51,6755 TL/kg |
| Tahmini maliyet / tahmini net çıktı A | 53,5409 TL/kg | 67,0657 TL/kg | -0,0715 | 51,6755 TL/kg |

Kayıp yüzdeleri gerçekleşmiş/simüle değerleri kullanıldığında kütle dengesi tanısının MAE’si 0,000261 kg’dır; bu üretim öncesi tahmin metriği değildir. Senaryo B ve maliyet/net çıktı oranı değerlendirmeleri de sentetik holdout ile sınırlıdır. A özelliklerindeki fiyat ve tarife alanlarının gerçek partilerde tahmin öncesi zaman damgası ayrıca doğrulanmalıdır. EKP için üretime hazır model yoktur.
## EKP aday karşılaştırması — 24.10.2026

training/compare_ekp_models.py, aynı 1.000 sentetik kayıtta 5 katlı CV çalıştırdı. Mevcut RF: MAE 49,9314 ± 3,1800 TL/kg, RMSE 61,2698 ± 4,4614, R² 0,1240 ± 0,0469. Formül ile türetilen malzeme/fason alt toplam özellikleri kullanan Huber GradientBoosting adayı: MAE 48,9869 ± 2,8174, RMSE 60,5653 ± 3,7470, R² 0,1436 ± 0,0313. Medyan Dummy baseline MAE 52,1642 ± 3,6097. Aday CV'de MAE'yi RF'ye göre %1,89 düşürdü.

Bu sonuç sentetik dağılımla sınırlı. Önceden kullanılan 800/200 holdout bağımsız değildir; orada aday 48,8140 / 61,1269 / 0,1098, mevcut üretim artefaktı 49,8723 / 61,2236 / 0,1070 verdi. Ölçüm zamanı doğrulanmamış fiyat/tarife girdileri hâlâ A senaryosunun riskidir. Aday ayrı models/candidates/ekp_gradient_boosting_huber_engineered_20261024.joblib dosyasına kaydedildi; API modeli değiştirilmedi ve aday üretime hazır değildir. Maliyet/net çıktı oranı ve hibrit alternatifler baseline'ı geçemedi. Tam sonuç: reports/ekp_improvement_report.md ve reports/ekp_improvement_comparison.json.
## Gerçek veri kronolojik değerlendirme altyapısı — 24.10.2026

training/validate_ekp_chronological.py sentetik/benchmark veriyi reddeden, zaman damgalı ve onaylanmış gerçek partiler bekleyen ayrı bir değerlendirme hattıdır. Üç expanding-window holdout, en az 50 tarihsel batch, pencerede 20 farklı test üretim zamanı ve üç pencere varsayılanıdır. Her fold'da eğitim etiketinin kaydedilme/onay zamanı test başlangıcından önce olmalıdır. Preprocessing ve estimator fit'i eğitim penceresi içinde tutulur; aynı test partileri direct EKP, geçmişten refit edilen RF/GradientBoosting-Huber, hash'i sabitlenmiş mevcut/sentetik frozen modeller, tahmini toplam maliyet/tahmini net çıktı ve hibrit yol için ortaktır.

Gerçek üretim veri dosyası bulunmadığından betik boş CSV şablonunda no_real_data döndürdü ve metrik üretmedi. Bu yeni sonuç değildir; önceki 1.000 sentetik kayıttan hesaplanan MAE/RMSE/R² sonuçları değişmeden sentetik araştırma/holdout raporlarında kalır. Üretim modeli üzerine yazılmadı. Frozen artifact SHA-256 eşleşmesi yalnızca bayt bütünlüğü kontrolüdür; kaynak sahipliği, imza veya bilimsel doğrulama değildir. Kayıp oranlarının ölçüm zamanı ve gerçek maliyet bileşeni muhasebe kapsamı ayrıca tesis kayıtlarından doğrulanmalıdır.
