# API, veri ve Docker doğrulama raporu

## Sonuç özeti

- Tarih: 24.10.2026
- Komut: `.\.venv\Scripts\python.exe -m pytest -v` (`ai/Model1` çalışma dizininde)
- Python: 3.12.10; pytest: 8.4.2
- Sonuç: **56 passed, 0 failed** (24.10.2026 EKP karşılaştırma testleri dahil)
- Uyarı: Starlette TestClient’in mevcut `httpx` kullanımı için bir deprecation uyarısı. Bağımlılıklar değiştirilmedi.
- Başlangıçta normal pytest çağrısı Model2 import yolu nedeniyle 2 modülde collection hatası verdi (`ModuleNotFoundError: Model2`). `pytest.ini` içindeki `pythonpath` proje `ai` kökünü de kapsayacak şekilde düzeltildi; testler gevşetilmedi ve son normal çağrı 53/53 geçti.
- Veri sınırı: Model1 CSV’deki 1.000 kayıt sentetik/simüledir. API değerlendirme ve Docker HTTP örnekleri test verisidir; gerçek fabrika kaydı değildir.

## Test kapsamı

| Alan | Kontrol | Sonuç |
|---|---|---|
| API temel | `/health`, model status ve EKP hazır değil uyarısı | Geçti |
| Tahmin ve değerlendirme | Mevcut Model1 joblib dosyalarını gerçek yükleyip tahmin; tahmin/gerçekleşen çıktı ve EKP farkı (`tahmin - gerçekleşen`) | Geçti |
| İstek şeması | Eksik/fazla alan, yanlış tip, sayısal metin, boolean, NaN/sonsuz, negatif/sıfır ve geçersiz kategori | Geçti |
| Kimlik doğrulama | Anahtar eksik/yanlış; production ortamında anahtar yapılandırılmadığında fail-closed | Geçti |
| Model hatası | Eksik/bozuk modelde dosya yolu veya serialization ayrıntısı sızmadan 503 | Geçti |
| Model çıktısı | Sonlu olmayan, negatif EKP ve net çıktının tüm girdi kütlesini aşması halinde güvenli 503 | Geçti |
| Veri kalitesi | Şema, eksik/tekrar, sentetik etiketi, kütle dengesi, maliyet mutabakatı ve EKP formülü | Geçti |
| Model2 regresyonu | SQLite migration yolu, ölçüm ve kalıcı tahmin/değerlendirme akışı, manifest/hash/sentetik aday korumaları dahil Model2 testleri | Geçti |

## Docker / gerçek HTTP

- `docker compose config -q`: geçti.
- `docker compose build`: geçti; son build bağlamı 790 byte oldu ve `.dockerignore` yalnızca Dockerfile’ın kopyaladığı kaynakları tuttu.
- Model1 servisi yeniden oluşturuldu; backend veya diğer servisler durdurulmadı.
- `model1-avatar-ml-api-1`: `healthy`; `127.0.0.1:8001 -> 8000`.
- Sağlık ve model durumu GET endpoint’leri HTTP 200 verdi; EKP için `production_ready=false` kaldı.
- Container üzerinden sentetik test payload’ı ile `POST /v1/predict/production`: HTTP 200; çıktı 196,957 kg, EKP 941,71 TL/kg. Yanıtta EKP’nin hazır olmadığı uyarısı korundu.
- Aynı test akışında `POST /v1/evaluate/production`: HTTP 200; test gerçekleşeni 200 kg / 185.000 TL; gerçekleşen EKP 925 TL/kg; çıktı farkı -3,043 kg, EKP farkı +16,71 TL/kg. Farklar tahmin eksi gerçekleşen şeklindedir.
- Bilinmeyen bölge kategorisi: HTTP 422; değerlendirmede API anahtarı eksik: HTTP 401.
- Container root filesystem salt okunur; tüm Linux capability’leri düşürüldü ve `no-new-privileges` etkin. Model2 SQLite için yalnızca `model1_model_b_audit_data` named volume yazılabilir kaldı; volume silinmedi veya sıfırlanmadı.

## Kabul ve sınırlamalar

