# RefData_2019.xlsx — Model 2 gerçek veri incelemesi

**İnceleme tarihi:** 2026-10-26 (Europe/Istanbul)
**Karar:** Dosya gerçek, hayvan bazında eşleşmiş karkas ve kesim ölçümleri içeriyor; ancak Model 2’nin sekiz hedefiyle tanımı doğrulanmış bire bir eşleşme bulunmadığından bu çalışma için bağımsız test seti olarak uygun değildir. Test metriği üretilmedi.

## Kaynak, dosya ve lisans

Dosya, [collinswakholi/Image-Analysis-Beef-Yield-Estimation](https://github.com/collinswakholi/Image-Analysis-Beef-Yield-Estimation) deposunun <code>main</code> dalındaki sabitlenmiş <code>0a48e3faee973d94362ae2b6090e7271d8ee2714</code> commit’inden [RefData_2019.xlsx](https://raw.githubusercontent.com/collinswakholi/Image-Analysis-Beef-Yield-Estimation/0a48e3faee973d94362ae2b6090e7271d8ee2714/RefData_2019.xlsx) olarak indirildi. Dosya, [ai/Model2/data/external/RefData_2019.xlsx](../data/external/RefData_2019.xlsx) altında orijinal XLSX biçiminde saklandı. Bu analiz öncesinde hedef dizinde yerel kopyası bulunmadı.

| Özellik | Değer |
|---|---|
| Dosya boyutu | 231.708 bayt |
| SHA-256 | <code>A3B7B7DCB73EA18E4A9B7406DAA2C24BA7C76018040F5F60E2E100B8D804F686</code> |
| Kaynak Git blob SHA-1 | <code>c27b1475abd8872cce1aacd2b1b28623316d5b3a</code> |
| İndirme tarihi | 2026-10-26 |
| XLSX metadata | Creator <code>Collins</code>; oluşturma 2019-10-22; son değiştirme 2019-11-01 |

Arşivlenmiş depoda veri için ayrı lisans beyanı veya kök <code>LICENSE</code> dosyası tespit edilmedi; GitHub API’sinde de lisans belirtilmiyor. Bu nedenle dosyanın yeniden dağıtım ve türev kullanım lisansı **belirsizdir**. Dosya bu inceleme amacıyla yerel saklandı; lisans izni varsayılmamalıdır.

## Çalışma kitabı ve şema

Çalışma kitabında 17 sayfa vardır. <code>Good_Data</code> 3 başlık satırı kullanır; üç bölüm ayırıcı sütunu boştur. Diğer sayfalarda ilk satır başlık, devamındaki 134 satır veri içerir. Excel’in biçimlendirilmiş boş satır/sütunları <code>max_row</code>/<code>max_column</code> değerlerini büyütebildiğinden aşağıdaki sayımlar içerik taşıyan kayıtlar ve gerçek sütun başlıkları üzerinden yapılmıştır.

| Sayfa | Veri satırı × anlamlı sütun | Sütunlar ve kaynakta görülen tip/birim |
|---|---:|---|
| <code>Good_Data</code> | 134 × 120 dolu alan (123 sütun yerleşimi) | 3 başlıklı düzen. Metadata: <code>SN</code>, <code>date</code>, <code>sex</code>, <code>origin</code>, <code>grade</code> (metin); <code>age</code> (tam sayı; ay), <code>length</code> (sayı; cm), <code>Total</code> (sayı; kg), <code>LMP</code> (sayı; kaynak başlığı <code>lean/total</code>). Bunlara ek olarak sol, sağ ve toplam taraf için 10 ana kesimin her birinde <code>total</code>, <code>fat</code>, <code>lean</code> (sayı; kg); kemik iliği, kuyruk, diz kemiği, diğer kemikler ve kaburga kemiğinde toplam ağırlık (kuyrukta ayrıca yağ/yağsız ağırlık). Birimler üst başlıkta “weight in kg” olarak yazılıdır. 47, 85 ve 123. sütunlar boş bölüm ayırıcılarıdır. |
| <code>Whole_carcass</code> | 134 × 9 | <code>SN</code>, <code>date</code>, <code>sex</code>, <code>origin</code>, <code>grade</code> (metin); <code>age (months)</code> (tam sayı, ay); <code>length (cm)</code> (tam sayı/sayı, cm); <code>carcass weight</code> (tam sayı/sayı, kg); <code>LMP (lean/total)</code> (tam sayı/sayı; kaynakta oran adı, makalede yüzde olarak ifade edilir). |
| <code>Tenderloin</code> | 134 × 4 | <code>date</code> (metin); <code>total</code>, <code>fat</code>, <code>lean</code> (sayı, kg). |
| <code>Sirloin</code> | 134 × 4 | <code>date</code> (metin); <code>total</code>, <code>fat</code>, <code>lean</code> (sayı, kg). |
| <code>Striploin</code> | 134 × 4 | <code>date</code> (metin); <code>total</code>, <code>fat</code>, <code>lean</code> (sayı, kg). |
| <code>Chuckroll</code> | 134 × 4 | <code>date</code> (metin); <code>total</code>, <code>fat</code>, <code>lean</code> (sayı, kg). |
| <code>Fore_shank</code> | 134 × 4 | <code>date</code> (metin); <code>total</code>, <code>fat</code>, <code>lean</code> (sayı, kg). |
| <code>Top_round</code> | 134 × 4 | <code>date</code> (metin); <code>total</code>, <code>fat</code>, <code>lean</code> (sayı, kg). |
| <code>Bottom_round</code> | 134 × 4 | <code>date</code> (metin); <code>total</code>, <code>fat</code>, <code>lean</code> (sayı, kg). |
| <code>Brisket</code> | 134 × 4 | <code>date</code> (metin); <code>total</code>, <code>fat</code>, <code>lean</code> (sayı, kg). |
| <code>Hind_shank</code> | 134 × 4 | <code>date</code> (metin); <code>total</code>, <code>fat</code>, <code>lean</code> (sayı, kg). |
| <code>Ribs</code> | 134 × 4 | <code>date</code> (metin); <code>total</code>, <code>fat</code>, <code>lean</code> (sayı, kg). |
| <code>Bone_marrow</code> | 134 × 2 | <code>date</code> (metin); <code>total</code> (sayı, kg). |
| <code>Tail</code> | 134 × 4 | <code>date</code> (metin); <code>total</code>, <code>fat</code>, <code>lean</code> (sayı, kg). |
| <code>Knee_bone</code> | 134 × 2 | <code>date</code> (metin); <code>Total</code> (sayı, kg). |
| <code>Other_bones</code> | 134 × 2 | <code>date</code> (metin); <code>Total</code> (sayı, kg). |
| <code>Rib_bone</code> | 134 × 2 | <code>date</code> (metin); <code>Total</code> (sayı, kg). |

Kesim sayfalarında birim sütun başlığında tekrar edilmez; kilogram yorumu, <code>Good_Data</code> üst başlığındaki kg açıklaması ve makalenin kesim ağırlıklarını kg cinsinden vermesiyle desteklenir. <code>SN</code> kaynağın verdiği benzersiz tanımlayıcı alanıdır; veri belgesi bunun resmi hayvan numarası mı yoksa örnek/karkas numarası mı olduğunu açıklamaz. Bu nedenle raporda “aday karkas kimliği” olarak ele alınmıştır.

### İlk ve son örnek kayıtlar

Kimlik numaraları rapora kopyalanmamıştır. <code>date</code> değerleri kaynakta bulunan örnek anahtarlardır; <code>_1</code> / <code>_2</code> son eklerinin anlamı kaynakta açıklanmıyor. Ağırlık üçlülerinde sıra <code>total / fat / lean</code>, birim kg’dir.

| Sayfa | İlk örnek (<code>2017_0918_1</code>) | Son örnek (<code>2019_0918_2</code>) |
|---|---|---|
| <code>Good_Data</code> / <code>Whole_carcass</code> | Dişi (암); Sacheon/사천; grade <code>2B</code>; 42 ay; 241 cm; karkas 338,10 kg; LMP 66,63 | Erkek (수); Pyeongtaek/평택; grade <code>2A</code>; 30 ay; 274 cm; karkas 550,70 kg; LMP 64,68 |
| <code>Tenderloin</code> | 7,38 / 1,33 / 6,05 | 10,87 / 2,29 / 8,58 |
| <code>Sirloin</code> | 35,29 / 7,64 / 27,65 | 47,81 / 6,86 / 40,95 |
| <code>Striploin</code> | 11,85 / 2,92 / 8,93 | 14,49 / 3,71 / 10,78 |
| <code>Chuckroll</code> | 16,46 / 1,33 / 15,13 | 43,24 / 1,86 / 41,38 |
| <code>Fore_shank</code> | 25,26 / 5,41 / 19,85 | 42,21 / 7,39 / 34,82 |
| <code>Top_round</code> | 23,99 / 4,22 / 19,77 | 38,57 / 7,55 / 31,02 |
| <code>Bottom_round</code> | 38,04 / 7,78 / 30,26 | 57,87 / 9,91 / 47,96 |
| <code>Brisket</code> | 71,55 / 40,52 / 31,03 | 121,75 / 67,62 / 54,13 |
| <code>Hind_shank</code> | 16,40 / 3,73 / 12,67 | 23,75 / 4,01 / 19,74 |
| <code>Ribs</code> | 47,58 / 2,77 / 44,81 | 72,16 / 10,52 / 61,64 |
| <code>Bone_marrow</code> (<code>total</code>) | 12,31 | 21,88 |
| <code>Tail</code> | 11,30 / 2,82 / 8,48 | 17,72 / 3,65 / 14,07 |
| <code>Knee_bone</code> (<code>Total</code>) | 1,38 | 2,64 |
| <code>Other_bones</code> (<code>Total</code>) | 13,70 | 25,38 |
| <code>Rib_bone</code> (<code>Total</code>) | 5,29 | 8,36 |

## Eksiklik, tekrar, kimlik ve anomali kontrolleri

- Her 17 sayfada 134 dolu kayıt vardır. <code>Good_Data</code> dahil 17 sayfanın tarih anahtarları bire bir eşleşir; anahtar birleştirmesinde eksik veya fazla kayıt yoktur. Bu, 17 × 134 bağımsız hayvan demek değildir: aynı 134 gözlemin aynı karkasları kesim sayfalarında tekrar eden görünümleridir.
- <code>Whole_carcass</code> içinde 134/134 <code>SN</code> ve <code>date</code> benzersizdir. Tekrar edilen tam satır bulunmadı. Kesim sayfalarında <code>date</code> başına tek satır ve tekrar eden tam satır yoktur.
- Boş ölçüm değeri yoktur. <code>Good_Data</code> içindeki 3 boş sütun ve üst başlıklardaki boş hücreler yerleşim ayırıcılarıdır, eksik ölçüm değildir.
- <code>Whole_carcass</code> karkas ağırlığı 238,8–597,9 kg; yaş 17–120 ay; uzunluk 230–295 cm aralığındadır. <code>sex</code> sayımları 55 <code>암</code> (dişi), 43 <code>수</code> (erkek), 36 <code>거세</code> (kastre erkek); <code>origin</code> 28 kategori içerir.
- Çiftlik kimliği alanı yoktur. <code>origin</code> bölge/yer adlarıdır ve kaynak bunu çiftlik numarası olarak tanımlamaz. Makalede örneklerin farklı Kore bölgelerinden geldiği söylenir; çiftlik kümeli ayırma bu dosyadan kurulamaz.
- <code>LMP (lean/total)</code> iki satırda sıfırdır (<code>2019_0722_1</code>, <code>2019_0722_2</code>). Diğer 132 değer dışındakileri düzeltmedim veya silmedim. İlgili makalede LMP aralığı %48–82 olarak raporlandığından bu iki sıfır şüpheli/sentinel olabilir; kaynak açıklaması bulunmadan anlamı doğrulanamaz. Excel’deki toplam aralık 0–74,88’dir.
- Makale örneklemi 140 Hanwoo sığırı olarak bildirirken dosyada 134 eşleşmiş kayıt bulunur. Altı gözlemin neden olmadığı açıklanmıyor; makaledeki 140 sayısı Excel’e ek kayıt olarak varsayılmadı.

## Kaynak kodu, README ve makale ile ölçüm tanımı

Arşiv deposunun README’si çalıştırma sırasını mask çıkarımı, görüntü özellik çıkarımı, <code>preprocess_data.m</code> ve <code>model_carcass2.m</code> olarak verir; depo açıklaması “22 yield parameters” der. Arşivde <code>preprocess_data.m</code> ve bazı modelleme yardımcı MATLAB dosyaları listelense de README’nin çağırdığı <code>model_carcass2.m</code> depo ağacında yoktur. Bu nedenle yayınlanan model kodundan hedef kolonlarının kesin dönüşümünü/kesim çizgilerini yeniden üretmek mümkün değildir. README’deki 22 hedef ifadesi, yayın makalesiyle de tutarlı değildir.

İlgili yayın: Wakholi ve ark., *Deep learning feature extraction for image-based beef carcass yield estimation*, Biosystems Engineering 218 (2022), 78–93, [DOI: 10.1016/j.biosystemseng.2022.04.008](https://www.sciencedirect.com/science/article/pii/S153751102200085X). Makale 140 Hanwoo örneği ve 23 model hedefi açıklar: LMP, sıcak karkas ağırlığı, toplam karkas yağı ve on ana kesimin her biri için toplam ve yağsız ağırlık. Dosyanın 10 kesim sayfasında <code>total</code>, <code>fat</code>, <code>lean</code> alanları vardır; ayrıca beş kemik/yan bileşen sayfası bulunur. Makale hedef listesi, Excel’in her sütununu model hedefi olarak kullandığını kanıtlamaz. Excel’in kesim sayfası başlıkları ölçüm adını verir, ancak kemikli/kemiksiz kapsamı, trim ve kesim sınırlarını tanımlamaz.

Kaynak GitHub arşivi ayrıca örnek toplama ve ölçüm adımlarına ilişkin eksiksiz protokol veya kesim standardı sunmuyor. Makaledeki fiziksel tanımlar ile Model 2 işletme hedeflerini aynılaştıracak kesim standardı mevcut değil. Bu sebeple benzer adları eşdeğer saymadım.

## Model 2 şemasıyla eşleşme

Model 2’de girişler <code>hayvan_turu</code> ve <code>karkas_agirligi_kg</code>; hedefler <code>but_kg</code>, <code>sirt_kg</code>, <code>omuz_kg</code>, <code>kaburga_kg</code>, <code>kiyma_kg</code>, <code>yan_urun_kg</code>, <code>kemik_yag_sinir_kg</code>, <code>fire_kg</code> olarak [Model 2 şemasında](../app/schemas.py) tanımlıdır. <code>Model2/docs/SENTETIK_VERI_KULLANIM_NOTU.md</code> bazı geniş hedeflerin fiziksel sınırlarının işletmece netleştirilmesi gerektiğini de belirtir.

| Model 2 hedefi | Bu workbook’taki gözlenen alanlar | Karar ve gerekçe |
|---|---|---|
| <code>but_kg</code> | <code>Top_round</code>, <code>Bottom_round</code> | **Kısmi aday; doğrudan eşleşme değil.** Bu iki kesim tartılmıştır, ancak Model 2’de “but”un bunların toplamı mı, başka arka bacak kesimlerini de kapsayıp kapsamadığı; kemik/trim sınırı belirtilmemiştir. Toplama yapmadım. |
| <code>sirt_kg</code> | <code>Sirloin</code>, <code>Striploin</code> | **Kısmi aday; doğrudan eşleşme değil.** İki ayrı kesim tartılmış; Model 2 “sırt”ının anatomik sınırları ve bunların birleşim kuralı tanımlı değildir. |
| <code>omuz_kg</code> | Açıkça omuz adlı ölçüm yok; <code>Chuckroll</code> ve <code>Fore_shank</code> ayrı ölçülmüş | **Eşleşme yok.** Bu kesimleri omuz saymak kaynağa dayanmıyor. |
| <code>kaburga_kg</code> | <code>Ribs</code> total/fat/lean; <code>Rib_bone</code> total | **Kısmi aday; doğrudan eşleşme değil.** Kaburga kesimi ölçümü vardır; fakat Model 2 kapsamı, kemik içeriği ve <code>Rib_bone</code> ile ilişki/örtüşme tanımlanmamıştır. |
| <code>kiyma_kg</code> | Kesimlerin <code>fat</code> ve <code>lean</code> değerleri | **Eşleşme yok.** Kıyma veya kıymalık ayrı tartımı yoktur; yağsız et, kıyma ile aynı ürün değildir. |
| <code>yan_urun_kg</code> | Kemik iliği, kuyruk ve kemik kategorileri | **Eşleşme yok.** Kaynak kategorileri Model 2’nin tanımsız yan ürün toplamasıyla aynı değil; sakatat/yan ürün toplamı tanımlanmamış. |
| <code>kemik_yag_sinir_kg</code> | Kesimlerdeki yağ ağırlıkları ve ayrı kemik bileşenleri | **Kısmi aday; doğrudan eşleşme değil.** Yağ ve bazı kemikler ayrı tartılmış; sinir ölçümü yok ve bu bileşenleri Model 2’nin tek bileşik alanına toplayan kaynak tanımı bulunmuyor. |
| <code>fire_kg</code> | Fire, trim veya işlem kaybı alanı yok | **Eşleşme yok.** Üretim kaybı/atık tartımı raporlanmamış. |

Sonuç: **0 bire bir, 4 kısmi, 4 eşleşmesi olmayan hedef.** Kısmi adayları birleştirip yeni ölçüm türetmedim. Model 2’nin sekiz hedefinden hiçbiri bu dosyadan tanımı doğrulanmış şekilde bağımsız test edilemez.

Girdi düzeyinde hayvan türü sığırdır ve modelde <code>dana</code> kategorisi vardır. Dosyada <code>carcass weight</code> kg cinsinden bulunur; makale bunu HCW olarak niteler. Bu, giriş için güçlü adaydır, ancak Excel sütun başlığı tek başına tartım aşamasını söylemez. Girdi eşleşmesi hedef eşleşmesinin yerini tutmaz.

## Bağımsızlık ve örnek sızıntısı

<code>ai/Model2/training/train_model_b.py</code> eğitim/validasyon/test dosyalarını yalnızca <code>ai/Model2/data/processed/splits/ModelB_{train,validation,test}_sentetik.csv</code> altından okuyor ve her satırın <code>veri_kaynagi == SENTETIK_SIMULASYON</code> olmasını zorunlu kılıyor. Bu kaynak workbook’unu okuyan bir eğitim yolu veya bu dosyaya ait <code>SN</code>/<code>date</code> anahtarlarıyla split eşleşmesi bulunmadı. Kod ve mevcut split yapısına göre **eğitim pipeline’ında doğrudan veri sızıntısı/örnek çakışması kanıtı yoktur**.

Sentetik kayıtların üretiminde bu yayının geçmişte dolaylı bir referans olarak kullanılıp kullanılmadığını yalnızca mevcut eğitim giriş kodu kanıtlayamaz; böyle bir köken kaydı bulunmuyor. Bu nedenle tarihsel/manuel esinlenme olasılığı için kesin “hiç kullanılmadı” hükmü verilemez. Gelecekte bu dataset uygun hale gelirse bölme satır veya sayfa bazında değil, tek karkas anahtarı (<code>SN</code>/<code>date</code>) bazında yapılmalıdır. Çiftlik ID’si yoktur; çiftlik bazlı ayırma yapılamaz.

## Sonuç ve sonraki adım

- **Gerçek hayvan kaydı:** 134 eşleşmiş karkas gözlemi.
- **Karkas ağırlığı:** Evet; 134 kayıtta kg cinsinden. Makale bunu sıcak karkas ağırlığı (HCW) olarak adlandırıyor, dosyanın kendi başlığı tartım aşamasını açıklamıyor.
- **Ölçülmüş parça verisi:** On ana kesimde total/fat/lean; ayrıca kemik iliği, kuyruk ve kemik kategorileri. Bu ölçümler gerçek kayıtlar için tarih anahtarıyla eşleşiyor.
- **Model 2 hedefleri:** 0 doğrulanmış bire bir eşleşme; 4 kısmi aday fiziksel tanım eksikliği nedeniyle test edilebilir hedef sayılmadı.
- **Güvenilir bağımsız değerlendirme:** Şu an sekiz hedefin hiçbirinde MAE/RMSE/R² hesaplamak doğru değil. Dataset, hedef/kesim standardı haritalaması netleştikten ve 140 makale örneği–134 dosya satırı farkı açıklığa kavuştuktan sonra yeniden değerlendirilebilir.
- **Gerekli sonraki teknik adım:** Model 2 için yazılı bir kesim standardı oluşturup her hedefin anatomik sınırını, kemik/trim kapsamını ve tartım aşamasını sabitleyin; veri sağlayıcıdan eksik altı kayıt ve iki sıfır LMP’nin açıklamasını, ayrıca veri lisansını isteyin. Sonra yalnız bire bir tanımlı ölçümleri örnek anahtarı bazında eşleyip önceden ayrılmış gerçek test değerlendirmesi planlayın.

## Kaynaklar

- [GitHub arşivi ve README](https://github.com/collinswakholi/Image-Analysis-Beef-Yield-Estimation) (README’de 22 parametre; arşiv 7 Şubat 2025’te salt okunur hale gelmiştir).
- [RefData_2019.xlsx — sabit commit URL’si](https://raw.githubusercontent.com/collinswakholi/Image-Analysis-Beef-Yield-Estimation/0a48e3faee973d94362ae2b6090e7271d8ee2714/RefData_2019.xlsx).
- Wakholi ve ark. (2022), [makale ve DOI](https://www.sciencedirect.com/science/article/pii/S153751102200085X).
