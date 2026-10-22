# Cilt 1.12 — Cilt 1.11 Revizyon Uygulama Günlüğü

**Tarih:** 22 Ekim 2026  
**Durum:** Dokümantasyon revizyon ekleri işlendi; son tam çapraz kontrol devam ediyor.  
**Migration durumu:** Alembic dosyası oluşturulmadı; MySQL kurulmadı/değiştirilmedi.

## İşlenen belgeler

| Belge | Yapılan güncelleme |
|---|---|
| Cilt 0 | Revizyon durumu ve migration öncesi onay kapısı eklendi. |
| Cilt 1.2 | Fire nullability, üretim tüketimi, stok çıkışı sahipliği, nullable semantiği, düzeltme/ters kayıt ve ağırlık toleransı kuralları eklendi. |
| Cilt 1.3 | Token/health, roller, stok etkileri, recall, fire, hata zarfı ve idempotency için kanonik davranışlar eklendi. |
| Cilt 1.4 | DTO/contract test gereksinimleri, nullability, idempotency, izin ve recall negatif testleri eklendi. |
| Cilt 1.5 | Üretim, fire, sevkiyat, recall, tolerans ve ters kayıt workflow kuralları eklendi. |
| Cilt 1.6 | Servis transaction sınırları, idempotency, güvenlik ve hata sözleşmesi güncellendi. |
| Cilt 1.7 | Migration ön koşul kontrol listesi ve seed/test beklentileri eklendi; migration dosyası oluşturulmadı. |
| Cilt 1.8 | JWT süresi, refresh/logout, rol izinleri ve health güvenliği eklendi. |
| Cilt 1.9 | Endpoint izinlerinin kanonik varsayılanları ve açık migration kapıları eklendi. |
| Cilt 1.10 | CC-01–CC-16 için revizyon haritası ve kalan kapılar eklendi. |
| DEC-001 | `requestId` örneği `request_id` olarak normalize edildi; onaylı kararların anlamı değişmedi. |
| README | Dokümantasyon durumu ve migration sınırı güncellendi. |

## Kanonik hale getirilen kurallar

1. Access token 30 dakika; refresh token MVP'de yok; logout istemci token'ını temizler.
2. Genel stok düzeltme yalnızca ADMIN; sevkiyat oluşturma/dispatch ADMIN ve SALES.
3. AI tahmin başlatma ADMIN/OPERATOR; sonuç okuma ADMIN/OPERATOR/TRACEABILITY_MANAGER/VIEWER.
4. Üretim girdisi stok düşümü tamamlamada, gerçek tüketim miktarıyla yapılır; IN_PROGRESS tek başına OUT üretmez.
5. Recall aktivasyonu MVP'de senkron/atomik; RESOLVED lot blokajını otomatik kaldırmaz.
6. Fire ölçüm satırı stokta izlenen çıktıdan ayrıdır; yalnızca fire satırında ürün/lot nullable olabilir.
7. Ağırlık toleransı sayısal olarak TBD; kaynakta olmayan değer uydurulmaz.
8. Satış/sevkiyat için çift fiziksel OUT yasaktır. Dispatch'in tek OUT sahibi olması önerilen varsayılandır; son çapraz kontrolde teyit edilecektir.
9. Kritik komutların tekrar istek davranışı endpoint bazında idempotency veya deterministik conflict ile korunur.
10. Hata zarfı kök seviyede `request_id` kullanır.

## Kalan kontrol işleri

- Cilt 1.2 tablo/kolon/nullability listesi ile DTO alanlarını tek tek eşleştirmek.
- Cilt 1.3 endpoint matrisi ile Cilt 1.8/1.9 izinlerini tek tek doğrulamak.
- Enum ve error-code örneklerinin tamamını registry ile karşılaştırmak.
- Dispatch'in tek stok OUT sahibi olduğu varsayımını son workflow kontrolünde doğrulamak.
- Web cookie/CSRF/CORS ayrıntısını ve liveness erişim biçimini implementasyondan önce kesinleştirmek.
- Düzeltme/ters kayıt ve unblock için son alan/permission adlarını eşleştirmek.
- Bu kontrol tamamlandıktan sonra ayrı bir rapor sunmak; migration dosyası oluşturmak için ayrıca açık onay beklemek.
