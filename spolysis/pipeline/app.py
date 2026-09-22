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
        "dtaidistance",
        "einops",
        "timm",
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
        # MotionBERT: clone repo and download H36M lite weights
        "git clone --depth=1 https://github.com/Walter0807/MotionBERT.git /opt/motionbert || true",
        "pip install einops timm --quiet || true",
        "mkdir -p /opt/weights/motionbert /opt/weights/smoothnet",
        "wget -q --show-progress -O /opt/weights/motionbert/MB_ft_h36m.bin "
        "'https://github.com/Walter0807/MotionBERT/releases/download/v1.0/MotionBERT_lite_MB_ft_h36m.bin' || true",
    )
    .env({"PYTHONPATH": "/opt/motionbert"})
    .add_local_python_source("pipeline")
    .add_local_dir("data/reference_motion", remote_path="/opt/reference_motion")
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
def run_full_pipeline(
    job_id: str,
    r2_key: str,
    tier: str,
    reference_motion_dir: str = "/opt/reference_motion",
) -> dict:
    """
    Run the complete pipeline for a single job on Modal GPU.
    Called directly via Modal (not through Temporal) for simple invocations.
    Branches on tier: "free"/"2d" runs the 2D path; "premium"/"3d" runs the full 3D path.
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
    from pipeline.r2 import download_file, put_json, upload_file
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
    keypoints_payload: dict = {"keypoints": keypoints.tolist()}
    if pose_result.bboxes is not None:
        keypoints_payload["bboxes"] = pose_result.bboxes.tolist()
    put_json(f"artifacts/{job_id}/keypoints_2d.json", keypoints_payload)

    # 4. Quality gate
    quality = check_quality(frame_dir, keypoints)
    if not quality.passed:
        notify(f"/internal/jobs/{job_id}/reject", {"rejection_reason": quality.reason})
        return {"status": "rejected", "reason": quality.reason}

    if tier in ("premium", "3d"):
        # --- Full 3D premium path ---
        from pipeline.stages.pose2d import Pose2DResult
        from pipeline.stages.lift import lift_to_3d
        from pipeline.stages.smooth3d import smooth_3d
        from pipeline.stages.normalize3d import normalize_skeleton
        from pipeline.stages.phases import detect_phases
        from pipeline.stages.align import align_to_reference
        from pipeline.stages.delta import compute_deltas
        from pipeline.stages.ik import apply_ik_correction
        from pipeline.stages.render import render_overlay

        # Reconstruct bboxes if not available on pose_result
        if pose_result.bboxes is not None:
            bboxes = pose_result.bboxes
        else:
            T = keypoints.shape[0]
            bboxes = np.zeros((T, 4), dtype=np.float32)
            for t in range(T):
                frame_kps = keypoints[t]
                visible = frame_kps[frame_kps[:, 2] > 0.1]
                if len(visible) > 0:
                    bboxes[t] = [visible[:, 0].min(), visible[:, 1].min(),
                                 visible[:, 0].max(), visible[:, 1].max()]

        pose2d = Pose2DResult(keypoints=keypoints, bboxes=bboxes, frame_paths=pose_result.frame_paths)

        # 3D lifting
        checkpoint = (
            settings.motionbert_checkpoint
            if settings.lift_model == "motionbert"
            else settings.posemamba_checkpoint
        )
        lift_result = lift_to_3d(pose2d, model_name=settings.lift_model, checkpoint=checkpoint)

        # Smoothing
        smooth_result = smooth_3d(lift_result.keypoints_3d, smoothnet_checkpoint=settings.smoothnet_checkpoint)

        # Normalization
        normalized = normalize_skeleton(smooth_result.keypoints_3d)

        # Feature extraction + classification for stroke type
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

        stroke_type = classification.stroke_type
        fault_label = classification.fault_label
        confidence = classification.confidence

        # Phase detection
        phases = detect_phases(normalized.keypoints_3d, stroke_type=stroke_type)

        # DTW alignment vs pro reference motion
        alignment = align_to_reference(
            normalized.keypoints_3d,
            phases,
            stroke_type=stroke_type,
            reference_dir=reference_motion_dir,
        )

        # Biomechanical delta computation
        delta_table = compute_deltas(alignment.user_seq, alignment.ref_seq, phases, stroke_type)

        # CCD IK correction (flawed joints only)
        corrected = apply_ik_correction(normalized, delta_table, phases)

        # Render overlay video onto original frames
        overlay_tmp = tempfile.mktemp(suffix=".mp4", prefix=f"spolysis_overlay_{job_id}_")
        render_overlay(
            frame_paths=pose_result.frame_paths,
            corrected_3d=corrected.keypoints_3d,
            original_2d_kps=keypoints,
            bboxes=bboxes,
            root_trajectory=normalized.root_trajectory,
            blend_weights=corrected.blend_weights,
            output_path=overlay_tmp,
        )

        # Upload overlay video to R2
        overlay_r2_key = f"results/{job_id}/overlay.mp4"
        upload_file(overlay_tmp, overlay_r2_key, content_type="video/mp4")

        # Upload corrected 3D skeleton JSON for Three.js viewer
        skeleton_r2_key = f"results/{job_id}/skeleton_3d.json"
        put_json(skeleton_r2_key, {
            "job_id": job_id,
            "stroke_type": stroke_type,
            "fps": 30,
            "frames": corrected.keypoints_3d.tolist(),
        })

        # Coaching recommendation
        first_fault_joint = delta_table.fault_joints[0] if delta_table.fault_joints else fault_label
        recommendation = generate_recommendation(stroke_type, first_fault_joint, confidence)

        r2_public_url = settings.r2_public_url.rstrip("/")
        result = {
            "job_id": job_id,
            "stroke_type": stroke_type,
            "fault_label": first_fault_joint,
            "confidence": confidence,
            "recommendation": recommendation,
            "overlay_video_url": f"{r2_public_url}/results/{job_id}/overlay.mp4",
            "skeleton_3d_url": f"{r2_public_url}/results/{job_id}/skeleton_3d.json",
            "delta_summary": delta_table.summary,
            "fault_joints": delta_table.fault_joints,
        }

        notify(f"/internal/jobs/{job_id}/complete_premium", {
            "stroke_type": stroke_type,
            "fault_label": first_fault_joint,
            "confidence": confidence,
            "recommendation": recommendation,
            "overlay_video_url": result["overlay_video_url"],
            "skeleton_3d_url": result["skeleton_3d_url"],
            "delta_summary": delta_table.summary,
            "fault_joints": delta_table.fault_joints,
        })

        return result

    else:
        # --- Free tier 2D path ---
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
