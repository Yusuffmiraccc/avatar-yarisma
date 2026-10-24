# Veri kalitesi, değişken zamanı ve EKP denetimi

## Veri kaynağı ve sınır

Denetlenen dosya `data/raw/sucuk_uretim_1000_simule_parti.csv` (1.000 satır, 42 sütun) ve eşlik eden `sucuk_uretim_gercek_veri_benchmarkli_1000_parti.xlsx` çalışma kitabıdır. Çalışma kitabının `Baslangic_ve_Yontem` sayfası 1.000 kaydın tümünü sentetik/simüle olarak tanımlar; aynı partiye ait gerçek girdi, maliyet ve net çıktı kayıtlarının bulunmadığını açıkça belirtir. Gerçek kaynak sayfasındaki fiyat/enerji/işçilik benchmark'ları simüle partileri gerçek kayıt haline getirmez.

`Degisken_Sozlugu` da kayıp oranlarının gerçek tartım olmadığını ve simüle edildiğini; net çıktının formülle hesaplandığını; fason fiyatı ve kurum içi tesis payı gibi kalemlerin varsayım olduğunu yazar. Bu nedenle kayıp oranları için “gerçekleşmiş ölçüm” etiketi veriyle desteklenmiyor. Scenario B yalnızca ileride kullanıcı tarafından gerçekten üretim öncesi belirlenmiş plan varsayımları olarak sağlandıkları koşulda anlamlıdır; bu dosyadaki sentetik sütunlar ölçüm zamanını doğrulamaz.

## Yapısal kontroller

| Kontrol | Sonuç |
|---|---:|
| Satır / sütun | 1.000 / 42 |
| Eksik hücre | 0 |
| Tam satır yinelenmesi | 0 |
| Yinelenen `Parti_ID` | 0 |
| Sayısal NaN / sonsuz değer | 0 |
| Negatif net çıktı veya toplam maliyet | 0 |
| Sıfır/negatif net çıktı | 0 |
| `Veri_sinifi` | 1.000 kaydın tümü sentetik/simüle olarak işaretli |

CSV ve sözlükteki ana birimler birbiriyle uyumludur: hammadde/net ürün miktarları kg, kılıf metre, birim fiyatlar ilgili kg veya metre başına TL, işçilik saati saat, elektrik kWh, kayıp oranları yüzde, toplam maliyet TL ve EKP TL/kg net üründür. Sütun adları bu birimleri içerir; kaynak fiyatların her biri gerçek sanayi teklifini temsil etmez. Çalışma kitabı özellikle kuyruk yağı ve baharatın liste fiyatı olabileceğini, küçük girdilerin yaklaşık maliyetlendiğini ve fiyatların parti bazında simüle edildiğini belirtiyor.

## Değişken zamanı ve özellik kararı

| Alan / grup | Bilgi zamanı değerlendirmesi | Model kararı |
|---|---|---|
| Et, yağ, baharat, tuz/diğer girdi miktarları | İsimleri planlanan girdi/reçete miktarlarını gösteriyor; bu örnek veri değerleri simüle edilmiş. Gerçek kullanımda sipariş/plan anında bilindiği doğrulanmalı. | A ve B'de planlanan girdi varsayımı olarak kullanılabilir. |
| Bölge, reçete profili, işleme modeli | Üretim emrinde planlanabilir etiketler; kaynağın kategori değerleri simüle. | A ve B'de aday özellik. |
| Birim fiyatlar, fason bedeli, işçilik ve elektrik tarifeleri, ambalaj TL/kg | Önceden bilinen teklif/tarife olabilir; ancak dosya bunların her parti için üretim öncesinde snapshot alındığını kanıtlamıyor. Fason bedeli açıkça varsayımsal; kaynak fiyatlarının bazıları web/liste benchmark'ı. | A/B'de yalnızca doğrulanmış plan fiyatı/tarifesi sağlandığında kullanılabilir; bu rapordaki A ölçümü koşulludur. |
| `Kuruma_kaybi_pct`, `Ayiklama_fire_pct` | Çalışma kitabı kayıpları deneysel aralıklardan simüle edildiğini ve gerçek parti tartımı olmadığını söylüyor. Gerçek ölçüm zamanı kanıtlanmış değil. | A'da çıkarıldı. B'de yalnızca üretim öncesi plan varsayımı şeklinde koşullu kullanılır; gerçekleşmiş kayıp iddiası yoktur. |
| `Iscilik_saati`, `Elektrik_kWh` | Tüketilmiş süre/enerji gerçekleşmiş operasyonda ölçülür; veri sözlüğü kurum içi maliyette bunları formül girdisi sayıyor. Önceden planlanmış değer olduğunu kanıtlayan zaman damgası yok. | Tahmin özelliklerinden çıkarıldı. |
| `Net_sucuk_ciktisi_kg_simule` | Hedef; girdi toplamı ve iki kayıp oranından türetilmiş. | Yalnızca hedef olarak kullanılır. |
| `Toplam_parti_maliyeti_TL`, `EKP_TL_kg` | Toplam maliyet bileşenlerden, EKP toplam maliyet/net kg oranından hesaplanır. | EKP veya maliyet tahminlerinde hedef/ölçüm olarak tutulur; özellik olarak kullanılmaz. |
| Maliyet bileşenleri ve `Et_maliyet_payi_pct` | Birim fiyat × miktar, toplam maliyet bileşimi veya maliyet payından türetilir. | Özelliklerden çıkarıldı. |
| `Karisim_girdi_toplam_kg` | Ham girdi sütunlarının toplamı. | Türetilmiş kopya olduğu için özelliklerden çıkarıldı. |
| Tarih, `Parti_ID`, `Veri_sinifi`, kaynak kodu, açıklama | Sentetik simülasyon/metaveri; parti ID'si tanımlayıcı. | Özelliklerden çıkarıldı. |

