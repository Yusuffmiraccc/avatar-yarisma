# Cilt 1.23 — Son Tüketim Tarihi, Fire Maliyeti, Ağırlık Toleransı ve Birim Dönüşümü


> **Normatif güncelleme — 22 Ekim 2026 (Cilt 1.32):** Bu belgedeki daha eski ve çelişen taslak ifadeler için `volume-01-32-approved-decisions-and-cross-check.md` ile Cilt 1.31'in onay kaydı önceliklidir. Bu not doküman sözleşmesini günceller; migration veya veritabanı değişikliği izni değildir.

**Tarih:** 22 Ekim 2026  
**Durum:** Kısmi karar onayı alındı; kalan kararlar açık  
**Amaç:** Cilt 1.17'de kayıtlı açık kararları sayısal örneklerle çözümleyip ERD/API/test sözleşmelerine aktarılabilir hale getirmek.  
**Kod/migration:** Bu cilt uygulama kodu veya migration üretmez; veritabanını oluşturma/değiştirme yetkisi vermez.

## 1. Normatiflik ve kaynak ayrımı

Etiketler:
- **[PDF]** Yarışma değerlendirme belgesinde açık gereksinim.
- **[ONAYLI KARAR]** Proje sahibinin önceki açık onayı.
- **[ÖNERİ]** Bu ciltte önerilen, henüz onaylanmamış tasarım.
- **[KARAR BEKLİYOR]** Proje sahibinin onayı olmadan bağlayıcı hale gelmeyecek konu.

**[PDF]** Son tüketim tarihi, hammadde lotlarına “uygun olduğunda” atanır. Parçalama işleminde girdi ağırlığı; stokta izlenen kesimler, stokta izlenen yan ürünler, fire ve açıklanan/izin verilen fark ile uzlaştırılmalıdır. Dağıtılan toplam maliyet, toplam girdi maliyetine eşit olmalıdır.

**[ONAYLI KARAR]** Fire `butchering_waste_records` tablosunda tutulur; fire satılabilir ürün veya stok girişi yaratmaz. Fire ağırlığı kütle dengesine dahil edilir. Fire ve stok çıktılarının maliyetleri birlikte girdi maliyetine eşit olmalıdır. `expiry_date`, uygulanabilir ürün/lotlarda zorunlu, diğerlerinde `NULL` olabilir.

Bu ciltteki formüller ve örnekler **öneri** niteliğindedir; proje sahibi onayı olmadan kesin karar olarak değerlendirilmemelidir.

## 2. Karar kayıtları özeti

| ID | Konu | Öneri | Durum |
|---|---|---|---|
| DEC-123-01 | Son tüketim tarihi uygulanabilirliği | Ürün kartında açık `requires_expiry_date` politikası | KARAR BEKLİYOR |
| DEC-123-02 | BY_WEIGHT maliyet tahsisi | Fire dahil tüm tartılmış çıktı kategorilerine ağırlık oranında maliyet tahsisi | ONAYLANDI (22 Ekim 2026) |
| DEC-123-03 | BY_VALUE maliyet tahsisi | Fireye ayrı bir maliyet payı atanabilsin; bu tutar satılabilir stok çıktısı maliyeti sayılmasın. Fire maliyetinin BY_VALUE altında nasıl hesaplanacağı ayrıca kararlaştırılacak. | KISMEN ONAYLANDI; FORMÜL AÇIK |
| DEC-123-04 | Ağırlık toleransı | Sabit gizli varsayım yok; konfigüre edilebilir tolerans, başlangıçta 0.000 kg önerisi | KARAR BEKLİYOR |
| DEC-123-05 | Birim standardı | Ağırlık dengeleme için kg canonical unit; g ve kg dönüşümü | KARAR BEKLİYOR |
| DEC-123-06 | Fire reason code | Başlangıçta kontrollü sözlük | KARAR BEKLİYOR |
| DEC-123-07 | Birden çok girdi lotu | Her fire satırı tek kaynak input lotuna bağlansın; birden çok kaynak varsa ayrı satırlar | KARAR BEKLİYOR |
| DEC-123-08 | Yuvarlama farkı | Son tahsis satırına deterministik residual; toplam tam eşitlenir | KARAR BEKLİYOR |

## 3. Son tüketim tarihi uygulanabilirliği

### 3.1 Önerilen kural

