# Cilt 1.15 — Revizyon Günlüğü

**Tarih:** 22 Ekim 2026  
**Önceki paket:** v1.14  
**Bu paket:** v1.15  
**Migration:** Oluşturulmadı; DB kurulmadı/değiştirilmedi.

## Bu turda yapılanlar

- Cilt 1.3 rol matrisi ve sevkiyat yazma endpoint'leri `ADMIN`/`SALES` ile eşitlendi; genel stok düzeltme `ADMIN`-only olarak yazıldı.
- Cilt 1.5 sevkiyat durum sözlüğü, ERD'deki `SHIPPED` enumuyla eşitlendi. MVP'de teslimat kanıtı olmadığı için `DELIVERED` çıkarıldı; `DISPATCHED` yalnızca komut adıdır.
- Cilt 1.8 token ve logout metnindeki eski “karar bekliyor” ifadeleri onaylı MVP sözleşmesine çevrildi.
- Cilt 1.9 izin/health satırları ve karar durumu güncellendi.
- Cilt 1.4 başarılı yanıt korelasyon kimliği ve logout test gereksinimi güncellendi.
- Cilt 1.7 migration öncesi kontrol listesine registry karşılaştırması eklendi.
- Cilt 1.15 permission, enum, error, token/health, side-effect ve schema-to-DTO kontrol registry'lerini tek yerde toplar.

## Bu turda yapılmayanlar

- Tüm ERD kolonları için tamamlanmış nullable envanteri çıkarılmadı.
- Gerçek OpenAPI şeması üretilmedi; ORM metadata diff'i veya DB şema diff'i çalıştırılmadı.
- Migration dosyası üretilmedi; MySQL kurulmadı veya değiştirilmedi.

## Açık blokajlar

1. Cilt 1.2 tüm kolonlarının DTO ve nullable semantiğiyle satır satır eşleştirilmesi.
2. P1 hata kodlarının her endpoint için kesin bağlanması ve test ID'leri.
3. Recall lot unblock endpoint/payload/izin/idempotency davranışının normatifleştirilmesi.
4. Android Bearer token ile web token taşıma/CSRF/CORS ayrımının uygulama düzeyinde kesinleştirilmesi.
5. Her kritik POST için idempotency veya deterministik state-conflict politikasının endpoint bazında tamamlanması.

Bu blokajlar kapanmadan ve kullanıcıdan ayrı açık onay alınmadan migration üretimine geçilmez.
