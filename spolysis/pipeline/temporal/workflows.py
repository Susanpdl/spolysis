from __future__ import annotations
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from pipeline.temporal.activities import (
        WorkflowParams,
        download_video,
        extract_frames_activity,
        run_pose_estimation_activity,
        quality_gate_activity,
        extract_features_activity,
        classify_activity,
        generate_result_activity,
        run_premium_pipeline_activity,
        _notify_api,
    )

_RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=10))
_NO_RETRY = RetryPolicy(maximum_attempts=1)


@workflow.defn
class TennisAnalysisWorkflow:
    @workflow.run
    async def run(self, params: dict) -> None:
        p = WorkflowParams(
            job_id=params["job_id"],
            r2_key=params["r2_key"],
            tier=params["tier"],
        )
        job_id = p.job_id

        try:
            # Download video
            video_path = await workflow.execute_activity(
                download_video,
                p,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY,
            )

            # Extract frames
            frame_dir = await workflow.execute_activity(
                extract_frames_activity,
                args=[video_path, job_id],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY,
            )

            # 2D pose estimation (GPU)
            keypoints_key = await workflow.execute_activity(
                run_pose_estimation_activity,
                args=[frame_dir, job_id],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=_RETRY,
            )

            # Quality gate
            passed = await workflow.execute_activity(
                quality_gate_activity,
                args=[frame_dir, keypoints_key, job_id],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=_NO_RETRY,
            )
            if not passed:
                return  # API already notified of rejection

            if p.tier == "premium":
                # Full 3D premium path - activity handles its own API notification
                await workflow.execute_activity(
                    run_premium_pipeline_activity,
                    args=[keypoints_key, frame_dir, job_id],
                    start_to_close_timeout=timedelta(minutes=20),
                    retry_policy=_RETRY,
                )
            else:
                # Free tier path: features -> classify -> generate result + notify API
                features_key = await workflow.execute_activity(
                    extract_features_activity,
                    args=[keypoints_key, job_id],
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY,
                )

                classification = await workflow.execute_activity(
                    classify_activity,
                    args=[features_key, job_id],
                    start_to_close_timeout=timedelta(minutes=3),
                    retry_policy=_RETRY,
                )

                await workflow.execute_activity(
                    generate_result_activity,
                    args=[classification, job_id],
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY,
                )

        except ActivityError as e:
            workflow.logger.error("workflow_activity_failed", job_id=job_id, error=str(e))
            await workflow.execute_activity(
                _notify_api,
                args=[f"/internal/jobs/{job_id}/fail", {"error_message": str(e)}],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_RETRY,
            )