**[ÖNERİ]** Ürün kartında `requires_expiry_date BOOLEAN NOT NULL DEFAULT FALSE` tutulur. Bu alan yalnızca ürünün izlenebilir lotlarında son tüketim tarihinin zorunlu olup olmadığını belirtir; lot kaydının kendisindeki `expiry_date` ise gerçek tarihtir.

- `requires_expiry_date = TRUE` ise yeni lot oluşturulurken `expiry_date` zorunludur.
- `requires_expiry_date = FALSE` ise `expiry_date` `NULL` olabilir.
- Boş string, sıfır tarih, `UNKNOWN` gibi sentinel değerler kullanılmaz.
- Bir ürünün politikası değişirse geçmiş lotların `expiry_date` değerleri otomatik doldurulmaz veya silinmez.
- API doğrulaması ve servis katmanı aynı kuralı uygular; DB düzeyindeki doğrulama mümkünse tutarlı biçimde eklenir. MySQL `CHECK`/ilişkili doğrulama seçimi schema review sırasında doğrulanır.

**Neden öneriliyor?** “Uygun olduğunda” koşulunu tek ve denetlenebilir yerde tanımlar; kodlama LLM'sinin ürün adı veya tahmini üzerinden son tüketim tarihi gerekip gerekmediğine karar vermesini engeller.

**Alternatif:** Son tüketim tarihi zorunluluğunu global olarak zorunlu/opsiyonel yapmak. Bu, PDF'deki koşullu gereksinimi yeterince temsil etmez; önerilmez.

### 3.2 Kabul testleri

1. `requires_expiry_date=true`, `expiry_date=null` → validation hatası.
2. `requires_expiry_date=true`, geçerli tarih → lot oluşturulur.
3. `requires_expiry_date=false`, `expiry_date=null` → lot oluşturulur.
4. Tarih alanı boş string veya geçersiz format → validation hatası; `NULL` ile eşdeğer sayılmaz.
6. Ürün politikası sonradan değiştiğinde geçmiş lotlar değiştirilmez.

## 4. Fire maliyetinin dağıtımı

### 4.1 Ortak zorunlu eşitlik

Her tamamlanmış parçalama emrinde:

`SUM(butchering_outputs.allocated_cost) + SUM(butchering_waste_records.allocated_cost) = butchering_orders.total_purchase_cost`

Tüm maliyet hesapları `Decimal`/sabit hassasiyetli decimal türleriyle yapılır; `float` kullanılmaz. Maliyet backend tarafından hesaplanır, istemciden gelen `allocated_cost` kabul edilmez.

### 4.2 BY_WEIGHT — önerilen hesap

**[ÖNERİ]** Ağırlık anahtarında maliyet; stokta izlenen kesimler, stokta izlenen yan ürünler ve ölçülmüş fire dahil, ağırlığı bilinen bütün kütle kategorilerine dağıtılır.

Formül:

`allocated_cost_i = total_purchase_cost × weight_i / total_measured_weight`

`total_measured_weight = SUM(output weights) + SUM(waste weights)`

Örnek: Girdi maliyeti €100; 8 kg kesim, 1 kg yan ürün, 1 kg fire. Ölçülen toplam 10 kg.
- Kesimler: €80
- Yan ürün: €10
- Fire: €10
- Toplam: €100

Bu yöntem fire maliyetini ayrı bir kayıtta görünür kılar. Fire satılabilir stok değildir; maliyet payı raporlama/uzlaştırma içindir.

### 4.3 BY_VALUE — kararın durumu ve kalan formül

**[KISMEN ONAYLANDI — 22 Ekim 2026]** Proje sahibi, fireye maliyet payı atanabilmesi ve bu tutarın satılabilir stok çıktısı maliyeti olarak gösterilmemesi yönündeki öneriyi onayladı. Bu onay, `BY_VALUE` altında fireye otomatik olarak `0` maliyet atanmasını onaylamaz. Fire maliyetinin nasıl hesaplanacağı ve değer anahtarının kaynağı hâlâ kararlaştırılmalıdır. Kodlama LLM’si bu boşluğu kendi varsayımıyla doldurmamalıdır.

Geçici hesaplama çerçevesi: değer taşıyan stok çıktılarının tahsis maliyetleri ile fireye ayrı tahsis edilen maliyetlerin toplamı, girdi maliyetine eşit olmalıdır. Fire maliyeti için onaylı formül tanımlanmadan `BY_VALUE` emri tamamlanmış sayılmamalıdır.

Formül:

`allocated_cost_i = total_purchase_cost × output_value_basis_i / SUM(all value-bearing output value bases)`

