from __future__ import annotations
from pydantic import BaseModel
from typing import Literal
from datetime import datetime


class UploadUrlRequest(BaseModel):
    tier: Literal["free", "premium"]
    filename: str


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
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int


class UploadConfirmRequest(BaseModel):
    pass  # body is empty; job_id is in the path


class JobCompleteRequest(BaseModel):
    stroke_type: str
    fault_label: str | None = None
    confidence: float
    recommendation: str
    reference_clip_url: str | None = None


class JobPremiumCompleteRequest(BaseModel):
    stroke_type: str
    fault_label: str | None = None
    confidence: float
    recommendation: str
    overlay_video_url: str | None = None
    skeleton_3d_url: str | None = None
    delta_summary: dict | None = None
    fault_joints: list[str] | None = None
    reference_clip_url: str | None = None


class JobFailRequest(BaseModel):
    error_message: str


class JobRejectRequest(BaseModel):
    rejection_reason: str
