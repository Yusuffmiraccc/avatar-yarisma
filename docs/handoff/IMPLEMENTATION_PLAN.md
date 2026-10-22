# AVATAR — Uygulama Planı

Bu plan kod yazacak LLM için çalışma sırasıdır. Bir fazın tamamlanması, ilgili testler gerçekten çalıştırılıp sonuçları kaydedilmeden ilan edilmemelidir.

## Faz 0 — Repo ve sözleşme envanteri

- Mevcut `backend/` iskeletini incele; bağımlılıkları ve çalışma komutlarını doğrula.
- ERD alanlarını, DTO'ları, endpoint imzalarını, permission manifestini ve workflow'ları tek parity matrisiyle eşleştir.
- Kaynakta mevcut olmayan tablo/kolon/endpoint uydurma; farkları `KNOWN_GAPS.md`'ye yaz.
- Çıktı: parity matrisi, güncellenmiş açık konu listesi, test komutları.

## Faz 1 — DB altyapısı ve ORM

- SQLAlchemy modellerini ayrıntılı ERD/alan sözleşmelerine göre oluştur.
- Naming convention, PK/FK, unique/check/index, on-delete davranışı ve Decimal türlerini uygula.
- `roles`, `user_roles`, `idempotency_records` dahil auth/retry tablolarını sözleşmeyle eşleştir.
- MySQL 8.4 uyumluluğunu kontrol et; yalnız izole test DB kullan.
- Çıktı: ORM metadata, ilk Alembic migration, migration upgrade smoke test, schema parity testi.

## Faz 2 — Ortak altyapı

- Settings, DB session, transaction pattern, logging/request ID, hata zarfı, pagination/filter conventions.
- Secret'ları loglama; `.env.example` içinde yalnız placeholder değerler.
- Liveness/readiness ayrımını kur: liveness DB gerektirmesin; readiness DB bağlantısını kontrol etsin.
- Çıktı: ortak testler ve OpenAPI smoke test.

## Faz 3 — Kimlik doğrulama ve yetki

- Parola hash'i, login, access token 15 dk, refresh 7 gün, refresh rotation ve token hash saklama.
- Logout refresh session'ı revoke eder; disabled user davranışı açıkça test edilir.
- Rol/permission kontrolü endpoint bazında; varsayılan olarak izin verme (deny-by-default).
- Çıktı: 401/403, refresh replay, logout, disabled-user, permission matrix testleri.

## Faz 4 — Referans verileri ve lot/stok

- Products, units/conversions, suppliers/customers, lots, balances, stock movement ledger.
- Bakiye güncellemesi yalnız servis katmanında, movement ile aynı transaction'da.
- Negatif stok, lot block, duplicate business code, idempotent command testleri.
- Çıktı: stok defteri/bakiye tutarlılık testleri.

## Faz 5 — Üretim ve maliyet

- Production order, inputs, outputs, service costs, EKP calculations.
- `IN_PROGRESS` stok değiştirmez; completion tüm tüketim/çıktı/genealogy/cost/audit işlemlerini atomik yapar.
- Başarısız adımda rollback testi.
- Çıktı: 100 kg et, 2 kg baharat, 5 kg kılıf, 85 paket ve 85 × €5.50 hizmet bedelli referans senaryo; toplam €1,543.50 ve yaklaşık €18.16/paket hesabını test et.

## Faz 6 — Parçalama ve fire

- Butchering inputs/outputs/waste; çıktılar lotlu stok, fire ayrı kayıttır ve stok girişi yaratmaz.
- Ağırlık dengesi, tolerans konfigürasyonu, gerekçe/audit.
- `BY_WEIGHT` dağıtımı ve yuvarlama uzlaşması testleri; `BY_VALUE` güvenilir değerleme yoksa fail-closed.
- Kaynak örneğinde 25 kg × €11.50 = €287.50 aritmetiğini koru; €351 kaynak toplamıyla tutarsızlığı açıkça raporla, neden uydurma.
- Çıktı: fire/weight/cost allocation testleri.

## Faz 7 — Satış, sevkiyat ve idempotency

- Sale/sale lines ticari kayıttır; fiziksel stok OUT yalnız dispatch/shipment yapar.
- `Idempotency-Key` aynı gövde/aynı sonuç; farklı gövde 409.
- Çıktı: duplicate dispatch/sale, stock movement uniqueness, concurrent dispatch testleri.

## Faz 8 — Genealogy, recall ve audit

- Lot genealogy miktarlı çoktan-çoğa; recall hangi müşteri/marketlere ne miktar gittiğini raporlar.
- Recall aktivasyonu ve stok çıkışı aynı lot/balance/block kayıtlarını tutarlı sırada kilitler; yarış koşulunda stok çıkışı recall sonrası geçemez.
- Recall `RESOLVED` blokajı otomatik kaldırmaz; yetkili release komutu gerekir.
- Çıktı: recall race integration testleri ve ET-2026-001 demo senaryosu.

## Faz 9 — AI tahminleri

- Üretim yield/EKP tahmini ve butchering output weight tahmini.
- Baseline, train/evaluation ayrımı, hata metrikleri, model/version, input summary ve prediction status.
- Az veri durumunda belirsizliği açıkla; model hatası operasyonel transaction'ı engellemez.
- Çıktı: tekrarlanabilir sentetik/izinli veri testleri ve model evaluation raporu.

## Faz 10 — Son doğrulama ve devir

- Tüm unit/integration/contract/concurrency/E2E testleri.
- OpenAPI endpoint/DTO/permission matrisi ile parity.
- Temiz ortamda Docker Compose başlangıcı, migration ve sentetik seed doğrulaması.
- README: kurulum, `.env`, migrate, seed, test, demo ve troubleshooting.
- Teslim raporu: test komutları ve gerçek çıktılar, kalan bilinen sınırlamalar, sürüm/commit.

## Her fazın zorunlu kapanış raporu

1. Değişen dosyalar.
2. Çalıştırılan komutlar.
3. Test sonuçları (sayı ve başarısızlıklar dahil).
4. Migration/DB etkisi; test DB dışında işlem yapılmadığı teyidi.
5. `KNOWN_GAPS.md` içindeki güncellenen maddeler.
6. Sonraki faz için kalan engeller.