Sayısal örnek, fireye tahsis edilecek tutar için bağlayıcı formül seçilmeden verilemez. Örneğin kesim A/B değer anahtarları €60/€40 olsa bile fire maliyetinin 0, ağırlık oranında veya ayrı kayıp hesabıyla bulunması birbirinden farklı sonuçlar üretir. Bu nedenle örnek sonuç uydurulmayacak; değer anahtarı ve fire payı kuralı onaylandıktan sonra eklenecektir.

### 4.4 Sıfır payda ve yuvarlama

- `BY_WEIGHT` için toplam ölçülen ağırlık `0` ise işlem tamamlanamaz.
- `BY_VALUE` için toplam değer anahtarı `0` veya eksik ise işlem tamamlanamaz; ağırlık yöntemine otomatik düşülmez.
- Hesaplamalar ara adımlarda decimal hassasiyetle yapılır.
- Para kolonları 4 ondalık hassasiyetliyse yuvarlama sonrası kalan fark deterministik biçimde son tahsis satırına eklenebilir. Bu kural kullanıcı onayı bekler.
- Her iki yöntemde de tamamlanma öncesi toplam maliyet eşitliği doğrulanır; eşit değilse transaction rollback olur.

## 5. Ağırlık dengesi ve tolerans

### 5.1 Denklem

`variance_kg = input_weight_kg - output_weight_kg - byproduct_weight_kg - waste_weight_kg`

Burada `output_weight` yalnızca stokta izlenen `CUT` çıktıları kapsar; `BYPRODUCT` ayrıca sayılır. Her kategori aynı fiziksel ağırlığı iki kez saymamalıdır.

### 5.2 Önerilen politika

**[ÖNERİ]** Tolerans birim bazlı konfigürasyon olmalı ve API cevabında gerçek fark, izin verilen tolerans ve sonuç açıkça görünmelidir. Başlangıç için sıfır tolerans en güvenli ve denetlenebilir varsayımdır; fakat ölçüm cihazı hassasiyeti ve işletme pratiği bilinmeden bunu bağlayıcı yapmak doğru olmayabilir.

- `abs(variance_kg) <= tolerance_kg` ise denge başarılıdır.
- Fark toleransı aşarsa tamamlama reddedilir veya yetkili kullanıcı tarafından gerekçeli istisna olarak onaylanır. Hangi seçenek kullanılacağı karara bağlanmalıdır.
- İstisna varsa `reason_code`, açıklama, onaylayan kullanıcı ve audit kaydı zorunlu olmalıdır.
- Sessizce `variance_kg` sıfıra yuvarlanmaz; ham ölçümler korunur.

**KARAR BEKLİYOR:** Sayısal tolerans, sıfır toleransın mı yoksa örneğin `0.050 kg` gibi işletme eşiğinin mi kullanılacağı ve tolerans dışı fark için bloke/istisna davranışı.

## 6. Birimler ve dönüşüm

### 6.1 Önerilen başlangıç kapsamı

- Ağırlık canonical unit: `kg`.
- İzinli ağırlık birimleri: `kg`, `g`; dönüşüm: `1 kg = 1000 g`.
- Paket/adet gibi sayım birimleri ağırlık birimine çevrilmez. Bir ürünün adet başına ağırlığı açıkça tanımlı ve bağlayıcı değilse `piece → kg` dönüşümü yapılmaz.
- Her ölçümde girilen miktar ve birim saklanabilir; karşılaştırma/hesaplama öncesi normalize edilmiş kg değeri kullanılır.
- Bilinmeyen veya boyutsal olarak uyumsuz birimler validation hatası üretir.
- Ağırlık ölçümlerinde onaylı decimal hassasiyet (DEC-001: quantity/weight `DECIMAL(19,6)`) korunur.

### 6.2 Dönüşüm testi örnekleri

- `2500 g` → `2.500000 kg`.
- `0.75 kg` → `750 g`.
- `85 piece` → kg dönüşümü tanımlı değilse reddedilir.
- `-1 kg` ağırlık miktarı → reddedilir; negatif miktar için düzeltme kaydı kullanılır, fiziksel ölçüm olarak kabul edilmez.
- Bilinmeyen `lb` birimi ilk sürümde reddedilir; sonradan desteklenirse sabit dönüşüm katsayısı ve testleri eklenir.

## 7. Birden fazla girdi lotu ve fire kaydı

