# ADR-001 — Android Çevrimiçi Öncelikli Çalışma

- **Durum:** Kabul edildi
- **Tarih:** 22 Ekim 2026
- **Karar sahibi:** Proje sahibi
- **Kapsam:** Kotlin Android uygulamasının satış ve merkezi veri işlemleri

## Bağlam

Yarışma PDF'si Kotlin Android uygulaması, yerel SQLite ve merkezi MySQL ister. SQLite ile MySQL arasında tutarlı senkronizasyon yaklaşımının açıklanmasını bekler. Lot bazlı satışların ve geri çağrılan lotların satışının kontrol edilmesi gerekir.

Tam çevrimdışı satış, yerel stok ile merkezi stok arasındaki çakışmalar, tekrar gönderilen satışların idempotent işlenmesi ve çevrimdışı cihazların güncel geri çağırma durumunu bilmemesi gibi ek riskler doğurur. Son teslim tarihi 1 Kasım 2026'dır.

## Karar

Android uygulaması **çevrimiçi öncelikli** çalışacaktır. Proje sahibi 22 Ekim 2026'da aşağıdaki teknoloji standardını onaylamıştır.

- Android: Kotlin + Jetpack Compose.
- Yerel veritabanı: **SQLite zorunludur**; SQLite erişim katmanı olarak Room kullanılacaktır. Room, SQLite'ın alternatifi değil, SQLite üzerinde çalışan persistence katmanıdır.
- Android API istemcisi: Retrofit + OkHttp; asenkron işlemler Kotlin Coroutines ile yürütülür.
- Backend: Python + FastAPI; istek/yanıt doğrulaması Pydantic ile, ORM SQLAlchemy 2.x ile, migration'lar Alembic ile, MySQL sürücüsü PyMySQL ile yönetilir.
- Merkezi veri: MySQL 8.4 LTS; Android MySQL'e doğrudan bağlanmaz.
- Web paneli: React + TypeScript + Vite + Tailwind CSS + TanStack Query + Recharts.
- ML: pandas + NumPy + scikit-learn + joblib; ilk sürümde FastAPI backend içinde ayrı modül.
- Test/çalıştırma: Git/GitHub, Docker Compose, pytest, JUnit, Vitest + React Testing Library.
- API: REST + JSON + OpenAPI.
- Satışın kabulü ve stok/lot doğrulaması backend tarafından yapılır.
- Backend doğrulaması ve başarılı yanıt olmadan istemci satışı tamamlanmış olarak göstermez.
- Çevrimdışı satış ilk teslim kapsamının dışındadır.
- SQLite/Room kapsamı, yerel veri/önbellek ve ilgili yenileme politikası Cilt 4'te ayrıntılandırılacaktır; SQLite'ın kullanılması kesin karardır.

## Değerlendirilen seçenekler

1. Çevrimiçi öncelikli: En düşük uygulama ve test karmaşıklığı; internet yokken satış yapılamaz.
2. Kontrollü çevrimdışı satış: Kesintilere dayanıklıdır ancak kuyruk, çakışma, tekrar gönderim ve geri çağırma politikaları gerektirir.
3. Hibrit risk bazlı satış: Bazı işlemler çevrimdışı olabilir; işlem bazında izin ve durum yönetimi ek karmaşıklık getirir.

## Gerekçe

Yarışma için temel gereksinimlerin güvenilir biçimde teslim edilmesine ve 1 Kasım tarihine öncelik verildi. Çevrimdışı satış, PDF'de açık bir zorunluluk olarak tanımlanmadığından ilk sürümde kapsam dışında tutuldu. Bu karar, SQLite kullanımını veya senkronizasyon yaklaşımının açıklanmasını ortadan kaldırmaz.

## Sonuçlar

### Olumlu
- Merkezi stok ve lot kontrolü sadeleşir.
- Geri çağırılan lotun satışını merkezi olarak engellemek daha kolaydır.
- Senkronizasyon ve test kapsamı daralır.
- İlk sürüm daha hızlı bütünleştirilebilir.

### Olumsuz / sınırlamalar
- Bağlantı veya backend erişimi yokken yeni satış tamamlanamaz.
- Yerel verinin güncelliği ve önbellek politikası yine tanımlanmalıdır.

## Kabul kriterleri

- Android uygulaması MySQL'e doğrudan bağlanmaz.
- Satış, REST API üzerinden gönderilir.
- Backend yetersiz stok veya bloke lot satışını reddeder.
- Aynı satış isteğinin tekrar gönderilmesi çift stok hareketi oluşturmaz.
- Başarılı sunucu yanıtı olmadan satış tamamlandı olarak gösterilmez.
- İnternet/API hatası kullanıcıya anlaşılır biçimde gösterilir.
- Çevrimdışı satış kapsam dışı olduğu kurulum ve kullanıcı dokümanında belirtilir.

## Yeniden değerlendirme koşulu

Yarışma değerlendirmesi veya işletme gereksinimi çevrimdışı satışın zorunlu olduğunu gösterirse yeni bir ADR hazırlanmalı, iş yükü ve riskler yeniden değerlendirilmelidir. Bu ADR sessizce değiştirilmemelidir.
