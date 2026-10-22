# Cilt 1.14 — WF-03 Kararının Normatif Uygulanması

**Tarih:** 22 Ekim 2026  
**Durum:** Kullanıcı kararı uygulandı; dokümantasyon revizyonu.  
**Migration:** Oluşturulmadı. Veritabanı oluşturulmadı/değiştirilmedi.

## Onaylanan karar

> Dispatch tek OUT hareketinin sahibidir.

## Normatif kurallar

1. `POST /api/v1/shipments/{shipment_id}/dispatch`, fiziksel stok çıkışını kaydeden tek komuttur.
2. Dispatch her sevkiyat satırı için `OUT/SHIPMENT` hareketi oluşturur ve `inventory_balances` bakiyesini aynı transaction içinde azaltır.
3. Satış oluşturma/tamamlama yalnızca ticari kaydı yazar; stok hareketi üretmez ve stok bakiyesini azaltmaz.
4. Aynı fiziksel miktar için ikinci `OUT` yasaktır.
5. Aynı dispatch komutunun tekrarı ikinci hareket yaratmaz. Transaction hatasında bütün etkiler birlikte rollback edilir.
6. Fiziksel stok çıkışı varsa ilgili dispatch kaydı bulunmalıdır. Satış kaydı tek başına fiziksel stok çıkışının kanıtı değildir.
7. Recall/izlenebilirlik raporları stok hareketi için dispatch kaydını; ticari bağlam için varsa ilgili satış kaydını ayrı ayrı gösterir. İkinci kademe market satışı kaydı yoksa varsayılmaz.

## Uygulama ayrıntısı

- `stock_movements.movement_type` sözlüğünden `SALE` çıkarıldı; satış kaydı stok ledger hareket türü değildir.
- Satış endpoint’inin backend kontrol listesinden yeterli stok ve stok bakiyesi kilitleme kontrolleri çıkarıldı; bu kontroller dispatch transaction’ında uygulanır. Lot/ürün eşleşmesi, ticari alanlar, idempotency ve aktif blokaj/recall iş kuralı kontrolleri korunur.

## Güncellenen belgeler

- Cilt 1.2: ERD/veri şeması, sales/shipment tanımları ve transaction sınırları.
- Cilt 1.3: Rol matrisi ve satış/dispatch endpoint normatif davranışı.
- Cilt 1.4: Contract-test beklentileri.
- Cilt 1.5: WF-03 ve 85 paket demo akışı.
- Cilt 1.6: Backend transaction etkileri ve faz planı.
- Cilt 1.7: Migration öncesi kontrol maddesi.
- Cilt 1.9: Dispatch endpoint izin tablosundaki stok yan etkisi açıklaması.
- Cilt 1.10 ve 1.13: CC-03/P0-03 durumu kapatıldı olarak işaretlendi.
- DEC-001: Karar 14 eklendi.

## Zorunlu testler

- Dispatch öncesi stok miktarı `Q`; dispatch sonrası `Q - shipment_quantity` olmalı.
- Dispatch başına tam olarak bir `OUT/SHIPMENT` hareketi oluşmalı.
- Aynı dispatch tekrar çağrıldığında ikinci `OUT` oluşmamalı.
- Satış kaydı oluşturmak stok miktarını değiştirmemeli ve `OUT` hareketi oluşturmamalı.
- Market A/B/C dispatch miktarları 30 + 25 + 30 = 85 paket ise toplam fiziksel stok çıkışı tam 85 paket olmalı.
- Transaction içindeki hata, hareket/bakiye/sevkiyat durumu/audit/idempotency etkilerini birlikte rollback etmeli.
- Recall raporu sevkiyat miktarlarını kaydedilmiş dispatch satırlarından üretmeli; kayıtlı olmayan market alt satışlarını uydurmamalı.

## Sınır

Bu karar yalnızca dokümantasyon sözleşmesini günceller. Alembic migration dosyası veya gerçek DB değişikliği için yetki vermez. Migration öncesinde ERD/kolon/constraint/DTO/API/permission/enum/error-code çapraz kontrolü tamamlanmalı ve kullanıcıdan ayrıca açık onay alınmalıdır.
