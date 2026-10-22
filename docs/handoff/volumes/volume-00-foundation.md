# Cilt 0 — Gereksinimler, Mimari Temel ve Ortak Geliştirme Kuralları

**Durum:** Teknoloji standardı proje sahibi tarafından onaylandı; ayrıntılı iş kuralları ve şema kararları ilgili ciltlerde kesinleştirilecek  
**Kaynak:** `AVATAR_Assessment.pdf`, sayfa 1–3  
**Son teslim tarihi:** 1 Kasım 2026  
**Hedef:** Dört kişilik ekip ve kodlama görevleri verilecek diğer LLM'ler için tek, tutarlı bir proje sözleşmesi oluşturmak.

---

## 0.1. Bu cildin amacı

Bu cilt kodlama talimatlarından önce okunmalıdır. Projenin neden yapıldığını, yarışmanın zorunlu gereksinimlerini, modüllerin birbirleriyle nasıl ilişkileneceğini, onaylanmış teknoloji standardını ve ilgili ciltlerde hâlâ kesinleştirilecek iş kurallarını tanımlar.

Bu cilt, ayrıntılı veritabanı şemasının veya bütün API endpoint'lerinin yerine geçmez. Bunlar Cilt 1'de tanımlanacaktır. Cilt 0, sonraki ciltlerin çelişmemesi için ortak çerçeveyi belirler.

### Etiketlerin anlamı

- **[PDF]**: Yarışma PDF'sinde açıkça bulunan gereksinim.
- **[KARAR]**: Kullanıcı tarafından açıkça seçilmiş karar.
- **[STANDART]**: Proje sahibi tarafından onaylanmış ve tüm modüllerde uygulanması gereken teknoloji/entegrasyon standardı.
- **[ÖNERİ]**: İlgili ciltte gerekçesiyle sunulan, henüz proje standardı olarak kabul edilmemiş iş kuralı veya tasarım tercihi.
- **[TBD]**: Kodlamadan önce karara bağlanması gereken konu.
- **[KAPSAM DIŞI]**: İlk teslim için yapılmayacak özellik.

Bir LLM, `[TBD]` olarak işaretlenmiş konuyu kendi başına kesin karara dönüştürmemelidir.

---

## 0.2. Ürün amacı ve başarı ölçütü

**[PDF]** Amaç; gerçek bir gıda işletmesinde kullanılabilecek, hammaddeden nihai satışa kadar maliyet ve stok hareketlerini yöneten bir uygulama geliştirmektir. Üç ana görev ve iki zorunlu yapay zekâ çalışması birbirine entegre olmalıdır.

Uygulama yalnızca ekranların çalışmasını değil, aşağıdaki doğruluk koşullarını sağlamalıdır:

1. Üretim maliyeti gerçek tüketim ve hizmet maliyetine dayanmalıdır.
2. Stok hareketleri lot ve miktar bazında izlenebilmelidir.
3. Parçalama maliyet dağıtımının toplamı, dağıtılması gereken toplam maliyete eşit olmalıdır.
4. Sorunlu hammaddenin etkilediği mamul lotları, stoklar ve bilinen alıcılar kesin kayıt ilişkileriyle bulunmalıdır.
5. Geri çağrılan lotların satışı engellenmelidir.
6. İki zorunlu AI çalışmasının tahminleri, gerçek sonuçları ve hata değerlendirmesi gösterilmelidir.
7. Çalıştırılabilir prototip, kaynak kodu, kurulum açıklaması, veri modeli, API açıklaması, örnek kayıtlar ve temel otomatik testler teslim edilmelidir.

**Başarı ölçütü:** Üç ana görevin uçtan uca gösterilebilmesi; özellikle `ET-2026-001` lotundan etkilenen marketlerin bulunması.

---

## 0.3. Yarışmanın kapsamı

### 0.3.1. Görev 1 — Dış hizmetle üretim ve gerçek maliyet (EKP)

**[PDF] Senaryo:**

İşletme dış üreticiye 100 kg et, 2 kg baharat ve 5 kg bağırsak gönderir. Üretici 85 adet, 1 kg'lık Narin Sucuk teslim eder ve yalnızca 85 × 5,50 € hizmet faturası keser. Hammaddeler işletmeye aittir; maliyetleri hizmet faturasına dahil değildir.

PDF'deki örnek hesap:

- Et: 100 kg × 9,70 € = 970,00 €
- Baharat: 2 kg × 24,00 € = 48,00 €
- Bağırsak: 5 kg × 11,60 € = 58,00 €
- Hizmet: 85 paket × 5,50 € = 467,50 €
- Toplam: 1.543,50 €
- EKP: 1.543,50 € / 85 = yaklaşık 18,16 € / paket

