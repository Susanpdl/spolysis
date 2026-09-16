from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import structlog

if TYPE_CHECKING:
    from pipeline.stages.phases import StrokePhases

log = structlog.get_logger(__name__)

# COCO-17 joint indices
_L_SHOULDER = 5
_R_SHOULDER = 6
_L_ELBOW = 7
_R_ELBOW = 8
_L_WRIST = 9
_R_WRIST = 10
_L_HIP = 11
_R_HIP = 12
_L_KNEE = 13
_R_KNEE = 14
_L_ANKLE = 15
_R_ANKLE = 16

# Fault threshold in degrees (or mm for wrist_height)
_FAULT_THRESHOLDS: dict[str, float] = {
    "hip_rotation": 15.0,
    "shoulder_rotation": 15.0,
    "right_elbow": 20.0,
    "left_elbow": 20.0,
    "right_knee": 20.0,
    "right_shoulder_abduction": 15.0,
    "right_wrist_height": 50.0,
}

# Window size to search around worst-fault frame for fault_frames range
_FAULT_FRAME_WINDOW = 10


@dataclass
class JointDelta:
    joint: str       # e.g. "right_elbow", "hip_rotation"
    phase: str       # "preparation" | "backswing" | "contact" | "follow_through"
    user_deg: float
    ref_deg: float
    delta_deg: float  # user_deg - ref_deg; positive = user > ref


@dataclass
class DeltaTable:
    deltas: list[JointDelta] = field(default_factory=list)
    fault_joints: list[str] = field(default_factory=list)
    fault_frames: tuple[int, int] = (0, 0)
    stroke_type: str = ""
    summary: dict[str, float] = field(default_factory=dict)  # contact-phase deltas


