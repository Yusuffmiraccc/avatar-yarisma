# AVATAR — Güvenlik Politikası ve Mimarisi (SECURITY)

Bu belge, AVATAR sisteminde uygulanan güvenlik kontrollerini, kimlik doğrulama/yetkilendirme mimarisini, veri bütünlüğü güvencelerini ve işletim kurallarını açıklar.

---

## 1. Kimlik Doğrulama ve Oturum Güvenliği

1. **Parola Saklama:**
   - Parolalar kaynak kodda veya veritabanında asla düz metin olarak tutulmaz.
   - Endüstri standardı **Argon2id** (`m=65536, t=3, p=4`) algoritması kullanılır.
   - Zamanlama saldırılarını (timing attack) önlemek amacıyla, kullanıcı veritabanında bulunmasa dahi dummy hash ile doğrulama çalıştırılarak sabit süreli yanıt üretilir.

2. **Access Token:**
   - 15 dakika geçerlilik süresine sahip JSON Web Token (`HS256`).
   - İçerik: `sub` (kullanıcı ID), `roles` (roller), `ver` (token versiyonu), `typ` ("access"), `jti` (benzersiz UUID), `exp` (son geçerlilik).
   - Kullanıcı devre dışı bırakıldığında veya parolası değiştiğinde `token_version` artırılarak mevcut tüm access token'lar anında geçersiz kılınır.

3. **Refresh Token ve Yenileme Döngüsü (Rotation):**
   - 7 gün geçerlilik süresi.
   - İstemciye düz metin 48-bayt URL-safe rastgele token döner; veritabanında yalnızca SHA-256 hash değeri saklanır.
   - **Tek Seferlik Kullanım:** Her `/auth/refresh` çağrısında kullanılan refresh token iptal edilir ve yeni bir refresh token üretilir.
   - **Replay / Çalınma Tespiti (Family Revocation):** Daha önce kullanılmış veya iptal edilmiş bir refresh token ile tekrar istek yapılırsa, token ailesine ait tüm aktif oturumlar derhal iptal edilir.
   - **Eşzamanlı 401 Kilidi (Single-Flight Lock):** Android mobil istemcisinde eşzamanlı gelen 401 yanıtlarında `TokenAuthenticator` senkronize kilit kullanarak aynı anda tek bir yenileme isteği atar; böylece yarış koşulları nedeniyle ailenin kazara iptal olması engellenir.

---

## 2. Rol Bazlı Yetkilendirme ve İzin Matrisi (RBAC)

Sistem **deny-by-default (varsayılan olarak engelle)** prensibiyle çalışır. Her uç nokta explicit izin kontrolü (`require("permission:name")`) ile korunur.

| Rol | Kapsam ve İzinler |
|---|---|
| **ADMIN** | Tam sistem yöneticisi. Kullanıcı yönetimi, sistem yapılandırması, tüm operasyonel ve maliyet okuma/yazma izinleri. |
| **OPERATOR** | Depo ve üretim sorumlusu. Hammadde kabulü, üretim emirleri, parçalama, stok transferleri ve düzeltmeler. |
| **SALES** | Saha satış personeli. Katalog okuma, satılabilir lotları görme, satış/sevkiyat oluşturma. **Fiyat düzenleme (`sales:override_price`) ve maliyet görme (`costs:read`) yetkisi kesinlikle yoktur.** |
| **TRACEABILITY_MANAGER** | Kalite güvence ve geri çağırma yöneticisi. İleri-geri lot izleme, geri çağırma oluşturma/aktive etme, lot blokajı ve blokaj kaldırma (`lots:unblock`). |
| **VIEWER** | Salt okunur izleme rolü. Maliyet ve kâr marjı verilerine erişemez. |

