#!/usr/bin/env python3
"""
Build MMAction2 annotation pickle files from THETIS RTMPose-x keypoints.

Produces two pickle files:
  1. stroke_annotations.pkl  - 4-class stroke type labels for PoseC3D stroke model
  2. fault_annotations.pkl   - 8-class weak fault labels for PoseC3D fault model

Stroke labels come directly from the THETIS folder structure.

Fault labels are derived by computing mean joint angles for each clip and
comparing against expert-player reference angles. Clips whose joint angles
deviate significantly from expert norms are labelled with the most prominent fault.
This is a weak labelling strategy - not ground truth but sufficient to bootstrap
the fault classifier.

Input: data/thetis/keypoints/ (from preprocess_thetis.py)
       Structure: keypoints/{stroke_folder}/{p{N}_{...}}.npy
       Player number extracted from filename to determine expert status.

Output: data/thetis/stroke_annotations.pkl, data/thetis/fault_annotations.pkl

Usage:
  python data/scripts/build_thetis_annotations.py \\
    --keypoints data/thetis/keypoints/ \\
    --output    data/thetis/
"""
from __future__ import annotations

import argparse
import pickle
import re
from pathlib import Path

import numpy as np

# Actual THETIS folder names -> canonical 4-class label
# Mirrors THETIS_STROKE_MAP in preprocess_thetis.py exactly
STROKE_FOLDERS: dict[str, str] = {
    "backhand":             "backhand",
    "backhand2hands":       "backhand",   # actual folder name (not backhand_2hands)
    "backhand_slice":       "backhand",
    "backhand_volley":      "volley",
    "forehand_flat":        "forehand",
    "forehand_openstands":  "forehand",   # actual folder name (not forehand_open_stance)
    "forehand_slice":       "forehand",
    "forehand_volley":      "volley",
    "flat_service":         "serve",
    "kick_service":         "serve",
    "slice_service":        "serve",
    "smash":                "serve",
}

_PLAYER_RE = re.compile(r"^p(\d+)_")
STROKE_LABEL_IDX = {"forehand": 0, "backhand": 1, "serve": 2, "volley": 3}

# Fault labels and their indices
FAULT_LABEL_IDX = {
    "late_contact": 0,
    "open_stance": 1,
    "low_follow_through": 2,
    "arm_only": 3,
    "no_hip_rotation": 4,
    "grip_issue": 5,
    "no_trophy_position": 6,
    "low_toss": 7,
}

# Players p32-p55 are experts in THETIS
EXPERT_MIN_PLAYER = 32


# COCO joint indices used for angle computation
L_SHOULDER, R_SHOULDER = 5, 6
L_ELBOW, R_ELBOW = 7, 8
L_WRIST, R_WRIST = 9, 10
L_HIP, R_HIP = 11, 12
L_KNEE, R_KNEE = 13, 14



