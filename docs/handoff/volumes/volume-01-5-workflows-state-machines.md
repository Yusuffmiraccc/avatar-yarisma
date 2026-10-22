# Cilt 1.5 — İş Akışları ve Durum Makineleri


> **Normatif güncelleme — 22 Ekim 2026 (Cilt 1.32):** Bu belgedeki daha eski ve çelişen taslak ifadeler için `volume-01-32-approved-decisions-and-cross-check.md` ile Cilt 1.31'in onay kaydı önceliklidir. Bu not doküman sözleşmesini günceller; migration veya veritabanı değişikliği izni değildir.

**Durum:** Uygulama öncesi iş akışı sözleşmesi  
**Tarih:** 22 Ekim 2026  
**Bağlı belgeler:** Cilt 0, Cilt 1, Cilt 1.2, Cilt 1.3, Cilt 1.4, DEC-001, ADR-001  
**Amaç:** Operasyonel kayıtların hangi sırayla oluşturulacağını, hangi durum geçişlerinin geçerli olduğunu ve hata/tekrar/eşzamanlı istek durumlarında sistemin nasıl davranacağını netleştirmek.

> **Normatiflik:** Bu belge, Cilt 1.2 veri modelini ve Cilt 1.3 API sözleşmesini tamamlayan iş akışı katmanıdır. Mevcut belgelerle çelişen bir nokta bulunursa kod yazmadan önce belgeler birlikte güncellenir. Sistem, kayıt bulunmayan bir iş olayını varsayarak tamamlamaz.

## 1. Tasarım ilkeleri

1. **Backend merkezî doğruluk kaynağıdır.** Android ve web istemcileri iş kuralını görsel olarak kolaylaştırabilir; kritik kurallar backend tarafından tekrar doğrulanır.
2. **Stok hareket defteri değiştirilemez geçmiş sağlar.** Hatalı hareket silinmez; yetkili düzeltme/ters kayıt eklenir.
3. **İşlemler atomiktir.** Bir iş akışının stok, lot bakiyesi, genealogy, maliyet snapshot'ı, durum ve audit etkileri tek transaction içinde tamamlanır veya hiçbiri uygulanmaz.
4. **Tekrarlanan komutlar güvenli olmalıdır.** Satış için `Idempotency-Key` zorunludur. Diğer kritik komutlar ya idempotent tasarlanır ya da tamamlanmış durumdan yeniden uygulanmaları güvenli biçimde reddedilir.
5. **Durumlar geçmişi gizlemez.** İptal, ret, ters kayıt ve düzeltmeler audit edilebilir olmalıdır.
6. **Recall engeli, AI tahmininden bağımsızdır.** Lot blokajı ve satış engeli deterministik kayıtlarla çalışır.
7. **Ağırlık ve maliyet farkı sessizce yok edilmez.** Tolerans varsa açık konfigürasyon ve gerekçe ile uygulanır; açıklanmayan fark için sistem otomatik neden üretmez.
8. **İstemci çevrimdışı satış kuyruğu ilk sürüm kapsamı dışındadır.** Android online-first çalışır; yerel SQLite/Room, merkezî MySQL'in yerine geçmez.

## 2. Ortak durum makinesi kuralları

### 2.1 Geçiş sözleşmesi

Her durum değişikliği için backend şunları kontrol eder:

- Kaydın mevcut durumu geçişe izin veriyor mu?
- Kullanıcının rolü ve kayda erişim kapsamı uygun mu?
- Gerekli ilişkili kayıtlar mevcut ve geçerli mi?
- Girdi lotları blokajlı mı, stokları yeterli mi?
- İstek tekrarı veya eşzamanlı başka bir işlem var mı?
- Geçiş, hareketler ve audit kaydı tek transaction içinde tamamlanabiliyor mu?

Geçersiz geçişte stok ve maliyet üzerinde kısmi etki oluşmaz. API, Cilt 1.4'teki ortak hata zarfıyla `409 INVALID_STATE_TRANSITION` veya daha özel bir hata kodu döndürür.

### 2.2 Eşzamanlılık ve kilitleme

Stok tüketen/üreten, lot bloklayan veya maliyet snapshot'ı oluşturan komutlarda:

- İlgili lot bakiye satırları transaction içinde kilitlenir (MySQL için uygun `SELECT ... FOR UPDATE` yaklaşımı).
- Stok miktarı kilit alındıktan sonra yeniden kontrol edilir.
- İşlemin tamamlanmasından önce stok defteri ile güncel bakiye aynı transaction'da güncellenir.
- Deadlock veya geçici veritabanı hatasında kontrollü retry politikası uygulanabilir; sınırsız retry yapılmaz.
- Aynı anda iki satış geldiğinde toplam satılan miktar eldeki kullanılabilir miktarı aşamaz.
- `updated_at` tek başına eşzamanlılık kontrolü olarak yeterli kabul edilmez; gerekiyorsa sürüm numarası/optimistic locking eklenir.

