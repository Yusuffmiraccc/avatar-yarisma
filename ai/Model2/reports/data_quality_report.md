# Model B veri kalitesi ve köken denetimi

Denetim tarihi: 24.10.2026. İncelenen sentetik ham dosya `data/raw/synthetic/ModelB_Sentetik_Parcalama_Verisi.csv` ve mevcut processed bölmeleridir. Gerçek bireysel saha verisi bulunmadı; sonuçlar sentetik dosya yapısına ilişkindir.

## Köken ve bölmeler

- Ham CSV: 1.200 kayıt; `veri_turu=SENTETIK` tüm kayıtlarda; 400 kuzu, 400 koyun, 400 dana.
- Split: 840 train / 180 validation / 180 test. Her split `SENTETIK_SIMULASYON` olarak işaretli. Kimlik kümeleri ayrık ve toplamda 1.200 benzersiz satır.
- Seed ve tür bazlı bölme bilgisi kaynak metodoloji dosyasında 20261024 olarak belirtilmiş; yeniden bölme yapılmadı.
- Saha verisi için `data/raw/measured/` boş hedef dizin olarak oluşturuldu; bireysel kayıt içermez. Mevcut splitler yalnız sentetik.

## Kalite kontrolleri

| Kontrol | Sonuç | Değerlendirme |
|---|---:|---|
| Ham kayıt / benzersiz kayıt kimliği | 1.200 / 1.200 | Yinelenen tam satır yok; `kayit_id` yinelenmiyor |
| Eksik alan | `yas_ay`: 1.200; `yag_durum_skoru`: 1.200 | Bu iki sütun tüm satırlarda boş; sıfırla doldurulmadı ve feature olarak kullanılmıyor |
| Diğer eksik ham alanlar | 0 | Irk/cinsiyet “bilinmiyor” metniyle kodlanmış; bilinmeyen gerçek özellik sayılmaz |
| Sayısal sonsuzluk | 0 | Sayısal alanlarda ±Infinity görülmedi |
| Negatif ağırlık / hedef | 0 hücre | Karkas ağırlığı 10,47–358,63 kg; hedefler 0 veya pozitif |
| Birim/tür bayrağı | 1.200/1.200 `karkas_agirligi`; hedef adları kg | CSV beyanı tutarlı; gerçek terazi/prosedür doğrulaması yok |
| Bölme ID kesişimi | 0 | Train, validation ve test kimlikleri ayrık |
| Toplam çıktı ve karkas farkı | Maksimum mutlak fark < 1.2e-13 kg | Sentetik dosyada sekiz çıktı toplamı girişe denk gelecek şekilde kurulmuş; bu, gerçek tartım/formül doğruluğu kanıtı değildir |

Tür bazında sentetik karkas aralıkları: kuzu 10,47–27,78 kg; koyun 18,77–41,68 kg; dana 190,10–358,63 kg. Aralıkların gerçek popülasyonu temsil ettiği doğrulanmamıştır.

## Formül ve hedef tanımı sınırı

`toplam_cikis_kg`, sekiz hedef sütununun toplamı olarak; `agirlik_dengesi_farki_kg`, toplam çıktı eksi giriş olarak hesaplanmış ve CSV’de kütle dengesi kapanmıştır. Ancak `but`, `sirt`, `omuz`, `kaburga`, `kiyma`, `yan_urun`, `kemik_yag_sinir` ve `fire` sınırlarının hangi parçalama standardına göre ayrıldığı, kıymanın trim’den türetilip türetilmediği, yan ürün/kemik/yağ/sinir kategorilerinin örtüşüp örtüşmediği saha tanımıyla teyit edilmedi. Dolayısıyla kütle dengesi yalnız simülasyon kurgusunun iç kontrolüdür; gerçek fiziksel muhasebe standardı diye kabul edilemez.

Ham tarihler sentetik tarih alanlarıdır; ölçüm zamanı veya tartım aşaması kanıtı değildir. Canlı ağırlık ve karkas ağırlığı aynı değildir. Eğitim/API girdi alanı yalnız `karkas_agirligi_kg` olarak tanımlıdır.

## Kullanılmayan kaynaklar

`published_aggregate` içindeki 8 satırlık dana ve 3 satırlık kuzu tabloları toplu yayın/site özetidir. Bireysel örnek olmadığı için eğitim, split veya metrik hesaplamasına katılmadı. Ayrıntılı kaynak/lisans durumu `docs/KAYNAKLAR_LISANSLAR.md` içindedir.
