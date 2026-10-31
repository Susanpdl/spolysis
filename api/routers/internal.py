from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from api.auth import verify_internal_token
from api.models.job import JobFailRequest, JobRejectRequest, JobPremiumCompleteRequest
from api.database import service_client
from api.redis_client import invalidate_job_cache

router = APIRouter(
    prefix="/internal", tags=["internal"], dependencies=[Depends(verify_internal_token)]
)


def _job(job_id: str) -> dict:
    rows = (
        service_client.table("jobs").select("id,status").eq("id", job_id).execute().data
    )
    if not rows:
        raise HTTPException(404, "Job not found")
    return rows[0]


@router.post("/jobs/{job_id}/processing")
def processing_job(job_id: str):
    _job(job_id)
    service_client.table("jobs").update({"status": "processing"}).eq("id", job_id).eq(
        "status", "pending"
    ).execute()
    invalidate_job_cache(job_id)
    return {"status": "ok"}


@router.post("/jobs/{job_id}/complete_premium")
def complete_premium_job(job_id: str, body: JobPremiumCompleteRequest):
    job = _job(job_id)
    if job["status"] in {"failed", "rejected"}:
        raise HTTPException(409, "Job is already terminal")
    # Upsert makes a repeated Temporal callback safe. A database failure must
    # propagate so Temporal retries instead of reporting a nonexistent result.
    service_client.table("results").upsert(
        {"job_id": job_id, **body.model_dump()}, on_conflict="job_id"
    ).execute()
    # Recheck in the write itself: another callback may have failed or rejected
    # the job while the result was being saved. Never revive a terminal job.
    updated = (
        service_client.table("jobs")
        .update({"status": "completed", "error_message": None})
        .eq("id", job_id)
        .in_("status", ["pending", "processing", "completed"])
        .execute()
    )
    if not updated.data:
        raise HTTPException(409, "Job is already terminal")
    invalidate_job_cache(job_id)
    return {"status": "ok"}


@router.post("/jobs/{job_id}/fail")
def fail_job(job_id: str, body: JobFailRequest):
    _job(job_id)
    # Completion may have persisted its result before its status write failed.
    # Leave that outcome recoverable by the idempotent completion callback.
    if (
        service_client.table("results")
        .select("job_id")
        .eq("job_id", job_id)
        .execute()
        .data
    ):
        return {"status": "ok"}
    service_client.table("jobs").update(
        {
            "status": "failed",
            "error_message": body.error_message,
        }
    ).eq("id", job_id).in_("status", ["pending", "processing"]).execute()
    invalidate_job_cache(job_id)
    return {"status": "ok"}


@router.post("/jobs/{job_id}/reject")
def reject_job(job_id: str, body: JobRejectRequest):
    _job(job_id)
    service_client.table("jobs").update(
        {
            "status": "rejected",
            "rejection_reason": body.rejection_reason,
        }
    ).eq("id", job_id).in_("status", ["pending", "processing"]).execute()
    invalidate_job_cache(job_id)
    return {"status": "ok"}
