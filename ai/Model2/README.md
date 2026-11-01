# AVATAR Yarışma — Model 2 (karkas parçalama)

## Amaç ve kapsam

Model B prototipi, hayvan türü ve karkas ağırlığından sekiz karkas çıktı kategorisini kg olarak tahmin etmek için hazırlanmıştır. Sentetik kayıtlardaki tartım zamanı kanıtlanmamıştır; saha kullanımında ağırlığın kesim öncesi ölçüldüğü prosedürle doğrulanmalıdır: but, sırt, omuz, kaburga, kıyma, yan ürün, kemik/yağ/sinir ve fire. Canlı ağırlık karkas ağırlığından farklıdır. Hedef kategorilerin gerçek kesim standardındaki sınırları ve birbirleriyle çakışıp çakışmadıkları işletme tarafından teyit edilmelidir.

## Veri durumu

`data/raw/synthetic/` içindeki 1.200 satırın tamamı sentetik/simüledir (400 kuzu, 400 koyun, 400 dana). Train/validation/test dosyaları sırasıyla 840/180/180 satır içerir ve yalnız sentetik kayıt barındırır. `data/raw/published_aggregate/` altındaki makale ve Steakpedia özetleri bireysel hayvan kayıtları değildir; eğitimde kullanılmaz. `data/raw/measured/` gerçek saha kayıtları için boş hedef klasördür. Gerçek fabrika doğrulaması yapılmamıştır.

## Ortam ve bağımlılıklar

Bu checkout'ta Model2 için ayrı bir `requirements.txt` veya sanal ortam bulunmuyor. Doğrulamada kullanılan mevcut ortam `ai/Model1/.venv` (Python 3.12.10); bağımlılık listesi `ai/Model1/requirements.txt` içinde. Model1 içinde yalnızca Model B varsayılan artefakt/audit dizinleri düzeltilmiş; API davranışının geri kalanı değiştirilmemiştir. SQLite Python standart kütüphanesindendir.

```powershell
# Komutları D:\Coding\projectDebugging\avatar-yarisma\ai içinden çalıştırın
# Mevcut doğrulama ortamını kullanın; yeni venv/bağımlılık kurulumu gerekmez.
.\Model1\.venv\Scripts\python.exe -m Model2.training.train_model_b
$env:PYTHONPATH = "Model1"
.\Model1\.venv\Scripts\python.exe -m pytest -v -c Model1\pytest.ini Model1\tests
```

Tam test komutu bu doğrulamada 43 testi geçirir; bir Starlette/httpx deprecation uyarısı vardır. Test ortamı ve ayrıntılar `reports/api_test_report.md`, değişiklik/kalan riskler `reports/comprehensive_audit.md` içindedir. Başka bir makinede temiz kurulum gerekiyorsa mevcut `ai/Model1/requirements.txt` kullanılabilir; bağımlılık sürümleri bu görevde değiştirilmedi.

Eski eğitim dosyasıyla uyumluluk için `python -m Model2.training.ModelB_egitim_kodu` aynı pipeline'ı çağırır.

## Eğitim ve metrikler

Özellikler: `hayvan_turu`, `karkas_agirligi_kg`. Kayıt ID, hedefler, hedef oranları, toplam çıkış, denge farkı ve post-process sütunları özelliklerden çıkarılmıştır. Preprocessing/pipeline sadece train'de fit edilir. Train'den öğrenilen tür-bazlı ortalama verim oranı baseline'ı, Ridge ve Random Forest karşılaştırılır. Aday, validation'da baseline'a göre hedef normalize MAE ile seçilir; test seti fit/seçim için kullanılmaz.

24.10.2026 çalışma koşusu Python 3.12.10 ve scikit-learn 1.9.1 kullandı. Validation'da Ridge seçildi. Testte ortalama hedef-bazlı normalize MAE oranı: baseline 1.0000, Ridge 1.0079, Random Forest 1.0523. Yani testte hiçbir ML adayı baseline'dan iyi değildi. Her hedef/model için test MAE, RMSE, R² ve n=180 değerleri `reports/synthetic_evaluation/model_b_candidate_metrics.csv` ve `.json` dosyalarındadır. Bunlar sentetik formülü ne kadar öğrendiğini gösterir; gerçek hayvan/işletme doğruluğu değildir.

