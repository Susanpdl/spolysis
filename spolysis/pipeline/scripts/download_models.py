"""
Download RTMPose-x model weights by triggering MMPoseInferencer initialization.
Weights are cached to ~/.cache/mmpose/ automatically.
"""
from __future__ import annotations
import sys


def main() -> None:
    print("Downloading RTMPose-x weights via MMPose...")
    try:
        from mmpose.apis import MMPoseInferencer
    except ImportError:
        print("ERROR: mmpose is not installed.")
        print("Run: pip install mmpose")
        sys.exit(1)

    try:
        # This triggers the weight download
        _ = MMPoseInferencer(pose2d="rtmpose-x_8xb256-420e_coco-256x192", device="cpu")
        print("RTMPose-x weights downloaded successfully.")
        print("Weights cached at: ~/.cache/mmpose/")
    except Exception as e:
        print(f"ERROR: Failed to download weights: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
