from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
import structlog
from scipy.signal import savgol_filter

log = structlog.get_logger(__name__)

# COCO-17 wrist index for the dominant (racket) hand
_R_WRIST = 10

# Savitzky-Golay params for speed smoothing.
# Window 9 is chosen to preserve the sharp swing peak while removing
# high-frequency jitter from lifter output.
_SAVGOL_WINDOW = 9
_SAVGOL_POLY = 3

# Minimum number of frames on each side of contact to search for backswing load
_MIN_BACKSWING_SEARCH = 5

# For serve upward-peak detection: minimum fractional upward displacement (in m
# relative to skeleton height) to consider a separate toss/trophy phase
_SERVE_UPWARD_THRESHOLD = 0.15  # ~15 cm for a normalised skeleton ~1 m tall


@dataclass
class StrokePhases:
    preparation: tuple[int, int]      # (start, end) frame indices - inclusive
    backswing: tuple[int, int]
    contact: int                       # single frame
    follow_through: tuple[int, int]
    total_frames: int


def _savgol_safe(signal: np.ndarray, window: int = _SAVGOL_WINDOW, poly: int = _SAVGOL_POLY) -> np.ndarray:
    """Apply SavGol with automatic window reduction for short sequences."""
    T = len(signal)
    if T < 4:
        return signal.copy()
    w = window
    if w > T:
        w = T if T % 2 == 1 else T - 1
    if w <= poly:
        w = poly + 1 if (poly + 1) % 2 == 1 else poly + 2
    if w > T:
        return signal.copy()
    return savgol_filter(signal, window_length=w, polyorder=poly)


def _find_local_minima(signal: np.ndarray) -> np.ndarray:
    """Return indices where signal is a local minimum (both neighbours are larger)."""
    if len(signal) < 3:
        return np.array([], dtype=int)
    prev = signal[:-2]
    curr = signal[1:-1]
    nxt = signal[2:]
    minima = np.where((curr <= prev) & (curr <= nxt))[0] + 1
    return minima


def _wrist_speed(keypoints_3d: np.ndarray) -> np.ndarray:
    """
    Compute smoothed right-wrist 3D speed from a (T, 17, 3) sequence.
    Returns (T-1,) speeds in the same unit as keypoints_3d (mm/frame).
    """
    wrist_pos = keypoints_3d[:, _R_WRIST, :]          # (T, 3)
    diff = np.diff(wrist_pos, axis=0)                  # (T-1, 3)
    speed = np.linalg.norm(diff, axis=1)               # (T-1,)
    return _savgol_safe(speed)


def detect_phases(
    keypoints_3d: np.ndarray,
    stroke_type: str,
) -> StrokePhases:
    """
    Detect preparation, backswing, contact, and follow-through frames from
    a 3D keypoint sequence.

    Uses wrist velocity to anchor the contact frame, then searches backwards
    for the backswing deceleration trough.

    Args:
        keypoints_3d: (T, 17, 3) mm root-relative
        stroke_type:  "forehand" | "backhand" | "serve" | "volley"

    Returns:
        StrokePhases with all indices in the original frame numbering.
    """
    if keypoints_3d.ndim != 3 or keypoints_3d.shape[1:] != (17, 3):
        raise ValueError(
            f"Expected (T, 17, 3) input, got {keypoints_3d.shape}"
        )
    if stroke_type not in ("forehand", "backhand", "serve", "volley"):
        raise ValueError(
            f"Unknown stroke_type '{stroke_type}'; must be one of "
            "forehand, backhand, serve, volley"
        )

    T = keypoints_3d.shape[0]
    speed = _wrist_speed(keypoints_3d)  # (T-1,)

    # --- Contact frame ---
    contact_frame = int(np.argmax(speed))

    if stroke_type == "serve":
        # Check for a distinct upward-velocity peak preceding the main swing peak.
        # The trophy position involves a large upward wrist movement that can
        # register as a speed peak before the actual contact peak.
        wrist_y = keypoints_3d[:, _R_WRIST, 1]  # vertical axis
        skel_height = float(np.abs(keypoints_3d).max())  # rough scale
        upward_disp = wrist_y - wrist_y[0]
        if skel_height > 1e-6:
            upward_disp_norm = upward_disp / skel_height
        else:
            upward_disp_norm = upward_disp

        # Find speed peaks before the main peak
        pre_speed = speed[: contact_frame]
        if len(pre_speed) > 2:
            pre_peaks = _find_local_minima(-pre_speed)  # invert to find maxima
            if len(pre_peaks) > 0:
                # Check whether the last pre-peak coincides with upward displacement
                candidate = int(pre_peaks[-1])
                if (
                    candidate < contact_frame
                    and float(upward_disp_norm[candidate]) > _SERVE_UPWARD_THRESHOLD
                ):
                    # The upward toss phase is the real contact-equivalent anchor
                    contact_frame = candidate
                    log.info(
                        "serve_trophy_peak_used_as_contact",
                        contact_frame=contact_frame,
                    )

    # --- Backswing start ---
    # Search the region before contact for the most recent speed local minimum,
    # which is where the forward swing begins (the "load point").
    search_region = speed[:contact_frame]
    backswing_start: int

    if len(search_region) >= _MIN_BACKSWING_SEARCH:
        minima = _find_local_minima(search_region)
        if len(minima) > 0:
            # Use the rightmost (most recent) minimum as the transition point
            backswing_start = int(minima[-1])
        else:
            # No clear minimum: use a heuristic offset from contact
            backswing_start = max(0, contact_frame - min(45, contact_frame // 2))
    else:
        backswing_start = 0

    backswing_start = max(0, backswing_start)

    # --- Phase windows ---
    prep_start = 0
    prep_end = max(0, backswing_start - 1)

    backswing_end = max(backswing_start, contact_frame - 1)

    follow_start = min(T - 1, contact_frame + 1)
    follow_end = T - 1

    phases = StrokePhases(
        preparation=(prep_start, prep_end),
        backswing=(backswing_start, backswing_end),
        contact=contact_frame,
        follow_through=(follow_start, follow_end),
        total_frames=T,
    )

    log.info(
        "phases_detected",
        stroke_type=stroke_type,
        total_frames=T,
        preparation=phases.preparation,
        backswing=phases.backswing,
        contact=phases.contact,
        follow_through=phases.follow_through,
    )

    return phases


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Detect stroke phases from a 3D keypoint sequence"
    )
    parser.add_argument(
        "--keypoints",
        required=True,
        help="Input .npy file of shape (T, 17, 3) in mm root-relative",
    )
    parser.add_argument(
        "--stroke",
        required=True,
        choices=["forehand", "backhand", "serve", "volley"],
        help="Stroke type",
    )
    args = parser.parse_args()

    kps = np.load(args.keypoints)
    phases = detect_phases(kps, stroke_type=args.stroke)

    print(f"Total frames:   {phases.total_frames}")
    print(f"Preparation:    frames {phases.preparation[0]}-{phases.preparation[1]}")
    print(f"Backswing:      frames {phases.backswing[0]}-{phases.backswing[1]}")
    print(f"Contact:        frame  {phases.contact}")
    print(f"Follow-through: frames {phases.follow_through[0]}-{phases.follow_through[1]}")
