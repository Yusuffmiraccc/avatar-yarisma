# Cilt 1.36 — Kesin İmza Farkı, Denetim Kanıtı ve Kapanış Kapıları

**Tarih:** 22 Ekim 2026  
**Durum:** Statik imza karşılaştırması tamamlandı; Cilt 1 henüz migration'a hazır değil.  
**Amaç:** Cilt 1.35'teki belirsiz denetim sonuçlarını ölçülebilir, tekrar üretilebilir bulgulara dönüştürmek.

## 1. Denetimin kesin sonucu

Cilt 1.3 API sözleşmesi ve Cilt 1.9 yetkilendirme dokümanları, HTTP method + path imzaları bakımından statik regex ile karşılaştırıldı.

- API sözleşmesinde benzersiz imza: **57**
- Yetki dokümanında benzersiz imza: **56**
- Her iki belgede bulunan: **56**
- API'de olup yetki dokümanında bulunmayan: **1**
- Yetki dokümanında olup API'de bulunmayan: **0**

### 1.1 Kesin fark

| Method | Path | Sonuç | Yapılması gereken |
|---|---|---|---|
| `POST` | `/api/v1/butchering-orders/{order_id}/waste-records` | `API_ONLY` | Cilt 1.9'a endpoint satırı eklenmeli; auth, rol/izin, kaynak kapsamı, hata, audit/transaction, idempotency ve testler açıkça belirlenmeli. |

Bu denetimde bulunan somut fark: **`POST /api/v1/butchering-orders/{order_id}/waste-records`**, API sözleşmesinde var; Cilt 1.9 endpoint izin matrisi satırlarında yok. Başka bir method/path farkı regex envanterinde bulunmadı.

**Önemli sınır:** Bu sonuç sadece dokümandaki imza metinlerinin karşılaştırılmasıdır. Auth/rol hücrelerinin doğruluğunu, DTO uyumunu, transaction atomikliğini veya çalışan router'ın bu endpoint'i gerçekten sunduğunu kanıtlamaz.

Makine tarafından okunabilir kanıtlar:
- `manifests/endpoint-permission-manifest-v1.36.json`
- `manifests/endpoint-signatures-v1.36.csv`

## 2. “Belirsizlik kalmasın” için durum sınıfları

Bu cilt, belirsizliği gizleyip `PASS` vermek yerine her kontrolü şu sonuçlardan biriyle sınıflandırır:

- **CLOSED-DOC:** Belge içindeki metinsel karşılaştırma tamamlandı ve fark açıkça gösterildi.
- **OPEN-OWNER-DECISION:** İş kuralı proje sahibinin kararı olmadan güvenle seçilemez.
- **OPEN-SOURCE-DETAIL:** Kaynak dokümanda gereken alan/geçiş/test açıkça bulunmuyor veya kanıtı yeterli değil.
- **NOT-RUNTIME-VERIFIED:** Çalışan API, ORM, OpenAPI çıktısı ya da gerçek MySQL üzerinde kanıt yok.
- **BLOCKED-BY-APPROVAL:** Migration/DB işlemi için ayrıca açık izin gerekir.

Bir kontrol bu kategorilerden birindeyse uygulayıcı LLM kendi varsayımıyla kapatamaz; ilgili belge/karar/test kanıtı üretilmelidir.

## 3. Workflow WF-01–WF-10 denetim durumu

Cilt 1.19'un kendi metni WF-01–WF-10'un bazı ayrıntılarını açık bırakıyor. Dolayısıyla yalnızca ID'lerin bulunması workflow sözleşmesini tamamlamaz.

| ID | Konu | Cilt 1.19'da belirtilen açık nokta | Cilt 1.36 sonucu |
|---|---|---|---|
| WF-01 | Butchering Output & Waste | Cilt 1.17 kararı var; kaynak/output/waste satırı, maliyet ve stok etkileri testle doğrulanmalı | `OPEN-SOURCE-DETAIL` |
| WF-02 | Production Consumption & Completion | Cilt 1.5 revizyonuna atıf var; alan/transition/transaction/test birebir eşlemesi gerekli | `OPEN-SOURCE-DETAIL` |
| WF-03 | Sale & Dispatch Stock Ownership | Satış ile fiziksel stok çıkışının ayrımı onaylı; uçtan uca endpoint/ledger testleri gerekli | `OPEN-SOURCE-DETAIL` |
| WF-04 | Recall Activation, Resolution & Release | Temel kural onaylı; çözüm ve serbest bırakma ayrıntıları açık | `OPEN-OWNER-DECISION` |
| WF-05 | Weight Balance & Variance | Tolerans 0 kg; yetkili açıklamalı varyansın kesin yetki/DTO/transition sözleşmesi gerekli | `OPEN-SOURCE-DETAIL` |
| WF-06 | Correction & Reversal | Genel kural onaylı; işlem bazında düzeltme/ters kayıt akışları açık | `OPEN-OWNER-DECISION` |
| WF-07 | Critical Command Retry | Genel ilke onaylı; endpoint bazlı idempotency matrisi tamamlanmalı | `OPEN-SOURCE-DETAIL` |
| WF-08 | Lot Receipt & Stock Entry | Idempotency ve kesin durumlar açık | `OPEN-OWNER-DECISION` |
| WF-09 | AI Prediction Lifecycle | Kalıcı durum enumu gerekip gerekmediği açık | `OPEN-OWNER-DECISION` |
| WF-10 | MVP State Minimalism | Her entity için nihai enum eşlemesi açık | `OPEN-OWNER-DECISION` |

