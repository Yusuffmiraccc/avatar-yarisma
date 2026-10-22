# Cilt 1.19 — Canonical Workflow IDs & State Registry

**Tarih:** 22 Ekim 2026  
**Durum:** Kanonikleştirme taslağı — açık maddeler proje sahibi onayı bekler  
**Bağlı belgeler:** Cilt 1.2, 1.3, 1.4, 1.5, 1.15, 1.16, 1.17, 1.18  
**Kod/migration:** Bu cilt kod üretmez; migration veya veritabanı değişikliği için onay değildir.

## 1. Amaç ve bağlayıcılık

Bu cilt, workflow kimliklerinin ve durum isimlerinin belgeler arasında farklılaşmasını önlemek için tek bir kayıt noktası oluşturur. Mevcut belgede açıkça onaylanmış kurallar **ONAYLI** olarak işaretlenir. Kaynakların yalnızca önerdiği veya tam tarif etmediği ayrıntılar **AÇIK** kalır; uygulayıcı LLM bunları tahmin ederek uygulayamaz.

Normatif öncelik: yarışma gereksinimi → proje sahibinin açık onayı/ADR/DEC → birbiriyle tutarlı ERD/API/DTO sözleşmeleri → onaylı workflow kararları → bu registry. Bir çelişki bulunursa sessizce bir kaynak seçilmez; blokaj raporu hazırlanır.

## 2. Kanonik workflow ID kataloğu

| ID | Kanonik ad | Kapsam | Durum |
|---|---|---|---|
| WF-01 | Butchering Output & Waste | Kesim/yan ürün ve ayrı fire kayıtları | ONAYLI — Cilt 1.17 |
| WF-02 | Production Consumption & Completion | Üretim emri, gerçek tüketim ve tamamlanma | ONAYLI — Cilt 1.5 rev. 1.11 |
| WF-03 | Sale & Dispatch Stock Ownership | Ticari satış ile fiziksel stok çıkışının ayrılması | ONAYLI — proje sahibi onayı |
| WF-04 | Recall Activation, Resolution & Release | Recall blokajı, çözüm ve ayrı serbest bırakma | ONAYLI temel kural; ayrıntılar açık |
| WF-05 | Weight Balance & Variance | Parçalama ağırlık dengesi ve tolerans | Tolerans AÇIK |
| WF-06 | Correction & Reversal | Tamamlanmış işlemlerin izlenebilir düzeltmesi | Genel kural ONAYLI; işlem bazlı ayrıntılar açık |
| WF-07 | Critical Command Retry | Kritik komutların tekrar davranışı | Genel ilke ONAYLI; endpoint matrisi açık |
| WF-08 | Lot Receipt & Stock Entry | Satın alma/kabul ve lot oluşturma | Akış tanımlı; idempotency ve kesin durumlar açık |
| WF-09 | AI Prediction Lifecycle | Tahmin isteği, sonuç ve hata davranışı | İşlev tanımlı; kalıcı durum enumu gerekliliği açık |
| WF-10 | MVP State Minimalism | Gereksiz ara durumları dışarıda tutma | ONAYLI ilke; entity bazında nihai enum eşlemesi açık |

**Not:** Eski belgelerde WF-01–WF-10 numaraları farklı anlamlarda kullanılmış olabilir. Bu tablo yeni kanonik ID eşlemesidir; geçmiş metinler değiştirilirken eski referanslar sessizce yeniden yorumlanmamalı, revizyon günlüğüne yazılmalıdır. WF-03 sevkiyat sahipliği için en güçlü dayanak Cilt 1.14 ve Cilt 1.5 revizyon 1.11'dir.

## 3. Durum registry'si — yalnızca kaynaklarda desteklenen durumlar

Bu tablo tüm entity'lerin son enum listesinin yerine geçmez; yalnızca belgelerde açıkça görünen ve kanonikleştirilebilen durumları kaydeder. Nihai enum değerleri Cilt 1.3 API, Cilt 1.2 ERD ve Cilt 1.4 DTO/test sözleşmesiyle çapraz kontrol edilmeden ORM enumu olarak kodlanamaz.

