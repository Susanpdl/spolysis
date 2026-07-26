from __future__ import annotations
import numpy as np
from scipy.signal import savgol_filter


def savgol_smooth(signal: np.ndarray, window: int = 11, poly: int = 3) -> np.ndarray:
    """Apply Savitzky-Golay filter. Handles short signals gracefully."""
    if len(signal) < window:
        return signal
    return savgol_filter(signal, window_length=window, polyorder=poly)


def normalize_keypoints(kps: np.ndarray) -> np.ndarray:
    """
    Normalize (T, 17, 3) keypoints to bounding box [0,1] per frame.
    Preserves confidence in channel 2.
    """
    out = kps.copy()
    for t in range(kps.shape[0]):
        xy = kps[t, :, :2]
        conf = kps[t, :, 2]
        visible = conf > 0.3
        if visible.sum() < 2:
            continue
        vis_xy = xy[visible]
        min_xy = vis_xy.min(axis=0)
        max_xy = vis_xy.max(axis=0)
        range_xy = max_xy - min_xy
        range_xy[range_xy < 1e-9] = 1.0
        out[t, :, :2] = (xy - min_xy) / range_xy
        out[t, :, 2] = conf
    return out


def compute_velocities(kps: np.ndarray) -> np.ndarray:
    """
    Compute per-frame per-keypoint velocity magnitude.
    kps: (T, 17, 2) xy positions.
    Returns (T, 17) velocity magnitudes. Frame 0 has velocity 0.
    """
    vel = np.zeros((kps.shape[0], kps.shape[1]), dtype=np.float32)
    if kps.shape[0] > 1:
        diff = np.diff(kps[:, :, :2], axis=0)
        vel[1:] = np.linalg.norm(diff, axis=2)
    return vel
