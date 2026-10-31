# Model 2 — Kapsamlı Teknik İnceleme ve Eksiklik Analizi

**Tarih:** 2026-10-25
**Kapsam:** ai/Model2 ve yalnızca Model2 entegrasyonunu anlamak için gerekli bağlantılı dosyalar
**Yöntem:** Salt okunur kaynak, yapılandırma, belge, CSV/XLSX ve metrik incelemesi

## 1. Yönetici özeti

Model 2, hayvan türü ve karkas ağırlığından sekiz kg hedefi tahmin etmek üzere tasarlanmış sentetik bir prototiptir. Kaynak kodda Ridge ve Random Forest adayları, tür bazlı ortalama oran baseline’ı, Model2’ye ait FastAPI girişi ve ayrı Docker Compose yapılandırması bulunur. Compose statik doğrulaması geçti; ancak Docker daemon’a erişim reddedildiğinden çalışan container ve 8002 gerçek port eşlemesi doğrulanamadı.

1.200 satırın tamamı sentetik/simüledir; bireysel measured veri yoktur. Yayımlanmış dana/kuzu kaynakları toplu özet düzeyindedir. Test raporları sentetik holdout n=180 için Ridge MAE 1,8439 kg, RMSE 3,4556 kg, uniform-average R² 0,9022 verir. R² doğruluk yüzdesi değildir. Aynı holdoutta baseline Ridge’den daha iyidir (MAE 1,8283 kg; RMSE 3,4431 kg). Seçim kodu baseline’ı final aday havuzuna almamaktadır.

API mevcut sentetik adayı production tahmini için yüklemez. Measured ve production_ready=true bundle bulunmazsa tahmin endpoint’i 503 verir; bu bilinçli ve doğru bir fail-closed davranıştır. Üretim hazırlığı yoktur: gerçek saha verisi/doğrulaması, hedef tanımları ve kategori sınırları eksiktir. Model artefaktı ve Docker süreci üretim iddiasında bulunmamalıdır.

**Bulgu sayıları:** Kritik 0, Yüksek 3, Orta 7, Düşük 2.

## 2. İncelemenin kapsamı ve sınırları

- ai/Model2 altında 58 dosya envanterlendi. API, eğitim, test, Docker, SQL, veri, kaynak belgeleri, saha şablonları, raporlar, üç Excel çalışma kitabı ve manifest incelendi. CSV istatistikleri salt okunur hesaplandı; Excel dosyaları read-only kipinde açıldı.
- .joblib dosyası pickle içeriği çalıştırmamak için deserialize edilmedi. Aday manifesti okundu; manifest SHA-256 değeri dosyanın yerel hash’iyle eşleşti.
- Bu denetimde eğitim, yeni değerlendirme/model üretimi, test paketi, HTTP/API isteği, veri yazımı, container build/start/stop veya bağımlılık kurulumu yapılmadı.
- Önceki bu oturumdaki Model2 bağımsız API test çıktısı 10 passed ve bir Starlette/httpx deprecation uyarısı gösteriyordu. Bu turda testler yeniden çalıştırılmadı. Diskteki api_test_report.md ayrıca 43’lük paket testi ve 28 legacy Model B API testini bildirir; bunu Model2 bağımsız testlerinin yeni çalıştırması olarak saymadım.
- docker compose config --quiet, gerçek anahtar değeri olmadan geçici audit-placeholder-only değerle geçti. docker ps Docker Desktop Linux engine named pipe erişim reddi verdi; canlı docker inspect yapılamadı.
- Başlangıç git status: feature/ai-models-development dalı; backend/tests/test_traceability_recall.py önceden değiştirilmiş; ai/.dockerignore, ai/.gitignore ve ai/Model2 önceden izlenmeyen. Başlangıç git diff --check çıktı vermedi. Bu dosyalara dokunulmadı.
- API anahtarı/parola/token değeri rapora yazılmadı.

## 3. İncelenen dosyalar

58 dosyalık envanterin önemli bölümleri:

- API: app/main.py, schemas.py, config.py, model_b_artifact.py, model_b_audit.py; sql/001_model_b_audit.sql; tests/test_api.py.
- Docker: Dockerfile, docker-compose.yml, requirements.txt, .gitignore.
- Eğitim/artefakt: training/train_model_b.py, training/ModelB_egitim_kodu.py, ModelB_EgitimPaketi.xlsx; models/model_b_synthetic_candidate.manifest.json ve .joblib.
- Veri: raw sentetik CSV/XLSX; train, validation, test ve birleşik split CSV’leri; published_aggregate dana/kuzu CSV/XLSX; boş measured dizini.
- Mevcut raporlar: istenen beş test raporunun tümü mevcut; aday metrikleri, data_quality_report.md, comprehensive_audit.md, api_test_report.md, competition_report.md.
- Doküman/şablon: README.md, docs/ içindeki beş metodoloji/kaynak/API notu; saha CSV şablonları ve GERCEK_SAHA_VERISI_KILAVUZU.md.

## 4. Mevcut mimari ve tahmin akışı

