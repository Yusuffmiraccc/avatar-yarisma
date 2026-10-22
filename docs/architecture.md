# AVATAR Yarışması — Hedef Mimari

Bu belge, mevcut proje gereksinimlerine göre hedeflenen bileşenleri ve aralarındaki sınırları açıklar. Aşağıdaki mimari plan niteliğindedir; bileşenlerin henüz uygulandığı anlamına gelmez.

## Bileşenler

- **Android uygulaması (Kotlin):** Yarışmacıların mobil istemcisi. Ağ bağlantısının kesildiği durumlarda gerekli yerel verileri saklamak ve çevrimdışı çalışmayı desteklemek için yerel SQLite veritabanı kullanması hedeflenir. Çevrimiçi olduğunda merkezi API ile eşitlenir.
- **REST API (Go):** Android ve web istemcilerinin merkezi sistemle iletişim kuracağı servis katmanı. İstekleri doğrular, iş kurallarını uygular ve merkezi veritabanına erişimi yönetir.
- **Merkezi veritabanı (MySQL):** Sunucu tarafındaki kalıcı ve ortak proje verilerinin tutulacağı veri katmanı. Şema ve migration yaklaşımı daha sonra belirlenecektir.
- **Web arayüzü (React):** Yarışma yönetimi ve ilgili web iş akışları için tarayıcı tabanlı istemci. Sunucu verilerine REST API üzerinden erişir.
- **AI/ML bileşenleri (Python):** Projenin gereksinimleriyle belirlenecek yapay zekâ veya makine öğrenmesi işlevlerini barındırır. API ile nasıl bütünleşeceği ve model/veri yaşam döngüsü ayrıca tasarlanacaktır.
- **Testler (`tests/`):** Servisler ve istemciler arasındaki davranışı kapsayan entegrasyon testleri ile kullanıcı ve sistem gereksinimlerini doğrulayan kabul testleri burada planlanır.

## Veri akışı

Android ve React web istemcilerinin merkezi işlevler için Go REST API'ye istek göndermesi hedeflenir. API, doğrulama ve iş kurallarından sonra gerekli merkezi verileri MySQL'den okur veya yazar. Android'in çevrimdışı kullanım için tuttuğu SQLite verileri çevrimiçi bağlantı kurulduğunda API aracılığıyla eşitlenir. Python AI/ML işlevlerinin veri alıp sonuçları sisteme sunma yolu, ilgili kullanım senaryoları netleşince API sınırları içinde tasarlanır.

## Güvenlik sınırları

- İstemciler MySQL'e doğrudan bağlanmaz; merkezi veriye erişim API üzerinden yapılır.
- API, kimlik doğrulama, yetkilendirme, girdi doğrulama ve iş kuralı kontrollerinin merkezi noktası olarak tasarlanır. Kullanılacak kimlik doğrulama yöntemi henüz belirlenmemiştir.
- Gizli anahtarlar ve ortam özelindeki değerler sürüm kontrolüne alınmaz; `.env.example` yalnızca daha sonra kesinleşecek değişkenler için açıklama taşır.
- Android'deki yerel SQLite verisi cihaz sınırında tutulur. Hassas yerel verilerin korunma ve eşitleme kuralları ilgili gereksinimler netleştiğinde tanımlanmalıdır.
- AI/ML bileşeninin API ve veri erişimi, yalnızca gerekli girdiler ve yetkilerle sınırlandırılmalıdır.
