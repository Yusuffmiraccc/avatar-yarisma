# AVATAR Yarışma — ML API başlangıç paketi

Bu paket, yönergedeki **4-A üretim verimi ve EKP tahmini** için ilk çalıştırılabilir ML servisini içerir. Eğitim verisi olarak sağlanan 1.000 satırlık CSV pakete eklenmiştir.

## Önemli veri doğruluğu notu
XLSX dosyasının `Baslangic_ve_Yontem` sayfası, 1.000 partinin tamamının **sentetik/simüle** olduğunu ve gerçek firma parti kayıtları olmadığını belirtiyor. Kaynak sayfasındaki bazı fiyatlar gözlemlenmiş olsa da bu, eğitim satırlarını gerçek yapmaz. Dolayısıyla ilk eğitim teknik prototip içindir; gerçek performans iddiası değildir.

## Mimari
- Python 3.11 veya 3.12
- FastAPI REST API
- pandas + scikit-learn + joblib
- Model 1 eğitim verisini CSV’den okur, aday artefaktları `models/` içine yazar. Model 1 tahminleri dosya tabanlıdır; Model 2 tahmin/gerçekleşen tartım denetimi SQLite volume’una kaydedilir.
- Bu bir **ML servis API'sidir**. Dış bir üçüncü taraf API'sine bağlanmak için şu aşamada anahtar gerekmez.
- Üretim sisteminde MySQL merkezi kayıt sistemi olmalı; bu ML API, ana backend'den HTTP ile çağrılmalı. Lot izlenebilirliği ve geri çağırma asla tahmin modeline bırakılmamalıdır.

## Aşama planı
1. **Ortam kurulumu:** Python, sanal ortam ve bağımlılıklar.
2. **Veri denetimi:** sütunlar, eksikler, uç değerler, hedeflerin mantığı ve sentetik veri etiketi.
3. **İlk eğitim:** üretim çıktısı ve EKP için ayrı modeller; eğitim/test ayrımı.
4. **Değerlendirme:** MAE, RMSE, R² ve hedef ortalamasını tahmin eden basit baseline karşılaştırması.
5. **API:** `/health`, `/v1/models/status`, `/v1/predict/production`, Swagger `/docs`.
6. **Entegrasyon:** ana backend REST üzerinden bu servisi çağırır; API anahtarı ortam değişkeninden verilir.
7. **Gerçek veriyle doğrulama:** gerçekleşen üretim sonucu, gerçek maliyet ve gerçek fire kayıtları toplanır; zamana göre ayrılmış test yapılır.
8. **İkinci zorunlu model:** kuzu parçalama verimi. Mevcut yüklenen veri setleri sucuk üretim partileri içeriyor; kuzu türü/giriş ağırlığı/parça bazlı gerçek sonuç sütunları bulunmadığından bu model dürüstçe eğitilemez. Uygun parçalama veri seti sağlanınca ayrı eğitim hattı eklenmeli.

## Windows PowerShell kurulumu
PowerShell'i proje klasöründe açın:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

PowerShell aktivasyon engeli alırsanız sadece mevcut terminal oturumu için:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Modelleri değerlendir ve aday üret
Proje kök dizinindeyken:

```powershell
python -m training.validate_models
```

Bu komut sabit 80/20 (`random_state=42`) split üzerinde RandomForest ve ExtraTrees adaylarını karşılaştırır. `models/*_candidate.joblib`, `reports/training_metrics.json`, `reports/model_comparison.json` ve `reports/model_validation.md` dosyalarını üretir. API'nin kullandığı `models/yield_model.joblib` ve `models/ekp_model.joblib` üzerine yazmaz.

Eski tek model eğitim hattını tekrar çalıştırmak isterseniz:

```powershell
python -m training.train_production
```

Bu komut da güvenlik için `yield_model_candidate.joblib`, `ekp_model_candidate.joblib` ve `reports/production_training_candidate_metrics.json` üretir; API'deki modelleri ya da güncel doğrulama raporunu değiştirmez.