### 2.3 İptal ve düzeltme

- Taslak durumundaki kayıt, iş etkisi yaratmadıysa iptal edilebilir.
- Stok/maliyet etkisi oluşmuş tamamlanmış kayıt doğrudan silinmez veya geriye dönük düzenlenmez.
- Düzeltme, yetkili bir ters hareket veya düzeltme kaydı ile yapılır; eski kayıt ve düzeltme birbirine bağlanır.
- Tamamlanmış üretim/parçalama/satış için “geri al” işlevi, ilgili iş alanının özel ters kayıt kurallarını uygulamadan yalnızca durum etiketini değiştiremez.
- Recall aktivasyonu gibi güvenlik etkili bir kayıt, yalnızca bir ekran düğmesini tekrar çağırarak etkisizleştirilemez; kapatma/çözme ayrı, yetkili ve audit edilen bir süreç olmalıdır.

## 3. Satın alma kabulü ve lot oluşturma

### 3.1 Akış

1. Yetkili kullanıcı tedarikçi, ürün, miktar, birim, lot kodu ve biliniyorsa son kullanma tarihini girer.
2. Backend ürün-birim uyumunu, pozitif miktarı, lot kodu benzersizliğini ve tedarikçi ilişkisini doğrular.
3. Aynı transaction içinde lot/lot kabul kaydı, `IN` stok hareketi, lot bakiyesi ve audit kaydı oluşturulur.
4. Başarılı yanıt yeni lot kimliğini, iş kodunu ve kabul edilen miktarı döndürür.

### 3.2 Kurallar

- Kabul miktarı sıfırdan büyük olmalıdır.
- Son kullanma tarihi bilinmiyorsa API/DB sözleşmesindeki nullable kuralı uygulanır; bilinmeyen tarih tahmin edilmez.
- Aynı lot koduyla ikinci kabul sessizce yeni lot oluşturmaz. İade, ek kabul veya düzeltme gibi ayrı iş olayı olarak kaydedilir.
- Ağ timeout'u sonrası tekrar gönderme ihtimali için istemci, sonuç belirsizse kayıt araması/işlem durumu sorgusu yapar; lot kabulünde idempotency standardı ayrıca API sözleşmesinde sabitlenmelidir.
- Kaynak belge/invoice bilgisi varsa belge referansı ilişkilendirilir; OCR sonucu insan onayı olmadan kesin stok hareketine dönüşmez.

## 4. Dış kaynaklı üretim akışı

### 4.1 Önerilen durumlar

`DRAFT → PLANNED → IN_PROGRESS → COMPLETED`

İş başlamadan önce iptal edilebilen kayıt için `CANCELLED` kullanılabilir. Kullanılan stok veya gerçekleşmiş maliyet etkisi olan üretim emri, doğrudan `CANCELLED` durumuna geçirilmez; düzeltme/ters kayıt süreci gerekir.

> Durum adları Cilt 1.3 endpoint enumlarıyla birebir doğrulanmalıdır. Endpoint sözleşmesinde farklı enum varsa bu belgeye göre sessizce yeniden adlandırma yapılmaz; belgeler aynı enum kümesinde birleştirilir.

### 4.2 Geçişler

| Geçiş | Ön koşullar | Atomik etkiler |
|---|---|---|
| `DRAFT → PLANNED` | Ürün/planlanan miktar, reçete veya girdi listesi, gerekli hizmet bilgileri tamam | Plan ve audit |
| `PLANNED → IN_PROGRESS` | Girdi lotları seçilmiş, kullanılabilir miktar yeterli, lotlar blokajlı değil | Başlangıç zamanı ve audit; tüketim politikası aşağıda belirlenir |
| `IN_PROGRESS → COMPLETED` | Gerçek tüketim, hizmet maliyeti ve üretilen miktar/lot kayıtları doğrulanmış | Girdi `OUT`, bitmiş ürün `IN`, genealogy, maliyet snapshot'ı, bakiye, durum ve audit |
| Taslak/planlı → `CANCELLED` | İş etkisi yok veya yalnızca plan kaydı mevcut | İptal nedeni ve audit |

### 4.3 Stok tüketiminin zamanı

İlk sürüm için önerilen ve onay gerektiren kural: **gerçek girdi stok hareketleri üretim emri tamamlanırken**, gerçek tüketim miktarları üzerinden yazılır. `IN_PROGRESS` aşamasında planlanan miktar fiziksel stoktan düşülmez; gerekirse “rezervasyon” ayrı bir kavram olarak modellenmelidir. Rezervasyon mevcut veri modelinde yoksa uygulama onu varmış gibi kullanmamalıdır.