1. Eğitim, önceden oluşturulmuş ModelB train/validation/test CSV’lerini okur; girdiler hayvan_turu ve karkas_agirligi_kg, hedefler sekiz kg alanıdır (training/train_model_b.py:23-42).
2. Tür ortalama oran baseline’ı, Ridge(alpha=1.0) ve 300 ağaçlı RF train üzerinde fit edilir. Ridge/RF validation’da kıyaslanır; test seçimden sonra raporlanır (training/train_model_b.py:86-121, 156-187).
3. Aday model model_b_synthetic_candidate.joblib adıyla ve source_type=synthetic, production_ready=false metadata’sıyla saklanır (training/train_model_b.py:188-217).
4. Model2 API app.main:app olarak çalışır. /health liveness, /v1/models/status aday ve üretim durumunu bildirir. /v1/predict/carcass-cuts yalnız doğrulanmış measured/ready production artefaktı yükler; yoksa 503 verir (app/main.py:72-109; app/model_b_artifact.py:73-126).
5. Başarılı prediction SQLite’a yazılır; actual ölçümü ayrı POST, kayıtlı karşılaştırma ayrı GET endpoint’indedir (app/main.py:124-196; app/model_b_audit.py:56-127).
6. Model2 Dockerfile kendi app/sql kaynaklarını kopyalar ve uvicorn app.main:app başlatır (Dockerfile:1-14). Compose image avatar-model2-api:local, container avatar-model2-api ve 127.0.0.1:8002:8000 portunu tanımlar (docker-compose.yml:1-10).
7. Model1 altında tarihsel Model B route’ları da bulunur (../Model1/app/main.py:155-156, 242-243). Mevcut Model2 Compose statik olarak Model2 uygulamasını başlatacak şekilde ayrıdır. Docker daemon erişimi olmadığından daha önce gözlenen Model1 alanlı yanıtın çalışan süreç kök nedeni bu turda doğrulanamadı.

## 5. Model algoritması analizi

- Ridge kullanımı kodda doğrulanır; sklearn Ridge sekiz hedef sütununu aynı çağrıda döndürür. Bu, tek feature matrisiyle çok hedefli regresyondur; hedefler arasında fiziksel bağ kısıtı kurmaz (training/train_model_b.py:27-33, 103-121).
- Hayvan türü OneHotEncoder(handle_unknown="ignore") ile kodlanır. Ridge hattında karkas kg StandardScaler’dan geçer. RF hattında tür one-hot, ağırlık passthrough’dur. Pipeline yalnız train üzerinde fit edilir (103-121, 156-162).
- Hiperparametreler Ridge alpha=1.0; RF n_estimators=300, min_samples_leaf=3, random_state=20261024, n_jobs=1. Hiperparametre araması yok (32, 103-121).
- Sekiz target ayrıca ölçeklenmez. Aynı Ridge alpha farklı ölçekli hedeflere uygulanır; hedefler arası kütle dengesi veya bağımlılık garantisi oluşmaz.
- Eğitim validasyonu gerekli sütun/kaynak/tür/ID, nonfinite-negatif değer, pozitif karkas, toplam ve split ID kesişimi kontrollerini yapar (43-83). API türü kuzu/koyun/dana, strict float karkas ağırlığını 0 < kg <= 1000 ve extra alanları yasaklar (schemas.py:16-20).
- API model tahmininde shape/finite kontrolü, negatifleri sıfıra kırpma ve 3 ondalık yuvarlama yapar. Üst sınır veya toplam tutarlılığı zorunlu değildir (main.py:112-123).
- Model sürümü, seed ve veri sürümü kısmen kaydedilir; manifestte çalışma zamanı sürümleri, eğitim kod hash’i, generator hash’i ve imza/attestation yoktur. Aday raporu Python 3.12.10/sklearn 1.9.1 verir (model_b_candidate_report.md:3,21), manifestte bu alanlar yer almaz.

## 6. Veri seti kalitesi ve sentetik veri gerçekçiliği

### 6.1 Kaynak ve ağırlık dağılımı

Ham CSV’de 1.200 satırın tamamı SENTETIK; kuzu/koyun/dana başına 400 kayıt vardır. Ham tabloda yas_ay ve yag_durum_skoru sütunları her satırda boş (2.400 eksik hücre); irk/cinsiyet “bilinmiyor” metnidir. Bu alanlar model feature’ı değildir. Yinelenen ID/tam satır ve negatif hedef görülmedi.

| Tür | n | Min kg | Medyan kg | Ortalama kg | Std. sapma kg | Maks kg |
|---|---:|---:|---:|---:|---:|---:|
| Kuzu | 400 | 10,47 | 19,215 | 19,388 | 3,677 | 27,78 |
| Koyun | 400 | 18,77 | 30,025 | 29,863 | 4,852 | 41,68 |
| Dana | 400 | 190,10 | 272,315 | 269,957 | 37,353 | 358,63 |

Birleşik karkas ağırlığı ortalaması 106,4027 kg, medyanı 30,025 kg, std. sapması 117,818 kg’dır; türler arası ölçek farkı bu özeti tek tür açısından temsilî olmaktan çıkarır.

### 6.2 Hedef dağılımları

Ham sentetik CSV’den hesaplandı; std. sapma örnek std. sapmasıdır.

| Hedef | Min | Medyan | Ortalama | Std. sapma | Maks (kg) |
|---|---:|---:|---:|---:|---:|
| but_kg | 1,848 | 6,0695 | 20,0309 | 22,1501 | 98,360 |
| sirt_kg | 1,030 | 3,3040 | 12,2880 | 14,0753 | 56,689 |
| omuz_kg | 1,002 | 4,3745 | 13,2109 | 14,2178 | 62,907 |
| kaburga_kg | 1,184 | 4,8810 | 15,7614 | 17,2556 | 69,880 |
| kiyma_kg | 1,827 | 6,1170 | 30,5080 | 36,9122 | 130,371 |
| yan_urun_kg | 0,615 | 3,1170 | 8,7650 | 9,4145 | 43,361 |
| kemik_yag_sinir_kg | 0,051 | 0,9010 | 2,6360 | 3,2353 | 20,913 |
| fire_kg | 0,084 | 1,0760 | 3,2025 | 3,8194 | 19,401 |

