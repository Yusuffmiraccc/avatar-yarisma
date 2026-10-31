# Model B — Gerçek kaynaklardan çıkarılmış yayımlanmış özetler

Bu dosyalar indirilebilir bireysel hayvan ham verisi değildir. Web'de erişilebilen yayımlanmış toplu sonuçlar ve makale tablosu özetlenmiştir. Eğitim/test veri seti gibi kullanmayın.

## Dana: Steakpedia Field Kitchen
Kaynak: https://steakpedia.com/field-data/
Lisans: Sayfa veriler için CC BY 4.0 lisansı bildiriyor; atıf ve kaynak bağlantısı gereklidir.
Kapsam: 279 butchery sheet, toplam 1,604.6 kg dana ana parçası; sayfa özetleri parça türü bazında. CSV/JSON indirme bağlantıları web sayfasında sunuluyor, ancak bu çalışma ortamında ham dosya indirme uç noktası doğrulanamadı. Bu nedenle burada yalnızca sayfada görünen toplu özetler kaydedildi.
Sınırlama: Kayıtlar bütün hayvan karkası değil, tedarikçiden gelen tek tek dana ana parçalarının mutfak içi trim/parçalama verisidir. Kuzu/dana bütün karkasındaki but/sırt/omuz/kaburga kg tahmini için doğrudan hedef veri değildir.

## Kuzu: Matos et al. (2026)
Makale: Predictive Models for Lamb Meat Cuts and Carcass Tissue Based on Ultrasonographic Images and Body Weight
URL: https://www.mdpi.com/2624-7402/8/3/111
DOI: 10.3390/agriengineering8030111
Kapsam: 45 erkek Pantaneiro kuzusu; kesim ağırlıkları 15–35 kg gruplarında; ticari kesim ağırlıkları ve kas/yağ/kemik bileşenleri ölçülmüş. Makale, Data Supplementary S1 Excel dosyasını işaret ediyor; veri erişim açıklaması ayrıca veri setlerinin sorumlu yazardan istek üzerine alınabileceğini söylüyor.
Lisans/erişim: Makalenin açık erişimli olması ham verinin otomatik olarak açık lisansla yeniden dağıtılabileceği anlamına gelmez. Ek dosya ve veri lisansı ayrıca doğrulanmalıdır.
Sınırlama: Bu CSV'de yalnızca makalede görüntülenen bazı toplu istatistikler yer alır; 45 hayvanın satır satır ham verisi değildir.

## Önerilen kullanım
1. Dana özetini yalnızca veri sözlüğü / başlangıç aralığı incelemesi için kullanın.
2. Kuzu çalışmasının Supplementary S1 Excel dosyasını makale sayfasındaki bağlantıdan indirin veya yazardan ham veri isteyin.
3. Gerçek bireysel satırlar elde edilmeden MAE/RMSE veya %95 kapsama performansı iddia etmeyin.
4. İki kaynağı birleştirmeyin: ölçüm birimi ve işlem seviyesi farklıdır.

Bu çalışma koşusunda makale sayfasında S1 eki bulunduğu doğrulanmış olsa da dosya bağlantısına ağ araştırma aracı 429/erişim hatası verdi; arşivde de S1 yoktur. Bu nedenle S1 indirilmedi/incelenmedi. Ham kuzu ölçümleri gerekiyorsa yazar/kurumdan izinli erişim istenmeli; makalede ayrıca veri setlerinin sorumlu yazardan istek üzerine verilebileceği belirtilmiştir.
