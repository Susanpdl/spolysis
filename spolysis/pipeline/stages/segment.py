from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from scipy.signal import find_peaks
import structlog
from pipeline.stages.features import FeatureSet

log = structlog.get_logger(__name__)

WINDOW_HALF = 45   # ±45 frames around stroke peak
MIN_DISTANCE = 15  # minimum frames between peaks
MIN_PROMINENCE = 0.05


@dataclass
class StrokeSegment:
    start_frame: int
    end_frame: int
    peak_frame: int
    prominence: float
    keypoints_norm: np.ndarray   # (window, 17, 3)
    joint_angles: list[dict[str, float]]


def segment_strokes(features: FeatureSet) -> StrokeSegment | None:
    """
    Detect stroke segments using wrist velocity peaks.
    Returns the highest-prominence stroke window, or None if no stroke found.
    """
    vel = features.wrist_velocity_smooth
    T = len(vel)

    if T < MIN_DISTANCE * 2:
        log.warning("segment_too_short", frames=T)
        return None

    peaks, props = find_peaks(
        np.abs(vel),
        distance=MIN_DISTANCE,
        prominence=MIN_PROMINENCE,
    )

    if len(peaks) == 0:
        log.info("no_stroke_peaks_found")
        return None

    # Take the highest-prominence peak
    best_idx = int(np.argmax(props["prominences"]))
    peak = int(peaks[best_idx])
    prominence = float(props["prominences"][best_idx])

    start = max(0, peak - WINDOW_HALF)
    end = min(T, peak + WINDOW_HALF)

    log.info("stroke_segment_found", peak=peak, start=start, end=end, prominence=prominence)

    return StrokeSegment(
        start_frame=start,
        end_frame=end,
        peak_frame=peak,
        prominence=prominence,
        keypoints_norm=features.keypoints_norm[start:end],
        joint_angles=features.joint_angles_per_frame[start:end],
    )


if __name__ == "__main__":
    import argparse
    from pipeline.stages.features import extract_features
    parser = argparse.ArgumentParser()
    parser.add_argument("--keypoints", required=True)
    args = parser.parse_args()
    kps = np.load(args.keypoints)
    feats = extract_features(kps)
    seg = segment_strokes(feats)
    if seg:
        print(f"Stroke: frames {seg.start_frame}-{seg.end_frame}, peak at {seg.peak_frame}, prominence {seg.prominence:.3f}")
    else:
        print("No stroke detected")
