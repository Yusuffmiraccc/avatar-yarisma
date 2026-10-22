# Cilt 1.41 — Endpoint Bazlı Sözleşme Kapatma ve Yetki Boşluğu Analizi

**Tarih:** 22 Ekim 2026  
**Durum:** Dokümantasyon çapraz kontrolü; uygulama ve migration için onay değildir.  
**Önceki cilt:** Cilt 1.40 — Alan Kartları ve API–Workflow–Test Eşleştirmesi  
**Amaç:** Cilt 1.40'ta kalan endpoint imza farkını, kaynaklarla desteklenen API/DTO/workflow/test kanıtını ve çözülmemiş kararları tek bir denetlenebilir kayıt altında toplamak.

## 1. Yönetici özeti

Cilt 1.40'ın statik imza kontrolünde API sözleşmesinde 57 endpoint, Cilt 1.9 yetki matrisinde 56 endpoint bulunmuştu. Bu ciltte eksik yetki satırı şu endpoint olarak doğrulanmıştır:

`POST /api/v1/butchering-orders/{order_id}/waste-records`

Cilt 1.3'te fire kayıtlarının `butchering_outputs` tablosuna değil, ayrı `butchering_waste_records` tablosuna ve ayrı DTO'ya ait olduğu açıkça belirtilir. Cilt 1.5 de fire satırının stok lotu veya stok `IN` hareketi üretmemesi gerektiğini söyler. Cilt 1.9'un parçalama endpoint'leri için mevcut varsayılanı `ADMIN` ve `OPERATOR` rolleridir; ancak bu özel endpoint için izin satırı bulunmadığından bu roller yalnızca **aday öneri** olarak gösterilir ve proje sahibi onayı olmadan kanonik izin sayılmaz.

**Bu ciltteki sonuçlar:**
- Eksik endpoint-yetki satırı tespit edildi; öneri olarak hazırlandı, onaylanmadı.
- API/DTO/workflow bağlantısı kaynak metinleriyle işaretlendi; tüm endpoint'ler için tam DTO alanlarını yeniden üretmek yerine yalnızca kanıtlanabilen maddeler kaydedildi.
- WF-01–WF-10 kapsamındaki açık kararların hiçbiri bu dokümanla sessizce kapatılmadı.
- Runtime OpenAPI, gerçek ORM metadata, MySQL kısıtları veya otomatik test çalıştırması yapılmadı.
- **Migration readiness: NOT READY.**

## 2. Normatif kaynaklar ve yorumlama kuralı

Bu rapor aşağıdaki dosyaları esas alır:

1. `volume-01-2-erd-and-data-schema.md`
2. `volume-01-3-api-contracts.md`
3. `volume-01-4-openapi-dto-contract-tests.md`
4. `volume-01-5-workflows-state-machines.md`
5. `volume-01-9-endpoint-permissions-security-decisions.md`
6. `volume-01-19-canonical-workflow-ids-state-registry.md`
7. `volume-01-21-error-idempotency-response-registry.md`
8. `volume-01-24-end-to-end-acceptance-tests-llm-handoff.md`
9. `volume-01-40-field-cards-api-workflow-crosswalk.md`
10. `decisions/DEC-001-data-api-contracts-proposal.md` ve `decisions/ADR-001-android-online-first.md`

Kaynaklarda bir davranışın bulunması, onun otomatik olarak runtime'da uygulandığını kanıtlamaz. Bu nedenle her kayıt şu ayrımı korur:
- **SOURCE-SUPPORTED:** Dokümanlarda açıkça belirtilmiş.
- **CANDIDATE:** Tutarlılık için öneri; proje sahibi onayı gerekir.
- **OPEN:** Kaynaklar kesin cevap vermiyor veya birbiriyle doğrulanmadı.
- **NOT-RUNTIME-VERIFIED:** Kod, OpenAPI çıktısı, DB metadata veya test koşusu ile doğrulanmadı.

## 3. Eksik yetki satırı — aday öneri

### 3.1 Endpoint

`POST /api/v1/butchering-orders/{order_id}/waste-records`

### 3.2 Kaynaklardan kanıtlanabilen davranış

- Fire, stokta izlenen `CUT`/`BYPRODUCT` çıktılarından ayrı bir `butchering_waste_records` kaydıdır.
- Fire için ürün veya çıktı lotu yaratılmaz.
- Fire kaydı tek başına stok `IN` hareketi üretmez.
- Fire kaydı ağırlık dengesi ve maliyet dağıtımına katılır.
- Kayıt, ilgili parçalama emriyle ilişkilendirilmelidir.
- Cilt 1.31/1.32 onay kayıtlarındaki audit ilkesi geçerliyse, kritik işlem ile audit kaydı aynı transaction'da yazılmalı; audit yazılamazsa operasyon rollback edilmelidir.

### 3.3 Yetki önerisi — proje sahibi onayı gerekli

