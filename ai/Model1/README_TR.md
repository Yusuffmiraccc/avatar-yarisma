> **Durum: deneysel.** Teslim edilen yapay zeka çalışması (A: üretim verimi/EKP, B: parçalama) `backend/app/ml` içindedir ve backend ile entegredir. Bu klasör ayrı bir ön çalışmadır; backend tarafından çağrılmaz, `ai_*` tabloları Alembic migration'ının dışındadır. "Aday model yalnızca aktif modelden iyiyse devreye girer" kuralı `app/ml/service.py` içine taşındı.

# AVATAR Model 1 — Üretim Tahmini, EKP ve Eşik Tabanlı Yeniden Eğitim

Bu proje AVATAR değerlendirme projesindeki **Model 1** için bağımsız Python ML servisi başlangıcıdır. İki veri akışı birbirinden ayrılmıştır:

1. `Manufacturing_Inventory_Analytics` veri seti, genel imalat verisinde veri işleme hattını ve benchmark modelini denemek içindir. Bu veri fan/ısıtıcı üretimine aittir; sucuk üretiminde doğrulanmış tahmin olarak kullanılamaz.
2. Gerçek AVATAR Model 1'i yalnızca backend'den gelen **tamamlanmış, doğrulanmış, gerçek üretim emirleri** ile eğitilir. Bu model için ilk eğitimden önce en az 100 gerçek üretim kaydı toplanmalıdır. Sonraki yeniden eğitim denemeleri, bir önceki eğitim denemesinden sonra 50 yeni uygun üretim kaydı biriktiğinde otomatik kuyruğa alınır.

Yeni bir tahmin kaydı, tek başına eğitim verisi değildir. Satışlar da kendi lot/stok tablolarında saklanır; üretim verimi modeline yalnızca üretim emri tamamlandığında doğrulanan üretim sonucu gönderilir.

## Klasörler

- `data/raw/`: yalnızca indirilen genel imalat benchmark CSV'leri. Orijinal dosyalar değiştirilmez.
- `data/processed/`: hazırlanmış geçici veri dosyaları.
- `src/`: veri indirme/denetim, benchmark modeli, gerçek AVATAR modeli eğitimi, REST API ve yeniden eğitim worker'ı.
- `models/`: gerçek AVATAR modelinin sürümlenmiş `.joblib` artifact dosyaları. Git'e eklenmemelidir.
- `reports/`: denetim ve model değerlendirme raporları.
- `sql/001_ai_tables_mysql.sql`: merkezi MySQL'e kurulacak AI kayıt, tahmin, model kayıt ve iş kuyruğu tabloları.
- `tests/`: maliyet hesaplama ve yeniden eğitim eşiği testleri.

## Kurulum (Windows PowerShell)

Proje yolunun `D:\Coding\AVATAR Project\ai\Model1` olduğunu varsayar:

```powershell
cd "D:\Coding\AVATAR Project\ai\Model1"
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Bypass komutu sadece mevcut PowerShell süreci için geçerlidir. Aktivasyon istemezsen doğrudan `\.venv\Scripts\python.exe` ile de komut çalıştırabilirsin.

## A. Genel imalat benchmark verisini indirme ve denetleme

```powershell
python src/download_data.py
python src/audit_data.py
python src/train_production_model.py
python src/predict.py --planned-quantity 400 --product-id P005 --shift Morning --production-line "Line 2"
```

Bu benchmark eğitimi yalnızca teknik deneme içindir. Gerçek AVATAR API'si bu benchmark artifact'ını kullanmaz.

## B. Otomatik yeniden eğitim nasıl çalışacak?

### Eşikler

- İlk gerçek AVATAR modeli: **en az 100** tamamlanmış + doğrulanmış gerçek üretim emri.
- Her sonraki eğitim denemesi: son eğitim **denemesinden sonra en az 50 yeni** tamamlanmış + doğrulanmış gerçek üretim emri.
- Worker her uygun işi MySQL kuyruğundan alır ve eğitimi arka planda yürütür.
- Eğitimde üretim tarihine göre zaman sıralı holdout kullanılır. Linear Regression ve Random Forest karşılaştırılır.
- Aday modelin holdout MAE'si, `meat_kg / package_weight_kg` referans yönteminden düşük olmalıdır. Aktif model varsa aday aynı holdout üzerinde aktif modelden de daha düşük MAE elde etmelidir.
- Aday bu koşulları geçemezse **aktif model korunur**; reddedilen aday production'a alınmaz. Yeni eşik miktarında kayıt geldikten sonra sistem yeni bir deneme kuyruğa alabilir.

Eşikler `.env` içindeki `AVATAR_MIN_INITIAL_RECORDS` ve `AVATAR_RETRAIN_NEW_RECORDS` değişkenleriyle değiştirilebilir. Varsayılanlar 100 ve 50'dir. Bu eşikler proje için başlangıç iş kuralıdır; istatistiksel yeterlilik garantisi değildir.

## C. MySQL tablolarını kurma

1. `.env.example` dosyasını `.env` olarak kopyala.
2. `AVATAR_DATABASE_URL` değerini gerçek MySQL bağlantınla değiştir.
3. `AVATAR_AI_API_KEY` için güçlü, rastgele bir anahtar oluştur.
4. `sql/001_ai_tables_mysql.sql` dosyasını **AVATAR'ın kullandığı MySQL veritabanında** çalıştır.

Örnek URL:

```text
mysql+pymysql://avatar_user:PAROLANI_DEGISTIR@127.0.0.1:3306/avatar_db?charset=utf8mb4
```

Gerçek parolanı `.env` dışında koda yazma ve `.env` dosyasını Git'e ekleme.

## D. API ve worker'ı çalıştırma

İki ayrı PowerShell penceresi aç. İkisinde de proje klasörüne geç ve `.venv`'i etkinleştir.

**Terminal 1 — REST API:**

```powershell
uvicorn src.api:app --host 127.0.0.1 --port 8001
```

**Terminal 2 — otomatik eğitim işçisi:**

```powershell
python -m src.retraining_worker
```

Worker MySQL'deki `ai_retraining_jobs` tablosunu 5 saniyede bir kontrol eder. API'ye kayıt geldikten sonra eşik karşılanırsa iş otomatik kuyruğa alınır ve worker başlatır. API veya worker kapalıysa otomatik süreç çalışmaz. Gerçek dağıtımda servisleri Windows service/container/process manager ile sürekli çalışır durumda tut ve API'yi internete doğrudan açma.

Sağlık kontrolü:

```text
GET http://127.0.0.1:8001/health
```

API anahtarı gerektiren model durumu:

```text
GET http://127.0.0.1:8001/ai/model/status
Header: X-API-Key: .env içindeki anahtar
```

## E. Ana AVATAR backend'inin bağlanması

Bu paket, backend uygulamasının kendi üretim tamamlanma kodunu otomatik değiştiremez; o backend'in kaynak kodu bu klasörde değil. Entegrasyon sözleşmesi hazırdır ve ana backend'den aşağıdaki çağrılar yapılmalıdır:

- Üretim öncesi tahmin: `POST /ai/production-forecast`
- Üretim emri tamamlanıp gerçek değerler doğrulandıktan sonra: `POST /ai/production-records`
- Durum kontrolü: `GET /ai/model/status`

Backend, ilk endpoint'e tahmin anında bilinen verileri (et, baharat, bağırsak, paket ağırlığı, planlanan maliyetler ve reçete türü) gönderir. İkinci endpoint'e yalnızca üretim gerçekten bitip onaylandıktan sonra gerçek paket sayısını ve gerçek maliyetleri gönderir. API bu kaydı `ai_production_training_records` tablosuna idempotent şekilde kaydeder ve varsa ön tahmini gerçek sonuçla eşleştirir.

### `POST /ai/production-forecast` istek örneği

```json
{
  "production_order_id": "URT-2026-045",
  "recipe_variant": "Narin Sucuk",
  "meat_kg": 100,
  "spice_kg": 2,
  "casing_kg": 5,
  "package_weight_kg": 1,
  "planned_material_cost_eur": 1076,
  "planned_service_cost_eur": 467.5
}
```

### `POST /ai/production-records` tamamlanmış kayıt örneği

```json
{
  "production_order_id": "URT-2026-045",
  "production_date": "2026-10-22",
  "recipe_variant": "Narin Sucuk",
  "meat_kg": 100,
  "spice_kg": 2,
  "casing_kg": 5,
  "package_weight_kg": 1,
  "planned_material_cost_eur": 1076,
  "planned_service_cost_eur": 467.5,
  "actual_package_count": 85,
  "actual_material_cost_eur": 1076,
  "actual_service_cost_eur": 467.5
}
```

Bu JSON'lar **API sözleşmesini gösteren örneklerdir**, gerçek veritabanı kayıtları değildir. Gerçek örnekteki maliyetlerin gerçekleşen tutarlar olduğu doğrulanmalıdır. Üretim kaydı ve tahmin aynı `production_order_id` ile ilişkilendirilir. Gerçek EKP, gerçekleşen maliyetlerin gerçek paket sayısına bölünmesiyle hesaplanır.

İki endpoint de `X-API-Key` başlığı ister. Ana backend'in üretim tamamlanma handler'ına POST çağrısı eklenmeden veriler otomatik akmaz. Satış olayı doğrudan eğitim kaydı oluşturmaz; satış/lot/stok hareketleri AVATAR ana sisteminde kendi tablolarında saklanmaya devam eder.

## F. Model ve yeniden eğitim sonuçları

- `ai_production_training_records`: doğrulanmış gerçek üretim emri girdileri ve hedefi.
- `ai_production_predictions`: tahmin anındaki girdi anlık görüntüsü, model sürümü, tahmin edilen miktar/EKP ve sonradan hesaplanan hata.
- `ai_retraining_jobs`: kuyruğa alınan, çalışan, yayınlanan, reddedilen veya başarısız olan eğitim işleri.
- `ai_model_registry`: model artifact dosyası, sürümü ve doğrulama metrikleri; aktif model bu kayıtta işaretlenir.
- `ai_retraining_state`: son deneme/eğitim zamanı ve aktif model bilgisi.

Bu proje aktif bir adayın doğrudan her satış sonrası değiştirilmesini yapmaz. Gerçek üretim verisi saklanır; eşik dolunca bir aday eğitilir ve değerlendirilir. Yeterli performans göstermeyen aday reddedilir, mevcut model korunur.

## G. Testler

```powershell
python -m unittest discover -s tests -v
python -m compileall -q src tests
```

Testler iş kuralı ve maliyet fonksiyonunu doğrular. MySQL entegrasyonunu tam doğrulamak için yerel bir MySQL veritabanında migration'ı uygulayıp API/worker uçtan uca testleri de çalıştırılmalıdır.

## Veri ve model sınırları

- 100/50 eşikleri operasyonel başlangıç değeridir; gerçek işletme verisinin istatistiksel niteliğine göre yeniden değerlendirilmelidir.
- Model yalnızca doğru, tamamlanmış ve doğrulanmış gerçek üretim kayıtlarını kullanmalıdır. Gerçek kayıtların yanlış etiketlenmesi API kimlik doğrulamasıyla tek başına engellenemez; ana backend çağrıyı yalnızca uygun üretim onayından sonra yapmalıdır.
- Birim maliyet formülü ML değil, deterministik iş kuralıdır.
- Lot izlenebilirliği ve geri çağırma sonuçları ML tahminine değil, kesin kayıt ilişkilerine dayanır.