### 6.3 Tür bazlı hedef/karkas oranları

Her satır için hedef kg / karkas kg oranının tür içi ortalaması:

| Tür | But | Sırt | Omuz | Kaburga | Kıyma | Yan ürün | Kemik/yağ/sinir | Fire |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Dana | 0,18519 | 0,11615 | 0,12015 | 0,14521 | 0,30135 | 0,07829 | 0,02430 | 0,02936 |
| Koyun | 0,20151 | 0,11338 | 0,14566 | 0,16537 | 0,20633 | 0,10432 | 0,02938 | 0,03405 |
| Kuzu | 0,20604 | 0,11244 | 0,14654 | 0,16423 | 0,20620 | 0,10408 | 0,02556 | 0,03491 |

Birleşik veride karkas ağırlığı-hedef Pearson korelasyonları 0,8617–0,9913 arasındadır. Bu, gerçek biyolojik ilişki kanıtı değildir; tür ve ağırlık ölçeği sentetik hedeflerle birlikte değişmektedir.

### 6.4 Split, tekrar eden özellik ve üretim kaynağı

Train/validation/test 840/180/180; her split tür başına 280/60/60’tır. Ortalama karkas kg sırasıyla 106,064 / 107,631 / 106,755. ID’ler ayrıdır; ancak tür+ağırlık çifti splitler arasında train-validation 17, train-test 26, validation-test 5 farklı girişte aynıdır. Bu ID disjoint kuralını ihlal etmez ve doğrudan target sızıntısı kanıtı değildir; 0,01 kg’a yuvarlanmış sentetik ağırlıklarda aynı X noktalarının ayrı kayıtlara düşebildiğini gösterir. Gerçek veride hayvan/parti gruplu split yine gerekir.

Train tür ağırlık aralıkları: kuzu 10,47–27,78; koyun 18,77–40,88; dana 190,10–353,10 kg. Validation’da train maksimumunu geçen 2, testte 3 kayıt (testte 2 koyun, 1 dana) vardır. Farklar yakındır. Buna rağmen API’nin 1000 kg kabulü eğitim desteğinden çok dışarı çıkar.

Model2’de sentetik satırları üreten generator/formül kodu bulunmadı. Eğitim yalnız mevcut split CSV’lerini okur (train_model_b.py:36-42). Sentetik kullanım notu kuzu/koyun oranlarının varsayımsal olduğunu bildirir (docs/SENTETIK_VERI_KULLANIM_NOTU.md:8-15). Ağırlık örnekleme dağılımı, hedef oran parametreleri, gürültü dağılımı ve split script’i kaynakla yeniden üretilemedi. Bunlar veriden tersine tahmin edilmedi.

Yayımlanmış kaynak Excel’inde dana için 8, kuzu için 3 özet kategori satırı vardır; bireysel karkas ölçümü değildir ve eğitime katılmadığı dokümanla uyumludur (docs/KAYNAKLAR_LISANSLAR.md:7-19; reports/data_quality_report.md:33-35). measured klasörü boş hedef dizindir.

## 7. Eğitim ve değerlendirme metodolojisi

- Eğitim mevcut splitleri okur, split üretmez (train_model_b.py:36-42). Seed 20261024 dokümanda belirtilse de split generator’ı kodda yoktur.
- Kod kaynak, bölüm, tür, ID, finite/nonnegative ağırlık, pozitif karkas, toplam ve ID kümelerinin ayrıklığını kontrol eder (43-83).
- Baseline yalnız train’den öğrenilir. Validation’da Ridge/RF baseline’a normalize MAE oranı ile kıyaslanır; test seçimden sonra raporlanır (86-100, 143-187). Testin seçimde kullanıldığına dair kanıt yoktur.
- Seçim tuple’ı yalnız Ridge/RF içerir (167-170). Baseline aday olamaz. Testte baseline üstün olsa bile test sonucuyla sonradan model seçilmemeli; baseline validation seçim havuzuna girmelidir.
- Hedef bazlı genel MAE/RMSE/R² raporlanır. Tür, karkas ağırlık bandı, signed bias, belirsizlik, kalibrasyon veya tahmin aralığı yoktur.
- Flattened kg MAE/RMSE büyük ölçekli hedefleri daha fazla ağırlıklandırabilir. Türler arası ölçek farkı varken hedef bazlı/normalize özet de sunulmalıdır.
- n=180 sentetik test prototip karşılaştırması içindir; gerçek popülasyona genelleme ölçüsü değildir. Aynı giriş çiftlerinin splitler arası tekrarı sonucu yorumlamada ek sınırdır.

## 8. Mevcut test raporlarının doğrulanması

İstenen beş dosyanın tümü vardır: model2_test_raporu.md/json, model2_test_metrikleri.csv, model2_test10_detay.csv, model2_test10_agirlik_dengesi.csv. JSON model sürümünü model-b-ridge-20261024-synthetic-v1, veri sürümünü model-b-synthetic-v1, source_type=synthetic, production_ready=false, n=180 ve sekiz hedef olarak bildirir. Markdown/JSON/CSV metrikleri dört ondalık yuvarlama farkları dışında tutarlıdır.