def _compute_stroke_features(kps: np.ndarray) -> dict[str, float]:
    """
    Compute aggregate biomechanical features over a clip.
    kps: (T, 17, 3) - x, y, confidence (pixel coords, not normalized here;
    we use relative angles which are scale-invariant).
    """
    T = kps.shape[0]
    xy = kps[:, :, :2]  # (T, 17, 2)
    conf = kps[:, :, 2]  # (T, 17)

    def pt(t: int, idx: int) -> np.ndarray:
        return xy[t, idx]

    def angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
        ba = a - b
        bc = c - b
        n = np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-9
        return float(np.degrees(np.arccos(np.clip(np.dot(ba, bc) / n, -1, 1))))

    # Wrist peak timing: when does right wrist reach max x-velocity?
    r_wrist_x = xy[:, R_WRIST, 0]
    if T > 3:
        vel = np.gradient(r_wrist_x)
        peak_frame = int(np.argmax(np.abs(vel)))
        wrist_peak_rel = peak_frame / T  # in [0, 1]
    else:
        wrist_peak_rel = 0.5

    # Contact-frame angles (approximate contact at 40% through clip)
    contact_t = max(0, min(T - 1, int(T * 0.4)))

    # Hip rotation: angle between shoulder vector and hip vector
    s_vec = pt(contact_t, R_SHOULDER) - pt(contact_t, L_SHOULDER)
    h_vec = pt(contact_t, R_HIP) - pt(contact_t, L_HIP)
    s_norm = np.linalg.norm(s_vec) + 1e-9
    h_norm = np.linalg.norm(h_vec) + 1e-9
    hip_rot = float(np.degrees(np.arccos(np.clip(np.dot(s_vec / s_norm, h_vec / h_norm), -1, 1))))

    # Follow-through: wrist y-position at end vs contact (image y increases downward)
    wrist_y_contact = float(xy[contact_t, R_WRIST, 1])
    wrist_y_end = float(xy[min(T - 1, int(T * 0.85)), R_WRIST, 1])
    follow_through_delta = wrist_y_end - wrist_y_contact  # positive = wrist went down

    # Open stance: hip width at contact (normalized by image width estimate)
    hip_width = abs(float(xy[contact_t, R_HIP, 0]) - float(xy[contact_t, L_HIP, 0]))
    frame_w_est = max(float(xy[:, :, 0].max() - xy[:, :, 0].min()), 1.0)
    open_stance_ratio = hip_width / frame_w_est

    # Serve: wrist y at peak (high = reaching up for trophy/toss)
    serve_t = max(0, min(T - 1, int(T * 0.35)))
    wrist_y_peak_serve = float(xy[serve_t, R_WRIST, 1])
    torso_y = float((xy[serve_t, L_SHOULDER, 1] + xy[serve_t, R_SHOULDER, 1]) / 2)
    trophy_height = torso_y - wrist_y_peak_serve  # positive = wrist above shoulders

    return {
        "hip_rotation": hip_rot,
        "wrist_peak_rel": wrist_peak_rel,
        "follow_through_delta": follow_through_delta,
        "open_stance_ratio": open_stance_ratio,
        "trophy_height": trophy_height,
    }


def _assign_fault(features: dict[str, float], stroke_label: str, expert_ref: dict) -> str | None:
    """
    Assign a fault label by comparing features against expert reference.
    Only assigns if the deviation exceeds a threshold (conservative to reduce noise).
    """
    ref = expert_ref.get(stroke_label, {})
    if not ref:
        return None

    # Hip rotation fault: significantly less hip rotation than experts
    hip_rot = features["hip_rotation"]
    ref_hip = ref.get("hip_rotation", 45.0)
    if hip_rot > ref_hip + 15:  # larger angle = less rotation (shoulders parallel to hips)
        return "arm_only" if stroke_label != "serve" else "arm_only"

    # Late contact: wrist peak in last 35% of stroke
    if features["wrist_peak_rel"] > 0.70:
        return "late_contact"

    # Low follow-through: wrist ends significantly lower than contact
    ref_ft = ref.get("follow_through_delta", 0.0)
    if features["follow_through_delta"] > ref_ft + 20:
        if stroke_label == "serve":
            return None  # follow-through metric doesn't apply cleanly to serve
        return "low_follow_through"

    # Open stance (forehand/volley only)
    if stroke_label in ("forehand", "volley"):
        ref_ost = ref.get("open_stance_ratio", 0.15)
        if features["open_stance_ratio"] > ref_ost + 0.10:
            return "open_stance"

    # Serve-specific: missing trophy position
    if stroke_label == "serve":
        ref_trophy = ref.get("trophy_height", 30.0)
        if features["trophy_height"] < ref_trophy - 20:
            return "no_trophy_position"

    return None


def _build_expert_reference(
    samples: list[dict],
) -> dict[str, dict[str, float]]:
    """
    Compute per-stroke mean feature values across expert clips as the reference baseline.
    """
    by_stroke: dict[str, list[dict]] = {}
    for s in samples:
        if s.get("is_expert"):
            sl = s["stroke_label"]
            by_stroke.setdefault(sl, []).append(s["features"])

    ref: dict[str, dict[str, float]] = {}
    for stroke, feats_list in by_stroke.items():
        if not feats_list:
            continue
        keys = feats_list[0].keys()
        ref[stroke] = {
            k: float(np.mean([f[k] for f in feats_list]))
            for k in keys
        }
    return ref


