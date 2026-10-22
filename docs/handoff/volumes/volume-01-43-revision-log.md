# Cilt 1.43 Revizyon Günlüğü

**Tarih:** 22 Ekim 2026

## Girdi
- Cilt 1.2 ERD ve veri şeması
- Cilt 1.42 şema envanteri ve açık gap ledger
- Cilt 1.3 API sözleşmeleri
- Cilt 1.5 workflow/state machine
- Cilt 1.9 endpoint permission matrisi
- Cilt 1.21 error/idempotency registry

## Değişiklikler
1. Cilt 1.2 içindeki Markdown tablo blokları satır bazında manifest edildi.
2. Başlık ve satır içi şema ifadelerinden tablo adı adayları çıkarıldı.
3. PK/FK/UNIQUE/CHECK/INDEX/DEFAULT metinsel adayları kaynak satırlarıyla kaydedildi.
4. Ayrıştırma ölçümleri ile gerçek fiziksel şema kanıtı birbirinden ayrıldı.

## Bilinçli olarak yapılmayanlar
- Markdown ayrıştırmasından DDL üretilmedi.
- Aday alanlar doğrulanmış fiziksel kolon olarak işaretlenmedi.
- SQLAlchemy veya MySQL runtime doğrulaması yapılmadı.
- Alembic migration oluşturulmadı; veritabanı değiştirilmedi.

## Sonuç
Cilt 1.43, şema doğrulama işini daha denetlenebilir hâle getirir. Migration readiness `NOT READY` kalır.
