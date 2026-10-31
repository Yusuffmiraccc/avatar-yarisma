# AVATAR — Makine Öğrenmesi Değerlendirme Raporu (ML_EVALUATION)

Bu belge, AVATAR Yapay Zekâ Yarışması değerlendirme belgesi gereğince geliştirilen iki zorunlu yapay zekâ modelinin mimarisini, deneysel değerlendirme sonuçlarını, baseline karşılaştırmalarını ve şeffaflık sınırlarını açıklar.

Ayrıntılı deney kütüğü ve bilimsel tablolar için: [`docs/AI_RAPORU.md`](AI_RAPORU.md) ve [`docs/ML.md`](ML.md).

---

## 1. Modellerin Amacı ve İşlevi

### Model A: Üretim Verimi ve Gerçek EKP Tahmini
- **Amaç:** Dış fason sucuk üretim emri oluşturulduğunda (`URT-xxxx`), geçmiş üretim geçmişine dayanarak beklenen sağlam paket sayısını ve beklenen EKP birim maliyetini (örn. 18,16 €) tahmin etmek; operasyonel anomali veya hammadde kalite sapmalarını erkenden uyarmak.
- **Seçilen Algoritmalar:** Ridge Regresyon ve Gradient Boosting Regressor.
- **Baseline Yöntemi:** Son $N$ emrin hareketli ortalaması (`BASELINE_MEAN`).

### Model B: Kuzu Parçalama Verimi Tahmini
- **Amaç:** Kesimhaneden alınan karkas kuzu girişinde (örn. 25 kg karkas), hayvan türü ve giriş ağırlığına göre parçalama sonrası elde edilecek parça et ağırlıklarını (But, Sırt, Omuz, Kaburga, Kıyma vb.) ve fire oranını tahmin etmek.
- **Seçilen Algoritmalar:** Random Forest Regressor ve Multi-Output Regressor.
- **Baseline Yöntemi:** Hayvan türü bazlı tarihsel ortalama verim oranları (`BASELINE_ANIMAL_MEAN`).

---

## 2. Deneysel Değerlendirme ve Metrikler

Modeller, zaman serisi holdout ve $K$-fold çapraz doğrulama ile test edilmiştir.

### 2.1 Model A Performansı (Üretim & EKP)

| Metrik | Baseline (Ortalama) | Model (Ridge Regresyon) | İyileşme Oranı |
|---|---|---|---|
| **Mamul Miktarı MAE** | 3.96 paket | **2.46 paket** | **%37.94 İyileşme** |
| **Mamul Miktarı RMSE** | 4.88 paket | **3.01 paket** | **%38.32 İyileşme** |
| **EKP Birim Maliyet MAE** | 0.4728 € | **0.2978 €** | **%37.01 İyileşme** |
| **EKP Birim Maliyet MAPE** | %2.60 | **%1.64** | **%36.92 İyileşme** |
| **Tahmin Aralığı Kapsama** | - | **%84.0** | %80 hedef aralığında |

### 2.2 Model B Performansı (Kuzu Parçalama)

| Metrik | Baseline (Ortalama) | Model (Random Forest) | İyileşme Oranı |
|---|---|---|---|
| **Parça Başına Ortalama MAE** | 1.446 kg | **0.997 kg** | **%31.06 İyileşme** |
| **Parça Başına Ortalama RMSE** | 1.821 kg | **1.218 kg** | **%33.11 İyileşme** |
| **%95 Güven Aralığı Kapsaması** | - | **%97.7** | Güvenilir |

---

## 3. Bilimsel Sınırlılıklar ve Şeffaflık Taahhüdü

1. **Sentetik Veri Bildirimi (`is_demo=True`):**
   Mevcut veri seti, fabrika saha verisi bulunmadığı için sentetik jeneratör ile üretilmiştir (`backend/app/ml/synthetic.py`). Gerçek endüstriyel başarı iddiasında bulunulamaz; üretim ortamında gerçek fabrika/kesimhane kayıtları ile yeniden eğitilmelidir.
2. **$R^2$ Metriği Kısıtı:**
   Dar varyanslı veya homojen küçük veri alt kümelerinde $R^2$ negatif veya tanımsız çıkabilmektedir. Bu nedenle model performansında birincil kabul kriteri olarak MAE ve MAPE esas alınmıştır.
3. **Asgari Örneklem Eşiği ($N \ge 30$):**
   Kategori veya ürün bazında en az 30 tamamlanmış gerçek operasyonel kayıt oluşmadan makine öğrenmesi tahminleri devreye alınmaz; sistem deterministik baseline modunda çalışır.
4. **Finansal ve Muhasebesel Bağımsızlık Garantisi:**
   EKP (Eşdeğer Karkas / Ürün Maliyeti), stok düşümü, kuzu parçalama maliyet dağılımı (ağırlık bazlı oranlama) ve kâr/zarar hesaplamaları **asla** ML model tahminlerine dayandırılmaz. Muhasebe ve envanter işlemleri tamamen deterministik formüller ve kesin işlem kayıtları üzerinden yürütülür. ML sadece anomali uyarısı (`MULTIVARIATE_ANOMALY`) ve operasyonel rehberlik sağlar.
5. **İzlenebilirlik ve Geri Çağırma Bağımsızlığı:**
   AI tahminleri hiçbir koşulda gerçek stok, lot ve geri çağırma blokajlarının yerine geçmez. Lot blokajı (`LOT_BLOCKED`, HTTP 409) deterministik güvenlik kuralıdır.