def angle_3d(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle in degrees at vertex b formed by rays b->a and b->c."""
    ba = a - b
    bc = c - b
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba < 1e-9 or norm_bc < 1e-9:
        return 0.0
    cos_val = np.dot(ba, bc) / (norm_ba * norm_bc)
    return float(np.degrees(np.arccos(np.clip(cos_val, -1.0, 1.0))))


def _rotation_angle_xz(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Signed angle in degrees between two vectors projected onto the xz (horizontal) plane.

    The xz plane is used because y is vertical in a root-centred skeleton -
    hip/shoulder rotation is a rotation about the vertical axis and is invisible
    in the y component.
    """
    a2 = vec_a[[0, 2]]  # drop y
    b2 = vec_b[[0, 2]]
    norm_a = np.linalg.norm(a2)
    norm_b = np.linalg.norm(b2)
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    cos_val = np.dot(a2, b2) / (norm_a * norm_b)
    return float(np.degrees(np.arccos(np.clip(cos_val, -1.0, 1.0))))


def _compute_angles(kps: np.ndarray, stroke_type: str) -> dict[str, float]:
    """
    Compute all diagnostic angles for a single frame.

    Args:
        kps:         (17, 3) 3D keypoints in mm
        stroke_type: used to gate serve-specific measurements

    Returns:
        dict mapping angle name to value in degrees (or mm for wrist_height)
    """
    angles: dict[str, float] = {}

    # Standard elbow flexion angles (applicable to all strokes)
    angles["right_elbow"] = angle_3d(
        kps[_R_SHOULDER], kps[_R_ELBOW], kps[_R_WRIST]
    )
    angles["left_elbow"] = angle_3d(
        kps[_L_SHOULDER], kps[_L_ELBOW], kps[_L_WRIST]
    )

    # Hip rotation: angle between hip vector and shoulder vector in xz plane.
    # Non-zero means the hips and shoulders are not aligned - this captures
    # the separation of hip-turn from shoulder-turn during the stroke.
    hip_vec = kps[_R_HIP] - kps[_L_HIP]
    shoulder_vec = kps[_R_SHOULDER] - kps[_L_SHOULDER]
    angles["hip_rotation"] = _rotation_angle_xz(hip_vec, shoulder_vec)

    # Shoulder rotation: torso-forward is approximated as the cross product of
    # the hip vector with the vertical (0,1,0), giving the direction the player
    # faces. Angle between that forward direction and the shoulder vector
    # captures whether the shoulders are open or closed at contact.
    up = np.array([0.0, 1.0, 0.0])
    torso_forward = np.cross(hip_vec, up)
    angles["shoulder_rotation"] = _rotation_angle_xz(torso_forward, shoulder_vec)

    # Knee flexion
    angles["right_knee"] = angle_3d(
        kps[_R_HIP], kps[_R_KNEE], kps[_R_ANKLE]
    )

    if stroke_type == "serve":
        # Shoulder abduction: arm raised from body (important for trophy position)
        angles["right_shoulder_abduction"] = angle_3d(
            kps[_R_HIP], kps[_R_SHOULDER], kps[_R_ELBOW]
        )
        # Wrist height relative to shoulder; positive = wrist above shoulder
        angles["right_wrist_height"] = float(
            kps[_R_WRIST, 1] - kps[_R_SHOULDER, 1]
        )

    return angles


def _phase_frames(phases: "StrokePhases", phase_name: str) -> list[int]:
    """Return the list of frame indices for the named phase."""
    if phase_name == "preparation":
        s, e = phases.preparation
        return list(range(s, e + 1))
    if phase_name == "backswing":
        s, e = phases.backswing
        return list(range(s, e + 1))
    if phase_name == "contact":
        return [phases.contact]
    if phase_name == "follow_through":
        s, e = phases.follow_through
        return list(range(s, e + 1))
    raise ValueError(f"Unknown phase '{phase_name}'")


def _avg_angles(
    keypoints_3d: np.ndarray,
    frames: list[int],
    stroke_type: str,
) -> dict[str, float]:
    """Average per-frame angles over the given frame indices."""
    if not frames:
        return {}

    T = keypoints_3d.shape[0]
    valid = [f for f in frames if 0 <= f < T]
    if not valid:
        return {}

    accum: dict[str, float] = {}
    for f in valid:
        a = _compute_angles(keypoints_3d[f], stroke_type)
        for k, v in a.items():
            accum[k] = accum.get(k, 0.0) + v

    n = len(valid)
    return {k: v / n for k, v in accum.items()}


def _find_worst_fault_frames(
    user_3d: np.ndarray,
    ref_aligned: np.ndarray,
    worst_joint: str,
    stroke_type: str,
    total_frames: int,
) -> tuple[int, int]:
    """
    Find the 10-frame window where the worst fault joint has maximum delta.

    Searches the full sequence frame by frame for the joint with the largest
    per-frame |delta|, then returns a symmetric window around that frame.
    """
    T = user_3d.shape[0]
    max_delta = -1.0
    worst_frame = 0

    for f in range(T):
        u_angles = _compute_angles(user_3d[f], stroke_type)
        r_angles = _compute_angles(ref_aligned[f], stroke_type)
        if worst_joint in u_angles and worst_joint in r_angles:
            delta = abs(u_angles[worst_joint] - r_angles[worst_joint])
            if delta > max_delta:
                max_delta = delta
                worst_frame = f

    half = _FAULT_FRAME_WINDOW // 2
    start = max(0, worst_frame - half)
    end = min(total_frames - 1, worst_frame + half)
    return (start, end)


def compute_deltas(
    user_3d: np.ndarray,
    ref_aligned: np.ndarray,
    phases: "StrokePhases",
    stroke_type: str,
) -> DeltaTable:
    """
    Compute per-phase, per-joint biomechanical deltas between user and reference.

    Args:
        user_3d:      (T, 17, 3) mm root-relative user sequence
        ref_aligned:  (T, 17, 3) mm root-relative reference, already warped to
                      user timing by align.py (must be the same length as user_3d)
        phases:       stroke phase windows for user_3d
        stroke_type:  "forehand" | "backhand" | "serve" | "volley"

    Returns:
        DeltaTable with one JointDelta per (joint, phase) combination.
    """
    if user_3d.shape != ref_aligned.shape:
        raise ValueError(
            f"user_3d shape {user_3d.shape} does not match ref_aligned shape {ref_aligned.shape}"
        )
    if user_3d.ndim != 3 or user_3d.shape[1:] != (17, 3):
        raise ValueError(f"Expected (T, 17, 3) input, got {user_3d.shape}")

    T = user_3d.shape[0]
    log.info(
        "compute_deltas_start",
        stroke_type=stroke_type,
        frames=T,
    )

    phase_names = ["preparation", "backswing", "contact", "follow_through"]
    deltas: list[JointDelta] = []
    summary: dict[str, float] = {}

    for phase_name in phase_names:
        frames = _phase_frames(phases, phase_name)
        user_avg = _avg_angles(user_3d, frames, stroke_type)
        ref_avg = _avg_angles(ref_aligned, frames, stroke_type)

        for joint in user_avg:
            if joint not in ref_avg:
                continue
            u_val = user_avg[joint]
            r_val = ref_avg[joint]
            delta = u_val - r_val
            deltas.append(JointDelta(
                joint=joint,
                phase=phase_name,
                user_deg=round(u_val, 2),
                ref_deg=round(r_val, 2),
                delta_deg=round(delta, 2),
            ))

            if phase_name == "contact":
                summary[joint] = round(delta, 2)

    # Identify fault joints using per-threshold logic
    # Use contact-phase deltas as the primary signal; fall back to max across phases
    fault_joints: list[str] = []
    max_abs_delta_per_joint: dict[str, float] = {}

    for d in deltas:
        cur = max_abs_delta_per_joint.get(d.joint, 0.0)
        max_abs_delta_per_joint[d.joint] = max(cur, abs(d.delta_deg))

    for joint, threshold in _FAULT_THRESHOLDS.items():
        if joint in max_abs_delta_per_joint:
            if max_abs_delta_per_joint[joint] >= threshold:
                fault_joints.append(joint)

    # Fault frames: find worst fault joint and locate its maximum delta window
    fault_frames = (0, min(T - 1, _FAULT_FRAME_WINDOW))
    if fault_joints:
        # Sort by absolute max delta to pick the most severe fault as anchor
        worst_joint = max(
            fault_joints,
            key=lambda j: max_abs_delta_per_joint.get(j, 0.0),
        )
        fault_frames = _find_worst_fault_frames(
            user_3d, ref_aligned, worst_joint, stroke_type, T
        )
        log.info(
            "fault_frames_located",
            worst_joint=worst_joint,
            fault_frames=fault_frames,
        )

    log.info(
        "compute_deltas_done",
        num_deltas=len(deltas),
        fault_joints=fault_joints,
        fault_frames=fault_frames,
        contact_summary=summary,
    )

    return DeltaTable(
        deltas=deltas,
        fault_joints=fault_joints,
        fault_frames=fault_frames,
        stroke_type=stroke_type,
        summary=summary,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute per-phase biomechanical deltas between user and reference 3D sequences"
    )
    parser.add_argument(
        "--user-keypoints",
        required=True,
        help="Path to .npy file of shape (T, 17, 3) - user 3D keypoints (mm, root-relative)",
    )
    parser.add_argument(
        "--ref-keypoints",
        required=True,
        help="Path to .npy file of shape (T, 17, 3) - warped reference (same length as user)",
    )
    parser.add_argument(
        "--stroke",
        required=True,
        choices=["forehand", "backhand", "serve", "volley"],
        help="Stroke type",
    )
    parser.add_argument(
        "--contact-frame",
        required=True,
        type=int,
        help="Contact frame index",
    )
    parser.add_argument(
        "--follow-through-start",
        required=True,
        type=int,
        help="First frame index of the follow-through phase",
    )
    args = parser.parse_args()

    user_kps = np.load(args.user_keypoints)
    ref_kps = np.load(args.ref_keypoints)

    T = user_kps.shape[0]
    contact = args.contact_frame

    # Reconstruct phases from CLI args so the CLI is self-contained
    from pipeline.stages.phases import StrokePhases

    follow_start = args.follow_through_start
    phases = StrokePhases(
        preparation=(0, max(0, contact - 1)),
        backswing=(0, max(0, contact - 1)),
        contact=contact,
        follow_through=(follow_start, T - 1),
        total_frames=T,
    )

    result = compute_deltas(
        user_3d=user_kps,
        ref_aligned=ref_kps,
        phases=phases,
        stroke_type=args.stroke,
    )

    # Formatted table output
    col_w = [22, 16, 10, 10, 10]
    header = (
        f"{'Joint':<{col_w[0]}}"
        f"{'Phase':<{col_w[1]}}"
        f"{'User':>{col_w[2]}}"
        f"{'Ref':>{col_w[3]}}"
        f"{'Delta':>{col_w[4]}}"
    )
    sep = "-" * sum(col_w)
    print(sep)
    print(header)
    print(sep)

    for d in result.deltas:
        fault_marker = " *" if d.joint in result.fault_joints else "  "
        print(
            f"{d.joint:<{col_w[0]}}"
            f"{d.phase:<{col_w[1]}}"
            f"{d.user_deg:>{col_w[2]}.1f}"
            f"{d.ref_deg:>{col_w[3]}.1f}"
            f"{d.delta_deg:>{col_w[4]}.1f}"
            f"{fault_marker}"
        )

    print(sep)
    print(f"Fault joints: {result.fault_joints or 'none'}")
    print(f"Fault frames: {result.fault_frames[0]}-{result.fault_frames[1]}")
    print("\nContact-phase summary:")
    for joint, delta in sorted(result.summary.items()):
        print(f"  {joint:<30} delta = {delta:+.1f}")