def _to_annotation(kps: np.ndarray, label_idx: int, filename: str) -> dict:
    """Convert (T, 17, 3) keypoints to MMAction2 skeleton annotation format."""
    T = kps.shape[0]
    kp_xy = kps[:, :, :2][np.newaxis]         # (1, T, 17, 2)
    kp_score = kps[:, :, 2][np.newaxis]        # (1, T, 17)
    return {
        "keypoint": kp_xy.astype(np.float32),
        "keypoint_score": kp_score.astype(np.float32),
        "total_frames": T,
        "label": label_idx,
        "filename": filename,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keypoints", required=True, help="data/thetis/keypoints/ directory")
    ap.add_argument("--output", required=True, help="Output directory for annotation .pkl files")
    args = ap.parse_args()

    kp_root = Path(args.keypoints)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Pass 1: load all clips, compute features ---
    # Keypoints are organized by stroke folder (mirrors THETIS VIDEO_RGB structure).
    # Player number is extracted from the filename: p{N}_{...}.npy
    all_samples: list[dict] = []
    missing = skipped = 0

    for stroke_dir in sorted(kp_root.iterdir()):
        if not stroke_dir.is_dir():
            continue
        stroke_folder = stroke_dir.name.lower()
        stroke_label = STROKE_FOLDERS.get(stroke_folder)
        if stroke_label is None:
            skipped += 1
            continue

        for npy_file in sorted(stroke_dir.glob("*.npy")):
            m = _PLAYER_RE.match(npy_file.name)
            if m is None:
                skipped += 1
                continue
            player_num = int(m.group(1))
            is_expert = player_num >= EXPERT_MIN_PLAYER

            try:
                kps = np.load(str(npy_file))  # (T, 17, 3)
                if kps.shape[0] < 5:
                    continue
                feats = _compute_stroke_features(kps)
                all_samples.append({
                    "path": str(npy_file),
                    "keypoints": kps,
                    "stroke_label": stroke_label,
                    "is_expert": is_expert,
                    "features": feats,
                    "player": f"p{player_num}",
                })
            except Exception:
                missing += 1

    print(f"Loaded {len(all_samples)} clips  (skipped {skipped} unknown strokes, {missing} load errors)")

    # --- Pass 2: compute expert reference ---
    expert_ref = _build_expert_reference(all_samples)
    print("Expert reference per stroke:")
    for stroke, ref in sorted(expert_ref.items()):
        print(f"  {stroke}: hip_rot={ref.get('hip_rotation', 0):.1f}  "
              f"trophy_h={ref.get('trophy_height', 0):.1f}  "
              f"ft_delta={ref.get('follow_through_delta', 0):.1f}")

    # --- Pass 3: build stroke and fault annotation lists ---
    stroke_annots: list[dict] = []
    fault_annots: list[dict] = []

    fault_counts: dict[str, int] = {}
    no_fault = 0

    for s in all_samples:
        kps = s["keypoints"]
        stroke_label = s["stroke_label"]
        filename = s["path"]

        # Stroke annotation: all clips
        stroke_annots.append(
            _to_annotation(kps, STROKE_LABEL_IDX[stroke_label], filename)
        )

        # Fault annotation: only beginner clips with an assigned fault
        if not s["is_expert"]:
            fault = _assign_fault(s["features"], stroke_label, expert_ref)
            if fault is not None:
                fault_annots.append(
                    _to_annotation(kps, FAULT_LABEL_IDX[fault], filename)
                )
                fault_counts[fault] = fault_counts.get(fault, 0) + 1
            else:
                no_fault += 1

    # Save
    stroke_path = out_dir / "stroke_annotations.pkl"
    fault_path = out_dir / "fault_annotations.pkl"

    with open(stroke_path, "wb") as f:
        pickle.dump(stroke_annots, f)
    with open(fault_path, "wb") as f:
        pickle.dump(fault_annots, f)

    print(f"\nStroke annotations: {len(stroke_annots)} clips -> {stroke_path}")
    print(f"Fault annotations:  {len(fault_annots)} clips -> {fault_path}")
    print(f"  Fault label distribution: {dict(sorted(fault_counts.items()))}")
    print(f"  Beginner clips with no fault assigned: {no_fault}")
    print("\nNext: python -m pipeline.scripts.train_posec3d --annotations data/thetis/stroke_annotations.pkl --task stroke ...")


if __name__ == "__main__":
    main()
