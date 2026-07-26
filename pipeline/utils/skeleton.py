from __future__ import annotations
import numpy as np

# COCO 17-keypoint layout
COCO_KEYPOINTS = [
    "nose",           # 0
    "left_eye",       # 1
    "right_eye",      # 2
    "left_ear",       # 3
    "right_ear",      # 4
    "left_shoulder",  # 5
    "right_shoulder", # 6
    "left_elbow",     # 7
    "right_elbow",    # 8
    "left_wrist",     # 9
    "right_wrist",    # 10
    "left_hip",       # 11
    "right_hip",      # 12
    "left_knee",      # 13
    "right_knee",     # 14
    "left_ankle",     # 15
    "right_ankle",    # 16
]

# Index aliases
NOSE = 0
L_SHOULDER, R_SHOULDER = 5, 6
L_ELBOW, R_ELBOW = 7, 8
L_WRIST, R_WRIST = 9, 10
L_HIP, R_HIP = 11, 12
L_KNEE, R_KNEE = 13, 14
L_ANKLE, R_ANKLE = 15, 16

# COCO skeleton connectivity for visualization
SKELETON_EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]


def compute_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle at vertex b formed by rays b->a and b->c, in degrees."""
    ba = a - b
    bc = c - b
    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-9)
    return float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))))


def compute_joint_angles(kps: np.ndarray) -> dict[str, float]:
    """
    kps: (17, 2) array of (x, y) keypoint positions.
    Returns dict of named joint angles in degrees.
    """
    def pt(idx: int) -> np.ndarray:
        return kps[idx, :2]

    angles: dict[str, float] = {}

    # Elbow angles
    angles["left_elbow"] = compute_angle(pt(L_SHOULDER), pt(L_ELBOW), pt(L_WRIST))
    angles["right_elbow"] = compute_angle(pt(R_SHOULDER), pt(R_ELBOW), pt(R_WRIST))

    # Knee angles
    angles["left_knee"] = compute_angle(pt(L_HIP), pt(L_KNEE), pt(L_ANKLE))
    angles["right_knee"] = compute_angle(pt(R_HIP), pt(R_KNEE), pt(R_ANKLE))

    # Hip rotation: angle between shoulder vector and hip vector (in xy plane)
    shoulder_vec = pt(R_SHOULDER) - pt(L_SHOULDER)
    hip_vec = pt(R_HIP) - pt(L_HIP)
    cos_rot = np.dot(shoulder_vec, hip_vec) / (
        np.linalg.norm(shoulder_vec) * np.linalg.norm(hip_vec) + 1e-9
    )
    angles["shoulder_hip_rotation"] = float(np.degrees(np.arccos(np.clip(cos_rot, -1.0, 1.0))))

    # Shoulder abduction (arm raised from torso)
    angles["left_shoulder_abduction"] = compute_angle(pt(L_HIP), pt(L_SHOULDER), pt(L_ELBOW))
    angles["right_shoulder_abduction"] = compute_angle(pt(R_HIP), pt(R_SHOULDER), pt(R_ELBOW))

    return angles
