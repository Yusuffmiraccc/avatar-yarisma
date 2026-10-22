# Cilt 1.11 — Çapraz Kontrol Sonrası Belge Revizyon Planı

**Durum:** Kullanıcı, Cilt 1.10 raporunu ve rapordaki önerileri onayladı. Belge revizyonu planlandı; henüz uygulanmadı.  
**Tarih:** 22 Ekim 2026  
**Kapsam:** Cilt 1.2–1.10 ve bunlara bağlı karar/temel belgeleri.  
**Kesin sınır:** Bu cilt bir plan belgesidir. Gerçek Alembic migration dosyaları oluşturulmayacak; veritabanı kurulmayacak veya değiştirilmeyecektir.

## 1. Amaç

Cilt 1.10'da listelenen CC-01–CC-16 bulgularını onaylanan önerilere göre ilgili belgelerde tutarlı hale getirmek. Amaç, ERD, DTO, endpoint, iş akışı, izin matrisi ve migration planının aynı kuralları anlatmasını sağlamak.

Bu onay, önerilen kuralların dokümantasyona işlenmesine izin verir. Tek başına migration dosyası oluşturma veya veritabanı üzerinde işlem yapma izni değildir.

## 2. Revizyon ilkeleri

1. Önce karar ve iş kuralı metinleri güncellenecek; tablo/kolon ve endpoint sözleşmeleri bunlarla uyumlandırılacak.
2. Aynı enum, error code, permission key ve alan semantiği için tek bir kanonik liste kullanılacak.
3. Bir belge diğerini etkiliyorsa yalnızca bir taraf güncellenmeyecek; tüm bağımlı belgeler aynı revizyonda ele alınacak.
4. Yarışma PDF'sinde olmayan sayısal toleranslar veya iş kuralları uydurulmayacak.
5. Önerisi genel kalan ve somut işletme/dağıtım tercihi gerektiren noktalar `TBD` olarak kalacak ve migration kapısında açıkça gösterilecek.
6. Her revizyondan sonra dokümanlar arası tutarlılık kontrolü yapılacak; yalnızca dokümantasyon ve test taslağı güncellenecek.

## 3. Bulgulara göre kabul edilen revizyon yönü

