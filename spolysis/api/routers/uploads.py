from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from api.auth import get_current_user
from api.models.job import UploadUrlRequest, UploadUrlResponse
from api.r2 import generate_upload_url
from api.database import service_client
from api.temporal_client import start_analysis_workflow
import uuid

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/url", response_model=UploadUrlResponse, status_code=201)
async def get_upload_url(body: UploadUrlRequest, user: dict = Depends(get_current_user)):
    job_id = str(uuid.uuid4())
    r2_key = f"raw/{job_id}/video.mp4"

    try:
        service_client.table("jobs").insert({
            "id": job_id,
            "user_id": user["user_id"],
            "tier": body.tier,
            "status": "pending",
            "video_r2_key": r2_key,
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {e}")

    upload_url = generate_upload_url(r2_key)

    try:
        await start_analysis_workflow(job_id, r2_key, body.tier)
    except Exception as e:
        service_client.table("jobs").update(
            {"status": "failed", "error_message": str(e)}
        ).eq("id", job_id).execute()
        raise HTTPException(status_code=500, detail="Failed to start analysis workflow")

    return UploadUrlResponse(upload_url=upload_url, r2_key=r2_key, job_id=job_id)
