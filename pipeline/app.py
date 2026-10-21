"""
Modal app definition for Spolysis pipeline.
Deploy with: modal deploy pipeline/app.py
"""

from __future__ import annotations
import modal

app = modal.App("spolysis-pipeline")

# GPU image: RTMPose-x pose estimation + MotionBERT reconstruction
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
    )
    .pip_install(
        "opencv-python-headless==4.10.0.84",
        "scipy==1.13.1",
        "boto3==1.35.32",
        "structlog==24.4.0",
        "pydantic-settings==2.5.2",
        "httpx==0.27.2",
        "temporalio==1.7.1",
        "dtaidistance==2.3.12",
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
    .run_commands(
        # MotionBERT: pin the official full model source and H36M checkpoint
        "mkdir -p /opt/motionbert/lib/model",
        "wget -q -O /opt/motionbert/lib/model/DSTformer.py https://huggingface.co/walterzhu/MotionBERT/resolve/370a9196aa3c89198b134c82476143b01c0fb32c/lib/model/DSTformer.py",
        "wget -q -O /opt/motionbert/lib/model/drop.py https://huggingface.co/walterzhu/MotionBERT/resolve/370a9196aa3c89198b134c82476143b01c0fb32c/lib/model/drop.py",
        "mkdir -p /opt/weights/motionbert /opt/weights/smoothnet",
        "wget -q --show-progress -O /opt/weights/motionbert/MB_ft_h36m.bin "
        "'https://huggingface.co/walterzhu/MotionBERT/resolve/370a9196aa3c89198b134c82476143b01c0fb32c/checkpoint/pose3d/FT_MB_release_MB_ft_h36m/best_epoch.bin'",
    )
    .env({"PYTHONPATH": "/opt/motionbert"})
    .add_local_python_source("pipeline")
    .add_local_dir("data/reference_motion", remote_path="/opt/reference_motion")
)

PIPELINE_SECRET = modal.Secret.from_name("spolysis-secrets")


@app.function(image=pose_image, gpu="A10G", timeout=1800, secrets=[PIPELINE_SECRET])
def run_full_pipeline(
    job_id: str,
    r2_key: str,
    tier: str = "premium",
    stroke_type: str = "forehand",
    handedness: str = "right",
    reference_motion_dir: str = "/opt/reference_motion",
) -> dict:
    if tier not in {"premium", "3d"}:
        raise ValueError("Unsupported analysis tier; expected 'premium' or '3d'")
    from pipeline.runner import run_analysis

    return run_analysis(job_id, r2_key, stroke_type, handedness, reference_motion_dir)