| Bulgu | Onaylanan revizyon yönü | Etkilenen belgeler | Doğrulama ölçütü |
|---|---|---|---|
| CC-01 Fire nullability | Stokta izlenen çıktı satırlarında ürün ve çıktı lotu zorunlu; yalnızca fire ölçüm satırında bu alanlar nullable olabilir. | 1.2, 1.3, 1.4, 1.5, 1.7 | ERD nullability ve DTO doğrulaması aynı ayrımı gösterir. |
| CC-02 Üretim girdisi stok düşümü | İlk sürümde gerçek tüketim miktarlarıyla üretim tamamlama anında `OUT`; `IN_PROGRESS` aşamasında rezervasyon yoksa stok düşümü yok. | 1.2, 1.3, 1.5, 1.6, 1.7 | Tek geçişte stok ledger ve balance güncellenir; başarısız işlemde ikisi de rollback olur. |
| CC-03 Satış/sevkiyat stok sahipliği | Bir fiziksel ürün için yalnızca tek olay `OUT` hareketi üretir. Hangi olayın sahibi olacağı açık bir alt karar olarak netleştirilecek; belgeye çelişkili iki davranış yazılmayacak. | 1.2, 1.3, 1.5, 1.6, 1.7 | Satış ve dispatch senaryosu tek bir fiziksel stok çıkışı üretir. |
| CC-04 Recall aktivasyonu | MVP'de senkron ve atomik aktivasyon; `ACTIVATING` durumu/outbox yalnızca daha sonra ayrı mimari kararla eklenebilir. | 1.3, 1.5, 1.6, 1.7 | Aktivasyon başarısızsa kısmi blokaj kalmaz; durum sözlüğü bunu yansıtır. |
| CC-05 Recall çözümü | Recall `RESOLVED` olduğunda lot blokajı kendiliğinden kalkmaz; yeniden satışa açma ayrı, yetkili ve audit edilen komuttur. | 1.3, 1.5, 1.8, 1.9 | Çözüm durumu tek başına satış izni vermez. |
| CC-06 Ağırlık farkı | Tolerans işletme/yarışma kararıyla belirlenir; sabit değer uydurulmaz. Tolerans dışı farkta açıklama ve audit gereksinimi belgelenir. | 1.2, 1.3, 1.5, 1.7 | Sayısal tolerans belirlenmediyse açık `TBD`/konfigürasyon gereksinimi olarak kalır. |
| CC-07 Düzeltme/ters kayıt | Tamamlanmış kayıtlar silinmez/değiştirilmez; kaynak kayda bağlı düzeltme/ters kayıt ve karşı stok hareketleri tek transaction'da tutulur. | 1.2, 1.3, 1.5, 1.6, 1.7, 1.9 | Orijinal kayıt ve audit izi korunur; ters hareketler çift/eksik etki oluşturmaz. |
| CC-08 Idempotency | Satış dışındaki stok/maliyet etkili kritik POST komutlarında idempotency veya aynı etkiyi ikinci kez üretmeyen deterministik conflict davranışı endpoint bazında tanımlanır. | 1.3, 1.4, 1.5, 1.6, 1.7 | Kritik komutların her biri tekrar istek davranışını ve testini belirtir. |
| CC-09 Durum enumları | Kullanılan durumlar tek kanonik sözlükte birleştirilir; MVP'de gereksiz ara durumlar çıkarılır. | 1.3, 1.4, 1.5, 1.6, 1.7 | API, DTO, iş akışı ve DB aynı enum adlarını kullanır. |
| CC-10 Stok düzeltme yetkisi | Genel stok düzeltme `ADMIN` ile sınırlandırılır; `OPERATOR` normal operasyonlar üzerinden stok hareketi oluşturabilir. | 1.3, 1.8, 1.9 | İzin tablosu ve endpoint örnekleri çelişmez. |
| CC-11 Sevkiyat rolü | Sevkiyat oluşturma/dispatch işlemleri `SALES`; `OPERATOR` ve `TRACEABILITY_MANAGER` yalnızca görüntüleme. | 1.3, 1.8, 1.9 | Endpoint permission key'leri rol matrisiyle eşleşir. |
| CC-12 AI izinleri | Tahmin başlatma `ADMIN`/`OPERATOR`; sonuç okuma `ADMIN`, `OPERATOR`, `TRACEABILITY_MANAGER`, `VIEWER`; `SALES` ilk sürümde dışarıda. | 1.3, 1.8, 1.9 | Başlatma ve okuma izinleri ayrı ve test edilebilir tanımlanır. |
| CC-13 JWT/token | Access token 30 dakika; ilk MVP'de refresh token yok; logout istemci token'ını temizler. Android güvenli saklama ve web token/CSRF davranışı ayrı ayrı açıkça yazılır. | 1.3, 1.4, 1.8, 1.9, 1.6 | Ömür, saklama, logout ve web CSRF belgeleri aynı davranışı anlatır. |
| CC-14 Hata kodları | Tek error-code registry oluşturulur; HTTP status ile `error.code` ayrımı korunur; alias/sessiz dönüşüm yapılmaz. | 1.3, 1.4, 1.6, 1.8, 1.9 | Örnek yanıtlar ve contract testleri registry ile eşleşir. |
| CC-15 Nullable semantiği | Her nullable alanın gerekçesi belirtilir; `NULL`, sıfır, bilinmiyor ve uygulanamaz birbirine karıştırılmaz. DTO ve DB anlamları eşleşir. | 1.2, 1.3, 1.4, 1.7 | Nullable alan envanteri ve DTO/DB eşleme tablosu tamamlanır. |
| CC-16 Health endpoint | Liveness ile ayrıntılı bağımlılık/DB health ayrılır; ayrıntılı health internal/authorized erişime alınır; hassas altyapı bilgisi döndürülmez. | 1.3, 1.6, 1.8, 1.9 | Endpoint erişim kuralları ve response örnekleri güvenli varsayılanı gösterir. |

## 4. Belge bazında yapılacak işler

### 4.1 Cilt 1.2 — ERD ve veri şeması

- Fire ölçüm satırı ile stokta izlenen çıktı satırlarının modelleme/nullability ayrımını yaz.
- Üretim tamamlama anındaki stok hareketi kurallarını tablo ilişkileri ve transaction sınırlarıyla eşleştir.
- Satış/sevkiyat stok çıkışının tek sahibi seçilene kadar çelişen stok etkisi metinlerini kaldır; açık kararı işaretle.
- Düzeltme/ters kayıt yaklaşımının veri modelindeki karşılığını tanımla; yeni tablo/kolon adlarını migration öncesi çapraz kontrolde kesinleştir.
- Nullable kolonların tamamı için gerekçe envanteri ekle.
- Sayısal ağırlık toleransını sabit şema kuralı gibi göstermeden işletme kararı/konfigürasyon olarak kaydet.

### 4.2 Cilt 1.3 — API sözleşmeleri

- Endpoint yan etkileri bölümünde her komutun stok, maliyet, audit ve lot-genealogy etkisini tek tek belirt.
- Sevkiyat, stok düzeltme, AI tahmin, recall çözümü ve lot blokajı izinlerini onaylanan role göre düzelt.
- Kritik POST endpoint'lerinin tekrar istek/idempotency davranışlarını tabloya ekle.
- Hata kodlarını ortak registry'ye bağla; generic `CONFLICT` ile özel kodların kullanımını tutarlı hale getir.
- Auth, logout, liveness/detailed health, recall release ve düzeltme örneklerini güncelle.

