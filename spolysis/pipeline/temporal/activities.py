"""Temporal activities exchange durable object keys, never local filesystem paths."""

from __future__ import annotations

import httpx
from temporalio import activity
from pipeline.config import settings


@activity.defn
async def notify_api(path: str, body: dict) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.internal_api_url}{path}",
            json=body,
            headers={"Authorization": f"Bearer {settings.internal_api_secret}"},
        )
        response.raise_for_status()


@activity.defn
async def analyze_video(params: dict) -> dict:
    import modal

    function = modal.Function.from_name("spolysis-pipeline", "run_full_pipeline")
    return await function.remote.aio(
        job_id=params["job_id"],
        r2_key=params["r2_key"],
        tier="premium",
        stroke_type=params["stroke_type"],
        handedness=params.get("handedness", "right"),
    )
