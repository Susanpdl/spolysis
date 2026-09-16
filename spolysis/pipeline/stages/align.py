from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import structlog

if TYPE_CHECKING:
    from pipeline.stages.phases import StrokePhases

log = structlog.get_logger(__name__)

_R_WRIST = 10
_L_HIP = 11
_R_HIP = 12

# Sakoe-Chiba band: fraction of sequence length to use as DTW radius
_DTW_BAND_FRACTION = 1 / 3
_DTW_BAND_MAX = 30


@dataclass
class AlignmentResult:
    user_seq: np.ndarray    # (T_aligned, 17, 3) user sequence, unchanged
    ref_seq: np.ndarray     # (T_aligned, 17, 3) reference warped to user timing
    dtw_cost: float
    user_contact: int       # contact frame in the aligned sequence
    ref_contact: int        # contact frame in the original reference


def _wrist_speed(keypoints_3d: np.ndarray) -> np.ndarray:
    """Compute right-wrist 3D speed, returns (T-1,) array."""
    from scipy.signal import savgol_filter

    wrist_pos = keypoints_3d[:, _R_WRIST, :]   # (T, 3)
    diff = np.diff(wrist_pos, axis=0)           # (T-1, 3)
    speed = np.linalg.norm(diff, axis=1)        # (T-1,)

    T = len(speed)
    if T < 4:
        return speed

    w = 9
    if w > T:
        w = T if T % 2 == 1 else T - 1
    if w <= 3:
        return speed

    return savgol_filter(speed, window_length=w, polyorder=3)


def _contact_frame(keypoints_3d: np.ndarray) -> int:
    """Find the contact frame as the wrist speed peak."""
    speed = _wrist_speed(keypoints_3d)
    if len(speed) == 0:
        return 0
    return int(np.argmax(speed))


def _select_reference(
    ref_npy_paths: list[str],
    user_contact_ratio: float,
) -> tuple[np.ndarray, int]:
    """
    From a list of candidate reference files, pick the one whose contact-frame
    timing ratio is closest to the user's.

    Matching on contact-ratio rather than raw frame count makes selection
    robust to clips recorded at different fps or with different amounts of
    pre/post-swing footage.
    """
    best_seq: np.ndarray | None = None
    best_contact: int = 0
    best_dist = float("inf")

    for path in ref_npy_paths:
        try:
            seq = np.load(path)
        except Exception as exc:
            log.warning("reference_load_failed", path=path, error=str(exc))
            continue

        if seq.ndim != 3 or seq.shape[1:] != (17, 3):
            log.warning("reference_wrong_shape", path=path, shape=seq.shape)
            continue

        contact = _contact_frame(seq)
        ratio = contact / max(seq.shape[0] - 1, 1)
        dist = abs(ratio - user_contact_ratio)

        if dist < best_dist:
            best_dist = dist
            best_seq = seq
            best_contact = contact

    if best_seq is None:
        raise FileNotFoundError(
            f"No valid reference sequences found among {ref_npy_paths}"
        )

    return best_seq, best_contact


