# AVATAR Yarışma — Model 2 Tamamlama ve Doğrulama Raporu

Tarih: 24.10.2026. Kaynak kanıtları Model2 içindeki mevcut ham/işlenmiş dosyalar, eğitim kodu, metrik raporları, Model1 API kodu ve backend şeması/testleridir. Gerçek hayvan, fabrika veya saha kayıtları bu doğrulamada kullanılmadı.

## 1. Proje amacı ve model yaklaşımı

Model B, hayvan türü ve karkas ağırlığından sekiz karkas çıktı kategorisini kilogram cinsinden tahmin eden teknik prototiptir. Karkas ağırlığı canlı hayvan ağırlığı değildir. Özellikler `hayvan_turu` ve `karkas_agirligi_kg`; hedefler `but_kg`, `sirt_kg`, `omuz_kg`, `kaburga_kg`, `kiyma_kg`, `yan_urun_kg`, `kemik_yag_sinir_kg`, `fire_kg` olarak tanımlanmıştır. Gerçek kesim standardında bu kategorilerin sınırları ve örtüşüp örtüşmediği teyit edilmiş değildir.

## 2. Veri kaynakları ve örnek/anonymize veriler

- `data/raw/synthetic/ModelB_Sentetik_Parcalama_Verisi.csv` ve `.xlsx`: 1.200 simüle satır; 400 kuzu, 400 koyun, 400 dana. Bu kayıtlar bireysel saha ölçümü değildir.
- `data/processed/splits/ModelB_{train,validation,test}_sentetik.csv`: 840/180/180 sentetik kayıt. Kod kaynak bayrağını, bölüm etiketini, kimlik tekrarı/kesişimini, negatif/sonlu değerleri ve sentetik formülleri doğruluyor. `kayit_id` kümeleri ayrık. Mevcut simülasyonda satır başına bir sentetik kimlik vardır; gerçek hayvanda/partide tekrarlı ölçüm bulunmadığı bu sentetik ID kontrolüyle kanıtlanamaz.
- `data/raw/published_aggregate/` içindeki akademik/site kaynakları toplu özetlerdir, bireysel hayvan satırı değildir ve eğitim/teste katılmamıştır. Kaynak URL, kullanım/lisans belirsizlikleri `docs/KAYNAKLAR_LISANSLAR.md` içindedir. Özetlerden bireysel kayıt türetilmemiştir.
- `data/raw/measured/` boş hedef klasördür. Gerçek veya anonimleştirilmiş bireysel saha örneği yoktur; mevcut CSV’ler anonimize gerçek veri değildir.
- Ham sentetik dosyada `yas_ay` ve `yag_durum_skoru` tüm satırlarda eksiktir; özellik olarak kullanılmamış ve doldurulmamıştır. Diğer ham alanlarda raporlanan eksik değer, sayısal sonsuzluk veya negatif ağırlık/hedef yoktur. Sekiz çıktı toplamı karkas girişine sentetik formül gereği eşittir (maksimum mutlak fark yaklaşık `1.2e-13 kg`); bu gerçek tartım tutarlılığını doğrulamaz.

## 3. Gerçek/sentetik ayrımı ve sınırlılıklar

Eğitim kodu sadece `SENTETIK_SIMULASYON` kaynaklı splitleri kabul eder. Kaydedilen artefakt `source_type=synthetic`, `production_ready=false` olarak, ayrı aday dosyasına yazılır. Makale ve site kaynaklarının toplu istatistikleri farklı kayıt düzeyi/ölçüm tanımları nedeniyle bireysel satır gibi kullanılmamıştır. Sentetik splitlerde sabit seed ve disjoint kayıt kimlikleri tekrar üretilebilir teknik deney sağlar; simülasyon üretim mekanizmasının paylaşılan dağılımına aşırı uyum riskini veya gerçek popülasyonda genellemeyi ortadan kaldırmaz.

## 4. Referans yöntemi ve aday karşılaştırması

