# Cilt 1.36 — Revizyon Günlüğü

- Tarih: 22 Ekim 2026
- Kaynak: Cilt 1.35 statik denetimi ve mevcut Cilt 1.3/Cilt 1.9 Markdown sözleşmeleri.
- Yeni rapor: `volume-01-36-static-diff-and-closure-gates.md`
- Yeni makine okunabilir manifest: `manifests/endpoint-permission-manifest-v1.36.json`
- Yeni imza CSV'si: `manifests/endpoint-signatures-v1.36.csv`
- Kesin statik bulgu: API sözleşmesinde 57, yetki belgesinde 56 benzersiz method/path imzası; ortak 56; API-only 1; permission-only 0.
- API-only imza(lar): POST /api/v1/butchering-orders/{order_id}/waste-records.
- Migration/DB değişikliği yapılmadı.
- Bu cilt, açık workflow ve ERD ayrıntılarını uydurarak kapatmaz; kapanış için gereken kanıtı listeler.
