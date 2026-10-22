# Cilt 1.10 — Cilt 1.2–1.9 Çapraz Kontrol Raporu

**Durum:** İnceleme raporu — kullanıcı onayı bekleniyor  
**Tarih:** 22 Ekim 2026  
**Kapsam:** Cilt 1.2 ERD/veri şeması, Cilt 1.3 API sözleşmeleri, Cilt 1.4 DTO/contract testleri, Cilt 1.5 iş akışları, Cilt 1.6 backend planı, Cilt 1.7 migration/seed planı, Cilt 1.8 auth/rol/güvenlik ve Cilt 1.9 endpoint izinleri  
**Önemli:** Bu rapor gerçek Alembic migration dosyaları oluşturmaz ve veritabanını oluşturmaz/değiştirmez. Bu işlemlere geçmek için kullanıcının bu rapora ayrıca açık onay vermesi gerekir.

## 1. Yönetici özeti

Cilt 1.9 onaylandıktan sonra önerilen sonraki adım, gerçek migration öncesi sözleşme çapraz kontrolüdür. Bu rapor, mevcut proje belgelerinde açıkça işaretlenmiş uyumsuzlukları ve migration öncesi karara bağlanması gereken noktaları toplar.

Mevcut dokümantasyon, sistemin genel mimarisini ve ana iş akışlarını tanımlıyor; ancak tüm tablo/kolon/DTO/endpoint/izin ilişkilerinin kodlamaya hazır tek bir kesin sözleşme halinde olduğu henüz gösterilmiş değildir. Bu nedenle bu rapor, belirsizlikleri kendi kendine “düzeltmez”. Her konu için öneri sunar ve kullanıcı kararı gerektirenleri açıkça ayırır.

## 2. Onaylanmış temel standartlar

Aşağıdakiler önceki onaylara göre sabit kabul edilir:

- Android: Kotlin + Jetpack Compose + Room/SQLite + Retrofit/OkHttp + Coroutines + DataStore.
- Backend: Python + FastAPI + Pydantic + SQLAlchemy 2.x + Alembic + PyMySQL.
- Merkezi veritabanı: MySQL 8.4 LTS.
- Web: React + TypeScript + Vite + Tailwind CSS + TanStack Query + Recharts.
- ML: pandas, NumPy, scikit-learn, joblib; ilk sürümde FastAPI içinde modül.
- API: REST/JSON, `/api/v1`, OpenAPI.
- İç kimlikler BIGINT; insan okunabilir iş kodları ayrı ve unique.
- Para `DECIMAL(19,4)`, miktar/ağırlık `DECIMAL(19,6)`; API'de string.
- Zaman anları ISO 8601 UTC `Z`; tarih-only `YYYY-MM-DD`.
- Stock movement ledger değiştirilemez; movement ve balance aynı transaction'da.
- Movement quantity pozitif; direction `IN`/`OUT`.
- Lot genealogy çoktan çoğa ve miktarlı.
- Satış ve sevkiyat ayrı kayıtlar; kayıt bulunmayan ikinci-tier satış varsayılmaz.
- JWT access token + rol tabanlı yetki temel yaklaşım.
- Kritik operasyon kayıtları hard-delete edilmez.
- Satışta `Idempotency-Key` zorunlu; aynı key/farklı body `409`.
- Hata zarfı: `error.code`, `error.message`, opsiyonel `error.details`, `request_id`.
- JSON/DB alanları `snake_case`, enumlar `UPPER_SNAKE_CASE`, endpoint yolları lowercase kebab-case.
- Android online-first; MySQL'e yalnızca backend erişir; ilk sürümde offline sales queue yok.

## 3. Çapraz kontrol bulguları

### CC-01 — Fire çıktısının ürün/lot alanları nullable mı?

**Kaynak:** Cilt 1.2, Cilt 1.3, Cilt 1.4, Cilt 1.5 WF-01, Cilt 1.7.

**Sorun:** Fire bir ölçüm/kayıp kaydı olarak mı tutulacak, yoksa her fire satırı stok lotu/ürününe mi bağlanacak? Belgelerde bu konuda açık uyuşmazlık olduğu zaten işaretlenmiş.

