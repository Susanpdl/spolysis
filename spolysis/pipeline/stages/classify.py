from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Literal
import structlog
from pipeline.stages.segment import StrokeSegment

log = structlog.get_logger(__name__)

StrokeType = Literal["forehand", "backhand", "serve", "volley"]
FaultLabel = str  # e.g., "late_contact", "arm_only", etc.

FAULT_LABELS: dict[str, list[str]] = {
    "forehand": ["late_contact", "open_stance", "low_follow_through", "arm_only"],
    "backhand": ["late_contact", "low_follow_through", "grip_issue"],
    "serve":    ["no_trophy_position", "low_toss", "arm_only"],
    "volley":   ["late_contact", "open_stance"],
}


@dataclass
class ClassificationResult:
    stroke_type: StrokeType
    fault_label: FaultLabel | None
    confidence: float
    method: str  # "stgcn" or "heuristic"


def _heuristic_stroke_type(segment: StrokeSegment) -> tuple[StrokeType, float]:
    """
    Rule-based stroke type from wrist trajectory shape.
    """
    kps = segment.keypoints_norm  # (T, 17, 3)
    T = kps.shape[0]
    if T == 0:
        return "forehand", 0.5

    r_wrist = kps[:, 10, :2]   # (T, 2) - right wrist
    r_wrist_y_vel = np.gradient(r_wrist[:, 1])  # y-velocity

    # Serve: strong upward arc at peak (negative y-vel in image coords means up)
    upward_frames = (r_wrist_y_vel < -0.01).sum()
    if upward_frames > T * 0.4:
        return "serve", 0.65

    # Wrist crosses midline direction
    x_range = r_wrist[:, 0].max() - r_wrist[:, 0].min()
    y_range = r_wrist[:, 1].max() - r_wrist[:, 1].min()

    # Volley: short punchy motion
    if segment.prominence < 0.08 and x_range < 0.3:
        return "volley", 0.60

    # Forehand vs backhand: direction of horizontal sweep
    x_vel_mean = float(np.gradient(r_wrist[:, 0]).mean())
    if x_vel_mean >= 0:
        return "forehand", 0.65
    else:
        return "backhand", 0.63


def _heuristic_fault(stroke_type: StrokeType, segment: StrokeSegment) -> FaultLabel | None:
    """
    Rule-based fault detection from joint angles at key moments.
    """
    angles_list = segment.joint_angles
    if not angles_list:
        return None

    kps = segment.keypoints_norm
    T = kps.shape[0]
    mid = T // 2  # approximate contact point

    # Use angles at contact (mid) and follow-through (last 20%)
    contact_angles = angles_list[mid] if mid < len(angles_list) else angles_list[-1]
    followthrough_angles = angles_list[min(int(T * 0.8), len(angles_list) - 1)]

    r_wrist_y_contact = float(kps[mid, 10, 1])
    r_wrist_y_end = float(kps[-1, 10, 1])

    # Arm-only swing: minimal hip rotation throughout stroke
    hip_rot = contact_angles.get("shoulder_hip_rotation", 90.0)
    if hip_rot > 80.0:  # near-parallel = no hip rotation
        return "arm_only"

    # Late contact: wrist peak in last 30% of stroke window
    r_wrist_x = kps[:, 10, 0]
    peak_frame = int(np.argmax(np.abs(np.gradient(r_wrist_x))))
    if peak_frame > T * 0.70:
        return "late_contact"

    # Low follow-through: wrist ends lower than at contact
    if r_wrist_y_end > r_wrist_y_contact + 0.05:  # y increases downward
        return "low_follow_through"

    # Open stance for forehand/volley: hips facing camera (hip width large)
    if stroke_type in ("forehand", "volley"):
        l_hip_x = float(kps[mid, 11, 0])
        r_hip_x = float(kps[mid, 12, 0])
        hip_width = abs(l_hip_x - r_hip_x)
        if hip_width > 0.25:
            return "open_stance"

    return None


def classify_stroke(segment: StrokeSegment, model_path: str | None = None) -> ClassificationResult:
    """
    Classify stroke type and fault. Uses ST-GCN model if weights are available,
    falls back to heuristic if not.
    """
    if model_path is not None:
        try:
            return _stgcn_classify(segment, model_path)
        except Exception as e:
            log.warning("stgcn_inference_failed_using_heuristic", error=str(e))

    log.info("using_heuristic_classifier")
    stroke_type, confidence = _heuristic_stroke_type(segment)
    fault_label = _heuristic_fault(stroke_type, segment)

    return ClassificationResult(
        stroke_type=stroke_type,
        fault_label=fault_label,
        confidence=confidence,
        method="heuristic",
    )


def _stgcn_classify(segment: StrokeSegment, model_path: str) -> ClassificationResult:
    import torch
    from pipeline.models.stgcn import STGCN

    kps = segment.keypoints_norm  # (T, 17, 3)
    # Pad or truncate to fixed length 90 frames
    target_len = 90
    T = kps.shape[0]
    if T < target_len:
        pad = np.zeros((target_len - T, 17, 3), dtype=np.float32)
        kps_fixed = np.concatenate([kps, pad], axis=0)
    else:
        kps_fixed = kps[:target_len]

    # (T, 17, 3) -> (1, 3, T, 17, 1) for ST-GCN
    x = torch.from_numpy(kps_fixed).float()
    x = x.permute(2, 0, 1).unsqueeze(0).unsqueeze(-1)  # (1, 3, T, 17, 1)

    checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
    num_stroke_classes = checkpoint.get("num_stroke_classes", 4)
    num_fault_classes = checkpoint.get("num_fault_classes", 8)

    model = STGCN(in_channels=3, num_class=num_stroke_classes + num_fault_classes, num_point=17)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    STROKE_LABELS: list[StrokeType] = ["forehand", "backhand", "serve", "volley"]
    ALL_FAULTS = [
        "late_contact", "open_stance", "low_follow_through", "arm_only",
        "no_hip_rotation", "grip_issue", "no_trophy_position", "low_toss",
    ]

    with torch.no_grad():
        logits = model(x)  # (1, num_stroke_classes + num_fault_classes)
        stroke_logits = logits[0, :num_stroke_classes]
        fault_logits = logits[0, num_stroke_classes:]

        stroke_probs = torch.softmax(stroke_logits, dim=0).numpy()
        fault_probs = torch.softmax(fault_logits, dim=0).numpy()

        stroke_idx = int(stroke_probs.argmax())
        fault_idx = int(fault_probs.argmax())

        stroke_type = STROKE_LABELS[stroke_idx]
        confidence = float(stroke_probs[stroke_idx])

        # Only report fault if confidence is high enough
        fault_label: str | None = None
        if float(fault_probs[fault_idx]) > 0.4:
            fault_label = ALL_FAULTS[fault_idx]

    return ClassificationResult(
        stroke_type=stroke_type,
        fault_label=fault_label,
        confidence=confidence,
        method="stgcn",
    )


if __name__ == "__main__":
    import argparse
    from pipeline.stages.features import extract_features
    from pipeline.stages.segment import segment_strokes
    parser = argparse.ArgumentParser()
    parser.add_argument("--keypoints", required=True)
    parser.add_argument("--model", help="Path to ST-GCN checkpoint")
    args = parser.parse_args()
    kps = np.load(args.keypoints)
    feats = extract_features(kps)
    seg = segment_strokes(feats)
    if not seg:
        print("No stroke detected")
    else:
        result = classify_stroke(seg, model_path=args.model)
        print(f"Stroke: {result.stroke_type}, Fault: {result.fault_label}, "
              f"Confidence: {result.confidence:.2f}, Method: {result.method}")