Bu yaklaşım, tamamlanmamış emirlerin stok defterinde gerçekleşmiş tüketim gibi görünmesini önler. Eğer işletme fiilî tüketimin üretim sırasında anında kaydedilmesini isterse ayrı hareket ve iptal/ters kayıt kuralları belirlenmelidir.

### 4.4 Gerçek birim maliyet

Örnek hesap:

- Gerçek hammadde maliyeti: tüketilen lot miktarları × o lot için geçerli maliyet yöntemi.
- Dış hizmet maliyeti: üretim emrine bağlanmış gerçekleşen hizmet maliyetleri.
- Toplam gerçekleşen maliyet: hammadde + dış hizmet + açıkça kapsamda tanımlanmış diğer maliyet bileşenleri.
- Gerçek birim maliyet (EKP): toplam gerçekleşen maliyet / iyi ürün olarak kabul edilen toplam çıktı miktarı.

PDF örneğinde toplam maliyet €1,543.50 ve iyi ürün çıktısı 85 paket olduğunda EKP yaklaşık €18.16/pakettir. Uygulama, 0 çıktı miktarına bölme yapmamalı; sıfır veya eksik çıktı halinde tamamlamayı reddetmeli ya da ayrı başarısız/inceleme durumuna yönlendirmelidir.

Yuvarlama yalnızca açıkça belirlenmiş gösterim veya tahsis aşamasında yapılır. Ara hesaplarda `Decimal` hassasiyeti korunur. Üretim maliyetinin nasıl stok lotlarına dağıtıldığı Cilt 1.2 maliyet alanlarıyla uyumlu olmalıdır.

### 4.5 Hata durumları

- Yetersiz stok: `409 INSUFFICIENT_STOCK`; hiçbir tüketim/çıktı hareketi yazılmaz.
- Girdi lotu blokajlı: `409 LOT_BLOCKED`; emir tamamlanamaz.
- Eksik çıktı lotu veya miktarı: doğrulama hatası; kısmi tamamlanma olmaz.
- Zaten tamamlanmış emir: ikinci stok etkisi oluşmaz; `409 INVALID_STATE_TRANSITION` veya tanımlanmış idempotent yanıt.
- Maliyet hesaplanamıyor: tamamlanma başarısız olur; eksik maliyetle sessizce tamamlanmaz.

## 5. Kuzu parçalama akışı

### 5.1 Önerilen durumlar

`DRAFT → PLANNED → IN_PROGRESS → COMPLETED`

Gerekli durum enumları Cilt 1.3 ile aynı olmalıdır. İptal kuralları üretim akışıyla aynı genel prensiplere tabidir.

### 5.2 Tamamlama ön koşulları

- Girdi hayvan/karkas lotu tanımlı ve kullanılabilir olmalıdır.
- Girdi ağırlığı, ürün sınıfı/türü ve maliyet temeli kayıtlı olmalıdır.
- Her `CUT` ve stokta izlenen `BYPRODUCT` için ürün, ağırlık, birim ve çıktı lotu tanımlanmalıdır.
- **Cilt 1.17 kararı:** `WASTE` ayrı `butchering_waste_records` tablosu/DTO’sudur; `butchering_outputs` yalnızca `CUT` ve stokta izlenen `BYPRODUCT` içerir. Fire satırı stok lotu veya stok IN hareketi üretmez.
- Çıktı ağırlıklarının toplamı ve farkı hesaplanmalı; fark için kullanıcı tarafından kayıtlı açıklama gerekebilecek politika ayrıca belirlenmelidir.

### 5.3 Ağırlık dengesi

Aşağıdaki değerler ayrı gösterilir:

- Girdi ağırlığı
- Kesim çıktıları toplamı
- Stokta izlenen yan ürünler toplamı
- Fire ağırlığı (kaydedilmişse)
- Açıklanamayan fark

`girdi ağırlığı = kesimler + stokta izlenen yan ürünler + ayrı fire kayıtları + açıklanan/izin verilen fark` eşitliği, belirlenmiş hassasiyet ve tolerans politikasıyla kontrol edilir. Fire maliyet payları ile stokta izlenen çıktılara tahsis edilen maliyetin toplamı giriş maliyetine eşit olmalıdır; `BY_VALUE` altında fire payı hesaplama kuralı migration öncesi açık kalır. Tolerans değeri onaylanmadan sabit bir sayı kod içine gömülmez.

PDF'deki örnek sayılarda tutarsızlık vardır: 25 kg × €11.50 = €287.50; PDF'de ayrıca €351 toplam gösterilmiştir ve listelenen kesim ağırlıkları 22 kg eder. Sistem bu değerleri olduğu gibi raporlar ve farkı görünür kılar; kaynağı açıklanmamış bir maliyet veya ağırlık farkını kendi kendine düzeltmez.

### 5.4 Maliyet tahsisi

