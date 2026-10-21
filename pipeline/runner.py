"""One 3D analysis implementation shared by Modal and integration tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
import numpy as np

from pipeline.stages.pose2d import run_pose_estimation, Pose2DResult
from pipeline.stages.extract import extract_frames
from pipeline.stages.quality import check_quality
from pipeline.stages.lift import lift_to_3d
from pipeline.stages.smooth3d import smooth_3d
from pipeline.stages.normalize3d import normalize_skeleton
from pipeline.stages.phases import detect_phases
from pipeline.stages.align import align_to_reference
from pipeline.stages.delta import compute_deltas
from pipeline.stages.ik import apply_ik_correction
from pipeline.stages.render import render_overlay
from pipeline.stages.recommend import recommend_3d
from pipeline import r2
from pipeline.config import settings

_SWAP = [0, 2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16, 15]


def mirror_pose(pose: np.ndarray) -> np.ndarray:
    mirrored = pose[:, _SWAP].copy()
    mirrored[..., 0] *= -1
    return mirrored


def run_analysis(
    job_id: str,
    r2_key: str,
    stroke_type: str,
    handedness: str = "right",
    reference_motion_dir: str = "data/reference_motion",
) -> dict:
    if stroke_type not in {"forehand", "backhand", "serve", "volley"}:
        raise ValueError("Choose the stroke type before uploading")
    if handedness not in {"right", "left"}:
        raise ValueError("Invalid handedness")
    result_key = f"results/{job_id}/result.json"
    if r2.key_exists(result_key):
        return r2.get_json(result_key)
    with tempfile.TemporaryDirectory(prefix="spolysis-") as work:
        video = str(Path(work) / "input.mp4")
        frame_dir = str(Path(work) / "frames")
        r2.download_file(r2_key, video)
        try:
            extract_frames(video, output_dir=frame_dir)
        except ValueError as exc:
            return {"status": "rejected", "reason": str(exc)}
        pose = run_pose_estimation(frame_dir)
        quality = check_quality(frame_dir, pose.keypoints)
        if not quality.passed:
            return {"status": "rejected", "reason": quality.reason}

        # Analyse the strongest swing, with 1.5 seconds of context on each side.
        # This bounds reconstruction and alignment without mislabelling a rally
        # as a single continuous stroke.
        wrist = 9 if handedness == "left" else 10
        speed = np.linalg.norm(np.diff(pose.keypoints[:, wrist, :2], axis=0), axis=1)
        body_height = np.median(np.ptp(pose.keypoints[:, 5:, 1], axis=1))
        if len(speed) < 30 or np.percentile(speed, 95) < max(2, body_height * 0.01):
            return {
                "status": "rejected",
                "reason": "No clear swing found. Record one complete stroke with your whole body visible.",
            }
        from scipy.ndimage import median_filter

        peak = int(np.argmax(median_filter(speed, size=5))) + 1
        start, end = max(0, peak - 45), min(len(pose.keypoints), peak + 46)
        pose = Pose2DResult(
            pose.keypoints[start:end],
            pose.frame_paths[start:end],
            pose.bboxes[start:end],
        )
        r2.put_json(
            f"artifacts/{job_id}/keypoints_2d.json",
            {
                "schema_version": 1,
                "start_frame": start,
                "keypoints": pose.keypoints.tolist(),
            },
        )
        lifted = lift_to_3d(pose, checkpoint=settings.motionbert_checkpoint)
        smoothed = smooth_3d(
            lifted.keypoints_3d, smoothnet_checkpoint=settings.smoothnet_checkpoint
        )
        original = smoothed.keypoints_3d
        analysis_pose = mirror_pose(original) if handedness == "left" else original
        normalized = normalize_skeleton(analysis_pose)
        phases = detect_phases(normalized.keypoints_3d, stroke_type)
        alignment = align_to_reference(
            normalized.keypoints_3d, phases, stroke_type, reference_motion_dir
        )
        deltas = compute_deltas(
            alignment.user_seq, alignment.ref_seq, phases, stroke_type
        )
        corrected = apply_ik_correction(normalized, deltas, phases)
        corrected_pose = (
            mirror_pose(corrected.keypoints_3d)
            if handedness == "left"
            else corrected.keypoints_3d
        )
        original_pose = (
            mirror_pose(normalized.keypoints_3d)
            if handedness == "left"
            else normalized.keypoints_3d
        )
        overlay = str(Path(work) / "overlay.mp4")
        render_overlay(
            pose.frame_paths,
            corrected_pose,
            pose.keypoints,
            pose.bboxes,
            normalized.root_trajectory,
            corrected.blend_weights,
            overlay,
            original_3d=original_pose,
        )
        overlay_key = f"results/{job_id}/overlay.mp4"
        skeleton_key = f"results/{job_id}/skeleton_3d.json"
        r2.upload_file(overlay, overlay_key, "video/mp4")
        r2.put_json(
            skeleton_key,
            {
                "schema_version": 1,
                "fps": 30,
                "coordinate_system": "coco17_y_up_relative",
                "start_frame": start,
                "contact_frame": phases.contact,
                "frames": corrected_pose.tolist(),
                "original_frames": original_pose.tolist(),
                "blend_weights": corrected.blend_weights.tolist(),
            },
        )
        # Confidence describes observed body keypoints, not clinical/model accuracy.
        confidence = float(np.clip(pose.keypoints[:, 5:, 2].mean(), 0, 1))

        def display_joint(name: str) -> str:
            if handedness == "right":
                return name
            return (
                name.replace("right_", "other_")
                .replace("left_", "right_")
                .replace("other_", "left_")
            )

        result = {
            "stroke_type": stroke_type,
            "fault_label": display_joint(deltas.fault_joints[0])
            if deltas.fault_joints
            else None,
            "confidence": confidence,
            "recommendation": recommend_3d(deltas, handedness),
            "overlay_video_url": overlay_key,
            "skeleton_3d_url": skeleton_key,
            "delta_summary": {display_joint(k): v for k, v in deltas.summary.items()},
            "fault_joints": [display_joint(k) for k in deltas.fault_joints],
        }
        r2.put_json(result_key, result)
        return result
