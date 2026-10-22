# AVATAR — Kodlama LLM'ine Teslim Talimatı

**Paket sürümü:** 1.46 (v1.45 doküman tabanı + devir paketi)  
**Dil:** Türkçe dokümantasyon; kod/identifier İngilizce.  
**Amaç:** Bu paketi alan LLM, AVATAR sisteminin uygulanmasını üstlenir. Proje sahibi kod yazdırmak için başka bir LLM kullanır; bu belge uygulama talimatıdır.

## 1. Önce okunacak dosyalar

1. `LLM_HANDOFF.md` (bu dosya).
2. `AVATAR_MASTER_BRIEF.md` — ürün kapsamı, teknoloji ve bağlayıcı kararlar.
3. `BACKEND_DATABASE_ARCHITECTURE_CLOSURE.md` — mimari, transaction, stok ve recall kuralları; v1.45'teki daha yeni kararlar eski ciltlerdeki çelişkili notlara üstün gelir.
4. `DOCUMENT_INDEX.md` — görev bazında hangi kaynakların açılacağı.
5. `IMPLEMENTATION_PLAN.md` — geliştirme sırası.
6. `ACCEPTANCE_CRITERIA.md` — tamamlanma koşulları.
7. `KNOWN_GAPS.md` — belirsizliklerin güvenli ele alınışı.

İlgili görev için `DOCUMENT_INDEX.md` içindeki kaynakları aç. Tüm ciltleri baştan sona okumak zorunlu değildir. `volumes/` ve `manifests/` içindeki sürüm numaralı belgeler tarihçe/kanıt kaynağıdır; güncel kanonik kararla çelişirse otomatik olarak eski ciltteki kuralı uygulama. Çelişkiyi `KNOWN_GAPS.md`'ye kaydet ve v1.45 kapanış belgesindeki en yeni kararı esas al.

## 2. Teknoloji sabitleri

- Backend: Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PyMySQL.
- DB: MySQL 8.4 LTS.
- API: REST/JSON, `/api/v1`, OpenAPI.
- Test: pytest; unit, integration, contract, concurrency ve end-to-end.
- Lokal çalıştırma: Docker Compose; secrets yalnızca `.env` dosyasında, gerçek secret repoya konulmaz.
- İstemciler MySQL'e doğrudan bağlanmaz. Backend tek doğruluk kaynağıdır.

Mevcut `backend/` klasörü yalnızca başlangıç iskeletidir; eksiksiz uygulama değildir. Var olan dosyaları incele, üzerine kontrollü biçimde geliştir. Baştan farklı teknoloji yığınına geçme.

## 3. Mimari zorunluluklar

- Router: HTTP/DTO/auth dependency/response mapping; iş mantığı service/use-case katmanında.
- Kritik iş akışlarında transaction sınırı servis katmanında olmalı.
- Para `Decimal` + DB `DECIMAL(19,4)`; ağırlık/miktar `Decimal` + `DECIMAL(19,6)`.
- API'de para ve miktar JSON string olarak taşınır; timestamp UTC ISO-8601 `Z`; tarih-only `YYYY-MM-DD`.
- Stok hareket defteri append-only: miktar pozitif, yön `IN` veya `OUT`. `stock_movements` ve `inventory_balances` aynı transaction'da güncellenir.
- Lot genealogy miktarlı çoktan-çoğa olmalı.
- Kritik kayıtlar hard-delete edilmez; correction/reversal + audit gerekir.
- Hata zarfı `error.code`, `error.message`, isteğe bağlı `error.details`, `request_id` biçiminde tutarlı olmalı.
- Satışta `Idempotency-Key` zorunlu: aynı anahtar+aynı gövde aynı sonucu döndürür; aynı anahtar+farklı gövde `409`.
- AI tahmini operasyonel stok, lot veya recall gerçeğinin kaynağı değildir.

## 4. Bağlayıcı iş kuralları

