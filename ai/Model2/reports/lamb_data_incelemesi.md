# LambDataNested — gerçek veri incelemesi ve bağımsız test kararı

İnceleme ve indirme tarihi: 2026-10-25 (Europe/Istanbul)

## Kısa cevap

- **Gerçek hayvan kaydı:** Paket belgesine göre 240 kuzu karkası ölçümü. Dosyada hayvan düzeyinde benzersiz ID yok; 240 sayısı yayımlanan dataset açıklamasına ve 240 satıra dayanıyor.
- **Çiftlik:** 30 çiftlik grubu (`Farm1`–`Farm30`), her grupta 8 satır. `Farm` hayvan kimliği değildir.
- **Karkas ağırlığı:** Evet. `Carcase_weight`, kaynakta kg olarak tanımlı; ölçüm aralığı 8,2–30,4 kg. Sıcak/soğuk karkas aşaması ve tartım protokolü belirtilmemiş.
- **Model 2'nin sekiz hedefi:** Hiçbiri ölçülmemiş veya dosyada bulunmuyor.
- **Bağımsız tahmin değerlendirmesi:** Yapılmadı. Hedef bazında uygun gerçek etiket sayısı 0; MAE, RMSE ve R² hesaplanmadı. Model 2'nin bu veriyle güvenilir biçimde test edilebilen hedefi **yok**.

## Kaynak ve gerçek ölçüm niteliği

