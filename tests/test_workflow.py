"""Workflow branch contracts with isolated activity execution, not a Temporal server."""

import asyncio
from datetime import timedelta
from unittest.mock import Mock

import pytest
from temporalio.exceptions import ActivityError, TimeoutError, TimeoutType
from pipeline.temporal import workflows


@pytest.mark.parametrize("queue_timeout", [False, True])
@pytest.mark.parametrize(
    "stage", ["processing", "analyze", "complete_premium", "reject"]
)
def test_only_analysis_failures_send_failure_callback(
    monkeypatch, stage, queue_timeout
):
    calls = []
    failure = ActivityError(
        "activity exhausted retries",
        scheduled_event_id=1,
        started_event_id=2,
        identity="test",
        activity_type="test",
        activity_id="test",
        retry_state=None,
    )

    if queue_timeout:
        failure.__cause__ = TimeoutError(
            "No activity worker",
            type=TimeoutType.SCHEDULE_TO_START,
            last_heartbeat_details=[],
        )

    async def execute(activity, *args, **kwargs):
        step = (
            "analyze"
            if activity == workflows.analyze_video
            else kwargs["args"][0].rsplit("/", 1)[-1]
        )
        calls.append(step)
        assert kwargs["schedule_to_start_timeout"] == timedelta(minutes=5)
        if step == "fail":
            assert kwargs["args"][1] == {
                "error_message": workflows.PLAYER_SERVICE_FAILURE
            }
        if step == stage:
            raise failure
        if step == "analyze":
            return (
                {"status": "rejected", "reason": "Full body required"}
                if stage == "reject"
                else {"status": "completed"}
            )

    monkeypatch.setattr(workflows.workflow, "execute_activity", execute)
    monkeypatch.setattr(workflows.workflow, "logger", Mock())
    with pytest.raises(ActivityError) as caught:
        asyncio.run(workflows.TennisAnalysisWorkflow().run({"job_id": "job"}))
    assert caught.value is failure
    assert ("fail" in calls) == (stage in {"processing", "analyze"})
