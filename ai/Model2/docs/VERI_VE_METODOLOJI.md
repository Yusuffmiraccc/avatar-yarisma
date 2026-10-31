# Model B — Eğitim/Test Veri Paketi

## İçerik
- `ModelB_EgitimPaketi.xlsx`: sentetik kayıtlar, train/validation/test, kaynak özetleri ve metrikler.
- `ModelB_train_sentetik.csv`, `ModelB_validation_sentetik.csv`, `ModelB_test_sentetik.csv`: ayrı kümeler.
- `ModelB_tum_veri_split.csv`: tüm kayıtlar ve bölüm etiketi.
- `ModelB_sentetik_model_degerlendirme.csv`, `ModelB_hedef_bazli_metrikler.csv`: baseline ve Random Forest ölçümleri.
- `ModelB_egitim_kodu.py`: yeniden çalıştırılabilir prototip değerlendirmesi.
- `ModelB_GercekVeri_Dana_TopluOzet.csv`, `ModelB_GercekVeri_Kuzu_MakaleOzetleri.csv`: gerçek kaynaklardan derlenmiş toplu/akademik özetler; bireysel hayvan kayıtları değildir.

## Şema
Girdiler: hayvan türü (`kuzu`, `koyun`, `dana`) ve karkas ağırlığı (kg).
Hedefler: but, sırt, omuz, kaburga, kıyma, yan ürün, kemik/yağ/sinir ve fire (kg).
Sentetik kayıt sayısı: 1200. Bölme: train 840, validation 180, test 180; tür bazında stratified, sabit seed 20261024.

## Şeffaflık ve sınırlamalar
Tüm 1.200 bireysel satır SENTETİKTİR. Steakpedia kaynağı 279 işlem formunda 1.604,6 kg önceden ayrılmış dana parçalarının işlenme verimini özetler; bütün karkas parçalama kayıtları sağlamaz. Kuzu makalesi 45 hayvan üzerinde karkas ve ticari parça ölçümleri raporlar; burada ham bireysel tablo indirilebilir şekilde doğrulanmış değildir. Bu nedenle gerçek özetler eğitim satırlarına dönüştürülmedi ve sentetik kayıt gibi karıştırılmadı.

Sentetik kütle dengesi ve test metrikleri yalnızca veri simülasyonunu kontrol etmeye yarar. Sentetik holdout üzerinde iyi sonuç, gerçek hayvanda doğru tahminin kanıtı değildir. Yarışma sunumunda bu metrikleri gerçek saha performansı olarak sunmayın.

Gerçek veri geldiğinde: her satır bir karkas/parti olmalı; canlı ağırlık ile sıcak/soğuk karkas ağırlığı ayrılmalı; çıkış kategorileri çakışmamalı; aynı hayvan/parti train-test arasında bölünmemeli; model MAE/RMSE ile tür bazlı ortalama oran baseline'ına karşı gerçek holdout üzerinde ölçülmelidir.

Kaynaklar:
- Steakpedia Field Kitchen (2026), https://steakpedia.com/field-data/ — CC BY 4.0; parça bazlı işleme verimi.
- Vargas Junior et al. (2026), https://www.mdpi.com/2624-7402/8/3/111 — 45 Pantaneiro kuzusunda karkas/parça ölçümleri; ham bireysel veri erişimi teyit edilmedi.
- `AVATAR_Assessment.pdf`: Model B gereksinimi.