| Hedef | MAE kg | RMSE kg | R² |
|---|---:|---:|---:|
| but_kg | 2,2415 | 4,0674 | 0,9647 |
| sirt_kg | 1,9175 | 3,4497 | 0,9433 |
| omuz_kg | 1,8232 | 3,1187 | 0,9525 |
| kaburga_kg | 2,4258 | 4,4268 | 0,9342 |
| kiyma_kg | 2,7486 | 4,7508 | 0,9830 |
| yan_urun_kg | 1,6257 | 3,0474 | 0,9090 |
| kemik_yag_sinir_kg | 1,0097 | 1,7939 | 0,7416 |
| fire_kg | 0,9590 | 1,6399 | 0,7891 |

Ridge tam test: MAE 1,8438897 kg, RMSE 3,4556262 kg, uniform-average R² 0,9021658. Mutlak hata ≤1 kg oranı %63,06; ≤2 kg oranı %75,49. Bunlar tolerans oranı, doğruluk yüzdesi değil. R² açıklanan varyans temelli regresyon metriğidir.

| Model | MAE kg | RMSE kg | Uniform-average R² |
|---|---:|---:|---:|
| Tür oran baseline | 1,8282865 | 3,4430830 | 0,9027437 |
| Ridge | 1,8438897 | 3,4556262 | 0,9021658 |
| Random Forest | 1,9411794 | 3,6899990 | 0,8941909 |

Ridge’in MAE’si baseline’dan 0,0156032 kg (%0,85), RF’ninki 0,1128928 kg (%6,17) daha yüksektir. Sonuçlar yalnız sentetik holdout içindir. Kaynaklar: model_b_candidate_report.md:3-15, ModelB_sentetik_model_degerlendirme.csv:1-4 ve model_b_candidate_metrics.json overall_test_metrics.

Excel tutarlılık farkı: training/ModelB_EgitimPaketi.xlsx içindeki Model_Metrikleri sayfası yalnız baseline ve RF içerir. Baseline MAE/RMSE/R² değerleri 1,8289718 / 3,4451555 / 0,9026320; güncel CSV/JSON ise 1,8282865 / 3,4430830 / 0,9027437 verir. Workbook’ta Ridge satırı ve koşu/hash bilgisi yoktur; güncel raporla aynı koşu olduğu kanıtlanamaz.

## 9. On örnek ve hata analizi

model2_test10_detay.csv 10 kayıt × 8 hedef = 80 hata değeri içerir. 10 kayıt genel MAE’si, hedef MAE ortalamasıyla 2,2864 kg’dır. Tür dağılımı 4 dana, 5 koyun, 1 kuzu; 10’lu alt küme dengeli değildir.

En büyük mutlak hata 13,946 kg: SYN-DANA-0324, 270,20 kg karkasta sirt_kg düşük tahmini. Sonraki büyük hatalar SYN-DANA-0325 kiyma_kg için 11,117 kg düşük ve SYN-DANA-0324 kaburga_kg için 10,728 kg yüksek.

| Tür | Hayvan | Hedef hücresi | 10 örnek MAE kg | Maks. mutlak hata kg |
|---|---:|---:|---:|---:|
| Dana | 4 | 32 | 4,840 | 13,946 |
| Koyun | 5 | 40 | 0,621 | 2,599 |
| Kuzu | 1 | 8 | 0,399 | 0,738 |

Hedef bazlı fazla/düşük hata yönü karışıktır; 10 örnekten popülasyon sapması çıkarılamaz. Dana örneklerinin kg hataları daha büyüktür, ancak tür ve ağırlık etkisi ayrıştırılmamıştır. Kaynaklar model2_test10_detay.csv sütunları ve model2_test_raporu.md:22-117.

## 10. Ağırlık dengesi ve fiziksel tutarlılık

Sentetik hedeflerin toplamı giriş karkas ağırlığına eşit olacak biçimde kurulmuştur. Kod toplam_cikis_kg ve agirlik_dengesi_farki_kg iç tutarlılığını denetler (train_model_b.py:66-73). Bu gerçek tartım dengesi kanıtı değildir.

On tahmin örneği için tahmin toplamı−karkas farkı: ortalama signed −0,0762 kg, ortalama mutlak 0,1804 kg, maksimum mutlak 0,9604 kg (SYN-DANA-0265, tahmin toplamı 299,3396 kg, karkas 300,30 kg). 4 örnek fazla, 6 örnek düşük; 5/10 örnek farkı mutlak 0,1 kg veya daha az. Rapor kategori örtüşmesi belirsiz olduğu için toplam kapanışını garanti etmez (model2_test_raporu.md:121-137).

But, sırt, omuz, kaburga, kıyma, yan ürün, kemik/yağ/sinir ve fire’nin belirli bir standartta birbirini dışlayan ve aynı aşamada ölçülen kategoriler olduğu doğrulanamadı. Kıyma trim olabilir; yan ürün/kemik/yağ/sinir kapsamı işletme tanımı ister. Toplam eşitliği varsayımı otomatik uygulanmamalı. Önce kategori sınırları, karkas sıcak/soğuk tanımı ve fire aşaması kararlaştırılmalı; ancak kategoriler tam ve ayrık ise denge toleransı belirlenmelidir.

## 11. API ve güvenlik incelemesi

### 11.1 Endpoint ve şema

FastAPI başlığı AVATAR Model 2 Carcass Cuts API’dir (app/main.py:44-48).

