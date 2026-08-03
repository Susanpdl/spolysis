from __future__ import annotations
import structlog
from fastapi import APIRouter, Depends
from api.auth import verify_internal_token
from api.models.job import JobCompleteRequest, JobFailRequest, JobRejectRequest
from api.database import service_client
from api.redis_client import invalidate_job_cache

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(verify_internal_token)],
)


def _safe_db(fn):
    """Wrap a DB call; log and swallow errors so notifications never return 500."""
    try:
        fn()
    except Exception as e:
        log.error("internal_db_error", error=str(e))


@router.post("/jobs/{job_id}/complete", status_code=200)
async def complete_job(job_id: str, body: JobCompleteRequest):
    _safe_db(lambda: service_client.table("results").insert({
        "job_id": job_id,
        "stroke_type": body.stroke_type,
        "fault_label": body.fault_label,
        "confidence": body.confidence,
        "recommendation": body.recommendation,
        "reference_clip_url": body.reference_clip_url,
    }).execute())
    _safe_db(lambda: service_client.table("jobs").update({"status": "completed"}).eq("id", job_id).execute())
    _safe_db(lambda: invalidate_job_cache(job_id))
    return {"status": "ok"}


@router.post("/jobs/{job_id}/fail", status_code=200)
async def fail_job(job_id: str, body: JobFailRequest):
    _safe_db(lambda: service_client.table("jobs").update({
        "status": "failed",
        "error_message": body.error_message,
    }).eq("id", job_id).execute())
    _safe_db(lambda: invalidate_job_cache(job_id))
    return {"status": "ok"}


@router.post("/jobs/{job_id}/reject", status_code=200)
async def reject_job(job_id: str, body: JobRejectRequest):
    _safe_db(lambda: service_client.table("jobs").update({
        "status": "rejected",
        "rejection_reason": body.rejection_reason,
    }).eq("id", job_id).execute())
    _safe_db(lambda: invalidate_job_cache(job_id))
    return {"status": "ok"}