## API'yi çalıştır
```powershell
$env:API_KEY = "yerel-test-anahtari"
uvicorn app.main:app --reload
```

Tarayıcı:
- `http://127.0.0.1:8000/health (doğrudan yerel Uvicorn)`
- `http://127.0.0.1:8000/docs (doğrudan yerel Uvicorn)`
- `http://127.0.0.1:8000/v1/models/status (doğrudan yerel Uvicorn)`


## Docker ile çalıştırma

`ai` klasöründen (bu dosyanın bir üst klasörü) çalıştırın. Compose API’yi yalnızca `127.0.0.1:8001` üzerinde yayınlar; ana backend’in `8000` portunu değiştirmez. `API_KEY` değerini terminal ortamına veya gizli değişken yöneticisine koyun; raporlara ya da kaynak koda yazmayın.

```powershell
$env:API_KEY = "yerel-test-anahtari"
docker compose -f Model1/docker-compose.yml config -q
docker compose -f Model1/docker-compose.yml build
docker compose -f Model1/docker-compose.yml up -d
Invoke-RestMethod http://127.0.0.1:8001/health
Invoke-RestMethod http://127.0.0.1:8001/v1/models/status
```

Build bağlamındaki `ai/.dockerignore` ortam dosyalarını, CSV/XLSX verilerini, model artefaktlarını ve raporları dışarıda tutar. Compose healthcheck `GET /health` endpoint’i üzerinden API sürecini kontrol eder; container root filesystem’i salt okunur, tüm Linux capability’leri düşürülmüş ve `no-new-privileges` etkin durumdadır. SQLite için ayrılmış named volume yazılabilir kalır. Model1 modelleri ve raporları salt okunur bind mount’tur. Model2 audit SQLite verisi `model_b_audit_data` adlı kalıcı volume’da tutulur; container yeniden oluşturulurken volume silinmemelidir.

## Tahmin isteği örneği
`/docs` ekranında `POST /v1/predict/production` seçin. API anahtarı yalnızca `API_KEY` ortam değişkeni doluysa zorunludur. Aşağıdaki istek yalnızca Scenario A'nın allow-list özelliklerini içerir; örnek değerler simülasyon içindir.

```json
{
  "Et_girdi_kg": 200,
  "Kuyruk_yagi_girdi_kg": 40,
  "Baharat_girdi_kg": 12,
  "Tuz_girdi_kg": 4,
  "Diger_kucuk_girdi_kg": 1,
  "Kilif_metre": 300,
  "Et_fiyat_TL_kg": 590,
  "Kuyruk_yagi_fiyat_TL_kg": 420,
  "Baharat_fiyat_TL_kg": 400,
  "Tuz_fiyat_TL_kg": 20,
  "Kilif_fiyat_TL_m": 44,
  "Fason_birim_bedel_TL_kg_girdi": 100,
  "Iscilik_maliyeti_TL_saat": 175,
  "Elektrik_fiyati_TL_kWh": 4.8,
  "Ambalaj_TL_kg_net_urun": 5.5,
  "Bolge": "İç Anadolu",
  "Recete_profili": "MEB_STANDART",
  "Isleme_modeli": "Fason"
}
```

Örnek yanıt biçimi (mevcut sentetik prototip modeliyle elde edilmiş örnek):

```json
{
  "predicted_net_output_kg": 314.451,
  "predicted_ekp_tl_per_kg": 932.97,
  "model_notice": "EKP modeli üretim kullanımı için hazır değildir. Eğitim verisi sentetik/simüledir; tahminler dış doğrulama olmadan karar veya muhasebe kaydı için kullanılmamalıdır. Bu Scenario A endpoint'i opsiyonel kuruma/ayıklama alanlarını kullanmaz; Scenario B için bu alanlar ancak üretim öncesi planlama varsayımı olarak doğrulanırsa kullanılabilir. Gerçekleşmiş ölçümleri tahmin girdisi olarak göndermeyin."
}
```

