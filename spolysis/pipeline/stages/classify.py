from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Literal
import structlog
from pipeline.stages.segment import StrokeSegment

log = structlog.get_logger(__name__)

StrokeType = Literal["forehand", "backhand", "serve", "volley"]
FaultLabel = str  # e.g., "late_contact", "arm_only", etc.

STROKE_LABELS: list[StrokeType] = ["forehand", "backhand", "serve", "volley"]
ALL_FAULTS = [
    "late_contact",
    "open_stance",
    "low_follow_through",
    "arm_only",
    "no_hip_rotation",
    "grip_issue",
    "no_trophy_position",
    "low_toss",
]

# Per-stroke faults surfaced to the user (classifier may detect others; only these are shown)
FAULT_LABELS: dict[str, list[str]] = {
    "forehand": ["late_contact", "open_stance", "low_follow_through", "arm_only"],
    "backhand": ["late_contact", "low_follow_through", "grip_issue"],
    "serve":    ["no_trophy_position", "low_toss", "arm_only"],
    "volley":   ["late_contact", "open_stance"],
}

_FAULT_CONFIDENCE_THRESHOLD = 0.40


@dataclass
class ClassificationResult:
    stroke_type: StrokeType
    fault_label: FaultLabel | None
    confidence: float
    method: str  # "posec3d" | "heuristic"


# ---------------------------------------------------------------------------
# Heuristic fallback (active at launch; replaced by PoseC3D once trained)
# ---------------------------------------------------------------------------

def _heuristic_stroke_type(segment: StrokeSegment) -> tuple[StrokeType, float]:
    kps = segment.keypoints_norm  # (T, 17, 3)
    T = kps.shape[0]
    if T == 0:
        return "forehand", 0.5

    r_wrist = kps[:, 10, :2]
    r_wrist_y_vel = np.gradient(r_wrist[:, 1])

    upward_frames = (r_wrist_y_vel < -0.01).sum()
    if upward_frames > T * 0.4:
        return "serve", 0.65

    x_range = r_wrist[:, 0].max() - r_wrist[:, 0].min()

    if segment.prominence < 0.08 and x_range < 0.3:
        return "volley", 0.60

    x_vel_mean = float(np.gradient(r_wrist[:, 0]).mean())
    return ("forehand", 0.65) if x_vel_mean >= 0 else ("backhand", 0.63)


def _heuristic_fault(stroke_type: StrokeType, segment: StrokeSegment) -> FaultLabel | None:
    angles_list = segment.joint_angles
    if not angles_list:
        return None

    kps = segment.keypoints_norm
    T = kps.shape[0]
    mid = T // 2

    contact_angles = angles_list[mid] if mid < len(angles_list) else angles_list[-1]

    r_wrist_y_contact = float(kps[mid, 10, 1])
    r_wrist_y_end = float(kps[-1, 10, 1])

    hip_rot = contact_angles.get("shoulder_hip_rotation", 90.0)
    if hip_rot > 80.0:
        return "arm_only"

    r_wrist_x = kps[:, 10, 0]
    peak_frame = int(np.argmax(np.abs(np.gradient(r_wrist_x))))
    if peak_frame > T * 0.70:
        return "late_contact"

    if r_wrist_y_end > r_wrist_y_contact + 0.05:
        return "low_follow_through"

    if stroke_type in ("forehand", "volley"):
        hip_width = abs(float(kps[mid, 11, 0]) - float(kps[mid, 12, 0]))
        if hip_width > 0.25:
            return "open_stance"

    return None


# ---------------------------------------------------------------------------
# PoseC3D inference
# ---------------------------------------------------------------------------

def _posec3d_classify(
    segment: StrokeSegment,
    stroke_model_path: str,
    fault_model_path: str | None,
) -> ClassificationResult:
    from pipeline.models.posec3d import PoseC3DClassifier

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"

    kps = segment.keypoints_norm  # (T, 17, 3)

    # --- Stroke classification ---
    stroke_clf = PoseC3DClassifier(stroke_model_path, num_classes=len(STROKE_LABELS), device=device)
    stroke_probs = stroke_clf.predict(kps)
    stroke_idx = int(stroke_probs.argmax())
    stroke_type: StrokeType = STROKE_LABELS[stroke_idx]
    confidence = float(stroke_probs[stroke_idx])

    # --- Fault classification ---
    fault_label: FaultLabel | None = None
    if fault_model_path is not None:
        fault_clf = PoseC3DClassifier(fault_model_path, num_classes=len(ALL_FAULTS), device=device)
        fault_probs = fault_clf.predict(kps)
        fault_idx = int(fault_probs.argmax())
        # Only report fault if confident AND it applies to this stroke type
        valid_faults = FAULT_LABELS.get(stroke_type, [])
        candidate = ALL_FAULTS[fault_idx]
        if float(fault_probs[fault_idx]) >= _FAULT_CONFIDENCE_THRESHOLD and candidate in valid_faults:
            fault_label = candidate
    else:
        # Fault model not yet available - use heuristic for fault detection only
        fault_label = _heuristic_fault(stroke_type, segment)

    return ClassificationResult(
        stroke_type=stroke_type,
        fault_label=fault_label,
        confidence=confidence,
        method="posec3d",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_stroke(
    segment: StrokeSegment,
    stroke_model_path: str | None = None,
    fault_model_path: str | None = None,
) -> ClassificationResult:
    """
    Classify stroke type and fault.

    Uses PoseC3D when stroke_model_path is provided, otherwise heuristic.
    fault_model_path is optional even when PoseC3D is active - the heuristic
    handles fault detection until the fault model is trained.
    """
    if stroke_model_path is not None:
        try:
            return _posec3d_classify(segment, stroke_model_path, fault_model_path)
        except Exception as e:
            log.warning("posec3d_inference_failed_using_heuristic", error=str(e))

    log.info("using_heuristic_classifier")
    stroke_type, confidence = _heuristic_stroke_type(segment)
    fault_label = _heuristic_fault(stroke_type, segment)

    return ClassificationResult(
        stroke_type=stroke_type,
        fault_label=fault_label,
        confidence=confidence,
        method="heuristic",
    )


if __name__ == "__main__":
    import argparse
    from pipeline.stages.features import extract_features
    from pipeline.stages.segment import segment_strokes

    parser = argparse.ArgumentParser()
    parser.add_argument("--keypoints", required=True, help="Path to .npy keypoints file (T, 17, 3)")
    parser.add_argument("--stroke-model", help="Path to PoseC3D stroke checkpoint")
    parser.add_argument("--fault-model", help="Path to PoseC3D fault checkpoint")
    args = parser.parse_args()

    kps = np.load(args.keypoints)
    feats = extract_features(kps)
    seg = segment_strokes(feats)
    if not seg:
        print("No stroke detected")
    else:
        result = classify_stroke(seg, stroke_model_path=args.stroke_model, fault_model_path=args.fault_model)
        print(
            f"Stroke: {result.stroke_type}  Fault: {result.fault_label}  "
            f"Confidence: {result.confidence:.2f}  Method: {result.method}"
        )
