# Cilt 1.39 — ERD Tablo Kaydı ve Alan Düzeyi Açık Nokta Defteri

**Tarih:** 22 Ekim 2026  
**Durum:** Aday tablo kayıtları ve açık nokta defteri oluşturuldu; tam ERD/kolon doğrulaması hâlâ açık.  
**Kapsam:** Cilt 1.2'nin tablo/kolon kanıtını kaynak satırlarıyla düzenlemek; Cilt 1.3/1.9 ve WF-01–WF-10 ile ilişkilendirmek.  
**Migration/DB:** Hiçbir migration oluşturulmadı; veritabanı değiştirilmedi.

## 1. Bu ciltte yapılan iş

Cilt 1.2 içindeki Markdown tabloları, başlıklar, kod biçimli identifier'lar ve Mermaid entity adları ayrıştırıldı. Sonuçlar aşağıdaki dosyalara kaydedildi:
- `manifests/erd-table-column-register-v1.39.json`
- `manifests/erd-table-register-v1.39.csv`
- `manifests/open-gap-ledger-v1.39.csv`

**Aday isimler kesin tablo şeması değildir.** Bir ismin Mermaid diyagramında veya metinde geçmesi, o tablonun kolonlarının, FK'lerinin ya da constraint'lerinin kesin olarak tanımlandığını kanıtlamaz. Bu nedenle her adayın `column_inventory_status=NOT_EXTRACTED` durumu korunmuştur.

## 2. Çıkarım özeti

- Markdown tablosu blokları: **9**
- Tablo/şema ile ilgili başlık adayları: **6**
- Aday tablo adı: **34**
- ERD içinde farklı backtick identifier: **100**
- API endpoint imzası: **57**
- Yetki matrisi imzası: **56**
- API-only fark: **1** — `POST /api/v1/butchering-orders/{order_id}/waste-records`
- Permission-only fark: **0**

Bu rakamlar doküman çıkarım metrikleridir; gerçek DB şemasının büyüklüğü veya tamamlanmışlığı hakkında tek başına kanıt sayılmaz.

## 3. Neden kolonları uydurmadım?

Kolonun gerçek tipi, nullable/default davranışı, PK/FK, index ve CHECK kısıtı migration güvenliğini doğrudan etkiler. Kaynakta açıkça bulunmayan kolon tanımı tahmin edilirse uygulama ve migration dokümanı birbirinden ayrışır. Bu yüzden Cilt 1.39, kolon bilgisi yerine kanıt satırlarını ve açık noktaları kaydeder.

## 4. Açık nokta defteri

`manifests/open-gap-ledger-v1.39.csv` içinde şu başlıklar `OPEN` olarak izlenir:
- Tam tablo ve kolon envanteri
- PK/FK ve referential action kuralları
- Unique/index/CHECK constraint'leri
- Waste-records endpoint izin satırı
- Recall çözüm/serbest bırakma ayrımı
- İşlem bazlı correction/reversal
- Lot receipt retry/duplicate davranışı
- AI prediction persistence/state contract
- Her entity'nin nihai enumları

Her açık nokta için gereken kanıt ve bir sonraki somut aksiyon aynı satırda yer alır.

## 5. Sonraki somut adım

Cilt 1.40, bu kayıt defterini kullanarak Cilt 1.2'deki her tablo için kaynak metin üzerinden **doğrulanmış alan kartı** üretmeye odaklanacak. Her alan kartında kaynak başlığı/satırı, SQL tipi, nullability/default, anahtar/kısıtlar ve DTO/workflow/test eşlemesi olacak. Kaynakta yoksa değer `OPEN` kalacak.

Cilt 1.40'ın sonunda migration'a geçilip geçilemeyeceğine dair bir **readiness verdict** verilecek; bu verdict tek başına migration/DB izni değildir. Ayrı açık izin şartı korunur.
