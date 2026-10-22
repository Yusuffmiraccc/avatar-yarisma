# Cilt 1.17 — Fire Tablosu, Son Tüketim Tarihi ve Maliyet Uzlaştırma Kararları

**Tarih:** 22 Ekim 2026  
**Durum:** Kullanıcı kararları işlendi; bazı uygulama ölçütleri migration öncesi açık.  
**Kapsam:** Cilt 1.2 ERD, Cilt 1.3 API, Cilt 1.4 DTO/test, Cilt 1.5 iş akışları ve Cilt 1.15–1.16 kontrol sözlükleri.

## 1. Kullanıcının onayladığı kararlar

### DEC-WASTE-01 — Fire ayrı tabloda tutulur

`WASTE` kayıtları `butchering_outputs` tablosunda tutulmaz. Ayrı `butchering_waste_records` tablosu ve ayrı API DTO'su kullanılır.

- `butchering_outputs` yalnızca stokta izlenen `CUT` ve `BYPRODUCT` satırlarını tutar.
- Bu iki çıktı türünde `product_id` ve `lot_id` zorunludur.
- Fire kaydı satılabilir ürün/çıktı lotu yaratmaz; fire için stok `IN` hareketi oluşturulmaz.
- Fire ağırlığı parçalama ağırlık dengesine katılır.
- Fire kayıtları, parçalama emri ve giriş lotuyla ilişkilendirilir.

### DEC-EXPIRY-01 — Son tüketim tarihi uygulanabilirlik kuralına bağlıdır

Son tüketim tarihi, ürün/lot için uygulanabilir olduğu durumlarda zorunludur; uygulanmadığı durumlarda `NULL` olabilir. Boş string, sıfır tarih veya `UNKNOWN` `NULL` yerine kullanılamaz.

**Açık uygulama ölçütü:** Mevcut belgeler, “uygulanabilir” kararının hangi ürün/lot niteliği, konfigürasyon veya ürün mevzuatı tablosundan okunacağını henüz tanımlamıyor. Yeni DB alanı sessizce eklenmeyecek. Bu ölçüt Cilt 1.2/1.3/1.4 içinde alan ve validation düzeyinde tanımlanmadan migration üretilemez.

### DEC-COST-01 — Fire ağırlığı ve maliyeti uzlaştırılır

Parçalama tamamlanırken şu ağırlık dengesi raporlanır:

`girdi ağırlığı = stokta izlenen kesimler + stokta izlenen yan ürünler + fire ağırlığı + açıklanan/izin verilen fark`

Her terim ortak bir ağırlık birimine çevrilerek karşılaştırılır. Tolerans için yarışma PDF'sinde sayısal değer verilmediğinden sabit tolerans uydurulmaz; tolerans değeri ayrıca kararlaştırılana kadar açıklanması gereken fark raporlanır.

Maliyet uzlaştırması:

`SUM(butchering_outputs.allocated_cost) + SUM(butchering_waste_records.allocated_cost) = butchering_orders.total_purchase_cost`

Tüm parasal alanlar DECIMAL(19,4) kullanır. Yuvarlama farkı deterministik olarak tanımlanan son maliyet payına uygulanır ve test edilir. `allocated_cost` istemciden güvenilir değer olarak kabul edilmez; backend tarafından hesaplanır.

**Açık maliyet alt kararı:** `BY_WEIGHT` yönteminde fire ağırlığının tahsis tabanına dahil edilmesi önerilen varsayılandır. `BY_VALUE` yönteminde fireye ayrı maliyet kaybı payı mı atanacağı, yoksa maliyetin yalnızca değer taşıyan stok çıktılara mı dağıtılacağı henüz kesin formülle tanımlanmamıştır. İki davranış aynı anda uygulanamaz; bu karar netleşmeden migration ve maliyet hesaplama implementasyonu tamamlanmış sayılmaz.

## 2. Önerilen şema

### `butchering_waste_records`

| Alan | Tip | NULL? | Kural |
|---|---|---:|---|
| `id` | `BIGINT UNSIGNED` PK | Hayır | Dahili kimlik |
| `butchering_order_id` | `BIGINT UNSIGNED` FK | Hayır | `butchering_orders.id` |
| `input_lot_id` | `BIGINT UNSIGNED` FK | Hayır | `lots.id`; fire kaynağı |
| `actual_weight` | `DECIMAL(19,6)` | Hayır | `>= 0`; ağırlık dengesine katılır |
| `unit_code` | `VARCHAR(16)` FK | Hayır | `units.code` |
| `reason_code` | `VARCHAR(40)` | Hayır | Kanonik fire nedeni sözlüğü tanımlanmalı |
| `notes` | `VARCHAR(1000)` | Evet | Ek açıklama |
| `allocated_cost` | `DECIMAL(19,4)` | Hayır | Backend hesaplar; `>= 0` |
| `created_at` | `DATETIME(6)` UTC | Hayır | Kayıt zamanı |

