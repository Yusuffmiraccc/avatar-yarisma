from functools import lru_cache
from urllib.parse import unquote, urlsplit

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AVATAR API"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "mysql+pymysql://avatar:change-me@localhost:3306/avatar_db?charset=utf8mb4"
    redis_url: SecretStr = SecretStr("redis://:change-me-local-only@localhost:6379/0")
    log_level: str = "INFO"
    jwt_secret_key: SecretStr = SecretStr("unsafe-local-placeholder-change-before-use")
    ml_signing_secret: SecretStr | None = None
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    ml_dir: str = "ml_artifacts"
    weight_tolerance_kg: str = "0.000"  # proje konfigürasyonu; kaynak PDF değeri değildir
    trusted_proxy_ips: str = ""

    @model_validator(mode="after")
    def validate_security_settings(self):
        if self.environment.strip().lower() != "local":
            secret = self.jwt_secret_key.get_secret_value()
            if (secret.startswith(("unsafe-", "local-dev-secret-change-me")) or len(secret) < 32):
                raise RuntimeError("JWT_SECRET_KEY must be configured with at least 32 characters outside local.")
            if self.ml_signing_secret is None:
                raise RuntimeError("ML_SIGNING_SECRET must be configured outside local.")
            ml_secret = self.ml_signing_secret.get_secret_value()
            if (ml_secret.startswith(("unsafe-", "local-dev-secret-change-me")) or len(ml_secret) < 32):
                raise RuntimeError("ML_SIGNING_SECRET must be configured with at least 32 characters outside local.")
            if secret == ml_secret:
                raise RuntimeError("ML_SIGNING_SECRET must not reuse JWT_SECRET_KEY outside local (Key Separation).")
            db_password = unquote(urlsplit(self.database_url).password or "")
            if not db_password or db_password in {"change-me", "change-me-local-only", "change-root-local-only"}:
                raise RuntimeError("DATABASE_URL must not use a default password outside local.")
            redis = urlsplit(self.redis_url.get_secret_value())
            redis_password = unquote(redis.password or "")
            if (redis.scheme not in {"redis", "rediss"} or not redis.hostname or not redis_password
                    or redis_password in {"change-me", "change-me-local-only"}):
                raise RuntimeError("REDIS_URL must use an authenticated Redis connection outside local.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
