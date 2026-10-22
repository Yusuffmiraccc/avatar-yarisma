# AVATAR — Kabul Kriterleri

Bir özellik ancak ilgili kriterleri test eden otomatik testler geçerse tamamlanmış sayılır. Manuel deneme tek başına yeterli değildir.

## A. Genel API

- [ ] Tüm API yolları `/api/v1` altında ve OpenAPI'de görünür.
- [ ] Request/response alanları kaynak DTO sözleşmeleriyle uyumlu; JSON `snake_case`.
- [ ] Hatalar ortak zarf ve `request_id` içerir; beklenen HTTP kodları 401/403/404/409/422/500 testlidir.
- [ ] Pagination/filter biçimi tutarlı; liste endpoint'lerinde kararlı sıralama vardır.
- [ ] Para/miktar string, Decimal dönüşümü kayıpsızdır; float ile para hesabı yapılmaz.

## B. Veritabanı ve migration

- [ ] Her fiziksel tablo/kolonun ERD sözleşmesiyle parity kaydı vardır.
- [ ] PK/FK/unique/check/index/nullability/precision açıkça doğrulanmıştır.
- [ ] Boş MySQL 8.4 test DB'sine migration baştan sona uygulanır.
- [ ] İkinci migration çalıştırması no-op/idempotent davranır.
- [ ] Migration testleri üretim veya kullanıcı DB'sine bağlanmaz.
- [ ] Sentetik seed yeniden çalıştırıldığında kontrolsüz duplicate yaratmaz.

## C. Kimlik ve güvenlik

- [ ] Parola yalnız güçlü password hash ile saklanır.
- [ ] Access 15 dk, refresh 7 gün; refresh rotation ve token hash saklama uygulanır.
- [ ] Logout refresh session'ı iptal eder; refresh replay reddedilir.
- [ ] Disabled user'ın erişimi testli şekilde reddedilir.
- [ ] Her endpoint deny-by-default permission kontrolünden geçer; izin matrisi ile parity vardır.
- [ ] Secret, token, parola ve hassas payload loglarda görünmez.

## D. Stok defteri

- [ ] Stok hareketi miktarı pozitif; yön yalnız `IN`/`OUT`.
- [ ] Movement ve balance aynı transaction'da yazılır; herhangi bir hata ikisini de rollback eder.
- [ ] Bakiye doğrudan düzenlenemez; düzeltme hareketi ve audit gerekir.
- [ ] Yasaklı negatif stok/lot-block çıkışları reddedilir.
- [ ] Aynı kritik komutun tekrarında duplicate hareket oluşmaz.

## E. Üretim

- [ ] `IN_PROGRESS` stok hareketi yaratmaz.
- [ ] Completion tüketim OUT, bitmiş ürün IN, genealogy, maliyet ve audit'i tek transaction'da yazar.
- [ ] Herhangi bir adım başarısızsa tamamı rollback olur.
- [ ] Referans senaryoda maliyet toplamı €1,543.50, 85 paket için EKP yaklaşık €18.16'dır; hesaplanan tam hassasiyet ve yuvarlama ayrıca testlidir.

## F. Parçalama/fire

- [ ] Çıktılar lotlu stok girişi alır; fire kaydı stok IN üretmez.
- [ ] Ağırlık dengesi ve tolerans davranışı testlidir; fark sessizce normalize edilmez.
- [ ] Fire kaynağı tek bir input/source lota bağlıdır; birden fazla input için ayrı fire satırları kullanılır.
- [ ] `BY_WEIGHT` dağıtımı ve rounding residual toplamı korur.
- [ ] `BY_VALUE` değerleme tabanı yoksa işlem fail-closed olur.
- [ ] Kaynak verilerindeki aritmetik tutarsızlıklar raporlanır, neden uydurulmaz.

## G. Satış ve sevkiyat

- [ ] Sale kaydı tek başına fiziksel stok düşürmez.
- [ ] Dispatch/sevkiyat fiziksel stok OUT'un tek sahibidir.
- [ ] Aynı `Idempotency-Key` + aynı gövde ilk sonucu verir.
- [ ] Aynı anahtar + farklı gövde 409 verir.
- [ ] Duplicate/concurrent dispatch ikinci OUT yaratmaz.

## H. Lot genealogy ve recall

- [ ] Kaynak lot → üretim/parçalama → bitmiş lot → sevkiyat → müşteri/market ilişkisi miktarlarıyla izlenir.
- [ ] Recall raporu etkilenen lotları, müşterileri/marketleri ve gönderilen miktarları gösterir.
- [ ] Recall aktivasyonu atomik ve eşzamanlı stok çıkışıyla güvenlidir.
- [ ] Aktif recall sonrası yeni stok çıkışı reddedilir.
- [ ] Recall `RESOLVED` olduğunda blokaj kalır; ayrı yetkili release ve audit olmadan kalkmaz.
- [ ] İkinci kademe dağıtım kaydı yoksa icat edilmez.

## I. Audit ve düzeltme

- [ ] Kritik tamamlanmış kayıtlar hard-delete edilmez.
- [ ] Correction/reversal kaynak kaydı, gerekçe, yetki, ters hareket ve audit içerir.
- [ ] Audit yazımı başarısız olduğunda kritik işlem için tutarlılık davranışı failure-injection testiyle doğrulanır.

## J. AI

- [ ] En az bir baseline ve değerlendirme metriği vardır.
- [ ] Model/version, tahmin girdisi özeti, prediction, varsa actual, metrik ve status kaydedilir.
- [ ] Veri azsa sınırlamalar açıkça raporlanır.
- [ ] ML arızası stok/traceability/recall akışlarını bozmaz.
- [ ] AI tahmini gerçek stok/lot bilgisinin yerine geçmez.

## K. Teslim ve çalıştırma

- [ ] Temiz checkout'tan README talimatlarıyla lokal sistem başlatılır.
- [ ] `.env.example` vardır; gerçek secret yoktur.
- [ ] Docker Compose, migration, seed, test ve demo komutları belgelenmiştir.
- [ ] Unit/integration/contract/concurrency/E2E test sonuçları raporlanmıştır.
- [ ] Bilinen sınırlamalar ve tamamlanmayan işler saklanmadan listelenmiştir.
