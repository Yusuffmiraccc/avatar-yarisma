# AVATAR Backend

FastAPI + SQLAlchemy 2 + Alembic + MySQL 8.4. Kararlar için `../docs/SOZLESME.md`, mimari için `../docs/architecture.md`.

## Hızlı başlangıç (Docker)

```bash
cd backend
docker compose up -d                 # MySQL + API (http://localhost:8000/api/v1/docs)
docker compose exec api python -m scripts.seed_demo   # DEMO verisi: ET-2026-001 senaryosu, kuzu, sentetik geçmiş, model eğitimi
```

Demo girişi: `admin@avatar.demo` / `Avatar-Demo-2026!` (yalnızca demo; `DEMO_PASSWORD` ile değiştirilebilir).
Diğer roller: `operator@`, `sales@`, `trace@`, `viewer@avatar.demo` (aynı parola).

## Yerel geliştirme

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -e ".[dev]"
copy .env.example .env                                # DATABASE_URL: localhost:3307
docker compose up -d mysql
alembic upgrade head
python -m scripts.seed_demo
uvicorn app.main:app --reload
python -m scripts.export_openapi                      # ../contract/openapi.json
```

## Test

```bash
pytest -q          # gerçek MySQL (docker compose up -d mysql) gerekir; avatar_test veritabanını kendisi oluşturur
```

Kapsam (56 test): auth/refresh rotation, kullanıcı yönetimi, izin matrisi parity (her endpoint korumalı), stok defteri, üretim+EKP (1543,50 / 85 = 18,1588), parçalama+fire+tolerans, BY_VALUE fail-closed,
satış/dispatch/idempotency, ileri-geri izleme, recall + **recall–dispatch yarış testi**, ML baseline karşılaştırması,
anomali/defter bütünlüğü, düzeltme/ters kayıt (üretim, parçalama, müşteri iadesi), yeniden işleme, fatura/irsaliye okuma
(insan onaylı), Android senkron anlık görüntüsü, migration–ORM parity.

## Önemli kurallar

- Fiziksel stok `OUT` yalnızca dispatch'te (satış da dispatch üretir). Defter append-only; düzeltme ters harekettir.
- Satış ve dispatch `Idempotency-Key` ister. Aynı anahtar+gövde → ilk yanıt; farklı gövde → `409 IDEMPOTENCY_KEY_REUSED`.
- Recall aktivasyonu senkron/atomiktir; `RESOLVED` blokajı kaldırmaz, `POST /lots/{id}/unblock` (`lots:unblock`) gerekir.
- Ağırlık toleransı `WEIGHT_TOLERANCE_KG` (demo 0.000). Aşım: `butchering:approve_variance` yetkisi + gerekçe.
- AI tahmini operasyonel gerçeğin kaynağı değildir; ML hatası stok/izlenebilirlik akışlarını etkilemez.

## Bilinen sınırlamalar

- ML modelleri sentetik DEMO geçmişle eğitilir; gerçek veriyle yeniden eğitilmeden performans iddiası yoktur.
- Fatura/irsaliye okuma kural tabanlıdır (.txt/.csv/.pdf metni); görüntüler için istemci tarafı OCR metni gönderilir. Her zaman insan onayı gerekir.
- Anomali taraması kural/z-skoru tabanlıdır.
- Giriş hız sınırı süreç belleğindedir (tek instance demo).
- İkinci kademe dağıtım yalnızca kayıtlıysa gösterilir.

## Belgeler

- `docs/DATA_MODEL.md`, `docs/API.md`: koddan üretilir (`python -m scripts.gen_docs`).
- `contract/openapi.json`: web ve Android DTO üretimi için tek kaynak (`python -m scripts.export_openapi`).