Model `models/model_b_synthetic_candidate.joblib` adına yazılır; eğitim aynı dizinde `model_b_synthetic_candidate.manifest.json` sidecar'ına model/veri sürümü, kaynak, hazır olma durumu, özellik/hedef listesi ve artefakt SHA-256 değerini yazar. Aday `source_type=synthetic`, `production_ready=false` olarak kalır; API bu adayı hiçbir koşulda servis etmez. Hash dosya byte bütünlüğünü kontrol eder; güvenilir kaynak veya bilimsel/saha doğruluğu kanıtı değildir. Saha doğrulaması ve bağımsız gerçek verili değerlendirme olmadan üretime hazır model yoktur.

## API ve güvenlik

Model2 kendi FastAPI uygulamasını ai/Model2/app/main.py içinden çalıştırır. Uygulama Model1 kodunu import etmez; Docker imajı Model2/Dockerfile ile ayrı kurulur. Yerel çalıştırmada ai/Model2 dizininden Model1 sanal ortamındaki Uvicorn kullanılabilir.

Config varsayılanı dosya konumuna göre `ai/Model2/models` dizinine çözümlenir; özel bir artifact dizininiz varsa `MODEL_B_DIR` ile mutlak yolu verebilirsiniz. Geçici Uvicorn HTTP smoke testi `/health` 200, `/v1/models/status` 200 ve doğrulanmış üretim artefaktı olmadığı için `/v1/predict/carcass-cuts` 503 döndürdü. Migration düzeltmesinden sonra fixture modelle tam tahmin/ölçüm/değerlendirme akışı testten geçti. Docker CLI mevcut, fakat daemon erişilemiyor.

- GET /health: Model2 liveness kontrolü; service=avatar-model2-api döndürür. Model readiness için status endpointini kullanın.
- GET /v1/models/status: yalnız Model2 üretim artefaktı, sentetik aday, feature ve sekiz hedef durumunu döndürür; Model1 yield/EKP alanları içermez.
- `POST /v1/predict/carcass-cuts`: `hayvan_turu` (kuzu/koyun/dana), `karkas_agirligi_kg` ister. Sadece `MODEL_B_DIR/model_b_production.joblib` ve buna eşleşen `model_b_production.manifest.json`, `production_ready=true`, `source_type=measured`, doğru feature/target şeması, model ve veri sürümü ve mevcut artifact byte'larıyla eşleşen 64 haneli `artifact_sha256` varsa tahmin döndürür. Hash yoksa/uyuşmazsa model yüklenmeden reddedilir. Eski hash'siz production manifestleri geriye dönük olarak kabul edilmez; güvenilir artefakt için manifest kontrollü dağıtım sürecinde yenilenmelidir. Şu anda production dosyası yoktur; beklenen cevap `503`'tür.
- `POST /v1/actual/carcass-cuts`: daha sonra gerçekten tartılmış sekiz çıktı değerini `prediction_id` ile ve saat dilimli `measured_at_utc` ile ayrı kayıt olarak ekler.
- `GET /v1/evaluate/carcass-cuts/{prediction_id}`: tahmin ile gerçekleşen kayıtlı ölçümü her hedef için karşılaştırır. `deviation_kg=tahmin-gerçekleşen`; pozitif modelin fazla, negatif düşük tahmin ettiğini gösterir.
- Swagger: `http://127.0.0.1:8000/docs`.

Örnek tahmin isteği:

```json
{"hayvan_turu":"kuzu","karkas_agirligi_kg":18.2}
```

Bir tahmin üretim artefaktı ile çalıştığında yanıt `prediction_id`, `predicted_cuts_kg`, `model_version`, `data_version` ve kaynak türü verir. Mevcut Model B artefaktı olmadığı için bu örnek şu an 503 ile yanıtlanır; sahte tahmin dönülmez.

