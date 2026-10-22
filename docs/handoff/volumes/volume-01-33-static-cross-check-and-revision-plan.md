# Cilt 1.33 — Statik Çapraz Kontrol Bulguları ve Düzeltme Planı

**Tarih:** 22 Ekim 2026  
**Durum:** Statik metin taraması yapıldı; dokümanlar arası çelişkiler saptandı. Cilt 1 kapatılmaya hazır değil.  
**Yöntem:** Markdown dokümanları karşılaştırıldı. SQLAlchemy metadata, gerçek MySQL, oluşturulmuş OpenAPI çıktısı veya CI testleri çalıştırılmış değildir.

## 1. Sonuç

Cilt 1.31 toplu onayı karar önerilerini normatif hale getirdi; fakat eski ciltlerde ters düşen ifadeler var. Cilt 1.32 karar önceliği notu eklendi. Bu not karar önceliğini netleştirir, her alan/endpoint'in tam revize edildiğini veya runtime uyumluluğunun kanıtlandığını göstermez.

## 2. Bulgular

| ID | Alan | Statik bulgu | Durum | Gerekli düzeltme/kanıt |
|---|---|---|---|---|
| XCHK-001 | Auth token | Cilt 1.3/1.4 eski metinlerinde “refresh token yok, access 30 dakika”; onaylı kararda access 15 dakika + refresh 7 gün ve rotation var. | CONFLICT | Auth endpoint/DTO örneklerini düzelt; refresh, revoke, reuse testleri ekle. |
| XCHK-002 | Health | Cilt 1.3'te `/api/v1/health/live` ve `/api/v1/health/ready`; onaylı SEC-09 kökte `/health/live` ve `/health/ready`. | CONFLICT | OpenAPI ve izin matrisi kök health yollarıyla hizalansın; anonim erişim ve 200/503 testleri. |
| XCHK-003 | Expiry policy | Cilt 1.2 lotta `expiry_date` uygulanabilirlik der; ürün düzeyindeki `requires_expiry_date` alanının şemadaki varlığı doğrulanmalı. | MISSING/VERIFY | Ürün kartı ve create-lot DTO kontrolü; migration yapmadan dokümanda işaretle. |
| XCHK-004 | BY_VALUE | Cilt 1.2/1.23 eski metinleri BY_VALUE fire maliyetini açık bırakıyor; onaylı karar waste `allocated_cost=0`, maliyet yalnız değer taşıyan stok çıktılarında. | CONFLICT | Allocation kuralı, DTO ve acceptance tests güncellensin. |
| XCHK-005 | BY_WEIGHT | Cilt 1.2/1.5'te fire formülü açık; onaylı karar tüm ölçülen kategoriler ve son satır residual kuralı. | CONFLICT | CUT+BYPRODUCT+WASTE ve deterministic residual testleri. |
| XCHK-006 | Tolerans/birim | Cilt 1.5 eski metni toleransı açık gösteriyor; onaylı karar kg canonical, g/kg conversion, tolerance 0 kg. | CONFLICT | Workflow/DTO'da variance ve yetkili açıklama davranışı. |
| XCHK-007 | Waste reason | Onaylı DATA-05 altı reason code belirledi; enum/DTO/DB karşılaştırması kanıtlanmadı. | MISSING/VERIFY | Enum, DTO, constraint ve OTHER açıklama testi. |
| XCHK-008 | Idempotency | Satışta key zorunlu; dispatch de key zorunlu görünüyor. API-02 diğer kritik POST'larda key veya güvenli state-conflict yaklaşımını endpoint bazında ister. | CROSSCHECK_REQUIRED | Her endpoint için bir tekrar-güvenliği stratejisi matrisi. |
| XCHK-009 | Audit transaction | API-01 kritik işlemle audit'in aynı transaction'da olmasını ve audit hatasında rollback'i ister; WF-01–WF-10 eşlemesi eksik. | CROSSCHECK_REQUIRED | Her kritik workflow için audit transaction ve rollback testi. |
| XCHK-010 | Permissions | Cilt 1.9 canonical kaynak; endpoint, permission key ve test ID kapsama sayımı henüz yapılmadı. | NOT_VERIFIED | Endpoint matrisi ve negatif rol testleri. |
| XCHK-011 | Web security | Cilt 1.27/1.29 auth kararlarını “değerlendirilecek/PROPOSED” gösteriyor; tek origin + HttpOnly cookie + CSRF artık onaylı. | CONFLICT | Deployment, cookie, CSRF, trusted proxy ve HTTPS testleri. |
| XCHK-012 | Runtime | ORM metadata, MySQL schema veya OpenAPI runtime çıktısı karşılaştırılmadı. | NOT_RUNTIME_VERIFIED | Uygulama sonrası otomatik diff/test çalıştır. |

## 3. BY_VALUE fire maliyetinin kesin yorumu

Cilt 1.31'in onaylanan önerisi `BY_VALUE` modunda `butchering_waste_records.allocated_cost = 0` ve toplam maliyetin değer taşıyan stok çıktıları arasında dağıtılmasıdır.
- **BY_WEIGHT:** fire ölçülmüş ağırlık payıyla maliyet alır.
- **BY_VALUE:** fire maliyeti sıfırdır; fire ağırlığı kütle dengesi/audit'te kalır.
- Her iki yöntemde `SUM(output allocated_cost) + SUM(waste allocated_cost) = total_purchase_cost` sağlanır.
- BY_VALUE altında değer taşıyan stok çıktısı yoksa işlem tamamlanamaz; otomatik BY_WEIGHT fallback yoktur.

## 4. Cilt 1'i kapatmak için kalan işler

1. Cilt 1.2 ERD alanlarını Cilt 1.3 request/response DTO ve Cilt 1.4 contract testleriyle alan alan eşleştir.
2. Cilt 1.5 WF-01–WF-10'u Cilt 1.19 state/transition/side effect registry ile birebir eşleştir.
3. Cilt 1.8/1.9/1.20 auth/permissions, Cilt 1.21 error/idempotency ve Cilt 1.24 acceptance testlerini onaylı kararlara göre hizala.
4. Cilt 1.17/1.23'te kapanmış kararları OPEN göstermeyi bırak; yalnız teknik doğrulama gerektirenleri VERIFY bırak.
5. Test ID'li güncel crosswalk üret. Runtime test edilmemiş konular NOT_RUNTIME_VERIFIED kalmalı.
6. Ardından Cilt 1 kapanış raporu oluştur; migration kapısı kapalı kalır.

## 5. Migration öncesi izin kapısı

**Migration üretme/çalıştırma veya DB oluşturma/değiştirme yapılmayacak.** Önce Cilt 1.2 tablo/alanları ile Cilt 1.5 WF-01–WF-10 kontrol edilip ayrı bir özet sunulmalı. Kullanıcıdan ayrıca açık izin alınmadan migration dosyası üretilemez.

### Tarihsel kayıt uyarısı (Cilt 1.34)
Bu rapordaki eski token/health/BY_VALUE ifadeleri tarihsel bulgudur; güncel normatif sözleşme olarak kullanılmamalıdır. Cilt 1.31/1.32 onayları ve Cilt 1.34 revizyonları önceliklidir.
