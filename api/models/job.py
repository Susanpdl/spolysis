from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class UploadUrlRequest(BaseModel):
    tier: Literal["premium"] = "premium"
    filename: str = Field(min_length=1, max_length=255)
    stroke_type: Literal["forehand", "backhand", "serve", "volley"]
    handedness: Literal["right", "left"] = "right"
    content_type: Literal["video/mp4", "video/quicktime"] = "video/mp4"


class UploadUrlResponse(BaseModel):
    upload_url: str
    r2_key: str
    job_id: str


class JobResponse(BaseModel):
    id: str
    tier: str
    status: str
    rejection_reason: str | None = None
    error_message: str | None = None
    handedness: Literal["right", "left"] | None = None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int


class JobPremiumCompleteRequest(BaseModel):
    stroke_type: str
    fault_label: str | None = None
    fault_phase: str | None = None
    fault_phases: dict[str, str] | None = None
    confidence: float = Field(ge=0, le=1)
    recommendation: str
    overlay_video_url: str
    skeleton_3d_url: str
    delta_summary: dict[str, float]
    fault_joints: list[str]
    reference_clip_url: str | None = None


class JobFailRequest(BaseModel):
    error_message: str


class JobRejectRequest(BaseModel):
    rejection_reason: str