**[PDF] İşlevler:**

- Hammadde kartları, alış fiyatları, ölçü birimleri, lot numaraları ve stoklar.
- Dış üretim emri, hammadde sevki, hizmet maliyeti, mamul kabulü ve miktar farkları.
- Gerçek mamul miktarına göre EKP; VKP, brüt kâr ve marj gösterimi.
- Maliyet ve stok hareketlerinin geçmişe dönük incelenmesi.

**[TBD]** PDF VKP'nin formülünü, satış fiyatı kaynağını ve marj tanımını ayrıntılandırmıyor. Bunlar Cilt 2'de kesinleştirilmeden kodlanmamalıdır.

### 0.3.2. Görev 2 — Bütün kuzu parçalama ve Kotlin ile satış

**[PDF] İşlevler:**

- Giriş hayvanı/partisi, ağırlık, gerçek toplam alış maliyeti ve işlem tarihi.
- Önceden tanımlanabilir parçalama reçetesi ve maliyet dağıtım anahtarı.
- İşlem sırasında fiilî parça ağırlıklarının kaydedilmesi.
- Parça ürünler, miktarlar, fire/yan ürünler ve ağırlık dengesi kontrolü.
- Maliyetlerin miktar veya değer ağırlıklı anahtara göre dağıtılması.
- Dağıtılan maliyetlerin toplamının toplam maliyete eşit olması.
- Ürünlerin lot bazında stoklanması ve Kotlin Android satış uygulamasından satılması.

**[PDF] Açıkça belirtilen tutarsızlık:**

Örnek görselde 25 kg × 11,50 € = 287,50 € olmalıdır; 351,00 € ile farklıdır. Görseldeki parça miktarları da 22 kg toplamaktadır. Uygulama bu tutarsızlığı tespit edip açıklamalıdır.

Sistem bu farkın nedenini veri olmadan tahmin edip kesin gerçek olarak göstermemelidir. Açıklanmamış fark, kullanıcıya doğrulama gerektiren fark olarak gösterilmelidir.

### 0.3.3. Görev 3 — Lot izlenebilirliği ve geri çağırma

**[PDF] Zorunlu senaryo:**

- Hammadde lotu: `ET-2026-001`, 100 kg et.
- Üretim emri: `URT-2026-045`.
- Mamul lotu: `SUC-2026-045`, 85 paket.
- Market A: 30 paket.
- Market B: 25 paket.
- Market C: 30 paket.
- Daha sonra et partisinde kalite sorunu oluşur.

**[PDF] İşlevler:**

- Hammadde girişlerinde tedarikçi, lot, tarih, miktar ve uygunsa son tüketim tarihi.
- Bir üretim emrinde birden fazla hammadde lotunun kullanılabilmesi.
- Bir hammadde lotunun birden fazla mamul lotuna dönüşebilmesi.
- Çoktan çoğa ilişkilerin miktarlarıyla saklanması.
- Parçalama giriş lotundan oluşan bütün parça ürün lotlarına izlenebilirlik.
- Depo transferi, satış, iade, yeniden işleme ve fire hareketlerinin lot bazında kaydı.
- İleri ve geriye izleme.
- Geri çağırma ekranında etkilenen ürünleri bloke etme; market/müşteri bazlı miktar, sevkiyat ve iletişim listesi üretme.
- İkinci kademe dağıtımın yalnızca kaydedilmişse kesin olarak gösterilmesi.
- Kotlin satış uygulamasında her satış satırının lotu, miktarı ve stok hareketinin saklanması; geri çağrılan lotların satışının engellenmesi.

**Mimari ilke:** İzlenebilirlik ve geri çağırma, AI tahminlerinden değil kesin kayıtlardan hesaplanır.

### 0.3.4. İki zorunlu AI çalışması

**AI-A — Üretim verimi ve EKP tahmini**

- Geçmiş üretim emirlerinden beklenen mamul miktarını ve birim maliyeti tahmin et.
- Tahmin, gerçek sonuç ve sapmayı birlikte göster.
- Örnek/anonymize veriler, model yaklaşımı, basit referans yöntem ve hata ölçümü sun.
- Gerçek veri azsa sınırlılıkları açıkla.

**AI-B — Parçalama verimi tahmini**

- Hayvan türü, giriş ağırlığı ve geçmiş parçalama kayıtlarından beklenen parça ağırlıklarını tahmin et.
- Gerçek miktarlarla farkları raporla.
- Referans yöntem ve hata ölçümü sun.
- Veri azlığını ve modelin sınırlarını açıkla.

