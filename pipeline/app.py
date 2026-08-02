"""
Modal app definition for Spolysis pipeline.
Deploy with: modal deploy pipeline/app.py
"""
from __future__ import annotations
import modal

app = modal.App("spolysis-pipeline")

# GPU image: RTMPose-x pose estimation + PoseC3D classification
pose_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1", "libglib2.0-0", "ffmpeg")
    .pip_install(
        "mmpose==1.3.1",
        "mmaction2==0.11.0",
        "mmdet==3.3.0",
        "mmengine==0.10.4",
        "torch==2.3.1",
        "torchvision==0.18.1",
        "opencv-python-headless==4.10.0.84",
        "scipy==1.13.1",
        "numpy==1.26.4",
        "boto3==1.35.32",
        "structlog==24.4.0",
        "pydantic-settings==2.5.2",
        "httpx==0.27.2",
        "anthropic==0.34.2",
        "upstash-redis==1.3.0",
    )
)

R2_SECRET = modal.Secret.from_name("spolysis-r2")
ANTHROPIC_SECRET = modal.Secret.from_name("spolysis-anthropic")
API_SECRET = modal.Secret.from_name("spolysis-api")


def _notify(path: str, body: dict, api_base_url: str, internal_secret: str) -> None:
    """Synchronous HTTP notification to the FastAPI backend."""
    import httpx
    url = f"{api_base_url}{path}"
    headers = {"Authorization": f"Bearer {internal_secret}"}
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json=body, headers=headers)
        resp.raise_for_status()


@app.function(
    image=pose_image,
    gpu="A10G",
    timeout=600,
    secrets=[R2_SECRET, ANTHROPIC_SECRET, API_SECRET],
)
def run_full_pipeline(job_id: str, r2_key: str, tier: str) -> dict:
    """
    Run the complete Phase 1 pipeline for a single job on Modal GPU.
    Called directly via Modal (not through Temporal) for simple invocations.
    """
    import tempfile
    import numpy as np
    from pipeline.stages.extract import extract_frames
    from pipeline.stages.pose2d import run_pose_estimation
    from pipeline.stages.quality import check_quality
    from pipeline.stages.features import extract_features
    from pipeline.stages.segment import segment_strokes
    from pipeline.stages.classify import classify_stroke
    from pipeline.stages.lookup import lookup_reference_clip
    from pipeline.stages.recommend import generate_recommendation
    from pipeline.r2 import download_file, put_json
    from pipeline.config import settings

    def notify(path: str, body: dict) -> None:
        _notify(path, body, settings.api_base_url, settings.internal_api_secret)

    # 1. Download video from R2
    video_path = tempfile.mktemp(suffix=".mp4")
    download_file(r2_key, video_path)

    # 2. Extract frames at 30 fps
    frame_dir = tempfile.mkdtemp()
    extract_frames(video_path, fps=30.0, output_dir=frame_dir)

    # 3. RTMPose-x 2D pose estimation
    pose_result = run_pose_estimation(frame_dir)
    keypoints = pose_result.keypoints  # (T, 17, 3)
    put_json(f"artifacts/{job_id}/keypoints_2d.json", {"keypoints": keypoints.tolist()})

    # 4. Quality gate
    quality = check_quality(frame_dir, keypoints)
    if not quality.passed:
        notify(f"/internal/jobs/{job_id}/reject", {"rejection_reason": quality.reason})
        return {"status": "rejected", "reason": quality.reason}

    # 5. Features -> segment -> PoseC3D classify (heuristic if model not loaded)
    features = extract_features(keypoints)
    segment = segment_strokes(features)
    if segment is None:
        from pipeline.stages.classify import ClassificationResult
        classification = ClassificationResult(
            stroke_type="forehand", fault_label=None, confidence=0.5, method="heuristic"
        )
    else:
        classification = classify_stroke(
            segment,
            stroke_model_path=settings.posec3d_stroke_model,
            fault_model_path=settings.posec3d_fault_model,
        )

    # 6. Reference clip lookup + coaching text
    reference_clip_url = lookup_reference_clip(classification.stroke_type, classification.fault_label)
    recommendation = generate_recommendation(
        classification.stroke_type, classification.fault_label, classification.confidence
    )

    result = {
        "job_id": job_id,
        "stroke_type": classification.stroke_type,
        "fault_label": classification.fault_label,
        "confidence": classification.confidence,
        "recommendation": recommendation,
        "reference_clip_url": reference_clip_url,
    }
    put_json(f"results/{job_id}/result.json", result)

    notify(f"/internal/jobs/{job_id}/complete", {
        "stroke_type": result["stroke_type"],
        "fault_label": result["fault_label"],
        "confidence": result["confidence"],
        "recommendation": result["recommendation"],
        "reference_clip_url": result["reference_clip_url"],
    })

    return result
