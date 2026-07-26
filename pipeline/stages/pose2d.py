from __future__ import annotations
import os
import numpy as np
from dataclasses import dataclass
import structlog

log = structlog.get_logger(__name__)

RTMPOSE_CONFIG = "rtmpose-x_8xb256-420e_coco-256x192"


@dataclass
class Pose2DResult:
    keypoints: np.ndarray  # (T, 17, 3) - x, y, confidence in pixel coords
    frame_paths: list[str]
    bboxes: np.ndarray  # (T, 4) - x1, y1, x2, y2 of player crop


def run_pose_estimation(frame_dir: str) -> Pose2DResult:
    """
    Run RTMPose-x on all frames in frame_dir.
    Uses MMPoseInferencer which auto-downloads weights on first run.
    """
    try:
        from mmpose.apis import MMPoseInferencer
    except ImportError:
        raise ImportError(
            "mmpose is not installed. Run: pip install mmpose\n"
            "Then download weights: python -m pipeline.scripts.download_models"
        )

    frame_paths = sorted(
        os.path.join(frame_dir, f)
        for f in os.listdir(frame_dir)
        if f.endswith(".jpg")
    )
    if not frame_paths:
        raise ValueError(f"No frames found in {frame_dir}")

    log.info("pose_estimation_start", frame_count=len(frame_paths), config=RTMPOSE_CONFIG)

    try:
        inferencer = MMPoseInferencer(
            pose2d=RTMPOSE_CONFIG,
            device="cuda",
        )
    except Exception:
        log.warning("cuda_unavailable_falling_back_to_cpu")
        inferencer = MMPoseInferencer(
            pose2d=RTMPOSE_CONFIG,
            device="cpu",
        )

    all_keypoints = []
    all_bboxes = []

    for frame_path in frame_paths:
        results = list(inferencer(frame_path, show=False, return_vis=False))
        if not results or not results[0].get("predictions"):
            # No person detected - fill with zeros
            all_keypoints.append(np.zeros((17, 3), dtype=np.float32))
            all_bboxes.append(np.zeros(4, dtype=np.float32))
            continue

        preds = results[0]["predictions"][0]
        # Take the highest-confidence person detection
        if isinstance(preds, list):
            preds = sorted(preds, key=lambda p: p.get("bbox_score", 0), reverse=True)[0]

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
    import argparse, json
    parser = argparse.ArgumentParser(description="Run RTMPose-x on a directory of frames")
    parser.add_argument("--frame-dir", required=True)
    parser.add_argument("--output", required=True, help="Output .npy file for keypoints")
    args = parser.parse_args()
    result = run_pose_estimation(args.frame_dir)
    np.save(args.output, result.keypoints)
    print(f"Saved keypoints shape {result.keypoints.shape} to {args.output}")
