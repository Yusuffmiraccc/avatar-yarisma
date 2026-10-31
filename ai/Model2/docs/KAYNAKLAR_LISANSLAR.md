# Model B — Kaynak, lisans ve veri kökeni kaydı

Denetim tarihi: 24.10.2026. Kaynak türleri `measured` (bireysel saha ölçümü), `published_aggregate` (yayın/site toplu verisi), `synthetic` (simülasyon) olarak ayrı tutulur. Bu pakette `measured` bireysel satır yoktur. Envanter Model2 dosyaları ve erişilebilen yayın/kurum sayfalarıyla sınırlıdır; özetlerden bireysel kayıt oluşturulmamıştır.

| Kaynak | URL / kimlik | Kaynak türü ve kapsam | Kayıt düzeyi | Lisans / kullanım durumu | Model kullanım kararı |
|---|---|---|---|---|---|
| ModelB sentetik parçalaması | `data/raw/synthetic/ModelB_Sentetik_Parcalama_Verisi.csv` | 1.200 satır; 400 kuzu, 400 koyun, 400 dana; karkas ağırlığı ve sekiz sentetik çıktı, kg | Sentetik satırlar | Gerçek ölçüm lisansı yok; proje içi prototip/test dosyası | Yalnız sentetik eğitim ve teknik test; saha başarısı değildir |
| Ardıçlı, Dinçel, Balcı (2018), Holstein boğa karkasları | [Makale PDF](https://dergipark.org.tr/tr/download/article-file/541592), DOI 10.30607/kvj.390226 | Güney Marmara mezbahasından 311 saf Holstein erkek sığır; sıcak/soğuk karkas, kemik ve değerli perakende kesim özetleri | Çalışma 311 hayvan gözlemi kullandığını bildiriyor; Model2 paketinde bireysel satırlar yok, web kaynağından bireysel CSV indirilmedi | Makalenin yeniden kullanım lisansı bu denetimde doğrulanamadı; atıf yapılması lisans izni anlamına gelmez | Yalnız yayımlanmış toplu özet; Model eğitimi için kullanılamaz |
| Özavcı (2009), kuzu karkas parçalama tezi | [Bursa Uludağ Üniversitesi AVESİS kaydı](https://avesis.uludag.edu.tr/yonetilen-tez/57956a69-5e54-4ca3-b7fe-4e6b1913e4e0/kuzu-karkaslarinin-parcalanmasinda-sistem-olusturma-verim-ve-kalite-degerlendirmesi), Tez No 247291 | Özette 100 kuzu; 50 kemiksiz, 50 kemikli parçalama sistemi ve kesim öncesi/sonrası ölçümler anlatılıyor | Kurum kaydı örneklem sayısını bildiriyor; AVESİS sayfasında ham tablo/indirilebilir hayvan satırları yok | Tez erişim/kullanım lisansı ham veri yeniden kullanımı için doğrulanmadı | Özetteki toplu bilgiler; bireysel veri gibi kullanılmadı |
| Matos et al. (2026), Pantaneiro kuzu çalışması | [AgriEngineering makalesi](https://www.mdpi.com/2624-7402/8/3/111), DOI 10.3390/agriengineering8030111 | 45 erkek kuzu; canlı kesim ağırlığı, soğuk karkas ve yarım karkas ticari kesim/tissue bilgileri | Makalede n=45; paket CSV’sinde bazı yayımlanmış özet istatistikler var; bireysel ek S1 bu çalışma dizininde yok | Makale açık erişim; ek verinin yeniden dağıtım lisansı ayrı doğrulanmadı. Makale veri bildirimi verinin sorumlu yazardan istek üzerine temin edilebileceğini söylüyor | Sadece özet bağlam; Model B bireysel eğitim verisi değil |
| Steakpedia Field Kitchen | [Field data](https://steakpedia.com/field-data/), [About/method](https://steakpedia.com/about/) | 279 kesim formu, toplam 1.604,6 kg tedarik edilmiş dana primali; kesim türü bazında verim | Site kendi alan kayıtlarını toplulaştırıp kesim türü başına satır yayımlar; bireysel karkas/parçalama satırı değildir | Sayfa CSV/JSON toplu tablosu için CC BY 4.0 bildiriyor; atıf ve kaynak bağlantısı gerekir | Yalnız toplu dana primal verimi; bütün karkas hedefleriyle aynı tanım değil. Paketteki özetin CSV’si eğitimde kullanılmadı |
| `AVATAR_Assessment.pdf` | Proje dosyaları içinde arandı | Görev/assessment belgesi | Erişilebilir dosya yok | — | İncelenmedi; varmış gibi varsayılmadı |

## Veri erişimi sonucu

- `data/raw/measured/` boş veri hedefi olarak oluşturulmuştur; içinde bireysel saha kaydı yoktur. Gerçek veri indirilmedi veya sentetikten türetilmedi.
- 311 Holstein kaynağının ve 100 kuzu tezinin örneklem büyüklüğü birincil akademik/kurumsal sayfada doğrulanabilir; fakat Model2 içinde bireysel kayıt dosyası yoktur.
- Steakpedia’nın yayımladığı indirme, kendi yöntem notuna göre “cut başına bir satır” toplu dosyadır. Karkas seviyesinde animal-level ölçüm akışı olarak ele alınmamıştır.
- Yayınlanmış verileri sentetik satırlara katma, özetlerden bireysel satır üretme veya belirsiz lisanslı dosyayı dağıtma yapılmadı.

## Atıf

Steakpedia verisi ileride türetilmiş biçimde kullanılacaksa CC BY 4.0 kapsamında sayfa atfı ve bağlantısı eklenmelidir. Diğer kaynakların sayısal özetleri burada yalnız kaynağın kapsamını ve veri erişim durumunu açıklamak içindir; makale/tez telif koşulları ayrıca kontrol edilmeden ham veri dağıtılmamalıdır.

### S1 supplementary file note

The MDPI article page names a supplementary Excel file, but the Excel file is not in the provided Model2 archive. The current research connector could retrieve the article/search metadata but its page request was rate-limited/unavailable for the supplement download; no S1 workbook was downloaded or inspected in this work. The article's data availability statement says analyzed datasets are available from the corresponding author on request. Therefore this source remains aggregate/context only in the project and has not entered training.
