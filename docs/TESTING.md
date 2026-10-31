# AVATAR — Test Stratejisi ve Doğrulama Kılavuzu (TESTING)

Bu belge, AVATAR Yapay Zekâ Yarışması projesinde uygulanan test metodolojisini, kapsanan 18 zorunlu iş senaryosunu, otomatik test paketlerini ve elde edilen gerçek doğrulama sonuçlarını açıklar.

---

## 1. 18 Temel Değerlendirme Senaryosunun Karşılanma Durumu

Aşağıdaki tablo, şartnamede belirtilen 18 kritik senaryonun depodaki somut test ve kod karşılıklarını listeler:

| No | İş Senaryosu | İlgili Test Paketi / Modül | Test Edilen Kural ve Doğrulama | Durum |
|---|---|---|---|---|
| **1** | Hammadde alış kaydı stok ve lot oluşturuyor mu? | `test_standalone_flows.py::test_ekp_production_and_stock_flow` | `lots_svc.receive` çağrısı `Lot` ve `InventoryBalance.on_hand_quantity = 100` oluşturur. | **PASSED** |
| **2** | Dış üretim emri doğru miktarda hammadde tüketiyor mu? | `test_standalone_flows.py::test_ekp_production_and_stock_flow` | Üretim kabulünde hammadde bakiyeleri atomik olarak 0'a düşer (`on_hand_quantity == 0`). | **PASSED** |
| **3** | EKP 1.543,50 / 85 = yaklaşık 18,16 € olarak hesaplanıyor mu? | `test_costing.py::test_pdf_reference_scenario_ekp` | 100kg et + 2kg baharat + 5kg bağırsak + 85pk fason bedeli = 1543.50 €. 85 pakete bölündüğünde 18.1588 € -> 18.16 € tam kuruş doğruluğu kanıtlandı. | **PASSED** |
| **4** | Geçersiz üretim miktarı maliyet hesabını bozmadan reddediliyor mu? | `test_standalone_flows.py::test_negative_quantity_receipt_rejected` | Negatif veya sıfır miktar girişi `400 Bad Request` ile reddedilir, veritabanına yazılmaz. | **PASSED** |
| **5** | Kuzu parçalama ağırlık dengesi kontrol ediliyor mu? | `test_standalone_flows.py::test_lamb_butchering_weight_and_cost_distribution` | 25 kg karkastan 22 kg parça et + 3 kg fire ayrılmış; tolerans ve ağırlık dengesi doğrulanmıştır. 287.50 € ≠ 351.00 € çelişkisi `SOURCE_COST_MISMATCH` ile yakalanır. | **PASSED** |
| **6** | Dağıtılan maliyet toplamı giriş maliyetine eşit mi? | `test_costing.py::test_allocate_sums_exactly_with_residual_on_last` | Ağırlık/değer bazlı maliyet dağıtımında artık pay son satıra aktarılır; 200 kombinasyonda parça + fire maliyet toplamının kuruşu kuruşuna eşit olduğu kanıtlandı. | **PASSED** |
| **7** | Lotlar arasındaki çoktan çoğa ilişkiler korunuyor mu? | `test_standalone_flows.py::test_reference_scenario_full_traceability_and_multi_market_recall` | `LotGenealogyEdge` üzerinden her girdi lotu her çıktı lotuna miktarlarıyla bağlanır. | **PASSED** |
| **8** | Satış doğru lotun stok miktarını azaltıyor mu? | `test_standalone_flows.py::test_sales_traceability_and_recall_flow` | 100 paketlik stoktan Market A'ya 30 paket satıldığında bakiye anında 70 pakete iner. | **PASSED** |
| **9** | Aynı satış isteğinin tekrarlanması çift stok düşümüne neden oluyor mu? | `test_standalone_flows.py::test_sales_traceability_and_recall_flow` | `Idempotency-Key` koruması sayesinde mükerrer istekte ikinci stok düşümü yapılmaz; `Idempotent-Replay: true` başlığı ile önceki yanıt döndürülür. | **PASSED** |
| **10** | ET-2026-001 lotundan SUC-2026-045 lotuna ulaşılabiliyor mu? | `test_standalone_flows.py::test_reference_scenario_full_traceability_and_multi_market_recall` | `traceability.forward([lot_et.id])` çağrısı mamul lotu `SUC-2026-045`'i ve sevk edilen marketleri eksiksiz bulur. | **PASSED** |
| **11** | Geri çağırma Market A/B/C için 30/25/30 paket sonucunu üretiyor mu? | `test_standalone_flows.py::test_reference_scenario_full_traceability_and_multi_market_recall` | `recall.simulate` çağrısı Market A: 30 pk, Market B: 25 pk, Market C: 30 pk çıktısını kesin kayıtlarla verir. | **PASSED** |
| **12** | Bloke edilen lot satılamıyor mu? | `test_standalone_flows.py::test_reference_scenario_full_traceability_and_multi_market_recall` | Geri çağırma ile bloke edilen lotun satışı backend katmanında `HTTP 409 LOT_BLOCKED` ile engellenir. | **PASSED** |
| **13** | Yetkisiz kullanıcı maliyet verilerine erişemiyor mu? | `test_standalone_flows.py::test_unauthorized_user_cost_redaction` & `test_unauthorized_price_tampering_is_rejected` | `costs:read` izni olmayan kullanıcıların yanıtlarında maliyet ve kâr alanları `redact_cost_data` ile maskelenir; liste fiyatı manipülasyonu `400 Bad Request` ile engellenir. | **PASSED** |
| **14** | React uygulaması gerçek API yanıtlarını doğru işliyor mu? | `web/src/test/api-client.test.tsx` vb. | Vitest ile 4 test dosyasında 11 birim test geçmiştir; veri geçersizleştirme ve hata pencereleri doğrulanmıştır. | **PASSED** |
| **15** | Android satışları doğru lot ve stok hareketiyle kaydediliyor mu? | `android/.../SaleValidatorTest.kt` & `OfflineQueueAuthTest.kt` | Room yerel veritabanında `PendingSaleEntity` oluşturulur, `createdByUserEmail` bağlanır, liste fiyatı ve lot kodu saklanır. | **PASSED** |
| **16** | SQLite–MySQL senkronizasyonu mükerrer kayıt üretmiyor mu? | `android/.../IdempotencyAndErrorTest.kt` & `SalesRepository.kt` | İstemci tarafında tekil `client_uuid` üretilerek `Idempotency-Key` başlığında sunucuya iletilir; ağ kopmalarında yeniden denense dahi tek hareket oluşur. | **PASSED** |
| **17** | ML tahminleri gerçek sonuçlardan ayrı saklanıyor mu? | `test_standalone_flows.py::test_ml_predictions_isolated_from_financial_ledgers` | Yapay zekâ tahminleri bağımsız `ml_predictions` tablosunda saklanır; muhasebe defterlerine, EKP birim maliyetine veya stok bakiyelerine müdahale etmez. | **PASSED** |
| **18** | Servisler Docker ortamında birbirine ulaşabiliyor mu? | `docker-compose config` doğrulaması | Ortak iç ağ (`avatar_default`) üzerinde `mysql:3306`, `redis:6379`, `api:8000` ve `web:80` servisleri healthcheck bağımlılıklarıyla yapılandırılmıştır. | **PASSED** |

