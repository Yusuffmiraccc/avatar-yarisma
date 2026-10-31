# Model2 toplu denetim ve doğrulama raporu

Denetim tarihi: 24.10.2026. Bu dosyanın ilk bölümleri önceki Model2 audit turlarının tarihsel kayıtlarını içerir; bu görevin güncel ve bağlayıcı sonucu son iki bölümde ve `competition_report.md` içindedir. Gerçek saha verisi veya tesis doğrulaması yoktur.

## Yönetici özeti

- Eğitim ve split denetimi çalıştı: 1.200 sentetik satır, 840/180/180 split, benzersiz ve ayrık `kayit_id`; özellikler yalnız `hayvan_turu` ve `karkas_agirligi_kg`.
- Model eğitimi aynı ortamda yeniden çalıştırıldı. Seçilen aday Ridge, ancak sentetik holdout testinde baseline'dan daha iyi değil. Üretim hazır değil.
- Önceki test engeli migration yolunu `ai/Model2/sql` konumuna sabitleyerek düzeltildi. Model B API ve tüm depo testleri yeniden çalıştırıldı; sonuçlar bu raporun son bölümündedir.
- Model2 saha CSV'si daha eksiksiz v3 şablonuyla genişletildi; eski şablonlar ve mevcut veriler korunuyor.
- Docker CLI/Compose kurulu, daemon erişilemiyor; container testi yapılmadı.

## Git başlangıç/bitiş durumu

Başlangıç dalı `main`; son commit `3330cb0 Merge pull request #2 from Yusuffmiraccc/security/backend-hardening`. Başlangıç çalışma ağacı temiz değildi: Model1 altında çok sayıda silinmiş/değişmiş ve izlenmeyen dosya zaten vardı; bunlara dokunulmadı. `git diff --check` başlangıçta geçmiştir (yalnız CRLF uyarıları vardı).

Model2 başlangıçta Git tarafından izlenmiyordu (`?? ai/Model2/`). Denetim sonunda Model2 de izlenmeyen dizin olarak kalır; bu değişiklikler commit edilmedi. Dosyalar proje Git'inde yeni oluşturulmuş olsa da henüz Git tarafından takip edilmiyor.

## Veri kökeni, kalite ve model

Kaynak dosyalar Model2 README ve `data_quality_report.md` içinde listelenmiştir. Bireysel 1.200 kaydın tamamı sentetik/simüledir. Yayın/toplu kaynak özetleri bireysel hayvan verisi gibi eğitime katılmamıştır. Gerçek measured dizini boş; kaynak indirimi veya saha sonucu bu denetimde üretilmedi.

Bağımsız yeniden eğitim: Python 3.12.10, scikit-learn 1.9.1, pandas 2.3.3, NumPy 2.5.4. Split sayıları 840/180/180. Mevcut hashler yeniden eğitim sonrası aynı kaldı:

| Dosya | SHA-256 |
|---|---|
| `models/model_b_synthetic_candidate.joblib` | `31E41871272B6546A3F077C191D7B3DA0DAB37C5B21607E90F248102AE67769A` |
| `reports/synthetic_evaluation/model_b_candidate_metrics.json` | `BF3E0C5DB74C18966FEE054256A38E56F584C88F948C24E9B80640C75AEBE179` |
| `reports/synthetic_evaluation/model_b_candidate_metrics.csv` | `83455BD31B569D459F0E1FD5BBA1BB6FF9A503E9861146375C1C029008F65D73` |

Test metrikleri (synthetic, n=180, sekiz hedef düzleştirilmiş):

| Model | MAE kg | RMSE kg | Uniform R² |
|---|---:|---:|---:|
| Tür oranı baseline | 1.82828653 | 3.44308295 | 0.90274366 |
| Ridge | 1.84388974 | 3.45562619 | 0.90216580 |
| Random Forest | 1.94117937 | 3.68999900 | 0.89419094 |

Validation seçiminde Ridge çıkmıştır; testte baseline MAE'sinden %0.85 daha yüksek MAE üretmiştir (1.84389 vs 1.82829). Random Forest da baseline'dan kötüdür. Metrikler yalnız sentetik formül/split başarısıdır, saha performansı değildir. Aday artefaktı sentetik adıyla ve `production_ready=false` olarak kalmıştır; üretim artefaktına yazılmamıştır.