Bu tablo, Cilt 1.19'un kendi beyanını aktarır; eksik kuralları yeni iş kararıymış gibi uydurmaz. Her satır kapatılacaksa Cilt 1.5 + Cilt 1.2 + Cilt 1.3 + Cilt 1.4 + Cilt 1.9 + Cilt 1.24 birlikte revize edilmelidir.

## 4. Alan ve tablo envanteri — neden henüz `PASS` değil?

Cilt 1.2 ERD'sinde Mermaid ilişkileri, tablo tanımları ve metin içi alan adları bulunuyor. Markdown içindeki tüm backtick ifadelerini tablo/alan saymak hatalı olur. Bu nedenle Cilt 1.36, regex token sayısından sahte bir tablo envanteri türetmez.

Migration öncesi kanıt dosyası aşağıdaki kolonları içeren gerçek bir normalize envanter olmalıdır:

`table_name`, `column_name`, `mysql_type`, `nullable`, `default`, `pk`, `fk_target`, `unique_group`, `index_name`, `check_constraint`, `source_section`, `api_dto_field`, `workflow_usage`, `status`.

Her Cilt 1.2 tablo ve alanı satır bazında çıkarılmalı; her FK hedefi mevcut tablo/kolona bağlanmalı; her endpoint DTO alanı ERD kolonuna eşlenmeli. Eksik/çelişkili kayıtlar migration'dan önce çözülmelidir.

## 5. Cilt 1.9 için zorunlu düzeltme

Cilt 1.9'a `POST /api/v1/butchering-orders/{order_id}/waste-records` satırı eklenmeden endpoint/izin eşleşmesi tamamlanmış sayılamaz. Bu satır en az şu alanları açıkça içermelidir:
- Auth: authenticated
- Rol/izin: proje tarafından onaylanmış least-privilege kuralı; varsayılan olarak geniş rol izni verilmemeli
- Request/response DTO ve HTTP status
- `reason_code` ve `OTHER` açıklaması doğrulaması
- Girdi lotu ile waste kaydı bağlantısı; gerekiyorsa lot başına ayrı satır
- Kilo dengesi ve maliyet tahsisi etkisi
- Stok hareketi oluşup oluşmadığı (Cilt 1.2/1.5 ile uyumlu)
- Audit transaction davranışı
- Retry/idempotency davranışı
- Yetkisiz erişim, geçersiz durum, yetersiz stok ve işlem hatası testleri

Bu ciltte rol ataması tahmin edilerek kesinleştirilmemiştir; çünkü izin matrisindeki diğer rollerin karar bağlamı da owner-approved policy olarak teyit edilmelidir.

## 6. Öncelik sırasıyla kapanış listesi

1. **P0 — API/permission farkı:** waste-records endpoint'inin Cilt 1.9 yetki satırı.
2. **P0 — WF-04, WF-06, WF-08, WF-09, WF-10:** açık owner kararlarını Cilt 1.19'daki kayıtlarla sınırlı tutarak kapat.
3. **P0 — ERD normalize envanteri:** tüm tablolar, kolonlar, FK, unique/index/check; alan adı/tip/nullability düzeyinde.
4. **P0 — DTO ve hata eşlemesi:** her endpoint için request, response, status, error, permission, transaction/audit, idempotency, test ID.
5. **P0 — test izlenebilirliği:** WF başına başarı, yetki reddi, validasyon, transaction rollback, concurrency/retry, audit failure testleri.
6. **P1 — statik eski ifadeler:** superseded tarihsel kayıtları aktif normatif kurallardan açık biçimde ayır; iki aktif kaynak çelişkili kalmamalı.
7. **P1 — runtime doğrulama:** yalnızca ayrı onay sonrasında ORM metadata, üretilmiş OpenAPI, MySQL constraint ve test sonuçları.
8. **P1 — migration gate:** aşağıdaki proje sahibi onayı alınmadan migration dosyası üretme veya DB değiştirme.

## 7. Değişiklik ve güvenlik sınırı

- Bu cilt yalnızca doküman ve statik imza manifestidir.
- Alembic migration oluşturulmadı.
- MySQL veritabanına bağlanılmadı/değişiklik yapılmadı.
- Kod, ORM modeli veya API router'ı değiştirilmedi.
- **Migration/DB için izin verilmiş sayılmaz.** Proje sahibinin ayrı, açık onayı gerekir.
- Cilt 1.2 ERD ile Cilt 1.5 WF-01–WF-10 son bir kez birlikte kontrol edilip açık kararlar kapatılmadan migration'a geçilmemelidir.
