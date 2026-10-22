# Cilt 1.21 — Error, Idempotency & Response Contract Registry


> **Normatif güncelleme — 22 Ekim 2026 (Cilt 1.32):** Bu belgedeki daha eski ve çelişen taslak ifadeler için `volume-01-32-approved-decisions-and-cross-check.md` ile Cilt 1.31'in onay kaydı önceliklidir. Bu not doküman sözleşmesini günceller; migration veya veritabanı değişikliği izni değildir.

**Tarih:** 22 Ekim 2026  
**Durum:** Sözleşme birleştirme taslağı; açık kararlar proje sahibi tarafından onaylanana kadar `PROPOSED`  
**Kapsam:** FastAPI REST API hata yanıtları, başarılı yanıtlar, doğrulama, idempotency ve tekrar çağırma davranışı.  
**Kapsam dışı:** Uygulama kodu, Alembic migration üretimi ve veritabanı oluşturma/değiştirme.

## 1. Amaç ve normatif yaklaşım

Bu cilt, kodlama LLM'sinin aynı hata veya tekrar isteği için farklı endpoint'lerde farklı davranışlar üretmesini önlemek üzere API yanıt sözleşmesini tek yerde toplar.

- `APPROVED`: proje sahibi tarafından onaylanmış bağlayıcı karar.
- `PROPOSED`: tutarlılık için önerilen, henüz proje sahibi onayı almamış karar.
- `OPEN`: karar verilmeden uygulama davranışı kesinleştirilemez.
- `BLOCKED`: uygulama veya migration açısından çözülmesi zorunlu bağımlılık.

Bu belgede önerilen yeni davranışlar otomatik olarak onaylanmış sayılmaz. Başka bir ciltteki eski bir metinle çelişki görülürse sessizce seçim yapılmaz; fark, etkilenen dosyalar ve gereken karar kayda geçirilir.

## 2. Önceden onaylanmış sözleşme temeli

Aşağıdaki maddeler mevcut proje kararlarından alınmıştır:

- API öneki `/api/v1`.
- JSON alan adları `snake_case`; enum değerleri `UPPER_SNAKE_CASE`; endpoint yolları küçük harf ve kebab-case.
- Hata zarfının temel alanları `error.code`, `error.message`, isteğe bağlı `error.details` ve `request_id`.
- Para ve miktar değerleri API JSON'unda ondalık hassasiyeti kaybetmemek için string olarak temsil edilir.
- Kritik operasyon kayıtları fiziksel olarak silinmez; iptal/düzeltme/ters kayıt iş kurallarına göre yapılır.
- Satış için `Idempotency-Key` zorunludur. Aynı key ve aynı istek gövdesi önceki sonucu döndürür; aynı key farklı gövdeyle kullanılırsa `409 Conflict` döner.
- MySQL'e yalnızca backend bağlanır; istemciler doğrudan MySQL'e erişmez.

## 3. Standart hata yanıtı

