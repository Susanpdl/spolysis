from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime


class ResultResponse(BaseModel):
    job_id: str
    stroke_type: str
    fault_label: str | None = None
    confidence: float
    recommendation: str
    reference_clip_url: str | None = None
    overlay_video_url: str | None = None
    created_at: datetime
