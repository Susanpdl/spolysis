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
    """
    Create a job record and return a presigned R2 upload URL.
    The client uploads directly to R2, then calls POST /uploads/{job_id}/confirm.
    The Temporal workflow does NOT start here - it starts only after confirm.
    """
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
    return UploadUrlResponse(upload_url=upload_url, r2_key=r2_key, job_id=job_id)


@router.post("/{job_id}/confirm", status_code=200)
async def confirm_upload(job_id: str, user: dict = Depends(get_current_user)):
    """
    Called by the client after the R2 upload completes.
    Starts the Temporal analysis workflow.
    """
    result = (
        service_client.table("jobs")
        .select("id, tier, video_r2_key, status")
        .eq("id", job_id)
        .eq("user_id", user["user_id"])
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    job = result.data
    if job["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Job already in status '{job['status']}'")

    try:
        workflow_id = await start_analysis_workflow(job_id, job["video_r2_key"], job["tier"])
        service_client.table("jobs").update({"temporal_run_id": workflow_id}).eq("id", job_id).execute()
    except Exception as e:
        service_client.table("jobs").update(
            {"status": "failed", "error_message": str(e)}
        ).eq("id", job_id).execute()
        raise HTTPException(status_code=500, detail="Failed to start analysis workflow")

    return {"status": "ok"}