Feature allow-list A, tahmin anı açıkça doğrulanmamış fiyat/tarife sütunları dahil olmak üzere `training/validate_models.py` içindedir. Dolayısıyla **A “varsayımsız kesin üretim öncesi bilgi” garantisi değildir**: miktar/kategori planlaması ve fiyat/tarife snapshot'ı sahada doğrulanmalıdır. `training/train_production.py` de aynı alan listesini kullanır ve yalnızca aday üretir.

## Formül, birimler ve maliyet tutarlılığı

Kütle dengesi:

`net kg = (Et + kuyruk yağı + baharat + tuz + diğer girdiler) × (1 − kuruma % / 100) × (1 − ayıklama % / 100)`

Formülün net çıktı hedefiyle mutlak farkı maksimum 0,000500 kg, ortalama 0,000253 kg. Bu, sentetik hedefin formülle neredeyse deterministik üretildiğini gösterir. Kayıp değerleri simülasyon/sonradan ölçüm ise, bu formül üretim öncesi tahmin değildir.

EKP:

`EKP (TL/kg net) = Toplam_parti_maliyeti_TL / Net_sucuk_ciktisi_kg_simule`

Net miktar sıfırdan büyük; TL/kg birimleri tutarlı. CSV üzerinde oranı yeniden hesaplamanın EKP sütunundan maksimum farkı 0,015946 TL/kg, ortalama farkı 0,002982 TL/kg (yuvarlama hassasiyetinde).

Direkt malzeme bileşen toplamının `Direkt_malzeme_toplam_TL` ile maksimum farkı 0,02 TL, ortalama 0,00386 TL. Direkt malzeme + fason hizmet + kurum içi işleme + paketleme + genel gider toplamının `Toplam_parti_maliyeti_TL` ile maksimum farkı 0,02 TL, ortalama 0,00394 TL. Negatif toplam maliyet bulunmadı.

Fason satırlarda `Fason_hizmet_TL` ortalama 28.104,88 TL ve kurum içi işleme maliyeti sıfır; kurum içi satırlarda fason maliyeti sıfır ve `Kurum_ici_isleme_TL` ortalama 23.207,23 TL. Hedef EKP ortalaması fason grubunda 937,26 TL/kg (n=338), kurum içinde 919,15 TL/kg (n=662). Grup farkı simüle varsayımların bileşimini yansıtır; gerçek proses maliyetleri hakkında kanıt değildir. İşleme modeli zaten A modelinde kategorik özellik olarak yer alır.

## EKP dağılımı ve zayıf A performansı

Hedef dağılımları (n=1.000):

| Hedef | Birim | Ortalama | Standart sapma | Medyan | Minimum | Maksimum |
|---|---|---:|---:|---:|---:|---:|
| Net çıktı | kg | 217,6058 | 99,0817 | 214,6285 | 40,3970 | 411,2720 |
| Toplam parti maliyeti | TL | 200.595,20 | 90.922,66 | 196.291,23 | 42.548,73 | 379.531,77 |
| EKP | TL/kg net | 925,2728 | 65,5680 | 910,6100 | 804,45 | 1.147,96 |