| Entity/alan | Kanonik değer(ler) | Kural | Durum |
|---|---|---|---|
| Üretim emri | `IN_PROGRESS`, `COMPLETED`, `CANCELLED` | `IN_PROGRESS` stok düşmez; tamamlama etkileri atomiktir. Etkili işlem doğrudan iptal edilmez. | Kaynakta destekli; nihai enum çapraz kontrolü gerekli |
| Sevkiyat | `SHIPPED` | `DISPATCHED` komut/işlem adıdır, kalıcı durum enumu değildir. `PREPARED` ayrı kalıcı durum değildir. | ONAYLI |
| Recall | `DRAFT`, `ACTIVE`, `RESOLVED` | Aktivasyon senkron/atomiktir; `ACTIVATING` yoktur. `RESOLVED` blokajı tek başına kaldırmaz. | ONAYLI temel sözleşme; API enum kontrolü gerekli |
| Lot satış blokajı | Ayrı blokaj/serbest bırakma davranışı | Recall çözümleme ile lotun satışa açılması ayrı komutlardır. Tam değer/alan adı mevcut ciltlerde tutarlı biçimde kanıtlanmadan enum adı atanmaz. | AÇIK — alan/enum crosswalk gerekli |
| Satış | Kalıcı durum listesi bu ciltte sabitlenmedi | Satış ticari kayıttır; satışın kendisi stok `OUT` üretmez. | AÇIK — Cilt 1.3 ile karşılaştır |
| Kasaplık emri | Nihai enum listesi bu ciltte sabitlenmedi | Tamamlama ağırlık ve maliyet mutabakatına bağlıdır; fire ayrı tabloda tutulur. | AÇIK — Cilt 1.2/1.3/1.4 crosswalk |
| Lot kabulü | Nihai enum listesi bu ciltte sabitlenmedi | Lot kabulü/stock entry akışı ve tekrar davranışı API ile uyumlu olmalı. | AÇIK |
| AI tahmin işi | Kalıcı state enumu onaylanmadı | Tahmin başarısızlığı gerçek stok/maliyet/recall kaydını değiştiremez. | AÇIK; yalnızca ihtiyaç kanıtlanırsa kalıcı state ekle |

## 4. Onaylı geçişler ve yan etkiler

### 4.1 Üretim emri

| Geçiş/komut | Önkoşul | Tek transaction içindeki etkiler | Hata davranışı |
|---|---|---|---|
| Oluştur → `IN_PROGRESS` | Gerekli emir ve referans kayıtlar geçerli | Yalnızca durum/iş akışı kaydı; stok rezervasyonu veya stok düşümü yok | Geçersiz veri/durum reddedilir |
| `IN_PROGRESS` → `COMPLETED` | Gerçek tüketim, hizmet maliyeti, iyi ürün miktarı ve lot bilgileri doğrulanmış; sıfır çıktı engellenmiş | Girdi lotları `OUT`, bitmiş lot `IN`, genealogy, maliyet snapshot'ı, bakiye, durum ve audit | Herhangi bir adım başarısızsa tüm transaction rollback |
| Taslak/etkisiz emir → `CANCELLED` | Henüz stok/maliyet etkisi yok | İptal durumu ve audit | İş etkisi varsa doğrudan iptal yok; ters kayıt süreci |

Rezervasyon ilk sürüm kapsamı dışıdır. Stok düşümü `IN_PROGRESS` anında değil, tamamlanma transaction'ında gerçekleşir.

### 4.2 Kasaplık/parçalama emri

Tamamlama öncesi girdi miktarı, `CUT` ve stokta izlenen `BYPRODUCT` çıktıları, fire ağırlığı ve açıklanmış/izin verilen fark uzlaştırılır. Maliyet tahsisi backend tarafından hesaplanır. Zorunlu mutabakat:

`SUM(butchering_outputs.allocated_cost) + SUM(butchering_waste_records.allocated_cost) = butchering_orders.total_purchase_cost`

Ağırlık toleransı sayısal olarak onaylanmamıştır; uygulayıcı bir sayı varsayamaz. Tolerans kararı ve `BY_VALUE` fire formülü kapanmadan kasaplık tamamlama için tüm kabul testleri nihai sayılmaz.

### 4.3 Satış ve sevkiyat

- Satış ticari işlemi temsil eder; satış kaydı tek başına stok `OUT` hareketi üretmez.
- Fiziksel sevkiyat/dispatch tek stok çıkışı sahibidir ve `SHIPPED` durumuyla kaydedilir.
- Aynı fiziksel miktar için ikinci `OUT` oluşturulamaz.
- Dispatch tekrar çağrıldığında ikinci stok hareketi üretilmez; idempotency veya deterministik conflict davranışı API bazında tanımlanır.
- Recall/blokajlı veya yetersiz bakiyeli lotun dispatch/satış süreci backend'de reddedilir; istemci ekranına güvenilmez.

### 4.4 Recall

- Recall taslağı (`DRAFT`) oluşturmak tek başına satış blokajı başlatmaz.
- `DRAFT` → `ACTIVE` aktivasyonu senkron ve atomiktir; `ACTIVATING` ara durumu kullanılmaz.
- İlgili lot/ürün üzerindeki satış engeli backend tarafından uygulanır.
- `ACTIVE` → `RESOLVED` geçişi geçmişi silmez ve blokajı otomatik kaldırmaz.
- Lotu yeniden satılabilir yapmak için ayrı, açıkça yetkilendirilmiş, audit kaydı üreten release/unblock komutu gerekir.
- Recall için kısmi blokaj bırakacak başarısız aktivasyon kabul edilmez.

## 5. Ortak geçiş kuralları