def _dtw_warp_ref_to_user(
    user_side: np.ndarray,  # (T_u, 17, 3)
    ref_side: np.ndarray,   # (T_r, 17, 3)
) -> np.ndarray:
    """
    DTW-align ref_side to user_side and return a warped reference of length T_u.

    Steps:
      1. Compute DTW warping path with a Sakoe-Chiba band.
      2. Build a per-user-frame index into the reference via the path.
      3. Linearly interpolate the reference at fractional indices.

    The Sakoe-Chiba band prevents unrealistic time-warpings (e.g. holding a
    single frame for half the sequence) while still handling natural swing
    speed variation between user and pro.
    """
    from dtaidistance import dtw as dtaidtw

    T_u = user_side.shape[0]
    T_r = ref_side.shape[0]

    if T_u == 0 or T_r == 0:
        # Degenerate edge case: return zero-padded reference
        return np.zeros((T_u, 17, 3), dtype=np.float32)

    radius = min(_DTW_BAND_MAX, max(1, int(min(T_u, T_r) * _DTW_BAND_FRACTION)))

    user_flat = user_side.reshape(T_u, -1).astype(np.double)  # (T_u, 51)
    ref_flat = ref_side.reshape(T_r, -1).astype(np.double)    # (T_r, 51)

    # dtaidistance expects 1D series; we compute the Euclidean norm per frame
    # as a 1D distance proxy for the path computation, then apply the path to
    # the full 3D sequence for interpolation.
    user_1d = np.linalg.norm(user_flat, axis=1)
    ref_1d = np.linalg.norm(ref_flat, axis=1)

    try:
        path = dtaidtw.warping_path(user_1d, ref_1d, window=radius)
    except Exception as exc:
        log.warning("dtw_failed_using_linear_resampling", error=str(exc))
        # Fall back to linear resampling if dtaidistance is unavailable
        interp_indices = np.linspace(0, T_r - 1, T_u)
        return _interp_ref(ref_side, interp_indices)

    # Build a mapping from each user frame to one or more reference frames.
    # When multiple reference frames map to the same user frame, average them.
    ref_mapped = np.zeros((T_u, 17, 3), dtype=np.float64)
    ref_count = np.zeros(T_u, dtype=np.int32)

    for u_idx, r_idx in path:
        if 0 <= u_idx < T_u and 0 <= r_idx < T_r:
            ref_mapped[u_idx] += ref_side[r_idx]
            ref_count[u_idx] += 1

    # Frames with no mapping (can happen at edges) use nearest neighbour
    for u_idx in range(T_u):
        if ref_count[u_idx] == 0:
            log.debug("dtw_unmapped_frame_using_nearest", u_idx=u_idx)
            # Find nearest mapped frame
            mapped = np.where(ref_count > 0)[0]
            if len(mapped) > 0:
                nearest = mapped[np.argmin(np.abs(mapped - u_idx))]
                ref_mapped[u_idx] = ref_mapped[nearest]
                ref_count[u_idx] = ref_count[nearest]
            else:
                ref_count[u_idx] = 1  # avoid divide-by-zero; stays zero

    counts = np.maximum(ref_count, 1)
    return (ref_mapped / counts[:, None, None]).astype(np.float32)