| Alan | Aday değer | Durum | Gerekçe |
|---|---|---|---|
| Authentication | Required | SOURCE-SUPPORTED | Cilt 1.9'daki parçalama yazma endpoint'leri kimlik doğrulama gerektirir; bu endpoint'in de aynı sınıfta olması önerilir. |
| Roles | `ADMIN`, `OPERATOR` | CANDIDATE — OWNER APPROVAL REQUIRED | Cilt 1.9'da `inputs`, `outputs` ve `complete` yazma işlemleri bu rollere verilmiştir. |
| Permission key | `butchering:manage` | CANDIDATE — OWNER APPROVAL REQUIRED | Aynı kaynakta `inputs` ve `outputs` için kullanılan anahtarla tutarlı aday. |
| Audit | Required for successful write | SOURCE-SUPPORTED decision principle; endpoint-specific runtime OPEN | Kritik operasyon kayıtları için onaylı audit ilkesi uygulanmalı. |
| Stock movement | None directly from waste row | SOURCE-SUPPORTED | Fire ayrı kayıt; stok lotu/IN hareketi üretmez. |
| Idempotency | OPEN | OPEN | Genel kural, satış ve endpoint matrisinde işaretlenmiş retry-prone kritik POST'lar için zorunlu. Bu endpoint'in kesin kapsamı Cilt 1.9 ve Cilt 1.3 ile karara bağlanmalı. |

**Gerekli proje sahibi kararı:** Bu endpoint için `ADMIN`, `OPERATOR` ve `butchering:manage` adayını onaylamak veya değiştirmek. Bu rapor rol atamasını kesinleştirmez.

## 4. Endpoint sözleşmesi için kapatma kontrol listesi

Her endpoint aşağıdaki kanıtların tümüyle kapatılmalıdır. Cilt 1.40'taki `SIGNATURE_MATCH_ONLY` durumu yeterli kabul edilmez.

1. Method + path: API sözleşmesi ile yetki matrisi birebir eşleşir.
2. Authentication: anonymous/authenticated durumu açıkça belirtilir.
3. Permission: role + permission key belirli ve aynı sözlükte bulunur.
4. Request DTO: alan adı, tip, required/nullable, sınır ve örnek kaynakta tanımlıdır.
5. Response DTO: başarı gövdesi ve HTTP durum kodu tanımlıdır.
6. Error contract: mümkün hata kodları ve HTTP durumları belirtilmiştir.
7. Workflow: WF-01–WF-10 veya “workflow yok / salt okunur” gerekçesi bağlanmıştır.
8. Transaction: aynı işlemde yazılan tablolar ve rollback sınırı belirlenmiştir.
9. Audit: audit gerekliliği ve transaction ilişkisi belirlenmiştir.
10. Idempotency/retry: zorunlu, opsiyonel veya uygulanmaz kararı kanıtlanmıştır.
11. Acceptance test: benzersiz test kimliği ve beklenen sonuç bağlanmıştır.
12. Runtime proof: OpenAPI, test ve DB metadata ile doğrulanmıştır.

Kaynaklarda bulunmayan DTO alanı, test kimliği veya durum kodu uydurulmaz; `OPEN` bırakılır.

## 5. WF-01–WF-10 eşleştirme durumu

Aşağıdaki eşleştirme, Cilt 1.5 ve Cilt 1.19'daki workflow tanımları ile Cilt 1.3 endpoint imzaları arasında bir navigasyon haritasıdır; bütün geçiş kurallarının kapatıldığı anlamına gelmez.

| WF | Konu | İlgili endpoint/işlem ailesi | Bu ciltteki durum |
|---|---|---|---|
| WF-01 | Fire çıktısı ve nullable alanlar | `POST /api/v1/butchering-orders/{order_id}/outputs`; `POST /api/v1/butchering-orders/{order_id}/waste-records`; butchering complete | Fire ayrı DTO/tablo kararı kaynakta destekli; alan tipleri ve tam DTO/DB kısıtları açık |
| WF-02 | Üretim girdisinin stoktan düşme anı | Production order inputs/complete | Tam geçiş/stock timing parity doğrulanmalı |
| WF-03 | Sevkiyatın tek stok OUT sahibi olması | Shipment dispatch; sales creation | Onaylı temel ilke: dispatch tek `OUT`; satışın kendisi `OUT` üretmez |
| WF-04 | Lot bakiyesi ve hareket defteri atomikliği | Stock movement/balance writes; sales; production/butchering completion | Transaction + row-lock/negative-stock davranışı runtime test edilmedi |
| WF-05 | Recall aktivasyonunun senkronluğu | Recall activate | Senkron/atomik temel karar mevcut; ölçek ve DB runtime doğrulanmadı |
| WF-06 | Recall resolve ile blokajı kaldırmanın ayrılması | Recall resolve; lot release/unblock action if present | Ayrı eylemler ilkesi mevcut; kesin endpoint/izin eşleştirmesi açık |
| WF-07 | Ağırlık farkı ve gerekçe | Butchering outputs/waste/complete | kg kanonik; varsayılan tolerans 0; açıklanmış yetkili fark kuralı kaynaklarla endpoint'e bağlanmalı |
| WF-08 | Tamamlanmış emri ters kayıt/düzeltme | Production/butchering correction/cancel endpoints if defined | Tam ters kayıt API'si ve veri modeli doğrulanmalı |
| WF-09 | Kritik POST idempotency | Receipt, production/butchering complete, sales and other retry-prone commands | Satış kesin; diğer kritik POST kapsamı endpoint matrisiyle belirlenmeli |
| WF-10 | Nihai entity state registry | Production, shipment, recall, butchering, prediction | Bir kısım state destekli; tüm enum ve geçişlerin API/DTO/DB parity'si açık |