1. Her komut, kaydın mevcut durumunu ve geçişin izinli olup olmadığını kontrol eder.
2. Stok, bakiye, genealogy, maliyet, durum ve audit etkileri ilgili iş akışının belirttiği tek transaction içinde yazılır.
3. Geçersiz geçiş stok/maliyet üzerinde kısmi etki bırakmaz; uygun `409` conflict ve kanonik hata kodu döner.
4. Kritik operasyon kayıtları hard-delete edilmez. Düzeltme/ters kayıt kaynak işleme bağlanır ve geçmişi korur.
5. Satışta `Idempotency-Key` zorunludur. Aynı key ve aynı body ilk sonucu döndürür; aynı key ve farklı body `409 Conflict` verir.
6. Diğer kritik komutlarda endpoint bazında idempotency key veya deterministik state-conflict davranışı tanımlanır. Nihai endpoint matrisi Cilt 1.21'de kapatılacaktır.
7. Stok bakiyesi ve ledger hareketleri aynı transaction'da güncellenir; eşzamanlı işlemler negatif stok doğuramaz. Kesin lock/optimistic concurrency tekniği DB/backend sözleşmesinde tanımlanmalıdır.
8. Tahmin veya AI başarısızlığı, stok, lot, maliyet veya recall kaydını değiştirmez.

## 6. Açık kararlar — kodlamayı bloke eden maddeler

| ID | Açık karar | Neden bloke ediyor? | Kapatılacağı yer |
|---|---|---|---|
| REG-01 | Üretim, kasaplık, satış, lot kabulü ve recall için API'deki tüm durum değerlerinin tek tek karşılaştırılması | ORM/DTO/DB enum uyuşmazlığı | Cilt 1.22 |
| REG-02 | Lot blokajı ve release alanı/enum adları ve çoklu recall davranışı | Recall güvenliği ve tekrar çağrısı | Cilt 1.20–1.22 |
| REG-03 | Recall çözümünde zorunlu iletişim/aksiyonların kesin listesi | `RESOLVED` koşulları test edilemiyor | Cilt 1.20/1.24 |
| REG-04 | Kasaplık ağırlık toleransının sayısı, birimi ve yapılandırma kaynağı | Tamamlama kabul/ret sonucu belirlenemiyor | Cilt 1.23 |
| REG-05 | `BY_VALUE` maliyet tahsisinde fire maliyeti formülü | Maliyet dağıtım sonucu belirlenemiyor | Cilt 1.23 |
| REG-06 | Çoklu girdi lotu için fire kaydının hangi lot(lar)a bağlanacağı | Genealogy ve maliyet ataması belirsiz | Cilt 1.22–1.23 |
| REG-07 | Lot kabulü, üretim/parçalama tamamlaması, dispatch, recall aktivasyonu ve düzeltme için retry/idempotency standardı | Timeout sonrası yinelenen etki riski | Cilt 1.21 |
| REG-08 | Her workflow için nihai error code ve HTTP status | İstemci ve test davranışı tutarsız olabilir | Cilt 1.21 |
| REG-09 | Her workflow'un başarılı response/request_id sözleşmesi | API response'ları tekleştirilmemiş | Cilt 1.21 |
| REG-10 | Tüm state transition'ların role/permission eşlemesi | Yetkisiz durum değişikliği riski | Cilt 1.20 |
| REG-11 | Tamamlanmış üretim/parçalama/dispatch işlemleri için işlem bazlı ters kayıt kuralları | Maliyet ve stok düzeltme etkileri tam belirlenmemiş | Cilt 1.22/1.24 |

## 7. Uygulayıcı LLM için zorunlu kurallar

- Bu ciltteki **ONAYLI** kuralları uygula; **AÇIK** maddeler için varsayım yapma.
- Durum enumlarını yalnızca bu cilde bakarak oluşturma; Cilt 1.2 ERD, 1.3 API, 1.4 DTO/test ve 1.16 crosswalk ile birebir doğrula.
- `DISPATCHED` durum enumu veya `PREPARED` kalıcı sevkiyat durumu ekleme; bu ciltte açıkça reddedilmiştir.
- Recall için `ACTIVATING` ekleme; aktivasyon senkron ve atomiktir.
- Recall çözümünün blokajı kaldırdığını varsayma; release ayrı komuttur.
- Satış için stok `OUT` hareketi oluşturma; dispatch tek stok çıkışı sahibidir.
- Tolerans, maliyet formülü, enum veya permission konusunda kaynaklar çelişirse kodlama/migration'ı durdur ve madde bazlı blokaj raporu ver.
- Proje sahibinin ayrıca açık onayı olmadan migration dosyası oluşturma veya veritabanı oluşturma/değiştirme.

## 8. Cilt 1.19 tamamlanma ölçütleri

- [x] Workflow ID'leri için tek kayıt tablosu oluşturuldu.
- [x] Kaynaklarda açıkça onaylanmış üretim, dispatch ve recall temel kuralları kaydedildi.
- [x] Kaynaklarda desteklenmeyen nihai enum değerleri uydurulmadan açık bırakıldı.
- [ ] Cilt 1.2/1.3/1.4/1.16 ile tam enum çapraz kontrolü tamamlandı.
- [ ] REG-01–REG-11 kararları kapatıldı veya proje sahibi tarafından açıkça kapsam dışı bırakıldı.
- [ ] Cilt 1.20–1.24 ve final migration gate tamamlandı.

**Sonuç:** Cilt 1.19 registry ve geçiş kurallarını tek yerde toplar; ancak tüm durum enumları ve açık kararlar kapanmadığı için kodlama devri veya migration için nihai onay değildir.