| Endpoint | Sözleşme ve davranış |
|---|---|
| GET /health | Auth yok; status ok ve service avatar-model2-api döndürür. Liveness’tır, model readiness değildir (main.py:72-75). |
| GET /v1/models/status | Auth yok; production manifest ve sentetik candidate var/hash/şema durumunu, model sürümünü, iki feature ve sekiz target adını döndürür. Modeli unpickle etmez (main.py:78-96; schemas.py:34-47). |
| POST /v1/predict/carcass-cuts | Girdi hayvan_turu kuzu/koyun/dana ve strict float karkas_agirligi_kg 0<kg≤1000; extra alan yasak. Örnek JSON: {"hayvan_turu":"kuzu","karkas_agirligi_kg":18.2}. API key gerekirse x-api-key header kullanılır. Measured production artifact yoksa 503; varsa predicted_cuts_kg sekiz hedefi, prediction ID/zamanı ve model/veri sürümlerini içerir (schemas.py:9-31; main.py:99-147). |
| POST /v1/actual/carcass-cuts | Prediction ID, sekiz hedefi içeren sonlu/sayısal/nonnegative actual_cuts_kg ve timezone’lı measured_at_utc ister; route tüm target key’lerini doğrular. DB’ye yazar (schemas.py:50-75; main.py:149-176). Denetimde çağrılmadı. |
| GET /v1/evaluate/carcass-cuts/{prediction_id} | Auth sonrası tahmin/actual karşılaştırır; fark tahmin−gerçekleşen. Kayıt yoksa 404, actual yoksa 409 (main.py:179-196). |

### 11.2 Güvenlik ve artefakt

- API_KEY varsa secrets.compare_digest ile kontrol edilir; eksik/yanlış anahtar 401. development/dev/test dışında anahtar yoksa fail-closed 503 (main.py:60-70). Compose APP_ENV=production ve zorunlu API_KEY ister (docker-compose.yml:18-24). Anahtar değeri rapora konmadı.
- Validation hata cevabından input ve ctx ayıklanır; DB/artefakt hata cevapları genel mesajdır (main.py:51-57, 141-146).
- Loader kaynak türü, production_ready, tam feature/target sırası, sürüm ve 64-hex SHA-256 doğrular; joblib’den önce hash kontrolü ve aynı açık handle’dan tekrar hash/load yapar (model_b_artifact.py:35-70, 73-126).
- Sentetik candidate status’ta hash/şema kontrolü görebilir, ama deserialize edilmez; production loader yalnız measured ve ready bundle’ı kabul eder (model_b_artifact.py:73-124). Bu, sentetik modelin 503 ile reddedilmesini bilinçli kılar.
- SHA-256 byte bütünlüğüdür, kimlik doğrulama değildir. Aynı güvenilmeyen yazma kanalından manifest ve model beraber değiştirilebiliyorsa hash tek başına kötücül modeli engellemez; imza/attestation veya ayrı korunan yetkili kanal gerekir.
- .gitignore audit DB ve measured veriyi Git dışında tutar (1-10). API gelen ölçümün gerçekten tartıldığını doğrulayamaz.

### 11.3 Docker

- Statik Compose service model2-api, image avatar-model2-api:local, container avatar-model2-api, host 127.0.0.1:8002 → container 8000, build context ai ve Dockerfile Model2/Dockerfile kullanır (docker-compose.yml:1-10).
- Uygulama FS read-only, /tmp tmpfs, model mount read-only, audit DB ayrı named volume, no-new-privileges ve cap_drop ALL etkin (11-40).
- Healthcheck yalnız /health liveness endpoint’ini çağırır (28-37). Model yokken container healthy/liveness 200 olabilir; status hazır değil ve prediction 503 kalır.
- Engine erişimi reddedildiğinden çalışan container adı/image digest/port mapping/health/volume/env doğrulanamadı. Tarihsel Model1 alanlı yanıtın aktif container kök nedeni belirlenemedi. Statik Compose config geçti; bu build/start/inspect başarısı değildir.
- Dockerfile’da USER yok; varsayılan kullanıcı root olabilir. Requirements ve python:3.12-slim tag’i tam digest/lock ile sabitlenmemiştir (Dockerfile:1-8; requirements.txt:1-6). Compose’un diğer sertleştirmeleri riski azaltır.

## 12. Test kapsamı ve yazılım kalitesi

tests/test_api.py 7 test fonksiyonu, parametrik dört input ile toplam 10 case içerir (55-180).

| Kapsam | Durum | Kaynak |
|---|---|---|
| Health/status Model2’ye özgü; legacy alanlar yok | Var | 55-77 |
| Production artifact yokken prediction 503 | Var | 80-90 |
| API key eksik | Var | 92-99 |
| Geçersiz tür, negatif kg, extra alan, eksik kg | Var | 101-118 |
| Hash uyuşmazlığında deserialize öncesi ret | Var | 120-131 |
| Sentetik bundle production adıyla da reddedilir | Var | 133-144 |
| Fixture ile prediction→actual→evaluation | Var | 146-180 |
| Sıfır, 1000 üstü, out-of-training-range, yanlış tip/Infinity | Test yok | Şema kuralları var, sınır testleri eksik |
| Negatif model çıktısı, bozuk shape/NaN, kütle dengesi | Test yok | Route kontrolü statik |
| Eksik/bozuk manifest, sürüm uyuşmazlığı, DB hata durumu | Bu Model2 dosyasında test yok | Loader statik incelendi |
| Eğitim split validator birim testi | Test yok | Kodda validator mevcut |

