# Cilt 1.17 — Revizyon Günlüğü

**Önceki paket:** v1.16  
**Bu paket:** v1.17  
**Migration:** Oluşturulmadı; veritabanı kurulmadı/değiştirilmedi.

## Kullanıcı kararları

- Fire ayrı `butchering_waste_records` tablosunda tutulacak.
- Son tüketim tarihi, uygulanabilir ürün/lotlarda zorunlu; diğerlerinde `NULL` olabilir.
- Fire ağırlık dengesine katılacak; fire maliyeti ile stokta izlenen çıktılara dağıtılan maliyet toplamı giriş maliyetini uzlaştıracak.

## Yapılan dokümantasyon revizyonları

- Cilt 1.2 ERD ve tablo listesine `butchering_waste_records` eklendi; `butchering_outputs` yalnızca `CUT`/stokta izlenen `BYPRODUCT` tutar.
- Cilt 1.3'e ayrı fire endpoint'i ve DTO örneği eklendi.
- Cilt 1.4'te eski nullable alternatifleri normatif olmaktan çıkarıldı.
- Cilt 1.5 iş akışlarında fire ayrı tablo ve maliyet uzlaştırması belirtildi.
- Cilt 1.15 side-effect ve nullable kayıtları güncellendi.
- Cilt 1.16 X-02 kararı kapatıldı; son tüketim tarihi uygulama ölçütü ve `BY_VALUE` fire maliyet formülü açık kaldı.

## Açık kalanlar

1. Son tüketim tarihinin uygulanabilirliğini belirleyen iş kuralı/alanı.
2. `BY_VALUE` altında fireye maliyet payı tahsisinin kesin formülü.
3. Fire `reason_code` sözlüğü.
4. Çoklu girdi lotu ve ağırlık birimi dönüşümü testleri.
5. OpenAPI ve ORM metadata/schema diff'i.

Bu açıklar netleşmeden migration üretimine geçilmez; ayrıca kullanıcıdan açık migration onayı gerekir.
