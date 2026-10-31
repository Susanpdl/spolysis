from __future__ import annotations
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from pipeline.temporal.activities import analyze_video, notify_api

# Bound queue waits separately from execution time when activity workers disappear.
_QUEUE_WAIT = timedelta(minutes=5)
_RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=10))

# Service failures are not a recapture problem. The clip can be retried later.
PLAYER_SERVICE_FAILURE = (
    "Analysis could not finish. Retry this clip, or try again later."
)


@workflow.defn
class TennisAnalysisWorkflow:
    @workflow.run
    async def run(self, params: dict) -> None:
        job_id = params["job_id"]
        try:
            await workflow.execute_activity(
                notify_api,
                args=[f"/internal/jobs/{job_id}/processing", {}],
                schedule_to_start_timeout=_QUEUE_WAIT,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=_RETRY,
            )
            result = await workflow.execute_activity(
                analyze_video,
                params,
                schedule_to_start_timeout=_QUEUE_WAIT,
                start_to_close_timeout=timedelta(minutes=35),
                retry_policy=RetryPolicy(
                    maximum_attempts=2, initial_interval=timedelta(seconds=30)
                ),
            )
        except ActivityError:
            workflow.logger.exception("Analysis failed for %s", job_id)
            await workflow.execute_activity(
                notify_api,
                args=[
                    f"/internal/jobs/{job_id}/fail",
                    {"error_message": PLAYER_SERVICE_FAILURE},
                ],
                schedule_to_start_timeout=_QUEUE_WAIT,
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=_RETRY,
            )
            raise

        # Delivery failure does not mean analysis failed. Preserve the outcome
        # for callback retry instead of replacing it with a failure callback.
        if result.get("status") == "rejected":
            path, body = "reject", {"rejection_reason": result["reason"]}
        else:
            path, body = "complete_premium", result
        await workflow.execute_activity(
            notify_api,
            args=[f"/internal/jobs/{job_id}/{path}", body],
            schedule_to_start_timeout=_QUEUE_WAIT,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=_RETRY,
        )
