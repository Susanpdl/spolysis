from __future__ import annotations
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from pipeline.config import settings
from pipeline.temporal.workflows import TennisAnalysisWorkflow
from pipeline.temporal.activities import analyze_video, notify_api
import structlog

log = structlog.get_logger(__name__)


async def main() -> None:
    connect_kwargs: dict = dict(namespace=settings.temporal_namespace)
    if settings.temporal_api_key:
        connect_kwargs["api_key"] = settings.temporal_api_key
        connect_kwargs["tls"] = True
    client = await Client.connect(settings.temporal_host, **connect_kwargs)
    log.info(
        "temporal_worker_starting",
        host=settings.temporal_host,
        queue=settings.temporal_task_queue,
    )

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[TennisAnalysisWorkflow],
        activities=[analyze_video, notify_api],
    )
    log.info("temporal_worker_running")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
