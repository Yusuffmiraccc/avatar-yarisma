# Cilt 1.34 Revizyon Günlüğü

**Tarih:** 22 Ekim 2026

## Tamamlanan doküman revizyonları
- API sözleşmesinde access 15 dakika / refresh 7 gün + rotation kuralı işlendi.
- Health endpoint yolları `/health/live` ve `/health/ready` olarak değiştirildi; eski `/api/v1/health/*` tanımı kaldırıldı veya normatif öncelik notuyla değiştirildi.
- DTO/contract test belgesinde refresh lifecycle ve health davranış testleri güncellendi.
- ERD belgesine ürün expiry policy, waste reason codes, source lot, weight units/tolerance, BY_WEIGHT/BY_VALUE allocation ve rounding kuralları eklendi.
- Cilt 1.23 karar durumları toplu onaya göre güncellendi.
- Auth/health/deployment ile ilgili dört belgede Cilt 1.34 normatif override eklendi.

## Açık kalanlar
- Fiziksel ERD/ORM alan varlığı, OpenAPI şema çıktısı ve DB constraints doğrulanmadı.
- Endpoint permission coverage, idempotency endpoint coverage ve WF-01–WF-10 eşleşmesi tamamlanmadı.
- Runtime test çalıştırılmadı.
- Cilt 1 kapanmadı.

## Güvenlik kapısı
- Migration oluşturulmadı veya çalıştırılmadı.
- Veritabanı oluşturulmadı veya değiştirilmedi.
