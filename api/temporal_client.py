from __future__ import annotations
from datetime import timedelta
from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError
from api.config import settings

_client: Client | None = None


async def get_temporal_client() -> Client:
    global _client
    if _client is None:
        connect_kwargs: dict = dict(namespace=settings.temporal_namespace)
        if settings.temporal_api_key:
            connect_kwargs["api_key"] = settings.temporal_api_key
            connect_kwargs["tls"] = True
        _client = await Client.connect(settings.temporal_host, **connect_kwargs)
    return _client


async def start_analysis_workflow(
    job_id: str, r2_key: str, tier: str, stroke_type: str, handedness: str
) -> str:
    client = await get_temporal_client()
    workflow_id = f"tennis-analysis-{job_id}"
    try:
        await client.start_workflow(
            "TennisAnalysisWorkflow",
            {
                "job_id": job_id,
                "r2_key": r2_key,
                "tier": "premium",
                "stroke_type": stroke_type,
                "handedness": handedness,
            },
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
            # Covers two 35-minute attempts, queue waits, and callback retries.
            execution_timeout=timedelta(hours=2),
        )
    except WorkflowAlreadyStartedError:
        pass
    return workflow_id