EKP 1. ve 99. yüzdelikleri 819,47 ve 1.106,19 TL/kg; kuyruklar veri hatası olarak doğrulanmadı, silinmedi.

Senaryo A RandomForest MAE 49,8723 TL/kg (yaklaşık hedef ölçeğinin %5,4'ü), RMSE 61,2236, R² 0,1070. Eğitim ortalaması baseline MAE 51,6755; iyileşme yalnızca %3,49. A özellikleri net çıktı kaybı bilgisini ve gerçekleşmiş işçilik/enerji miktarlarını içermez; oysa maliyet formülü birden fazla bileşeni ve net kg paydasını kapsar. Reçete/miktar/fiyatlar bazı maliyetleri açıklar, ancak simüle kayıp, işçilik/enerji tüketimi ve mod-seçimine bağlı maliyet bileşenleri ile payda değişkenliği A özelliklerinden tam belirlenemiyor. Bu bulgular zayıf performans için formül ve erişilebilirlik temelli açıklamadır; sentetik tablo tek başına nedenselliği kanıtlamaz.

Scenario B EKP MAE'sinin düşmesi, kayıp yüzdeleri simüle üretim formülünün parçası olduğu için beklenir; bunların üretimden önce güvenilir plan girdisi olduğu veya ölçülmüş gerçekleşen değer olduğu anlamına gelmez. Toplam maliyet→EKP oran adayında maliyet modeli A özelliklerinden öğrenilir, net çıktı A RF'den tahmin edilir. İkisi de tahmin olsa da toplam maliyet tahmininin kendi MAE'si EKP oranından daha güvenilir bir karar eşiğini kanıtlamaz; oran adayı EKP baseline'ını %3,61 geride bıraktı. Gerçek maliyet, çıktı ve EKP tahmin girdisi yapılmadı. Üretime hazır EKP modeli yoktur.

## Sonraki veri toplama ve doğrulama

Her gerçek parti için planlanan miktar, plan/fiyat snapshot zamanı, fason teklifi veya işçilik/enerji tarifeleri; ayrı sütunlarda planlanan ve gerçekleşmiş kayıp yüzdeleri; gerçekleşmiş net tartım; gerçekleşmiş işçilik saati, kWh ve her maliyet bileşeni; işleme türü, tarih, vardiya/hat ve parti kimliği tutulmalı. Simüle ve gerçek kayıtlar işaretlenip eğitimde gerçeklik sınıfı filtrelenmeli. Gerçek partilerle zaman bazlı holdout ve mümkünse farklı hat/aylarda dış doğrulama yapılmalı; EKP MAE/RMSE/baseline ve TL/kg iş etkisi kabul edilmeden API yanıtı karar veya muhasebe akışına bağlanmamalı.


## Kodla tekrar denetim — 24.10.2026

`tests/test_data_integrity.py` içindeki otomatik kontroller aynı CSV için 1.000×42 şema, tekil başlıklar, 0 eksik hücre, 0 yinelenen satır/Parti_ID, tüm satırlarda sentetik sınıf, kütle dengesi (maksimum fark ≤0,00051 kg), malzeme/toplam maliyet mutabakatı (maksimum fark ≤0,0201 TL) ve EKP oranı (maksimum fark ≤0,016 TL/kg) doğruladı. Bu eşikler CSV’deki yuvarlama farklarına dayanır; muhasebe kuralı olarak yorumlanmamalıdır. Fason ve kurum içi maliyet ayrımı yalnızca bu simüle tablodaki sıfır-dışı kalemlerle tutarlıdır; gerçek muhasebe politikasıyla doğrulanmamıştır.
## EKP araştırma karşılaştırması için ek formül kontrolü — 24.10.2026

training/compare_ekp_models.py tekrar kontrolünde gerekli model girdileri/target alanlarında eksik hücre 0, tam yinelenen satır 0 ve tam aynı 18 özellik değerine sahip kayıt 0 bulundu. EKP sütunu toplam maliyet / net çıktı oranıyla en çok 0,015946 TL/kg ayrışıyor; bu CSV yuvarlamasıyla uyumlu. 338 fason kaydında fason hizmeti = toplam girdi kg × fason bedeli en çok 0,005 TL farkla tutarlı. Bu eşitlik yalnız simüle Fason satırlarında doğrulandı; gerçek maliyet politikası teyidi değildir.

Hibrit aday deterministik alt toplamda yalnız et, kuyruk yağı, baharat, kılıf miktarı×fiyatlarını ve Fason türünde doğrulanan fason bedelini kullandı. Tuz/diğer girdi maliyeti, kurum içi işleme, ambalajın ön üretim tutarı ve genel gider için erişilebilir ve doğrulanmış formül bulunmadı. Girdi fiyatlarının zaman damgası da sentetik dosyada yoktur.
## Boş gerçek-veri şeması ve doğrulama hattı — 24.10.2026

Yeni toplama şablonları data/templates/real_production_batches_template.csv ve .xlsx altında üretildi; ikisi de yalnızca başlık/yardımcı sayfa içerir, parti örneği içermez. Alan, tip, birim, gereken kullanım, kabul edilen değer, kaynak ve ölçüm zamanı reports/production_data_dictionary.md içinde verilir. Mevcut eğitim kaynağında gerçek saha partisi bulunmadı; bu nedenle aşağıdaki yeni şema için eksik/tekrar/formül istatistiği gerçek kayıt üzerinde hesaplanmış değildir (0 satır, kalite oranı yok).

app/production_data.py doğrulayıcısı eksik zorunlu alan, beklenmeyen sütun, yanlış tip, NaN/sonsuz, negatif değer, yüzde aralığı, batch ID tekrarı, zaman dilimi ve zaman sırası, geç plan snapshot'ı, TRY/parti dönem birimi, maliyet dökümü ve kütle dengesi için satır/alan/kod seviyesinde hata verir. Kaydı değiştirmez veya sessizce düşürmez. Değerlendirici sentetik veya external benchmark kaydını gerçek kaynakla karıştırmaz; gerçek değerlendirmesi için tüm kayıtların gerçek, kaynak referanslı ve onaylı olması gerekir.

Birim politikası: maliyet TRY/batch; girdi ve ürün/kayıp kg; kılıf m; enerji kWh; işçilik hour; EKP TRY/kg. Kur dönüşümü veya aylık maliyet tahsisi yapılmaz. On maliyet kolonu birbirini dışlayan bileşenler olmalıdır; fason hizmeti ve kurum içi işleme ayrı tutulur. Tam dökümde her bileşen açıkça girilir; toplam mutabakat toleransı her tutarın TRY kuruşuna yuvarlandığı varsayımından hesaplanır (0.005 × (bileşen sayısı + toplam) TL). Kaynaklar daha düşük hassasiyetle yuvarlanıyorsa önce muhasebe standardı tanımlanmalıdır.

Kütle dengesi girdi kg - kuruma kg - ayıklama kg - diğer kg = ölçülmüş net kg şeklindedir; yalnız losses_complete=true ve ölçümlerin zamanı/yöntemi varsa denetlenir. Tolerans hücrede yazılı ondalık hassasiyetlerden türetilir; bu, gerçek terazi çözünürlüğünün kanıtı değildir. Parti sınırına su/katkı, ara ürün veya yeniden işleme girip girmediği süreç sahibi tarafından netleştirilmelidir. Kayıp yüzdeleri payda/timing kaydı yoksa mass-balance yerine geçmez. Sonradan ölçülen kayıplar tahmin girdisi olamaz.

Scenario A feature allow-list'i 18 plan alanıdır ve plan_snapshot_at <= production_started_at koşulunu arar. Sonuç hedefleri (total_cost_tl, ölçülen net_output_kg, maliyet bileşenleri) ve post-production alanları feature değildir. Model girdileri eksikse veya snapshot zamanını kanıtlayamıyorsa kronolojik tahmin değerlendirmesi durur. record_created_at ve validated_at hedefin ilgili test tarihinden önce kullanılabilir olduğunun ek zaman kapısıdır.

Kayıp yüzdelerinin gerçek ölçüm zamanı mevcut sentetik kaynakta kanıtlanmamıştır. Scenario B ölçülmüş kayıp değerleri varsa kütle dengesi/sonradan gerçekleşen EKP hesaplaması için koşullu bir referanstır; üretim öncesi tahmin girdisi değildir. Yeni şablon boş olduğu için yeni gerçek veri kalitesi sonucu/metric yoktur.

Tam kronolojik değerlendirme raporu reports/ekp_chronological_evaluation.md/.json içindedir. İlk çalışma boş şablonda no_real_data verdi; doğrudan EKP, cost/yield ve hibrit yolların hiçbiri için gerçek test metriği hesaplanmadı. Gerçek kayıtla yeniden çalıştırılacak komut ve minimum split politikası README'dedir.