Tahmin isteği sayısal JSON türlerini katı doğrular; sayısal metin ve boolean değerleri kabul etmez. Bölge, reçete ve işleme kategorileri eğitim CSV’sindeki bilinen kategorilerle sınırlandırılmıştır. Yanıttaki net çıktı girdilerin toplam kütlesini aşarsa veya tahmin sonlu/negatiflik sınırlarını ihlal ederse API güvenli 503 döndürür.

`POST /v1/evaluate/production` tahmin sonrasında gerçekleşen sonuçları karşılaştırır. Örnek test girdisi:

```json
{
  "predicted_net_output_kg": 85,
  "actual_net_output_kg": 82,
  "predicted_ekp_tl_per_kg": 180,
  "actual_total_cost_tl": 15170
}
```

Yanıt tahmini/gerçekleşen çıktıyı, `actual_total_cost_tl` değerini, gerçekleşen EKP'yi ve farkları ayrı verir. `fark = tahmin - gerçekleşen`; pozitif fark fazla, negatif fark düşük tahmin demektir. Bu test örneğinde gerçekleşen EKP 15.170 / 82 = 185 TL/kg ve EKP farkı -5 TL/kg'dır. Bu değerler test amaçlıdır, gerçek fabrika kaydı değildir.

Endpoint'ler:

- `GET /health`: herkese açık sağlık kontrolü.
- `GET /v1/models/status`: model dosyalarının durumu ve EKP hazır değil uyarısı.
- `POST /v1/predict/production`: tahmin. `API_KEY` ayarlıysa `x-api-key` gerektirir.
- `POST /v1/evaluate/production`: gerçekleşen sonuç karşılaştırması. `API_KEY` ayarlıysa `x-api-key` gerektirir.
- `GET /docs`: Swagger arayüzü.

Üretim ortamında `APP_ENV=production` ve güçlü bir `API_KEY` değerini gizli ortam değişkeni/secret store üzerinden sağlayın; kaynak koda veya loglara yazmayın. `API_KEY` boşken geliştirme/test ortamı anahtarsız çalışır; development dışı ortamda anahtar yoksa POST uçları fail-closed olarak 503 verir. Canlıya çıkarken TLS ve ağ/erişim kontrolü de zorunludur.

## Test

Sanal ortam etkin ve çalışma dizini `ai/Model1` iken:

```powershell
python -m pytest -v
```

Son tam doğrulama (24.10.2026): **78 test geçti, 0 başarısız, 1 Starlette/httpx deprecation uyarısı**. Bağımlılıklar değiştirilmedi. Veri testleri mevcut sentetik CSV’yi ve boş gerçek-veri şablonu/validasyon kurallarını denetler. Bu sonuçlar gerçek fabrika doğrulaması değildir.

## 4. aşama doğrulaması

Leakage-aware karşılaştırmayı ayrı aday dosyaları üretmek için çalıştırın:

```powershell
python -m training.validate_models
```

Bu komut `reports/training_metrics.json` ve `reports/model_comparison.json` raporlarını günceller, deney modellerini `models/*_candidate.joblib` adlarıyla kaydeder ve API'nin mevcut model dosyalarını değiştirmez. Yöntem, sonuçlar ve sınırlamalar `reports/model_validation.md` içindedir.

API varsayılan olarak **Scenario A** kullanır: yalnızca üretim başlamadan önce bilinebilecek özellikler modele gider. Kuruma/ayıklama yüzdeleri şemada geriye dönük uyumluluk için opsiyoneldir, Scenario A tahmininde yok sayılır. Scenario B'de bu alanlar yalnızca üretim öncesinde belirlenmiş plan varsayımları olabilir; CSV bunların zamanlamasını kanıtlamıyor ve Scenario B modeli API'ye etkinleştirilmemiştir. Gerçekleşmiş işçilik saati, elektrik tüketimi ve maliyetler tahmin isteğine eklenmemelidir.