**Öneri:** Fire satırını stokta izlenen çıktıdan ayır. Stokta izlenen kesim/yan ürünlerde ürün ve çıktı lotu zorunlu olsun; yalnızca fire ölçümü için ürün/lot alanları nullable olabilsin. Ancak bu öneri ERD'deki mevcut alanlarla doğrulanmadan migration'a aktarılmamalıdır.

**Gerekli işlem:** Cilt 1.2 tablo/kolon nullability ve Cilt 1.3 request DTO'su tek karara bağlanmalı.

**Durum:** AÇIK — kullanıcı kararı gerekli.

### CC-02 — Üretim girdisi stoktan hangi aşamada düşer?

**Kaynak:** Cilt 1.2, Cilt 1.3, Cilt 1.5 WF-02, Cilt 1.6 transaction planı.

**Sorun:** Planlama/başlangıç anında mı yoksa üretim tamamlanırken gerçek tüketim miktarıyla mı `OUT` movement oluşturulacağı tüm sözleşmelerde kesinleştirilmelidir.

**Öneri:** İlk sürümde üretim tamamlanırken gerçek tüketim miktarlarıyla düş; `IN_PROGRESS` aşamasında stok rezervasyonu modelde yoksa fiziksel stok düşme. Bu, Cilt 1.5'teki öneriyle uyumludur.

**Gerekli işlem:** API durum geçişi ve movement oluşturma zamanı aynı şekilde belgelenmeli.

**Durum:** AÇIK — kullanıcı kararı gerekli.

### CC-03 — Satış mı sevkiyat mı fiziksel stok çıkışının sahibi?

**Kaynak:** Cilt 1.2, Cilt 1.3, Cilt 1.5 WF-03, Cilt 1.6, Cilt 1.7.

**Sorun:** Satış ve sevkiyat ayrı kayıtlardır; ancak aynı fiziksel ürün için her ikisinin de `OUT` movement yazması çift stok düşümüne yol açar.

**Öneri:** Fiziksel stok düşümünü yalnızca tek bir olay sahiplenmeli. Eğer satış stoktan teslim anında düşüyorsa dispatch ikinci kez düşmemeli; eğer stok sevkiyatta düşüyorsa satış yalnızca ticari kaydı tutmalı. Yarışma senaryosundaki market sevkiyatları için iş akışı açıkça seçilmelidir.

**Gerekli işlem:** Cilt 1.2 movement ilişkileri, Cilt 1.3 endpoint yan etkileri ve Cilt 1.5 durum geçişleri tekleştirilmeli.

**Durum:** AÇIK — migration öncesi bloklayıcı karar.

### CC-04 — Recall aktivasyonu senkron mu, outbox/worker ile mi?

**Kaynak:** Cilt 1.3, Cilt 1.5 WF-05, Cilt 1.6, Cilt 1.7.

**Sorun:** Büyük bir genealogy grafiğinde tüm lotları tek transaction içinde bloklamak pahalı olabilir; ara durum/outbox yaklaşımı ek durum ve tablo gerektirir.

**Öneri:** MVP demo veri hacmi küçük olduğundan senkron/atomik aktivasyonla başla; performans ihtiyacı doğarsa outbox yaklaşımını ayrı karar olarak ekle. Bu seçim veri modeli ve API sözleşmesiyle doğrulanmalı.

**Durum:** AÇIK — kullanıcı kararı gerekli.

### CC-05 — Recall çözümünde blokaj otomatik kalkar mı?

**Kaynak:** Cilt 1.3, Cilt 1.5 WF-06, Cilt 1.8.

**Sorun:** Recall `RESOLVED` durumuna geçince lot blokajının kaldırılması otomatik mi olacağı netleştirilmelidir.

**Öneri:** Recall'ın çözülmesi geçmiş olayın kapandığını gösterir; lot blokajını otomatik kaldırmaz. Yeniden satılabilir duruma getirme ayrı, yetkili ve audit edilen bir komut olmalıdır.