**[ÖNERİ]** Her `butchering_waste_records` satırı tam olarak bir `input_lot_id` ve bir ölçüm kaynağına bağlanır. Tek işlemde iki girdi lotundan fire çıkıyorsa her lot için ayrı fire satırı oluşturulur. Böylece ileri/geriye izlenebilirlik ve lot bazlı miktar açıklaması belirsiz kalmaz.

- Bir fire satırı iki lota aynı anda bağlanmaz.
- Fire miktarının lotlara nasıl paylaştırılacağı fiziksel ölçümle bilinmiyorsa sistem otomatik ve sessiz tahmin yapmaz; işlem bloklanır veya yetkili kullanıcı her lot için açık miktar girer.
- Girdi lotuna göre toplam tüketim, çıktılar, fire ve varyans ayrı ayrı doğrulanmalıdır.
- Aynı fiziksel fire kaydı iki farklı lota kopyalanarak toplam fire ağırlığı şişirilemez.

## 8. Önerilen reason_code sözlüğü

Aşağıdaki liste **öneridir; proje sahibi onayı olmadan kanonik enum değildir**:

| Kod | Açıklama |
|---|---|
| `TRIMMING_LOSS` | Kesim/temizleme sırasında ayrılan fire |
| `BONE_WASTE` | Kullanılmayan kemik/kemiksi artık |
| `FAT_TRIMMING` | Ayrılan ve stok yan ürünü olarak izlenmeyen yağ |
| `CONTAMINATION_DISCARD` | Kontaminasyon nedeniyle imha |
| `QUALITY_REJECTION` | Kalite nedeniyle reddedilen parça |
| `PROCESS_LOSS` | Süreç kaynaklı ölçülmüş kayıp |
| `OTHER` | Diğer; açıklama zorunlu |

Önerilen doğrulama: `reason_code=OTHER` ise `reason_note` zorunlu. Her kod için `reason_note` opsiyonel olabilir. Kodlar kullanıcı tarafından serbest metin olarak yazılmaz; kontrollü sözlükten seçilir.

## 9. Karar verilmesi gereken sorular — proje sahibi onayı

| ID | Karar | Önerilen varsayılan | Onay durumu |
|---|---|---|---|
| Q-123-01 | Son tüketim tarihini hangi kural belirlesin? | Ürün kartında `requires_expiry_date` | Açık |
| Q-123-02 | `BY_WEIGHT` fire maliyeti nasıl ele alınsın? | Fire ağırlığı dahil, fireye maliyet payı verilsin | ONAYLANDI |
| Q-123-03 | `BY_VALUE` fire maliyeti nasıl ele alınsın? | Fireye ayrı maliyet payı atanabilsin; stok çıktısı maliyetinden ayrı gösterilsin | KISMEN ONAYLANDI; FORMÜL AÇIK |
| Q-123-04 | `BY_VALUE` değer anahtarı ne olsun? | Parçalama emrinde onaylı değer girdisi; kaynağı ayrıca seçilmeli | AÇIK |
| Q-123-05 | Ağırlık toleransı kaç olsun? | Varsayılan 0 kg; tolerans dışı fark bloke edilsin | Açık |
| Q-123-06 | Tolerans dışı fark için yetkili istisna olsun mu? | İlk sürümde hayır; gerekirse audit'li istisna | Açık |
| Q-123-07 | İlk sürümde hangi ağırlık birimleri desteklensin? | kg ve g | Açık |
| Q-123-08 | Fire reason code listesi onaylansın mı? | Bölüm 8'deki liste | Açık |
| Q-123-09 | Çoklu lot fire ölçümü nasıl kaydedilsin? | Her satır tek girdi lotuna bağlansın | Açık |
| Q-123-10 | Decimal yuvarlama farkı nasıl dağıtılsın? | Residual son tahsis satırına | Açık |

## 10. Kabul testleri — karar sonrası bağlayıcı hale getirilecek