Baseline, yalnız train bölümünden tür bazında hesaplanan ortalama hedef/karkas oranını test karkas ağırlığıyla çarpar. Ridge ve Random Forest aynı train/validation/test kayıtları üzerinde kıyaslanır; pipeline ön işleme train verisine fit edilir. Aday seçimi validation normalize MAE ile yapılmış, test yalnız karşılaştırma için raporlanmıştır. Validation’da Ridge seçilmiştir; bu, testte baseline’ı geçtiği anlamına gelmez. Üretim kabulü için hedef/tür bazında izinli MAE/RMSE aralıkları ve baseline karşısında gereken iyileşme eşiği gerçek test açılmadan önce işletme/veri sahibiyle yazılı belirlenmeli; bağımsız hayvan/lot/zaman holdoutunda her hedef bu önceden kayıtlı eşikleri sağlamalı, ölçüm standardı ve (kategoriler ayrık ise) kütle dengesi kalite kontrolleri geçmelidir. Bu eşikler henüz belirlenmedi ve saha testi yok; üretim onayı verilmedi.

## 5. Sentetik test metrikleri

Test bölümü `n=180` sentetik karkastan oluşur. Aşağıdaki MAE/RMSE tüm sekiz hedef değerleri düzleştirilerek kg cinsinden hesaplanmıştır; R² uniform-average’tir.

| Yöntem | MAE (kg) | RMSE (kg) | R² |
|---|---:|---:|---:|
| Tür ortalama oran baseline | 1.8283 | 3.4431 | 0.9027 |
| Ridge | 1.8439 | 3.4556 | 0.9022 |
| Random Forest | 1.9412 | 3.6900 | 0.8942 |

Bu sentetik testte baseline her iki adaydan da daha düşük hata ve biraz daha yüksek R² verdi. Hedef başına MAE/RMSE/R² `reports/synthetic_evaluation/model_b_candidate_metrics.csv` ve JSON’da bulunur. Sonuçlar yalnız simüle veride yöntem/pipeline karşılaştırmasıdır; gerçek fabrika performansı değildir ve üretim onayı vermez.

## 6. Lot izlenebilirliği ve geri çağırma

Merkezi backend’in şeması `lots`, `lot_genealogy_edges`, `production_inputs/outputs`, `butchering_inputs/outputs`, `stock_movements`, `shipment_lines`, `recall_lots` ve `recall_customer_impacts` tablolarını kesin sayısal kimlik/FK ilişkileriyle tanımlar. İzleme ve geri çağırma servisleri kayıtlı genealogy ile sevkiyatları sorgular; model tahmini ilişki kaynağı olarak kullanılmaz. `backend/tests/test_traceability_recall.py` kayıtlı üretim-lot-sevkiyat-geri çağırma akışını, bloklanan satış/sevkiyatı, mükerrer dispatch ve dispatch/recall yarışını kapsar. Ek olarak bilinmeyen lot, genealogy ilişkisi olmayan lotun sadece kendisi olarak dönmesi ve tekrar eden origin lot kodunun tek kayıt olarak ele alınması için bir test eklendi.

Model B audit tahmin kaydı yalnız tür ve karkas ağırlığı taşır; merkezi `lot_id` ile ilişkilendirilmemiştir. Dolayısıyla Model B tahmininden lot bağlantısı veya geri çağırma kapsamı çıkarılmaz. Bu turda backend’in MySQL test fixture’ı `localhost:3307/avatar_test` bağlantısını reddettiği için 5 traceability/recall testi setup aşamasında **ERROR** verdi; davranış geçer olarak doğrulanmış sayılmaz. Fixture başlamadan bağlantı başarısız oldu; veritabanı oluşturulmadı, truncate edilmedi ve gerçek veriye dokunulmadı. Test konfigürasyonu MySQL `CREATE DATABASE` ve tablo `TRUNCATE` işlemleri yapabildiğinden, tekrar denemede yalnızca ayrılmış ephemeral test DB kullanılmalıdır.