**Durum:** AÇIK — güvenlik açısından bloklayıcı karar.

### CC-06 — Ağırlık farkı toleransı ve gerekçe

**Kaynak:** Cilt 1.2, Cilt 1.3, Cilt 1.5 WF-07, Cilt 1.7.

**Sorun:** Girdi ağırlığı ile kesim/yan ürün/fire toplamı arasındaki kabul edilebilir tolerans tanımlı değil.

**Öneri:** Tolerans değeri işletme/yarışma gereksiniminden gelmeli; kod içine tahmini sabit değer gömülmemeli. Tolerans dışı fark için kullanıcı açıklaması ve audit zorunlu olabilir.

**Durum:** AÇIK — kullanıcı/işletme kuralı gerekli.

### CC-07 — Tamamlanmış işlerin düzeltme/ters kayıt yöntemi

**Kaynak:** Cilt 1.2, Cilt 1.3, Cilt 1.5 WF-08, Cilt 1.6.

**Sorun:** Tamamlanmış üretim, parçalama ve satış kayıtları silinmemeli; fakat ters kayıtların alanları ve stok/maliyet etkileri açıkça tanımlanmalı.

**Öneri:** Kaynak kayda referans veren ayrı reversal/correction kaydı oluştur; karşı movement'ları aynı transaction'da yaz; eski kaydı değişmez tut. Hangi rolün hangi düzeltmeyi yapacağı Cilt 1.9 izin matrisiyle eşleşmeli.

**Durum:** AÇIK — API ve veri modeli tasarımı gerekli.

### CC-08 — Satış dışındaki kritik komutlar için idempotency

**Kaynak:** Cilt 1.3, Cilt 1.4, Cilt 1.5 WF-09, Cilt 1.7.

**Sorun:** Satış için idempotency zorunlu; lot kabulü, üretim tamamlama, parçalama tamamlama, sevkiyat dispatch ve recall activation için tekrar istek davranışı kesinleştirilmeli.

**Öneri:** Stok/maliyet etkisi olan tüm POST komutlarında ya idempotency key kullan ya da mevcut durumdan tekrar çalıştırıldığında ikinci etki oluşturmayan deterministik conflict yanıtı tanımla. MVP'de her endpoint için ortak middleware eklemek yerine kritik komutları tek tek sözleşmede işaretle.

**Durum:** AÇIK — API sözleşmesi kararı gerekli.

### CC-09 — Ara durumlar

**Kaynak:** Cilt 1.3, Cilt 1.5 WF-10, Cilt 1.6.

**Sorun:** `IN_PROGRESS`, `PREPARED`, `ACTIVATING` gibi ara durumların hepsi gerçekten gerekli olmayabilir; bazıları API'lerde var, bazıları sadece olası tasarım olarak tartışılmıştır.

**Öneri:** İlk sürümde yalnızca istemcinin göreceği ve iş kuralı gerektiren durumları kullan. Recall için `ACTIVATING` ancak asenkron outbox seçilirse gerekli olabilir. Endpoint enumları tek kaynakta sabitlenmeli.

**Durum:** AÇIK — durum sözlüğü birleştirilmeli.

### CC-10 — Stok düzeltme yetkisi

**Kaynak:** Cilt 1.3, Cilt 1.8, Cilt 1.9.

**Sorun:** Cilt 1.3 ADMIN+OPERATOR; Cilt 1.8/1.9 önerisi yalnızca ADMIN.

**Öneri:** İlk sürümde yalnızca ADMIN; OPERATOR normal kabul/üretim/parçalama işlemleriyle stok hareketi oluşturur, genel düzeltme yapmaz.

**Durum:** AÇIK — kullanıcı onayı gerekli.

### CC-11 — Sevkiyat rolü

**Kaynak:** Cilt 1.3, Cilt 1.8, Cilt 1.9.

**Sorun:** Üst seviye rol matrisi ile endpoint bazlı rol önerileri arasında farklılık var.

