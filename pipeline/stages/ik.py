"""Joint-angle corrections with rigid subtree rotations and eased targets.

Rotating bone vectors preserves every original limb length, including during
transitions. Cartesian interpolation of two poses would shorten the bones.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from pipeline.stages.delta import DeltaTable, angle_3d
from pipeline.stages.normalize3d import NormalizedSkeleton


@dataclass
class CorrectedSequence:
    keypoints_3d: np.ndarray
    blend_weights: np.ndarray
    corrected_joints: list[str] = field(default_factory=list)


_CHAINS = {
    "right_elbow": (6, 8, 10, [10]),
    "left_elbow": (5, 7, 9, [9]),
    "right_knee": (12, 14, 16, [16]),
    "right_shoulder_abduction": (12, 6, 8, [8, 10]),
}


def _rotate(
    points: np.ndarray, pivot: np.ndarray, axis: np.ndarray, radians: float
) -> np.ndarray:
    axis = axis / max(float(np.linalg.norm(axis)), 1e-9)
    vectors = points - pivot
    c, s = np.cos(radians), np.sin(radians)
    return (
        pivot
        + vectors * c
        + np.cross(axis, vectors) * s
        + (vectors @ axis)[..., None] * axis * (1 - c)
    )


def _build_blend_weights(T: int, start: int, end: int, ease_frames: int) -> np.ndarray:
    if not 0 <= start <= end < T or ease_frames < 1:
        raise ValueError("Invalid correction interval")
    t = np.arange(T)
    distance = np.maximum(np.maximum(start - t, t - end), 0)
    return (0.5 * (1 + np.cos(np.pi * np.clip(distance / ease_frames, 0, 1)))).astype(
        np.float32
    )


def apply_ik_correction(
    user_skeleton: NormalizedSkeleton,
    delta_table: DeltaTable,
    phases: object,
    ease_frames: int = 8,
) -> CorrectedSequence:
    original = user_skeleton.keypoints_3d
    out = original.copy()
    primary = getattr(delta_table, "primary", None)
    supported = [
        j for j in delta_table.fault_joints if j in _CHAINS or j == "hip_rotation"
    ]
    if primary is not None and (
        primary.joint in _CHAINS or primary.joint == "hip_rotation"
    ):
        supported = [primary.joint] + [j for j in supported if j != primary.joint]
    if not supported:
        return CorrectedSequence(out, np.zeros(len(out), dtype=np.float32), [])
    weights = _build_blend_weights(len(out), *delta_table.fault_frames, ease_frames)
    # Primary joint uses the chosen (joint, phase) pair; secondaries keep their peak.
    targets = {}
    for joint in supported:
        if primary is not None and joint == primary.joint:
            targets[joint] = primary
            continue
        targets[joint] = max(
            (d for d in delta_table.deltas if d.joint == joint),
            key=lambda d: abs(d.delta_deg),
        )
    for t, weight in enumerate(weights):
        if weight == 0:
            continue
        for joint in supported:
            delta = targets[joint]
            if joint == "hip_rotation":
                indices = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
                pivot = (out[t, 5] + out[t, 6]) / 2
                # XZ signed angles rotate opposite to a right-handed Y rotation.
                out[t, indices] = _rotate(
                    out[t, indices],
                    pivot,
                    np.array([0.0, 1.0, 0.0]),
                    np.radians(delta.delta_deg * weight),
                )
                continue
            root, mid, end, children = _CHAINS[joint]
            a, b = out[t, root] - out[t, mid], out[t, end] - out[t, mid]
            axis = np.cross(a, b)
            if np.linalg.norm(axis) < 1e-8:
                axis = np.cross(a, np.array([0.0, 0.0, 1.0]))
            if np.linalg.norm(axis) < 1e-8:
                continue
            current = angle_3d(out[t, root], out[t, mid], out[t, end])
            target = np.clip(current - delta.delta_deg * weight, 10, 175)
            out[t, children] = _rotate(
                out[t, children], out[t, mid], axis, np.radians(target - current)
            )
    return CorrectedSequence(out.astype(np.float32), weights, supported)
