# AVATAR — Değerlendirme Demosu Adım Adım Senaryosu (DEMO)

Bu belge, AVATAR Yapay Zekâ Yarışması değerlendirme jürisi önünde baştan sona icra edilecek zorunlu demo akışını, gerekli komutları, beklenen ekran çıktılarını ve doğrulama noktalarını içerir.

---

## 1. Demo Ön Hazırlığı ve Başlatma

### 1.1 Demo Kullanıcı Hesapları
Tüm hesapların parolası varsayılan olarak **`Avatar-Demo-2026!`** değerindedir:

| Rol | E-posta | Yetki Kapsamı |
|---|---|---|
| **Yönetici** | `admin@avatar.demo` | Tam sistem erişimi, tüm ekranlar ve maliyetler |
| **Operatör** | `operator@avatar.demo` | Üretim, parçalama, stok hareketleri |
| **Saha Satış** | `sales@avatar.demo` | Android uygulaması, satış oluşturma, katalog (Maliyetler gizlidir) |
| **İzlenebilirlik** | `trace@avatar.demo` | Lot takibi, geri çağırma (recall) aktivasyonu |
| **İzleyici** | `viewer@avatar.demo` | Salt okunur raporlama (Maliyetler gizlidir) |

### 1.2 Sistemi Başlatma Komutları

```powershell
# 1. Backend Servisini Başlatın (backend klasöründe)
docker compose up -d mysql                     # kökte; veya tüm sistem için: docker compose up -d --build
cd backend
python -m scripts.seed_demo                    # Tekrarlanabilir demo verisini yükler

# 2. Web Yönetim Panelini Başlatın (web klasöründe)
cd ../web
npm run dev                                     # http://127.0.0.1:5173 adresinde açılır

# 3. Android Satış Uygulamasını Başlatın (android klasöründe)
cd ../android
./gradlew :app:installDebug                    # Emülatör veya cihaza yükler
# Fiziksel cihaz kullanılıyorsa port yönlendirme:
adb reverse tcp:8000 tcp:8000
```

---

## 2. Adım Adım Demo Senaryosu

### Adım 1: Dış Hizmetle Üretim ve Gerçek Maliyet (EKP) Doğrulaması

1. Web paneline `admin@avatar.demo` ile giriş yapın.
2. **Üretim Emirleri** (`/production`) ekranına gidin.
3. `URT-2026-045` kodlu üretim emrini açın.
4. **Hammadde Tüketimi Tablosu:**
   - `ET-2026-001`: 100 kg × 9,70 € = 970,00 €
   - `BAH-2026-001`: 2 kg × 24,00 € = 48,00 €
   - `BAG-2026-001`: 5 kg × 11,60 € = 58,00 €
   - **Toplam Hammadde Maliyeti:** **1.076,00 €**
5. **Dış Hizmet / İşçilik Faturası:**
   - 85 paket × 5,50 € = **467,50 €**
6. **EKP ve Toplam Maliyet Doğrulaması:**
   - Toplam Gerçekleşen Maliyet: $1.076,00 + 467,50 = \mathbf{1.543,50\text{ €}}$
   - Gerçek Üretim: **85 paket** `SUC-2026-045`
   - Gerçekleşen Birim Maliyet (EKP): $\frac{1.543,50}{85} = 18,158823...\text{ €} \longrightarrow \mathbf{18,16\text{ €/paket}}$.
7. **Jüri Kontrolü:** Hammadde bedelinin dış hizmet faturasına ikinci kez eklenmediğini ve kuruş yuvarlamasının doğruluğunu gösterin.

---

### Adım 2: Bütün Kuzu Parçalama ve Belge Tutarsızlığı Kontrolü

1. Web panelinde **Kuzu Parçalama** (`/butchering`) ekranına gidin.
2. `PRC-2026-001` kodlu parçalama emrini inceleyin.
3. **Kaynak Belge Tutarsızlığı Uyarısı:**
   - Sistem sarı/kırmızı bilgi rozetiyle şunu gösterir:
     > *"Kaynak Belge Tutarsızlığı: 25 kg kuzu × 11,50 €/kg = 287,50 € olup fatura tutarı 351,00 € beyan edilmiştir. Parça toplamı 22 kg olup 3 kg açıklanmamış kayıp/fire bulunmaktadır."*
   - Sistem bu tutarsızlığı gizlememiş veya sessizce düzeltmemiştir; `weight_variance_records` tablosuna gerekçeli olarak kaydetmiştir.
4. **Maliyet Dağıtımı Dengesi:**
   - But: 12 kg
   - Sırt: 6 kg
   - Omuz: 4 kg
   - Kemik/Fire: 3 kg
   - `BY_WEIGHT` yöntemiyle 351,00 € toplam maliyet kuruşu kuruşuna dağıtılmış, yuvarlama artığı deterministik olarak son satıra aktarılmıştır. Toplam dağıtılan maliyet tam 351,00 €'dur.

---

### Adım 3: Android Satış Uygulaması ve Dağıtım Akışı

