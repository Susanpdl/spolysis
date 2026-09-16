from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import structlog

if TYPE_CHECKING:
    import torch

log = structlog.get_logger(__name__)

# COCO-17 joint indices for root computation
_L_HIP = 11
_R_HIP = 12

# Window parameters match MB_ft_h36m training setup
_WINDOW = 243
_STRIDE = 81

# Heuristic: if the max inter-joint distance is under 5 the network returned
# metres rather than mm, so we scale up. Real human skeletons in mm span 400+.
_MM_THRESHOLD = 5.0


class MotionBERTLifter:
    """
    Wraps the DSTformer-based MotionBERT model for monocular 3D pose lifting.

    Performs sliding-window inference with linear blending in overlap regions,
    then returns root-relative 3D coordinates in millimetres.
    """

    _DEFAULT_CHECKPOINT = "/opt/weights/motionbert/MB_ft_h36m.bin"

    # MB_ft_h36m.yaml model config
    _MODEL_CFG: dict = dict(
        dim_in=3,
        dim_out=3,
        dim_feat=512,
        dim_rep=512,
        depth=5,
        num_heads=8,
        mlp_ratio=2,
        maxlen=_WINDOW,
    )

    def __init__(
        self,
        checkpoint: str | None = None,
        device: str = "cuda",
    ) -> None:
        self._checkpoint = checkpoint or self._DEFAULT_CHECKPOINT
        self._device = device
        self._model = self._load_model()

    def _load_model(self) -> "torch.nn.Module":
        try:
            sys.path.insert(0, "/opt/motionbert")
            from lib.model.DSTformer import DSTformer  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "MotionBERT is not installed. Clone the repo and place it at /opt/motionbert:\n"
                "  git clone https://github.com/Walter0807/MotionBERT /opt/motionbert\n"
                "Then download the checkpoint to /opt/weights/motionbert/MB_ft_h36m.bin\n"
                "following instructions in pipeline/README.md."
            ) from exc

        import torch

        model = DSTformer(**self._MODEL_CFG)

        try:
            raw = torch.load(self._checkpoint, map_location=self._device, weights_only=False)
            state_dict = raw.get("state_dict", raw) if isinstance(raw, dict) else raw
            model.load_state_dict(state_dict, strict=False)
            log.info(
                "motionbert_checkpoint_loaded",
                checkpoint=self._checkpoint,
                device=self._device,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load MotionBERT checkpoint '{self._checkpoint}': {exc}"
            ) from exc

        model.to(self._device)
        model.eval()
        return model

    def _normalize_input(self, window: np.ndarray) -> np.ndarray:
        """
        Zero-mean the xy positions relative to the hip root midpoint.

        MotionBERT is trained with the root at the origin, so a non-centred
        input biases depth predictions for the entire window.
        """
        # window: (W, 17, 3) - x, y in [-2,2] + confidence
        root = (window[:, _L_HIP, :2] + window[:, _R_HIP, :2]) / 2.0  # (W, 2)
        out = window.copy()
        out[:, :, 0] -= root[:, 0:1]
        out[:, :, 1] -= root[:, 1:2]
        return out

    def _run_window(self, window: np.ndarray) -> np.ndarray:
        """
        Run one (W, 17, 3) window through the model.
        Returns (W, 17, 3) root-relative 3D coordinates.
        """
        import torch

        window_norm = self._normalize_input(window)  # (W, 17, 3)
        x = torch.from_numpy(window_norm[None].astype(np.float32)).to(self._device)

        with torch.no_grad():
            out = self._model(x)  # (1, W, 17, 3)

        return out.squeeze(0).cpu().numpy()  # (W, 17, 3)

    def lift(self, keypoints_norm: np.ndarray) -> np.ndarray:
        """
        Lift a 2D keypoint sequence to 3D.

        Args:
            keypoints_norm: (T, 17, 3) - normalized x, y in [-2, 2] + confidence

        Returns:
            (T, 17, 3) - 3D positions in mm, root-relative
        """
        if keypoints_norm.ndim != 3 or keypoints_norm.shape[1:] != (17, 3):
            raise ValueError(
                f"Expected (T, 17, 3) input, got {keypoints_norm.shape}"
            )

        T = keypoints_norm.shape[0]
        log.info("motionbert_lift_start", frames=T)

        # Short sequences: reflect-pad to WINDOW, run, crop
        if T < _WINDOW:
            pad_len = _WINDOW - T
            padded = np.pad(keypoints_norm, ((0, pad_len), (0, 0), (0, 0)), mode="reflect")
            result_padded = self._run_window(padded)  # (_WINDOW, 17, 3)
            result_3d = result_padded[:T]
        else:
            result_3d = self._stitch_windows(keypoints_norm)

        # Scale metres -> mm if the model returned metres
        max_dist = float(np.linalg.norm(result_3d, axis=-1).max())
        if max_dist < _MM_THRESHOLD:
            result_3d = result_3d * 1000.0
            log.info("motionbert_scaled_m_to_mm", max_dist_before=round(max_dist, 4))

        log.info(
            "motionbert_lift_done",
            output_shape=result_3d.shape,
            root_mean_abs_mm=round(float(np.abs(result_3d).mean()), 2),
        )
        return result_3d.astype(np.float32)

    def _stitch_windows(self, seq: np.ndarray) -> np.ndarray:
        """
        Sliding-window inference with linear blending in overlap regions.

        Linear blending in the overlap (rather than taking the first or last
        window's output) smooths the seam between windows without introducing
        a hard discontinuity in the lifted trajectory.
        """
        T = seq.shape[0]
        accum = np.zeros((T, 17, 3), dtype=np.float64)
        weights = np.zeros(T, dtype=np.float64)

        starts = list(range(0, T - _WINDOW + 1, _STRIDE))
        # Always include the final window so the tail is covered
        if not starts or starts[-1] + _WINDOW < T:
            starts.append(max(0, T - _WINDOW))

        for start in starts:
            end = start + _WINDOW
            window_out = self._run_window(seq[start:end])  # (_WINDOW, 17, 3)

            # Ramp weight: 1 at centre, linearly tapers at edges of this window.
            # Avoids hard-edge seams where adjacent windows disagree.
            ramp = np.minimum(
                np.arange(1, _WINDOW + 1),
                np.arange(_WINDOW, 0, -1),
            ).astype(np.float64)  # (_WINDOW,)

            accum[start:end] += window_out * ramp[:, None, None]
            weights[start:end] += ramp

        weights = np.maximum(weights, 1e-9)
        return (accum / weights[:, None, None]).astype(np.float32)

    # Alias used by pipeline/stages/lift.py
    def infer(self, keypoints_norm: np.ndarray, confidence: np.ndarray) -> np.ndarray:
        """
        Thin adapter matching the interface expected by lift.py.

        confidence is folded back into keypoints_norm as the third channel
        since MotionBERT uses the joint score to down-weight uncertain joints.
        """
        T, J = keypoints_norm.shape[:2]
        combined = np.concatenate(
            [keypoints_norm, confidence.reshape(T, J, 1)], axis=-1
        )  # (T, 17, 3)
        return self.lift(combined)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run MotionBERT 3D pose lifting on normalized 2D keypoints"
    )
    parser.add_argument(
        "--keypoints",
        required=True,
        help="Path to .npy file of shape (T, 17, 3) - x, y in [-2,2] + confidence",
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help=f"Checkpoint path. Defaults to {MotionBERTLifter._DEFAULT_CHECKPOINT}",
    )
    parser.add_argument(
        "--device",
        default="cuda",
        help="Device: cuda or cpu (default: cuda)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output .npy file of shape (T, 17, 3) in mm root-relative",
    )
    args = parser.parse_args()

    kps = np.load(args.keypoints)
    lifter = MotionBERTLifter(checkpoint=args.checkpoint, device=args.device)
    out = lifter.lift(kps)
    np.save(args.output, out)
    print(f"Saved 3D keypoints shape {out.shape} to {args.output}")