**[PDF] İsteğe bağlı özellikler:**

- Fatura/irsaliye okuma: ürün, miktar, lot ve maliyet alanlarını öneri olarak çıkarma; insan onayıyla kaydetme.
- Anomali uyarıları: beklenmedik fire, maliyet artışı, düşük üretim verimi veya tutarsız lot hareketleri.

**Öncelik kuralı:** İsteğe bağlı AI özellikleri, üç ana görevin ve iki zorunlu AI çalışmasının doğruluğunu tehlikeye atacak şekilde öne alınmamalıdır.

---

## 0.4. Onaylanmış teknoloji standardı

**Durum: ONAYLANDI — 22 Ekim 2026.** Aşağıdaki yığın tüm ekip ve LLM görevleri için bağlayıcıdır. Sonraki ciltler bu teknolojileri farklı alternatiflerle değiştirmemelidir. Bir değişiklik gerekiyorsa önce karar kaydı güncellenmelidir.

| Katman | Onaylanmış standart | Durum ve gerekçe |
|---|---|---|
| Android dili | Kotlin | **[PDF + STANDART]** Yarışma Kotlin Android uygulaması ister. |
| Android arayüzü | Jetpack Compose | **[STANDART]** Android ekranlarının ortak arayüz teknolojisi. |
| Yerel veritabanı | SQLite | **[PDF + STANDART / ZORUNLU]** Android tarafında yerel veritabanı olarak kullanılacaktır. |
| SQLite erişim katmanı | Room | **[STANDART]** Room, SQLite'ın yerine geçen ayrı bir veritabanı değildir; SQLite üzerinde tip güvenli erişim ve DAO katmanıdır. |
| Android API istemcisi | Retrofit + OkHttp | **[STANDART]** Backend REST API iletişimi. |
| Android asenkron işlemleri | Kotlin Coroutines | **[STANDART]** Ağ ve veritabanı işlemleri. |
| Android yerel ayarları | Android DataStore | **[STANDART]** Uygulama tercihleri ve uygun oturumla ilişkili ayarlar; hassas sırlar düz metin olarak saklanmayacak. |
| Backend dili/framework | Python + FastAPI | **[STANDART]** REST API, iş kuralları ve ML entegrasyonu. |
| API veri doğrulama | Pydantic | **[STANDART]** İstek/yanıt şemaları ve veri doğrulama. |
| ORM | SQLAlchemy 2.x | **[STANDART]** Backend'in ilişkisel veritabanı erişimi. |
| Veritabanı migration | Alembic | **[STANDART]** Sürümlenmiş şema değişiklikleri. |
| MySQL sürücüsü | PyMySQL | **[STANDART]** SQLAlchemy ile MySQL bağlantısı. |
| Merkezi veritabanı | MySQL 8.4 LTS | **[PDF + STANDART]** Merkezi ve esas veri kaynağı. |
| Web paneli | React + TypeScript | **[STANDART]** Yönetim paneli ve raporlama. |
| Web geliştirme aracı | Vite | **[STANDART]** Web geliştirme ve derleme. |
| Web stilleri | Tailwind CSS | **[STANDART]** Ortak stil yaklaşımı. |
| Web API veri yönetimi | TanStack Query + standart `fetch` istemcisi | **[STANDART]** Backend istekleri ve sunucu verisi durumu. |
| Web grafikleri | Recharts | **[STANDART]** Gerekli rapor grafikleri. |
| ML/veri işleme | Python, pandas, NumPy, scikit-learn, joblib | **[STANDART]** İki zorunlu AI çalışması için başlangıç ekosistemi. Algoritma veri analizi sonrası seçilecek. |
| ML dağıtımı | İlk sürümde FastAPI backend içindeki ayrı ML modülü | **[STANDART]** Bağımsız ML mikroservisi ilk teslim için kullanılmayacak. |
| Sürüm kontrolü | Git + GitHub | **[STANDART]** Ortak kaynak kodu ve değişiklik geçmişi. |
| Yerel servis çalıştırma | Docker Compose | **[STANDART]** Tekrarlanabilir geliştirme/demo ortamı. |
| Backend testleri | pytest | **[STANDART]** Birim ve entegrasyon testleri. |
| Android testleri | JUnit ve gerekli Android test araçları | **[STANDART]** Android mantığı ve kritik akış testleri. |
| Web testleri | Vitest + React Testing Library | **[STANDART]** Arayüz ve davranış testleri. |
| API sözleşmesi | REST + JSON + OpenAPI | **[STANDART]** Android ve web aynı sözleşmeyi kullanır. |
| Android çalışma modeli | Çevrimiçi öncelikli; satış için backend doğrulaması zorunlu | **[KARAR]** ADR-001 ile kabul edildi. |
| Çevrimdışı satış | İlk teslimde desteklenmeyecek | **[KARAR / KAPSAM DIŞI]** Stok ve geri çağırma tutarlılığı ile teslim süresi gerekçesi. |

