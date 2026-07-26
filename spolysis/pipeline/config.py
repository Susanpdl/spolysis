from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket_name: str = "spolysis"
    r2_public_url: str

    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "tennis-analysis"

    anthropic_api_key: str
    api_base_url: str = "https://api.spolysis.com"
    internal_api_secret: str

    sentry_dsn: str = ""


settings = Settings()
