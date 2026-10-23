# AVATAR Web Yönetim ve Raporlama Paneli — Yol Haritası

Bu belge `web/` klasöründe yapılacak React uygulamasının kapsamını, mimarisini, ekranlarını, iş sırasını ve kabul ölçütlerini tanımlar.
Henüz kod yoktur; bu bir planlama belgesidir. Backend hazırdır ve sözleşmesi `contract/openapi.json` dosyasındadır.

- Gereksinim kaynağı: `AVATAR_Assessment.pdf` (Bölüm 6: "React veya uygun modern web teknolojisi"; en az alış, üretim, parçalama, lot hareketleri, satış ve geri çağırma raporları gösterilmeli).
- Kararlar: `docs/SOZLESME.md`. API özeti: `docs/API.md`. Şema ayrıntısı: `contract/openapi.json`, çalışan backend'de `/api/v1/docs`.
- Teslim son günü: 2026-11-01 23:59.

## 1. Amaç ve kapsam

Web paneli yönetici, operatör, izlenebilirlik yöneticisi ve görüntüleyici rollerinin kullandığı ofis uygulamasıdır. Satış yapan saha uygulaması Android'dir (bkz. `android/README.md`).

Panelin ispatlaması gereken şeyler (PDF'in değerlendirme odağı):

1. Maliyet doğru hesaplanıyor ve açıklanabilir (EKP, VKP, brüt kâr, marj; 1.543,50 € / 85 paket = 18,16 €).
2. Lot ilişkileri eksiksiz görülebiliyor (ileri/geri izleme, çoktan çoğa miktarlı ilişkiler).
3. Stok hareketleri güvenilir ve geçmişe dönük incelenebilir.
4. Geri çağırma uçtan uca çalışıyor: ET-2026-001 sorunlu lotundan etkilenen marketlerin (A/B/C: 30/25/30 paket) bulunması.
5. Yapay zeka katkısı ölçülebilir: tahmin, gerçek sonuç ve sapma birlikte gösteriliyor.

Kapsam dışı (bilerek): mobil satış akışı, kullanıcı kayıt/parola unuttum e-postası, gerçek zamanlı bildirim (WebSocket), çok dilli arayüz (yalnızca Türkçe), ödeme/fatura kesme.

## 2. Teknik kararlar

| Konu | Karar | Gerekçe |
|---|---|---|
| Çatı | Vite + React 18 + TypeScript (strict) | Hızlı kurulum, tip güvenliği. Next.js gereksiz (SSR yok). |
| Yönlendirme | React Router 6 | Rol bazlı korumalı rotalar. |
| Sunucu durumu | TanStack Query | Önbellek, yeniden deneme, sayfalama, geçersiz kılma. Redux gerekmez. |
| API tipleri | `openapi-typescript` ile `contract/openapi.json` dosyasından üretim; `openapi-fetch` istemcisi | Sözleşme ile tip uyumu otomatik; elle DTO yazılmaz. |
| Arayüz | Tailwind CSS + küçük bir ortak bileşen seti (Tablo, Form alanı, Rozet, Modal) | Ağır bir bileşen kütüphanesi olmadan hızlı ve tutarlı. |
| Grafik | Recharts (en fazla 3–4 grafik) | Yalnızca pano ve AI sapma grafiği. |
| Formlar | React Hook Form + Zod | Doğrulama mesajlarını backend hata kodlarıyla birleştirmek kolay. |
| Para/miktar | `decimal.js` | API para ve miktarı **string** döner; JavaScript `number` kullanılmaz. |
| Test | Vitest + Testing Library; tek bir uçtan uca Playwright senaryosu | Bkz. bölüm 9. |

Kısayol notu: erişim token'ı bellekte, yenileme token'ı `sessionStorage` içinde tutulur. HttpOnly çerez backend değişikliği ister; yarışma kapsamında kabul edilen bir sınırlamadır ve README'de belirtilecektir.

### Klasör yapısı (hedef)

```
web/
  src/
    api/            openapi-fetch istemcisi, üretilmiş tipler (schema.d.ts), hata çözümleyici
    auth/           oturum, token yenileme, RequireRole, izin yardımcıları
    components/     Tablo, Sayfalama, Rozet, Modal, ParaHücresi, MiktarHücresi, Boş/Yükleniyor/Hata
    features/       her modül kendi klasöründe: catalog, lots, purchases, production,
                    butchering, inventory, sales, traceability, recalls, reports, ai, alerts, audit, users
    routes.tsx
    main.tsx
  tests/
  e2e/
```

## 3. Backend ile çalışma kuralları (herkesin bilmesi gerekenler)

Bu kurallar hem web hem Android için geçerlidir; ihlali hata veya yanlış sayı üretir.

1. **Taban adres:** `/api/v1`. Geliştirmede backend `http://127.0.0.1:8000`. CORS izinli kaynaklar `CORS_ORIGINS` ayarındadır (varsayılan `http://localhost:5173,http://localhost:3000`).
2. **Kimlik doğrulama:** `POST /auth/login` → `{access_token, refresh_token, expires_in, user}`. Erişim token'ı 15 dakika, yenileme token'ı 7 gün geçerlidir. Her istek `Authorization: Bearer ...` taşır.
   - `401` gelince **bir kez** `POST /auth/refresh` denenir ve istek tekrarlanır. Yenileme token'ı her kullanımda **döner** (rotation); eski token'ı yeniden göndermek tüm oturum ailesini iptal eder. Aynı yenileme isteğinin 10 saniye içinde tekrarı güvenlidir (ağ kopması durumu).
   - Eşzamanlı birden çok `401` tek bir yenileme isteğine indirgenmelidir (tek uçuşlu kilit); aksi halde oturum düşer.
   - Yenileme de başarısızsa oturum kapatılır ve giriş sayfasına yönlendirilir.
3. **Hata zarfı:** `{ "error": {"code", "message", "details"}, "request_id": "..." }`. Doğrulama hatası `400` (`VALIDATION_ERROR`). Kullanıcıya `message` gösterilir, `request_id` küçük puntoyla eklenir (destek için).
4. **Para ve miktar JSON string'tir** (`"18.1588"`). `float` ile hesap yapılmaz; gösterimde `decimal.js` kullanılır. Gösterim kuralı: EKP/VKP 2 hane (`18.16`), hesap 4 hane, miktar 3 hane (backend tam hassasiyeti `*_display` alanlarıyla ayrıca verir).
5. **Zaman:** UTC ISO-8601, sonunda `Z`. Kullanıcıya `Europe/Istanbul` saatiyle gösterilir.
6. **Sayfalama:** `?page=1&page_size=50` (en çok 100) → `{items, page, page_size, total}`.
7. **Idempotency-Key:** `POST /sales` ve `POST /shipments/{id}/dispatch` için **zorunlu** başlık. Her kullanıcı eylemi için bir UUID üretilir; ağ hatasında **aynı anahtarla** tekrar denenir. Aynı anahtar + farklı gövde `409 IDEMPOTENCY_KEY_REUSED` döner.
8. **Maliyet alanları rol bağımlıdır.** `costs:read` yetkisi olmayan rollerde (SALES, VIEWER, TRACEABILITY_MANAGER) `unit_cost`, `ekp`, `total_cost`, `margin_percent` vb. yanıtta **hiç bulunmaz**. Tüm maliyet alanları TypeScript'te opsiyonel (`?`) ele alınmalı; yoksa sütun/kart gizlenir (boş veya `0` gösterilmez).
9. **İzin → arayüz:** Menü ve düğmeler `GET /auth/me` ile gelen izinlere göre gösterilir (örn. `production:manage`). Bu yalnızca kolaylıktır; yetki denetimi sunucudadır ve `403 FORBIDDEN` her zaman ele alınmalıdır.
10. **Hız sınırı:** Giriş denemeleri sınırlıdır (`429 RATE_LIMITED`). Arayüz bekleme süresini göstermelidir.
11. **Tarih filtresi:** `updated_after` gibi parametrelerde saat dilimli değer gönderilebilir; sunucu UTC'ye çevirir.

Roller (ayrıntı `docs/API.md`): `ADMIN`, `OPERATOR`, `SALES`, `TRACEABILITY_MANAGER`, `VIEWER`. Demo hesapları `seed_demo` ile gelir (`admin@avatar.demo`, `operator@…`, `sales@…`, `trace@…`, `viewer@…`; parola `backend/README.md` içinde).

## 4. Ekranlar ve backend eşlemesi

Öncelik: **P0** = PDF'in zorunlu tuttuğu, demo için şart; **P1** = tamamlayıcı; **P2** = zaman kalırsa.

### 4.1 Giriş ve iskelet (P0)
- Giriş formu, hata/hız sınırı mesajları, oturum kalıcılığı, çıkış (`POST /auth/logout`).
- Rol bazlı menü, korumalı rotalar, 403/404/500 sayfaları, genel yükleniyor/boş/hata bileşenleri.

### 4.2 Pano (P0) — `GET /reports/dashboard`
- Kartlar: aktif recall sayısı, bloke lot sayısı, tamamlanan üretim emri, stok değeri (`stock_value`, yalnızca `costs:read` varsa), açık uyarı sayısı.
- Son uyarılar listesi (`GET /alerts`), son recall'lar.

### 4.3 Katalog (P1)
- Ürünler (`/products`, fiyatlar `/products/{id}/prices`), tedarikçiler, müşteriler/marketler, birimler (`/units`, salt okunur).
- Form kuralları: ürün birimi sonradan lot birimiyle eşleşmek zorunda; `requires_expiry_date` true ise lot kabulünde son tüketim tarihi zorunlu.

### 4.4 Alış / hammadde kabulü (P0) — PDF "alış raporu"
- **Lot kabulü** formu (`POST /lots/receipts`): tedarikçi, lot no, tarih, miktar, birim, birim maliyet, son tüketim tarihi.
- **Alış raporu:** kabul edilen lotların listesi (`GET /lots` + `inventory/movements?movement_type=RECEIPT`), tedarikçiye ve tarihe göre filtre.
- **Fatura/irsaliye okuma** (isteğe bağlı yapay zeka, P1):
  1. Metin yapıştır veya dosya yükle (`POST /documents/extract`, `/documents/extract-file`, en çok 5 MB).
  2. Çıkarılan satırlar **öneri** olarak gösterilir; ürün eşleşmeyenler, `TOTAL_MISMATCH` ve `SUPPLIER_UNMATCHED` uyarıları vurgulanır.
  3. Kullanıcı düzeltip onaylar (`POST /documents/{id}/approve`) veya reddeder. Onay atomiktir (ya hepsi ya hiçbiri).
  - Kural: öneri **asla** otomatik kaydedilmez.

### 4.5 Lotlar ve stok hareketleri (P0) — PDF "lot hareketleri raporu"
- Lot listesi: filtre (ürün, durum, bloke), lot detayı (`GET /lots/{id}`, `/lots/by-code/{kod}`): eldeki miktar, birim maliyet (yetkiye göre), son tüketim, bloke nedeni.
- **Stok hareketleri defteri** (`GET /inventory/movements`): hareket tipi, yön, miktar, lot, ilişkili belge, zaman. Filtre: lot, hareket tipi, tarih aralığı.
- Depo transferi ve stok düzeltme formları (`/inventory/transfers`, `/inventory/adjustments`; düzeltme gerekçe ister).
- Defter bütünlüğü kartı (`GET /reports/ledger-integrity`): bakiye = Σ(giriş) − Σ(çıkış) tutarlılığı.

### 4.6 Dış hizmetle üretim (P0) — Görev 1
- Emir listesi ve detay (`/production-orders`).
- **Emir sihirbazı:** emir oluştur → girdi lotları ekle (`/inputs`) → hizmet maliyeti ekle (`/service-costs`; 85 × 5,50 €) → başlat (`/start`) → tamamla (`/complete`, mamul lot kodu ve gerçek miktar).
- **Maliyet paneli** (yetki varsa): girdi maliyeti 1.076,00 €, hizmet 467,50 €, toplam 1.543,50 €, EKP 18,16 € (hesap 18,1588), VKP, brüt kâr/birim, marj. Planlanan ve gerçek miktar farkı (`quantity_difference`).
- Emir `IN_PROGRESS` iken stok değişmez; tamamlanınca hammadde düşer, mamul lot oluşur. Arayüz bu durumu açıkça gösterir.
- Düzeltme: `POST /…/reverse` (`corrections:manage`, gerekçe zorunlu). Ters kayıt eklenir, silme yoktur; zaten sevk edilmiş çıktı varsa `409 CANNOT_REVERSE` mesajı gösterilir.
- Yeniden işleme (rework) emri formu (P2).
- **AI tahmini:** emir detayında "Tahmini çıktı / EKP" kartı (bölüm 4.12).

### 4.7 Bütün kuzu parçalama (P0) — Görev 2
- Emir oluştur (hayvan türü, giriş ağırlığı, gerçek toplam alış maliyeti, beyan edilen birim fiyat, dağıtım anahtarı `BY_WEIGHT`/`BY_VALUE`), giriş lotu bağla, başlat, fire kaydı ekle (`/waste-records`), tamamla.
- **Reçete düzenleyici** (`GET/PUT /butchering-recipes/{hayvan}`): beklenen oranlar ve toplam oran uyarısı.
- **Ağırlık dengesi göstergesi:** giriş = Σ parça + fire + fark. Fark toleransı aşarsa tamamlama `409 WEIGHT_VARIANCE_EXCEEDED` döner; `butchering:approve_variance` yetkisi olan kullanıcı **gerekçe yazarak** onaylar. Sessiz düzeltme yoktur.
- **Kaynak tutarsızlığı bulgusu:** PDF örneği 25 kg × 11,50 € = 287,50 € iken kaynak toplam 351,00 €'dur ve parçalar 22 kg'dır. Emir detayında `SOURCE_COST_MISMATCH` bulgusu kırmızı rozetle, hesaplanan/beyan edilen/fark değerleriyle gösterilir (yetkiye göre). Bu, gereksinimde açıkça istenen "tutarsızlığı tespit edip açıkla" maddesidir.
- Maliyet dağıtım tablosu: parça, ağırlık, dağıtılan maliyet, birim maliyet; **toplam dağıtılan = toplam maliyet** doğrulaması görünür.
- `BY_VALUE` için değerleme tabanı yoksa `BY_VALUE_WASTE_VALUATION_REQUIRED` hatası kullanıcıya anlaşılır biçimde sunulur.
- Beklenen–gerçek ağırlık sapması (reçeteye göre) ve AI tahmin kartı.

### 4.8 Satış ve sevkiyat (P0) — PDF "satış raporu"
- Satış listesi/detayı (`/sales`): satır başına lot, miktar, birim fiyat ve ilgili stok hareketi. İptal (`/void`, `sales:void`).
- Sevkiyat listesi (`/shipments`): oluştur, **sevk et** (`/dispatch`, `Idempotency-Key`), iptal, **iade** (`/return`, gerekçe). Sevk, fiziksel stok çıkışının tek sahibidir.
- Satış oluşturma ekranı web'de P2'dir (saha satışı Android'dedir); ancak demo için yönetici satışı gerekebilir.

### 4.9 İzlenebilirlik (P0) — Görev 3
- **Lot arama kutusu** (lot kodu: `ET-2026-001`).
- **İleri izleme** (`GET /traceability/lots/by-code/{kod}/forward`): hammadde lotu → üretim emirleri → mamul lotları (miktar ve pay) → sevkiyatlar → müşteri/market (miktar). İkinci kademe dağıtım **yalnızca kayıtlıysa** gösterilir; yoksa "kayıtlı değil" yazılır, varsayım yapılmaz.
- **Geriye izleme** (`/backward`): mamul lot → kullanılan hammadde lotları → tedarikçi → üretim emirleri.
- **Grafik görünümü** (`/graph`): lotlar düğüm, üretim/parçalama/rework işlemleri kenar; miktar etiketli. Çoktan çoğa ilişkiler görünür olmalı. Basit bir katmanlı yerleşim yeterlidir (ör. `reactflow` veya SVG); fiziksel yerleşim süslemesi gereksizdir.
- Sonuç tabloları dışa aktarılabilir (CSV).

### 4.10 Geri çağırma (P0) — Görev 3
- Recall listesi ve oluşturma (`POST /recalls`: kod, neden kodu, açıklama, sorunlu lot kodları).
- **Simülasyon** (`GET /recalls/{id}/simulation`): aktive etmeden önce etkilenecek lotlar, bloke edilecek stok, müşteri/market bazlı miktarlar.
- **Aktive et** (`POST /recalls/{id}/activate`): onay penceresi (geri alınamaz uyarısı). Aktivasyon eşzamanlı satış/sevkiyatlara karşı atomiktir; sonrasında etkilenen lotların çıkışı reddedilir.
- **Etkilenen müşteri/market ve iletişim listesi** (`GET /reports/recalls/{id}/notification-list`): market adı, miktar, sevkiyat kodu, telefon/e-posta. Demo hedefi: **Market A 30, Market B 25, Market C 30**. Yazdırılabilir/CSV.
- Etki satırı durumu güncelleme (`PATCH …/impacts/{id}`: iletişime geçildi vb.).
- Çözüm (`/resolve`, `recalls:resolve`): **çözüm bloğu kaldırmaz.** Blokajı kaldırmak ayrı yetki (`lots:unblock`) ve gerekçe ister (`POST /lots/{id}/unblock`). Arayüz bu iki adımı ayrı düğmelerle sunar.
- İptal (`/cancel`).

### 4.11 Raporlar (P0) — PDF'te adı geçen raporlar
Tek bir "Raporlar" bölümünde, hepsi tablo + filtre + CSV:

| Rapor | Veri kaynağı |
|---|---|
| Alış raporu | `lots` + `inventory/movements` (RECEIPT) |
| Üretim raporu | `GET /reports/production-costs` (emir, miktar, EKP, VKP, marj) |
| Parçalama raporu | `GET /butchering-orders` + detay (verim, fire, dağıtım) |
| Lot hareketleri raporu | `GET /inventory/movements` |
| Satış raporu | `GET /sales`, `GET /shipments` |
| Geri çağırma raporu | `GET /recalls`, notification-list |
| Stok değerleme | `GET /reports/stock-valuation` (yetkiye göre) |
| Defter bütünlüğü | `GET /reports/ledger-integrity` |

### 4.12 Yapay zeka (P0 tahmin–sapma, P1 diğerleri)
- **Tahmin–gerçek–sapma** görünümü (`GET /ai/predictions`): her kayıt için tahmin, baseline, gerçek ve sapma yan yana. A modeli: paket sayısı ve EKP. B modeli: parça bazında kg. Sapma grafiği (tahmin ve baseline hatası karşılaştırması).
- **Tahmin al** düğmeleri: üretim emri (`POST /ai/production-yield/predict`), parçalama emri veya hayvan türü + ağırlık (`POST /ai/butchering-output/predict`).
- **Model durumu** (`GET /ai/models`): sürüm, örnek sayısı, seçilen model, çapraz doğrulama ve holdout metrikleri, **sınırlılık notları** (her zaman görünür: "Eğitim verisi sentetik olabilir").
- Eğitim ve sentetik veri üretimi yalnızca yönetici/operatör (`ai:run`) için; büyük veride istek dakikalar sürebilir, zaman aşımı mesajı gerekir.
- Kural: AI çıktısı stok/lot bilgisinin yerine geçmez; ekranda "tahmin" etiketi taşır.
- Anomali uyarıları (`GET /alerts`, `POST /alerts/scan`, `…/acknowledge`): tür, önem derecesi, açıklama; `MULTIVARIATE_ANOMALY` INFO düzeyindedir.
- Raporun tamamı `docs/AI_RAPORU.md` içindedir; panelde bağlantı verilir.

### 4.13 Denetim ve kullanıcılar (P1)
- Denetim kayıtları (`GET /audit-events`, `audit:read`): varlık, işlem, kullanıcı, zaman, ayrıntı; filtreli. Maliyet alanları yetkisiz kullanıcıya gelmez.
- Kullanıcı yönetimi (`/users`, `users:manage`): oluştur, rol/aktiflik değiştir, parola sıfırla.

## 5. Durum ve hata yönetimi kuralları

- Her liste: yükleniyor iskeleti, boş durum metni, hata durumu + "Tekrar dene".
- Her yazma işlemi: düğme kilidi (çift tıklama koruması), başarıda ilgili sorgu geçersiz kılma, başarısızlıkta `error.message`.
- Beklenen hata kodları için özel mesaj: `INSUFFICIENT_STOCK`, `LOT_BLOCKED`, `INVALID_STATE_TRANSITION`, `WEIGHT_VARIANCE_EXCEEDED`, `BY_VALUE_WASTE_VALUATION_REQUIRED`, `CANNOT_REVERSE`, `LOT_ALREADY_EXISTS`, `UNIT_MISMATCH`, `EXPIRY_REQUIRED_MISSING`, `IDEMPOTENCY_KEY_REUSED`, `RATE_LIMITED`.
- Kritik eylemler (recall aktivasyonu, reverse, void, iade, blokaj kaldırma) onay penceresi ve **gerekçe alanı** ister.

## 6. İş sırası ve takvim (4–5 gün, 1 kişi)

| Gün | Çıktı | Kabul |
|---|---|---|
| 1 | İskelet: Vite+TS+Tailwind, API istemcisi (tipler üretilir), oturum + token yenileme, korumalı rotalar, rol menüsü, ortak bileşenler, pano | Admin ile girilir, 401'de sessiz yenileme çalışır, pano gerçek veri gösterir |
| 2 | Katalog, lot kabulü, lot listesi/detay, stok hareketleri, fatura okuma akışı | Lot kabul edilir, hareket defterinde görünür, fatura öneri→onay çalışır |
| 3 | Üretim sihirbazı ve maliyet paneli, parçalama + reçete + varyans onayı + tutarsızlık bulgusu | Referans senaryo: EKP 18,16 €; kuzu örneğinde 351,00/287,50 tutarsızlığı ve 22/25 kg farkı görünür |
| 4 | İzlenebilirlik (ileri/geri/graf), recall (simülasyon, aktivasyon, bildirim listesi), sevkiyat/satış listeleri | ET-2026-001 aratılınca A/B/C marketleri 30/25/30 ile listelenir |
| 5 | Raporlar sekmesi + CSV, AI sayfası, uyarılar, denetim, kullanıcılar, cila, e2e testi, README | Bölüm 8'deki demo betiği baştan sona hatasız oynar |

Android ile paralel ilerlenecekse web'in 3. günden sonraki işleri (P1/P2) kısaltılabilir. Önce **P0** hedefleri bitirilir.

## 7. Test stratejisi

- **Birim/bileşen (Vitest + Testing Library):**
  - `decimal.js` biçimlendirme (4 hane hesap / 2 hane gösterim, yuvarlama ROUND_HALF_UP).
  - Maliyet alanı yoksa sütunun gizlendiği (rol: VIEWER/SALES) testi.
  - Token yenileme: eşzamanlı üç `401` → tek `refresh` isteği.
  - Hata zarfı çözümleme ve kod → mesaj eşlemesi.
- **Sözleşme:** `npm run gen:api` sonrası `git diff --exit-code src/api/schema.d.ts` (sözleşme değişince tipler de güncellenmeli; CI/hızlı kontrol).
- **Uçtan uca (Playwright, 1 senaryo):** seed'li backend'e karşı admin girişi → ET-2026-001 ara → ileri izleme → recall oluştur, simüle et, aktive et → bildirim listesinde Market A/B/C = 30/25/30 → bloke lot satışının reddedildiği görülür.
- Kabul listesi: `docs/handoff/ACCEPTANCE_CRITERIA.md` Bölüm A, E, F, G, H, I, J'nin kullanıcı arayüzüyle ilgili maddeleri.

## 8. Demo betiği (web tarafı)

1. Admin ile giriş → pano: aktif recall ve bloke lot sayıları.
2. Üretim → `URT-2026-045`: girdiler (ET 100 kg, baharat 2 kg, bağırsak 5 kg), hizmet 85 × 5,50 €, EKP 18,16 €, VKP 24,00 €, marj. AI kartı: tahmin ve gerçek yan yana.
3. Parçalama → `PRC-2026-001`: 351,00 / 287,50 € tutarsızlık bulgusu, 25 kg giriş / 22 kg parça farkı ve gerekçeli onay, dağıtılan toplam = toplam maliyet.
4. İzlenebilirlik → `ET-2026-001` ileri: `URT-2026-045` → `SUC-2026-045` (85) → Market A/B/C (30/25/30). `SUC-2026-045` geriye: hammadde lotu ve tedarikçi.
5. Recall → `ET-2026-001` için simülasyon → aktivasyon → etkilenen lotlar bloke → bildirim listesi (telefon/e-posta) → CSV.
6. Android'den aynı lotun satışının reddedildiğini göster (bkz. `android/README.md`).
7. Raporlar: alış, üretim, parçalama, lot hareketleri, satış, geri çağırma.

## 9. Kabul ölçütleri (web "bitti" tanımı)

- [ ] Tüm P0 ekranları çalışır ve rol izinlerine saygı gösterir.
- [ ] Hiçbir yerde `number` ile para/miktar hesabı yoktur.
- [ ] Maliyet alanı olmayan rolde arayüz bozulmaz (sütun/kart gizlenir).
- [ ] Token yenileme eşzamanlı isteklerde oturumu düşürmez.
- [ ] Kritik eylemler gerekçe/onay ister; geri alınamaz olanlar açıkça uyarır.
- [ ] Referans sayıları doğrulanır: 1.543,50 € / 85 = 18,16 €; 30/25/30 market dağılımı; 287,50 ≠ 351,00 ve 22 ≠ 25 kg bulguları görünür.
- [ ] `npm run build` uyarısızdır, Vitest ve Playwright testleri geçer.
- [ ] README'de kurulum, çalıştırma, ortam değişkeni (`VITE_API_BASE_URL`), demo hesapları ve bilinen sınırlamalar bulunur.

## 10. Riskler ve açık sorular

| Risk / soru | Önlem |
|---|---|
| İzlenebilirlik grafiği zaman alabilir | Önce tablo/ağaç görünümü teslim edilir, grafik P1 olarak eklenir. |
| Backend sözleşmesi değişirse tipler eskir | Tipler her gün başında yeniden üretilir; değişiklik `contract/openapi.json` PR'ında görünür. |
| Rol/maliyet gizleme ekranları bozabilir | Her maliyet alanı opsiyonel tipli; VIEWER ve SALES ile elle kontrol edilir. |
| Uzun süren AI eğitim isteği zaman aşımına düşebilir | Sunucu 200 dönene kadar bekleme göstergesi; eğitim zaten seed'de yapıldığı için demo bunu tetiklemez. |
| Token saklama (sessionStorage) | Bilinen sınırlama olarak belgelenir; HttpOnly çerez backend değişikliği ister. |
| Açık: web'de satış oluşturma ekranı gerekli mi? | Önerilen: gerekli değil (P2); saha satışı Android'dedir. Karar bekliyor. |
| Açık: dışa aktarım biçimi CSV mi, PDF mi? | Önerilen: yalnızca CSV (tarayıcıda üretilir). |

## 11. Çalıştırma (hedef)

```bash
# backend (ayrı terminal): backend/README.md
cd web
npm install
cp .env.example .env        # VITE_API_BASE_URL=http://127.0.0.1:8000
npm run gen:api             # contract/openapi.json -> src/api/schema.d.ts
npm run dev                 # http://localhost:5173
npm run test && npm run build
```
