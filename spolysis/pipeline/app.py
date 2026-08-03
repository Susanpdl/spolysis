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
    .apt_install("libgl1", "libglib2.0-0", "ffmpeg", "git", "build-essential", "wget")
    # torch 2.1.0 + CUDA 12.1: the OpenMMLab CDN has a pre-built mmcv 2.1.0 CUDA wheel
    # ONLY for torch2.1.0 (not 2.2 or 2.3). The wheel is installed via direct URL in the
    # final run_commands to bypass Modal's local PyPI mirror (which serves the CPU-only sdist
    # regardless of -f find-links flags, causing the NMS CUDA ops to be missing at runtime).
    .pip_install(
        "torch==2.1.0",
        "torchvision==0.16.0",
        extra_index_url="https://download.pytorch.org/whl/cu121",
    )
    .pip_install("openmim==0.3.9", "numpy==1.26.4", "Cython")
    .run_commands(
        "mim install mmengine==0.10.4",
        "mim install mmdet==3.3.0",
        "mim install mmpose==1.3.1",
        "mim install mmaction2==1.2.0",
    )
    .pip_install(
        "opencv-python-headless==4.10.0.84",
        "scipy==1.13.1",
        "boto3==1.35.32",
        "structlog==24.4.0",
        "pydantic-settings==2.5.2",
        "httpx==0.27.2",
        "anthropic==0.34.2",
        "upstash-redis==1.3.0",
        "temporalio==1.7.1",
    )
    # Final layer: re-pin numpy, build xtcocotools from source, and install the mmcv
    # CUDA wheel via a DIRECT URL (not -f find-links). Direct URL pip installs bypass
    # Modal's local PyPI mirror, which only serves the CPU-only mmcv sdist.
    # The OpenMMLab cu121/torch2.1.0 wheel is pre-compiled with CUDA NMS ops.
    .run_commands(
        "pip install 'numpy==1.26.4' --force-reinstall --no-deps",
        "pip install xtcocotools --no-binary xtcocotools --no-deps --force-reinstall",
        "pip install 'https://download.openmmlab.com/mmcv/dist/cu121/torch2.1.0/"
        "mmcv-2.1.0-cp311-cp311-manylinux1_x86_64.whl' --force-reinstall --no-deps",
        # RTMPose-x is in projects/rtmpose (not main mmpose configs), not in mim download db.
        # Download config + weights directly; config uses mmpose:: prefix for base refs
        # which resolves from the installed mmpose package at runtime.
        "mkdir -p /opt/mmpose",
        "wget -q -O /opt/mmpose/rtmpose-x_8xb256-700e_coco-384x288.py "
        "https://raw.githubusercontent.com/open-mmlab/mmpose/main/"
        "projects/rtmpose/rtmpose/body_2d_keypoint/rtmpose-x_8xb256-700e_coco-384x288.py",
        "wget -q --show-progress -O /opt/mmpose/rtmpose-x_body7.pth "
        "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/"
        "rtmpose-x_simcc-body7_pt-body7_700e-384x288-71d7b7e9_20230629.pth",
        # Pre-download RTMDet person detector weights into torch.hub cache so
        # MMPoseInferencer finds them locally instead of downloading at cold-start.
        "mkdir -p /root/.cache/torch/hub/checkpoints",
        "wget -q --show-progress "
        "-O /root/.cache/torch/hub/checkpoints/rtmdet_m_8xb32-100e_coco-obj365-person-235e8209.pth "
        "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/"
        "rtmdet_m_8xb32-100e_coco-obj365-person-235e8209.pth",
    )
    .add_local_python_source("pipeline")
)

PIPELINE_SECRET = modal.Secret.from_name("spolysis-secrets")


def _notify(path: str, body: dict, internal_api_url: str, internal_secret: str) -> None:
    """Synchronous HTTP notification to the FastAPI backend."""
    import httpx
    url = f"{internal_api_url}{path}"
    headers = {"Authorization": f"Bearer {internal_secret}"}
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json=body, headers=headers)
        resp.raise_for_status()


@app.function(
    image=pose_image,
    gpu="A10G",
    timeout=600,
    secrets=[PIPELINE_SECRET],
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
        _notify(path, body, settings.internal_api_url, settings.internal_api_secret)

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


@app.function(
    image=pose_image,
    gpu="A10G",
    timeout=3600,
    secrets=[PIPELINE_SECRET],
    min_containers=1,
)
async def run_temporal_worker() -> None:
    """Long-running Temporal worker - always polling the tennis-analysis queue."""
    from pipeline.temporal.worker import main
    await main()