### 3.1 Önerilen kanonik zarf

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid fields.",
    "details": [
      {
        "field": "quantity",
        "issue": "Must be greater than zero."
      }
    ]
  },
  "request_id": "req_example_01"
}
```

**Durum: `PROPOSED`.** Alan yapısı mevcut kararlarla uyumludur; `details` içindeki öğelerin tam şeması, hata mesajlarının dili ve `request_id`'nin response body ile HTTP header arasında nerelerde taşınacağı ayrıca onaylanmalıdır.

Kurallar:

1. Her hata yanıtında `error.code`, güvenli ve kullanıcıya gösterilebilir `error.message`, `request_id` bulunur.
2. `error.details` yalnızca gerektiğinde eklenir; parola, token, SQL sorgusu, bağlantı bilgisi, stack trace veya kişisel sır içermez.
3. İstemci kararını `message` metnine göre değil, makine tarafından okunabilir `error.code` değerine göre verir.
4. Hata mesajları kullanıcıya uygun ve sabit olmalı; ham framework/DB hata metni dışarı verilmemelidir.
5. Her hata `request_id` ile sunucu loglarına bağlanabilmelidir.
6. Tek bir istekte birden fazla doğrulama hatası varsa sıralı, alanı belirtilmiş liste dönülmesi önerilir; bu sıralamanın deterministik olup olmayacağı açık karardır.

## 4. HTTP durum kodu kaydı

Aşağıdaki eşleştirme öneridir; genel sözleşme olarak onaylanmadan tüm endpoint'lere uygulanmamalıdır.

| HTTP | Kanonik `error.code` örneği | Kullanım |
|---|---|---|
| 400 | `BAD_REQUEST` | İstek sözdizimi/formatı geçersiz ve 422 ayrımı uygulanmıyorsa |
| 401 | `UNAUTHENTICATED` | Token eksik, geçersiz veya süresi dolmuş |
| 403 | `FORBIDDEN` | Kimliği doğrulanmış kullanıcının izni yok |
| 404 | `RESOURCE_NOT_FOUND` | Kaynak yok veya görünürlüğü güvenlik gereği gizleniyor |
| 409 | `CONFLICT` | Durum geçişi, stok/lot durumu veya idempotency çakışması |
| 422 | `VALIDATION_ERROR` | Alan doğrulaması ya da iş kuralı girdisi geçersiz |
| 429 | `RATE_LIMITED` | İstek sınırı aşıldı; rate-limit politikası onaylanırsa |
| 500 | `INTERNAL_ERROR` | Beklenmeyen sunucu hatası |
| 503 | `SERVICE_UNAVAILABLE` | Hazır olmayan servis veya gerekli bağımlılık erişilemiyor |

**Açık karar:** İstek parse hataları için `400` mı, Pydantic doğrulama hataları için `422` mı kullanılacağı; iş kuralı doğrulamalarının `409` veya `422` olarak sınıflandırılması. Önerilen ayrım: bozuk JSON/parametre biçimi `400`, doğru biçimli fakat alan kuralına aykırı girdi `422`, geçerli girdinin mevcut kaynak durumuyla çatışması `409`.

## 5. Kanonik hata kodu kataloğu — taslak

| Kod | Önerilen HTTP | Koşul | Not |
|---|---:|---|---|
| `BAD_REQUEST` | 400 | İstek biçimi bozuk | Genel parse/format hatası |
| `UNAUTHENTICATED` | 401 | Kimlik doğrulaması yok/geçersiz | Token ayrıntısını sızdırma |
| `TOKEN_EXPIRED` | 401 | Token süresi dolmuş | `UNAUTHENTICATED` alt türü; ayrı kod kararı açık |
| `FORBIDDEN` | 403 | Yetki yok | Yetki ayrıntılarını gereksiz ifşa etme |
| `RESOURCE_NOT_FOUND` | 404 | Kaynak bulunamadı | ID/code bazlı kaynaklar |
| `VALIDATION_ERROR` | 422 | Alan/iş girdisi geçersiz | `details` alan bazlı olabilir |
| `CONFLICT` | 409 | Genel kaynak durumu çatışması | Tek başına belirsiz kalırsa özel kod kullanılmalı |
| `INVALID_STATE_TRANSITION` | 409 | Geçiş mevcut durumdan izinli değil | Workflow registry ile eşleşmeli |
| `INSUFFICIENT_STOCK` | 409 | Kullanılabilir lot bakiyesi yetersiz | Stok kontrolü transaction içinde |
| `LOT_BLOCKED` | 409 | Lot recall/başka nedenle satışa kapalı | Satış engelleme için kritik |
| `IDEMPOTENCY_KEY_REUSED` | 409 | Aynı key farklı payload ile kullanılmış | Satışta mevcut karar onaylı |
| `IDEMPOTENCY_KEY_REQUIRED` | 422 | Zorunlu key eksik | HTTP sınıflandırması onaya açık |
| `RATE_LIMITED` | 429 | Rate limit aşıldı | Politika henüz kesin değil |
| `INTERNAL_ERROR` | 500 | Beklenmeyen hata | Stack trace istemciye verilmez |
| `SERVICE_UNAVAILABLE` | 503 | Servis hazır değil | Health/readiness sözleşmesiyle uyumlu olmalı |

Bu katalog **taslaktır**. Sonraki ciltte tüm kodlar için nihai, tekil registry yapılmalı; kullanılmayan/çakışan kodlar kaldırılmalıdır.

## 6. Başarılı yanıt sözleşmesi

### 6.1 Kaynak döndüren istekler

Önerilen yaklaşım: JSON response body doğrudan kaynak DTO'su olur; her yanıta zorunlu genel `data` sarmalayıcısı eklenmez. Liste yanıtlarında pagination alanları endpoint sözleşmesinde açıkça tanımlanır.

### 6.2 Oluşturma ve komut endpoint'leri

- Kaynak oluşturan `POST`: tercihen `201 Created`, response body oluşturulan kaynağı içerir; uygun olduğunda `Location` header döner.
- İşlem yapan fakat yeni bir kaynak temsilini oluşturmayan komut: `200 OK` ve tanımlı sonuç DTO'su ya da gövdesiz `204 No Content`; endpoint bazında kararlaştırılmalıdır.
- Başarılı yanıtların `request_id` taşıma biçimi **OPEN**: öneri, `X-Request-ID` response header'ı ve hata gövdesinde `request_id`; başarılı body'ye her zaman eklemek zorunlu olmasın.
- `204 No Content` yanıtında body bulunmaz; `request_id` header'da taşınır.

Bu öneri henüz onaylanmadı. Cilt 1.3/1.4'teki her endpoint'in status code, body ve header'larıyla tek tek eşleştirilmesi gereklidir.

## 7. Idempotency standardı

### 7.1 Satış — onaylanmış temel davranış

- `Idempotency-Key` zorunludur.
- İlk başarılı işleme ait key, istek gövdesi özeti ve sonuç ilişkilendirilir.
- Aynı key + aynı normalize edilmiş istek: ilk isteğin sonucunu tekrar döndürür; ikinci satış veya ikinci stok `OUT` hareketi oluşmaz.
- Aynı key + farklı istek gövdesi: `409` ve `IDEMPOTENCY_KEY_REUSED`.
- Eşzamanlı aynı-key istekleri atomik biçimde tek satış oluşturmalıdır.

**Henüz tam kararlaştırılmamış ayrıntılar:** key saklama süresi, kullanıcı/tenant kapsamı, normalize edilmiş payload karşılaştırma algoritması, ilk istek başarısız olduğunda key'in davranışı ve hangi yanıtların replay edileceği.

### 7.2 Diğer kritik komutlar

Aşağıdaki komutların her biri için idempotency key veya deterministik state-conflict yaklaşımı seçilmelidir:

- Üretim emrini tamamlamak ve mamul kabulü
- Kasaplık emrini tamamlamak
- Lot sevkiyatı / dispatch onayı
- İade kaydı
- Fire kaydı
- Recall aktivasyonu
- Recall çözümü / lot blokajını kaldırma
- Stok düzeltme ve ters kayıt

**Önerilen politika:** her komutta tekrar çağrının yan etkisini açıkça belirle. Aynı komutun ikinci kez çalışması ikinci stok hareketi, ikinci maliyet dağıtımı, ikinci genealogy bağlantısı veya ikinci audit iş etkisi yaratmamalıdır. İdempotency key kullanılıp kullanılmayacağı, key kapsamı ve replay davranışı endpoint bazında kaydedilmelidir. Bu öneri proje sahibi onayı gerektirir.

## 8. İşlem ve hata atomikliği

- Stok ledger hareketi, lot bakiyesi, lot genealogy, maliyet kayıtları ve iş akışı durumu aynı iş kuralının gerektirdiği transaction içinde tutarlı kalmalıdır.
- İşlem başarısız olursa ilgili transaction içindeki değişiklikler rollback edilir.
- Audit kayıtlarının ana işlemle atomik olup olmayacağı, audit sisteminin ayrı depoya yazıp yazmadığı ve audit yazma hatasında kritik işlemin durdurulması **OPEN** konudur; Cilt 1.20 ve workflow ciltleriyle birlikte karara bağlanmalıdır.
- Beklenmeyen exception'lar istemciye stack trace olarak dönülmez; sunucu tarafında `request_id` ile kaydedilir.
- Bir transaction commit edildikten sonra istemci bağlantısı koptuğunda tekrar deneme çift yan etki yaratmamalıdır; idempotency veya kaynak durumunu güvenli sorgulama gerekir.

## 9. Pagination, filtering ve list response

Mevcut karar, API'nin tutarlı pagination ve filtreleme kullanmasıdır; sayfa parametrelerinin tam biçimi henüz tek registry'de kesinleşmemiştir.

**Önerilen taslak:** `page` 1 tabanlı, `page_size` varsayılan 20 ve üst sınır 100; sıralama açıkça istenmedikçe kararlı bir varsayılan sıralama. Bu sayılar proje sahibi onayı olmadan bağlayıcı değildir.

Her liste endpoint'i şu bilgileri belirtmelidir:
- Desteklenen filtreler ve türleri
- Varsayılan sıralama ve eşitlik bozucu alan
- Sayfalama parametreleri ve sınırlar
- Boş sonuç davranışı
- Yanıt DTO'su ve pagination metadata alanları

## 10. Test matrisi

Her endpoint için uygun olanlar uygulanmak üzere:

1. Başarılı yanıtın status, header ve body şeması.
2. Geçersiz JSON/parametre ve Pydantic doğrulaması.
3. Kimlik doğrulama ve rol/yetki ihlali.
4. Kaynak bulunamadı.
5. Geçersiz durum geçişi.
6. Yetersiz stok veya bloke lot.
7. DB constraint / unique conflict'in güvenli hata yanıtına çevrilmesi.
8. Aynı idempotency key + aynı payload tekrar çağrısı.
9. Aynı key + farklı payload.
10. Eşzamanlı tekrar istekleri.
11. Transaction rollback: başarısız işlem kısmi stok/maliyet/genealogy kaydı bırakmamalı.
12. Hata yanıtında hassas bilgi bulunmaması ve `request_id` ile log korelasyonu.

## 11. Açık karar kayıtları

| ID | Karar | Öneri | Durum / etkisi |
|---|---|---|---|
| ERR-01 | 400/422 ayrımı | Bozuk format 400; alan doğrulama 422 | `OPEN`; tüm endpoint testlerini etkiler |
| ERR-02 | İş kuralı hatası sınıflandırması | Mevcut durum çatışması 409; geçersiz girdi 422 | `PROPOSED` |
| ERR-03 | Hata `details` şeması ve mesaj dili | Alan/issue listesi; istemci mesajı Türkçe mi İngilizce mi tek dil politikasıyla seçilmeli | `OPEN` |
| RESP-01 | Başarılı yanıtta request ID | `X-Request-ID` header; hata gövdesinde `request_id` | `PROPOSED` |
| RESP-02 | Genel `data` wrapper | Wrapper olmadan endpoint'e özgü DTO; liste metadata'sı açıkça tanımlı | `PROPOSED` |
| IDEM-01 | Satış idempotency retention/scope | Süre ve kullanıcı/tenant kapsamı belirlenmeli | `OPEN` |
| IDEM-02 | İlk isteğin başarısız olması | Hangi hata sonuçlarının saklanacağı/replay edileceği belirlenmeli | `OPEN` |
| IDEM-03 | Kritik komut kapsamı | Komut başına key veya deterministik state conflict | `OPEN` |
| IDEM-04 | Eşzamanlı aynı-key isteği | Tek iş etkisi; atomik kontrol | `PROPOSED`, test zorunlu |
| PAGE-01 | Pagination standardı | page/page_size; 20 varsayılan, 100 maksimum | `OPEN`; sayı onayı gerekiyor |
| AUD-01 | Audit hatası ana işlemi durdurur mu? | Kritik operasyonlarda audit kaybını sessizce kabul etme; atomiklik mimarisi seçilmeli | `OPEN`; Cilt 1.20 ile çapraz karar |
| ERR-04 | 429 rate limit standardı | Login ve hassas endpoint'ler için limit ve `Retry-After` davranışı belirlenmeli | `OPEN` |

## 12. Ciltler arası yapılması gereken güncellemeler

Kararlar onaylandığında en az şu belgeler çapraz güncellenmelidir:

- Cilt 1.3: her endpoint'in status code, error code, body/header ve idempotency davranışı.
- Cilt 1.4: Pydantic DTO, OpenAPI örnekleri ve sözleşme testleri.
- Cilt 1.5: durum geçişi çatışmaları, rollback ve tekrar komut etkileri.
- Cilt 1.6: exception handler, transaction, log correlation ve idempotency servis sorumlulukları.
- Cilt 1.7: unique/index/constraint adayları; yalnızca kararlar onaylandıktan sonra migration planı.
- Cilt 1.8–1.9 ve 1.20: auth/permission hataları, rate limit ve audit davranışı.
- Cilt 1.18–1.19: açık karar registry'si ve workflow ID/state eşleştirmesi.

## 13. Kodlama LLM'sine talimat

1. Bu ciltte `PROPOSED` ve `OPEN` işaretli maddeleri onaylanmış gibi uygulama.
2. Her endpoint için success/error/status/header/idempotency matrisi çıkar; belirsizlikleri `BLOCKED` listesine al.
3. Genel hata zarfını tek FastAPI exception-handling katmanında uygula; hassas detayları sızdırma.
4. Stok ve maliyet etkisi olan komutlarda retry davranışını ve transaction sınırını test et.
5. Aynı idempotency key ile iki iş etkisinin oluşmadığını eşzamanlı testle kanıtla.
6. Doküman ile OpenAPI çıktısı çelişirse kendi tercihini uygulama; fark raporu hazırla.
7. Bu cilt migration veya veritabanı oluşturma/değiştirme izni vermez.

## 14. Sonraki adım

Cilt 1.22 — Full Nullable/Constraint/Index/DTO Crosswalk hazırlanacaktır. Açık kararlar için ayrıca bir karar oturumu planlanacaktır; kararlar ciltler boyunca toplanacak ancak kodlama devri ve migration onayı öncesinde hiçbir kritik `OPEN` veya `BLOCKED` madde bırakılmayacaktır.