İstenen [thoree/stat340 GitHub deposu](https://github.com/thoree/stat340) GitHub API'sinde güncel paket deposu olan [thoree/BIAS.data](https://github.com/thoree/BIAS.data) adına yönleniyor. Paket sürümü `1.1`; indirme anındaki varsayılan dal `master`, HEAD commit `04df4127bdf8db2d5b795c71c3259a6f8eec915e`.

[LambDataNested kaynak belgesi](https://rdrr.io/github/thoree/stat340/man/LambDataNested.html) ve [paketteki veri kod kitabı](https://rdrr.io/github/thoree/stat340/src/R/LambDataNested.R), bunun kesimhanede tartılmış 240 kuzu karkasının gerçek verisi olduğunu, 30 çiftlikten her birinden sekiz kuzu bulunduğunu ve ırkın her kuzu için kaydedildiğini söylüyor. Kaynak, veriyi Animalia AS tarafından yönetilen Norveç Sauekontrollen veri tabanına bağlıyor ve Lars Erik Gangsei'nin sağladığını belirtiyor. Dolayısıyla bu sentetik/eğitim amaçlı üretilmiş kayıt değildir; yayımlanan paketteki ölçüm tablosudur.

Bu doğrulama dataset açıklaması ve indirilen binary dosyadaki yapıya dayanır. Bu kayıtta ayrı hayvan kimliği, tartım tarihi, kesimhane adı/ID'si veya orijinal tartım fişi sunulmuyor; fiziksel kaynağın bireysel kayıtları sağlayıcıdan ayrıca doğrulanmadı.

## İndirilen dosyalar ve lisans

| Dosya | Kaynak URL | İndirme tarihi / boyut | SHA-256 | Kullanım ve lisans durumu |
|---|---|---|---|---|
| `ai/Model2/data/external/lamb_data_nested.rda` | [GitHub doğrudan dosya](https://raw.githubusercontent.com/thoree/BIAS.data/04df4127bdf8db2d5b795c71c3259a6f8eec915e/data/LambDataNested.rda); [paket sayfası](https://github.com/thoree/stat340) | 2026-10-25; 912 bayt | `AC50A0BA05D8272CA19951DF281831F06BB903CF90ADBCB0D6E6837B8BC36C2C` | Kaynak R paketi `DESCRIPTION` içinde `MIT + file LICENSE` beyan ediyor. Dataset belgesinde veri için ayrı lisans belirtilmemiş. Repo lisansı MIT olsa da veri kaynağı üçüncü taraf Animalia/Sauekontrollen olduğundan bağımsız veri yeniden dağıtım hakkı açıkça ayrıştırılmamış; daha geniş türev/dağıtım için sağlayıcı koşullarını teyit edin. |
| `ai/Model2/data/external/stat340_LICENSE` | [Kaynak LICENSE dosyası](https://raw.githubusercontent.com/thoree/BIAS.data/master/LICENSE) | 2026-10-25; 43 bayt | `1B7ED92F0D570656E8763F98BE1DB575D6F809E267749AB0CF6C2C2B5851EE13` | Paket `MIT + file LICENSE` tanımı için yıl ve hak sahibi metaverisi: 2021, Thore Egeland. |
| `ai/Model2/data/external/stat340_LICENSE.md` | [Kaynak MIT metni](https://raw.githubusercontent.com/thoree/BIAS.data/master/LICENSE.md) | 2026-10-25; 1.072 bayt | `773C8C612990B7467E12AF0A12C42BD31CF39AD95F2DCBA0E941DDED95ECAD1B` | Paket deposundaki MIT izin metninin kopyası. Bu paket lisansı dataset için ayrıca yazılmış bir veri lisansı olarak değerlendirilmedi. |

RDA orijinal biçiminde korundu; satırlar yeniden yazılmadı, sentetik kayıt eklenmedi ve bu dosyadan test CSV'si türetilmedi. RDA, geçici analiz ortamında `pyreadr` ile açıldı; proje bağımlılıklarına paket eklenmedi. Rscript ortamda kurulu değildi.

## Veri şeması ve içerik doğrulaması

Kaynak kod kitabındaki veri tipi ve anlam birincil tanım kabul edildi; içeriği okurken oluşan Python dtype ayrıca gösterilmiştir.

| Kaynak sütunu | Kaynak veri tipi | Dosyayı okurken alınan dtype | Satır sayısı / eksik | Birim | Kaynakta tanımlanan anlam |
|---|---|---|---:|---|---|
| `Farm` | character | object/string | 240 / 0 | Yok; kategorik kimlik | 30 çiftlikten biri (`Farm1`–`Farm30`). Her çiftlikte sekiz kuzu gözlemi vardır. Hayvan ID'si değildir. |
| `Breed` | character | object/string | 240 / 0 | Yok; kategorik | Her kuzu için kaydedilen koyun ırkı. Dosyada beş etiket bulunur. |
| `Carcase_weight` | numeric | float64 | 240 / 0 | kg | Kuzu karkas ağırlığı; kaynak kod kitabı gözlenen aralığı 8,2–30,4 kg olarak verir. Ağırlığın sıcak/soğuk aşaması belirtilmemiştir. |

Veri dosyasından doğrulanan yapı:

- Boyut: **240 satır × 3 sütun**; tüm sütunlarda eksik değer sayısı 0.
- `Farm`: 30 farklı grup; her birinde tam 8 kayıt.
- `Breed`: beş kategori ve her kategoride 48 kayıt: `Kvit spaelsau`, `Norsk kvit sau (NKS)`, `Texel`, `Norsk pelssau`, `Gammalnorsk spaelsau`.
- `Carcase_weight`: 110 farklı ağırlık değeri; minimum 8,2 kg, maksimum 30,4 kg, ortalama 18,395 kg, medyan 18,25 kg, örnek standart sapma 3,5368 kg.
- `animal_id`, doğum/kesim yaşı, cinsiyet, kesim tarihi, kesimhane ID'si, canlı ağırlık, ölçüm aşaması veya karkas parçası sütunu yok.

Bu özet, 240 ölçümün her birinin kaynakta tanımlanan satır gözlemi olduğunu doğrular; dosya hayvanı çiftlik grubu dışında tekil olarak takip etmeye izin vermez.

## Model 2 ile uyum

Model 2'nin mevcut şeması `hayvan_turu`, `karkas_agirligi_kg` girdilerini ve aşağıdaki sekiz kg çıktısını tanımlar. Veri, kuzu türü ve karkas ağırlığıyla **girdi düzeyinde kısmi uyumludur**: tür `kuzu` olarak yorumlanabilir, `Carcase_weight` birimi kg'dır; ancak veri ağırlığın sıcak/soğuk aşamasını açıklamaz ve ırk Model 2 girdisi değildir. Bu girdi benzerliği bir performans değerlendirmesi değildir.

| Model 2 hedefi | Sınıflandırma | LambDataNested'de dayanak |
|---|---|---|
| `but_kg` | Eşleşme yok | But veya arka bacak tartımı yok. |
| `sirt_kg` | Eşleşme yok | Sırt kesimi tartımı yok. |
| `omuz_kg` | Eşleşme yok | Omuz tartımı yok. |
| `kaburga_kg` | Eşleşme yok | Kaburga tartımı yok. |
| `kiyma_kg` | Eşleşme yok | Kıyma veya kıymalık et tartımı yok. |
| `yan_urun_kg` | Eşleşme yok | Yan ürün/sakatat ağırlığı yok. |
| `kemik_yag_sinir_kg` | Eşleşme yok | Kemik, yağ ve sinir bileşen tartımı yok. |
| `fire_kg` | Eşleşme yok | Fire/trim/işleme kaybı ölçümü yok. |

Karkas ağırlığı tek başına parça çıktısı değildir. Ağırlık farkından hedef, toplam verim veya fire türetilmedi; hedeflerin toplanabilir/çakışmasız olduğu da varsayılmadı.

## Bağımsız test kararı

**Tahmin testi yapılmadı ve metrik üretilmedi.** Test edilebilir hedef sayısı sıfırdır; gerçek ölçülmüş hedef sütunu olmadığından `MAE`, `RMSE` ve `R²` hesaplamak mümkün değildir. Karkas ağırlığı kayıtlarını yalnız model girdisi olarak modele verip bir çıktı görmek bağımsız değerlendirme sayılmaz.

Bu dosya, model performans testinde kullanılamaz. Yalnızca Norveç kuzularında 8,2–30,4 kg aralığında karkas girdisi bulunduğunu ve çiftlik yapısını gösteren tanımlayıcı girdi/veri kapsamı kontrolünü destekler. Model 2'nin sekiz hedefinin hiçbirinde güvenilir biçimde test sağlayamaz.

Eğer ileride aynı hayvanlar için hedef tartımları edinilirse, `Farm` kümelenmesi nedeniyle test ayırımı çiftlik bazında yapılmalı; bir çiftliğin hayvanları train ve test taraflarına rastgele bölünmemelidir. Bu dosyada hayvan ID'si olmadığı için tekil hayvan eşleştirmesi yine veri sağlayıcısından doğrulanmalıdır.

## Sonraki adım

Animalia/Sauekontrollen veri sağlayıcısından veya veri katkıcısından aynı 240 kuzuya bağlanabilen, tanımlı kesim standardında tartılmış sekiz hedefin bulunup bulunmadığını sorun. İstenmesi gereken alanlar: anonim ama stabil hayvan ID'si, çiftlik ID'si, ırk, karkas ölçüm aşaması/zamanı, kesim standardı, sekiz ayrı gerçek tartım, birimler, eksik kayıt nedenleri ve yeniden kullanım izni. Yalnız eşleşme ve haklar doğrulanırsa bu veriyi ayrı gerçek doğrulama kümesi olarak değerlendirin; Model 2 model/eğitim/API/üretim kilidi bu incelemede değiştirilmedi.
