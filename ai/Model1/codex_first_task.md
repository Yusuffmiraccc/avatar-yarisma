# Codex Görev Planı — AVATAR Model 1

Proje yolu: `D:\Coding\AVATAR Project\ai\Model1`
Önce `README_TR.md` dosyasını tamamen oku. Bu projede benchmark modeli ile gerçek AVATAR modelini kesinlikle birbirine karıştırma.

## Aşama 1 — Kurulum ve benchmark veri denetimi
1. Python ortamını kontrol et; `requirements.txt` paketlerini kurmadan önce komutu göster ve kullanıcı onayı bekle.
2. `python src/download_data.py` ve ardından `python src/audit_data.py` komutlarını çalıştır.
3. Ham CSV dosyalarını değiştirme; sentetik kayıtları gerçek olarak işaretleme.
4. Benchmark `train_production_model.py` dosyasının yalnızca fan/ısıtıcı verisi için demo olduğunu raporda açık tut.

## Aşama 2 — Eşik tabanlı gerçek model servisinin doğrulanması
1. `sql/001_ai_tables_mysql.sql` şemasını incele ve MySQL 8.0+ uyumluluğunu kontrol et.
2. `.env.example` alanlarının açık parolalar içermediğinden emin ol. Gerçek `.env` dosyasını Git'e ekleme.
3. API sözleşmesini kontrol et: üretim öncesi `/ai/production-forecast`, yalnızca tamamlanmış/onaylanmış gerçek üretim sonrası `/ai/production-records`.
4. Eğitim verisi olarak `ai_production_training_records` tablosundaki yalnızca `actual + completed + validated` kayıtları kullan.
5. İlk gerçek eğitim eşiğinin 100 kayıt, sonraki her deneme için eşiğin son denemeden itibaren 50 yeni kayıt olduğunu koru.
6. Aday modeli tarih sıralı holdout üzerinde baseline ve varsa aktif modelle karşılaştır. Aday daha iyi değilse aktif modeli değiştirme.
7. `python -m unittest discover -s tests -v` ve `python -m compileall -q src tests` çalıştır.
8. MySQL bağlantısı sağlanmadıysa API/worker'ın uçtan uca çalıştığını iddia etme; bağlantı ve migration gereksinimlerini raporla.

Önemli: Gerçek AVATAR backend'i bu paketin dışında. Kullanıcı onayı olmadan ana backend dosyalarını veya MySQL veritabanını değiştirme. Backend tamamlanma handler'ının `POST /ai/production-records` çağrısını yapması gerektiğini açıklayarak bekle.