EKP modeli baseline'dan yeterli farkla ayrışmadığı için üretime hazır sayılmaz. Veri setindeki 1.000 kaydın tamamı sentetik/simüledir; sonuçlar gerçek fabrika performansını kanıtlamaz. Gerçek kayıtlarla bağımsız, zamana göre ayrılmış dış doğrulama yapılmadan modeller karar veya muhasebe akışında kullanılmamalıdır.

## Mevcut metrikler ve kullanım kararı

Son sabit test bölümünde Scenario A net çıktı RandomForest MAE 12,1671 kg, RMSE 16,4788 kg, R² 0,9711; EKP RandomForest MAE 49,8723 TL/kg, RMSE 61,2236 TL/kg, R² 0,1070 ve eğitim-ortalaması baseline MAE 51,6755 TL/kg (yalnızca %3,49 iyileşme) verdi. EKP modeli **üretime hazır değildir**. Scenario B kayıp oranlarını plan varsayımı olarak kullanırsa sentetik veride EKP ExtraTrees MAE 10,4697 TL/kg verir; workbook kayıpların simüle olduğunu söylediğinden bu metrik ölçüm erişilebilirliğini veya gerçek tahmin gücünü ispatlamaz.

Metrik anlamları: MAE ortalama mutlak hata, RMSE büyük hataları daha fazla cezalandıran karekök ortalama kare hata, R² baseline'a göre açıklanan varyans; baseline MAE her kayıtta eğitim hedef ortalamasını tahmin eder. Karşılaştırma ayrıntıları `reports/model_comparison.json` ve `reports/model_validation.md` içindedir. Yapısal denetim `reports/data_quality_report.md`, endpoint test listesi/çıktısı `reports/api_test_report.md` içindedir.

## Gerçek fabrika verisi için gerekli alanlar

Parti kimliği ve zaman damgası; üretim öncesi reçete/girdi planı ve o anda geçerli fiyat/tarife snapshot'ı; planlanan kayıp varsayımı ile gerçekleşmiş kayıp ölçümlerinin ayrı değer/zamanları; net çıktı tartımı; işleme türü; gerçekleşen işçilik saati, elektrik kWh, ambalaj ve tüm maliyet bileşenleri; para birimi ve ölçü birimleri gereklidir. Simüle ve gerçek kayıtları açık gerçeklik bayrağıyla ayırın. Eğitim dışında bırakılan, zamana göre ayrılmış gerçek partilerde dış doğrulama yapılmalı; model önce gölge modda denenmelidir. Modelin zayıf EKP performansı giderilip dış doğrulama tamamlanmadan karar/muhasebe entegrasyonu yapılmamalıdır.

Bilinen riskler: fiyat ve tarife alanlarının parti anındaki kullanılabilirliği kanıtlanmamıştır; simülasyon formülünü öğrenen yüksek skorlar gerçek genelleme değildir; EKP mod karışımına ve maliyet/payda formüllerine bağlıdır; joblib dosyaları yalnızca güvenilir kaynaklardan yüklenmelidir. Bu proje henüz gerçek dış doğrulama içermiyor.

## Veri setinin önemli sınırlaması
İki hedef de mevcut CSV'den öğrenilir:
- `Net_sucuk_ciktisi_kg_simule`
- `EKP_TL_kg`

Özellik listesi üretim öncesinde bilinebilecek girdilerle sınırlanmıştır; çıktı veya maliyet toplamları doğrudan girdi yapılmaz. Yine de sentetik verideki formüller/model varsayımları test skorlarını olduğundan iyi gösterebilir. Gerçek üretim kayıtları gelince bağımsız doğrulama şarttır.

