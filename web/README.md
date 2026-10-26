# AVATAR Web Yönetim Paneli

React yönetim paneli FastAPI uygulamasına `contract/openapi.json` ile tanımlanan `/api/v1` sözleşmesi üzerinden bağlanır. İstek/yanıt tipleri `src/api/generated.ts` dosyasına OpenAPI'den üretilir.

## Yerel geliştirme

Gereksinimler: Node.js 20+ ve pnpm.

```powershell
pnpm install
Copy-Item .env.example .env.local
pnpm run typegen
pnpm dev
```

Vite varsayılan olarak `http://127.0.0.1:5173` adresinde açılır. API adresi `.env.local` içindeki `VITE_API_BASE_URL` ile değiştirilebilir. Backend'i ve demo verisini kök `backend/README.md` içindeki adımlarla başlatın; demo yönetici girişi de orada açıklanmıştır.

## Komutlar

```powershell
pnpm run build
pnpm test
pnpm run test:e2e
```

Playwright uçtan uca kabul senaryosu backend'i değiştirmemek için API sözleşmesini tarayıcı rotalarıyla taklit eder. Gerçek servis entegrasyonu için backend'i ayrıca başlatıp demo senaryo verisini yükleyin.

## Oturum ve güvenlik notu

Backend'in mevcut OpenAPI sözleşmesi yenileme anahtarını `/auth/refresh` ve `/auth/logout` istek gövdesinde taşıyor; CORS yapılandırması da credential-cookie akışını açmıyor. Bu yüzden panel kısa ömürlü erişim anahtarını bellekte, yenileme anahtarını sekme kapanınca silinen `sessionStorage` içinde tutar. `docs/SOZLESME.md` belgesinde geçen HttpOnly cookie/CSRF akışı mevcut çalışan backend ile uyuşmuyor. Backend sözleşmesi cookie tabanlı hale getirildiğinde panelin oturum katmanı da buna göre güncellenmelidir.

## Bilinen veri sınırları

- Alış görünümü kabul edilmiş lot kayıtlarından oluşturulur; API'de ayrı bir alış raporu endpoint'i yoktur. Lot kodu araması sunucu tarafında yapılır; tedarikçi ve kabul tarihi süzgeçleri API'de karşılığı olmadığı için açık olan sayfada uygulanır.
- Belge önerileri metinden veya en fazla 5 MB boyutundaki PDF/CSV/TXT dosyalarından oluşturulur. Taranmış PDF'ler için OCR metnini metin alanına aktarın; dosya yükleme tek başına OCR yapmaz.
- Et ve kuzu EKP/VKP göstergeleri maliyet izni olan kullanıcılara gösterilir. Tutar ve miktar hesapları ondalık hassasiyetle yapılır.
- Yapay zekâ önerileri karar desteği olarak sunulur. Otomatik fiyat, blokaj kaldırma veya stok hareketi başlatılmaz.
- İkinci kademe market dağıtımı API'de kayıtlı değilse panel bunu tahmin etmez.