`API_KEY` ayarlanmışsa tahmin, gerçek ölçüm ve değerlendirme uçlarının tamamı `x-api-key` ister (değerlendirme ucu GET'tir). `APP_ENV=development/test` dışında anahtarsız servis fail-closed davranır. Anahtarı kaynak koda/loglara koymayın. Manifest ve artefakt birlikte aynı güvenilmeyen kaynaktan değiştirilebiliyorsa saldırgan yeni hash hesaplayıp kötü amaçlı joblib yerleştirebilir. Hash dijital imza/yetkilendirme değildir; üretimde manifesti yetkili kanaldan koruyun, imza/attestation veya eşdeğer güven zinciri kullanın. Üretim için secret store, TLS, ağ erişim kontrolü, yetki rolleri, hız sınırı, izleme ve DB saklama/yedekleme politikası gerekir.

## Kayıt veritabanı ve migration

Başlangıç backend'inde DB/migration yoktu; Model B izlenebilirliği için yalnızca SQLite tabanlı, bağımsız `sql/001_model_b_audit.sql` migration'ı eklendi. Tahmin satırı girdi, çıktı, model/veri sürümü ve kayıt zamanını içerir. Sonradan gelen ölçüm ayrı tabloda; fiziksel ölçüm zamanı (`measured_at_utc`) ve API'ye kayıt zamanı ayrı saklanır. Tek tahmine ikinci ölçüm eklenemez; bilinmeyen tahmin ID'si reddedilir. `MODEL_B_AUDIT_DB` ile konum değiştirilebilir; varsayılan `Model2/var/model_b_audit.sqlite3`, Docker Compose bu dizini volume olarak bağlar. DB `.gitignore` içindedir.

API kendisi terazi ölçümünün gerçek olduğunu doğrulayamaz. `source_type=measured` kayıt endpoint'i sadece gerçek ölçüm yapıldığında kullanılmalıdır. Kimlik ve tesis verilerini anonim tutun.

## Saha doğrulaması ve sonraki koşullar

Genişletilmiş boş saha kayıt şablonu: `templates/field_data/model_b_saha_verisi_v3.csv`. Eski v1/v2 şablonları korunmuştur. V3, ölçüm aşaması ve saatleri, kesim standardı, kategori tanımları, terazi kalibrasyonu, kaynak/izin ve kalite kontrol durumunu satır bazında kaydetmek içindir. Zaman damgaları saat dilimli ISO 8601 olmalıdır; alanların kurumun tartım prosedürüyle eşleştirilmesi gerekir.

1. Hayvan ID'si anonim ama stabil olacak; aynı hayvan train ve test'e dağılmayacak.
2. Karkas ağırlığı parçalama öncesi tartılacak; tür, sıcak/soğuk karkas, kemikli/kemiksiz tanım, kesim standardı, birim, ölçüm cihazı/kalibrasyonu ve zaman damgası kaydedilecek.
3. Sekiz hedefin kapsamı, tartım sınırı ve örtüşmesi işletme ile kararlaştırılacak. Yalnız tüm kategoriler aynı aşamada ve örtüşmeden tartılıyorsa kütle dengesi geçerli denetimdir.
4. Eksik hedefler boş kalacak, sıfıra doldurulmayacak. Hayvan/grup bazlı ve zaman/işletme ayrımlı train-validation-test kurulacak.
5. Gerçek train/validation üzerinde tür baseline, Ridge ve RF karşılaştırılacak; bir defa ayrılmış bağımsız gerçek testte hedef bazlı MAE/RMSE/R² ve n raporlanacak. Saha gölge modu ve sorumlu onayı tamamlanmadan production artifact üretilmeyecek.

Kaynak, lisans/kullanım ve veri düzeyi envanteri `docs/KAYNAKLAR_LISANSLAR.md`; eğitim API/saha akışı `docs/EGITIM_API_SAHA_DOGRULAMA.md`; veri kalitesi `reports/data_quality_report.md`; test sonucu `reports/api_test_report.md` içindedir. Gerçek kaynakların mevcut CSV/özet kayıt sayıları ve kapsam sınırlamaları `docs/KAYNAKLAR_LISANSLAR.md`'de listelenmiştir.

### Test amaçlı kayıt örneği

Aşağıdaki tahmin kimliği ve ağırlıklar yalnızca API testi örneğidir; saha verisi değildir. Gerçek kurulumda `prediction_id`, successful tahmin yanıtından alınır.

```json
{
  "prediction_id":"00000000-0000-0000-0000-000000000001",
  "measured_at_utc":"2026-10-24T08:00:00+03:00",
  "actual_cuts_kg":{"but_kg":2,"sirt_kg":2,"omuz_kg":2,"kaburga_kg":2,"kiyma_kg":2,"yan_urun_kg":2,"kemik_yag_sinir_kg":2,"fire_kg":2}
}
```

Gönderim `POST /v1/actual/carcass-cuts` ile yapılır. Kayıtlı comparison için `GET /v1/evaluate/carcass-cuts/{prediction_id}` çağrılır; yanıt her hedefte `predicted_kg`, `actual_kg`, `deviation_kg` alanları ve model/veri sürümleriyle iki zaman damgası döndürür. Test raporu sentetik fixture ile bu akışı doğrular; gerçek üretim modeli veya saha ölçümü anlamına gelmez.


## Docker ve yarışma raporu

Model2 Compose yapılandırması ai/Model2/docker-compose.yml içindedir. Model2 dizininden docker compose config --quiet ile doğrulayın; imajı docker compose build model2-api ile derleyin ve API_KEY güvenli ortamda ayarlandıktan sonra docker compose up -d model2-api ile yalnız Model2 servisini çalıştırın. Servis 127.0.0.1:8002 üzerinde ve avatar-model2-api container adıyla dinler. Üretim artefaktı yokken status üretime hazır olmadığını, prediction endpointi ise 503 durumunu bildirir.

Kanıta dayalı yarışma özeti, testteki baseline/Ridge/Random Forest metrikleri, veri kökeni, lot geri çağırma sınırları ve kalan doğrulama koşulları `reports/competition_report.md` içindedir. Gerçek saha doğrulaması yapılmadı.

---

## 2026-11-01 MLOps & Çift Katmanlı Backend Entegrasyonu

### 1. Mimari ve Konumlandırma
- **Mikroservis Dağıtımı:** `ai/Model2/` (Kendi Dockerfile ve `docker-compose.yml` dosyasıyla 8002 portunda çalışan bağımsız mikroservis).
- **Backend Entegre Dağıtımı:** `backend/app/ml/` (Ana backend üzerinden `POST /api/v1/ai/butchering-output/predict` port 8000).
- **Audit Veritabanı:** `model2_audit_data` volume'u altındaki SQLite deposunda tahminler, gerçekleşen ölçümler ve değerlendirmeler saklanır.
- **Fail-Closed Güvenlik Kuralı:** `models/model_b_production.joblib` ve doğrulanmış `model_b_production.manifest.json` (`source_type=measured`, `production_ready=true`, SHA-256 eşleşmesi) bulunmadığında tahmin uç noktası **HTTP 503** döner. Sentetik aday asla sahte üretim tahmini olarak sunulmaz.

### 2. Eğitim ve Doğrulama Komutları
- **Sentetik Aday Eğitimi:**
  ```powershell
  python -m ai.Model2.training.train_model_b
  ```
  *Çıktı:* `ai/Model2/models/model_b_synthetic_candidate.joblib` ve `model_b_synthetic_candidate.manifest.json`.
- **Birim ve Entegrasyon Testleri:**
  ```powershell
  $env:PYTHONPATH="ai/Model2"
  python -m pytest ai/Model2/tests/ -v
  ```
  *Sonuç:* 16 passed, 0 failed, 1 uyarı (Starlette deprecation).
- **Docker İle Mikroservisi Başlatma:**
  ```powershell
  $env:API_KEY="your-secure-key"
  docker compose -f ai/Model2/docker-compose.yml up -d
  ```

### 3. API Uç Noktaları ve Doğrulama
- `GET /health`: Liveness kontrolü (`service="avatar-model2-api"`).
- `GET /v1/models/status`: Model hazırlık durumunu açıkça raporlar (`model_b_production_ready: false`, `model_b_candidate_available: true`, `model_notice`).
- `POST /v1/predict/carcass-cuts`: Üretim artefaktı yokken güvenli **HTTP 503** döner (Fail-closed prensibi).
- `POST /v1/predict/carcass-cuts/experimental`: Sentetik aday modeli pilot ve test amaçlı çalıştırır. Yanıtta `experimental: true`, `production_ready: false`, `source_type: "synthetic"` ve yasal/ticari uyarı döner.
- `POST /v1/actual/carcass-cuts`: Fiili tartım ölçümlerini kaydeder.
- `GET /v1/evaluate/carcass-cuts/{prediction_id}`: Tahmin ile gerçekleşen tartımı 8 kategori bazında kıyaslar (`deviation_kg = predicted - actual`, `is_experimental: true/false`).

### 4. Gerçek Üretim Durumu ve Şeffaflık
- **Veri Kaynağı:** `data/raw/synthetic/` (1.200 simüle karkas: 400 kuzu, 400 koyun, 400 dana; 840 train / 180 validation / 180 test).
- **Üretime Hazır Olma:** **ÜRETİME HAZIR DEĞİL (FAIL-CLOSED KORUNUYOR).** Gerçek saha ölçümleri (`data/raw/measured/`) sağlanana kadar model güvenli biçimde üretim dışı tutulmaktadır.

