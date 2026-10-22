# Cilt 1.38 — ERD Alan Envanteri Çıkarımı ve Kanıtlı Eşleştirme

**Tarih:** 22 Ekim 2026  
**Durum:** Makine destekli çıkarım tamamlandı; tam alan envanteri kaynakta yapılandırılmış biçimde bulunmadığından `NOT_COMPLETE`.  
**Kaynak:** `volume-01-2-erd-and-data-schema.md`; karşılaştırma için Cilt 1.3, 1.4, 1.5, 1.9 ve 1.24.  
**Önemli:** Bu sürüm migration veya veritabanı değişikliği yapmaz.

## 1. Ne bulduk?

- ERD dokümanında SQL code fence içinde makine tarafından ayrıştırılabilecek `CREATE TABLE` ifadesi: **0**.
- Başlık sayısı: **70**.
- Backtick biçimindeki farklı identifier adayı: **100**.
- Bu sayılar tam tablo/kolon sayısı değildir. Backtick ifadeleri tablo, kolon, enum, endpoint, durum ya da örnek kod olabilir. Bu nedenle otomatik olarak tablo/kolon envanteri kabul edilmedi.
- Mermaid diyagramı ana ilişkileri gösterir; tüm kolonların nullability, default, index, unique, FK ve CHECK ayrıntılarını tek başına kanıtlamaz.

## 2. Makine çıkarım dosyaları

1. `manifests/erd-schema-extraction-v1.38.json` — kaynak başlıkları, SQL tablo çıkarım sonucu, identifier adayları, workflow mention kanıtları ve uyarılar.
2. `manifests/erd-field-inventory-template-v1.38.csv` — kolon bazlı doğrulama şablonu. İçindeki dört kritik örnek `VERIFY` olarak işaretlidir; bunlar tam envanter veya migration-ready şema iddiası değildir.

## 3. Kritik alanlar — doğrulama şablonu

| Tablo | Alan | Neden kritik? | Durum |
|---|---|---|---|
| `products` | `requires_expiry_date` | Ürün politikasına göre son kullanma tarihi zorunluluğu | `VERIFY` |
| `lots` | `expiry_date` | Lot kabulü ve tarih kontrolü | `VERIFY` |
| `butchering_waste_records` | `reason_code` | Fire sebebi, `OTHER` açıklaması ve denetim | `VERIFY` |
| `butchering_waste_records` | `allocated_cost` | BY_WEIGHT/BY_VALUE maliyet tahsisi ve yuvarlama | `VERIFY` |

Bu alanların iş kuralları önceki onaylı kararlarda mevcut olsa da, tam tablo tanımı, FK, nullability, index ve DTO/test karşılığı bu sürümde henüz satır satır kanıtlanmış değildir.

## 4. Workflow ve API çapraz kontrolü

- WF-01–WF-10 için Cilt 1.5 ve Cilt 1.19'daki kaynak satırları manifestte kanıt olarak saklandı; yalnızca ID'nin bulunması transition/side-effect doğruluğunu kanıtlamaz.
- Cilt 1.3 ile Cilt 1.9 imza karşılaştırması yeniden üretildi: API **57**, yetki matrisi **56**; fark: `POST /api/v1/butchering-orders/{order_id}/waste-records` API'de var, yetki matrisi satırlarında yok.
- Bu statik çalışma çalışan OpenAPI/test sonuçları üretmez.

## 5. Migration öncesi gerekli kanıtlar

1. Tam tablo/kolon envanteri ve Mermaid dışındaki tüm tabloların kapsanması.
2. Her kolonun SQL tipi, nullability, default, PK/FK, unique/index/check kısıtları.
3. API request/response DTO alanlarının birebir ERD kolonlarına eşlenmesi.
4. WF-01–WF-10 için geçiş, stok hareketi, genealogy, maliyet, audit ve idempotency etkileri.
5. API/permission farkının kapatılması.
6. Migration planı ve rollback/upgrade test stratejisi.
7. Proje sahibinin ayrı açık migration/DB onayı.

Bu şartlar henüz tamamlanmış olarak gösterilemiyor. Dokümantasyona devam onayı migration izni yerine geçmez.

## 6. Sonraki somut iş

Cilt 1.39'da ERD'nin tablo tanımı bölümleri tek tek çıkarılacak ve tablo bazında alanlar/tipler, PK/FK, unique/index/check, API DTO eşlemesi, workflow kullanımı, test kimlikleri ve çelişen kaynaklar tek matriste birleştirilecek. Kaynak metinde açıkça olmayan ayrıntılar `OPEN` kalacak; uydurulmayacak.
