"""
PoseC3D inference wrapper.

Input: (T, 17, 3) normalized keypoints (x, y, confidence) from RTMPose-x.
Pipeline:
  1. generate_pseudo_heatmap: keypoints -> (V, T, H, W) Gaussian heatmap volume
  2. PoseC3DClassifier: heatmap volume -> class logits via SlowOnly 3D CNN

Two separate classifiers:
  - stroke model: 4-class (forehand, backhand, serve, volley)
  - fault model:  8-class (late_contact, open_stance, ...) - optional

The confidence-weighted Gaussian heatmap preserves the full RTMPose-x output
(spatial uncertainty, multi-modal distributions) that coordinate-only models
like ST-GCN discard. This is the primary accuracy advantage of PoseC3D.
"""
from __future__ import annotations

import numpy as np
import structlog

log = structlog.get_logger(__name__)

STROKE_LABELS = ["forehand", "backhand", "serve", "volley"]
FAULT_LABELS = [
    "late_contact",
    "open_stance",
    "low_follow_through",
    "arm_only",
    "no_hip_rotation",
    "grip_issue",
    "no_trophy_position",
    "low_toss",
]

# SlowOnly-R50 config for COCO-17 skeleton input.
# in_channels=17 treats joints as the channel dim (analogous to RGB=3 for video).
# I3DHead in_channels=512 matches 3-stage SlowOnly output width.
_BACKBONE_CFG = dict(
    type="ResNet3dSlowOnly",
    depth=50,
    pretrained=None,
    lateral=False,
    in_channels=17,
    base_channels=32,
    num_stages=3,
    out_indices=(2,),
    stage_blocks=(4, 6, 3),
    conv1_stride=(1, 1),
    pool1_stride=(1, 1),
    inflate=(0, 1, 1),
    spatial_strides=(2, 2, 2),
    temporal_strides=(1, 1, 2),
)
_HEAD_IN_CHANNELS = 512  # output width of 3-stage SlowOnly with base_channels=32


def generate_pseudo_heatmap(
    keypoints_norm: np.ndarray,
    scores: np.ndarray,
    heatmap_size: tuple[int, int] = (56, 56),
    sigma: float = 0.6,
) -> np.ndarray:
    """
    Convert normalized keypoints to a pseudo-heatmap volume.

    Args:
        keypoints_norm: (T, V, 2) - x, y in [0, 1]
        scores:         (T, V)    - confidence in [0, 1]
        heatmap_size:   (H, W)    - output spatial dims
        sigma:          Gaussian width in heatmap pixels

    Returns:
        (V, T, H, W) float32 heatmap volume
    """
    T, V, _ = keypoints_norm.shape
    H, W = heatmap_size

    xx, yy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    # xx, yy: (H, W) each

    # Scale to heatmap grid - (T, V, 1, 1)
    cx = (keypoints_norm[..., 0] * (W - 1))[:, :, None, None]
    cy = (keypoints_norm[..., 1] * (H - 1))[:, :, None, None]
    conf = scores[:, :, None, None]  # (T, V, 1, 1)

    # Squared distance from each grid point to each joint center - (T, V, H, W)
    d2 = (xx[None, None] - cx) ** 2 + (yy[None, None] - cy) ** 2

    # Confidence-weighted Gaussian - (T, V, H, W)
    heatmaps = conf * np.exp(-d2 / (2 * sigma ** 2))

    # Zero out very low confidence keypoints to avoid noise
    heatmaps[scores < 0.05] = 0.0

    # (T, V, H, W) -> (V, T, H, W)
    return heatmaps.transpose(1, 0, 2, 3).astype(np.float32)


def _build_recognizer(num_classes: int) -> "torch.nn.Module":
    from mmaction.registry import MODELS

    cfg = dict(
        type="Recognizer3D",
        backbone=_BACKBONE_CFG,
        cls_head=dict(
            type="I3DHead",
            in_channels=_HEAD_IN_CHANNELS,
            num_classes=num_classes,
            spatial_type="avg",
            dropout_ratio=0.5,
        ),
        data_preprocessor=dict(
            type="ActionDataPreprocessor",
            mean=[0.0],
            std=[1.0],
        ),
    )
    model = MODELS.build(cfg)
    model.eval()
    return model


class PoseC3DClassifier:
    """
    Wraps a fine-tuned PoseC3D checkpoint for inference.

    Args:
        checkpoint_path: Local path or R2-downloaded path to .pth checkpoint.
        num_classes:     Number of output classes (4 for stroke, 8 for fault).
        device:          "cuda" or "cpu".
    """

    def __init__(self, checkpoint_path: str, num_classes: int, device: str = "cuda") -> None:
        import torch
        from mmaction.registry import MODELS  # noqa: F401 - validates install

        self._device = device
        self._num_classes = num_classes

        try:
            model = _build_recognizer(num_classes)
            checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
            state_dict = checkpoint.get("state_dict", checkpoint)
            model.load_state_dict(state_dict, strict=False)
            model.to(device)
            model.eval()
            self._model = model
            log.info("posec3d_model_loaded", classes=num_classes, device=device)
        except Exception as e:
            raise RuntimeError(f"Failed to load PoseC3D checkpoint: {e}") from e

    def predict(self, keypoints_norm: np.ndarray) -> np.ndarray:
        """
        Run inference on a stroke segment.

        Args:
            keypoints_norm: (T, 17, 3) - normalized x, y, confidence

        Returns:
            class probabilities (num_classes,)
        """
        import torch

        kp_xy = keypoints_norm[:, :, :2]  # (T, 17, 2)
        conf = keypoints_norm[:, :, 2]     # (T, 17)

        heatmaps = generate_pseudo_heatmap(kp_xy, conf)  # (17, T, 56, 56)

        # (1, 17, T, 56, 56)
        x = torch.from_numpy(heatmaps[None]).to(self._device)

        with torch.no_grad():
            # Access backbone and head directly to bypass MMAction2 data pipeline
            feats = self._model.backbone(x)
            logits = self._model.cls_head(feats)
            probs = logits.softmax(dim=-1)[0].cpu().numpy()

        return probs