Tahsis yöntemi (ağırlık bazlı veya değer bazlı) parçalama emrinde açıkça kaydedilmelidir. Tahsis payları, yuvarlama sonrası toplam giriş maliyetine eşit olmalıdır. Kuruş/son basamak farkı oluşursa tanımlı yuvarlama düzeltmesi bir çıktı satırına deterministik biçimde uygulanır ve audit edilir; toplam maliyet sessizce kaybolmaz.

### 5.5 Atomik tamamlanma

Tek transaction içinde:

1. Girdi lotunun kullanılabilir miktarı doğrulanır.
2. Girdi lotu için `OUT` hareketi yazılır.
3. Kesim/yan ürün lotları için `IN` hareketleri yazılır.
4. Lot genealogy bağlantıları miktarla birlikte oluşturulur.
5. Maliyet tahsisleri ve ağırlık dengesi sonuçları saklanır.
6. Emir `COMPLETED` yapılır ve audit kaydı eklenir.

Bu adımlardan biri başarısızsa hiçbiri commit edilmez.

## 6. Satış akışı

### 6.1 Akış

1. Kullanıcı ürün ve lot seçer.
2. İstemci miktar ve birim fiyatı girer; backend ürün-birim uyumunu ve rol yetkisini doğrular.
3. Backend `Idempotency-Key` ve istek gövdesini kontrol eder.
4. İlgili lot bakiyesini kilitleyip güncel kullanılabilir miktarı yeniden kontrol eder.
5. Lot recall/blokaj durumunu kontrol eder.
6. Tek transaction'da satış, satış satırları, `OUT` hareketleri, lot bakiyeleri, idempotency sonucu ve audit yazılır.
7. Başarı yanıtı satış kodunu, satırları ve toplamları döndürür.

### 6.2 Satışın reddedilmesi

Satış aşağıdaki durumlarda reddedilir:

- Lot recall nedeniyle blokajlıdır.
- Kullanılabilir miktar yetersizdir.
- Miktar pozitif değildir veya birim uyumsuzdur.
- Kullanıcı rolü satış yapamaz.
- `Idempotency-Key` eksiktir veya aynı anahtar farklı gövdeyle kullanılmıştır.
- Ürün/lot ilişkisi geçersizdir.

Reddedilen satış için satış kaydı veya stok hareketi oluşmaz; güvenlik/audit gereksinimi varsa başarısız komut olayı ayrı bir güvenlik günlüğüne yazılabilir ancak bu, gerçekleşmiş stok hareketi olarak gösterilmez.

### 6.3 Eşzamanlı satış örneği

Lotta 10 paket varsa ve iki satış aynı anda 7 paket isterse yalnızca bir satış başarılı olabilir. İkinci istek stok kilidi sonrası yeniden kontrol edilir ve `INSUFFICIENT_STOCK` ile reddedilir. İki satışın toplamı 14 paket olamaz.

## 7. Sevkiyat akışı

### 7.1 Satış ve sevkiyat ayrımı

Satış ve sevkiyat ayrı iş kayıtlarıdır. Satış kaydı, sevkiyatın otomatik gerçekleştiği anlamına gelmez. Bir markete gönderilen miktar ve lotlar sevkiyat kaydında tutulur; ikinci-tier dağıtım ancak gerçekten kaydedilmişse izlenir.

### 7.2 Bağlayıcı MVP durumları

`DRAFT → SHIPPED`; `DRAFT → CANCELLED`; `SHIPPED → RETURNED` yalnızca kayıtlı iade akışıyla.

MVP, teslimat kanıtı veya teslim alan onayı tutmadığı için `DELIVERED` kullanılmaz. DB/API enumunun tek sevkiyat çıkış durumu `SHIPPED` değeridir; `DISPATCHED` yalnızca komut/işlem adı olarak kullanılır, durum enumu değildir. `PREPARED` ayrı kalıcı durum olarak kullanılmaz; taslak içi hazırlık alanı yoksa ayrı state oluşturulmaz.

### 7.3 Sevkiyat ön koşulları ve etkileri

- Alıcı/market, sevk satırları, ürünler, lotlar ve miktarlar doğrulanır.
- Sevk edilecek miktar kullanılabilir stoktan fazla olamaz.
- Recall blokajlı lot sevk edilemez.
- **Bağlayıcı karar:** Fiziksel stok çıkışının tek sahibi dispatch işlemidir. Dispatch her sevkiyat satırı için tek `OUT/SHIPMENT` hareketi oluşturur; satış kaydı stok hareketi üretmez ve bakiyeyi azaltmaz.
- Sevkiyat, müşteri/market, lot, miktar ve zaman bilgisini saklar.
- İptal edilmiş veya hazırlık aşamasındaki sevkiyat, stok hareketi yaratmadıysa iptal edilebilir; gönderimden sonra düzeltme/iadeye özel akış gerekir.