1. **Parçalama:** Satılabilir çıktılar ürün/lot olarak stoklanır. Fire ayrı kayıttır, stok `IN` hareketi değildir.
2. **Üretim:** İlk sürümde rezervasyon yoktur. `IN_PROGRESS` stok düşürmez. Tamamlama sırasında tüketim `OUT`, ürün `IN`, genealogy, maliyet ve audit tek transaction içinde tamamlanır.
3. **Sevkiyat:** Fiziksel stok `OUT` işleminin tek sahibi dispatch/sevkiyattır. Satış aynı miktarı ikinci kez stoktan düşmez.
4. **Recall:** Aktivasyon senkron/atomiktir. `ACTIVATING` durumu yoktur. Recall `RESOLVED` olduğunda lot blokajı otomatik kalkmaz; ayrı yetkili release/unblock gerekir.
5. **Ağırlık farkı:** Kaynakta evrensel tolerans yoktur. Sessiz normalize etme yok; ayar ve gerekçe/audit kullan. Demo varsayılanı `0.000 kg` bir proje konfigürasyonudur, kaynakta verilmiş gerçek değer değildir.
6. **Düzeltme:** Tamamlanmış işlem silinmez/üzerine yazılmaz; kaynak kaydı, gerekçe, yetki, audit ve ters stok hareketleri tek transaction'da tutulur.
7. **Maliyet:** `BY_WEIGHT` dağıtımı ölçülen ağırlık kategorilerine, fire dahil, maliyet payı verir; fire maliyeti ayrı gösterilir ve satılabilir ürün stok maliyetine karıştırılmaz. `BY_VALUE` güvenilir/onaylı fire değerlemesi olmadan tamamlanamaz; sıfır değer veya rastgele fallback icat etme. Yuvarlama artığı toplamı eşitlemek için deterministik son tahsis satırına verilir.
8. **Son tüketim tarihi:** `products.requires_expiry_date` varsayılan `false`; `true` ise lot `expiry_date` zorunlu.
9. **Güvenlik:** Roller `ADMIN`, `OPERATOR`, `SALES`, `TRACEABILITY_MANAGER`, `VIEWER`; izinler endpoint bazında kontrol edilir. Access token 15 dakika, refresh token 7 gün ve rotation; refresh token hash'i saklanır. Token/secret loglanmaz.
10. **Fire endpoint'i:** `POST /api/v1/butchering-orders/{order_id}/waste-records` için kapanış belgesindeki eşleme `ADMIN`/`OPERATOR` + `butchering:manage` olarak uygulanır; eski manifestteki eksiklik/gap notunu güncel kararın üstüne koyma.

## 5. Uygulama şekli

- Önce mevcut repository yapısını ve tüm kaynakları envanterle; dosyaları sebepsiz yere yeniden adlandırma.
- Her fazı küçük ve test edilebilir değişiklikler olarak uygula. Önce model/constraint haritası, sonra ORM, migration, servis, router, test.
- Her tabloda PK/FK/unique/check/index/nullability ve decimal precision kararlarını kaynak şema ile karşılaştır. Kaynakta alanı net değilse rastgele kolon/iş kuralı üretme; makul, geri alınabilir bir teknik default gerekiyorsa bunu kod yorumunda ve `KNOWN_GAPS.md`'de açıkça kaydet.
- Migration oluşturmak ve çalıştırmak serbesttir **yalnızca yerel/izole test DB'de**. Kullanıcının gerçek/üretim DB'sine bağlanma; gerçek veriyi silme/değiştirme.
- Her migration için upgrade/downgrade davranışını kontrol et. Testler için sentetik seed kullan.
- Transaction ve eşzamanlılık kurallarını test et; özellikle recall aktivasyonu ile stok çıkışının aynı lot üzerinde yarışması.
- AI servisleri hata verdiğinde stok/izlenebilirlik operasyonları çalışmaya devam etmeli. ML için baseline ve hata metriği olmadan performans iddiası yazma.
- Sadece kod üretmek yeterli değildir: komutları çalıştır, test çıktısını gerçek sonuçlarla raporla. Çalıştırmadığın teste “başarılı” deme.

## 6. İletişim ve karar yönetimi

Proje sahibi, teknik kararları yürütmek için genel yetki vermiştir. Rutin ve geri alınabilir uygulama kararlarında onay bekleme. Güvenli bir default seçmen gerekiyorsa en dar, açıkça belgelenmiş seçeneği seç ve kaydet. Ancak:

- Üretim/gerçek DB, gerçek kimlik bilgisi veya dış serviste yıkıcı işlem yapma.
- Kaynakta bulunmayan ticari/izlenebilirlik verisi uydurma.
- Bir çelişkiyi sessizce çözme: en güncel kanonik belgenin kararını uygula; gerçekten çözülemiyorsa ilgili davranışı fail-closed tasarla ve `KNOWN_GAPS.md`'ye yaz.
- Her faz sonunda değişen dosyaları, test komutlarını, gerçek sonuçları, migration durumunu ve kalan engelleri kısa raporla.

## 7. İlk görev

İlk çıktı olarak:

1. `backend/` dosyalarını ve kaynak ERD/API/workflow sözleşmelerini incele.
2. ERD tablo/alanlarını, ORM modellerini, DTO'ları, endpoint'leri, izinleri ve testleri eşleyen bir parity matrisi oluştur.
3. P0 eksiklerini `KNOWN_GAPS.md` ile karşılaştırıp kapatılabilir olanları kodla; sırf doküman üretmek için yeni cilt açma.
4. ORM modelleri ve ilk Alembic migration'ını **yalnızca yerel test DB'si** için oluştur.
5. Başlangıç testleri + migration smoke testini çalıştır ve sonuçları raporla.

## 8. Teslimat

Proje tamamlandığında kaynak kod, migration, seed, `.env.example`, çalıştırma rehberi, OpenAPI çıktısı/kontrat testleri, test raporu, bilinen sınırlamalar ve demo adımları birlikte teslim edilmeli. “Tamamlandı” ifadesi yalnızca ilgili kabul kriterleri test edilmişse kullanılabilir.
