# Harici veri kaynakları

İndirme tarihi: 2026-10-25 (Europe/Istanbul)

Bu klasördeki dosyalar kaynağından indirildi; sentetik kayıt eklenmedi. Her iki dosya da toplu/özet veri düzeyindedir. **Model 2 bağımsız test veya eğitim kümesi değildir.** Hiçbiri hayvan bazında karkas ağırlığı ile sekiz Model 2 çıktısını eşleştirmiyor.

| Dosya | Orijinal kaynak | İçerik ve veri düzeyi | Lisans | SHA-256 |
|---|---|---|---|---|
| `ireland_beef_kill_figures_2020_2024_aggregate.csv` | [DAFM National beef kill figures — doğrudan CSV](https://opendata.agriculture.gov.ie/dataset/75d76c93-c6b7-4e10-8842-f2f3320dc9ae/resource/e5368324-35c0-4b0d-95ee-25c9e6e59082/download/2_2020_2024.csv), [veri kataloğu](https://opendata.agriculture.gov.ie/dataset/national-beef-kill-figures) | 30.12.2019–23.09.2024 haftalık, sınıf bazında sığır kesim adedi. 1.735 CSV satırı; hayvan ağırlığı veya parça verisi içermez. | Kaynakta CC BY 4.0. Atıf: Department of Agriculture, Food and the Marine (Ireland), National beef kill figures. | `708640C1E1C239ACF4A8BD1542B795AB68278DC40DF06DF4DFEDC0299813469D` |
| `steakpedia_field_data_aggregate.csv` | [Steakpedia Field Kitchen field data — doğrudan CSV](https://steakpedia.com/field-data/steakpedia-field-data.csv), [yöntem/lisans sayfası](https://steakpedia.com/field-data/) | Sayfa, 1 Temmuz–17 Ekim 2026 arasında 279 kasaplık sheet ve 1.604,6 kg et ölçüldüğünü bildiriyor. İndirilen CSV 8 kesim türü için toplu satırlardır; sheet başına ham gözlem, hayvan/karkas kimliği veya karkas ağırlığı yoktur. Bu gerçek ölçümlerden yayımlanmış bir kesim özetidir, bireysel test verisi değildir. | CC BY 4.0. Atıf: Steakpedia Field Kitchen (2026), “Steakpedia field data: measured beef yields by cut”, https://steakpedia.com/field-data/ | `4849A9D9C17A8461F5CCE81C83370D581B49EA55F8D03A97988ABA7B0AAF590D` |

## Teste alınmayan, indirilemeyen veya erişim bekleyen kaynaklar

- Güney Kore KAPE/data.go.kr: [API kataloğu](https://www.ekape.or.kr/contents/list.do?menuId=menu166539), [data.go.kr hizmeti](https://www.data.go.kr/data/15058822/openapi.do) ve [sertifika numarası sorgu hizmeti](https://www.data.go.kr/data/15057101/openapi.do?recommendDataYn=Y). Katalogda sığır derecelendirme sertifika kayıtları ve sertifikaya bağlı et parçası/yan ürün bilgisi bulunuyor. REST/XML çağrısı için data.go.kr hesabı ve servis anahtarı gerekiyor. Bu çalışma ortamında anahtar olmadığından API'ye istek gönderilmedi ve dosya indirilmedi. Kamu eseri tür 1 atıf koşulu ve ücretsiz erişim bilgisi API sayfasında; kota/erişim koşullarını çağrı tarihinde tekrar kontrol edin.
- Kore Hanwoo makaleleri: [50.227 kayıt](https://www.mdpi.com/2076-2615/16/1/136) ve [403 hayvan](https://pmc.ncbi.nlm.nih.gov/articles/PMC8819321/). Makale tabloları/sonuçları erişilebilir; ham kayıt için API veya makul talep yazara yönlendiriyor. Bireysel dosya indirilmedi. Makalenin açık lisansını ham veri lisansı saymayın.
- İrlanda [54.250 hayvanlık kesimhane araştırması](https://pmc.ncbi.nlm.nih.gov/articles/PMC7200582/) kesim profilleri içeriyor, fakat açık ek ham satır dosyası bulunmadı; makale ekindeki kesim listesi ham kayıt değildir. Ticari veri erişimi/lisansı doğrulanmalı.
- Türkiye [311 Holstein boğa makalesi](https://dergipark.org.tr/en/pub/kvj/article/390226?issue_id=37070): bireysel ölçümler araştırmada kullanılmış olsa da erişilebilir makale tabloları grup ortalamalarıdır. 311 hayvan için eşleşmiş CSV/ham dosya ve açık veri lisansı bulunmadı.
- [Steakpedia sayfası](https://steakpedia.com/field-data/) her gelen parçanın ve porsiyonların tartıldığını, yağ/trim/fire türlerinin kaydedildiğini açıklar; ancak açık CSV bu sheet kayıtlarını değil kesim başına özet sayıları yayımlar. Tam sheet dosyaları kamuya açık bağlantıda sunulmamıştır.
- [CORA DATA2868](https://doi.org/10.34810/DATA2868) metadata'sı CC BY 4.0 olan tek sürü örneğini tarif eder; bu denetimde dosya içeriği indirilebilir şekilde doğrulanmadı ve kesim hedeflerini içermiyor.
- GitHub, Kaggle, Zenodo ve Figshare taramasında sekiz Model 2 hedefi ve aynı hayvanın karkas girdisini içeren, lisansı/indirilebilir ham dosyası doğrulanmış uygun veri kümesi bulunmadı. [CowDatabase3 GitHub deposu](https://github.com/ruchaya/CowDatabase3) karkas verileri içerir ancak hedef parça çıktılarıyla eşleşmez; indirilmedi.

Herhangi bir dosya test setine alınmadan önce aynı anonim hayvan kimliğinde karkas girdisi ve hedef ölçümleri, fiziksel kesim standardı, sıcak/soğuk tartım aşaması, birim, lisans ve kalite kontrolleri doğrulanmalıdır. Toplu tablo ortalamalarını bireysel gözleme dönüştürmeyin.



## LambDataNested — gerçek kuzu karkas ölçümleri (2026-10-25 incelemesi)

Kaynak dosya `lamb_data_nested.rda` orijinal RDA biçiminde saklandı. Kaynak: [thoree/stat340 GitHub adresi](https://github.com/thoree/stat340), güncel depo `thoree/BIAS.data`; [doğrudan RDA dosyası](https://raw.githubusercontent.com/thoree/BIAS.data/04df4127bdf8db2d5b795c71c3259a6f8eec915e/data/LambDataNested.rda); [değişken açıklaması](https://rdrr.io/github/thoree/stat340/man/LambDataNested.html). Paket açıklaması bunun kesimhanede tartılmış gerçek 240 kuzu karkası olduğunu, 30 çiftlikten her birinde 8 kuzu bulunduğunu ve ırkın kaydedildiğini söyler. Kaynak, Animalia AS tarafından yönetilen Sauekontrollen veri tabanı ve Lars Erik Gangsei'dir.

| Dosya | Boyut | SHA-256 | İndirme | Lisans |
|---|---:|---|---|---|
| `lamb_data_nested.rda` | 912 bayt | `AC50A0BA05D8272CA19951DF281831F06BB903CF90ADBCB0D6E6837B8BC36C2C` | 2026-10-25 | Paket `DESCRIPTION`: MIT + file LICENSE; dataset'e ayrı lisans yazılmamış. Ayrıntı/korunan lisans metinleri: `stat340_LICENSE`, `stat340_LICENSE.md`. |
| `stat340_LICENSE` | 43 bayt | `1B7ED92F0D570656E8763F98BE1DB575D6F809E267749AB0CF6C2C2B5851EE13` | 2026-10-25 | Kaynak paketin LICENSE metadata dosyası. |
| `stat340_LICENSE.md` | 1.072 bayt | `773C8C612990B7467E12AF0A12C42BD31CF39AD95F2DCBA0E941DDED95ECAD1B` | 2026-10-25 | Kaynak depodaki MIT lisans metni. |

Şema: `Farm` (character, 30 çiftlik grubu), `Breed` (character, beş ırk) ve `Carcase_weight` (numeric, kg). İçerik 240×3; her sütunda 0 eksik; her çiftlikte 8 kayıt, her ırkta 48 kayıt; karkas ağırlığı aralığı 8,2–30,4 kg. Tekil hayvan ID'si, sıcak/soğuk tartım aşaması ve parça ölçümü bulunmuyor. Model 2'nin sekiz hedefinin hiçbiri bu dosyada yoktur; bağımsız test ve MAE/RMSE/R² hesaplanmamıştır. Ayrıntılı şema, eşleme ve değerlendirme kararı [lamb_data_incelemesi.md](../reports/lamb_data_incelemesi.md) içindedir.

Lisans notu: kaynak R paketi MIT + file LICENSE beyan ediyor; veri belgesinde ayrıca veri lisansı yok ve GitHub lisans algılayıcısı `NOASSERTION` döndürüyor. Veri kaynağı üçüncü taraf olarak tanımlandığından daha geniş yeniden dağıtım veya türev kullanım öncesinde sağlayıcı hakları ayrıca teyit edilmeli.


## RefData_2019.xlsx — gerçek Hanwoo karkas ve kesim ölçümleri (2026-10-26)

İndirilen dosya: <code>RefData_2019.xlsx</code>, kaynak [GitHub arşivi](https://github.com/collinswakholi/Image-Analysis-Beef-Yield-Estimation), sabit commit <code>0a48e3faee973d94362ae2b6090e7271d8ee2714</code>. Doğrudan dosya: [raw XLSX](https://raw.githubusercontent.com/collinswakholi/Image-Analysis-Beef-Yield-Estimation/0a48e3faee973d94362ae2b6090e7271d8ee2714/RefData_2019.xlsx). Boyut 231.708 bayt; SHA-256 <code>A3B7B7DCB73EA18E4A9B7406DAA2C24BA7C76018040F5F60E2E100B8D804F686</code>; indirme tarihi 2026-10-26.

Çalışma kitabında 17 sayfa ve sayfa başına 134 kayıt vardır; <code>date</code> anahtarları karkas, kesim ve kemik sayfaları arasında bire bir örtüşür. Benzersiz <code>SN</code> ve tarih alanları 134 karkas örneği gösterir. On ana kesim için <code>total</code>, <code>fat</code>, <code>lean</code> kg değerleri; karkas ağırlığı, LMP ve ek kemik/kuyruk ölçümleri bulunur. Eksik hücre ve yinelenen satır görülmedi. İki LMP sıfırı şüpheli olarak raporlandı; düzeltilmedi. İlgili makalede 140 hayvan raporlanırken workbook’ta 134 satır var.

**Model 2 bağımsız testine alınmadı:** sekiz hedefin hiçbiri için bire bir ve fiziksel tanımı doğrulanmış eşleşme yoktur. <code>but_kg</code>, <code>sirt_kg</code>, <code>kaburga_kg</code>, <code>kemik_yag_sinir_kg</code> kısmi adaydır; bunların bileşik kesim sınırları Model 2’de tanımlanmamıştır. Diğer hedeflerle eşleşme bulunmadı. Metrik hesaplanmadı. GitHub deposunda veri lisansı belirtilmemiştir; yeniden dağıtım/türev kullanım izni belirsizdir.

Ayrıntılar ve sayfa şemaları: [refdata_2019_incelemesi.md](../reports/refdata_2019_incelemesi.md). İlgili yayın: Wakholi ve ark. (2022), [Biosystems Engineering makalesi](https://www.sciencedirect.com/science/article/pii/S153751102200085X), DOI <code>10.1016/j.biosystemseng.2022.04.008</code>.