### 0.4.1. Teknoloji değişikliği kuralı

- Bu tabloda onaylanmış bir teknolojiye başka bir LLM kendi kararıyla alternatif ekleyemez.
- Bir paket sürümü uyumsuzluk veya kurulum sorunu çıkarırsa uyumlu sürüm aralığı önerilebilir; teknoloji ailesi değiştirilmez.
- Teknoloji değişikliği gerekiyorsa gerekçe, etkilenen modüller, geçiş adımları ve test etkisiyle birlikte karar kaydı önerilir. Proje sahibi onaylamadan standart değişmiş sayılmaz.
- Onaylanmış teknoloji listesi, her cildin ve kodlama görevinin başlangıç bağlamına eklenmelidir.

### 0.4.2. İlk teslimde kullanılmayacak alternatifler

İlk sürümde Go/Express backend, PostgreSQL/MongoDB/Firebase/Supabase ana veritabanı, Kafka/RabbitMQ, Redis, Kubernetes, ayrı ML mikroservisi ve çevrimdışı satış kuyruğu kullanılmayacaktır. Gerçek bir zorunluluk doğarsa ayrı karar kaydı gerekir.

### 0.4.3. Henüz açık kalabilecek konular

Teknoloji yığını onaylanmıştır; bu, tüm iş kurallarının da karara bağlandığı anlamına gelmez. Para gösterimi ve yuvarlama, VKP/brüt kâr/marj formülleri, maliyet dağıtım anahtarı, kullanıcı rolleri, stok bakiyesi stratejisi, SQLite'ta tutulacak kayıtların kesin kapsamı, örnek veri üretimi ve ML değerlendirme ayrıntıları ilgili ciltlerde tanımlanacaktır. Bu açık konular teknoloji seçimiyle karıştırılmamalıdır.

---

## 0.5. Önerilen mantıksal mimari

```text
React Web Yönetim Paneli ─────┐
                              │ HTTPS / REST API
Kotlin Android + SQLite ──────┼────> Python Backend ─────> MySQL
                              │             │
                              │             └────> ML bileşeni/servisi
                              │
                              └──── Tüm iş kuralları merkezi backend'de doğrulanır
```

Bu, mantıksal mimaridir; henüz nihai dağıtım/topoloji kararı değildir.

### 0.5.2. SQLite ve MySQL'in birlikte kullanımı — zorunlu standart

SQLite yerel veritabanı olarak zorunludur; Room ise Android uygulamasının SQLite'a erişim katmanıdır. Bu ikisi birbirinin alternatifi değildir.

- **MySQL:** Merkezi ve esas iş kayıtlarının kaynağıdır.
- **SQLite/Room:** Android'de ihtiyaç duyulan yerel referans verileri, son başarılı API yanıtlarından oluşan önbellek ve uygulama için gerekli sınırlı yerel durumu tutar.
- **Satış:** İnternet/API erişimi varken satış isteği backend'e gönderilir. Backend lotun bloke olmadığını, yeterli stoğu ve diğer iş kurallarını doğrular; merkezi kaydı ve stok hareketini transaction içinde yazar.
- **Çevrimdışı durum:** SQLite satış taslağını veya kullanıcıya ait geçici arayüz durumunu tutabilir; ancak ilk sürümde satışın çevrimdışı kabul edilmesi veya daha sonra otomatik senkronize edilmesi desteklenmez.
- **Yenileme:** Yerel katalog/önbellek verileri API yanıtlarıyla yenilenir. Yerel önbellek hiçbir zaman merkezi stok/lot durumunu tek başına kesin gerçek kabul edemez.
- **Çakışma:** İlk sürümde çevrimdışı satış senkronizasyonu olmadığı için satış kuyruğu uzlaştırma algoritması tasarlanmayacaktır. API'den gelen güncel durum ve hata yanıtları esas alınır.
- **Güvenlik:** Kimlik bilgileri ve token'lar SQLite'a düz metin olarak yazılmaz. Hassas veri kapsamı en aza indirilir.

