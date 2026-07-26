from __future__ import annotations
import numpy as np
import structlog

log = structlog.get_logger(__name__)

RTMPOSE_CONFIG = "rtmpose-x_8xb256-420e_coco-256x192"


class RTMPoseInferencer:
    """
    Wrapper around MMPoseInferencer for RTMPose-x.
    Lazy-initializes on first call to avoid import overhead.
    """

    def __init__(self, device: str = "cuda"):
        self._inferencer = None
        self._device = device

    def _get_inferencer(self):
        if self._inferencer is None:
            try:
                from mmpose.apis import MMPoseInferencer
            except ImportError:
                raise ImportError(
                    "mmpose is not installed. Run:\n"
                    "  pip install mmpose\n"
                    "Then download model weights:\n"
                    "  python -m pipeline.scripts.download_models"
                )
            try:
                self._inferencer = MMPoseInferencer(pose2d=RTMPOSE_CONFIG, device=self._device)
                log.info("rtmpose_initialized", config=RTMPOSE_CONFIG, device=self._device)
            except Exception as e:
                if self._device != "cpu":
                    log.warning("gpu_init_failed_falling_back", error=str(e))
                    self._inferencer = MMPoseInferencer(pose2d=RTMPOSE_CONFIG, device="cpu")
                else:
                    raise
        return self._inferencer

    def infer_frame(self, image_path: str) -> tuple[np.ndarray, np.ndarray]:
        """
        Run pose estimation on a single frame.

        Returns:
            keypoints: (17, 3) array of (x, y, confidence)
            bbox: (4,) array of (x1, y1, x2, y2)
        """
        inferencer = self._get_inferencer()
        results = list(inferencer(image_path, show=False, return_vis=False))

        if not results or not results[0].get("predictions"):
            return np.zeros((17, 3), dtype=np.float32), np.zeros(4, dtype=np.float32)

        preds = results[0]["predictions"][0]
        if isinstance(preds, list):
            preds = sorted(preds, key=lambda p: p.get("bbox_score", 0), reverse=True)[0]

        kps = np.array(preds["keypoints"], dtype=np.float32)
        scores = np.array(preds["keypoint_scores"], dtype=np.float32)
        kps_with_conf = np.concatenate([kps, scores[:, None]], axis=1)

        bbox = preds.get("bbox", [[0, 0, 0, 0]])[0]
        bbox_arr = np.array(bbox[:4], dtype=np.float32)

        return kps_with_conf, bbox_arr

    def infer_batch(self, image_paths: list[str]) -> tuple[np.ndarray, np.ndarray]:
        """
        Run pose estimation on multiple frames.

        Returns:
            keypoints: (T, 17, 3)
            bboxes: (T, 4)
        """
        all_kps, all_bboxes = [], []
        for path in image_paths:
            kps, bbox = self.infer_frame(path)
            all_kps.append(kps)
            all_bboxes.append(bbox)
        return np.stack(all_kps), np.stack(all_bboxes)