### Veri sızıntısı ve ölçüm zamanı

Model eğitim özellik listesi yalnız tür ve karkas kg'dır. ID, hedefler, toplam çıkış, denge farkı ve hedeflerden türetilen oranlar girdi değildir. Preprocessor pipeline içinde sadece train'e fit edilir; validation aday seçimi, test nihai ölçüm içindir.

Sentetik kaynak, `karkas_agirligi_kg` alanının adı dışında gerçek tartım zamanı kanıtı sunmuyor. Saha şablonu ağırlığı kesim öncesi ölçmeyi hedefliyor, ancak bu mevcut sentetik kaydın ölçüm zamanını kanıtlamaz. Bu nedenle gelecekteki API tahmini için üretim öncesi kullanılabilir girdi olarak ancak saha prosedürüyle teyit edildiğinde kabul edilebilir.

Sekiz çıktı hedefinin sınırları ve birbirini dışlayıp dışlamadığı doğrulanmış değil. `toplam_cikis_kg` hedef toplamından, denge farkı da bu toplamdan türetilmiştir; bunlar girdi değildir. Sentetik veride kütle dengesi formül gereği kapanır. Gerçek fiziksel kütle dengesi olduğu iddia edilemez. Ölçüm sonrası sekiz kayıp/çıktı oranının tahmin girdisi yapılması hedefe/gerçekleşmiş sonuca sızıntı olur; bunlar üretim öncesi biliniyorsa bile yalnız doğrulanmış plan varsayımı olarak ayrı senaryoda değerlendirilebilir.

## API, güvenlik ve SQLite

Ortak API kaynak dosyaları bu checkout'ta `ai/Model1/app/` altında. Testler API anahtarının yapılandırıldığı durumda korumayı, geliştirme dışı ortamda anahtarsız fail-closed davranışını, Pydantic girdi kontrollerini ve sentetik adayın reddini kapsıyor. Sağlık/model status herkese açık; status hash doğrulaması yapar ama joblib yüklemez. Tahmin loader'ı production manifestinde 64 hex SHA-256 ister, status aşamasında hash'i kontrol eder ve joblib öncesi aynı açık dosya tanıtıcısından hash'i tekrar hesaplayıp o tanıtıcı üzerinden deserialize eder. Model bundle sürümleri manifestle eşleşmelidir. Hash'siz eski manifestler fail-closed reddedilir. Hash yalnızca byte bütünlüğü kontrolüdür; aynı güvenilmeyen kaynağın hem modeli hem manifesti değiştirmesine karşı imza veya güvenilir dağıtım kanalı değildir.

SQLite şeması `CREATE TABLE IF NOT EXISTS` kullanıyor; aynı migration'ı geçici test DB'sinde tekrar çalıştırdım ve mevcut audit kaydı korundu. Prediction ID PK, actual ID aynı zamanda PK/FK; böylece tek tahmine tek actual bağı korunur. İzole eşzamanlı insert denemesinde aynı tahmin için bir actual yazıldı ve ikinci insert duplicate olarak reddedildi. Şema JSON içeriği veya tartım kategorilerinin kütle dengesini SQL düzeyinde doğrulamaz; API tip/negatif/non-finite sınırlarını denetler, kategorilerin fiziksel tanımı ve örtüşmesi ise işletme kararı gerektirir.

## Test, Docker ve çözülemeyen kusur

Kullanılan komut (AI kökünde `PYTHONPATH=Model1` ayarlanarak):

```powershell
cd D:\Coding\projectDebugging\avatar-yarisma\ai
.\Model1\.venv\Scripts\python.exe -m pytest -v -c Model1\pytest.ini Model1\tests
```

Sonuç: 32 toplandı; 29 geçti, 3 başarısız, 0 atlandı. Başarısızlar:

