from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field

import numpy as np
import structlog

from pipeline.utils.skeleton import (
    L_SHOULDER, R_SHOULDER,
    L_ELBOW, R_ELBOW,
    L_WRIST, R_WRIST,
    L_HIP, R_HIP,
    L_KNEE, R_KNEE,
    L_ANKLE, R_ANKLE,
)

log = structlog.get_logger(__name__)

# Bone definitions as (joint_a_index, joint_b_index) pairs.
# Spine is handled separately because it connects computed midpoints, not
# individual joints, so it cannot be expressed as a simple index pair.
_BONE_PAIRS: dict[str, tuple[int, int]] = {
    "left_upper_arm":  (L_SHOULDER, L_ELBOW),
    "right_upper_arm": (R_SHOULDER, R_ELBOW),
    "left_forearm":    (L_ELBOW, L_WRIST),
    "right_forearm":   (R_ELBOW, R_WRIST),
    "left_thigh":      (L_HIP, L_KNEE),
    "right_thigh":     (R_HIP, R_KNEE),
    "left_shin":       (L_KNEE, L_ANKLE),
    "right_shin":      (R_KNEE, R_ANKLE),
    "shoulder_width":  (L_SHOULDER, R_SHOULDER),
    "hip_width":       (L_HIP, R_HIP),
}

_STABLE_WINDOW = 10  # frames used for "most stable" bone length measurement


@dataclass
class NormalizedSkeleton:
    keypoints_3d: np.ndarray       # (T, 17, 3) root-centered, bone-lengths locked to subject
    bone_lengths: dict[str, float] = field(default_factory=dict)  # bone name -> length in mm
    root_trajectory: np.ndarray = field(default_factory=lambda: np.zeros((0, 3)))  # (T, 3)


def _find_stable_window(keypoints_3d: np.ndarray) -> slice:
    """
    Find the 10-frame window with lowest total joint-position variance.

    We measure bone lengths in the least-dynamic window to avoid measuring
    a limb mid-swing where lifter output has the highest temporal error.
    Using per-joint position variance as the stability proxy is cheap and
    correlates well with frames where the subject is relatively still or
    in a stance phase.
    """
    T = keypoints_3d.shape[0]
    if T <= _STABLE_WINDOW:
        return slice(0, T)

    best_start = 0
    best_var = np.inf

    for start in range(T - _STABLE_WINDOW + 1):
        window = keypoints_3d[start : start + _STABLE_WINDOW]
        # Sum of per-joint variance across xyz - scalar per window
        var = float(window.var(axis=0).sum())
        if var < best_var:
            best_var = var
            best_start = start

    return slice(best_start, best_start + _STABLE_WINDOW)


def _measure_bone_lengths(keypoints_3d: np.ndarray) -> dict[str, float]:
    """
    Measure bone lengths in the most stable window.

    Takes the mean across frames in the stable window rather than a single
    frame to average out residual lifter jitter.
    """
    stable = _find_stable_window(keypoints_3d)
    window = keypoints_3d[stable]  # (W, 17, 3)

    bone_lengths: dict[str, float] = {}

    for bone_name, (idx_a, idx_b) in _BONE_PAIRS.items():
        diffs = window[:, idx_a, :] - window[:, idx_b, :]  # (W, 3)
        lengths = np.linalg.norm(diffs, axis=1)             # (W,)
        bone_lengths[bone_name] = float(lengths.mean())

    # Spine: midpoint(hips) to midpoint(shoulders)
    hip_mid = (window[:, L_HIP, :] + window[:, R_HIP, :]) / 2.0       # (W, 3)
    shoulder_mid = (window[:, L_SHOULDER, :] + window[:, R_SHOULDER, :]) / 2.0  # (W, 3)
    spine_lengths = np.linalg.norm(shoulder_mid - hip_mid, axis=1)     # (W,)
    bone_lengths["spine"] = float(spine_lengths.mean())

    return bone_lengths


def normalize_skeleton(keypoints_3d: np.ndarray) -> NormalizedSkeleton:
    """
    Normalize a 3D skeleton sequence to a canonical root-centered frame.

    This stage does two things and nothing more:
      1. Centers every frame on the hip midpoint root so downstream DTW and
         delta computation are translation-invariant.
      2. Measures subject-specific bone lengths from the most stable part of
         the sequence so the IK stage has ground-truth limb proportions.

    Bone length enforcement is intentionally NOT done here. IK owns that
    responsibility because only IK knows which joints are being corrected and
    needs to blend smoothly around flawed windows.
    """
    if keypoints_3d.ndim != 3 or keypoints_3d.shape[1:] != (17, 3):
        raise ValueError(
            f"Expected (T, 17, 3) input, got {keypoints_3d.shape}"
        )

    T = keypoints_3d.shape[0]
    log.info("normalize_skeleton_start", frames=T)

    # Step 1: root centering
    # Root = midpoint of L_HIP and R_HIP per frame
    root_trajectory = (keypoints_3d[:, L_HIP, :] + keypoints_3d[:, R_HIP, :]) / 2.0  # (T, 3)
    centered = keypoints_3d - root_trajectory[:, np.newaxis, :]  # (T, 17, 3)

    log.info(
        "normalize_skeleton_root_centered",
        root_mean_abs_mm=float(np.abs(root_trajectory).mean()),
    )

    # Step 2: bone length measurement (on centered coords - root offset doesn't
    # affect distances, but centering ensures the stable-window search uses the
    # same coordinate space as subsequent pipeline stages)
    bone_lengths = _measure_bone_lengths(centered)

    log.info(
        "normalize_skeleton_bone_lengths_measured",
        spine_mm=round(bone_lengths.get("spine", 0.0), 1),
        left_upper_arm_mm=round(bone_lengths.get("left_upper_arm", 0.0), 1),
        right_upper_arm_mm=round(bone_lengths.get("right_upper_arm", 0.0), 1),
    )

    return NormalizedSkeleton(
        keypoints_3d=centered.astype(np.float32),
        bone_lengths=bone_lengths,
        root_trajectory=root_trajectory.astype(np.float32),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Normalize a 3D skeleton sequence: root-center and measure bone lengths"
    )
    parser.add_argument(
        "--keypoints",
        required=True,
        help="Input .npy file of shape (T, 17, 3) in mm (root-relative from lifter)",
    )
    parser.add_argument(
        "--output-keypoints",
        required=True,
        help="Output .npy file of shape (T, 17, 3) - root-centered keypoints",
    )
    parser.add_argument(
        "--output-bone-lengths",
        required=True,
        help="Output JSON file mapping bone name to length in mm",
    )
    args = parser.parse_args()

    kps = np.load(args.keypoints)
    result = normalize_skeleton(kps)

    np.save(args.output_keypoints, result.keypoints_3d)
    with open(args.output_bone_lengths, "w") as f:
        json.dump(result.bone_lengths, f, indent=2)

    print(
        f"Saved normalized keypoints shape {result.keypoints_3d.shape} "
        f"to {args.output_keypoints}"
    )
    print(f"Saved bone lengths ({len(result.bone_lengths)} bones) to {args.output_bone_lengths}")