## 6. DTO, hata, transaction ve test kanıtı — mevcut sınırlar

- Cilt 1.21 ortak hata zarfı için `error.code`, `error.message`, isteğe bağlı `error.details`, `request_id` alanlarını kaydeder. Bazı alt ayrıntılar hâlâ `PROPOSED` veya `OPEN` olduğundan endpoint düzeyinde tamamı onaylanmış gibi gösterilmemelidir.
- `Idempotency-Key`, satış için zorunludur; aynı key + aynı body önceki sonucu döndürür; aynı key + farklı body `409 Conflict` üretir.
- Genel transaction ilkesi, kritik stok/maliyet/genealogy/state/audit etkilerinin atomik olmasını gerektirir. Her endpoint'in tam tablo listesi ve lock sırası bu ciltte kanıtlanmış değildir.
- Cilt 1.24'te AT-01, AT-02 ve recall uçtan uca senaryosu gibi kabul senaryoları vardır; bunlar kaynakta bulunan test beklentileridir, otomatik testlerin gerçekten yazıldığı veya geçtiği anlamına gelmez.
- Test koşusu yapılmadığından bu cilt hiçbir endpoint'i `PASS` olarak işaretlemez.

## 7. Migration öncesi açık engeller — güncel kayıt

| ID | Engel | Öncelik | Kapanma kanıtı |
|---|---|---|---|
| G-01 | Cilt 1.2 için tam tablo/kolon/PK/FK/index/unique/check envanteri kaynakla doğrulanmadı | BLOCKER | Kanonik ERD + alan/kısıt envanteri; kaynak referansları |
| G-02 | `waste-records` endpoint'inin Cilt 1.9 izin satırı eksik | BLOCKER | Proje sahibi onaylı rol/permission satırı ve 57/57 imza parity |
| G-03 | DTO alanları endpoint bazında tam doğrulanmadı | BLOCKER | Request/response/error alan crosswalk'ı, kaynakta destekli |
| G-04 | WF-01–WF-10 geçiş/yan etki kararlarının tamamı kapatılmadı | BLOCKER | Workflow decision register; her madde onaylı veya açıkça MVP dışı |
| G-05 | Transaction, audit, idempotency kapsamı tüm kritik POST'lar için endpoint bazında kanıtlanmadı | BLOCKER | Endpoint transaction/retry matrisi + testler |
| G-06 | Runtime OpenAPI, ORM metadata, MySQL constraint ve otomatik test doğrulaması yok | BLOCKER | Gerçek çalışma çıktıları ve test raporu |
| G-07 | Yetki matrisi signature parity tek başına rol hücrelerinin doğruluğunu kanıtlamaz | BLOCKER | Her endpoint için rol ve permission review |

## 8. Cilt 1.41 teslim dosyaları

- `manifests/endpoint-permission-gap-v1.41.csv`: eksik endpoint için aday izin satırı ve onay durumu.
- `manifests/workflow-endpoint-status-v1.41.csv`: WF-01–WF-10 ile endpoint ailelerinin eşleştirme durumu.
- `manifests/migration-blockers-v1.41.csv`: migration öncesi engeller ve kapanma kanıtı.
- `manifests/endpoint-contract-evidence-v1.41.json`: kanıt seviyeleri ve doğrulama sınırları.

## 9. Karar ve güvenlik kapısı

**Cilt 1.41 kararı: dokümantasyon analizini ilerletir, migration readiness'i değiştirmez.**

Bu ciltte:
- Alembic migration dosyası oluşturulmadı.
- Veritabanı oluşturulmadı veya değiştirilmedi.
- Rol önerisi kesinleştirilmedi.
- Runtime test çalıştırıldığı iddia edilmedi.

Sonraki adım Cilt 1.42'de tam şema envanterini ve endpoint DTO/constraint eşleştirmesini kaynak kanıtlarıyla genişletmek olabilir. Ancak Cilt 1.2 ile ERD'nin fiziksel alan/kısıt karşılaştırması ve WF-01–WF-10 kararlarının kapatılması için ayrı bir karar kontrolü devam etmelidir.
