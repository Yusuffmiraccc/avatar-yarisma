from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AVATAR API"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "mysql+pymysql://avatar:change-me@localhost:3306/avatar_db?charset=utf8mb4"
    log_level: str = "INFO"
    jwt_secret_key: SecretStr = SecretStr("unsafe-local-placeholder-change-before-use")
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    ml_dir: str = "ml_artifacts"
    weight_tolerance_kg: str = "0.000"  # proje konfigürasyonu; kaynak PDF değeri değildir


@lru_cache
def get_settings() -> Settings:
    return Settings()
