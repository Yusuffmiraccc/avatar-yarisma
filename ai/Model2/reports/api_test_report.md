# Model B API ve uçtan uca test raporu

Son doğrulama: 24.10.2026. Gerçek saha verisi kullanılmadı; API akışındaki başarılı measured bundle yalnız test fixture'ıdır.

## Ortam ve test sonucu

- Python 3.12.10, pytest 8.4.2; mevcut ortam `ai/Model1/.venv`.
- Komut (AI kökünden):

```powershell
$env:PYTHONPATH = "Model1"
.\Model1\.venv\Scripts\python.exe -m pytest -v -p no:cacheprovider
```

- **43 passed, 0 failed, 0 skipped; 1 uyarı; 4.59 saniye.**
- Uyarı: Starlette TestClient/httpx entegrasyonu için deprecation uyarısı (`httpx2` önerisi). Bu görevde bağımlılık değiştirilmedi.

Düzeltmeden önce başarısız olan üç test ayrı yeniden çalıştırıldığında **3 passed**. Model B test dosyaları ayrıca **28 passed** (2.82 saniye).

## Kapsam

- Eski migration yolu hatasının `ai/Model2/sql/001_model_b_audit.sql` konumuyla giderilmesi ve çalışma dizini değişse de yolun sabit kalması.
- Migration dosyası yok/okunamaz olduğunda anlaşılır `sqlite3.OperationalError`.
- Sentetik aday için SHA-256 sidecar manifest üretimi; dosya hash'inin manifestteki değerle eşleşmesi.
- Production manifestte hash eşleşmesiyle model yükleme; hash uyuşmadığında ve hash eksik olduğunda `joblib.load` çağrılmadan ret.
- Model bundle/manifest model sürümü uyuşmazlığını ret.
- `source_type=synthetic` ve `production_ready=false` manifestini deserialize öncesi ret; sentetik aday adı/konumu production endpoint'inde kabul edilmez.
- Production artefakt/manifest olmadığında status hazır değil ve tahmin 503.
- Geçici test modeli ile tahminin SQLite'a yazılması; actual ölçümün aynı prediction ID'ye ayrı kaydı; saat diliminin UTC'ye çevrilmesi; tahmin-gerçekleşen fark işareti; bilinmeyen ID, duplicate actual ve actual yokken evaluation davranışı.
- Model A mevcut tahmin ve assessment örnek testleri de tüm paket içinde geçti.

Uçtan uca SQLite DB yalnız `tmp_path` içinde oluşturuldu. Gerçek veya kullanıcı DB'si açılmadı/sıfırlanmadı. Uçtan uca tahmin → actual → evaluation testi başarılı oldu; test değerleri gerçek saha ölçümü değildir.

## SHA-256 davranışı ve sınırı

API status manifest ile artifact'ın hash eşleşmesini joblib yüklemeden kontrol eder. Prediction loader, deserialize öncesi aynı açık dosya tanıtıcısındaki baytları yeniden hash'ler ve aynı tanıtıcı üzerinden `joblib.load` yapar. Hash eksik/geçersiz/uyuşmazsa fail-closed olur. Önceki hash'siz production manifestleri otomatik dönüştürülmez; yeni ve yetkili bir manifest yayımlanana kadar API 503 verir.

SHA-256 dosya byte bütünlüğünü denetler; model kaynağının güvenilir, izinli veya bilimsel olarak doğrulanmış olduğunu kanıtlamaz. Saldırgan manifest ve modeli birlikte değiştirebiliyorsa eşleşen yeni hash üretebilir. Üretim için imzalı manifest/attestation veya manifesti artefakttan ayrı koruyan yetkili dağıtım kanalı gerekir.

## Docker ve saha doğrulaması

Docker CLI/Compose var, fakat `docker info` `dockerDesktopLinuxEngine` named pipe'ına erişemedi. Compose/build/container testleri yapılamadı. Uvicorn/TestClient sonuçları Docker container testi yerine geçmez. Gerçek Model B production artefaktı ve saha ölçümleri yoktur; üretime hazır değildir.

Tam değerlendirme ve kalan konfigürasyon notları `reports/comprehensive_audit.md` içindedir.


Güncel AI tam paket komutu `-p no:cacheprovider` ile (test cache klasörüne yazmadan) çalıştırıldı. Lot/geri çağırma backend testleri ayrı denemede 5 setup hatası verdi: mevcut beş test `localhost:3307/avatar_test` MySQL'ine bağlanamadığı için setup aşamasında ERROR verdi (connection refused). Ardından bilinmeyen lot, ilişkisiz lot ve tekrar eden recall origin için altıncı test eklendi; MySQL engeli nedeniyle çalıştırılamadı. Bu testler başarılı raporlanmadı; fixture mevcut MySQL'e bağlanırsa DB create/truncate işlemi yaptığı için yalnız ephemeral test DB ile çalıştırılmalıdır.
