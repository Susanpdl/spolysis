from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field

import numpy as np
import structlog

from pipeline.stages.delta import DeltaTable, JointDelta
from pipeline.stages.normalize3d import NormalizedSkeleton
from pipeline.utils.skeleton import (
    L_SHOULDER, R_SHOULDER,
    L_ELBOW, R_ELBOW,
    L_WRIST, R_WRIST,
    L_HIP, R_HIP,
    L_KNEE, R_KNEE,
    L_ANKLE, R_ANKLE,
)

log = structlog.get_logger(__name__)

# (chain indices, corrected joint position within chain, bone names for length lookup)
_CHAIN_DEFS: dict[str, tuple[list[int], str | None, list[str]]] = {
    "right_elbow": (
        [R_SHOULDER, R_ELBOW, R_WRIST],
        "elbow",
        ["right_upper_arm", "right_forearm"],
    ),
    "left_elbow": (
        [L_SHOULDER, L_ELBOW, L_WRIST],
        "elbow",
        ["left_upper_arm", "left_forearm"],
    ),
    "right_knee": (
        [R_HIP, R_KNEE, R_ANKLE],
        "knee",
        ["right_thigh", "right_shin"],
    ),
    "right_shoulder_abduction": (
        [R_HIP, R_SHOULDER, R_ELBOW],
        "shoulder",
        ["right_thigh", "right_upper_arm"],
    ),
}

# These faults require rotating a joint pair in the horizontal plane
# rather than a full IK chain solve.
_ROTATION_FAULTS = {"hip_rotation", "shoulder_rotation"}

# Hard clamp ranges in degrees for each joint type (prevents anatomically
# impossible poses that look broken in the overlay).
_JOINT_LIMITS: dict[str, tuple[float, float]] = {
    "elbow": (10.0, 170.0),
    "knee": (10.0, 170.0),
    "shoulder": (0.0, 180.0),
}


@dataclass
class CorrectedSequence:
    keypoints_3d: np.ndarray   # (T, 17, 3) corrected sequence, mm root-relative
    blend_weights: np.ndarray  # (T,) ease-in/out blend weight [0, 1] per frame
    corrected_joints: list[str] = field(default_factory=list)