Cilt 4, SQLite'ta hangi tabloların/önbelleklerin tutulacağını, yenileme ve geçersizleştirme kurallarını, bağlantı yokken kullanıcı deneyimini ve yerel verinin temizlenme politikasını kesinleştirecektir.

### 0.5.1. Katman sorumlulukları

**Android:**
- Kullanıcı arayüzü, ürün/lot seçimi ve satış isteği.
- API yanıtlarını işleme ve kullanıcıya açık sonuç gösterme.
- SQLite'ta gerekli yerel veri/önbellek.
- MySQL'e doğrudan erişim yok.
- Çevrimdışı iken satış başarılıymış gibi gösterilmez.

**React web:**
- Yönetim, kayıt görüntüleme, üretim/parçalama işlemleri ve raporlar.
- İş kurallarının kopyasını kendi içinde bağımsız olarak uygulamamalı.
- Backend'in döndürdüğü doğrulama hatalarını anlaşılır biçimde göstermeli.

**Backend:**
- İş kuralları ve veri doğrulama.
- Maliyet hesaplama, stok hareketi, lot bağlantıları ve geri çağırma.
- Yetkilendirme ve API sözleşmeleri.
- Satış/üretim/parçalama işlemlerinin atomik ve tutarlı kaydı.
- ML tahminlerini çağırma ve sonuçlarını sunma.

**MySQL:**
- Merkezi iş kayıtları ve ilişkiler.
- Stok hareketleri ve lot izlenebilirliği için kalıcı kayıt.
- İşlem tutarlılığına uygun ilişkisel yapı.

**ML:**
- Tahmin üretir; kesin stok/maliyet/lot kaydının yerine geçmez.
- Tahmin, model sürümü, girdiler ve değerlendirme metrikleri izlenebilir olmalıdır.

### 0.5.2. ML'nin dağıtımı hakkında

**[KARAR]** İlk sürümde ML, FastAPI backend içindeki ayrı bir Python modülü olarak çalışacaktır. Bağımsız ML mikroservisi ilk teslim kapsamında değildir. Cilt 6 bu karara göre hazırlanacaktır.

---

## 0.6. Çapraz modül iş kuralları

Bu kurallar tüm ciltler için geçerlidir.

### 0.6.1. Miktar ve birim

- Miktar alanlarında birim açıkça belirtilmelidir: kg, paket, adet vb.
- Farklı birimlerle işlem yapılırken dönüşüm kuralı tanımlı olmalıdır.
- Birim dönüşümü tanımsızsa sistem sessizce dönüşüm yapmamalıdır.
- Ondalık miktarlar ve parasal değerler için uygun veri türleri seçilmelidir; parasal hesaplamalarda ikili kayan nokta hassasiyetine güvenilmemelidir.
- Ekran yuvarlaması ile veri tabanında saklanan hassasiyet birbirinden ayrılmalıdır.

### 0.6.2. Stok hareketleri

- Stok miktarı yalnızca bir ekrandaki alanı değiştirerek güncellenmemelidir; hareket kaydı oluşturulmalıdır.
- Her hareketin türü, ürün/lotu, miktarı, zamanı, kaynağı ve ilgili belge/işlem bağlantısı bulunmalıdır.
- İptal/düzeltme gerektiğinde geçmiş hareketin izini kaybettiren sessiz silme yerine denetlenebilir düzeltme yaklaşımı kullanılmalıdır.
- Negatif stok politikası Cilt 1'de açıkça tanımlanmalıdır; varsayılan öneri, onaylı bir iş kuralı yoksa stok eksiye düşmesini engellemektir.

### 0.6.3. Maliyet

- Maliyet hesabı birden fazla modülde birbirinden bağımsız biçimde kopyalanmamalıdır.
- Üretim ve parçalama maliyetleri test edilebilir ortak kurallara dayanmalıdır.
- Dağıtılan maliyet toplamı, dağıtılması gereken maliyete eşit olmalıdır; kuruş seviyesindeki dağıtım farklarının hangi ürüne aktarılacağı belgelenmelidir.
- Gerçekleşen maliyet ile AI tahmini ayrı alanlar/sonuçlar olarak ele alınmalıdır.

### 0.6.4. Lot ve geri çağırma

- Lot kodları, üretim emirleri ve satış belgeleri birbirinden ayrıdır.
- Çoktan çoğa ilişkiler, ilişki tablosu ve miktar alanlarıyla temsil edilmelidir.
- Geri çağırma kararı kayıtlı lot ilişkilerinden hesaplanmalıdır.
- Geri çağrılan lot için satış doğrulaması backend'de yapılmalıdır.
- Marketlere sevkiyat miktarı ile son tüketiciye ikinci kademe dağıtım aynı veriymiş gibi sunulmamalıdır.
- Bilinmeyen dağıtım bilgisi uydurulmamalıdır.

