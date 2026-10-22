# Cilt 1.28 — Yarışma Teslimatı ve Demo Dağıtım Kararı

**Tarih:** 22 Ekim 2026  
**Durum:** Teslimat gereksinimlerine dayalı mimari değerlendirme; REG-125-08 kararı henüz kapanmadı.  
**Kaynak:** Kullanıcının paylaştığı AVATAR yarışması teslimat şartları.  
**Amaç:** GitHub deposu ve en fazla 15 dakikalık demo videosu şartlarının web/API deployment kararına etkisini açıklamak.

## 1. Kaynaktan doğrulanan teslimat şartları

Kullanıcının paylaştığı metne göre:

- Son teslim: **1 Kasım 2026, 23:59**.
- Teslim e-postası: `ext.s.a.bakir@delta-ac.de`; önceki e-postaya yanıt verilecek ve konu satırında takım adı yazılacak.
- E-postaya iki bağlantı eklenecek:
  1. Herkese açık GitHub deposu; kaynak kodu ve kurulum açıklaması (`README`) içermeli.
  2. Üç görevin uçtan uca gösterildiği, en fazla 15 dakikalık video; YouTube liste dışı veya Google Drive bağlantısı olabilir.
- Teslimat listesinde canlı üretim sunucusu veya herkese açık çalışan web adresi açıkça zorunlu kılınmamış.

Son madde yalnızca paylaşılan teslimat metnine dayanır. Yarışmanın başka belgelerinde ek koşullar varsa ayrıca kontrol edilmelidir.

## 2. Bu şartlar deployment kararını nasıl etkiler?

GitHub deposunun public olması, uygulamanın internette canlı ve herkese açık bir servis olarak çalışması gerektiği anlamına gelmez. Kurulum açıklaması ve çalıştırılabilir prototip şartı, yerel olarak yeniden çalıştırılabilir bir demo yaklaşımını destekler.

Demo videosu da sistemin nasıl çalıştığını gösterir; fakat tek başına kurulum talimatlarının, kaynak kodunun, örnek verilerin ve testlerin yerini tutmaz.

Dolayısıyla yarışma şartları tek başına REG-125-08 için A/B/C web token seçimini belirlemez. Önce iki ayrı konuyu ayırmalıyız:

1. **Yarışma demo/yerel çalışma topolojisi:** Jüri videosunda ve README adımlarında sistem nasıl çalıştırılacak?
2. **İlerideki internet üzerinden production topolojisi:** Gerçek alan adı, HTTPS, web/API origin'leri ve oturum güvenliği nasıl olacak?

İkinci konu henüz belirlenmediyse bunu zorla kararlaştırmak yerine TBD bırakabiliriz.

## 3. Önerilen teslimat mimarisi

### Öneri: Önce yeniden üretilebilir yerel demo

İlk teslimat için aşağıdaki yaklaşımı öneriyoruz; bu bir öneridir ve kullanıcı onayı olmadan kesin karar sayılmaz:

- GitHub deposunda kaynak kodu, README, örnek çevre değişkeni dosyası (`.env.example`), Docker Compose yapılandırması ve test komutları bulunur.
- Gerçek parola, token, API anahtarı veya kişisel veri depoya eklenmez.
- Örnek seed/demo verisi komutla kurulabilir ve demo senaryosu tekrarlanabilir olur.
- Backend MySQL'e yalnızca backend üzerinden erişir.
- Demo, temiz bir ortamda kurulumdan başlayarak üç görevi gösterecek şekilde prova edilir.
- `ET-2026-001` için backward/forward trace ve etkilenen Market A/B/C miktarları videoda gösterilir.
- AI için yalnızca tahmin ekranı değil; yöntem, örnek tahmin, gerçek değer, hata metriği ve veri kısıtları da gösterilir.
- Video en fazla 15 dakika olacak şekilde zamanlanır; GitHub README'si aynı demo akışını yazılı olarak tekrar ettirir.

### Web ve API origin kararı