## Güvenlik ve canlıya geçiş
- Gerçek API anahtarını Git'e koymayın; `.env` dosyasını paylaşmayın.
- `API_KEY` yalnızca basit servis korumasıdır; canlı ortamda TLS, gizli anahtar yönetimi, erişim kontrolü, loglama ve hız sınırı gerekir.
- ML servisi maliyet/üretim tahmini verir. Stok, muhasebe, lot bağlantısı, satış engeli ve geri çağırma işlemleri deterministik backend kuralları ve merkezi veritabanı ile yönetilmelidir.

## Model 2 — karkas parçalama prototipi

Model 2 görev paketi [Model2/README.md](Model2/README.md) altında tutulur. Ham kaynak CSV'sindeki 1.200 bireysel satır **sentetik/simüledir**; `published_aggregate` yayın/site özetleri bireysel kayıt değildir. Model2 eğitim ve kaynak metodolojisi `Model2/docs/EGITIM_API_SAHA_DOGRULAMA.md` ve `Model2/docs/KAYNAKLAR_LISANSLAR.md` içinde açıklanır.

Repo kökünden Model B adayını çalıştırma komutu:

```powershell
python -m Model2.training.train_model_b
```

Model B için API'ye eklenen `POST /v1/predict/carcass-cuts` endpoint'i yalnızca saha verisiyle doğrulanmış `model_b_production.joblib` ve eşleşen manifesti kabul eder. Bu pakette böyle bir üretim artefaktı yoktur; sentetik aday servis edilmez, endpoint anlaşılır `503` döndürür. `POST /v1/actual/carcass-cuts` daha sonra ölçülen sonuçları prediction ID ile ayrı SQLite migration tablolarına kaydeder; `GET /v1/evaluate/carcass-cuts/{prediction_id}` kayıtlı tahmini ve gerçekleşeni karşılaştırır. Ana backend'de daha önce DB yoktu; Model2 için ayrı SQLite audit migration eklendi. Model2 test/kalite raporları `Model2/reports/` altındadır.
## EKP araştırma karşılaştırması — 24.10.2026

Aynı sentetik veri üzerinde 5 katlı, sabit tohumlu çapraz doğrulama ile Dummy mean/median, RandomForest, log-target RandomForest, ExtraTrees, HistGradientBoosting, GradientBoosting-Huber, Ridge, HuberRegressor, formül özelliği eklenmiş GradientBoosting ve maliyet/net çıktı-hibrit yaklaşımları karşılaştırıldı. Ön işleme her fold içinde yalnız eğitim bölümüne fit edildi.

| Model | CV MAE (TL/kg) | CV RMSE (TL/kg) | CV R² |
|---|---:|---:|---:|
| Mevcut RF | 49,9314 ± 3,1800 | 61,2698 ± 4,4614 | 0,1240 ± 0,0469 |
| Huber GradientBoosting + doğrulanmış alt toplam özellikleri | 48,9869 ± 2,8174 | 60,5653 ± 3,7470 | 0,1436 ± 0,0313 |
| Medyan baseline | 52,1642 ± 3,6097 | 67,1315 ± 3,0199 | -0,0535 ± 0,0319 |

Araştırma adayının CV'de mevcut RF'ye göre MAE'si %1,89, RMSE'si %1,15 daha düşüktür; R² 0,0196 artmıştır. Daha önce tekrar tekrar kullanılmış sabit holdout'ta yeni aday MAE 48,8140 / RMSE 61,1269 / R² 0,1098; mevcut üretim artefaktı MAE 49,8723 / RMSE 61,2236 / R² 0,1070 verdi. Holdout farkı çok küçük ve bağımsız doğrulama değildir.

Araştırma adayı yalnızca 800 satırlık eğitim bölümünde fit edilerek models/candidates/ekp_gradient_boosting_huber_engineered_20261024.joblib dosyasına kaydedildi. production_ready=false; API bunu kullanmaz. Mevcut models/ekp_model.joblib korunmuştur. Aday araştırma betiğini Model1 dizininde şu komutla tekrarlayın:

    python -c "from training.compare_ekp_models import main; main()"