### 4.3 Cilt 1.4 — OpenAPI, DTO ve contract testleri

- Cilt 1.3 ile birebir eşleşen DTO alan/nullability tablosu oluştur.
- Para ve miktarların JSON string olması, `snake_case`, UTC timestamp ve enum yazımlarını tüm örneklerde doğrula.
- Ortak hata registry'sinden test fixture'ları üret.
- Her kritik POST için idempotency veya deterministik conflict test senaryosu ekle.
- Role/permission negatif testlerini (izin verilmeyen rol) ekle.

### 4.4 Cilt 1.5 — İş akışları ve durum makineleri

- WF-01–WF-10'u yeni karar yönleriyle güncelle.
- Üretim tamamlanması, satış/sevkiyat stok çıkışı, recall aktivasyonu/çözümü ve ters kayıt akışlarında her durum geçişinin atomik etkilerini göster.
- Recall çözümü ile lotu yeniden satışa açmayı iki ayrı işlem olarak tanımla.
- MVP durum enumlarını tekleştir; asenkron recall durumlarını kapsam dışı tut.
- Ağırlık farkı toleransının sayısal değerini uydurmadan `TBD` olarak bırak.

### 4.5 Cilt 1.6 — Backend uygulama planı

- Transaction/service sınırlarını güncel iş akışlarıyla eşleştir.
- Idempotency ve audit yaklaşımının backend katmanındaki sorumluluklarını ekle.
- Health endpoint ayrımını, token davranışını ve rol kontrollerini güncelle.
- Test aşamalarını error registry, nullable semantics, retry/idempotency ve permission testleriyle genişlet.

### 4.6 Cilt 1.7 — Migration, constraint ve seed planı

- Yalnızca plan metnini güncelle; gerçek migration dosyası oluşturma.
- Constraint/index adaylarını revize edilmiş ERD ile eşleştir.
- Seed verisinde lot recall senaryosu, fire ölçümü, üretim tamamlaması, sevkiyat ve düzeltme/ters kayıt örneklerinin beklenen stok bakiyelerini yaz.
- DB düzeyindeki `CHECK`/FK/unique kararlarını ERD ve API sözleşmesiyle çapraz kontrol et.
- Bu belgenin başına “Migration üretimi için ön koşullar” kontrol listesini ekle.

### 4.7 Cilt 1.8 ve 1.9 — Kimlik, güvenlik ve izin matrisi

- Rol matrisi ile endpoint izinlerini tek kanonik izin listesine göre eşleştir.
- `ADMIN`-only stok düzeltme, `SALES` sevkiyat işlemleri ve AI tahmin izinlerini aynılaştır.
- Access token süresini 30 dakika olarak eşleştir; refresh token olmadığını ve logout davranışını net yaz.
- Android token saklama yaklaşımını ve web cookie/CSRF yaklaşımını ayrı platform kararları olarak belgele.
- Recall release ve reversal/correction için ayrı permission key ve audit gereksinimlerini tanımla.
- Liveness ve ayrıntılı health erişimini ayır.

### 4.8 Cilt 1.10 — Çapraz kontrol raporu

- Durumunu “öneriler onaylandı; revizyon planı hazırlanıyor/uygulanıyor” şeklinde güncelle.
- Her CC maddesine revizyonun işlendiği belge ve doğrulama ölçütü bağlantısı ekle.
- Açık kalan işletme/dağıtım alt kararlarını raporun sonunda ayrı listede tut.
- Gerçek migration dosyalarının henüz oluşturulmadığı uyarısını koru.

### 4.9 Cilt 0, DEC-001 ve ADR-001

- Cilt 0'a belge revizyon süreci ve migration öncesi kapı durumunu ekle.
- DEC-001'in onaylı 13 temel veri/API kararını değiştirme; bu planın kararları onunla çelişirse açıkça işaretle.
- ADR-001 online-first kararını koru; SQLite yerel önbelleği ve MySQL'e yalnızca backend erişimiyle çelişen bir senkronizasyon varsayımı ekleme.

## 5. Revizyon sırası ve bağımlılıklar

