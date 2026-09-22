from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from api.auth import get_current_user
from api.models.job import JobResponse, JobListResponse
from api.models.result import ResultResponse
from api.database import service_client
from api.redis_client import get_cached_job_status, cache_job_status
from datetime import datetime

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _parse_job(row: dict) -> JobResponse:
    return JobResponse(
        id=row["id"],
        tier=row["tier"],
        status=row["status"],
        rejection_reason=row.get("rejection_reason"),
        error_message=row.get("error_message"),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    offset = (page - 1) * page_size
    result = (
        service_client.table("jobs")
        .select("*", count="exact")
        .eq("user_id", user["user_id"])
        .order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )
    jobs = [_parse_job(r) for r in result.data]
    return JobListResponse(jobs=jobs, total=result.count or 0, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    cached = get_cached_job_status(job_id)
    if cached:
        return JobResponse(**cached)

    result = (
        service_client.table("jobs")
        .select("*")
        .eq("id", job_id)
        .eq("user_id", user["user_id"])
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _parse_job(result.data)
    cache_job_status(job_id, job.model_dump(mode="json"))
    return job


@router.get("/{job_id}/result", response_model=ResultResponse)
async def get_job_result(job_id: str, user: dict = Depends(get_current_user)):
    job_result = (
        service_client.table("jobs")
        .select("id, status")
        .eq("id", job_id)
        .eq("user_id", user["user_id"])
        .single()
        .execute()
    )
    if not job_result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    if job_result.data["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed (status: {job_result.data['status']})",
        )

    result = (
        service_client.table("results")
        .select("*")
        .eq("job_id", job_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Result not found")

    r = result.data
    return ResultResponse(
        job_id=r["job_id"],
        stroke_type=r["stroke_type"],
        fault_label=r.get("fault_label"),
        confidence=r["confidence"],
        recommendation=r["recommendation"],
        reference_clip_url=r.get("reference_clip_url"),
        overlay_video_url=r.get("overlay_video_url"),
        skeleton_3d_url=r.get("skeleton_3d_url"),
        delta_summary=r.get("delta_summary"),
        fault_joints=r.get("fault_joints"),
        created_at=datetime.fromisoformat(r["created_at"]),
    )
