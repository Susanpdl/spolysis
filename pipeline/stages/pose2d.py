from __future__ import annotations
import os
import numpy as np
from dataclasses import dataclass
import structlog

log = structlog.get_logger(__name__)

# RTMPose-x (700e, body7 pretrained, 384x288) - baked into image at build time.
# Config from projects/rtmpose; uses mmpose:: prefix for base refs which resolves
# from the installed mmpose package. Weights downloaded via wget during build.
_BAKED_CONFIG = "/opt/mmpose/rtmpose-x_8xb256-700e_coco-384x288.py"
_BAKED_WEIGHTS = "/opt/mmpose/rtmpose-x_body7.pth"


@dataclass
class Pose2DResult:
    keypoints: np.ndarray  # (T, 17, 3) - x, y, confidence in pixel coords
    frame_paths: list[str]
    bboxes: np.ndarray  # (T, 4) - x1, y1, x2, y2 of player crop


def _require_baked_rtmpose() -> None:
    missing = [
        path for path in (_BAKED_CONFIG, _BAKED_WEIGHTS) if not os.path.isfile(path)
    ]
    if missing:
        raise RuntimeError(
            "The trained RTMPose-x checkpoint is missing: "
            + ", ".join(missing)
            + ". Analysis cannot substitute another pose model."
        )


def _build_rtmpose_inferencer(inferencer_cls, config: str, weights: str):
    """Load the baked RTMPose-x checkpoint, falling back to CPU for the same files."""
    try:
        return inferencer_cls(pose2d=config, pose2d_weights=weights, device="cuda")
    except Exception:
        log.warning("cuda_unavailable_falling_back_to_cpu")
        return inferencer_cls(pose2d=config, pose2d_weights=weights, device="cpu")


def run_pose_estimation(frame_dir: str) -> Pose2DResult:
    """Run the baked RTMPose-x checkpoint on every frame in frame_dir."""
    frame_paths = sorted(
        os.path.join(frame_dir, f) for f in os.listdir(frame_dir) if f.endswith(".jpg")
    )
    if not frame_paths:
        raise ValueError(f"No frames found in {frame_dir}")

    _require_baked_rtmpose()

    try:
        from mmpose.apis import MMPoseInferencer
    except ImportError:
        raise ImportError(
            "mmpose is not installed. Run: pip install mmpose\n"
            "Use the GPU image defined in pipeline/app.py for pinned model weights."
        )

    log.info("pose_estimation_start", frame_count=len(frame_paths))
    log.info(
        "rtmpose_using_baked_checkpoint",
        config=_BAKED_CONFIG,
        weights=_BAKED_WEIGHTS,
    )
    inferencer = _build_rtmpose_inferencer(
        MMPoseInferencer, _BAKED_CONFIG, _BAKED_WEIGHTS
    )

    all_keypoints = []
    all_bboxes = []
    previous_box = None

    for frame_path in frame_paths:
        results = list(inferencer(frame_path, show=False, return_vis=False))
        if not results or not results[0].get("predictions"):
            # No person detected - fill with zeros
            all_keypoints.append(np.zeros((17, 3), dtype=np.float32))
            all_bboxes.append(np.zeros(4, dtype=np.float32))
            continue

        preds = results[0]["predictions"][0]
        # Track the foreground player rather than switching to a spectator
        # whenever detection confidence changes between frames.
        if isinstance(preds, list):
            if not preds:
                all_keypoints.append(np.zeros((17, 3), dtype=np.float32))
                all_bboxes.append(np.zeros(4, dtype=np.float32))
                continue

            def score(person):
                box = np.asarray(person.get("bbox", [[0, 0, 0, 0]])).reshape(-1)[:4]
                area = max(0, box[2] - box[0]) * max(0, box[3] - box[1])
                if previous_box is None:
                    return area * float(person.get("bbox_score", 1))
                intersection = np.maximum(
                    0,
                    np.minimum(box[2:], previous_box[2:])
                    - np.maximum(box[:2], previous_box[:2]),
                ).prod()
                prior_area = np.maximum(0, previous_box[2:] - previous_box[:2]).prod()
                return float(intersection / max(area + prior_area - intersection, 1))

            preds = max(preds, key=score)
        previous_box = np.asarray(preds.get("bbox", [[0, 0, 0, 0]])).reshape(-1)[:4]

        kps = np.array(preds["keypoints"], dtype=np.float32)  # (17, 2)
        scores = np.array(preds["keypoint_scores"], dtype=np.float32)  # (17,)
        kps_with_conf = np.concatenate([kps, scores[:, None]], axis=1)  # (17, 3)
        all_keypoints.append(kps_with_conf)

        bbox = preds.get("bbox", [[0, 0, 0, 0]])[0]
        all_bboxes.append(np.array(bbox[:4], dtype=np.float32))

    keypoints = np.stack(all_keypoints, axis=0)  # (T, 17, 3)
    bboxes = np.stack(all_bboxes, axis=0)  # (T, 4)

    log.info("pose_estimation_done", frames=len(frame_paths), shape=keypoints.shape)
    return Pose2DResult(keypoints=keypoints, frame_paths=frame_paths, bboxes=bboxes)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run RTMPose-x on a directory of frames"
    )
    parser.add_argument("--frame-dir", required=True)
    parser.add_argument(
        "--output", required=True, help="Output .npy file for keypoints"
    )
    args = parser.parse_args()
    result = run_pose_estimation(args.frame_dir)
    np.save(args.output, result.keypoints)
    print(f"Saved keypoints shape {result.keypoints.shape} to {args.output}")
