# Backend security operations

## Login rate limiting

Login attempt counters are stored in Redis and reserved/finished with atomic Lua scripts, so workers and API containers share the same account and IP limits. The Redis service is internal to the Compose network, password-protected, configured with append-only persistence, a 128 MB cap, and `noeviction`; when Redis cannot enforce the limit (including memory exhaustion), login fails closed with a generic 503. Redis credentials must be unique and strong outside local development. An external Redis deployment must provide equivalent access control, persistence, capacity, and availability.

## ML artifacts

Model artifacts use joblib, which serializes Python objects with pickle semantics. Loading an artifact from an untrusted or tamperable source can execute arbitrary code. Only load artifacts produced by this backend's training path and stored in the configured `ML_DIR`; do not accept artifact uploads or copy files from untrusted sources into that directory. In the container, the directory is owned by the unprivileged `avatar` service account and is restricted to that account.

Model training runs synchronously in an API worker. A process and OS file lock prevents concurrent workers from replacing the same artifacts at once, but a large training dataset can occupy a request worker for minutes. A bounded background job system may be needed if training demand grows.

## Expired records

Idempotency responses are retained for 24 hours. Legacy rows without `expires_at` use `created_at + 24 hours`. Refresh sessions are purged only after every token in a family has expired. Run `python scripts/purge.py --dry-run` from `backend/` to inspect eligible counts, then `python scripts/purge.py` to remove them. Anomaly alerts, audit events, and ML predictions are retained and are not removed by this command.