1. **Sözlükleri hazırla:** enum, error code, permission key, nullable alan ve endpoint yan etkisi envanterleri.
2. **İş akışı kararlarını işle:** Cilt 1.5; özellikle stok çıkışının sahibi ve toleransın TBD durumu.
3. **ERD'yi güncelle:** Cilt 1.2; workflow ve alan semantiğiyle tutarlı hale getir.
4. **API/DTO sözleşmelerini güncelle:** Cilt 1.3 ve 1.4.
5. **Güvenlik ve backend planını eşleştir:** Cilt 1.6, 1.8, 1.9.
6. **Migration planını güncelle:** Cilt 1.7 yalnızca dokümantasyon seviyesinde.
7. **Çapraz kontrolü tekrarla:** Cilt 1.10 bulgularını tek tek kapat veya açık karar olarak kaydet.
8. **Kullanıcıya migration öncesi kontrol özeti sun:** tablo/kolon/constraint/endpoint/permission/enum/error-code karşılaştırması ve açık karar listesi.
9. **Ayrı açık onay bekle:** gerçek Alembic migration dosyaları oluşturulmadan ve/veya veritabanı oluşturulmadan önce kullanıcıdan açık onay al.

## 6. Revizyon tamamlanma ölçütleri

- [ ] CC-01–CC-16 her biri güncellenmiş belgeye veya açık `TBD` kararına bağlandı.
- [ ] ERD, DTO, API ve workflow alan adları/nullability açısından eşleşiyor.
- [ ] Her stok etkili komut için movement, balance, cost, audit ve idempotency davranışı tanımlı.
- [ ] Satış/sevkiyat çift stok düşümü mümkün görünmüyor; stok çıkışının sahibi açıkça seçilmiş.
- [ ] Recall çözümü lotu otomatik olarak satışa açmıyor.
- [ ] Rol matrisi ve endpoint izinleri birbiriyle tutarlı.
- [ ] JWT süresi, refresh token yaklaşımı, logout ve web/Android token saklama kuralları tutarlı.
- [ ] Error code registry ile tüm örnekler ve contract testleri eşleşiyor.
- [ ] Nullable alanların her biri için iş gerekçesi var.
- [ ] Cilt 1.7 migration planı yeni ERD ile eşleşiyor; fakat gerçek migration dosyası yok.
- [ ] Son çapraz kontrol raporunda açık kalan kararlar ve bloklayıcılar açıkça listeleniyor.
- [ ] Kullanıcıya migration öncesi son kontrol sunuldu ve gerçek migration için ayrı açık onay alındı.

## 7. Migration öncesinde hâlâ somutlaştırılması gereken alt kararlar

Rapor ve genel öneriler onaylanmış olsa da aşağıdaki noktalar, öneri metninde tek başına kesin uygulama davranışına dönüşmemiştir. Bunlar belge revizyonu sırasında gizlice varsayılmayacak:

1. **Satış/sevkiyat stok çıkışı:** Yarışma demo akışında satış ve sevkiyat ayrı kayıtlar olarak kalacak. Fiziksel `OUT` hareketinin sahibi tek bir olay olacak. Önerilen varsayılan, markete fiziksel teslimi temsil eden `dispatch` anında stok düşmek ve satış kaydının ikinci `OUT` üretmemesidir; bu varsayılan son çapraz kontrolde açıkça gösterilecek.
2. **Ağırlık farkı toleransı:** Yarışma PDF'si sayısal tolerans vermiyor. Tolerans değeri kullanıcı/işletme tarafından belirlenene kadar konfigürasyon/TBD kalacak; sahte bir sayı sabitlenmeyecek.
3. **Web token taşıma:** Web için HttpOnly/Secure/SameSite cookie + CSRF koruması kullanılacaksa API sözleşmesi, CORS ve CSRF ayrıntıları beraber tanımlanacak. Bu plan, henüz yazılmamış ayrıntıları uygulanmış gibi göstermeyecek.
4. **Health erişimi:** Liveness endpoint'inin dışa açık mı yoksa yalnızca altyapı probe'una mı açık olacağı dağıtım şekline göre belgelenecek; detaylı health internal/authorized kalacak.
5. **Düzeltme/ters kayıt veri yapısı:** Alanlar ve ilişkiler ERD revizyonunda önerilecek; migration öncesi son şemada kullanıcıya gösterilip doğrulanacak.

## 8. Kapsam dışı işlemler — bu aşamada yapılmayacak

- Alembic revision dosyaları üretmek veya mevcut migration dosyalarını değiştirmek.
- MySQL veritabanı kurmak, tablo oluşturmak, migration çalıştırmak veya veriye dokunmak.
- API/backend kodunu üretmek ya da mevcut kodu değiştirmek.
- Açık `TBD` noktalarını kullanıcı adına sessizce kesinleştirmek.

## 9. Sonraki teslimat

Bu planın ardından yapılacak çalışma, Cilt 1.2–1.9 belgelerini yukarıdaki sırayla revize etmek ve yeni bir çapraz kontrol raporu çıkarmaktır. Bu revizyon teslimatı da dokümantasyon/test taslağı düzeyinde kalacaktır. Migration üretimine geçmeden önce kullanıcıya ERD–kolon–constraint–DTO–endpoint–permission–enum/error registry karşılaştırması sunulacak ve ayrı açık onay beklenecektir.