1. Android uygulamasını açın ve `sales@avatar.demo` ile giriş yapın.
2. Ana ekranda "Katalog Senkronla" butonuna dokunun. `SUC-2026-045` lotunun 85 paket ve 24,00 € sabit liste fiyatıyla stokta olduğunu gösterin.
3. **Satış 1:** Market A'ya 30 paket satın.
4. **Satış 2:** Market B'ye 25 paket satın.
5. **Satış 3:** Market C'ye 30 paket satın.
   - Toplam sevk edilen miktar: $30 + 25 + 30 = \mathbf{85\text{ paket}}$.
   - Kalan stok: **0 paket**.
6. **Satış Geçmişi Ekranı:** Her satış satırının altında sunucudan dönen `stock_movement_id` değerini jüriye gösterin.

---

### Adım 4: Kritik Geri Çağırma (Recall) ve Blokaj Zinciri

1. Web paneline dönün ve `trace@avatar.demo` ile giriş yapın.
2. **Geri Çağırma Yönetimi** (`/recalls`) ekranına gidin.
3. `RCL-2026-001` kodlu kaydı açın:
   - Kaynak lot: `ET-2026-001` (Dana Eti).
   - Sebep: *"Mikrobiyolojik kalite güvence riski (DEMO)"*.
4. **İzlenebilirlik Şecere Analizi:**
   - Sistem ilişkisel grafikten anında şu zinciri çıkarır:
     - Kaynak Lot: `ET-2026-001`
     - Etkilenen Üretim Emri: `URT-2026-045`
     - Etkilenen Mamul Lotu: `SUC-2026-045` (85 paket)
     - Bilinen Sevkiyatlar ve Müşteriler:
       - **Market A:** 30 paket (Tel: +90 212 000 00 10)
       - **Market B:** 25 paket (Tel: +90 212 000 00 11)
       - **Market C:** 30 paket (Tel: +90 212 000 00 12)
5. **Geri Çağırmayı Aktive Et:** "Geri Çağırmayı Başlat (Aktive Et)" butonuna basın.
   - Mamul lotu `SUC-2026-045` atomik olarak **BLOKE** edilir.

---

### Adım 5: Mobil İstemcide Bloke Lot Satış Engeli Testi

1. Android uygulamasına dönün.
2. **Çevrimiçi Senkron Durumu:**
   - Senkron yapıldığında `SUC-2026-045` satılabilir listeden kaybolur; **Bloke Lotlar** sekmesinde kırmızı *"GERİ ÇAĞRILDI / BLOKE — SATIŞI YASAKTIR"* rozetiyle listelenir.
3. **Yarış Koşulu / Eski Önbellek Testi:**
   - Telefonun eski önbelleğe sahip olduğu (veya uçak modundayken) senaryoda satış ekranına gidip bloke lot satılmaya çalışıldığında:
   - İstemci doğrulayıcısı `SaleValidator` işlemi yerelde durdurur: *"Lot bloke edilmiştir; satışı yapılamaz."*
   - Zorla API isteği atıldığında backend `409 Conflict` ve `{"error": {"code": "LOT_BLOCKED"}}` döner.
   - Mobil satış kuyruğunda durum **REJECTED** olarak işaretlenir; stok asla düşmez.

---

### Adım 6: Yapay Zekâ (ML) Tahminleri ve Baseline Karşılaştırması

1. Web panelinde **Yapay Zekâ & Tahminler** ekranına gidin.
2. **Model A (Üretim Verimi & EKP):**
   - Model Adı: `RIDGE` / `GRADIENT_BOOSTING`
   - Baseline: `BASELINE_MEAN`
   - Çapraz Doğrulama İyileşmesi: **%37.94** MAE düşüşü.
   - Gerçekleşen 18,16 € EKP ile tahmin edilen 18,22 € EKP karşılaştırmasını ve %95 güven aralığını gösterin.
3. **Model B (Kuzu Parçalama Verimi):**
   - Model Adı: `RANDOM_FOREST`
   - Baseline: `BASELINE_ANIMAL_MEAN`
   - İyileşme: **%31.06** genel MAE düşüşü.
   - 25 kg kuzu için parça bazında (But: 12 kg, Sırt: 6 kg, Omuz: 4 kg) tahmin ve gerçekleşen grafiklerini gösterin.

---

## 3. Demo Kontrol Listesi

- [x] Üretim maliyeti ve EKP: 1.543,50 € / 85 = 18,16 € doğrulandı.
- [x] Kuzu parçalama: 287,50 € ≠ 351,00 € tutarsızlığı raporlandı, 351,00 € kuruşu kuruşuna dağıtıldı.
- [x] Android: SQLite Room yerel veritabanı, çevrimdışı kuyruk ve UUID idempotency çalışıyor.
- [x] Satış satırında lot, miktar, fiyat ve `stock_movement_id` saklanıyor.
- [x] Geri çağırma (Recall): Market A (30), Market B (25), Market C (30) doğru tespit edildi.
- [x] Bloke lotun satışı hem web hem mobil tarafında engellendi.
- [x] İki yapay zekâ modeli baseline'ları karşısında sırasıyla %37 ve %31 iyileşme gösterdi.
