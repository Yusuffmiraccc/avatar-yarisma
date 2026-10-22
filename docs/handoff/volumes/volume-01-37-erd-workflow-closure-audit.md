# Cilt 1.37 — ERD ve WF-01–WF-10 Birleşik Kapanış Çalışması

**Tarih:** 22 Ekim 2026  
**Durum:** Doküman incelemesi ve denetim matrisi hazırlandı; ERD/workflow kapanışı henüz onaylanmış değil.  
**Kapsam:** Cilt 1.2, 1.3, 1.4, 1.5, 1.9, 1.19 ve 1.24 dokümanlarının birbirine bağlanması.  
**Yapılmayanlar:** ORM kodu, Alembic migration, gerçek MySQL şeması, API router'ı veya veritabanı değiştirilmedi.

## 1. Kullanıcı onayı nasıl yorumlandı?

Proje sahibi dokümantasyon ve denetim çalışmalarına devam edilmesi için onay verdi. Önceden belirlenen özel güvenlik kapısı ise hâlâ geçerlidir: Cilt 1.2 ERD ile Cilt 1.5 WF-01–WF-10 birlikte kontrol edilip açık noktalar gösterildikten sonra, migration veya veritabanı değişikliği için ayrıca açık onay alınmalıdır. Bu ciltte o özel onay varsayılmamıştır.

## 2. ERD incelemesinin sınırı

Cilt 1.2'deki Mermaid ilişki diyagramından güvenli şekilde ayırt edilebilen entity isimleri makine tarafından çıkarıldı. Bu liste **tam tablo envanteri değildir**; ilişki diyagramında görünmeyen tabloları, tüm kolonları, nullability, FK hedefleri, indeksleri veya CHECK constraint'leri kanıtlamaz.

Bu nedenle Cilt 1.37 şu sonucu verir:
- Mermaid ilişkilerindeki entity isimleri: **11**
- Tam tablo/kolon/FK/index/constraint envanteri: **AÇIK**
- Bu envanter olmadan ORM/migration doğruluğu: **kanıtlanmış değil**

Ayrıntılı, güvenilir envanter üretiminde her tablo için şu alanlar bulunmalı: `table_name`, `column_name`, `mysql_type`, `nullable`, `default`, `pk`, `fk_target`, `unique_group`, `index_name`, `check_constraint`, `source_section`, `api_dto_field`, `workflow_usage`, `status`. Sadece Mermaid ilişki isimleri bu tablo yerine kullanılamaz.

## 3. Workflow kimliği denetimi

WF-01–WF-10 kimliklerinin Cilt 1.5 ve Cilt 1.19'da bulunması, her akışın ayrıntılarının kapandığını göstermez. Bu sürüm her workflow için gereken kapanış kanıtını CSV manifestine yazdı.

| Workflow | Cilt 1.5 / registry kimliği | Kapanış için gereken ana kanıt |
|---|---|---|
| WF-01 | Kimlik mevcut | Girdi lotu, çıktı/fire satırları, maliyet tahsisi, stok ve audit etkileri |
| WF-02 | Kimlik mevcut | Tüketim, hizmet maliyeti, çıktı, tamamlanma ve maliyet snapshot'ı |
| WF-03 | Kimlik mevcut | Satış ile sevkiyat ayrımı ve sevk anındaki stok çıkışı |
| WF-04 | Kimlik mevcut | Recall aktivasyonu, çözüm/serbest bırakma, blokaj ve etkilenen müşteri miktarları |
| WF-05 | Kimlik mevcut | Ağırlık dengesi, tolerans, açıklamalı varyans ve artık dağıtım kuralı |
| WF-06 | Kimlik mevcut | İşlem türüne göre ters kayıt/düzeltme ve kaynak işleme bağlantı |
| WF-07 | Kimlik mevcut | Endpoint bazında retry/idempotency ve test kanıtı |
| WF-08 | Kimlik mevcut | Lot kabulü, stok defteri/bakiye atomikliği, duplicate/retry davranışı |
| WF-09 | Kimlik mevcut | Tahminin kalıcı olup olmayacağı, model sürümü, hata ve sonuç sözleşmesi |
| WF-10 | Kimlik mevcut | Her entity'nin nihai enumları ve API/DTO/ORM parity |

Makine tarafından okunabilir kanıt:
- `manifests/erd-workflow-reconciliation-v1.37.json`
- `manifests/erd-workflow-checklist-v1.37.csv`

## 4. Endpoint/izin farkı — tekrar doğrulama

Cilt 1.3 ve Cilt 1.9 statik imza karşılaştırması bu ciltte tekrarlandı:
- API sözleşmesi: **57** benzersiz method/path
- Yetki matrisi: **56** benzersiz method/path
- API-only: **1**
- Permission-only: **0**

- `API_ONLY`: `POST /api/v1/butchering-orders/{order_id}/waste-records` — Cilt 1.9'a yetki satırı eklenmeli veya Cilt 1.3 sözleşmesi gerekçeli biçimde revize edilmeli.

Bu karşılaştırma method/path seviyesindedir; permission hücrelerinin doğruluğunu veya çalışan API davranışını kanıtlamaz.

## 5. Belirsizlik bırakmamak için kapatma protokolü

Bir madde yalnızca şu kanıtlardan uygun olanları üretince `CLOSED-DOC` sayılabilir:
1. Tek bir kanonik kural metni.
2. Kaynak ERD alanı/ilişkisi.
3. İlgili endpoint ve DTO alanları.
4. Yetki kararı.
5. Transaction/audit/idempotency davranışı.
6. Başarı ve hata durumları için test kimlikleri.
7. Diğer kaynaklarda çelişen aktif metin bulunmadığının gösterilmesi.

Bir iş kararı proje sahibine aitse `OPEN-OWNER-DECISION` olarak kalır; eksik kanıt `PASS` yapılmaz. Runtime kanıtı gerektiren maddeler, ancak uygulama ve test ortamı hazır olduğunda `NOT-RUNTIME-VERIFIED` durumundan çıkarılabilir.

## 6. Kesinlikle yapılmayan işlemler

- Alembic migration dosyası oluşturulmadı.
- MySQL veritabanı oluşturulmadı/değiştirilmedi.
- ORM modelleri veya API kodu değiştirilmedi.
- Cilt 1'in migration'a hazır olduğu iddia edilmedi.

## 7. Sonraki somut iş

Cilt 1.38, Cilt 1.2 ERD'nin her tablo ve kolonunu ayrı satırlı, kaynak bölümü işaretli bir envantere dönüştürmeli; ardından her kolonun DTO ve workflow kullanımı eşlenmelidir. ERD metninden otomatik çıkarılan isimler doğrulanmadan “tam” olarak etiketlenmemelidir.
