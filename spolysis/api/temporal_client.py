from __future__ import annotations
from temporalio.client import Client
from api.config import settings

_client: Client | None = None


async def get_temporal_client() -> Client:
    global _client
    if _client is None:
        _client = await Client.connect(
            settings.temporal_host,
            namespace=settings.temporal_namespace,
        )
    return _client


async def start_analysis_workflow(job_id: str, r2_key: str, tier: str) -> str:
    client = await get_temporal_client()
    handle = await client.start_workflow(
        "TennisAnalysisWorkflow",
        args=[{"job_id": job_id, "r2_key": r2_key, "tier": tier}],
        id=f"tennis-analysis-{job_id}",
        task_queue=settings.temporal_task_queue,
    )
    return handle.id
