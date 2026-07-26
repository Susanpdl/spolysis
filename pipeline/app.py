"""
Modal app definition for Spolysis pipeline.
Deploy with: modal deploy pipeline/app.py
"""
from __future__ import annotations
import modal

app = modal.App("spolysis-pipeline")

# GPU image for pose estimation (RTMPose-x)
pose_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1", "libglib2.0-0", "ffmpeg")
    .pip_install(
        "mmpose==1.3.1",
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

# Lightweight CPU image for feature/classification stages
cpu_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        "torch==2.3.1",
        "scipy==1.13.1",
        "numpy==1.26.4",
        "opencv-python-headless==4.10.0.84",
        "boto3==1.35.32",
        "structlog==24.4.0",
        "pydantic-settings==2.5.2",
        "httpx==0.27.2",
        "anthropic==0.34.2",
    )
)

R2_SECRET = modal.Secret.from_name("spolysis-r2")
ANTHROPIC_SECRET = modal.Secret.from_name("spolysis-anthropic")
API_SECRET = modal.Secret.from_name("spolysis-api")


@app.function(image=pose_image, gpu="A10G", timeout=600, secrets=[R2_SECRET, ANTHROPIC_SECRET, API_SECRET])
def run_full_pipeline(job_id: str, r2_key: str, tier: str) -> dict:
    """
    Run the complete Phase 1 pipeline for a single job.
    Called directly (not via Temporal) for Modal-native invocation.
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
    from pipeline.r2 import download_file, put_json, get_public_url
    import httpx
    from pipeline.config import settings

    async def notify(path: str, body: dict) -> None:
        url = f"{settings.api_base_url}{path}"
        headers = {"Authorization": f"Bearer {settings.internal_api_secret}"}
        import asyncio
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(url, json=body, headers=headers)

    import asyncio

    # 1. Download
    video_path = tempfile.mktemp(suffix=".mp4")
    download_file(r2_key, video_path)

    # 2. Extract frames
    frame_dir = tempfile.mkdtemp()
    frame_result = extract_frames(video_path, fps=30.0, output_dir=frame_dir)

    # 3. Pose estimation
    pose_result = run_pose_estimation(frame_dir)
    keypoints = pose_result.keypoints
    put_json(f"artifacts/{job_id}/keypoints_2d.json", {"keypoints": keypoints.tolist()})

    # 4. Quality gate
    quality = check_quality(frame_dir, keypoints)
    if not quality.passed:
        asyncio.run(notify(f"/internal/jobs/{job_id}/reject", {"rejection_reason": quality.reason}))
        return {"status": "rejected", "reason": quality.reason}

    # 5. Features + segment + classify
    features = extract_features(keypoints)
    segment = segment_strokes(features)
    if segment is None:
        classification_result = type("R", (), {"stroke_type": "forehand", "fault_label": None, "confidence": 0.5, "method": "heuristic"})()
    else:
        classification_result = classify_stroke(segment)

    # 6. Lookup + recommend
    reference_clip_url = lookup_reference_clip(classification_result.stroke_type, classification_result.fault_label)
    recommendation = generate_recommendation(classification_result.stroke_type, classification_result.fault_label, classification_result.confidence)

    result = {
        "job_id": job_id,
        "stroke_type": classification_result.stroke_type,
        "fault_label": classification_result.fault_label,
        "confidence": classification_result.confidence,
        "recommendation": recommendation,
        "reference_clip_url": reference_clip_url,
    }
    put_json(f"results/{job_id}/result.json", result)

    asyncio.run(notify(f"/internal/jobs/{job_id}/complete", {
        "stroke_type": result["stroke_type"],
        "fault_label": result["fault_label"],
        "confidence": result["confidence"],
        "recommendation": result["recommendation"],
        "reference_clip_url": result["reference_clip_url"],
    }))

    return result
