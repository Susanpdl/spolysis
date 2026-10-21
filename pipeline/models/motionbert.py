"""Strict pretrained MotionBERT inference, with explicit COCO/H36M conversion.

Model configuration and preprocessing follow Walter0807/MotionBERT.
Output uses COCO joint order with Y up; scale is relative, not measured millimetres.
"""

from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

_WINDOW = 243
_STRIDE = 81


def coco_to_h36m(coco: np.ndarray) -> np.ndarray:
    out = np.zeros_like(coco)
    out[:, 0] = (coco[:, 11] + coco[:, 12]) / 2
    out[:, [1, 2, 3, 4, 5, 6]] = coco[:, [12, 14, 16, 11, 13, 15]]
    out[:, 8] = (coco[:, 5] + coco[:, 6]) / 2
    out[:, 7] = (out[:, 0] + out[:, 8]) / 2
    out[:, 9] = coco[:, 0]
    out[:, 10] = (coco[:, 1] + coco[:, 2]) / 2
    out[:, [11, 12, 13, 14, 15, 16]] = coco[:, [5, 7, 9, 6, 8, 10]]
    return out


def h36m_to_coco(h36m: np.ndarray) -> np.ndarray:
    out = np.zeros_like(h36m)
    out[:, 0] = h36m[:, 9]
    # H36M has no separate eye/ear predictions. Face points are display-only.
    out[:, 1:5] = h36m[:, 10:11]
    out[:, [5, 7, 9, 6, 8, 10]] = h36m[:, [11, 12, 13, 14, 15, 16]]
    out[:, [12, 14, 16, 11, 13, 15]] = h36m[:, [1, 2, 3, 4, 5, 6]]
    out -= (out[:, 11:12] + out[:, 12:13]) / 2
    out[:, :, 1] *= -1  # camera image Y down -> display Y up
    return out


class MotionBERTLifter:
    _DEFAULT_CHECKPOINT = "/opt/weights/motionbert/MB_ft_h36m.bin"

    def __init__(self, checkpoint: str | None = None, device: str = "cuda"):
        import torch

        self.device = device
        checkpoint = checkpoint or self._DEFAULT_CHECKPOINT
        if not Path(checkpoint).is_file():
            raise RuntimeError(
                "The trained MotionBERT checkpoint is missing. Analysis is unavailable."
            )
        sys.path.insert(0, "/opt/motionbert")
        from lib.model.DSTformer import DSTformer

        self.model = DSTformer(
            dim_in=3,
            dim_out=3,
            dim_feat=512,
            dim_rep=512,
            depth=5,
            num_heads=8,
            mlp_ratio=2,
            maxlen=_WINDOW,
        )
        raw = torch.load(checkpoint, map_location="cpu", weights_only=True)
        state = raw.get("model_pos", raw.get("state_dict", raw))
        state = {k.removeprefix("module."): v for k, v in state.items()}
        self.model.load_state_dict(state, strict=True)
        self.model.to(device).eval()

    def infer(self, xy: np.ndarray, confidence: np.ndarray) -> np.ndarray:
        import torch

        if len(xy) < 2 or not np.isfinite(xy).all():
            raise ValueError("At least two finite pose frames are required")
        data = coco_to_h36m(np.concatenate([xy, confidence[..., None]], axis=-1))
        output = np.zeros((len(data), 17, 3), dtype=np.float32)
        weights = np.zeros(len(data), dtype=np.float32)
        flip_indices = [0, 4, 5, 6, 1, 2, 3, 7, 8, 9, 10, 14, 15, 16, 11, 12, 13]
        for start in range(0, len(data), _STRIDE):
            clip = data[start : start + _WINDOW]
            n = len(clip)
            clip = np.pad(clip, ((0, _WINDOW - n), (0, 0), (0, 0)), mode="edge")
            x = torch.as_tensor(clip[None], dtype=torch.float32, device=self.device)
            with torch.inference_mode():
                flipped = x[:, :, flip_indices].clone()
                flipped[..., 0] *= -1
                a = self.model(x)
                b = self.model(flipped)[:, :, flip_indices]
                b[..., 0] *= -1
                prediction = ((a + b) / 2)[0, :n].cpu().numpy()
            blend = np.maximum(np.hanning(_WINDOW)[:n], 0.01)
            output[start : start + n] += prediction * blend[:, None, None]
            weights[start : start + n] += blend
            if start + n == len(data):
                break
        result = h36m_to_coco(output / weights[:, None, None])
        if not np.isfinite(result).all():
            raise RuntimeError("MotionBERT produced invalid coordinates")
        return result