- `test_model_b_prediction_loads_measured_ready_bundle`: ölçüm API yanıtı 503; audit migration yolu bulunamadı.
- `test_model_b_persisted_prediction_then_measured_actual_then_evaluation`: prediction aynı migration dosyası hatasıyla 503.
- `test_model_b_actual_endpoint_rejects_unknown_id_and_ambiguous_timestamp`: beklenen 404 yerine migration dosyası `FileNotFoundError` test istemcisine sızdı.

Kök neden: `ai/Model1/app/model_b_audit.py` migration sabitini `Path(__file__).resolve().parents[1] / "Model2" / "sql" / ...` kuruyor. Bu checkout'ta uygulama `ai/Model1/app`, migration `ai/Model2/sql` konumunda; çözülmüş yol yanlışlıkla `ai/Model1/Model2/sql` oluyor. Düzeltilmesi API kodunda (Model1) değişiklik gerektiriyor; görev kapsamındaki açık koruma nedeniyle düzenlenmedi. Testlerin başlangıçta Model1 klasöründen çağrıldığı denemede `Model2` import yolu bulunamadı; doğru AI kökü/config ile çalıştırıldığında yukarıdaki üç esas hata ortaya çıktı.

Tek uyarı Starlette TestClient/httpx deprecation uyarısıdır; bağımlılık değiştirilmedi. Geçici Uvicorn sürecinde HTTP smoke testleri geçti: `/health` 200, `/v1/models/status` 200/production-ready false, measured production artifact yokken prediction 503. ModelB uçtan uca prediction → actual → evaluation bu ortamda **geçmiş sayılmaz**. Eski rapordaki 32 passed beyanı güncel checkout için yeniden doğrulanmadığından burada başarı sonucu olarak kullanılmamalıdır.

Docker CLI 29.9.2 ve Compose 5.6.1 mevcut. `docker info` `dockerDesktopLinuxEngine` named pipe'ına erişemedi. Bu nedenle Compose doğrulama, build, container başlangıcı veya HTTP smoke testi yapılmadı.

## Saha verisi için hazırlık

`templates/field_data/model_b_saha_verisi_v3.csv` yeni, boş ve zenginleştirilmiş saha şablonudur; eski CSV'ler korunmuştur. Hayvan/parti kimliği, tür/ırk, karkas ağırlığının niteliği/aşaması/zamanı, başlangıç ve çıktı tartım zamanları, kesim/sınıflandırma sürümü, hedef tanımları, kg, terazi/kalibrasyon, anonim işletme/operatör, kaynak ve onay/kalite durumu alanları içerir. Ölçüm zamanları ISO 8601 saat dilimiyle girilmelidir. Hayvan kimliği anonim ve stabil olmalı ki aynı birey split'ler arasında bölünmesin. Üretimden önce saha sahibi kategori sınırlarını, kemik/yağ/sinir/fire kapsamını, terazi standardını, sıcak/soğuk karkas türünü ve kaynak/onay akışını tanımlamalıdır.

Model2 `.gitignore` dosyası operasyonel SQLite DB/WAL/SHM dosyalarını, `measured` altındaki gerçek bireysel verileri ve yerel production artifact/manifest dosyalarını Git dışında tutar; `.gitkeep` ve sentetik candidate korunur.

## Öncelikli kalan işler

1. İmzalı/attested manifest veya hash'i modelden ayrı koruyan yetkili üretim dağıtım zinciri belirlemek.
2. Şablon alanlarını tesis, veri sorumlusu ve kalite ekibiyle teyit etmek; gerçek veriyi anonim/onaylı biçimde toplamak.
3. Gerçek hayvan/parti düzeyinde bağımsız holdout ve gölge çalışma yapıp baseline ile karşılaştırmak.
4. Ayrılmış ephemeral MySQL test DB ile backend lot/recall testlerini çalıştırmak.
5. Docker daemon erişimi sağlandığında Compose/build/health akışını test etmek.

## Durum

Model2 sentetik araştırma prototipi olarak kullanılabilir; gerçek parçalama tahmini, operasyon veya muhasebe kararı için hazır değildir. Gerçek saha doğrulaması tamamlanmamıştır. Migration düzeltmesiyle geçici test modeli üzerinden Model B API tahmin → DB → actual → evaluation akışı testten geçti.