Dosyada test olması çalıştırma kanıtı değildir. Önceki oturum test çıktısında Model2 için 10 passed kaydı vardır; bu turda tekrar edilmedi. api_test_report.md’deki 43/28 sonuçları ayrı, legacy Model1 bağlantılı koşular olarak ayrıştırıldı. Docker testleri bu turda çalıştırılamadı.

## 13. Önem derecesine göre bulgu listesi

### F-01 — Bireysel gerçek ölçüm/doğrulama verisi yok
**Önem:** Yüksek. **Kanıt:** docs/KAYNAKLAR_LISANSLAR.md:3-19; data/raw/measured/.gitkeep; reports/data_quality_report.md:3-10.
**Davranış/neden ve etki:** 1.200 satırın tümü sentetik; yayın özetleri bireysel hayvan değildir. Gerçek başarı/genelleme iddiası mümkün değildir.
**Güven:** Yüksek. **Öneri:** İzinli, anonim, hayvan/parti düzeyinde ölçüm ve tartım/kategori metadata’sı toplayın.
**Başarı ölçütü:** Her hedef/tür için bağımsız gerçek holdout n, MAE/RMSE/bias ve baseline karşılaştırması; grup ID ayrımı doğrulanmış.

### F-02 — Hedef kategori sınırları/örtüşmeleri belirsiz
**Önem:** Yüksek. **Kanıt:** README amaç bölümü; docs/SENTETIK_VERI_KULLANIM_NOTU.md:24-34; reports/data_quality_report.md:27-31; train_model_b.py:66-73.
**Davranış/neden ve etki:** Sentetik hedef toplamı karkasa kapanıyor; gerçek kesim standardı, trim/kıyma, yan ürün, kemik/yağ/sinir ve fire sınırı onaylı değil. Kütle dengesi fiziksel doğruluk sayılmaz.
**Güven:** Yüksek. **Öneri:** Her hedef için ölçüm aşaması ve dahil/hariç/örtüşme tanımı yazılı onaylansın.
**Başarı ölçütü:** Onaylı veri sözlüğü; aynı standarda göre gerçek ölçümlerde tanımlanmış denge toleransı.

### F-03 — Sentetik veri üretici/formül kaynakta bulunmuyor
**Önem:** Yüksek. **Kanıt:** train_model_b.py:36-42 hazır CSV okur; Model2 inventory’de generator yok; docs/SENTETIK_VERI_KULLANIM_NOTU.md:8-15.
**Davranış/neden ve etki:** Ağırlık dağılımı, oran/gürültü parametreleri ve split üretim kodu yok; veri aynı seed ile yeniden üretilemez, varsayımlar audit edilemez.
**Güven:** Yüksek. **Öneri:** Generator, parametre/seed/schema/source bilgisi ve üretilen dosya hash’leri sürümlensin.
**Başarı ölçütü:** Aynı seed’de geçici dizinde deterministik satır/hash ve generator testleri.

### F-04 — Baseline final aday seçimine alınmıyor
**Önem:** Orta. **Kanıt:** train_model_b.py:143-170; ModelB_sentetik_model_degerlendirme.csv:1-4.
**Davranış/neden ve etki:** Baseline karşılaştırılır, seçim yalnız Ridge/RF’dir; aynı testte baseline MAE 1,8283 ve Ridge 1,8439 kg. ML kazancı gösterilmedi.
**Güven:** Yüksek. **Öneri:** Baseline’ı validation seçim havuzuna alın; test kilidini koruyun.
**Başarı ölçütü:** Önceden belirlenen validation ölçütünde seçilen aday baseline’dan iyi; final test bir kez seçimden sonra raporlanmış.

### F-05 — Aynı giriş çiftleri splitler arasında tekrarlanıyor
**Önem:** Orta. **Kanıt:** train/validation/test CSV’lerinin tür+ağırlık karşılaştırması; 17/26/5 benzersiz ortak çift; data_quality_report.md:8-22 yalnız ID kesişimini bildirir.
**Davranış/neden ve etki:** Farklı ID’ler aynı iki feature değerine sahip; doğrudan target sızıntısı kanıtı yok, ancak bağımsızlık zayıflayabilir.
**Güven:** Orta-yüksek. **Öneri:** Gerçek veride stable animal_id/lot_id ile group split; sentetik tekrarların etkisini ayrıca raporlayın.
**Başarı ölçütü:** Group ID kesişimi sıfır ve tekrar eden özelliklerin raporlanması.

### F-06 — Tür/ağırlık bandı performansı ve tahmin belirsizliği yok
**Önem:** Orta. **Kanıt:** train_model_b.py:125-140; model2_test_metrikleri.csv; tests/test_api.py.
**Davranış/neden ve etki:** Hedef bazlı genel hata var; tür/band bias, kalibrasyon ve aralık yok; büyük ölçekli türler kg toplamını etkileyebilir.
**Güven:** Yüksek. **Öneri:** Gerçek holdout’ta hedef×tür×ağırlık bandı n/MAE/RMSE/bias ve uygun kalibrasyon raporu.
**Başarı ölçütü:** Veri sahibi onaylı asgari n/eşiklerle tüm alt grup sonuçları.

### F-07 — API ağırlık sınırı training desteğinden geniş
**Önem:** Orta. **Kanıt:** schemas.py:16-20; sentetik aralıklar bölüm 6.
**Davranış/neden ve etki:** API 1000 kg’a kadar kabul eder; sentetik maksimum dana 358,63, koyun 41,68, kuzu 27,78 kg’dır. Gelecekte measured modelde sessiz extrapolation riski.
**Güven:** Yüksek. **Öneri:** Gerçek türe özgü destek aralığı ve OOD politikası tanımlayın.
**Başarı ölçütü:** Alt/üst sınır testleri; sınır dışı girişe açık ve test edilmiş davranış.

