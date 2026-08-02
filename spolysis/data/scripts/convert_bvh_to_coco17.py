#!/usr/bin/env python3
"""
Convert Tennis-MoCap BVH files to COCO 17-joint NPY format.

Used to produce normalized reference motion sequences for Phase 2 DTW alignment.
Only converts files whose performance tier matches --tier (default 1,2 = high-performance).

Usage:
  python data/scripts/convert_bvh_to_coco17.py \\
    --input  data/tennis-mocap/data/ \\
    --labels data/tennis-mocap/labels.csv \\
    --output data/reference_motion/ \\
    --tier 1 2 \\
    --fps 30

Output:
  data/reference_motion/<filename>_<stroke>.npy  shape (T, 17, 3), normalized
  data/reference_motion/manifest.json             stroke_label -> list of npy paths
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

# COCO 17 body joint to BVH joint name
# Face joints 0-4 don't exist in BVH; we copy from Head (they're unused in biomechanics)
_BVH_TO_COCO: dict[str, int] = {
    "Head":          0,   # nose - approximate; eyes/ears (1-4) copy from this
    "LeftShoulder":  5,
    "RightShoulder": 6,
    "LeftElbow":     7,
    "RightElbow":    8,
    "LeftWrist":     9,
    "RightWrist":    10,
    "LeftHip":       11,
    "RightHip":      12,
    "LeftKnee":      13,
    "RightKnee":     14,
    "LeftAnkle":     15,
    "RightAnkle":    16,
}

# Tennis-MoCap stroke_type int -> our canonical stroke label
_STROKE_MAP: dict[int, str] = {
    0: "serve",
    1: "serve",     # smash - same overhead motion, treated as serve
    2: "forehand",
    3: "volley",    # forehand volley - compact swing, separate from full forehand
    4: "backhand",
    5: "volley",    # backhand volley - same compact motion category
}


@dataclass
class _Joint:
    name: str
    parent: Optional[str]
    offset: np.ndarray      # (3,) local offset from parent
    channels: list[str]     # BVH channel names in application order
    channel_start: int      # index into the flat per-frame channel array
    children: list[str] = field(default_factory=list)


def _parse_hierarchy(lines: list[str]) -> tuple[dict[str, _Joint], list[str], list[str]]:
    """
    Parse HIERARCHY section.
    Returns (joints, joint_order, remaining_lines_from_MOTION).
    """
    joints: dict[str, _Joint] = {}
    stack: list[str] = []
    joint_order: list[str] = []
    channel_idx = 0

    for i, raw in enumerate(lines):
        line = raw.strip()
        if line.startswith(("ROOT", "JOINT")):
            name = line.split()[1]
            parent = stack[-1] if stack else None
            joints[name] = _Joint(
                name=name,
                parent=parent,
                offset=np.zeros(3, dtype=np.float64),
                channels=[],
                channel_start=channel_idx,
            )
            if parent:
                joints[parent].children.append(name)
            joint_order.append(name)
        elif line.startswith("OFFSET"):
            _, x, y, z = line.split()
            joints[joint_order[-1]].offset = np.array([float(x), float(y), float(z)])
        elif line.startswith("CHANNELS"):
            parts = line.split()
            n = int(parts[1])
            ch = parts[2: 2 + n]
            joints[joint_order[-1]].channels = ch
            joints[joint_order[-1]].channel_start = channel_idx
            channel_idx += n
        elif line == "{":
            stack.append(joint_order[-1])
        elif line == "}":
            stack.pop()
        elif line.startswith("MOTION"):
            return joints, joint_order, lines[i:]

    raise ValueError("MOTION section not found in BVH file")


def _rot_matrix(angle_deg: float, axis: str) -> np.ndarray:
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    if axis == "X":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)
    if axis == "Y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)
    # Z
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)


def _local_transform(
    channels: list[str],
    values: np.ndarray,
    offset: np.ndarray,
) -> np.ndarray:
    """Build 4x4 homogeneous transform for one joint at one frame."""
    T = np.eye(4, dtype=np.float64)
    T[:3, 3] = offset

    pos = np.zeros(3, dtype=np.float64)
    R = np.eye(3, dtype=np.float64)

    for ch, val in zip(channels, values):
        if ch == "Xposition":
            pos[0] = val
        elif ch == "Yposition":
            pos[1] = val
        elif ch == "Zposition":
            pos[2] = val
        elif ch in ("Xrotation", "Yrotation", "Zrotation"):
            R = R @ _rot_matrix(val, ch[0])

    M = np.eye(4, dtype=np.float64)
    M[:3, :3] = R
    M[:3, 3] = pos
    return T @ M


def _forward_kinematics(
    joints: dict[str, _Joint],
    joint_order: list[str],
    frame_vals: np.ndarray,
) -> dict[str, np.ndarray]:
    """Return world (x,y,z) for each joint for one frame."""
    world: dict[str, np.ndarray] = {}
    for name in joint_order:
        j = joints[name]
        n = len(j.channels)
        vals = frame_vals[j.channel_start: j.channel_start + n]
        local = _local_transform(j.channels, vals, j.offset)
        if j.parent is None:
            world[name] = local
        else:
            world[name] = world[j.parent] @ local
    return {name: world[name][:3, 3] for name in joint_order}


def _parse_bvh(path: str) -> tuple[np.ndarray, float, list[str]]:
    """
    Parse BVH file.
    Returns (positions, frame_time, joint_order).
    positions: (T, N_joints, 3) in capture-space units.
    """
    with open(path) as f:
        lines = f.readlines()

    joints, joint_order, motion_lines = _parse_hierarchy(lines)

    n_frames = int(motion_lines[1].split()[-1])
    frame_time = float(motion_lines[2].split()[-1])

    positions = np.zeros((n_frames, len(joint_order), 3), dtype=np.float32)
    for fi, line in enumerate(motion_lines[3: 3 + n_frames]):
        vals = np.fromstring(line, sep=" ", dtype=np.float64)
        wp = _forward_kinematics(joints, joint_order, vals)
        for ji, name in enumerate(joint_order):
            positions[fi, ji] = wp[name]

    return positions, frame_time, joint_order


def _to_coco17(positions: np.ndarray, joint_order: list[str]) -> np.ndarray:
    """
    Map BVH world positions to COCO 17 joints.
    Returns (T, 17, 3).
    """
    T = positions.shape[0]
    name_to_idx = {name: i for i, name in enumerate(joint_order)}
    coco = np.zeros((T, 17, 3), dtype=np.float32)
    for bvh_name, coco_idx in _BVH_TO_COCO.items():
        if bvh_name in name_to_idx:
            coco[:, coco_idx] = positions[:, name_to_idx[bvh_name]]
    # Face joints 1-4 (eyes, ears): copy from nose position (joint 0 from Head)
    for i in range(1, 5):
        coco[:, i] = coco[:, 0]
    return coco


def _normalize(coco: np.ndarray) -> np.ndarray:
    """
    Root-center + scale-normalize.
    Root = midpoint of left_hip (11) and right_hip (12).
    Scale = mean hip-to-hip distance set to 1.0.
    """
    root = (coco[:, 11] + coco[:, 12]) / 2.0   # (T, 3)
    centered = coco - root[:, None, :]
    hip_width = float(np.linalg.norm(coco[:, 11] - coco[:, 12], axis=-1).mean())
    if hip_width > 1e-6:
        centered = centered / hip_width
    return centered


def _resample(seq: np.ndarray, src_fps: float, tgt_fps: float) -> np.ndarray:
    """Linear interpolation resample of (T, J, C) sequence."""
    T_src = seq.shape[0]
    T_tgt = max(1, round(T_src * tgt_fps / src_fps))
    src_t = np.linspace(0.0, 1.0, T_src)
    tgt_t = np.linspace(0.0, 1.0, T_tgt)
    out = np.empty((T_tgt,) + seq.shape[1:], dtype=seq.dtype)
    for j in range(seq.shape[1]):
        for c in range(seq.shape[2]):
            out[:, j, c] = np.interp(tgt_t, src_t, seq[:, j, c])
    return out


def convert_file(bvh_path: str, out_path: str, target_fps: float = 30.0) -> None:
    positions, frame_time, joint_order = _parse_bvh(bvh_path)
    src_fps = 1.0 / frame_time
    coco = _to_coco17(positions, joint_order)
    coco = _normalize(coco)
    if abs(src_fps - target_fps) > 0.5:
        coco = _resample(coco, src_fps, target_fps)
    np.save(out_path, coco)


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert Tennis-MoCap BVH -> COCO 17-joint NPY")
    ap.add_argument("--input", required=True, help="Directory containing .bvh files")
    ap.add_argument("--labels", required=True, help="Path to labels.csv")
    ap.add_argument("--output", required=True, help="Output directory for .npy files")
    ap.add_argument(
        "--tier",
        type=int,
        nargs="+",
        default=[1, 2],
        help="Performance tiers to include: 0=regular, 1=high-perf, 2=outstanding (default: 1 2)",
    )
    ap.add_argument("--fps", type=float, default=30.0, help="Target fps (default 30)")
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load labels
    file_meta: dict[str, dict] = {}
    with open(args.labels) as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)  # skip header
        for row in reader:
            if len(row) < 5:
                continue
            fname, _pb, perf_tier, _gender, stroke_type = row[:5]
            file_meta[fname.strip()] = {
                "perf_tier": int(perf_tier),
                "stroke_type": int(stroke_type),
            }

    manifest: dict[str, list[str]] = {}
    converted = skipped = 0

    for bvh_path in sorted(Path(args.input).glob("*.bvh")):
        meta = file_meta.get(bvh_path.name)
        if meta is None:
            print(f"  skip (no label): {bvh_path.name}")
            skipped += 1
            continue
        if meta["perf_tier"] not in args.tier:
            skipped += 1
            continue
        stroke_label = _STROKE_MAP.get(meta["stroke_type"])
        if stroke_label is None:
            skipped += 1
            continue

        out_name = f"{bvh_path.stem}_{stroke_label}.npy"
        out_path = str(out_dir / out_name)

        try:
            convert_file(str(bvh_path), out_path, target_fps=args.fps)
            manifest.setdefault(stroke_label, []).append(out_path)
            seq = np.load(out_path)
            print(f"  ok  {bvh_path.name:40s} -> {out_name}  shape={seq.shape}")
            converted += 1
        except Exception as exc:
            print(f"  ERR {bvh_path.name}: {exc}")
            skipped += 1

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"\n{converted} converted, {skipped} skipped")
    print(f"Manifest: {manifest_path}")
    for stroke, files in sorted(manifest.items()):
        print(f"  {stroke}: {len(files)} sequences")


if __name__ == "__main__":
    main()