### 2.1 Maliyet Bilgisi İzolasyonu
- `costs:read` izni bulunmayan kullanıcılara (SALES, VIEWER) API seviyesinde `redact_cost_data` filtresi uygulanır.
- `unit_cost`, `unit_cost_ekp`, `total_cost`, `total_input_cost`, `gross_margin` gibi hassas maliyet alanları yanıtlardan tamamen çıkarılır; arayüzde gösterilmez.

---

## 3. Kaba Kuvvet (Brute-Force) ve Hız Sınırı (Rate Limiting)

- Giriş denemeleri IP adresi ve `IP + E-posta` çifti bazında bağımsız sayaçlarla sınırlandırılır.
- Limitler: E-posta başına 10 başarısız deneme / 15 dakika; IP başına 50 deneme / 15 dakika.
- Atomik Redis Lua betikleri ile kontrol edilir. Redis bağlantısı sağlanamadığında, tekil demo ortamları için süreç belleği (`threading.Lock` ile korunan in-memory dict) devreye girer.
- Limit aşıldığında `429 RATE_LIMITED` döner.

---

## 4. Veri Bütünlüğü ve İşlem Güvenliği (Concurrency)

1. **Idempotency Güvencesi:**
   - Satış (`POST /sales`) ve sevkiyat (`POST /shipments/{id}/dispatch`) işlemlerinde `Idempotency-Key` başlığı zorunludur.
   - İstemci UUID üretir ve satırla kalıcı saklar.
   - Aynı anahtar + aynı gövde ilk sonucu döner (çift kayıt veya mükerrer stok çıkışı oluşmaz).
   - Aynı anahtar + farklı gövde `409 IDEMPOTENCY_KEY_REUSED` ile reddedilir.

2. **Geri Çağırma (Recall) ile Satış Yarış Koşulu Koruması:**
   - Bir hammadde veya mamul lotu geri çağrıldığında, veritabanı seviyesinde `SELECT ... FOR UPDATE` satır kilitleri kullanılır.
   - Blokaj işlemi ile aynı milisaniyede gelen satış veya sevkiyat istekleri bekletilir; kilit açıldığında lot bloke statüsünde olduğu için `409 LOT_BLOCKED` hatasıyla geri çevrilir.

3. **Stok Defteri Bütünlüğü (Append-Only):**
   - Stok miktarı rastgele bir sayıyla güncellenemez. Her değişim `stock_movements` tablosuna `IN` veya `OUT` olarak yazılır.
   - Veritabanı seviyesinde negatif stok kısıtlamaları uygulanmıştır.

---

## 5. Ağ Güvenliği ve İletişim

1. **Ağ İzolasyonu:**
   - Web ve Android istemcileri doğrudan veritabanına (MySQL port 3306) bağlanamaz; tüm iletişim REST API üzerinden yürütülür.
   - Üretim ortamında veritabanı portu yalnızca backend konteyneriyle paylaşılır.

2. **Düz Metin HTTP (Cleartext) Kısıtı:**
   - Android uygulamasında `network_security_config.xml` ile cleartext HTTP izni yalnızca debug derlemesinde yerel adreslerle (`10.0.2.2`, `localhost`) sınırlandırılmıştır.
   - Release derlemesinde güvensiz HTTP trafiği tamamen engellenmiştir.

3. **CORS:**
   - Backend CORS ayarları `CORS_ORIGINS` ortam değişkeni ile sınırlandırılmıştır; yetkisiz etki alanlarından tarayıcı istekleri kabul edilmez.

---

## 6. Sırlar ve Konfigürasyon Yönetimi

- Hiçbir API anahtarı, veritabanı parolası veya JWT gizli anahtarı kaynak kodda sabit (hardcoded) olarak yer almaz.
- Tüm sırlar `.env` dosyasından okunur; repoya yalnızca yer tutucu içeren `.env.example` dosyası commit edilir.
- Pydantic Settings sınıflarında `SecretStr` tipi kullanılarak parolaların loglara ve hata çıktılarına yazılması önlenir.