## Kritik hata düzeltme isteği — tekrar doğrulama

2026-10-24 tarihli kritik düzeltme turunda yalnızca `ai/Model1/app/model_b_audit.py` migration path'i, `ai/Model1/app/main.py` Model B manifest/hash loader'ı, Model B testleri ve Model2 eğitim/report dokümantasyonu değiştirildi. Üç eski başarısız test ayrı çalıştırıldığında **3 passed** oldu. Model B test dosyalarına varsayılan dizin testi eklendi. Tüm paket **43 passed, 0 failed, 0 skipped, 1 warning** verdi (4.59 saniye); uyarı Starlette TestClient/httpx deprecation uyarısıdır.

Ek testler hash eşleşmesiyle başarılı bundle yükleme, yanlış hash ve hash eksikliğinde joblib'in hiç çağrılmadan reddetme, eski/uyuşmayan model sürümü, sentetik manifestin deserialize öncesi reddi, üretim artefaktı yokluğu, migration yolu ve migration kayıp hata mesajını kapsar. Uçtan uca test geçici fixture model ve `tmp_path` SQLite kullanır; tahminden sonra ölçümü ayrı kaydeder, saat dilimini UTC'ye çevirir, pozitif/negatif sapma kuralını doğrular ve duplicate/unknown ID kontrollerini yapar. Gerçek Model B production artifact yoktur; API bu nedenle 503 döndürür.

Eğitim akışı sentetik adaya SHA-256 içeren sidecar manifest üretir: `model_b_synthetic_candidate.manifest.json`; üretim adına dosya yazılmaz. Üretim loader'ı hash'i manifest okunurken doğrular, daha sonra aynı dosya tanıtıcısında tekrar hesaplar ve yalnız o tanıtıcıyı `joblib.load`'a verir. Hash, dosyanın güvenilir kaynaktan geldiğini veya modelin bilimsel/saha doğruluğunu kanıtlamaz. Manifest ve model birlikte değiştirilebiliyorsa saldırgan eşleşen yeni hash üretebilir; imza/attestation ve ayrı korunan dağıtım zinciri gereklidir. Eski hash'siz production manifestler otomatik onarılmaz, 503 ile reddedilir.

Docker daemon yeniden kontrol edildi: `dockerDesktopLinuxEngine` named pipe bulunamadı. Compose/build/container doğrulaması yapılamadı. Bu ara snapshot'taki yanlış `MODEL_B_DIR` varsayılanı son tamamlama turunda `ai/Model2/models` olacak şekilde düzeltildi; yeni test farklı çalışma dizininden doğruladı. Model1'de izin verilen iki konu dışındaki davranışlara dokunulmadı; commit/push/deploy yapılmadı.


## Model 2 tamamlama görevi — ek doğrulama

`MODEL_B_DIR` varsayılanı `ai/Model2/models`; audit DB varsayılanı `ai/Model2/var/model_b_audit.sqlite3` olarak dosya konumuna göre hesaplanır. Test bu ayarları farklı cwd içinden alt süreçte doğrular. Model1 Dockerfile/Compose, `ai` build context'iyle uyumlu olacak biçimde düzenlendi; app `/app/Model1` altında kalır, migration SQL imaja alınır, Model1 model/rapor ve Model2 model dizinleri ayrı mount edilir, DB yeni named volume içindedir. Model B test dosyaları **28 passed** verdi (2.82 saniye). `docker compose ... config --quiet` geçti, fakat daemon named pipe yok; image/container testleri yapılmadı.

`reports/competition_report.md` güncel Model2 kaynak/method/metric/lot sınırı özetidir. Backend `test_traceability_recall.py` daha önceki 5 testi MySQL `localhost:3307` bağlantı reddi nedeniyle setup edemedi; ardından altıncı unknown/unlinked/duplicate-origin senaryosu testi eklendi ancak çalıştırılamadı; test fixture'ı veritabanı oluşturup tabloları truncate edebildiğinden bu davranış doğrulanana dek sadece ayrılmış ephemeral test DB kullanılmalıdır. Görev sırasında bağlantı kurulamadığı için fixture veritabanı değiştirmedi.