### F-08 — Tahmin sonrası fiziksel sınırlar sınırlı
**Önem:** Orta. **Kanıt:** app/main.py:112-123; model2_test10_agirlik_dengesi.csv.
**Davranış/neden ve etki:** Şekil/finite kontrolü sonrası negatifler sıfıra kırpılır; üst/denge/kategori kısıtı yok. 10 örnekte toplam farkın maksimum mutlak değeri 0,9604 kg.
**Güven:** Yüksek. **Öneri:** Yalnız saha standardından doğrulanan invariants uygulayın ve ihlalleri görünür kılın.
**Başarı ölçütü:** Gerçek holdout ve property testlerde tanımlı invariant ihlal oranı.

### F-09 — Hash doğrulaması artefakt kaynağını doğrulamıyor
**Önem:** Orta. **Kanıt:** model_b_artifact.py:35-70, 95-126; docs/EGITIM_API_SAHA_DOGRULAMA.md:28.
**Davranış/neden ve etki:** SHA-256 bütünlük kontrolüdür; model ve manifesti birlikte yazabilen aktör eşleşen hash üretebilir.
**Güven:** Yüksek. **Öneri:** Yetkili registry ve imzalı/attested manifesti deserialize öncesi doğrulayın.
**Başarı ölçütü:** Yetkisiz kaynak/manifest ve artifact tamper testleri joblib yüklemeden reddedilir.

### F-10 — Compose health liveness’tır, model readiness değildir
**Önem:** Orta. **Kanıt:** docker-compose.yml:28-37; app/main.py:72-109.
**Davranış/neden ve etki:** /health 200 olabilirken production model yokluğu status=false ve prediction=503’tür; “healthy” yanlışlıkla tahmin hazır sanılabilir.
**Güven:** Yüksek. **Öneri:** Liveness/readiness’ı izleme ve deployment’ta ayırın.
**Başarı ölçütü:** Model yokken liveness başarılı/readiness başarısız; measured artifact ile ikisi başarılı.

### F-11 — Build tekrarlanabilirliği ve non-root sertleştirme eksik
**Önem:** Düşük. **Kanıt:** Dockerfile:1-8; requirements.txt:1-6.
**Davranış/neden ve etki:** Base tag ve bağımlılık aralıkları tam kilitli değil; USER tanımlı değil, varsayılan root olabilir. Compose diğer önlemleri uygular.
**Güven:** Orta-yüksek. **Öneri:** Lock/hash, image digest ve uygun volume izinleri sonrası non-root kullanın.
**Başarı ölçütü:** Tekrarlanabilir build; süreç non-root ve yalnız audit volume yazılabilir.

### F-12 — Excel metrikleri ve API dokümantasyonu güncel kaynakla uyuşmuyor
**Önem:** Düşük. **Kanıt:** training/ModelB_EgitimPaketi.xlsx Model_Metrikleri; güncel ModelB_sentetik_model_degerlendirme.csv; docs/EGITIM_API_SAHA_DOGRULAMA.md:18 ve README.md:35-43.
**Davranış/neden ve etki:** Workbook baseline sayıları farklı ve Ridge satırı yok; API notu Model1’i işaret ederken güncel README/Compose Model2’yi gösterir. Rapor/servis sahibi karışabilir.
**Güven:** Yüksek. **Öneri:** Tek metrik kaynağı ve koşu hash’i; güncel Model2 app/Compose’ı gösteren API belgesi.
**Başarı ölçütü:** Workbook/CSV/JSON aynı run version/hash; doküman ve Compose eşleşiyor.

## 14. Güçlü yönler

- Sentetik, measured ve aggregate kaynaklar ayrılmış ve sentetik etiketler açık.
- Feature listesi açık; ID, target, oran ve post-process alanları modele sızmıyor.
- Baseline/Ridge/RF aynı holdoutta karşılaştırılmış; R² doğruluk yüzdesi olarak sunulmamış.
- Split ID disjointliği, negatif/nonfinite, tür ve sentetik denge kontrolleri bulunuyor.
- API şema, API key, genel hata mesajları ve manifest hash/şema doğrulaması içeriyor.
- Sentetik aday production tahmini için reddediliyor.
- Prediction/actual/evaluation ayrılmış; SQLite ilişkileri var.
- Compose ayrı image/container/port, read-only filesystem/model mount, capability drop ve no-new-privileges içeriyor.
- Saha v3 şablonu hayvan/parti, ölçüm zamanı, standard, terazi kalibrasyonu ve QC alanlarını kapsıyor.

## 15. Eksikler ve doğrulanamayan konular

- Measured bireysel hayvan/parti verisi ve bağımsız gerçek test yok.
- Hedeflerin gerçek standardı, kapsamı, overlap durumu ve tartım aşaması onaylanmamış.
- Sentetik generator/formül/noise parametreleri bulunmuyor.
- Tür/ağırlık dilimi gerçek performansı ve belirsizlik ölçümü yok.
- Hash doğru, fakat imza/attestation/güven kökü yok; .joblib açılmadı.
- Statik Compose doğru Model2 uygulamasını gösteriyor, ancak Docker daemon erişimi yüzünden aktif container/port/health ve önceki Model1 benzeri yanıtın proses kaynağı doğrulanamadı.
- model2_test_raporu.md terminalde UTF-8 açık seçilince düzgün okunuyor; varsayılan Windows kodlaması mojibake gösterebilir. Dosya byte encoding’i hatalı diye hükmedilmedi.
- Excel metrik sayfasının güncel koşu sürüm/hash bağlantısı yok.
- Production model olmadığı için gerçek inference başarısı doğrulanamaz.

