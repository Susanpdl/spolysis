from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from api.auth import get_current_user
from api.rate_limit import limiter
from api.models.job import UploadUrlRequest, UploadUrlResponse
from api.r2 import InvalidUploadError, generate_upload_url, verify_upload
from api.database import service_client
from api.temporal_client import start_analysis_workflow
import uuid
import logging

router = APIRouter(prefix="/uploads", tags=["uploads"])
logger = logging.getLogger(__name__)


@router.post("/url", response_model=UploadUrlResponse, status_code=201)
@limiter.limit("10/minute")
async def get_upload_url(
    request: Request, body: UploadUrlRequest, user: dict = Depends(get_current_user)
):
    """
    Create a job record and return a presigned R2 upload URL.
    The client uploads directly to R2, then calls POST /uploads/{job_id}/confirm.
    The Temporal workflow does NOT start here - it starts only after confirm.
    """
    job_id = str(uuid.uuid4())
    r2_key = f"raw/{job_id}/video.mp4"

    try:
        service_client.table("jobs").insert(
            {
                "id": job_id,
                "user_id": user["user_id"],
                "tier": "premium",
                "stroke_type": body.stroke_type,
                "handedness": body.handedness,
                "status": "pending",
                "video_r2_key": r2_key,
            }
        ).execute()
    except Exception:
        raise HTTPException(
            status_code=500, detail="Could not create analysis. Please try again."
        )

    upload_url = generate_upload_url(r2_key, body.content_type)
    return UploadUrlResponse(upload_url=upload_url, r2_key=r2_key, job_id=job_id)


@router.post("/{job_id}/confirm", status_code=200)
async def confirm_upload(job_id: str, user: dict = Depends(get_current_user)):
    """
    Called by the client after the R2 upload completes.
    Starts the Temporal analysis workflow.
    """
    result = (
        service_client.table("jobs")
        .select("id, tier, video_r2_key, status, stroke_type, handedness")
        .eq("id", job_id)
        .eq("user_id", user["user_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    job = result.data[0]
    if job["status"] != "pending":
        return {"status": job["status"]}

    try:
        verify_upload(job["video_r2_key"])
    except InvalidUploadError:
        raise HTTPException(
            status_code=400,
            detail="Video upload is missing or invalid. Upload an MP4 or MOV under 500 MB.",
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not check the saved video. Retry starting the analysis without uploading again.",
        )

    try:
        workflow_id = await start_analysis_workflow(
            job_id,
            job["video_r2_key"],
            "premium",
            job["stroke_type"],
            job["handedness"],
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not confirm analysis start. Retry starting the analysis without uploading again.",
        )

    # Temporal has accepted the durable workflow. This metadata is not required
    # for callbacks, which identify the job directly.
    try:
        service_client.table("jobs").update({"temporal_run_id": workflow_id}).eq(
            "id", job_id
        ).execute()
    except Exception:
        logger.warning(
            "Workflow started but metadata could not be saved for job %s", job_id
        )

    return {"status": "ok"}