**Öneri:** `SALES` sevkiyat oluşturma ve dispatch işlemlerini yürütür; `OPERATOR` ve `TRACEABILITY_MANAGER` yalnızca görüntüler. Bu, rol sorumluluklarını ayırır.

**Durum:** AÇIK — kullanıcı onayı gerekli.

### CC-12 — AI tahmin okuma ve başlatma izinleri

**Kaynak:** Cilt 1.3, Cilt 1.8, Cilt 1.9.

**Sorun:** `VIEWER` tahmin başlatabilmeli mi, yalnızca sonuçları mı okuyabilmeli? `GET prediction` için ayrı permission key de kesinleştirilmeli.

**Öneri:** Tahmin başlatma `ADMIN` ve `OPERATOR`; tahmin sonuçlarını okuma `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`, `VIEWER`. `SALES` erişimi ilk sürümde olmasın.

**Durum:** AÇIK — kullanıcı onayı gerekli.

### CC-13 — JWT ve web token saklama

**Kaynak:** Cilt 1.3, Cilt 1.8, Cilt 1.9.

**Sorun:** Cilt 1.3 örneğinde `expires_in: 3600`, Cilt 1.9 önerisinde 30 dakika var. Refresh token yokluğu ve logout invalidation da netleştirilmeli.

**Öneri:** Access token 30 dakika; ilk MVP'de refresh token yok; logout istemci token'ını temizler ve bu davranış açıkça belgelenir. Web için HttpOnly/Secure/SameSite cookie + CSRF koruması seçilecekse FastAPI cookie ve CSRF sözleşmesi ayrıca yazılmalı. Android için token güvenli depolama kararı da belgelenmeli.

**Durum:** AÇIK — güvenlik kararı gerekli.

### CC-14 — Hata kodu sözlüğü

**Kaynak:** Cilt 1.3, Cilt 1.4, Cilt 1.8, Cilt 1.9.

**Sorun:** Bazı belgelerde genel `CONFLICT`, bazılarında `INVALID_STATE_TRANSITION`, `IDEMPOTENCY_KEY_REUSED` gibi özel kodlar geçiyor.

**Öneri:** HTTP status ile `error.code` ayrımını koruyarak tek bir error code registry oluştur. Cilt 1.3 ve 1.4 örnekleri bu registry'ye göre güncellensin. Kod adları için alias veya sessiz dönüşüm kullanma.

**Durum:** AÇIK — API sözleşmesi düzenlemesi gerekli.

### CC-15 — Nullable alanlar ve eksik bilgi semantiği

**Kaynak:** Cilt 1.2, Cilt 1.3, Cilt 1.4, Cilt 1.7.

**Sorun:** `NULL`, sıfır, bilinmiyor ve uygulanamaz değerler birbirinden ayrılmalı. Fire dışında son kullanma tarihi, hizmet maliyeti ve tahmin alanlarında da bu anlamlar tutarlı olmalı.

**Öneri:** Her nullable kolon için “neden nullable?” açıklaması yaz; bilinmeyen değerleri sıfır veya varsayılan tarihle doldurma. DTO ve DB nullability birebir eşleşsin.

**Durum:** AÇIK — ERD/API kolon bazında kontrol edilmeli.

### CC-16 — Health endpoint ve bilgi ifşası

**Kaynak:** Cilt 1.3, Cilt 1.6, Cilt 1.9.

**Sorun:** Liveness ile DB/bağımlılık ayrıntısı veren health kontrolü aynı endpoint'te herkese açık olmamalı.

**Öneri:** Temel liveness endpoint'i public veya internal probe'a açık; ayrıntılı DB health yalnızca internal/authorized erişime açık. Yanıt SQL, hostname, credential veya stack trace içermez.

**Durum:** AÇIK — dağıtım politikası kararı gerekli.

## 4. API sözleşmesinde birleştirilmesi gereken ortak kurallar

