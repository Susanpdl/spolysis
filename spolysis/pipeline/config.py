from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket_name: str = "spolysis"

    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "tennis-analysis"

    internal_api_url: str = "https://spolysis-api.fly.dev"
    internal_api_secret: str

    temporal_api_key: str = ""

    # Reconstruction model checkpoint
    motionbert_checkpoint: str | None = (
        None  # None = use default /opt/weights/motionbert/MB_ft_h36m.bin
    )

    # SmoothNet
    smoothnet_checkpoint: str | None = None  # None = skip SmoothNet, use SavGol only


settings = Settings()