### 0.6.5. API ve hata yönetimi

- API girişleri backend'de doğrulanmalıdır.
- Hata yanıtları tutarlı bir yapıda olmalıdır.
- İstemci, başarılı satış yanıtı almadan satışı başarılı olarak göstermemelidir.
- Aynı satış isteğinin ağ tekrarları çift kayıt üretmemelidir.
- Stok kontrolü ve stok düşümü arasında eş zamanlı işlemlerin yaratacağı yarış durumları ele alınmalıdır.

---

## 0.7. SQLite–MySQL yaklaşımı

**[PDF]** Yerel SQLite ve merkezi MySQL arasında tutarlı senkronizasyon yaklaşımı açıklanmalıdır.

**[KARAR]** Android ilk sürümde çevrimiçi öncelikli olacaktır; çevrimdışı satış kapsam dışıdır.

Bu durumda ilk sürüm için:
- Merkezi satış kaydı backend/MySQL üzerinde tutulur.
- SQLite, ekranların gerektirdiği yerel veri ve önbellek için kullanılır.
- Sunucuda doğrulanmamış satış, başarılı işlem olarak işaretlenmez.
- Yerel verilerin güncellenmesi ve geçerlilik süresi Cilt 4'te tanımlanır.
- İnternet yokken satışın engellendiği kullanıcı deneyimi test edilir.
- İleride çevrimdışı satış eklenirse bu ayrı bir mimari değişiklik ve yeni ADR gerektirir.

SQLite/Room kullanımı kesindir. SQLite'ın tam veri kapsamı, önbellek yenileme stratejisi ve yerel veri saklama süresi **[TBD]** olarak kalır; Cilt 4'te kararlaştırılır.

---

## 0.8. Güvenlik, gizlilik ve denetlenebilirlik

Asgari tasarım beklentileri:

- Veritabanı parolaları ve gizli anahtarlar kaynak koda yazılmamalıdır.
- Android uygulamasına MySQL erişim bilgileri gömülmemelidir.
- Yönetim işlemleri ile satış işlemlerinin yetkileri ayrılmalıdır.
- API, kullanıcıdan gelen miktar, lot ve maliyet değerlerini güvenilir kabul etmemelidir.
- Üretim, stok, satış ve geri çağırma değişiklikleri denetlenebilir olmalıdır.
- Gerçek müşteri/tedarikçi verileri demo ve model eğitim verilerinde gereksiz yere kullanılmamalıdır.
- AI için sentetik/anonim veri kullanılıyorsa bunun gerçek tarihsel veri olmadığı açıkça belirtilmelidir.

**[TBD]** Ayrıntılı kimlik doğrulama yöntemi, roller ve izin matrisi Cilt 1'de belirlenmelidir.

---

## 0.9. Ciltler arası bağımlılıklar ve uygulama sırası

Önerilen doküman sırası:

1. **Cilt 0:** Gereksinimler ve ortak kurallar.
2. **Cilt 1:** Veri modeli, backend sınırları ve API sözleşmeleri.
3. **Cilt 2:** Dış hizmetle üretim ve maliyet.
4. **Cilt 3:** Kuzu parçalama ve maliyet dağıtımı.
5. **Cilt 4:** Kotlin Android, SQLite ve satış.
6. **Cilt 5:** Lot izlenebilirliği ve geri çağırma.
7. **Cilt 6:** İki zorunlu ML modeli.
8. **Cilt 7:** React yönetim paneli ve raporlama.
9. **Cilt 8:** Entegrasyon, testler, demo ve teslimat.

Bu sıra, bütün kodların sıralı olarak yazılacağı anlamına gelmez. Cilt 1'in veri/API sözleşmeleri onaylandıktan sonra bağımsız modüller paralel geliştirilebilir. Geri çağırma ve satış gibi kritik modüller ise entegrasyon testleriyle doğrulanmalıdır.

### Kritik bağımlılıklar

- Cilt 2 ve 3, ortak ürün/birim/lot/maliyet kavramlarına bağlıdır.
- Cilt 4, API ve lot/stok sözleşmelerine bağlıdır.
- Cilt 5, üretim, parçalama, sevkiyat ve satış kayıtlarının eksiksiz olmasına bağlıdır.
- Cilt 6, geçmiş kayıtların ve hedef değişkenlerin tanımlanmasına bağlıdır.
- Cilt 7, backend API'lerine bağlıdır.
- Cilt 8, bütün ciltlerin kabul kriterlerini birleştirir.

