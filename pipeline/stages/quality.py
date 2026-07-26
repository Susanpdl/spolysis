from __future__ import annotations
import os
import cv2
import numpy as np
from dataclasses import dataclass
import structlog

log = structlog.get_logger(__name__)

BLUR_THRESHOLD = 100.0
MIN_VISIBLE_FRACTION = 0.6
MAX_OCCLUDED_FRACTION = 0.4
MAX_LOW_CONF_JOINTS = 4
CONFIDENCE_THRESHOLD = 0.3


@dataclass
class QualityResult:
    passed: bool
    reason: str | None = None


def _laplacian_variance(image_path: str) -> float:
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0
    h, w = img.shape
    # Center crop 50%
    ch, cw = h // 4, w // 4
    center = img[ch : h - ch, cw : w - cw]
    return float(cv2.Laplacian(center, cv2.CV_64F).var())


def check_quality(
    frame_dir: str,
    keypoints: np.ndarray,  # (T, 17, 3) - x, y, confidence
    sample_every: int = 5,
) -> QualityResult:
    """
    Run quality gate on extracted frames and pose keypoints.

    Checks:
    1. Blur: mean Laplacian variance of sampled frames must exceed threshold.
    2. Framing: all 17 keypoints visible (conf > 0.3) in >= 60% of frames.
    3. Occlusion: <= 40% of frames may have > 4 low-confidence keypoints.
    """
    frames = sorted(f for f in os.listdir(frame_dir) if f.endswith(".jpg"))
    if not frames:
        return QualityResult(passed=False, reason="No frames extracted from video")

    # --- Blur check ---
    sampled = frames[::sample_every]
    blur_scores = [_laplacian_variance(os.path.join(frame_dir, f)) for f in sampled]
    mean_blur = float(np.mean(blur_scores))
    if mean_blur < BLUR_THRESHOLD:
        log.info("quality_fail_blur", mean_blur=mean_blur, threshold=BLUR_THRESHOLD)
        return QualityResult(
            passed=False,
            reason=f"Video is too blurry (sharpness score {mean_blur:.1f}, minimum {BLUR_THRESHOLD}). "
                   "Try recording in better lighting or ensure the camera is stable.",
        )

    T = keypoints.shape[0]
    if T == 0:
        return QualityResult(passed=False, reason="No pose keypoints detected in video")

    conf = keypoints[:, :, 2]  # (T, 17)

    # --- Framing check: all 17 joints visible in >= 60% of frames ---
    all_visible = (conf > CONFIDENCE_THRESHOLD).all(axis=1)  # (T,)
    visible_fraction = float(all_visible.mean())
    if visible_fraction < MIN_VISIBLE_FRACTION:
        log.info("quality_fail_framing", visible_fraction=visible_fraction)
        return QualityResult(
            passed=False,
            reason=f"Your full body was not visible in {visible_fraction*100:.0f}% of frames "
                   f"(minimum {MIN_VISIBLE_FRACTION*100:.0f}%). Make sure your whole body is in frame.",
        )

    # --- Occlusion check: > 4 low-conf joints in <= 40% of frames ---
    low_conf_count = (conf < CONFIDENCE_THRESHOLD).sum(axis=1)  # (T,)
    occluded_frames = (low_conf_count > MAX_LOW_CONF_JOINTS).mean()
    if occluded_frames > MAX_OCCLUDED_FRACTION:
        log.info("quality_fail_occlusion", occluded_fraction=occluded_frames)
        return QualityResult(
            passed=False,
            reason=f"Parts of your body were obscured in too many frames ({occluded_frames*100:.0f}%). "
                   "Ensure nothing is blocking the camera view and you are well-lit.",
        )

    log.info("quality_pass", blur=mean_blur, visible_fraction=visible_fraction, occluded_fraction=occluded_frames)
    return QualityResult(passed=True)


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame-dir", required=True)
    parser.add_argument("--keypoints", required=True, help="Path to keypoints .npy file")
    args = parser.parse_args()
    kps = np.load(args.keypoints)
    result = check_quality(args.frame_dir, kps)
    print(json.dumps({"passed": result.passed, "reason": result.reason}))
