# Cilt 1.40 — Alan Kartları ve API–Workflow–Test Eşleştirmesi

**Tarih:** 22 Ekim 2026  
**Durum:** İlk kritik alan kartları ve endpoint crosswalk üretildi; migration readiness: **NOT READY**.  
**Kaynaklar:** Cilt 1.2, 1.3, 1.4, 1.5, 1.9, 1.19, 1.24 ve onaylı karar kayıtları.  
**Sınır:** Bu cilt, aday alanları kaynak kanıtıyla işaretler; kaynakta açıkça bulunmayan SQL ayrıntılarını kesinleştirmez.

## 1. Sonuç

Cilt 1.39'daki aday tablo kayıtlarından hareketle 20 kritik alan kartı üretildi. Bunlar alan düzeyinde kontrol listesi olarak kullanılmalıdır; her birinin tipi veya ilişkisi kesinleşmiş değildir. Mermaid ilişkileri konseptual bağlantıyı destekleyebilir, ancak tek başına fiziksel FK, nullable, index ya da DB constraint kanıtı değildir.

- Alan kartı sayısı: **20**
- API endpoint imzası: **57**
- Yetki matrisi imzası: **56**
- API-only endpoint: **1**
- Permission-only endpoint: **0**
- Migration readiness: **NOT READY**

## 2. Üretilen dosyalar

- `manifests/field-cards-v1.40.csv` — 20 kritik alan kartı, doğrulama durumları ve gerekli kanıt.
- `manifests/field-cards-v1.40.json` — aynı kayıtların makine tarafından okunabilir hali.
- `manifests/endpoint-workflow-dto-test-crosswalk-v1.40.csv` — API imzası başına izin, DTO, workflow, test, transaction/audit ve idempotency kontrol durumları.

## 3. Kritik alan grupları

| Alan grubu | Örnek alanlar | Neden önemli? |
|---|---|---|
| Lot ve expiry | `products.requires_expiry_date`, `lots.expiry_date` | Son kullanma tarihi zorunluluğu ve lot kabul doğrulaması |
| Fire ve maliyet | `butchering_waste_records.reason_code`, `allocated_cost` | Fire gerekçesi, kilo dengesi ve maliyet tahsisi |
| Stok doğruluğu | `inventory_balances.lot_id`, `stock_movements.lot_id` | Defter/bakiye tutarlılığı ve stok hareketinin atomikliği |
| Üretim genealogy | `production_inputs`, `production_outputs` | Hammadde lotundan bitmiş ürün lotuna bağlantı |
| Satış/sevkiyat | `sale_lines.lot_id`, `shipment_lines.lot_id` | Satılan/sevk edilen miktarı lot bazında izleme |
| Recall | `recall_impacts.recall_id`, `shipment_id` | Etkilenen müşteri/sevkiyat miktarı ve bildirim durumu |
| Audit | `audit_events.actor_user_id` | Kritik işlemlerin kim tarafından yapıldığının izlenmesi |

Bu isimlerin bir kısmı gereksinim veya ilişki modelinden aday olarak türetilmiştir. Kesin kolon adı/tipi/nullable/FK doğrulaması yapılmadan migration'da kullanılmamalıdır.

## 4. API–yetki farkı

Statik imza karşılaştırması:
- API sözleşmesi: **57**
- Yetki matrisi: **56**
- API'de olup Cilt 1.9'da yetki satırı olmayan: **1**
- `POST /api/v1/butchering-orders/{order_id}/waste-records`


İmza eşleşmesi, yetki satırının içeriğinin doğru olduğunu kanıtlamaz. CSV'de eşleşen endpoint'ler de `OPEN` durumunda bırakıldı; her endpoint için DTO, workflow, hata, audit/transaction, idempotency ve test doğrulaması yapılmalıdır.

## 5. Migration readiness kararı

**Karar: NOT READY.**

Nedenler:
1. Cilt 1.2'de tam kolon/kısıt envanteri kaynak kanıtıyla tamamlanmış değil.
2. API-only waste-records endpoint'inin Cilt 1.9 yetki satırı eksik.
3. WF-04, WF-06, WF-08, WF-09, WF-10 için kaynakta açık ayrıntılar var.
4. Her endpoint için DTO/test/transaction/idempotency birebir kanıtı henüz yok.
5. Gerçek ORM metadata, üretilmiş OpenAPI veya MySQL runtime doğrulaması yapılmadı.

## 6. Sonraki cilt

Cilt 1.41, endpoint bazlı crosswalk'teki eksik alanları kaynağa dönerek kapatmaya odaklanacak. Öncelik:
1. `POST /api/v1/butchering-orders/{{order_id}}/waste-records` için Cilt 1.9 izin satırı önerisi (proje sahibi onayı gerektiren rol kararı açık işaretlenecek).
2. Cilt 1.3/1.4 request/response/error sözleşmelerinin endpoint başına listelenmesi.
3. WF-01–WF-10 geçiş ve yan etkilerinin endpointlerle eşlenmesi.
4. Her testin belirli bir kabul kriterine bağlanması.

**Güvenlik kapısı:** Bu ciltte migration oluşturulmadı ve DB değiştirilmedi. Dokümantasyon onayı migration/DB onayı değildir; bunun için ayrıca açık izin gereklidir.