def _interp_ref(ref: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """Linearly interpolate ref (T_r, 17, 3) at fractional indices."""
    T_r = ref.shape[0]
    out = np.zeros((len(indices), 17, 3), dtype=np.float32)
    for i, idx in enumerate(indices):
        lo = int(np.floor(idx))
        hi = min(lo + 1, T_r - 1)
        alpha = idx - lo
        out[i] = (1 - alpha) * ref[lo] + alpha * ref[hi]
    return out


def align_to_reference(
    user_3d: np.ndarray,
    user_phases: "StrokePhases",
    stroke_type: str,
    reference_dir: str = "data/reference_motion",
) -> AlignmentResult:
    """
    Align a user 3D stroke sequence to the best-matching reference via
    keyframe-anchored DTW.

    The contact frame is used as the anchor: DTW runs independently on the
    pre-contact and post-contact sides, allowing the model to accommodate
    swing-speed differences on each side without warping through the impact
    point itself.

    Args:
        user_3d:       (T_user, 17, 3) normalized 3D keypoints
        user_phases:   phase information for user_3d (contact frame used as anchor)
        stroke_type:   "forehand" | "backhand" | "serve" | "volley"
        reference_dir: directory containing .npy reference sequences

    Returns:
        AlignmentResult with user_seq unchanged and ref_seq warped to user timing.
    """
    if user_3d.ndim != 3 or user_3d.shape[1:] != (17, 3):
        raise ValueError(f"Expected (T, 17, 3) user_3d, got {user_3d.shape}")

    T_user = user_3d.shape[0]
    user_contact = user_phases.contact

    log.info(
        "align_start",
        stroke_type=stroke_type,
        user_frames=T_user,
        user_contact=user_contact,
        reference_dir=reference_dir,
    )

    # Resolve reference files matching this stroke type
    if not os.path.isdir(reference_dir):
        raise FileNotFoundError(
            f"Reference directory not found: {reference_dir}"
        )

    ref_paths = [
        os.path.join(reference_dir, f)
        for f in os.listdir(reference_dir)
        if f.endswith(".npy") and stroke_type.lower() in f.lower()
    ]

    if not ref_paths:
        raise FileNotFoundError(
            f"No .npy reference files found in '{reference_dir}' matching stroke_type='{stroke_type}'"
        )

    user_contact_ratio = user_contact / max(T_user - 1, 1)
    ref_seq, ref_contact = _select_reference(ref_paths, user_contact_ratio)

    T_ref = ref_seq.shape[0]
    log.info(
        "reference_selected",
        ref_frames=T_ref,
        ref_contact=ref_contact,
        num_candidates=len(ref_paths),
    )

    # Split at contact frames
    user_pre = user_3d[: user_contact]           # [0, contact)
    user_post = user_3d[user_contact:]            # [contact, T_user]
    ref_pre = ref_seq[: ref_contact]
    ref_post = ref_seq[ref_contact:]

    # DTW-warp each side of the reference to match user timing
    warped_pre = _dtw_warp_ref_to_user(user_pre, ref_pre)    # (len(user_pre), 17, 3)
    warped_post = _dtw_warp_ref_to_user(user_post, ref_post)  # (len(user_post), 17, 3)

    ref_warped = np.concatenate([warped_pre, warped_post], axis=0)  # (T_user, 17, 3)

    # DTW cost: mean per-frame Euclidean distance after warping (diagnostic only)
    diff = user_3d - ref_warped
    dtw_cost = float(np.mean(np.linalg.norm(diff.reshape(T_user, -1), axis=1)))

    log.info(
        "align_done",
        dtw_cost_mm=round(dtw_cost, 2),
        user_contact=user_contact,
        ref_contact=ref_contact,
    )

    return AlignmentResult(
        user_seq=user_3d,
        ref_seq=ref_warped,
        dtw_cost=dtw_cost,
        user_contact=user_contact,
        ref_contact=ref_contact,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Align a user 3D stroke sequence to a reference via keyframe-anchored DTW"
    )
    parser.add_argument(
        "--user-keypoints",
        required=True,
        help="Path to .npy file of shape (T, 17, 3) - user 3D keypoints (mm, root-relative)",
    )
    parser.add_argument(
        "--stroke",
        required=True,
        choices=["forehand", "backhand", "serve", "volley"],
        help="Stroke type",
    )
    parser.add_argument(
        "--contact-frame",
        required=True,
        type=int,
        help="Contact frame index in the user sequence",
    )
    parser.add_argument(
        "--reference-dir",
        default="data/reference_motion",
        help="Directory containing .npy reference motion sequences (default: data/reference_motion)",
    )
    parser.add_argument(
        "--output-ref",
        default=None,
        help="Optional: save warped reference to this .npy path",
    )
    args = parser.parse_args()

    user_kps = np.load(args.user_keypoints)

    # Build a minimal StrokePhases so align_to_reference has the contact anchor
    from pipeline.stages.phases import StrokePhases

    T = user_kps.shape[0]
    phases = StrokePhases(
        preparation=(0, max(0, args.contact_frame - 1)),
        backswing=(0, max(0, args.contact_frame - 1)),
        contact=args.contact_frame,
        follow_through=(min(T - 1, args.contact_frame + 1), T - 1),
        total_frames=T,
    )

    result = align_to_reference(
        user_3d=user_kps,
        user_phases=phases,
        stroke_type=args.stroke,
        reference_dir=args.reference_dir,
    )

    print(f"DTW cost (mean per-frame mm): {result.dtw_cost:.2f}")
    print(f"User contact frame:           {result.user_contact}")
    print(f"Reference contact frame:      {result.ref_contact}")
    print(f"Output shape:                 {result.ref_seq.shape}")

    if args.output_ref:
        np.save(args.output_ref, result.ref_seq)
        print(f"Saved warped reference to {args.output_ref}")
