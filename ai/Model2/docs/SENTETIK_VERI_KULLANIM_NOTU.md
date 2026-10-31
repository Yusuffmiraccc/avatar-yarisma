# Model B — Sentetik Parçalama Verisi

## Dosyalar
- `ModelB_Sentetik_Parcalama_Verisi.csv`: 1.200 sentetik kayıt (kuzu 400, koyun 400, dana 400)
- `ModelB_Sentetik_Parcalama_Verisi.xlsx`: aynı veri + kısa README sayfası

## Kritik uyarı
Bu veri setindeki her satır **sentetik olarak üretilmiştir**. Gerçek bir kesimhaneden alınmış bireysel ölçüm değildir; bilimsel olarak doğrulanmış bir eğitim seti veya gerçek performans kanıtı olarak sunulmamalıdır. Yazılım prototipi, veri hattı, API, grafikler ve ilk model pipeline'ını test etmek için uygundur. Gerçek işletme kararlarında kullanılmamalıdır.

## Kaynaklardan nasıl yararlanıldı?
- Bursa Uludağ Üniversitesi arşivindeki “Besi danalarında ortalama karkas ve parça et verimi üzerinde araştırmalar” çalışması; dana karkas/verim bağlamında referans olarak ele alındı. Çalışmada bildirilen oranlar farklı paydalara dayanabildiğinden, yayın yüzdeleri bu CSV'ye birebir ve doğrulanmış etiketler gibi kopyalanmadı.
  Kaynak: https://acikerisim.uludag.edu.tr/items/3a336059-74a0-4d41-922c-60c8b5e9fd63/full
- ActLedger'ın karkas verimi örneği yalnızca genel bir sektör örneği olarak dikkate alındı; hakemli ve bireysel kayıt veri seti değildir.
  Kaynak: https://www.actledger.com/blog/karkas-verimi-parca-maliyeti-hesaplama
- Kuzu ve koyun için aynı düzeyde doğrulanmış bireysel parça ölçüm verisi burada mevcut değildi. Bu türlere ait oranlar açıkça varsayımsal/sentetik dağılımlardır.

## Ağırlık tanımı
`giris_agirligi_kg`, **karkas ağırlığıdır**, canlı hayvan ağırlığı değildir. Modeliniz canlı ağırlıktan tahmin yapacaksa canlı ağırlık ve kesim randımanı ölçümleri içeren gerçek kayıtlar toplanmalıdır.

## Alanlar
- `kayit_id`: sentetik kayıt kimliği
- `veri_turu`: her satırda `SENTETIK`
- `hayvan_turu`: `kuzu`, `koyun`, `dana`
- `giris_agirligi_kg`: karkas giriş ağırlığı
- `giris_agirligi_tipi`: `karkas_agirligi`
- `parcalama_tarihi`: sentetik tarih
- `irk`, `cinsiyet`, `yas_ay`, `yag_durum_skoru`: mevcut kaynaklarda bireysel kayıt olmadığı için bilinmiyor/boş
- `but_kg`, `sirt_kg`, `omuz_kg`, `kaburga_kg`, `kiyma_kg`: ürün kategorisi ağırlıkları
- `yan_urun_kg`: tanımı işletme tarafından netleştirilmesi gereken yan ürün grubu
- `kemik_yag_sinir_kg`: kemik/yağ/sinir gibi ayrıştırılmış materyal grubu
- `fire_kg`: işlem kaybı için sentetik miktar
- `*_oran`: ilgili kategorinin giriş karkas ağırlığına oranı
- `toplam_cikis_kg`: tüm çıkış kalemlerinin toplamı
- `agirlik_dengesi_farki_kg`: toplam çıkış eksi giriş; sıfır olması beklenir

## Modelleme önerisi
1. `veri_turu == SENTETIK` olduğunu veri hattında koruyun; gerçek ve sentetik kayıtları ayırın.
2. İlk prototipte hayvan türüne göre ortalama oran baseline'ı kurun.
3. Ridge ve Random Forest'i aynı holdout/split üzerinde karşılaştırın; ancak bu sentetik veri üzerindeki metrikler yalnızca sentetik dağılımı ne kadar öğrendiğini gösterir.
4. Gerçek veriler geldiğinde hayvan/lot bazlı grup ayrımı yapın; aynı hayvanın birden fazla satırını eğitim ve test tarafına bölmeyin.
5. Her hedef için MAE ve RMSE raporlayın. Birden fazla parça hedefi varsa tür bazında da raporlayın.
6. %95 tahmin aralığı için gerçek doğrulama verisiyle kalibre edilmiş conformal prediction veya uygun quantile modeller kullanın. Sentetik veriden üretilen aralıklar gerçek dünyada %95 kapsama garantisi vermez.

## Gerçek veri toplama için zorunlu önerilen alanlar
- `animal_id`, `lot_id`, `species`, `breed`, `sex`, `age_months`
- `live_weight_kg`, `carcass_weight_kg`, `carcass_definition` (sıcak/soğuk, kemikli/kemiksiz)
- `cutting_standard_id`, `operator_id`, `measurement_scale_id`, `processing_date`
- Her standart parçanın ayrı kg ölçümü; kemik, yağ, sinir, sakatat/yan ürün ve fire ayrı kategoriler
- `input_weight - sum(output_weights)` farkı ve açıklama kodu
- Terazilerin kalibrasyon/ölçüm prosedürü

Bu veri seti **prototip ve eğitim akışını denemek** içindir; işletmede verim, maliyet veya fire kararı vermek için gerçek, temsil edici ve bağımsız ölçümler gereklidir.