**Sözleşme durumu:** WF-03 kullanıcı tarafından onaylandı. Cilt 1.2/1.3 normatif metinleri dispatch’i tek stok çıkışı sahibi olarak tanımlar; satış ve sevkiyat aynı fiziksel miktarı iki kez düşüremez.

## 8. Recall (geri çağırma) akışı

### 8.1 Temel durumlar

`DRAFT → ACTIVE → RESOLVED`

`CANCELLED` yalnızca henüz aktif edilmemiş taslak recall için kullanılabilir. Aktif recall, sıradan bir iptal işlemiyle silinemez. `RESOLVED`, ürünün geçmişte etkilenmediği anlamına gelmez; aksiyonların tamamlandığını ve yetkili kapatma yapıldığını ifade eder.

Bu durum isimleri Cilt 1.3 sözleşmesinde mevcut enumlarla uyumlu hale getirilmelidir; enum farkı varsa belge/API beraber güncellenir.

### 8.2 Taslak oluşturma

1. Yetkili kullanıcı kaynak lot kodunu/ID'sini ve gerekçeyi belirtir.
2. Backend lotun varlığını ve kullanıcının yetkisini doğrular.
3. Recall taslağı ve audit olayı oluşturulur.
4. Taslak durumunda satış blokajı henüz uygulanmaz; blokajın `ACTIVE` geçişinde başlayacağı açıkça gösterilir.

### 8.3 Recall aktivasyonu

Aktivasyon, tek transaction veya güvenilir bir outbox/işlem modeliyle tutarlı hale getirilmelidir:

1. Kaynak lot ve aşağı-akış lot genealogy bağlantıları üzerinden etkilenen lotlar bulunur.
2. İlgili lotlar satış/sevkiyat için blokajlı yapılır.
3. Etkilenen bitmiş ürün lotları, miktarlar ve kayıtlı müşteriler/marketler listelenir.
4. Mevcut stok, sevk edilmiş miktar, satışla kaydedilmiş miktar, iade ve atık kayıtları ayrı kategoriler olarak raporlanır; aynı miktar iki kategoride iki kez sayılmaz.
5. Recall durumu `ACTIVE` olur.
6. Audit ve iletişim/aksiyon kayıtları oluşturulur.

Daha sonraki bir sürümde ölçek gereksinimi senkron aktivasyonu yetersiz kılarsa outbox/worker ayrı mimari kararla değerlendirilebilir. Bu, ilk MVP kapsamı değildir; MVP recall aktivasyonu senkron ve atomiktir.

### 8.4 Satış ve sevkiyat engeli

- Her satış ve sevkiyat komutu, işlem anında lotun blokajını kontrol eder.
- Recall aktivasyonu ile eşzamanlı satışlar için aynı lot satırlarında tutarlı kilitleme/transaction stratejisi gerekir.
- Recall aktivasyonu önce commit olduysa sonrasındaki satış engellenir.
- Satış önce commit olduysa recall raporu bu satışı ve ilgili hareketi etkilenen geçmiş işlem olarak göstermelidir.
- Bir istemcinin ekranında eski “satılabilir” durumu görünmesi backend kontrolünü atlatamaz.

### 8.5 Geriye ve ileriye izleme

- **Geriye izleme:** bitmiş ürün lotu → üretim/parçalama kaydı → girdi lotları → tedarikçi/kabul kaydı.
- **İleriye izleme:** kaynak girdi lotu → ilişkili üretim/parçalama çıktıları → bitmiş lotlar → kayıtlı satış/sevkiyat → müşteri/market.
- Her bağlantıda ilişkilendirilen miktar ve birim korunur.
- Miktarlar farklı birimlerdeyse dönüşüm kuralı ve baz birim açık olmalıdır; dönüşüm bilinmiyorsa miktarlar doğrudan toplanmaz.
- Genealogy bağlantısı olmayan bir ilişki sistem tarafından tahmin edilmez.
- İkinci-tier market dağıtımı yalnızca kaydedilmişse rapora girer.

### 8.6 Recall çözümleme

Recall `RESOLVED` durumuna yalnızca yetkili kullanıcı, zorunlu aksiyon/iletişim durumlarını ve çözüm notunu tamamladığında geçebilir. Eksik aksiyonların zorunlu olup olmadığı ürün gereksiniminde belirlenmelidir. Çözümleme geçmiş blokaj ve recall kaydını silmez. Ürünü yeniden satılabilir yapmak gerekiyorsa ayrı, açıkça yetkilendirilmiş lot serbest bırakma kuralı tanımlanmalıdır; `RESOLVED` tek başına blokajı otomatik kaldırmamalıdır.

## 9. İade, atık ve yeniden işleme

Bu iş olayları veri modelinde ve Cilt 1.3 API'sinde açıkça tanımlı değilse kapsam varmış gibi implementasyon yapılmamalıdır. Gerekli olduklarında:

