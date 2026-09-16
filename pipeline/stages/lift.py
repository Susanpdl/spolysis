from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

import numpy as np
import structlog

from pipeline.stages.pose2d import Pose2DResult

log = structlog.get_logger(__name__)


@dataclass
class LiftResult:
    keypoints_3d: np.ndarray  # (T, 17, 3) in mm, root-relative (root = midpoint of hips)
    model_name: str           # "motionbert" | "posemamba"
    fps: float


def _normalize_2d_for_lifting(
    keypoints: np.ndarray,  # (T, 17, 3) pixel coords + confidence
    bboxes: np.ndarray,     # (T, 4) x1, y1, x2, y2
) -> np.ndarray:
    """
    Normalize pixel keypoints to [-1, 1] per the convention expected by both
    MotionBERT and PoseMamba: center at bbox center, scale by half-diagonal.

    Half-diagonal rather than side length because the player crop is usually
    portrait-shaped - using the diagonal prevents extreme axis-asymmetric
    scaling that would distort aspect ratio for tall narrow crops.
    """
    T = keypoints.shape[0]
    out = np.zeros((T, 17, 2), dtype=np.float32)

    for t in range(T):
        x1, y1, x2, y2 = bboxes[t]
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        half_diag = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) / 2.0

        # Guard against degenerate (all-zero) bboxes on frames with no detection
        if half_diag < 1e-6:
            half_diag = 1.0

        xy = keypoints[t, :, :2]
        normalized = (xy - np.array([cx, cy])) / half_diag
        out[t] = np.clip(normalized, -2.0, 2.0)

    return out  # (T, 17, 2)


def lift_to_3d(
    pose2d: Pose2DResult,
    model_name: str = "motionbert",
    checkpoint: str | None = None,
    fps: float = 30.0,
) -> LiftResult:
    """
    Lift a 2D keypoint sequence to 3D using MotionBERT or PoseMamba.

    Both models return root-relative coordinates in millimetres where the root
    is the midpoint of L_HIP (11) and R_HIP (12). This convention is shared
    with downstream normalize3d and smooth3d stages so no re-rooting is needed
    between stages.
    """
    if model_name not in ("motionbert", "posemamba"):
        raise ValueError(f"Unknown model_name '{model_name}'; must be 'motionbert' or 'posemamba'")

    keypoints_2d_norm = _normalize_2d_for_lifting(pose2d.keypoints, pose2d.bboxes)
    T = keypoints_2d_norm.shape[0]

    log.info(
        "lift_3d_start",
        model=model_name,
        frames=T,
        fps=fps,
        checkpoint=checkpoint,
    )

    if model_name == "motionbert":
        from pipeline.models.motionbert import MotionBERTLifter
        lifter = MotionBERTLifter(checkpoint=checkpoint)
    else:
        from pipeline.models.posemamba import PoseMambaLifter
        lifter = PoseMambaLifter(checkpoint=checkpoint)

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
        root_mean_mm=float(np.abs(keypoints_3d).mean()),
    )

    return LiftResult(
        keypoints_3d=keypoints_3d.astype(np.float32),
        model_name=model_name,
        fps=fps,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run 3D pose lifting on 2D keypoints"
    )
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
        choices=["motionbert", "posemamba"],
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