## 7. Güvenlik, artefakt bütünlüğü ve API

Önceki düzeltmelerde Model B production loader’ı manifest SHA-256’sını joblib deserialization öncesi doğrular; eksik/geçersiz hash, artefakt/manifest yokluğu, hash uyuşmazlığı, bundle/manifest sürüm farkı ve sentetik kaynak ret edilir. Hash kontrolü tek başına kaynağa güven veya bilimsel geçerlilik kanıtı değildir; manifest ve model aynı güvenilmeyen kaynaktan birlikte değiştirilirse yeni eşleşen hash üretilebilir. İmzalı manifest veya ayrı korunan dağıtım zinciri gereklidir; uygulanabilir tasarım, artifact SHA-256 ve canonical manifest içeriğini imzalayan Ed25519 özel anahtarını KMS/secret store’da tutmak ve API başlangıcında pinlenmiş güvenilir public key ile doğrulamaktır. Anahtar eklenmemiş veya imza doğrulama kodlanmamıştır.

`MODEL_B_DIR` ve `MODEL_B_AUDIT_DB` varsayılanları artık `ai/Model2/models` ve `ai/Model2/var/model_b_audit.sqlite3` konumlarına, çalışma dizininden bağımsız şekilde çözülür. Container’da uygulama `/app/Model1` düzeninde kalır; Compose ayrı Model1/Model2 bind mount’ları ve Model B audit DB için named volume tanımlar. Model2 modeller dizininde yalnız sentetik aday bulunuyor; production adıyla artefakt/manifest yok. API status Model B’yi hazır değil gösterir; prediction endpoint’i sentetik adayı kullanmaz ve `503` verir. API fixture testleri geçerli ölçülmüş bundle’ı yalnız izole test amacıyla kurar.

## 8. Test sonuçları ve Docker

AI kökünden, Model1 sanal ortamında tüm paket:

```powershell
$env:PYTHONPATH = "Model1"
.\Model1\.venv\Scripts\python.exe -m pytest -v -p no:cacheprovider
```

Sonuç: **43 passed, 0 failed, 0 skipped; 1 Starlette/httpx deprecation uyarısı; 4.59 saniye.** Model B API/egitim testleri içinde migration, default path, SHA-256, sentetik model reddi ve geçici SQLite prediction → actual → evaluation senaryoları yer aldı. Gerçek fabrika ölçümü yoktur.

`API_KEY` yalnızca config doğrulaması için geçici komut ortamında verilerek `docker compose -f Model1/docker-compose.yml config --quiet` **başarılı** oldu. Docker CLI mevcut, fakat Docker daemon `dockerDesktopLinuxEngine` named pipe’ında bulunamadı. Bu nedenle image build, container başlangıcı, health/status/prediction container testi yapılamadı. Compose parse başarısı container test başarısı değildir.

## 9. Tamamlananlar, kalan işler ve üretim koşulları

Tamamlananlar: Model2 varsayılan yol testi; Compose build context ve mounts; kaynak kökeni/sentetik ayrımı ve metriklerin raporlanması; önceki migration/hash güvenlik testlerinin korunması; Model2 API uçtan uca testinin yeniden çalıştırılması; Docker Compose yapılandırma parse kontrolü.

Kalanlar: Docker daemon ile build/smoke; MySQL backend testlerinin özel ephemeral test DB üzerinde çalıştırılması; gerçek hayvan/lot düzeyinde izinli ölçüm toplama, tartım zamanı/birimi/kategori standardı doğrulaması, grup bazlı bağımsız holdout ve baseline kıyası; üretim manifesti için imza/attestation ve yetkili dağıtım; Model B kayıtlarını lotla bağlamak istenirse AI tahminini recall kaynağı yapmadan ayrı, açık işletme tasarımı.

Saha verisi ve bağımsız doğrulama tamamlanana dek Model B yalnız sentetik araştırma/test prototipidir; operasyon, geri çağırma veya muhasebe kararı için hazır değildir.