- İade, kaynak satış/sevkiyat ve lotla ilişkilendirilir.
- Geri dönen ürün kalite kontrolünden geçmeden otomatik olarak satılabilir stoğa eklenmez.
- Atık, lot/iş emri ve gerekçe ile kaydedilir; satılabilir stok yaratmaz.
- Yeniden işleme, girdi lotları ve yeni çıktı lotları arasında miktarlı genealogy bağlantısı kurar.
- Her stok etkisi `IN`/`OUT` hareketleri ve düzeltme/ters kayıt kurallarıyla izlenir.
- Recall blokajı altındaki ürünün iadesi blokajı kaldırmaz.

## 10. AI tahmin akışları

AI tahmini operasyonel kayıt yerine geçmez.

### 10.1 Üretim verimi ve EKP tahmini

1. Kullanıcı geçmiş veriye dayalı tahmin isteği gönderir.
2. Backend model sürümünü ve kullanılan özellikleri kaydeder.
3. Tahmin, tahmin aralığı varsa aralık ve model sürümü ile döner.
4. Gerçek üretim tamamlandığında tahmin ile gerçekleşen değer karşılaştırılır.
5. Hata metrikleri yalnızca yeterli doğrulanmış veri olduğunda raporlanır; veri azsa “güvenilir değerlendirme için yetersiz veri” uyarısı verilir.

Tahmin, gerçek maliyeti otomatik değiştirmez; gerçek maliyet yalnızca kayıtlı girdiler, hizmet maliyetleri ve tanımlı hesap yöntemiyle hesaplanır.

### 10.2 Parçalama ağırlığı tahmini

1. Girdi hayvan/karkas özellikleri ve ağırlık bilgileri doğrulanır.
2. Model tahmini kesim/yan ürün ağırlıklarını döndürür.
3. Kullanıcı gerçek ağırlıkları kaydeder.
4. Tahmin-gerçek farkı ve model performansı raporlanır.
5. Tahmin edilen değerler stok lotu veya kesin maliyet hareketi oluşturmaz.

### 10.3 AI hata ve güvenlik durumları

- Model yok veya yüklenemiyor: tahmin endpoint'i kontrollü hata döndürür; stok/üretim işlemleri çalışmaya devam edebilir.
- Girdi özellikleri eksik/geçersiz: açıklayıcı doğrulama hatası döner.
- Eğitim verisi az veya dağılım dışı girdi: tahmin uyarı ile sunulur veya ürün politikasına göre reddedilir.
- Model sürümü, tahmin zamanı ve sonuç kaydedilebiliyorsa audit edilebilir olmalıdır.
- AI recall kapsamını, lot ilişkilerini veya stok bakiyesini belirlemez.

## 11. Ortak hata ve tekrar davranışları

| Durum | Beklenen davranış | Veri etkisi |
|---|---|---|
| Yetkisiz rol | `403` ve ortak hata zarfı | İş kaydı/stok etkisi yok |
| Kayıt bulunamadı | `404` | İş kaydı/stok etkisi yok |
| Geçersiz durum geçişi | `409 INVALID_STATE_TRANSITION` | Kısmi etki yok |
| Yetersiz stok | `409 INSUFFICIENT_STOCK` | Hareket/bakiye değişmez |
| Lot blokajlı | `409 LOT_BLOCKED` | Satış/sevkiyat oluşmaz |
| Aynı idempotency anahtarı, aynı gövde | İlk sonucun yeniden dönmesi | İkinci iş etkisi yok |
| Aynı idempotency anahtarı, farklı gövde | `409 IDEMPOTENCY_KEY_REUSED` | Yeni iş etkisi yok |
| Decimal parse/precision hatası | `422` doğrulama hatası | İş etkisi yok |
| Beklenmeyen DB hatası | Genel `500`, request ID loglanır | Transaction rollback |
| AI servis/model hatası | Tahmin hatası; operasyon kayıtları etkilenmez | Stok/maliyet değişmez |

HTTP status ve error code adları Cilt 1.3'teki kesin listede sabitlenmelidir. Bu tabloda farklı bir kod önerisi görülürse API sözleşmesi güncellenmeden istemcilerde yeni kod varsayılmamalıdır.

## 12. Uçtan uca demo akışı

Demo, AVATAR değerlendirme senaryosunu uçtan uca ve audit edilebilir şekilde göstermelidir.

### Aşama A — Girdi lotu ve üretim

1. Tedarikçi ve hammadde kartları oluşturulur.
2. `ET-2026-001` kodlu 100 kg girdi lotu kabul edilir.
3. Üretim emri oluşturulur ve ilgili lot girdi olarak seçilir.
4. Gerçek tüketim, dış hizmet maliyeti ve 85 paket çıktı kaydedilir.
5. `SUC-2026-045` bitmiş ürün lotu oluşur.
6. EKP, VKP, brüt kâr ve marj tanımlı formüllerle gösterilir.
7. Girdi `OUT`, bitmiş ürün `IN` hareketleri ve genealogy bağlantısı doğrulanır.