Yerel demo için iki olası model vardır:

**Model D1 — Tek origin/reverse proxy (tercih edilen hedef, uygulanabilirliği doğrulanmalı)**  
Web paneli ve API tek origin altında sunulur; `/api` istekleri backend'e yönlendirilir. Cookie tabanlı auth seçilirse origin/CORS karmaşıklığını azaltabilir. Bunun için proxy yapılandırması ve HTTPS/cookie davranışı yine test edilmelidir.

**Model D2 — Geliştirmede ayrı portlar**  
Örneğin web geliştirme sunucusu ile FastAPI farklı portlarda çalışır. Bu farklı origin demektir ve cookie/CORS/CSRF testlerini gerektirir. Geliştirme ayarları üretim ayarları gibi kabul edilmemelidir.

Bu seçeneklerden hangisinin uygulanabilir olduğu repo düzeni, Docker Compose ve demo işletim adımlarına göre belirlenmelidir.

## 4. REG-125-08 kararı için sonuç

Kullanıcının teslimat bilgisi, **C yaklaşımını destekliyor**: önce gerçek ihtiyaçları ve demo mimarisini belirlemek. Ancak teslimat metni canlı deployment zorunlu tutmadığı için production domain'lerini şu an uydurmamalıyız.

Önerilen karar yolu:
1. İlk teslimatın yerel olarak çalıştırılabilir olmasını hedefle.
2. README ve demo videosunun aynı, deterministik senaryoyu kullandığını doğrula.
3. Web/API için D1 tek origin yaklaşımının uygulanabilirliğini değerlendir.
4. D1 uygulanabiliyorsa web token/CSRF tasarımını bu topoloji üzerinde değerlendir.
5. D1 uygun değilse D2 için CORS, cookie ve CSRF davranışını ayrı ayrı tanımla.
6. Bu keşif tamamlanmadan REG-125-08'i kapatma.

## 5. Teslimat kontrol listesi

- [ ] Public GitHub repo adresi hazır.
- [ ] README, desteklenen çalışma ortamı ve kurulum adımlarını açıklıyor.
- [ ] `.env.example` var; gerçek secrets repoda yok.
- [ ] Seed/demo data tek komutla veya belgelenmiş adımlarla yüklenebiliyor.
- [ ] Otomatik testler nasıl çalıştırılacağıyla birlikte belgelenmiş.
- [ ] Temiz ortamda kurulum provası yapıldı.
- [ ] Üretim maliyeti örneği ve beklenen `18.16 EUR/pack` gösterildi.
- [ ] Kasaplık iş akışında ağırlık ve maliyet dengesi gösterildi; PDF'deki sayısal tutarsızlık uydurma bir açıklamayla kapatılmadı.
- [ ] `ET-2026-001` üzerinden `URT-2026-045`, `SUC-2026-045` ve Market A/B/C sevkiyatları izlenebiliyor.
- [ ] Geri çağırma etkilenen lotun satışını engelliyor.
- [ ] İki AI görevi için yöntem, tahmin/gerçek karşılaştırması, metrik ve sınırlamalar hazır.
- [ ] Demo video 15 dakikayı aşmıyor ve bağlantı erişim izinleri kontrol edildi.
- [ ] E-posta konu satırında takım adı var ve iki gerekli link eklenmiş.

## 6. Açık kalan kararlar ve sınırlar

- REG-125-08: **OPEN** — demo origin modeli ve web token/CSRF yaklaşımı onay bekliyor.
- REG-125-09–REG-125-15: **OPEN** — bu cilt bunları kapatmaz.
- Production domain/hosting: **TBD**.
- Canlı herkese açık web uygulaması: paylaşılan teslimat metninde açıkça zorunlu değil; ek yarışma şartları varsa ayrıca doğrulanmalı.
- Migration: **NOT AUTHORIZED**.
- Dış LLM'ye kodlama devri: açık kararlar ve nihai çapraz kontrol tamamlanana kadar **NOT READY**.