---

## 0.10. LLM'ler için zorunlu çalışma kuralları

Her kodlama görevinin başında ilgili cilt ve ortak sözleşmeler okunmalıdır.

LLM:
1. Görev kapsamı dışındaki dosyaları gereksiz yere değiştirmemelidir.
2. Onaylanmamış teknoloji veya kütüphaneyi sessizce eklememelidir.
3. Veri modeli/API sözleşmesiyle çelişki görürse kodlamadan önce çelişkiyi bildirmelidir.
4. Örnek sayısal değerleri ve zorunlu lot kodlarını korumalıdır.
5. Hata durumlarını ve testleri atlamamalıdır.
6. Test çalıştırmadıysa testlerin geçtiğini iddia etmemelidir.
7. Sahte veriyi gerçek üretim verisi gibi göstermemelidir.
8. Güvenlik kontrolünü yalnızca frontend'e bırakmamalıdır.
9. Tahmini stok/maliyet değerlerini gerçek kayıtlara yazmamalıdır.
10. Yaptığı değişiklikleri, eklediği dosyaları, çalıştırdığı testleri ve bilinen eksikleri raporlamalıdır.

### Her görev için zorunlu çıktı formatı

- Amaç ve kapsam.
- Değiştirilen/oluşturulan dosyalar.
- Uygulama özeti.
- API veya veri modeli etkileri.
- Çalıştırılan testler ve sonuçları.
- Kabul kriterlerinin durumu.
- Bilinen eksikler ve sonraki bağımlılıklar.

---

## 0.11. Teslimat ve kabul yaklaşımı

**[PDF] Teslimat beklentileri:**
- Çalıştırılabilir prototip, kaynak kodu ve kurulum açıklaması.
- Veri modeli, API açıklaması, örnek kayıtlar ve temel otomatik testler.
- Üç görevin uçtan uca demosu.
- Özellikle ET-2026-001 lotundan etkilenen marketlerin bulunması.
- AI yöntemleri, örnek tahminler ve doğruluk değerlendirmesi.

Bir modül “tamamlandı” sayılabilmek için yalnızca ekranının açılması yeterli değildir. İlgili iş kuralları, hatalı girişler, veri tutarlılığı ve kabul testleri de çalıştırılmalıdır.

### Önerilen genel kabul kapıları

- **G1 — Sözleşme:** Veri modeli, API ve iş kuralları onaylandı.
- **G2 — İşlev:** Modülün normal akışı çalışıyor.
- **G3 — Hata durumları:** Geçersiz miktar, yetersiz stok, geçersiz lot ve bağlantı hataları test edildi.
- **G4 — Entegrasyon:** Diğer modüllerle gerçek API/veri sözleşmesi üzerinden çalışıyor.
- **G5 — Demo:** Temiz kurulumdan başlayarak senaryo tekrarlanabilir biçimde gösterilebiliyor.

---

## 0.12. Açık karar listesi

Aşağıdaki konular, ilgili cilt hazırlanırken çözülmelidir:

| ID | Konu | Hedef cilt | Durum |
|---|---|---|---|
| TBD-01 | Backend için Python + FastAPI'nin nihai onayı | 0/1 | Onay bekliyor |
| TBD-02 | React yanında TypeScript ve geliştirme araçları | 7 | Açık |
| TBD-03 | Kullanıcı rolleri ve yetki matrisi | 1 | Açık |
| TBD-04 | Para hassasiyeti, yuvarlama ve dağıtım farkı | 1/2/3 | Açık |
| TBD-05 | VKP, brüt kâr ve marj formülleri | 2 | Açık |
| TBD-06 | Kuzu alış maliyetinin dağıtım anahtarı ve fire yaklaşımı | 3 | Açık |
| TBD-07 | SQLite kapsamı ve yerel veri yenileme stratejisi | 4 | Açık |
| TBD-08 | ML model dağıtımı, veri şeması ve metrikler | 6 | Açık |
| TBD-09 | Demo için sentetik/örnek veri üretim planı | 1/6/8 | Açık |
| TBD-10 | Otomatik test ve çalıştırma ortamı | 8 | Açık |

Bu tablo yeni belirsizlikler bulunduğunda güncellenmelidir. Belirsiz bir konu, yalnızca uygulaması kolay olduğu için sessizce karara bağlanmamalıdır.

---

## 0.13. Bu cildin tamamlanma ölçütü