### Aşama B — Market sevkiyatları

1. Kayıtlı marketlere 30, 25 ve 30 paketlik miktarlar ilişkilendirilir.
2. Market A/B/C için 30 + 25 + 30 = 85 paket dispatch edilir; toplam stok çıkışı tam 85 paket olmalı, satış kayıtları ilave stok çıkışı oluşturmamalıdır.
3. Lot → üretim emri → bitmiş lot → kayıtlı market ilişkileri gösterilir.
4. İkinci-tier satış kaydı yoksa arayüz bunu açıkça “kayıtlı değil/bilinmiyor” şeklinde gösterir; sıfır olarak varsaymaz.

### Aşama C — Recall

1. `ET-2026-001` için recall taslağı oluşturulur.
2. Recall aktive edilir.
3. Sistem `SUC-2026-045` ve bu lotla ilişkili kayıtlı sevkiyat/satışları bulur.
4. Kalan stok, Market A/B/C miktarları ve iletişim/aksiyon durumları ayrı ayrı raporlanır.
5. Aynı lot üzerinden yeni satış denenir ve backend tarafından reddedildiği gösterilir.
6. Audit geçmişi ve genealogy miktarları incelenir.

### Aşama D — AI

1. Üretim verimi/EKP tahmini istenir.
2. Tahmin ve gerçekleşen değer karşılaştırılır.
3. Parçalama ağırlığı tahmini istenir; gerçek ağırlıklar girilerek fark gösterilir.
4. Model performans ölçümü ve veri kısıtları sunulur.
5. AI servisi devre dışı bırakıldığında stok, maliyet ve recall iş akışlarının doğru çalıştığı gösterilir.

## 13. Uygulama öncesi karar kapıları

Aşağıdaki noktalar kodlama başlamadan önce ilgili belgelerde kesinleştirilmelidir.

| ID | Karar | Neden önemli | Gereken belge güncellemesi |
|---|---|---|---|
| WF-01 | Fire çıktısı için ürün/lot alanları nullable mı? | DB constraint ve DTO tutarlılığı | Cilt 1.2 + Cilt 1.3 + Cilt 1.4 |
| WF-02 | Üretim girdisi stoktan hangi aşamada düşer? | Stok doğruluğu ve yarım emir davranışı | Cilt 1.2 + Cilt 1.3 |
| WF-03 | Satış ve sevkiyat stok çıkışının sahibi hangisi? | **KAPATILDI — dispatch tek OUT sahibidir** | Cilt 1.2 + Cilt 1.3 + kullanıcı onayı |
| WF-04 | Lot bakiyesi ile defter hareketi transaction/lock stratejisi | Eşzamanlı satışlarda negatif stok önleme | Cilt 1.2 + Cilt 1.3 |
| WF-05 | Recall aktivasyonu senkron mu, ara durum/outbox mı? | Büyük genealogy grafiği ve atomiklik | Cilt 1.3 + mimari karar |
| WF-06 | Recall çözümünde blokaj otomatik kalkar mı? | Güvenlik ve yanlış satış riski | Cilt 1.3 + rol/izin matrisi |
| WF-07 | Ağırlık farkı toleransı ve gerekçe zorunluluğu | Kuzu parçalama denetimi | Gereksinim + Cilt 1.2 |
| WF-08 | Tamamlanmış iş emirleri nasıl ters kaydedilir? | Audit ve maliyet düzeltmesi | Cilt 1.2 + Cilt 1.3 |
| WF-09 | Kabul/üretim/parçalama komutları için idempotency standardı | Timeout sonrası yinelenen kayıtları önleme | Cilt 1.3 + Cilt 1.4 |
| WF-10 | `IN_PROGRESS`, `PREPARED`, `ACTIVATING` gibi ara durumlar gerçekten gerekli mi? | İlk MVP kararı: recall için `ACTIVATING` yok; diğer durumlar yalnızca iş kuralı gerektiriyorsa kullanılır. | Durum enumları ve API |

## 14. Önerilen uygulama sırası

1. WF-01 ve WF-03 gibi veri bütünlüğünü doğrudan etkileyen kararları netleştir.
2. Durum enumlarını tek bir ortak sözlükte sabitle.
3. Her kritik komut için ön koşul, transaction etkisi ve hata kodlarını Cilt 1.3'e bağla.
4. Cilt 1.2 veri modelinde gerekli unique/check/foreign-key kısıtlarını doğrula.
5. Backend servis fonksiyonlarını UI'dan bağımsız yaz ve transaction sınırlarını test et.
6. Önce stok kabulü ve stok defteri testlerini; sonra üretim/parçalama; ardından satış/sevkiyat; en son recall uçtan uca testlerini tamamla.
7. Android ve web istemcilerini yalnızca sözleşme testleri sabitlendikten sonra bağla.
8. AI tahminlerini deterministik stok ve recall akışlarından ayrı doğrula.