1. Tüm response/request alanları `snake_case`.
2. Para ve miktar değerleri JSON string.
3. UTC timestamp'ler ISO 8601 `Z`.
4. Ortak error envelope tek örnek ve tek registry kullanır.
5. Pagination/filtering parametreleri aynı isim ve davranışı kullanır.
6. Her kritik POST komutu için idempotency veya tekrar davranışı açıkça belirtilir.
7. Her endpoint için auth, permission ve kaynak kapsamı tanımlıdır.
8. Her stok etkili komutun movement ledger/balance/audit etkileri belirtilir.
9. API'de enum olan her durum, DB ve iş akışı belgelerinde aynı isimle yer alır.
10. Nullable DTO alanı ve DB kolonu aynı iş anlamını taşır.

## 5. Migration öncesi önerilen karar listesi

Aşağıdaki öneriler kullanıcı onayı bekler. Hiçbiri otomatik olarak onaylanmış sayılmaz.

| Karar | Öneri | Önemi |
|---|---|---|
| Fire ürün/lot nullability | Fire ölçümü stokta izlenen çıktıdan ayrı | DB/API schema |
| Üretim stok düşümü | Tamamlama anında gerçek tüketim | Inventory ledger |
| Satış/sevkiyat stok sahibi | Tek bir olay stok düşürür; seçimi netleştir | Negatif/çift stok |
| Recall aktivasyonu | MVP'de atomik senkron | State/transaction |
| Recall çözümünde blokaj | Otomatik kaldırma yok; ayrı yetkili release | Gıda güvenliği |
| Ağırlık toleransı | İşletme gereksinimiyle belirlenir; sabit uydurulmaz | Butchering validation |
| Reversal/correction | Ayrı kayıt ve ters hareket | Audit/stock/cost |
| Idempotency | Kritik komutlar için açık sözleşme | Duplicate writes |
| Durum enumları | Tek ortak sözlük | API/DB consistency |
| Stok düzeltme rolü | ADMIN only | Authorization |
| Sevkiyat rolü | SALES owns create/dispatch | Authorization |
| AI prediction permissions | Operator/admin start; defined roles read | Authorization |
| JWT | 30 min, refresh yok MVP, logout behavior documented | Security |
| Error codes | Tek registry | Client compatibility |
| Health | Liveness ile detailed health ayrılır | Security |

## 6. Çapraz kontrolün sınırları

Bu rapor mevcut ciltlerde açıkça görülen uyuşmazlıkları ve karar noktalarını derler. Gerçek şema kodu veya OpenAPI makinesi üzerinden otomatik diff yapılmış olduğu anlamına gelmez. Kesin tablo/kolon eşleştirmesi için Cilt 1.2'nin tüm tablo tanımları ile Cilt 1.3/1.4'ün her request/response DTO'su satır satır incelenmeli ve sonuçlar ek bir mapping tablosunda gösterilmelidir.

**Bu raporun hazırlanmış olması migration'a geçiş izni değildir.** Kullanıcıdan bu rapor için açık onay alınmalıdır.

## 7. Kullanıcıdan beklenen onay

Lütfen aşağıdakilerden birini seç:

- **A — Raporu onaylıyorum:** Önerilen kararları onaylıyorum; ilgili ciltlerdeki çelişkileri düzeltecek bir revizyon planı hazırla. Migration dosyalarına henüz geçme.
- **B — Raporu onaylıyorum, bazı kararları değiştireceğim:** Hangi CC maddelerinin değişeceğini birlikte netleştirelim.
- **C — Raporu düzelt:** Hangi bulguların veya önerilerin değiştirilmesini istediğini belirt.

Raporun onaylanması tek başına gerçek Alembic migration dosyalarını yazmak için yeterli değildir. Önce ilgili belgeler ve karar kayıtları revize edilir, ardından güncellenmiş migration öncesi plan kullanıcıya sunulur. Gerçek migration dosyalarını oluşturmak veya veritabanını değiştirmek için ayrıca açık onay alınır.

### Tarihsel kayıt uyarısı (Cilt 1.34)
Bu rapordaki eski token/health/BY_VALUE ifadeleri tarihsel bulgudur; güncel normatif sözleşme olarak kullanılmamalıdır. Cilt 1.31/1.32 onayları ve Cilt 1.34 revizyonları önceliklidir.
