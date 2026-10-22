# Cilt 1.23 — Revizyon Günlüğü

- **Tarih:** 22 Ekim 2026
- **Sürüm:** 1.1
- **Durum:** Kısmi karar onayı; kalan sorular açık

## Kullanıcı onayı
- `BY_WEIGHT`: fire ağırlığı toplam ağırlık paydasına dahil edilir ve fireye oransal maliyet tahsis edilir. Onaylandı.
- Genel fire ilkesi: fire ayrı kayıtta maliyet payı taşıyabilir, ancak bu tutar satılabilir stok çıktısının maliyeti sayılmaz. Onaylandı.
- `BY_VALUE` için fire payının sayısal formülü ve değer anahtarının kaynağı **henüz onaylanmadı**. Bu konularda kodlama LLM'si varsayım yapmamalıdır.

## Güncellenen bölümler
- Karar kayıtları ve Q-123 karar tablosu güncellendi.
- `BY_VALUE` bölümünden, kullanıcı onayıyla çelişen “fire maliyeti sıfır” önerisi çıkarıldı.
- `BY_VALUE` için hesaplama kuralı açık/bloke olarak işaretlendi.
- Kabul testleri kısmi onayla uyumlu hale getirildi.

## Hâlâ açık kararlar
- Son tüketim tarihi politikası (`requires_expiry_date`).
- `BY_VALUE` değer anahtarının kaynağı ve fire maliyetinin hesaplanma formülü.
- Ağırlık toleransı ve tolerans dışı fark istisnası.
- Desteklenecek birimler, fire `reason_code` listesi, çoklu lot fire kaydı ve yuvarlama kuralı.

## Güvenlik sınırı
- Kod veya migration üretilmedi. Veritabanı oluşturulmadı/değiştirilmedi.
- Onaylanan kararlar Cilt 1.2, 1.3, 1.4, 1.5, 1.15, 1.16 ve 1.22 ile nihai çapraz kontrol sırasında senkronize edilmelidir.