Cilt 0, ekip şu konularda aynı anlayışa sahip olduğunda onaylanabilir:

- Yarışmanın üç zorunlu iş görevi ve iki zorunlu AI çalışması açıkça tanımlı.
- PDF gereksinimleri ile proje önerileri birbirinden ayrılmış.
- Android çevrimiçi öncelikli kararı kaydedilmiş.
- Merkezi iş kuralları ve lot izlenebilirliği ilkeleri belirlenmiş.
- Teknoloji kararlarının durumu ve açık sorular görünür.
- Sonraki ciltlerin bağımlılıkları tanımlanmış.
- LLM'ler için kodlama ve test raporlama kuralları yazılmış.

**Önemli:** Bu cilt ilk taslaktır; Cilt 1'in veri modeli ve API sözleşmeleri oluşturulup çapraz kontrol edilmeden bütün mimari ayrıntılar kesinleşmiş sayılmamalıdır.


### 0.4.4. Onaylanmış DEC-001 veri/API kararları

Proje sahibi 22 Ekim 2026'da DEC-001 belgesindeki 13 kararın tamamını kabul etti. Bu kararlar bağlayıcıdır:

1. Dahili anahtarlar `BIGINT`; insan tarafından görülen iş kodları ayrı benzersiz alanlardır.
2. MySQL parasal değerleri `DECIMAL(19,4)`, miktar/ağırlık değerleri `DECIMAL(19,6)` olarak saklar. Hassas ondalık API alanları JSON string biçiminde taşınır. Para birimi `currency_code` ile tutulur; ilk demo para birimi EUR'dur.
3. Zaman anları ISO 8601 UTC (`Z`) ile; yalnızca tarih olan değerler `YYYY-MM-DD` ile ifade edilir.
4. Stok hareketleri denetlenebilir ledger olarak, güncel lot bakiyeleri ayrı bakiye kaydı olarak tutulur; ikisi aynı transaction içinde güncellenir.
5. Stok hareketi miktarı pozitif mutlak değerdir; yön `IN`/`OUT` alanıyla belirtilir.
6. Lot kökeni, miktarlı ve çoktan çoğa genealogy bağlantılarıyla tutulur.
7. İşletme satışları ile market/müşteri sevkiyatları ayrı kavram ve kayıtlardır. İkinci kademe dağıtım, ayrıca kaydedilmedikçe varsayılmaz.
8. Backend JWT access token ve rol bazlı yetkilendirme uygular. Başlangıç rolleri `ADMIN`, `OPERATOR`, `SALES`, `TRACEABILITY_MANAGER`, `VIEWER` olarak tanımlanır; nihai işlem-yetki matrisi ilgili ciltte açıklanır.
9. Kritik operasyon kayıtları hard delete ile silinmez; iptal/düzeltme ve ters hareketlerle denetlenebilir biçimde ele alınır.
10. Satışta `Idempotency-Key` zorunludur. Aynı anahtar ve aynı içerik ilk sonucu döndürür; aynı anahtar farklı içerikle kullanılırsa `409 Conflict` döner.
11. Hata yanıtları `error.code`, `error.message`, isteğe bağlı `error.details` ve `request_id` alanlarını kullanır.
12. API yolları `/api/v1` ile başlar; liste endpoint'leri ortak sayfalama/filtreleme yaklaşımı izler.
13. Veritabanı ve API JSON alanları `snake_case`, enum değerleri `UPPER_SNAKE_CASE` kullanır. Endpoint path'leri küçük harf/kebab-case kullanır.

Ayrıntılı gerekçe, etkiler ve örnek hata JSON'u `decisions/DEC-001-data-api-contracts-proposal.md` dosyasındadır. Bu kararların ayrıntılı uygulaması Cilt 1 ve sonraki ilgili ciltlerde aynı şekilde sürdürülmelidir.



## Doküman revizyon durumu — 1.11

Cilt 1.10 çapraz kontrol raporu ve önerileri proje sahibi tarafından onaylandı. Cilt 1.11 planına göre Cilt 1.2–1.9 için bağlayıcı revizyon ekleri işlendi ve Cilt 1.10'a kapanış haritası eklendi. Bu aşama yalnızca dokümantasyon güncellemesidir. Gerçek Alembic migration dosyaları oluşturulmamış, veritabanı kurulmamış veya değiştirilmemiştir. Migration öncesinde ERD tablo/kolonları, nullable alanlar, iş akışları, endpoint/DTO'lar, izinler, enumlar ve hata kodları son kez çapraz kontrol edilmeli; ardından proje sahibinden ayrı açık onay alınmalıdır.
