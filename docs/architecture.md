# AVATAR — Hedef Mimari

Geçerli kararlar için `docs/SOZLESME.md` esas alınır. Ayrıntılar `docs/handoff/` altındadır.

## Bileşenler

- **Android (`android/`):** Kotlin, Jetpack Compose, Room/SQLite, Retrofit. Online-first: satış backend onayı olmadan tamamlanmaz. SQLite ürün/lot önbelleği ve oturum durumunu tutar. Çevrimdışı satış kuyruğu kapsam dışıdır (ADR-001).
- **Backend (`backend/`):** Python, FastAPI, SQLAlchemy 2.x, Alembic, PyMySQL. REST `/api/v1`, OpenAPI. İş kuralları servis katmanında, transaction sınırı servis katmanında.
- **Merkezi veritabanı (MySQL 8.4):** Tek doğruluk kaynağı. Şema Alembic ile yönetilir.
- **Web (`web/`):** React, TypeScript, Vite. Yönetim ve raporlama.
- **AI/ML (`backend/app/ml`):** scikit-learn ile üretim verimi/EKP ve parçalama verimi tahmini. Backend içinde modül; hata durumunda operasyonel akışlar etkilenmez.
- **Testler (`tests/`, `backend/tests`):** birim, entegrasyon, kontrat, eşzamanlılık ve uçtan uca demo.

## SQLite–MySQL tutarlılığı

MySQL tek doğruluk kaynağıdır. Android SQLite'ı yalnızca önbellek olarak kullanır: oturum açınca ürün/lot listesi çekilir, her satış öncesi backend stok ve recall durumunu yeniden doğrular. Satış `Idempotency-Key` ile gönderilir; tekrar gönderim çift stok hareketi üretmez. Bu sayede çevrimdışı çakışma yönetimi gerekmez.

## Veri akışı

Android ve web yalnızca REST API ile konuşur. API doğrulama, yetki ve iş kurallarını uygular; stok defteri (`stock_movements`) ve bakiye (`inventory_balances`) aynı transaction'da güncellenir. Lot izleme ve geri çağırma kesin kayıt ilişkilerine dayanır; AI tahmini bunların kaynağı değildir.

## Güvenlik sınırları

- İstemciler MySQL'e bağlanmaz.
- JWT: access 15 dk, refresh 7 gün rotation; roller `ADMIN`, `OPERATOR`, `SALES`, `TRACEABILITY_MANAGER`, `VIEWER`; deny-by-default izin kontrolü.
- Gizli değerler yalnız yerel `.env` içinde; `.env.example` yer tutucu taşır.
- Android token'ı Keystore ile korunur.
