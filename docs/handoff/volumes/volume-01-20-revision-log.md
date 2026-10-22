# Cilt 1.20 — Revizyon Günlüğü

**Tarih:** 22 Ekim 2026

## Revizyon 1.20.0

- Cilt 1.8 ve 1.9'daki authentication, token, role/permission ve health kararları uzlaştırma amacıyla bir araya getirildi.
- Access token 30 dakika, refresh token yok ve logout'un server-side revoke yapmadığı mevcut onaylar korundu.
- Cilt 1.9 revizyon 1.11'de kaydedilen stok düzeltme, sevkiyat ve AI prediction rol kararları aynen aktarıldı.
- Liveness/readiness endpoint'leri ve hassas bilgi sızdırmama kuralları net bir tabloda toplandı.
- Android ve web token saklama/taşıma kararları için mevcut kanıtın yetmediği noktalar açık karar olarak işaretlendi.
- Password policy, disabled-user token davranışı, rate limit, audit-failure davranışı ve endpoint permission crosswalk konuları açık bırakıldı; varsayım olarak kesinleştirilmedi.
- Güvenlik kabul testleri ve kodlama LLM'si için talimatlar eklendi.
- Migration veya DB değişikliği yapılmadı.

### Tarihsel kayıt uyarısı (Cilt 1.34)
Bu rapordaki eski token/health/BY_VALUE ifadeleri tarihsel bulgudur; güncel normatif sözleşme olarak kullanılmamalıdır. Cilt 1.31/1.32 onayları ve Cilt 1.34 revizyonları önceliklidir.