1. Son tüketim tarihi uygulanabilirliği ürün kartı kuralına göre doğrulanır.
2. BY_WEIGHT örneğinde €100 maliyet; 8 kg kesim, 1 kg yan ürün, 1 kg fire için toplam tahsis €100 olur.
3. BY_VALUE altında fireye atanan ayrı maliyet, satılabilir stok çıktısı maliyetine eklenmez; fire maliyet formülü onaylanana kadar bu akış tamamlanamaz.
4. BY_VALUE toplam değer paydası 0 ise işlem tamamlanamaz ve alternatif yönteme otomatik geçilmez.
4. Toplam maliyet tahsisi girdi maliyetine eşit değilse transaction rollback olur.
6. Kütle dengesi, normalize kg ölçümleriyle hesaplanır.
7. Tolerans dışı fark onaylı politikaya göre reddedilir veya audit'li istisnaya gider.
8. Çoklu girdi lotu varsa her fire satırı doğru kaynak lotuna bağlıdır.
9. Bilinmeyen birim veya `piece → kg` dönüşümü olmayan değer reddedilir.
10. `OTHER` fire nedeni seçildiğinde açıklama zorunludur (bu öneri onaylanırsa).
11. Tamamlanmış parçalama emrinde fire kaydı stok `IN` hareketi veya satılabilir lot oluşturmaz.

## 11. Etkilenen belgeler

Bu ciltteki kararlar onaylandıktan sonra en az şu belgeler senkronize edilmelidir:
- Cilt 1.2 ERD/veri şeması: `requires_expiry_date`, fire alanları, birim/tolerans kısıtları.
- Cilt 1.3 API sözleşmeleri: DTO doğrulamaları, fire endpoint'i, maliyet/denge hata kodları.
- Cilt 1.4 DTO ve contract testleri.
- Cilt 1.5 iş akışları: tamamlanma/rollback/istisna kuralları.
- Cilt 1.15 kanonik sözlükler: reason code, unit ve enum kayıtları.
- Cilt 1.16 ERD–DTO crosswalk ve Cilt 1.22 crosswalk.
- Cilt 1.7 migration planı: yalnızca plan metni; gerçek migration bu ciltte oluşturulmaz.
- Cilt 1.24 kabul testleri ve LLM devir paketi.

## 12. Migration kapısı

Bu cilt **migration üretme veya DB oluşturma/değiştirme onayı değildir**. Q-123 kararları proje sahibi tarafından onaylanmadan şema ve API sözleşmeleri nihai kabul edilemez. Onaylardan sonra etkilenen tüm ciltler güncellenmeli, çapraz kontrol raporu çıkarılmalı ve migration için ayrıca açık onay alınmalıdır.


## 10. Onay durumu düzeltmesi — 22 Ekim 2026

Cilt 1.31/1.32 toplu onayı sonrası aşağıdaki eski `AÇIK`/`KARAR BEKLİYOR` etiketleri kararın kendisi bakımından artık geçerli değildir. Teknik şema/DTO doğrulaması ayrı bir iştir.

| Karar | Normatif sonuç | Durum |
|---|---|---|
| DEC-123-01 / expiry | Ürün kartı `requires_expiry_date`; true ise yeni lotta expiry zorunlu, false ise null kabul edilir; geçmiş lotlar otomatik değişmez. | ONAYLANDI; fiziksel schema doğrulaması bekliyor |
| DEC-123-02 / BY_WEIGHT | CUT + stoklu BYPRODUCT + WASTE tüm ölçülmüş ağırlıkları paydada; fire maliyet payı alır. | ONAYLANDI |
| DEC-123-03 / BY_VALUE | Fire `allocated_cost=0`; toplam maliyet değer taşıyan stok çıktılarına dağıtılır. Değer anahtarı yoksa işlem tamamlanmaz, BY_WEIGHT'e fallback yok. | ONAYLANDI |
| DEC-123-04 / tolerance | Varsayılan tolerans 0 kg; aşım ret veya yetkili, açıklamalı variance akışı gerektirir. | ONAYLANDI |
| DEC-123-05 / unit | Kanonik kg; g/kg dönüşümü hesap öncesi yapılır. | ONAYLANDI |
| DEC-123-06 / reason codes | `TRIMMING_LOSS`, `BONE_WASTE`, `CONTAMINATION`, `SPOILAGE`, `PROCESS_LOSS`, `OTHER`; OTHER için açıklama zorunlu. | ONAYLANDI |
| DEC-123-07 / input lots | Her output/waste satırı tek kaynak lot; çoklu kaynak lot için ayrı satırlar. | ONAYLANDI |
| DEC-123-08 / rounding | Deterministik yuvarlama artığı son tahsis satırına eklenir. | ONAYLANDI |

### Uygulama doğrulama uyarısı
Bu kararlar normatiftir ancak bu belge güncellemesi tek başına fiziksel ERD, ORM, OpenAPI veya DB'nin uyumlu olduğunu kanıtlamaz. Cilt 1.34 ve sonrası çapraz kontrol listesi tamamlanana kadar alan/constraint varlığı `VERIFY` olarak kalır.