def _angle_at_mid(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle in degrees at vertex b formed by rays b->a and b->c."""
    ba = a - b
    bc = c - b
    n_ba = np.linalg.norm(ba)
    n_bc = np.linalg.norm(bc)
    if n_ba < 1e-9 or n_bc < 1e-9:
        return 0.0
    cos_val = np.dot(ba, bc) / (n_ba * n_bc)
    return float(np.degrees(np.arccos(np.clip(cos_val, -1.0, 1.0))))


def _enforce_bone_length(origin: np.ndarray, target: np.ndarray, length: float) -> np.ndarray:
    """Project target onto sphere of given radius centred at origin."""
    delta = target - origin
    dist = np.linalg.norm(delta)
    if dist < 1e-9:
        # Degenerate: offset slightly along +x so the limb has a direction
        delta = np.array([1.0, 0.0, 0.0])
        dist = 1.0
    return origin + (delta / dist) * length


def _ccd_set_angle(
    kps_frame: np.ndarray,
    chain_indices: list[int],
    target_angle_deg: float,
    bone_lengths: dict[str, float],
    bone_names: list[str],
    joint_type: str,
    n_iter: int = 10,
) -> np.ndarray:
    """
    Adjust the middle joint of a 3-joint chain so the angle at that joint
    equals target_angle_deg.

    Binary search rotates the end-effector around the middle joint in the
    plane defined by the three points, then re-projects to preserve bone
    lengths.  A plane-based binary search is cheaper than full CCD iteration
    and suffices because we're correcting a single joint angle, not a
    multi-link reach problem.

    Args:
        kps_frame:       (17, 3) keypoints for one frame (will NOT be modified in-place)
        chain_indices:   [root_idx, mid_idx, end_idx]
        target_angle_deg: desired angle at mid joint
        bone_lengths:    bone name -> mm from NormalizedSkeleton
        bone_names:      [root_to_mid_bone, mid_to_end_bone]
        joint_type:      key into _JOINT_LIMITS for clamping
        n_iter:          binary search iterations

    Returns:
        (17, 3) copy of kps_frame with mid and end joints adjusted.
    """
    kps = kps_frame.copy()

    root_idx, mid_idx, end_idx = chain_indices
    lo, hi = _JOINT_LIMITS[joint_type]
    target_angle_deg = float(np.clip(target_angle_deg, lo, hi))

    root_pt = kps[root_idx]
    mid_pt = kps[mid_idx]
    end_pt = kps[end_idx]

    len_rm = bone_lengths.get(bone_names[0], float(np.linalg.norm(mid_pt - root_pt)))
    len_me = bone_lengths.get(bone_names[1], float(np.linalg.norm(end_pt - mid_pt)))

    # Re-anchor mid to preserve root-to-mid bone length first.
    mid_pt = _enforce_bone_length(root_pt, mid_pt, len_rm)
    kps[mid_idx] = mid_pt

    # Compute rotation axis perpendicular to the current arm plane.
    # If the three joints are collinear, pick an arbitrary perpendicular.
    ba = root_pt - mid_pt
    bc = end_pt - mid_pt
    axis = np.cross(ba, bc)
    axis_norm = np.linalg.norm(axis)
    if axis_norm < 1e-9:
        # Pick any perpendicular to ba
        arbitrary = np.array([0.0, 1.0, 0.0])
        if abs(np.dot(ba / (np.linalg.norm(ba) + 1e-9), arbitrary)) > 0.9:
            arbitrary = np.array([1.0, 0.0, 0.0])
        axis = np.cross(ba, arbitrary)
        axis_norm = np.linalg.norm(axis)
        if axis_norm < 1e-9:
            return kps
    axis = axis / axis_norm

    current_angle = _angle_at_mid(root_pt, mid_pt, end_pt)

    # Binary search on rotation angle delta needed to reach target_angle_deg.
    # We search over the signed rotation range [-180, 180] degrees.
    low_rot = -180.0
    high_rot = 180.0

    def _rotated_angle(delta_rad: float) -> float:
        c, s = np.cos(delta_rad), np.sin(delta_rad)
        # Rodrigues' rotation of end-effector direction around axis
        vec = end_pt - mid_pt
        rotated = (
            vec * c
            + np.cross(axis, vec) * s
            + axis * np.dot(axis, vec) * (1 - c)
        )
        new_end = mid_pt + rotated
        return _angle_at_mid(root_pt, mid_pt, new_end)

    # Determine search direction: does increasing rotation increase or decrease angle?
    test_angle = _rotated_angle(np.radians(5.0))
    if abs(test_angle - current_angle) < 1e-6:
        # No movement possible; return as-is
        return kps
    angle_increases_with_positive_rotation = test_angle > current_angle

    for _ in range(n_iter):
        mid_rot = (low_rot + high_rot) / 2.0
        achieved = _rotated_angle(np.radians(mid_rot))
        if angle_increases_with_positive_rotation:
            if achieved < target_angle_deg:
                low_rot = mid_rot
            else:
                high_rot = mid_rot
        else:
            if achieved > target_angle_deg:
                low_rot = mid_rot
            else:
                high_rot = mid_rot

    best_rot = (low_rot + high_rot) / 2.0
    best_rad = np.radians(best_rot)
    c, s = np.cos(best_rad), np.sin(best_rad)
    vec = end_pt - mid_pt
    rotated_vec = (
        vec * c
        + np.cross(axis, vec) * s
        + axis * np.dot(axis, vec) * (1 - c)
    )
    new_end = mid_pt + rotated_vec
    kps[end_idx] = _enforce_bone_length(mid_pt, new_end, len_me)

    return kps


def _apply_rotation_fault(
    kps_frame: np.ndarray,
    fault_name: str,
    delta_deg: float,
) -> np.ndarray:
    """
    Correct hip or shoulder rotation by rotating the joint pair by half the
    delta around the vertical (Y) axis at the pair midpoint.

    Half the delta is used because both joints in the pair are moved
    symmetrically, so the net rotation matches the full correction target.
    """
    kps = kps_frame.copy()

    if fault_name == "hip_rotation":
        left_idx, right_idx = L_HIP, R_HIP
    else:
        left_idx, right_idx = L_SHOULDER, R_SHOULDER

    left_pt = kps[left_idx]
    right_pt = kps[right_idx]
    midpoint = (left_pt + right_pt) / 2.0

    # Rotate both joints by half the correction delta around midpoint's vertical axis.
    # Negative sign: delta_deg = user - ref, so we subtract to bring user toward ref.
    rot_rad = np.radians(-delta_deg * 0.5)
    cos_r, sin_r = np.cos(rot_rad), np.sin(rot_rad)

    def _rotate_xz(pt: np.ndarray) -> np.ndarray:
        """Rotate a point around mid in the XZ plane (horizontal rotation)."""
        offset = pt - midpoint
        new_x = cos_r * offset[0] - sin_r * offset[2]
        new_z = sin_r * offset[0] + cos_r * offset[2]
        return midpoint + np.array([new_x, offset[1], new_z])

    kps[left_idx] = _rotate_xz(left_pt)
    kps[right_idx] = _rotate_xz(right_pt)
    return kps


def _build_blend_weights(
    T: int,
    fault_start: int,
    fault_end: int,
    ease_frames: int,
) -> np.ndarray:
    """
    Build cosine ease-in/out blend weights for the fault window.

    Weight is 0 outside the ease zone, ramps from 0 to 1 in the ease-in
    zone, holds at 1 through the fault window, and ramps back to 0 in the
    ease-out zone.  Cosine easing produces a smooth S-curve that eliminates
    visible pop at the blend boundaries.
    """
    weights = np.zeros(T, dtype=np.float32)

    blend_start = max(0, fault_start - ease_frames)
    blend_end = min(T - 1, fault_end + ease_frames)

    for t in range(blend_start, fault_start):
        t_in_zone = t - blend_start
        weights[t] = 0.5 * (1.0 - np.cos(np.pi * t_in_zone / ease_frames))

    for t in range(fault_start, fault_end + 1):
        weights[t] = 1.0

    for t in range(fault_end + 1, blend_end + 1):
        t_in_zone = t - fault_end
        weights[t] = 0.5 * (1.0 + np.cos(np.pi * t_in_zone / ease_frames))

    return weights


def _contact_phase_delta(delta_table: DeltaTable, fault_joint: str) -> float | None:
    """Return the contact-phase delta_deg for a given fault joint, or None."""
    for d in delta_table.deltas:
        if d.joint == fault_joint and d.phase == "contact":
            return d.delta_deg
    # Fall back to any phase if contact is missing
    for d in delta_table.deltas:
        if d.joint == fault_joint:
            return d.delta_deg
    return None


def _ref_angle_at_contact(delta_table: DeltaTable, fault_joint: str) -> float | None:
    """Return the contact-phase ref_deg for a given fault joint, or None."""
    for d in delta_table.deltas:
        if d.joint == fault_joint and d.phase == "contact":
            return d.ref_deg
    for d in delta_table.deltas:
        if d.joint == fault_joint:
            return d.ref_deg
    return None


def apply_ik_correction(
    user_skeleton: NormalizedSkeleton,
    delta_table: DeltaTable,
    phases: object,  # StrokePhases - imported lazily to avoid circular deps
    ease_frames: int = 8,
) -> CorrectedSequence:
    """
    Apply CCD IK correction to the user's 3D skeleton sequence for all
    joints identified as faulty in delta_table.

    Only frames within the fault window (plus ease-in/out margins) are
    modified.  Outside that window the original keypoints are returned
    unchanged so the correction blends naturally into unmodified motion.

    Args:
        user_skeleton: normalized user skeleton from normalize3d.py
        delta_table:   fault analysis from delta.py
        phases:        StrokePhases for the stroke
        ease_frames:   cosine blend frames on each side of the fault window

    Returns:
        CorrectedSequence with the blended corrected keypoints.
    """
    kps = user_skeleton.keypoints_3d         # (T, 17, 3)
    bone_lengths = user_skeleton.bone_lengths
    T = kps.shape[0]

    fault_start, fault_end = delta_table.fault_frames
    fault_joints = delta_table.fault_joints

    log.info(
        "ik_correction_start",
        stroke_type=delta_table.stroke_type,
        fault_joints=fault_joints,
        fault_frames=(fault_start, fault_end),
        ease_frames=ease_frames,
        total_frames=T,
    )

    blend_weights = _build_blend_weights(T, fault_start, fault_end, ease_frames)

    blend_start = max(0, fault_start - ease_frames)
    blend_end = min(T - 1, fault_end + ease_frames)

    # Build correction targets once (not per-frame) to keep all frames in the
    # fault window aimed at the same biomechanical target.
    chain_corrections: list[tuple[list[int], float, str, list[str], str]] = []
    rotation_corrections: list[tuple[str, float]] = []

    for fault_joint in fault_joints:
        if fault_joint in _ROTATION_FAULTS:
            delta_deg = _contact_phase_delta(delta_table, fault_joint)
            if delta_deg is not None:
                rotation_corrections.append((fault_joint, delta_deg))
            else:
                log.warning("ik_no_delta_found", fault_joint=fault_joint)
            continue

        if fault_joint not in _CHAIN_DEFS:
            log.warning("ik_unknown_fault_joint_skipped", fault_joint=fault_joint)
            continue

        chain_indices, joint_type, bone_names = _CHAIN_DEFS[fault_joint]
        target_angle = _ref_angle_at_contact(delta_table, fault_joint)
        if target_angle is None:
            log.warning("ik_no_ref_angle_found", fault_joint=fault_joint)
            continue

        # Clamp target to joint limits before passing to CCD
        lo, hi = _JOINT_LIMITS[joint_type]
        target_angle = float(np.clip(target_angle, lo, hi))

        chain_corrections.append(
            (chain_indices, target_angle, joint_type, bone_names, fault_joint)
        )

    corrected = kps.copy()

    for t in range(blend_start, blend_end + 1):
        w = float(blend_weights[t])
        if w < 1e-6:
            continue

        frame_kps = kps[t].copy()

        # Apply all chain (IK) corrections for this frame
        for chain_indices, target_angle, joint_type, bone_names, fault_joint in chain_corrections:
            frame_kps = _ccd_set_angle(
                frame_kps,
                chain_indices,
                target_angle,
                bone_lengths,
                bone_names,
                joint_type,
            )

        # Apply rotation corrections
        for fault_joint, delta_deg in rotation_corrections:
            frame_kps = _apply_rotation_fault(frame_kps, fault_joint, delta_deg)

        # Blend: w=1 in fault zone means fully corrected; w<1 in ease zone
        # means a proportional mix of original and corrected.
        corrected[t] = (1.0 - w) * kps[t] + w * frame_kps

    applied_joints = [j for j, _ in rotation_corrections] + [
        j for _, _, _, _, j in chain_corrections
    ]

    log.info(
        "ik_correction_done",
        corrected_joints=applied_joints,
        blend_start=blend_start,
        blend_end=blend_end,
    )

    return CorrectedSequence(
        keypoints_3d=corrected.astype(np.float32),
        blend_weights=blend_weights,
        corrected_joints=applied_joints,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Apply CCD IK correction to a user 3D skeleton sequence"
    )
    parser.add_argument(
        "--user-keypoints",
        required=True,
        help="Path to .npy file of shape (T, 17, 3) - normalized user keypoints (mm, root-relative)",
    )
    parser.add_argument(
        "--bone-lengths",
        required=True,
        help="Path to JSON file mapping bone name to length in mm (from normalize3d.py)",
    )
    parser.add_argument(
        "--delta-table",
        required=True,
        help="Path to JSON file produced by delta.py CLI",
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
        help="Contact frame index in the user sequence",
    )
    parser.add_argument(
        "--ease-frames",
        type=int,
        default=8,
        help="Blend frames on each side of the fault window (default: 8)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output .npy path for corrected (T, 17, 3) keypoints",
    )
    parser.add_argument(
        "--output-blend-weights",
        default=None,
        help="Optional: save blend weights (T,) to this .npy path",
    )
    args = parser.parse_args()

    raw_kps = np.load(args.user_keypoints)
    T = raw_kps.shape[0]

    with open(args.bone_lengths) as f:
        bone_lengths_dict: dict[str, float] = json.load(f)

    with open(args.delta_table) as f:
        dt_raw = json.load(f)

    from pipeline.stages.phases import StrokePhases

    delta_list = [JointDelta(**d) for d in dt_raw.get("deltas", [])]
    fault_frames_raw = dt_raw.get("fault_frames", [0, min(T - 1, 10)])
    delta_table = DeltaTable(
        deltas=delta_list,
        fault_joints=dt_raw.get("fault_joints", []),
        fault_frames=(int(fault_frames_raw[0]), int(fault_frames_raw[1])),
        stroke_type=dt_raw.get("stroke_type", args.stroke),
        summary=dt_raw.get("summary", {}),
    )

    contact = args.contact_frame
    phases = StrokePhases(
        preparation=(0, max(0, contact - 1)),
        backswing=(0, max(0, contact - 1)),
        contact=contact,
        follow_through=(min(T - 1, contact + 1), T - 1),
        total_frames=T,
    )

    root_traj = np.zeros((T, 3), dtype=np.float32)
    user_skel = NormalizedSkeleton(
        keypoints_3d=raw_kps.astype(np.float32),
        bone_lengths=bone_lengths_dict,
        root_trajectory=root_traj,
    )

    result = apply_ik_correction(
        user_skeleton=user_skel,
        delta_table=delta_table,
        phases=phases,
        ease_frames=args.ease_frames,
    )

    np.save(args.output, result.keypoints_3d)
    print(f"Saved corrected keypoints shape {result.keypoints_3d.shape} to {args.output}")
    print(f"Corrected joints: {result.corrected_joints}")

    if args.output_blend_weights:
        np.save(args.output_blend_weights, result.blend_weights)
        print(f"Saved blend weights to {args.output_blend_weights}")
