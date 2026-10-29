# AVATAR — Kabul Kriterleri ve Tamamlanma Durumu

Bu belge, AVATAR Yapay Zekâ Yarışması değerlendirme kriterlerinin her biri için mevcut depodaki tamamlanma ve doğrulama durumunu gösterir.

---

## A. Genel API

- [x] Tüm API yolları `/api/v1` altında ve OpenAPI'de görünür (`contract/openapi.json`).
- [x] Request/response alanları kaynak DTO sözleşmeleriyle uyumlu; JSON `snake_case`.
- [x] Hatalar ortak zarf ve `request_id` içerir; beklenen HTTP kodları 401/403/404/409/422/500 testlidir.
- [x] Pagination/filter biçimi tutarlı; liste endpoint'lerinde kararlı sıralama vardır (`id DESC`).
- [x] Para/miktar string, Decimal dönüşümü kayıpsızdır; float/Double ile para hesabı yapılmaz.

## B. Veritabanı ve Migration

- [x] Her fiziksel tablo/kolonun ERD sözleşmesiyle parity kaydı vardır (`docs/DATA_MODEL.md`).
- [x] PK/FK/unique/check/index/nullability/precision açıkça tanımlanmıştır (MySQL 8.4 ve SQLite uyumlu).
- [x] Boş MySQL 8.4 test DB'sine migration Alembic ile baştan sona uygulanır.
- [x] İkinci migration çalıştırması no-op/idempotent davranır.
- [x] Migration testleri üretim veya kullanıcı DB'sine bağlanmaz (`avatar_test` izole veritabanı).
- [x] Sentetik seed yeniden çalıştırıldığında kontrolsüz duplicate yaratmaz (`scripts.seed_demo` idempotency kontrolü).

## C. Kimlik ve Güvenlik

- [x] Parola yalnız güçlü password hash (Argon2id) ile saklanır.
- [x] Access 15 dk, refresh 7 gün; refresh rotation ve token hash saklama uygulanır.
- [x] Logout refresh session'ı iptal eder; refresh replay aile iptali ile reddedilir.
- [x] Disabled user'ın erişimi token sürümü ve aktiflik kontrolüyle anında reddedilir.
- [x] Her endpoint deny-by-default permission kontrolünden geçer; izin matrisi ile parity vardır.
- [x] Secret, token, parola ve hassas payload loglarda görünmez (`logging_mw.py`).

## D. Stok Defteri

- [x] Stok hareketi miktarı pozitif; yön yalnız `IN`/`OUT`.
- [x] Movement ve balance aynı transaction'da yazılır; herhangi bir hata ikisini de rollback eder.
- [x] Bakiye doğrudan düzenlenemez; düzeltme hareketi ve audit gerekir.
- [x] Yasaklı negatif stok/lot-block çıkışları veritabanı kısıtlarıyla reddedilir.
- [x] Aynı kritik komutun tekrarında duplicate hareket oluşmaz.

## E. Üretim

- [x] `IN_PROGRESS` aşaması stok hareketi yaratmaz.
- [x] Completion tüketim OUT, bitmiş ürün IN, genealogy, maliyet ve audit'i tek transaction'da yazar.
- [x] Herhangi bir adım başarısızsa tamamı rollback olur.
- [x] Referans senaryoda maliyet toplamı €1.543,50, 85 paket için EKP 18,1588 € (gösterim 18,16 €); tam hassasiyet ve yuvarlama test edilmiştir (`test_costing.py`).

## F. Parçalama / Fire

- [x] Çıktılar lotlu stok girişi alır; fire kaydı stok IN üretmez (`butchering_waste_records`).
- [x] Ağırlık dengesi ve tolerans davranışı testlidir; fark sessizce normalize edilmez (`weight_variance_records`).
- [x] Fire kaynağı tek bir input/source lota bağlıdır; birden fazla input için ayrı fire satırları kullanılır.
- [x] `BY_WEIGHT` dağıtımı ve rounding residual toplamı korur (artık son satıra aktarılır).
- [x] `BY_VALUE` değerleme tabanı yoksa işlem fail-closed olur.
- [x] Kaynak verilerindeki aritmetik tutarsızlıklar (287,50 € ≠ 351,00 €) açıkça raporlanır, neden uydurulmaz.

## G. Satış ve Sevkiyat

- [x] Sale kaydı tek başına fiziksel stok düşürmez.
- [x] Dispatch/sevkiyat fiziksel stok OUT'un tek sahibidir.
- [x] Aynı `Idempotency-Key` + aynı gövde ilk sonucu verir.
- [x] Aynı anahtar + farklı gövde 409 `IDEMPOTENCY_KEY_REUSED` verir.
- [x] Duplicate/concurrent dispatch ikinci OUT yaratmaz.

## H. Lot Genealogy ve Geri Çağırma (Recall)

- [x] Kaynak lot → üretim/parçalama → bitmiş lot → sevkiyat → müşteri/market ilişkisi miktarlarıyla izlenir.
- [x] Recall raporu etkilenen lotları, müşterileri/marketleri (Market A: 30, B: 25, C: 30) ve miktarları gösterir.
- [x] Recall aktivasyonu atomik ve eşzamanlı stok çıkışıyla güvenlidir (`SELECT ... FOR UPDATE`).
- [x] Aktif recall sonrası yeni stok çıkışı `409 LOT_BLOCKED` ile reddedilir.
- [x] Recall `RESOLVED` olduğunda blokaj kalır; ayrı yetkili release (`lots:unblock`) olmadan kalkmaz.
- [x] İkinci kademe dağıtım kaydı yoksa icat edilmez.

## I. Audit ve Düzeltme

- [x] Kritik tamamlanmış kayıtlar hard-delete edilmez.
- [x] Correction/reversal kaynak kaydı, gerekçe, yetki, ters hareket ve audit içerir.
- [x] Audit yazımı başarısız olduğunda kritik işlem için tutarlılık davranışı fail-closed olarak uygulanır.

## J. Yapay Zekâ (AI)

- [x] En az bir baseline (`BASELINE_MEAN`, `BASELINE_ANIMAL_MEAN`) ve değerlendirme metrikleri (MAE, RMSE, MAPE, R²) vardır.
- [x] Model/version, tahmin girdisi özeti, prediction, varsa actual, metrik ve status kaydedilir (`ml_predictions`).
- [x] Veri azsa sınırlamalar açıkça raporlanır (sentetik DEMO veri şeffaflığı).
- [x] ML arızası stok/traceability/recall akışlarını bozmaz (yumuşak hata toleransı).
- [x] AI tahmini gerçek stok/lot bilgisinin yerine geçmez (yalnızca karar desteğidir).

## K. Teslim ve Çalıştırma

- [x] Temiz checkout'tan README talimatlarıyla lokal sistem başlatılır.
- [x] `.env.example` vardır; gerçek secret repoya commit edilmemiştir.
- [x] Docker Compose, migration, seed, test ve demo komutları belgelenmiştir (`docs/DEMO.md`).
- [x] Unit/integration/contract/concurrency/E2E test sonuçları raporlanmıştır (`docs/TEST_REPORT.md`).
- [x] Bilinen sınırlamalar ve çalışma ortamı kısıtları açıkça raporlanmıştır.