## 16. Önceliklendirilmiş geliştirme yol haritası

### Aşama A — Temel güvenilirlik
**Öncelik:** P0, model performansından önce.
**Bağımlılık:** Veri sahibi, kalite ekibi, veri izinleri ve anonim ID politikası.
**İş:** Hedef sözlüğü/karkas tanımı; generator ve split kaynağını seed/parametre/hash ile sürümleme; ölçüm timestamp/scale/source alanları; animal_id/lot_id ile group split; baseline’ı validation seçim havuzuna katma.
**Fayda:** Etiket ve split kökeni denetlenebilir olur.
**Ölçülebilir kriter (öneri):** Zorunlu alan validasyonu, group ID kesişimi 0, aynı seed ile üretici/split tekrarlanabilirliği.
**Testler:** Şema/provenance, missing/duplicate/nonfinite, generator determinism, group leakage.
**Engel:** Onaylı saha verisi ve kategori sözlüğü yok.

### Aşama B — Model performansı
**Öncelik:** P1, A’dan sonra.
**Bağımlılık:** Temiz measured kayıtlar ve kilitli bağımsız holdout.
**İş:** Baseline/Ridge/RF ve gerekçeli alternatifleri train/validation’da kıyaslama; hedef×tür×ağırlık bandı MAE/RMSE/bias ve residual; gerçek veride kalibre edilmiş tahmin aralığı.
**Fayda:** Modelin baseline’a gerçek değer katıp katmadığını ve zayıf dilimleri gösterir.
**Kriter (öneri):** Her hedef/tür bandı için n ve hata ölçüsü; önceden tanımlanmış gerçek holdout kabul eşiği. Projede henüz sayısal eşik kararı yoktur.
**Testler:** Group holdout, leakage, alt grup metric, residual/calibration.
**Engel:** Yeterli temsili örnek sayısı bilinmiyor.

### Aşama C — Fiziksel tutarlılık
**Öncelik:** P1, operasyonel kullanımdan önce.
**Bağımlılık:** Hedef sınırları, ölçüm standardı ve B sonuçları.
**İş:** Kategorilerin ayrık/tam/örtüşen olmasını ve input/output aşamalarını tanımlama; denge toleransını ölçüm belirsizliğiyle belirleme; OOD ve clipping sözleşmesi.
**Fayda:** Tahmin çıktısının fiziksel anlamı test edilebilir.
**Kriter (öneri):** Sadece tam/ayrık kategorilerde denge invariantı; gerçek/API testlerinde ihlal oranı raporu. Mevcut projede tolerans yok.
**Testler:** Property/boundary, kütle dengesi, target şema ve negatif/üst sınır.
**Engel:** Kesim kategorilerinin işletme tarafından teyidi.

### Aşama D — Üretime hazırlık
**Öncelik:** P0 go/no-go; A/B/C tamamlandıktan sonra.
**Bağımlılık:** İzinli measured data, bağımsız test, hedef standardı ve onaylı model.
**İş:** İmzalı/attested artifact dağıtımı, secret store, TLS/ağ/rate limit/rol, DB saklama-yedekleme, non-root ve kilitli image/dependency, readiness/liveness ayrımı; gerçek Docker engine’de build/start/smoke.
**Fayda:** Denetlenebilir ve yalnız onaylı modeli sunan servis.
**Kriter (öneri):** source_type=measured, production_ready=true, imza/şema/sürüm eşleşmesi; bozuk artifact deserialize öncesi ret; artifact yokken readiness false ve prediction 503.
**Testler:** Tamper/auth/readiness/Compose build ve port 8002/inference/actual/evaluate/DB.
**Engel:** Measured artifact yok ve Docker engine şu ortamda erişilemiyor.

## 17. Üretime hazır olma değerlendirmesi

**Karar: HAYIR — araştırma/prototip seviyesi.**

Üretim model dosyası/manifesti yok; tek aday sentetik ve production_ready=false. Tahmin endpoint’inin 503 vermesi beklenen güvenli davranıştır. Bu, API arızası değil, onaylı model yokluğunun açık ifadesidir.

Gerçek ölçümlü eğitim ve bağımsız holdout yoktur; hedef tanımları belirsizdir; baseline sentetik holdoutta Ridge’i geçmiştir; generator kaynağı bulunamamıştır. Çalışan container ve 8002 eşlemesi Docker daemon erişimi olmadan kanıtlanamamıştır. Statik Compose ise ayrı Model2 uygulamasına, image’a ve porta işaret etmektedir.

## 18. Sonuç ve sonraki adım

Model2 API, sentetik candidate manifesti ve ayrı Compose mimarisi kaynak kodda tanımlıdır. Test kodu temel API korumalarını kapsar. Modelin gerçek operasyon başarısı için kanıt yoktur.

İlk olarak hedef sözlüğü ve tartım standardını işletmeyle kesinleştirin; sonra izinli measured veri toplama/onayını ve generator sürümlemesini tamamlayın. Baseline dahil model seçimini yalnız validation’da yapıp hayvan/parti gruplarından ayrılmış gerçek holdoutta ölçün. Bu koşullar sağlanana kadar production artifact yayımlamayın ve tahmin endpoint’inin 503 davranışını koruyun.