Bu alan listesi dokümantasyon kararıdır; gerçek migration değildir. `reason_code` sözlüğü, aynı işlemde birden çok girdi lotu kullanıldığında fire ağırlığının hangi girişe bağlanacağı ve birim dönüşümü doğrulaması implementasyon öncesi testlerde tanımlanmalıdır.

## 3. API sözleşmesi

Önerilen endpoint:

`POST /api/v1/butchering-orders/{order_id}/waste-records`

Örnek request:

```json
{
  "input_lot_id": 9001,
  "actual_weight": "0.350000",
  "unit_code": "KG",
  "reason_code": "TRIMMING_LOSS",
  "notes": null
}
```

Request, `allocated_cost`, ürün kimliği veya çıktı lotu kabul etmez. Maliyet backend hesaplamasının sonucudur. Başarılı parçalama tamamlama transaction'ı, stokta izlenen çıktıların lotlarını/hareketlerini, fire kayıtlarını, maliyet uzlaştırmasını, genealogy ilişkilerini ve audit kaydını atomik biçimde tamamlar. Fire için lot genealogy hedefi veya stok `IN` hareketi yazılmaz.

## 4. Yarışma gereksinimiyle karşılaştırma

Yarışma PDF'si (Görev 2) parçaları, miktarları, fire/yan ürünleri ve ağırlık dengesini ister; maliyetin miktar veya değer ağırlıklı anahtarla ürünlere aktarılmasını ve toplam tahsis tutarının toplam maliyete eşit olmasını ister. Ayrı fire tablosu bu gereksinimle çelişmez; fire ağırlığı dengeye dahil edilir ve fire maliyet payı + stok çıktılarının maliyet payı giriş maliyetini tam olarak uzlaştırır.

Yarışma PDF'si son tüketim tarihinin yalnızca “uygun olduğunda” atanacağını belirtir. Dolayısıyla her lot için zorunlu olması şart koşulmamıştır; kullanıcı tarafından seçilen uygulanabilirlik kuralı kaynakla uyumludur. Ancak uygulanabilirliğin sistemde nasıl belirleneceği PDF tarafından tanımlanmamıştır.

## 5. Güncellenen belgeler

- Cilt 1.2: ERD ve tablo tanımı; `butchering_waste_records` eklendi, `butchering_outputs` sadece stokta izlenen çıktılar olarak ayrıldı.
- Cilt 1.3: Fire için ayrı endpoint/DTO ve stok etkisi kuralı eklendi.
- Cilt 1.4: Eski nullable-alan alternatifleri tarihsel olarak işaretlendi; ayrı tablo kararı normatifleştirildi.
- Cilt 1.5: Ağırlık dengesi ve fire tablosu iş akışına işlendi.
- Cilt 1.15: Kanonik side-effect ve nullable kayıtları güncellendi.
- Cilt 1.16: Fire tablosu blokajı karar verildi olarak güncellendi; son tüketim tarihi ve `BY_VALUE` maliyet alt kararı açık bırakıldı.

## 6. Açık kalan kararlar / migration blokajları

1. “Son tüketim tarihi uygulanabilir” ölçütü hangi ürün/lot kuralıyla belirlenir? Mevcut şemada bu ölçüt için özel alan gösterilmemiştir; yeni alan eklemeden önce ayrıca karar gerekir.
2. `BY_VALUE` maliyet dağıtımında fireye ayrı `allocated_cost` kaybı atanacak mı, yoksa tüm maliyet değer taşıyan stok çıktılara mı dağıtılacak? Tam formül ve örnek test bekleniyor.
3. `reason_code` için kanonik fire nedenleri sözlüğü tamamlanmalı.
4. Girdi lotu ile fire ölçümü birimi farklıysa dönüşüm ve ağırlık denge kuralları test edilmelidir.
5. Gerçek OpenAPI/ORM metadata diff'i henüz çalıştırılmadı.

**Migration dosyaları oluşturulmadı. Veritabanı kurulmadı veya değiştirilmedi. Bu karar belgesi migration üretimi için yetki değildir.**