Model 1 EKP tahmini teknik API ve Docker üzerinde yanıt veriyor; bu güvenilirlik veya üretim uygunluğu kanıtı değildir. EKP Scenario A holdout iyileşmesi yalnızca %3,49 ve veri tamamen simüle. Gerçek saha verisiyle bağımsız, zamana göre ayrılmış dış doğrulama yapılmadı. Gerçek veriler, ölçüm zamanları ve muhasebe kuralları doğrulanana kadar EKP modeli üretime hazır değildir.

## EKP model karşılaştırması sonrası yeniden test — 24.10.2026

- Proje sanal ortamında python -m pytest -v: 56 passed, 0 failed, 1 Starlette/httpx deprecation warning.
- Yeni testler: allow-list dışı hedef/kayıp alanlarının feature transformer'a girmemesi, CSV'nin sentetik etiketi/formül kontrolü ve ayrı araştırma artefaktının yüklenip sonlu tahmin üretmesi.
- Docker daemon 29.9.2 erişilebilirdi; docker compose config -q başarılıydı; avatar-ml-api healthy durumdaydı.
- Gerçek HTTP health, model status, production prediction, evaluation çağrıları başarılıydı. Tahmin: 196,957 kg ve 941,71 TL/kg. Yalnız test için sentetik gerçekleşen 200 kg / 185.000 TL girildi; gerçekleşen EKP 925 TL/kg, farklar tahmin eksi gerçekleşen: çıktı -3,043 kg ve EKP +16,71 TL/kg.
- Status EKP production_ready=false uyarısını korudu. API anahtarı komut çıktısına veya rapora yazılmadı. Gerçek fabrika verisi kullanılmadı.
## Kapsam dışı backend regresyon kontrolü — 24.10.2026

- tests/test_traceability_recall.py, backend/.venv ile çalıştırıldı: 6 passed, 0 failed, bir Starlette/httpx deprecation uyarısı.
- Model1 sanal ortamındaki ilk deneme SQLAlchemy bulunmadığı için collection aşamasında durdu; backend’in kendi sanal ortamı kullanıldı.
- Fixture DATABASE_URL değerini ayrı avatar_test şemasına yönlendiriyor. Test Redis’i, backend’in docker-compose.test-redis.yml tanımından geçici olarak başlatıldı ve test sonunda kaldırıldı. Normal backend servisleri çalışır durumda bırakıldı.
## Gerçek veri hattı testleri — 24.10.2026

tests/test_production_data.py veri şeması, maliyet mutabakatı/EKP formülü, zero/negative/non-finite ve yanlış tipler, kayıt tekrarı, timestamp, preproduction feature gate, kayıp dengesi, boş şablonlar ve chronological split/gate kurallarını kapsar. Bu testlerdeki satırlar yalnız açıkça SENTETIK ORNEK olarak adlandırılan geçici bellek fixture'larıdır; kaynak dosyaya veya metrik raporuna eklenmemiştir. Detaylı pytest çıktısı final run raporuna eklenmiştir. Tam API suite ayrıca python -m pytest -v ile çalıştırılmıştır.

Gerçek parti verisi mevcut olmadığı için prediction accuracy veya gerçek fabrika API performansı değerlendirilmemiştir. Bu hattaki testlerin geçmesi yalnız kod ve iş kuralı denetimidir; saha doğrulaması değildir.
## Son tam pytest çalıştırması — 24.10.2026

- Model1 proje sanal ortamında python -m pytest -v: **78 passed, 0 failed**.
- Bu tam paket sonucu, rapordaki önceki 56 testlik anlık sonuçların yerini alır.
- Toplam 1 uyarı: Starlette TestClient'in mevcut httpx kullanımı deprecated; bağımlılıklar değiştirilmedi.
- Bu çalıştırmada 22 yeni production-data testinin tamamı geçti. Test fixture'ları açık SENTETIK ORNEK etiketli, yalnız test belleğinde kullanıldı.
- Gerçek üretim verisi bulunmadığından yeni zaman bazlı EKP hata metriği hesaplanmadı; API mevcut sözleşmesi değiştirilmedi.