Tahmini maliyet / tahmini net çıktı ve hibrit maliyet/net çıktı yaklaşımları bu sentetik holdout'ta medyan baseline'dan daha kötü kaldı. Veri satırlarının tamamı simüle; bu iyileştirmeler fabrika performansını kanıtlamaz. Tam CV, holdout ve formül sonuçları reports/ekp_improvement_report.md ile reports/ekp_improvement_comparison.json dosyalarındadır.

## Gerçek parti verisi: şablon, doğrulama ve kronolojik değerlendirme

Bu proje içinde doğrulanmış gerçek fabrika partisi bulunmuyor. Mevcut 1.000 satırlık eğitim CSV'si sentetik/simüledir. Gerçek veri gelene kadar zaman bazlı değerlendirme raporu no_real_data kalmalı; sentetik satırlarla bu boşluk doldurulmaz.

Boş, örnek satır içermeyen dosyaları yeniden üretmek için Model1 kökünde şu komutu çalıştırın: python -m training.create_production_data_template

Oluşan dosyalar:

- data/templates/real_production_batches_template.csv
- data/templates/real_production_batches_template.xlsx (Instructions, Production_Batches, Data_Dictionary sayfaları)
- reports/production_data_dictionary.md

İçe aktarma için şablonun kopyasını ayrı bir kaynak dosyası olarak oluşturun; var olan sentetik CSV'nin üstüne yazmayın:

    Copy-Item data\templates\real_production_batches_template.csv data\raw\real_production_batches.csv -NoClobber

Boş/ölçülmemiş alanı boş bırakın. Gerçek satırlarda source_type=real, kaynak sistemi ve referansı, benzersiz batch ID, timezone içeren üretim/ölçüm zamanları, currency=TRY, cost_period=per_batch, ölçülmüş net_output_kg, pozitif çıktı ve kapatılmış total_cost_tl gerekir. Kronolojik değerlendirme için ayrıca validation_status=validated, record_created_at, validated_at, plan_snapshot_at ve 18 Model1 Scenario A plan girdisinin tamamı gerekir. Onay zamanını hedef ölçümünden önce yazmayın. Bu kayıtlar veri sahibi tarafından doğrulanmadan validated seçilmemelidir.

Birimler sütun adlarında kanoniktir: miktarlar kg, kılıf metre, işçilik saat, enerji kWh, bütün parti maliyetleri TRY/batch, EKP TRY/kg. Döviz veya kg/g dönüşümü örtük yapılmaz. Aylık/genel dönem maliyetini parti maliyetine çevirmek için bu araçta tahsis kuralı yoktur; doğrulanmış muhasebe politikası olmadan girilmemelidir. On maliyet alanı ayrık bileşenlerdir; fason hizmeti ve kurum içi işleme ayrı tutulur, aynı fatura tutarını iki kez yazmayın. Tam maliyet dökümünde cost_breakdown_complete=true ve tüm alanlarda tutar (yoksa 0) gerekir. Toplam ile bileşenler arasındaki tolerans, TRY kuruş yuvarlamasının alan sayısıyla birikimini yansıtır.

Net kütle dengesi yalnız losses_complete=true, bütün üç kayıp kg ölçümü, kayıp ölçüm zamanı/yöntemi ve giriş/net kütle mevcutsa denetlenir. Karşılaştırma toleransı girilen kaynak hassasiyetinden hesaplanır; gerçek tartı çözünürlüğü ve hangi proses aşamalarının kütle sınırına dahil olduğu tesis sorumlusu tarafından onaylanmalıdır. Kayıp yüzdelerinin paydası açık değilse bunlar yalnız tanısal alandır. Ölçüm zamanı bilinmeyen veya üretimden sonra ölçülen kayıplar Scenario A model girdilerine hiçbir şekilde girmez.

