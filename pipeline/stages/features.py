from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
import structlog
from pipeline.utils.skeleton import compute_joint_angles
from pipeline.utils.smoothing import normalize_keypoints, compute_velocities, savgol_smooth

log = structlog.get_logger(__name__)


@dataclass
class FeatureSet:
    keypoints_norm: np.ndarray        # (T, 17, 3) normalized, smoothed
    velocities: np.ndarray            # (T, 17) velocity magnitudes
    wrist_velocity_smooth: np.ndarray # (T,) smoothed right-wrist x-velocity
    joint_angles_per_frame: list[dict[str, float]] = field(default_factory=list)
    frame_count: int = 0


def extract_features(keypoints: np.ndarray) -> FeatureSet:
    """
    Extract biomechanical features from raw (T, 17, 3) keypoints.
    """
    T = keypoints.shape[0]
    log.info("feature_extraction_start", frames=T)

    # Normalize to bounding box
    kps_norm = normalize_keypoints(keypoints)

    # Velocities
    velocities = compute_velocities(kps_norm[:, :, :2])

    # Right wrist (index 10) x-velocity, smoothed
    r_wrist_x = kps_norm[:, 10, 0]  # (T,)
    r_wrist_x_vel = np.gradient(r_wrist_x)
    r_wrist_x_vel_smooth = savgol_smooth(r_wrist_x_vel, window=11, poly=3)

    # Joint angles per frame
    angles_list: list[dict[str, float]] = []
    for t in range(T):
        angles = compute_joint_angles(kps_norm[t, :, :2])
        angles_list.append(angles)

    log.info("feature_extraction_done", frames=T)
    return FeatureSet(
        keypoints_norm=kps_norm,
        velocities=velocities,
        wrist_velocity_smooth=r_wrist_x_vel_smooth,
        joint_angles_per_frame=angles_list,
        frame_count=T,
    )


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--keypoints", required=True, help="Path to keypoints .npy file")
    args = parser.parse_args()
    kps = np.load(args.keypoints)
    features = extract_features(kps)
    print(f"Features extracted: {features.frame_count} frames, wrist vel shape {features.wrist_velocity_smooth.shape}")