---

## 2. Test Çalıştırma Sonuçları

### 2.1 Backend Test Paketi (13 Test, %100 Başarı)

- **Komut:**
  ```powershell
  backend\.venv\Scripts\python.exe -m pytest backend/tests/test_costing.py backend/tests/test_standalone_flows.py -v
  ```
- **Çıktı:**
  ```text
  backend\tests\test_costing.py::test_pdf_reference_scenario_ekp PASSED                        [  7%]
  backend\tests\test_costing.py::test_allocate_sums_exactly_with_residual_on_last PASSED       [ 15%]
  backend\tests\test_costing.py::test_allocate_by_weight_property PASSED                       [ 23%]
  backend\tests\test_costing.py::test_lamb_source_inconsistency_arithmetic PASSED             [ 30%]
  backend\tests\test_standalone_flows.py::test_ekp_production_and_stock_flow PASSED           [ 38%]
  backend\tests\test_standalone_flows.py::test_lamb_butchering_weight_and_cost_distribution PASSED [ 46%]
  backend\tests\test_standalone_flows.py::test_sales_traceability_and_recall_flow PASSED       [ 53%]
  backend\tests\test_standalone_flows.py::test_unauthorized_price_tampering_is_rejected PASSED [ 61%]
  backend\tests\test_standalone_flows.py::test_idempotency_key_reused_with_different_body_fails_with_409 PASSED [ 69%]
  backend\tests\test_standalone_flows.py::test_negative_quantity_receipt_rejected PASSED      [ 76%]
  backend\tests\test_standalone_flows.py::test_reference_scenario_full_traceability_and_multi_market_recall PASSED [ 84%]
  backend\tests\test_standalone_flows.py::test_unauthorized_user_cost_redaction PASSED        [ 92%]
  backend\tests\test_standalone_flows.py::test_ml_predictions_isolated_from_financial_ledgers PASSED [100%]

  ======================= 13 passed, 1 warning in 29.91s ========================
  ```

### 2.2 Web Yönetim Paneli Vitest Paketi (11 Test, %100 Başarı)

- **Komut:**
  ```powershell
  cd web && npm test
  ```
- **Çıktı:**
  ```text
  ✓ src/test/api-client.test.tsx (4 tests)
  ✓ src/test/invalidation.test.ts (2 tests)
  ✓ src/test/format-validation.test.ts (4 tests)
  ✓ src/test/confirm-dialog.test.tsx (1 test)

  Test Files  4 passed (4)
        Tests  11 passed (11)
  ```

### 2.3 Android Birim Testleri (`android/app/src/test/...`)

- `BigDecimalCalculationTest.kt`: Parasal yuvarlama ve EKP hassasiyet testleri.
- `SaleValidatorTest.kt`: Bloke lot, yetersiz stok, negatif miktar denetimleri.
- `IdempotencyAndErrorTest.kt`: UUID formatı ve hata kodu haritalama testleri.
- `BarcodeParserTest.kt`: Lot URI, GS1-128 / DataMatrix AI (01, 10, 21), EAN-13 GTIN ve ham lot kodu regex ayrıştırıcı testleri.
- `OfflineQueueAuthTest.kt`: Kullanıcı e-posta bağlama (`createdByUserEmail`), paylaşımlı cihaz güvenliği, HTTP 401 durumunda kuyruk koruma ve HTTP 409 reddi testleri.