Veri kalitesi/formül denetimi: python -m pytest -v tests\test_production_data.py

Gerçek veri dosyası doldurulduktan sonra: python -m training.validate_ekp_chronological --input data\raw\real_production_batches.csv

Değerlendirici sentetik veya benchmark satırları gerçek satırlarla karıştırmayı reddeder; satır hatalarını silmez. Genişleyen üç zaman penceresi kullanır; varsayılan pencere başına en az 50 geçmiş batch ve 20 farklı test üretim zaman damgası ister. Eğitim batch'lerinin hedefi test penceresi başlamadan kaydedilmiş ve onaylanmış olmalıdır. Veri bu eşiği karşılamazsa metrik üretmeden nedenini raporlar.

Karşılaştırılan yollar:

1. Doğrudan EKP: Random Forest, Huber kayıplı GradientBoosting araştırma mimarisi, sabitlenmiş mevcut EKP artefaktı ve sentetik aday; test partileri ortak tutulur.
2. Ayrı maliyet ve net çıktı tahminleri: her iki alt model yalnızca geçmiş eğitim penceresinde fit edilir; test tahmini tahmini toplam maliyet / tahmini net çıktı olur.
3. Hibrit: plan girdilerinden et, kuyruk yağı, baharat, kılıf ve Fason ise fason ücretinin bilinen alt toplamı hesaplanır; kalan maliyet residual'ı ve net çıktı geçmiş veride tahmin edilir. Bu maliyet alt toplamının gerçek faturalama kapsamıyla aynı olduğu tesis muhasebesince doğrulanmalıdır.

Gerçek kayıt olmadığı için bu üç yol için yeni gerçek fabrika metriği yoktur. Önceki sentetik CV/holdout metrikleri ayrı raporlarda kalır ve gerçek performans gibi sunulmaz. Mevcut production RF ve sentetik aday artefaktları üzerine yazılmaz; frozen ağırlıklar kronolojik raporda yalnız kayıtlı SHA-256 değerleriyle eşleşirse teşhis amaçlı test edilir. Hash dosya bayt bütünlüğünü kontrol eder; imza, kaynak kimliği, güvenilir eğitim veya bilimsel geçerlilik kanıtı değildir. Beklenen hash değişirse artefakt açılmaz.

### Veri senaryoları ve kullanım kararı

- Senaryo A — üretim öncesi tahmin: yalnız frozen plan snapshot'ındaki planned_* alanları. Net çıktı, gerçekleşen maliyet, gerçekleşen işçilik/enerji tüketimi ve gerçekleşen kayıplar özellik değildir. Her fiyat ve tarifenin gerçekten plan anında erişilebilir olduğu saha kaydıyla doğrulanmalıdır.
- Senaryo B — ölçülmüş kayıplarla koşullu hesaplama: kayıp ölçüm zamanı ve yöntemi biliniyorsa, ölçülen kütle dengesi / sonradan yapılan EKP hesaplaması için kullanılabilir. Üretim bittikten sonra ölçüldüyse bu üretim öncesi tahmin değildir. Bu projede Scenario B API tahmin özelliği değildir.
- Mevcut EKP Random Forest ve GradientBoosting adayı: yalnız sentetik geliştirme/araştırma karşılaştırması. EKP modeli gerçek veride zaman bazlı doğrulanmadı ve üretime hazır değildir.
- Formül EKP: ölçülmüş, TRY cinsinden kapanmış toplam batch maliyeti ve pozitif ölçülmüş net kg varsa gerçekleşen EKP'yi deterministik olarak hesaplar; bu model tahmini değildir.



## EKP comparison refresh — 2026-10-24

The current run uses a date-grouped research split because the synthetic CSV has a generated Tarih_simulasyon field. Run from this directory with:

    python -m training.report_ekp_data_quality
    python -m training.compare_ekp_models_chronological
    python -m pytest -v

