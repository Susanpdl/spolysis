from __future__ import annotations
import os
import tempfile
import numpy as np
import httpx
from dataclasses import dataclass
from temporalio import activity
import structlog
from pipeline.config import settings

log = structlog.get_logger(__name__)


@dataclass
class WorkflowParams:
    job_id: str
    r2_key: str
    tier: str


@activity.defn
async def _notify_api(path: str, body: dict) -> None:
    url = f"{settings.internal_api_url}{path}"
    headers = {"Authorization": f"Bearer {settings.internal_api_secret}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()


@activity.defn
async def download_video(params: WorkflowParams) -> str:
    """Download video from R2 to a temp file. Returns local path."""
    from pipeline.r2 import download_file

    tmp = tempfile.mktemp(suffix=".mp4", prefix=f"spolysis_{params.job_id}_")
    log.info("downloading_video", job_id=params.job_id, r2_key=params.r2_key)
    download_file(params.r2_key, tmp)
    return tmp


@activity.defn
async def extract_frames_activity(video_path: str, job_id: str) -> str:
    """Extract frames from video. Returns frame directory path."""
    from pipeline.stages.extract import extract_frames

    frame_dir = tempfile.mkdtemp(prefix=f"spolysis_frames_{job_id}_")
    log.info("extracting_frames", job_id=job_id)
    result = extract_frames(video_path, fps=30.0, output_dir=frame_dir)
    log.info("frames_extracted", count=result.frame_count)
    return frame_dir


@activity.defn
async def run_pose_estimation_activity(frame_dir: str, job_id: str) -> str:
    """Run RTMPose-x. Saves keypoints to R2. Returns R2 key."""
    from pipeline.stages.pose2d import run_pose_estimation
    from pipeline.r2 import put_json

    log.info("pose_estimation", job_id=job_id)
    result = run_pose_estimation(frame_dir)

    # Save to R2 as JSON (convert ndarray to list)
    r2_key = f"artifacts/{job_id}/keypoints_2d.json"
    put_json(r2_key, {
        "keypoints": result.keypoints.tolist(),
        "frame_count": result.keypoints.shape[0],
    })
    log.info("keypoints_saved", r2_key=r2_key, shape=result.keypoints.shape)
    return r2_key


@activity.defn
async def quality_gate_activity(frame_dir: str, keypoints_r2_key: str, job_id: str) -> bool:
    """
    Run quality gate. Returns True if passed.
    Calls /internal/jobs/{job_id}/reject if failed.
    """
    from pipeline.stages.quality import check_quality
    from pipeline.r2 import get_json

    log.info("quality_gate", job_id=job_id)
    data = get_json(keypoints_r2_key)
    keypoints = np.array(data["keypoints"], dtype=np.float32)

    result = check_quality(frame_dir, keypoints)
    if not result.passed:
        log.info("quality_gate_failed", reason=result.reason)
        await _notify_api(f"/internal/jobs/{job_id}/reject", {"rejection_reason": result.reason})
        return False

    log.info("quality_gate_passed")
    return True


@activity.defn
async def extract_features_activity(keypoints_r2_key: str, job_id: str) -> str:
    """Extract features from keypoints. Saves to R2. Returns R2 key."""
    from pipeline.stages.features import extract_features
    from pipeline.r2 import get_json, put_json

    data = get_json(keypoints_r2_key)
    keypoints = np.array(data["keypoints"], dtype=np.float32)

    features = extract_features(keypoints)
    r2_key = f"artifacts/{job_id}/features.json"
    put_json(r2_key, {
        "wrist_velocity": features.wrist_velocity_smooth.tolist(),
        "keypoints_norm": features.keypoints_norm.tolist(),
        "frame_count": features.frame_count,
    })
    return r2_key


@activity.defn
async def classify_activity(features_r2_key: str, job_id: str) -> dict:
    """Segment and classify stroke. Returns classification dict."""
    from pipeline.stages.features import FeatureSet
    from pipeline.stages.segment import segment_strokes
    from pipeline.stages.classify import classify_stroke
    from pipeline.utils.skeleton import compute_joint_angles
    from pipeline.r2 import get_json

    data = get_json(features_r2_key)
    keypoints_norm = np.array(data["keypoints_norm"], dtype=np.float32)
    wrist_vel = np.array(data["wrist_velocity"], dtype=np.float32)
    T = keypoints_norm.shape[0]

    angles_list = [compute_joint_angles(keypoints_norm[t, :, :2]) for t in range(T)]
    features = FeatureSet(
        keypoints_norm=keypoints_norm,
        velocities=np.zeros((T, 17), dtype=np.float32),
        wrist_velocity_smooth=wrist_vel,
        joint_angles_per_frame=angles_list,
        frame_count=T,
    )
    segment = segment_strokes(features)

    if segment is None:
        return {"stroke_type": "forehand", "fault_label": None, "confidence": 0.5, "method": "heuristic"}

    result = classify_stroke(
        segment,
        stroke_model_path=settings.posec3d_stroke_model,
        fault_model_path=settings.posec3d_fault_model,
    )
    return {
        "stroke_type": result.stroke_type,
        "fault_label": result.fault_label,
        "confidence": result.confidence,
        "method": result.method,
    }


@activity.defn
async def generate_result_activity(classification: dict, job_id: str) -> dict:
    """Lookup clip, generate recommendation, post result to API."""
    from pipeline.stages.lookup import lookup_reference_clip
    from pipeline.stages.recommend import generate_recommendation
    from pipeline.r2 import put_json

    stroke_type = classification["stroke_type"]
    fault_label = classification.get("fault_label")
    confidence = classification["confidence"]

    reference_clip_url = lookup_reference_clip(stroke_type, fault_label)
    recommendation = generate_recommendation(stroke_type, fault_label, confidence)

    result = {
        "job_id": job_id,
        "stroke_type": stroke_type,
        "fault_label": fault_label,
        "confidence": confidence,
        "recommendation": recommendation,
        "reference_clip_url": reference_clip_url,
    }

    put_json(f"results/{job_id}/result.json", result)

    await _notify_api(f"/internal/jobs/{job_id}/complete", {
        "stroke_type": stroke_type,
        "fault_label": fault_label,
        "confidence": confidence,
        "recommendation": recommendation,
        "reference_clip_url": reference_clip_url,
    })

    log.info("job_completed", job_id=job_id, stroke=stroke_type, fault=fault_label)
    return result