## 15. Tamamlanma ölçütleri

Bu cilt uygulamaya hazır kabul edilmeden önce:

- Her iş akışının geçerli/geçersiz durum geçişleri listelenmiş olmalı.
- Stok hareketi ve bakiye güncellemesi aynı transaction içinde olmalı.
- Negatif stok ve çift tüketim testlerle engellenmeli.
- Aynı komutun tekrarında mükerrer stok etkisi oluşmamalı.
- Recall aktivasyonu ile eşzamanlı satış davranışı test edilmiş olmalı.
- Lot genealogy hem geriye hem ileriye miktarlarıyla doğrulanmalı.
- Ağırlık ve maliyet farkları görünür olmalı; açıklanmayan değerler uydurulmamalı.
- AI hatası operasyonel kayıtları bozmamalı.
- WF-01–WF-10 kararlarının durumu belgelerde açıkça işaretlenmeli.

---

**Sonraki cilt önerisi:** Cilt 1.6 — Backend Uygulama Planı ve Modül Sınırları. Bu belge, onaylanmış veri/API/iş akışı sözleşmelerini FastAPI paket yapısına, servis katmanlarına, transaction sahipliğine, migration sırasına ve backend geliştirme görevlerine dönüştürmelidir.

## Revizyon 1.11 — Onaylanan workflow kuralları

### WF-01 — Parçalama çıktısı ve fire ayrımı
Cilt 1.17 kararı: stokta izlenen kesim/yan ürün çıktısı `butchering_outputs` tablosundadır ve ürün/lot gerektirir. Fire ayrı `butchering_waste_records` tablosundadır; ürün/çıktı lotu ve stok IN hareketi oluşturmaz.

### WF-02 — Üretim tüketimi
İlk sürümde rezervasyon yoktur. `IN_PROGRESS` geçişinde stok düşülmez. Üretim tamamlanırken gerçek tüketim miktarlarıyla `OUT` hareketleri, bitmiş ürün `IN` hareketleri, lot genealogy, maliyet ve audit tek transaction'da yazılır. Hata olursa tüm etkiler rollback olur.

### WF-03 — Satış/sevkiyat stok çıkışı
**Durum: KAPATILDI — proje sahibi onayı alındı.** Aynı fiziksel miktar için yalnızca bir `OUT` hareketi oluşturulur. Dispatch fiziksel teslimi ve stok çıkışını kaydeder; satış kaydı ticari işlemi temsil eder ve stok düşmez. Dispatch idempotent olmalı; aynı sevkiyatın tekrar dispatch edilmesi ikinci hareket yaratmamalıdır. Herhangi bir fiziksel çıkış dispatch kaydıyla ilişkilendirilmelidir.

### WF-04 — Recall aktivasyonu ve çözümü
Recall aktivasyonu MVP'de senkron ve atomiktir. Aktivasyonun bir parçası başarısızsa hiçbir kısmi blokaj kalmaz. `ACTIVATING` kullanılmaz. Recall `RESOLVED` olduğunda lot blokajı korunur; blokajı kaldırmak için ayrı, rol kontrolü ve audit içeren `release/unblock` komutu gerekir.

### WF-05 — Ağırlık farkı
Yarışma PDF'si sayısal tolerans belirlemez. Tolerans `TBD`/konfigürasyon olarak kalır. Sistem farkı sessizce sıfırlamaz ve otomatik neden uydurmaz; gerekli olduğunda kullanıcı gerekçesi ve audit kaydı ister.

### WF-06 — Düzeltme ve ters kayıt
Tamamlanmış işlem silinmez veya geçmiş satırları sessizce güncellenmez. Kaynak işleme bağlı düzeltme/ters kayıt oluşturulur; ters stok hareketleri ve audit aynı transaction içinde yazılır. Tekrar komut ikinci etki üretmemelidir.

### WF-07 — Kritik komutların tekrar çağrılması
Satışta `Idempotency-Key` zorunludur. Diğer kritik komutlar (lot kabulü, üretim/parçalama tamamlama, dispatch, recall aktivasyonu, stok düzeltme) için endpoint bazında idempotency key veya deterministik `INVALID_STATE_TRANSITION`/uygun conflict yanıtı tanımlanır.

### Kanonik durum ve izin notları
Recall MVP durumları asenkron `ACTIVATING` olmadan tanımlanır. Genel stok düzeltme yalnızca `ADMIN`; sevkiyat oluşturma/dispatch `ADMIN`/`SALES`; AI tahmin başlatma `ADMIN`/`OPERATOR`, sonuç okuma `ADMIN`/`OPERATOR`/`TRACEABILITY_MANAGER`/`VIEWER` olarak ele alınır. Cilt 1.3 ve 1.8/1.9 bu matrise uymalıdır.
