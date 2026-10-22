# AVATAR — Bilinen Açık Konular ve Güvenli Uygulama Politikası

**Amaç:** Kaynak dokümanlarda açık kalan veya eski revizyonlarla çelişen konuları kodlama LLM'inin sessizce uydurmasını önlemek. Bu liste, tüm kararların kesinleştiği iddiası değildir.

## Karar önceliği

`BACKEND_DATABASE_ARCHITECTURE_CLOSURE.md` v1.45, aynı konudaki eski revizyon notlarından daha günceldir. Özellikle migration konusu için: migration dosyaları hazırlanabilir ve yalnızca izole test DB'de çalıştırılabilir; gerçek/production DB'ye bağlanmak veya veri silmek yasaktır. Cilt 1.25'teki daha eski “hiç migration oluşturma/ayrıca onay bekle” notu bu güncel yetki çerçevesiyle okunmalıdır.

## Konular ve uygulama davranışı

| Konu | Durum | LLM'in uygulaması gereken davranış |
|---|---|---|
| ERD–ORM–constraint–DTO parity | Tamamlanması gerekiyor | İlk fazda parity matrisi üret; her tablo/kolon/constraint'i gerçek ORM metadata ve OpenAPI ile doğrula. Kaynakta olmayan alanı sessizce icat etme. |
| Waste endpoint permission | Eski manifestte gap var; v1.45 kapanışında karar var | `POST /api/v1/butchering-orders/{order_id}/waste-records`: `ADMIN`/`OPERATOR` + `butchering:manage`. İzin manifesti ve testleri buna göre güncelle. |
| Weight tolerance | Evrensel kaynak değeri yok | Konfigüre et; demo varsayılanı `0.000 kg`; fark sessizce normalize edilmez, gerekçe ve audit gerektirir. Bunun proje varsayımı olduğunu belgele. |
| BY_VALUE fire allocation | Değerleme tabanı tam tanımlı değil | Güvenilir ve onaylı fire değerlemesi yoksa tamamlamayı reddet (fail-closed); 0 veya başka fallback uydurma. `BY_WEIGHT` demo yolu kullanılabilir. |
| Expiry date | Kural kapanış belgesinde var | `products.requires_expiry_date` default `false`; true olduğunda `lots.expiry_date` zorunlu. |
| Waste source | Çoklu input lot karmaşıklığı | Her waste row tek input/source lota bağlanır; farklı kaynak lotlar için ayrı satırlar. |
| Rounding residual | Kapanış kararı var | Decimal kullan; maliyet dağıtımındaki son yuvarlama artığını deterministik son tahsis satırına ata ve toplamı assert et. |
| Correction/reversal | Uçtan uca sözleşme parity'si test edilmeli | Kaynak kayıt + reason + permission + audit + ters stok hareketleri aynı transaction; hard-delete yok. |
| Recall/stock race | Kritik entegrasyon riski | Recall activation ve stock exit aynı lot/balance/block kayıtlarını tutarlı kilit sırasıyla almalı; concurrency test yaz. |
| Audit failure | Eski sicilde açık | Kritik transaction'da audit yazılamazsa işlem de rollback olsun (fail-closed); failure injection testi ekle. |
| Disabled user/token | Eski sicilde açık | Her authenticated request'te kullanıcının aktifliğini kontrol et veya eşdeğer, kısa ve testli invalidation mekanizması uygula; tercih edilen çözüm aktiflik kontrolüdür. |
| Access/refresh/logout | v1.45 closure kararı var | Access 15 min, refresh 7 days, rotation; refresh token hash sakla; logout revoke eder; secret/token loglama. |
| Lot expiry / units / conversion | Kaynak alan detaylarıyla cross-check gerekir | Cilt 1.2 ve 1.23 ile doğrula; dönüşümleri açık ve testli yap, implicit unit conversion yok. |
| Status enums | Eski WF numaraları çakışıyor | WF-08–WF-10 gibi eski numaralara kod sabiti olarak dayanma; konu adları ve güncel state registry kullan. |
| ML lifecycle | Tam parity testleri gerekli | Model/version, input snapshot/summary, prediction, actual, metric, `SUCCEEDED`/`FAILED`; ML hatası operasyonu engellemez. |
| Second-tier distribution | Kaynakta her zaman bulunmayabilir | Yalnızca kaydedilmiş sevkiyat/dağıtım bağlantıları raporla; eksik zinciri varsayma. |
| Source arithmetic conflict | Demo kaynağında tutarsızlık var | 25 kg × €11.50 = €287.50; kaynak toplamı €351 ise uyuşmazlığı göster. Sebep uydurma veya rakamı sessizce düzeltme. |

## Öncelik etiketleri

- **P0:** Stok, maliyet, yetkilendirme, recall, transaction veya veri bütünlüğü hatası yaratabilecek konu.
- **P1:** API sözleşmesi, kullanılabilirlik veya raporlama doğruluğu.
- **P2:** İyileştirme/ek ergonomi.

## Uygulama LLM'inin kayıt tutma yükümlülüğü

Her yeni fark için bu dosyaya şu alanları ekle: `ID`, açıklama, etkilenen modüller, seçilen çözüm, çözümün dayanağı, test kanıtı, kalan risk. Kapalı maddeleri yalnızca test kanıtı varsa `CLOSED` yap. Kullanıcıya her küçük kararı sormak yerine güvenli teknik default kullan; gerçek/production sistemini etkileyen yıkıcı işlem yapma.
