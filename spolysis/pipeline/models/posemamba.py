from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import numpy as np
import structlog

if TYPE_CHECKING:
    import torch

log = structlog.get_logger(__name__)

# Shared with MotionBERT to keep evaluation on equal footing
_WINDOW = 243
_STRIDE = 81
_L_HIP = 11
_R_HIP = 12
_MM_THRESHOLD = 5.0


def _build_bilstm_fallback() -> "torch.nn.Module":
    """
    Bidirectional LSTM lifter used when PoseMamba is not installed.

    This is not a replacement for PoseMamba - it is a structural placeholder
    that implements the same interface so the rest of the pipeline stays intact
    during development before PoseMamba weights are available. Output quality
    will be poor with untrained weights.
    """
    import torch.nn as nn

    class _BiLSTMLifter(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.lstm = nn.LSTM(
                input_size=17 * 3,
                hidden_size=512,
                num_layers=3,
                bidirectional=True,
                batch_first=True,
            )
            self.proj = nn.Linear(1024, 17 * 3)

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            # x: (B, T, 17*3) -> (B, T, 17*3)
            h, _ = self.lstm(x)
            return self.proj(h)

    return _BiLSTMLifter()


class PoseMambaLifter:
    """
    Wraps the PoseMamba model for monocular 3D pose lifting.

    Falls back to a BiLSTM architecture if PoseMamba is not installed at
    /opt/posemamba. The fallback provides the same tensor interface and can
    be swapped for real PoseMamba weights without any code changes once the
    installation is available.
    """

    _DEFAULT_CHECKPOINT = "/opt/weights/posemamba/posemamba_h36m.pth"

    def __init__(
        self,
        checkpoint: str | None = None,
        device: str = "cuda",
    ) -> None:
        self._checkpoint = checkpoint or self._DEFAULT_CHECKPOINT
        self._device = device
        self._model = self._load_model()

    def _load_model(self) -> "torch.nn.Module":
        import torch

        model = None
        using_fallback = False

        try:
            sys.path.insert(0, "/opt/posemamba")
            from model.PoseMamba import PoseMamba  # type: ignore[import]
            model = PoseMamba()
            log.info("posemamba_model_imported", path="/opt/posemamba")
        except ImportError:
            log.warning(
                "posemamba_not_found_using_bilstm_fallback",
                install_path="/opt/posemamba",
                note="Clone PoseMamba repo to /opt/posemamba to enable real model",
            )
            model = _build_bilstm_fallback()
            using_fallback = True

        try:
            raw = torch.load(self._checkpoint, map_location=self._device, weights_only=False)
            state_dict = raw.get("state_dict", raw) if isinstance(raw, dict) else raw
            model.load_state_dict(state_dict, strict=False)
            log.info(
                "posemamba_checkpoint_loaded",
                checkpoint=self._checkpoint,
                device=self._device,
                fallback=using_fallback,
            )
        except Exception as exc:
            log.warning(
                "posemamba_checkpoint_load_failed_using_untrained_weights",
                checkpoint=self._checkpoint,
                error=str(exc),
            )

        model.to(self._device)
        model.eval()
        return model

    def _normalize_input(self, window: np.ndarray) -> np.ndarray:
        """Centre the window at the hip root, mirroring MotionBERT's convention."""
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
        W = window_norm.shape[0]

        x_flat = window_norm.reshape(W, -1).astype(np.float32)  # (W, 51)
        x = torch.from_numpy(x_flat[None]).to(self._device)    # (1, W, 51)

        with torch.no_grad():
            out = self._model(x)  # (1, W, 51) expected from both architectures

        out_np = out.squeeze(0).cpu().numpy()  # (W, 51)
        return out_np.reshape(W, 17, 3)

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
        log.info("posemamba_lift_start", frames=T)

        if T < _WINDOW:
            pad_len = _WINDOW - T
            padded = np.pad(keypoints_norm, ((0, pad_len), (0, 0), (0, 0)), mode="reflect")
            result_padded = self._run_window(padded)
            result_3d = result_padded[:T]
        else:
            result_3d = self._stitch_windows(keypoints_norm)

        max_dist = float(np.linalg.norm(result_3d, axis=-1).max())
        if max_dist < _MM_THRESHOLD:
            result_3d = result_3d * 1000.0
            log.info("posemamba_scaled_m_to_mm", max_dist_before=round(max_dist, 4))

        log.info(
            "posemamba_lift_done",
            output_shape=result_3d.shape,
            root_mean_abs_mm=round(float(np.abs(result_3d).mean()), 2),
        )
        return result_3d.astype(np.float32)

    def _stitch_windows(self, seq: np.ndarray) -> np.ndarray:
        """Sliding-window inference with linear blending - same logic as MotionBERT."""
        T = seq.shape[0]
        accum = np.zeros((T, 17, 3), dtype=np.float64)
        weights = np.zeros(T, dtype=np.float64)

        starts = list(range(0, T - _WINDOW + 1, _STRIDE))
        if not starts or starts[-1] + _WINDOW < T:
            starts.append(max(0, T - _WINDOW))

        for start in starts:
            end = start + _WINDOW
            window_out = self._run_window(seq[start:end])

            ramp = np.minimum(
                np.arange(1, _WINDOW + 1),
                np.arange(_WINDOW, 0, -1),
            ).astype(np.float64)

            accum[start:end] += window_out * ramp[:, None, None]
            weights[start:end] += ramp

        weights = np.maximum(weights, 1e-9)
        return (accum / weights[:, None, None]).astype(np.float32)

    # Alias used by pipeline/stages/lift.py
    def infer(self, keypoints_norm: np.ndarray, confidence: np.ndarray) -> np.ndarray:
        """Thin adapter matching the interface expected by lift.py."""
        T, J = keypoints_norm.shape[:2]
        combined = np.concatenate(
            [keypoints_norm, confidence.reshape(T, J, 1)], axis=-1
        )
        return self.lift(combined)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run PoseMamba 3D pose lifting on normalized 2D keypoints"
    )
    parser.add_argument(
        "--keypoints",
        required=True,
        help="Path to .npy file of shape (T, 17, 3) - x, y in [-2,2] + confidence",
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help=f"Checkpoint path. Defaults to {PoseMambaLifter._DEFAULT_CHECKPOINT}",
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
    lifter = PoseMambaLifter(checkpoint=args.checkpoint, device=args.device)
    out = lifter.lift(kps)
    np.save(args.output, out)
    print(f"Saved 3D keypoints shape {out.shape} to {args.output}")
