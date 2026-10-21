from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
import structlog

from pipeline.stages.pose2d import Pose2DResult

log = structlog.get_logger(__name__)


@dataclass
class LiftResult:
    keypoints_3d: (
        np.ndarray
    )  # (T, 17, 3), relative coordinates (root = midpoint of hips)
    model_name: str  # "motionbert"
    fps: float


def _normalize_2d_for_lifting(
    keypoints: np.ndarray,  # (T, 17, 3) pixel coords + confidence
    bboxes: np.ndarray,  # (T, 4) x1, y1, x2, y2
) -> np.ndarray:
    """
    Normalize visible image keypoints to [-1, 1] for MotionBERT.

    Use one center and uniform scale across the selected window to preserve
    aspect ratio and motion between frames.
    """
    valid = keypoints[..., 2] > 0.3
    if valid.sum() < 4:
        raise ValueError("Too few visible joints for reconstruction")
    points = keypoints[..., :2][valid]
    low, high = points.min(axis=0), points.max(axis=0)
    scale = float((high - low).max())
    if scale < 1:
        raise ValueError("Degenerate player framing")
    center = (low + high) / 2
    return np.clip((keypoints[..., :2] - center) * (2 / scale), -1, 1).astype(
        np.float32
    )


def lift_to_3d(
    pose2d: Pose2DResult,
    model_name: str = "motionbert",
    checkpoint: str | None = None,
    fps: float = 30.0,
) -> LiftResult:
    """
    Reconstruct root-relative 3D motion from image keypoints with MotionBERT.

    The output uses the shared COCO-17 layout with its root at the hip midpoint.
    Coordinates are relative estimates, not calibrated millimetres.
    """
    if model_name != "motionbert":
        raise ValueError(
            f"Unknown model_name '{model_name}'; only the validated MotionBERT integration is enabled"
        )

    keypoints_2d_norm = _normalize_2d_for_lifting(pose2d.keypoints, pose2d.bboxes)
    T = keypoints_2d_norm.shape[0]

    log.info(
        "lift_3d_start",
        model=model_name,
        frames=T,
        fps=fps,
        checkpoint=checkpoint,
    )

    from pipeline.models.motionbert import MotionBERTLifter

    lifter = MotionBERTLifter(checkpoint=checkpoint)

    # Confidence scores are passed so the lifter can down-weight occluded joints
    confidence = pose2d.keypoints[:, :, 2]  # (T, 17)
    keypoints_3d = lifter.infer(keypoints_2d_norm, confidence)  # (T, 17, 3)

    if keypoints_3d.shape != (T, 17, 3):
        raise RuntimeError(
            f"Lifter returned unexpected shape {keypoints_3d.shape}; expected ({T}, 17, 3)"
        )

    log.info(
        "lift_3d_done",
        model=model_name,
        output_shape=keypoints_3d.shape,
        root_mean=float(np.abs(keypoints_3d).mean()),
    )

    return LiftResult(
        keypoints_3d=keypoints_3d.astype(np.float32),
        model_name=model_name,
        fps=fps,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run 3D pose lifting on 2D keypoints")
    parser.add_argument(
        "--keypoints",
        required=True,
        help="Path to .npy file of shape (T, 17, 3) - x, y, confidence in pixel coords",
    )
    parser.add_argument(
        "--bboxes",
        required=True,
        help="Path to .npy file of shape (T, 4) - x1, y1, x2, y2 player crop bboxes",
    )
    parser.add_argument(
        "--model",
        default="motionbert",
        choices=["motionbert"],
        help="Which 3D lifter to use (default: motionbert)",
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help="Path to model checkpoint (.pth). Uses default baked path if omitted.",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
        help="Frame rate of the source video (default: 30.0)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to save output .npy of shape (T, 17, 3)",
    )
    args = parser.parse_args()

    kps_2d = np.load(args.keypoints)
    bboxes = np.load(args.bboxes)

    # Reconstruct a minimal Pose2DResult from the loaded arrays
    pose2d = Pose2DResult(
        keypoints=kps_2d,
        frame_paths=[],
        bboxes=bboxes,
    )

    result = lift_to_3d(
        pose2d=pose2d,
        model_name=args.model,
        checkpoint=args.checkpoint,
        fps=args.fps,
    )

    np.save(args.output, result.keypoints_3d)
    print(
        f"Saved 3D keypoints shape {result.keypoints_3d.shape} "
        f"from {result.model_name} to {args.output}"
    )
