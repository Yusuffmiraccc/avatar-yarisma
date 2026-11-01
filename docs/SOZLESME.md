# AVATAR — Tek Geçerli Sözleşme

Bu belge tasarım kararlarının tek kaynağıdır; kod ve diğer belgeler arasında çelişki olursa **bu belge** geçerlidir.

Kaynak: `AVATAR_Assessment.pdf`. Tarih: 2026-10-22. Teslim: 2026-11-01 23:59.

## 1. Teknoloji (kesin)

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, PyMySQL, MySQL 8.4. Go kullanılmaz.
- ML: scikit-learn, pandas; backend içinde `app/ml` modülü.
- Android: Kotlin, Jetpack Compose, Room (SQLite), Retrofit. Online-first (ADR-001).
- Web: React, TypeScript, Vite.
- İstemciler MySQL'e doğrudan bağlanmaz.

## 2. Çelişki çözümleri

| Konu | Geçerli karar |
|---|---|
| Access token | 15 dk (`expires_in: 900`) |
| Refresh token | 7 gün, rotation, hash saklanır, reuse'da aile iptali, logout revoke eder. `POST /api/v1/auth/refresh` eklenir. |
| Health | `/health/live` ve `/health/ready`, kökte (`/api/v1` dışı), anonim |
| Stok OUT sahibi | Yalnız dispatch/sevkiyat. Satış ticari kayıttır. |
| Android satışı | Satış onaylanınca backend aynı transaction'da satış + dispatch oluşturur. Stok düşer, müşteri bağı recall'da görünür. (Varsayılan karar; değiştirilebilir.) |
| Fire | Ayrı `butchering_waste_records`. Stok `IN` üretmez. |
| BY_WEIGHT | Demo varsayılanı. Yuvarlama artığı son tahsis satırına. |
| BY_VALUE | Ürün değer ağırlığı (`product_prices`) ile dağıtım yapılır. Fire değerlemesi onaylı değilse tamamlama reddedilir (fail-closed). |
| Ağırlık toleransı | Konfigürasyon, demo `0.000 kg`. Aşım: yetkili variance kaydı (gerekçe + audit) olmadan tamamlanamaz. |
| Recall durumu | `DRAFT`, `ACTIVE`, `RESOLVED`, `CANCELLED` |
| RESOLVED | Lot blokajını kaldırmaz. Ayrı `lots:unblock` izni ve audit gerekir. |
| Hata kodları | 400 `VALIDATION_ERROR`, 401 `UNAUTHENTICATED`, 403 `FORBIDDEN`, 404 `NOT_FOUND`, 409 `CONFLICT` / `IDEMPOTENCY_KEY_REUSED` / `INSUFFICIENT_STOCK` / `LOT_BLOCKED` / `INVALID_STATE_TRANSITION`, 500 `INTERNAL_ERROR`. Pydantic 422 yanıtı bu zarfa çevrilir ve 400 döner. |
| Hata zarfı | `{"error": {"code", "message", "details"}, "request_id"}` (`request_id` kökte) |
| Fire izni | `ADMIN`/`OPERATOR` + `butchering:manage` |
| Yuvarlama | Para 4 basamak `ROUND_HALF_UP`, gösterim 2 basamak. EKP = 1543.5000 / 85 = 18.1588, gösterim 18.16. |
| Idempotency | Satış ve dispatch'te `Idempotency-Key` zorunlu. Diğer kritik POST'larda aynı tablo üzerinden isteğe bağlı. |
| PK tipi | `BIGINT UNSIGNED` (FK'ler aynı tip) |

## 3. Eklenen kapsam (dokümanda eksikti)

1. `refresh_sessions` tablosu ve `/auth/refresh`.
2. `weight_variance_records` (tolerans aşımı gerekçesi, onaylayan, audit).
3. `butchering_recipe_lines` (PDF: önceden tanımlı reçete ve dağıtım anahtarı).
4. Lot maliyeti: `lots.unit_cost` ve üretim çıktısı lotuna EKP yazılır.
5. `production_service_costs`: `quantity`, `unit_price`, `amount`.
6. `POST /api/v1/lots/{id}/unblock` (`lots:unblock`).
7. `/api/v1/reports/*`: EKP/VKP/marj, parçalama uzlaştırma, recall.
8. `ml_predictions`: çok değerli çıktı için JSON alanı, baseline ve model karşılaştırması.
9. Kural tabanlı anomali uyarıları (fire, maliyet artışı, düşük verim). İsteğe bağlı fatura okuma sonraya bırakılır.
10. Üretim/parçalama `start` ve `cancel` geçişleri.
11. Depo transferi, iade ve yeniden işleme: hareket tipleri kullanılır, tek depo + lokasyon alanı ile.

## 4. Kapsam dışı

- Çevrimdışı satış kuyruğu.
- Canlı sunucu. Demo yerelde Docker Compose ile.
- Fatura/irsaliye okuma (zaman kalırsa).

## 5. PDF doğrulamaları (testle kanıtlanacak)

- 970 + 48 + 58 + 467,50 = 1.543,50; ÷ 85 = 18,1588 (gösterim 18,16).
- Kuzu örneği: 25 kg × 11,50 = 287,50 ≠ 351,00; parça toplamı 22 kg ≠ 25 kg. Sistem uyuşmazlığı gösterir, neden uydurmaz.
- ET-2026-001 → URT-2026-045 → SUC-2026-045 (85); Market A/B/C = 30/25/30. İleri izleme 3 marketi bulur; recall lotu bloke eder, satışı engeller.

## 6. Güvenlik sınırı

Migration yalnızca yerel/izole test MySQL'inde çalıştırılır. Gerçek veri uydurulmaz; tüm seed verisi `DEMO` olarak işaretlenir.
