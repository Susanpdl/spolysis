from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket_name: str = "spolysis"
    r2_public_url: str = ""

    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "tennis-analysis"

    anthropic_api_key: str = ""
    internal_api_url: str = "https://spolysis-api.fly.dev"
    internal_api_secret: str

    temporal_api_key: str = ""

    # PoseC3D model checkpoints - local paths or R2-downloaded paths.
    # When None, the heuristic classifier is used as fallback.
    posec3d_stroke_model: str | None = None
    posec3d_fault_model: str | None = None

    # 3D lifting model
    lift_model: str = "motionbert"  # "motionbert" | "posemamba"
    motionbert_checkpoint: str | None = None   # None = use default /opt/weights/motionbert/MB_ft_h36m.bin
    posemamba_checkpoint: str | None = None

    # SmoothNet
    smoothnet_checkpoint: str | None = None   # None = skip SmoothNet, use SavGol only

    # Reference motion directory for DTW alignment
    reference_motion_dir: str = "data/reference_motion"

    sentry_dsn: str = ""


settings = Settings()