The quality report is reports/ekp_data_quality_report.md. The new experiment writes reports/ekp_model_comparison.md, reports/ekp_model_comparison.csv, and reports/ekp_model_comparison.json. It holds out whole trailing dates and performs five expanding-window folds only within the earlier training dates. Imputation, scaling, and category encoding are fitted inside each fold. Fixed estimator settings are used; the final holdout is not used to select models.

All 1,000 rows are synthetic/simulated. The 789 earlier rows (2026-09-01 through 2026-10-11) train the models, and the last 211 rows (2026-10-12 through 2026-10-22) form a grouped holdout. Those dates are simulation metadata, not verified factory chronology. The training-only CV MAE leader was HuberRegressor: 48.4457 ± 2.6859 TL/kg, RMSE 60.9184 ± 2.3710 TL/kg, R² 0.1152 ± 0.0652. Its held-out metrics were MAE 52.6041 TL/kg, RMSE 66.2836 TL/kg, and R² 0.1075. The training-median holdout baseline was MAE 56.0123, RMSE 71.7718, R² -0.0464. The engineered Huber GradientBoosting had the lowest holdout MAE (51.5420 TL/kg), but it was not selected because the experiment ranks architectures on training-only CV, not the holdout. No candidate was saved or promoted.

The predicted-total-cost / predicted-net-output RF approach scored MAE 60.5867 TL/kg and R² -0.1399 on the holdout, worse than the training-median baseline. The hybrid planned-cost/residual approach scored MAE 57.6474 and R² -0.0288; it also did not beat the median baseline on MAE. Neither approach is supported for use. The prior shuffled-split RF result (MAE 49.8723, RMSE 61.2236, R² 0.1070) is retained as historical and is not directly comparable with the newer date-grouped evaluation.

Scenario A's 18 input, category, price and tariff fields are candidate preproduction features only; this synthetic data has no immutable plan or quote snapshots proving their availability. Scenario B adds Kuruma_kaybi_pct and Ayiklama_fire_pct, which the workbook describes as simulated, not measured loss records. Their real measurement time is unknown, so Scenario B is not a preproduction candidate. EKP itself is total batch cost (TRY) divided by measured net output (kg), but the current dataset's costs and output are simulated and the ratio is a constructed target.

Production artifact SHA-256 values recorded before evaluation:

- models/ekp_model.joblib: aae0a3538e0c57dff7fc12bc8d20961f4802644b2f4a4cde40eb49d375e9b802
- models/yield_model.joblib: 0ef1990770c1ad2a8a9deb57f356559b9165a19d65f9155c58bb4f9db4b46bca

The new comparison did not deserialize or alter model artifacts. Existing shuffled split artifacts have no proven row/date membership, so they were not scored as unseen-date results.

The requested Swedish Meats process-inventory CSV files were not found in the searched local locations and were not reconstructed. Source metadata, flow values, scope and limitations are documented in reports/ekp_external_benchmark_note.md. The existing ekp_published_cost_structure_benchmark.csv is a separate historical aggregate cost-share benchmark, not those inventory files.

Decision: EKP remains research-only and is not ready for production. Before evaluation with a real plant, record immutable pre-run recipe, input quantities, supplier quotes/tariffs and process plan; unique batch ID; production timestamps; measured net kg and loss timestamps/methods; closed TRY batch cost with disjoint component reconciliation; source/provenance references; and validation/availability timestamps. Evaluate all candidates against a median baseline on untouched chronological plant data, then independently validate across a later period or site.


Final regression run on 2026-10-24: .venv\Scripts\python.exe -m pytest -v completed with 83 passed, 0 failed, and 1 StarletteDeprecationWarning from the installed FastAPI/Starlette/httpx TestClient stack. This is the project virtual environment equivalent of python -m pytest -v. No dependency was changed.
