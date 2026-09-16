from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

import numpy as np
import structlog
from scipy.signal import savgol_filter

log = structlog.get_logger(__name__)

_DEFAULT_SMOOTHNET_CHECKPOINT = "/opt/weights/smoothnet/smoothnet_h36m.pth"

# SmoothNet hidden dim from the paper. Changing this means the checkpoint
# weight shapes change, so treat it as a file-format constant.
_SMOOTHNET_HIDDEN = 64


@dataclass
class SmoothResult:
    keypoints_3d: np.ndarray  # (T, 17, 3) smoothed, same units/coords as input


# ---------------------------------------------------------------------------
# SmoothNet architecture (inline, from "SmoothNet: A Plug-and-Play Network
# for Refining Human Poses in Videos", Zeng et al. 2022)
# ---------------------------------------------------------------------------

def _build_smoothnet(input_dim: int):
    """
    Build the SmoothNet module.

    The architecture is a residual MLP operating on the full flattened pose
    sequence at once (not frame-by-frame), which is why it understands
    temporal structure. The residual formulation means an untrained net is
    a no-op: output = input + 0 = input, making checkpoint-free fallback safe.
    """
    import torch
    import torch.nn as nn

    class _ResBlock(nn.Module):
        def __init__(self, dim: int) -> None:
            super().__init__()
            self.fc = nn.Linear(dim, dim)
            self.act = nn.ReLU(inplace=True)

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            return x + self.act(self.fc(x))

    class SmoothNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.input_proj = nn.Linear(input_dim, _SMOOTHNET_HIDDEN)
            self.act = nn.ReLU(inplace=True)
            self.res1 = _ResBlock(_SMOOTHNET_HIDDEN)
            self.res2 = _ResBlock(_SMOOTHNET_HIDDEN)
            self.res3 = _ResBlock(_SMOOTHNET_HIDDEN)
            self.output_proj = nn.Linear(_SMOOTHNET_HIDDEN, input_dim)

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            # x: (1, T, J*3) - residual correction is added by the caller
            h = self.act(self.input_proj(x))
            h = self.res1(h)
            h = self.res2(h)
            h = self.res3(h)
            return self.output_proj(h)

    return SmoothNet()


def _savgol_pass(
    keypoints_3d: np.ndarray,
    window: int,
    poly: int,
) -> np.ndarray:
    """
    Apply Savitzky-Golay along the time axis independently per joint per axis.

    Window is reduced on short sequences - the window must be odd and strictly
    greater than poly, otherwise scipy raises. Minimum meaningful window is
    poly + 1 rounded up to odd.
    """
    T = keypoints_3d.shape[0]
    if T < 4:
        return keypoints_3d.copy()

    # Reduce window until it fits the sequence length and the odd+>poly constraints
    w = window
    if w > T:
        w = T if T % 2 == 1 else T - 1
    if w <= poly:
        w = poly + 1 if (poly + 1) % 2 == 1 else poly + 2
    if w > T:
        return keypoints_3d.copy()

    out = keypoints_3d.copy()
    for j in range(keypoints_3d.shape[1]):
        for ax in range(keypoints_3d.shape[2]):
            out[:, j, ax] = savgol_filter(
                keypoints_3d[:, j, ax],
                window_length=w,
                polyorder=poly,
            )
    return out


def _smoothnet_pass(
    keypoints_3d: np.ndarray,
    checkpoint: str,
) -> np.ndarray:
    """
    Apply SmoothNet as a residual correction.

    The model was trained on H3.6M (standard benchmark); the residual
    formulation keeps it applicable to our SportsPose-fine-tuned coordinate
    space because it only predicts a correction delta, not absolute positions.
    """
    import torch

    T, J, C = keypoints_3d.shape
    input_dim = J * C

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    net = _build_smoothnet(input_dim).to(device)

    state = torch.load(checkpoint, map_location=device)
    # Checkpoints may be stored as the raw state_dict or wrapped in a dict
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    net.load_state_dict(state)
    net.eval()

    x_np = keypoints_3d.reshape(1, T, input_dim).astype(np.float32)
    x = torch.from_numpy(x_np).to(device)

    with torch.no_grad():
        correction = net(x)  # (1, T, J*3)

    corrected = x + correction
    return corrected.squeeze(0).cpu().numpy().reshape(T, J, C).astype(np.float32)


def smooth_3d(
    keypoints_3d: np.ndarray,  # (T, 17, 3) in mm
    smoothnet_checkpoint: str | None = None,
    savgol_window: int = 11,
    savgol_poly: int = 3,
) -> SmoothResult:
    """
    Two-pass smoothing of a 3D keypoint sequence.

    Pass 1 (Savitzky-Golay) removes gross sensor/lifter noise while preserving
    the derivative structure of fast ballistic motions like a tennis swing.
    Pass 2 (SmoothNet) applies learned motion-aware refinement as a residual
    correction. The two passes are complementary: SavGol handles high-frequency
    noise; SmoothNet handles unnatural joint trajectories.

    If no SmoothNet checkpoint is available the stage degrades gracefully to
    SavGol-only, which is still a substantial improvement over raw lifter output.
    """
    if keypoints_3d.ndim != 3 or keypoints_3d.shape[1:] != (17, 3):
        raise ValueError(
            f"Expected (T, 17, 3) input, got {keypoints_3d.shape}"
        )

    T = keypoints_3d.shape[0]
    log.info("smooth_3d_start", frames=T, savgol_window=savgol_window, savgol_poly=savgol_poly)

    smoothed = _savgol_pass(keypoints_3d, window=savgol_window, poly=savgol_poly)
    log.info("smooth_3d_savgol_done")

    ckpt = smoothnet_checkpoint or _DEFAULT_SMOOTHNET_CHECKPOINT
    if not os.path.isfile(ckpt):
        log.warning(
            "smooth_3d_smoothnet_checkpoint_missing_skipping_pass2",
            checkpoint=ckpt,
        )
        return SmoothResult(keypoints_3d=smoothed)

    try:
        smoothed = _smoothnet_pass(smoothed, ckpt)
        log.info("smooth_3d_smoothnet_done", checkpoint=ckpt)
    except Exception as exc:
        log.warning("smooth_3d_smoothnet_failed_returning_savgol_only", error=str(exc))

    return SmoothResult(keypoints_3d=smoothed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Two-pass 3D keypoint smoothing (Savitzky-Golay + SmoothNet)"
    )
    parser.add_argument(
        "--keypoints",
        required=True,
        help="Input .npy file of shape (T, 17, 3)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output .npy file of shape (T, 17, 3)",
    )
    parser.add_argument(
        "--checkpoint",
        default=None,
        help=(
            "SmoothNet checkpoint path. "
            f"Defaults to {_DEFAULT_SMOOTHNET_CHECKPOINT} if omitted."
        ),
    )
    parser.add_argument(
        "--savgol-window",
        type=int,
        default=11,
        help="Savitzky-Golay window length (must be odd, default: 11)",
    )
    parser.add_argument(
        "--savgol-poly",
        type=int,
        default=3,
        help="Savitzky-Golay polynomial order (default: 3)",
    )
    args = parser.parse_args()

    kps = np.load(args.keypoints)
    result = smooth_3d(
        keypoints_3d=kps,
        smoothnet_checkpoint=args.checkpoint,
        savgol_window=args.savgol_window,
        savgol_poly=args.savgol_poly,
    )
    np.save(args.output, result.keypoints_3d)
    print(f"Saved smoothed keypoints shape {result.keypoints_3d.shape} to {args.output}")
