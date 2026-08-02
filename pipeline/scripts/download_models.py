"""
Download pretrained model weights.

RTMPose-x: downloaded automatically by MMPoseInferencer on first use.
PoseC3D (NTU RGB+D): downloaded from OpenMMLab model zoo for fine-tuning.

Usage:
  python -m pipeline.scripts.download_models           # both
  python -m pipeline.scripts.download_models --rtmpose # RTMPose-x only
  python -m pipeline.scripts.download_models --posec3d # PoseC3D only
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.request
from pathlib import Path

# OpenMMLab model zoo URL for PoseC3D NTU-60 xsub keypoint checkpoint.
# SlowOnly-R50, 240e, pretrained on NTU RGB+D 60 cross-subject skeleton keypoints.
POSEC3D_NTU60_URL = (
    "https://download.openmmlab.com/mmaction/skeleton/posec3d/"
    "slowonly_r50_u48_240e_ntu60_xsub_keypoint/"
    "slowonly_r50_u48_240e_ntu60_xsub_keypoint-f3adabf1.pth"
)
POSEC3D_NTU60_FILENAME = "posec3d_ntu60_xsub.pth"
WEIGHTS_DIR = Path(__file__).parent.parent / "weights"


def download_rtmpose() -> None:
    print("Downloading RTMPose-x weights via MMPose...")
    try:
        from mmpose.apis import MMPoseInferencer
    except ImportError:
        print("ERROR: mmpose is not installed. Run: pip install mmpose")
        sys.exit(1)

    try:
        _ = MMPoseInferencer(pose2d="rtmpose-x_8xb256-420e_coco-256x192", device="cpu")
        print("RTMPose-x weights downloaded. Cached at: ~/.cache/mmpose/")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


def download_posec3d() -> None:
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = WEIGHTS_DIR / POSEC3D_NTU60_FILENAME

    if out_path.exists():
        print(f"PoseC3D weights already present: {out_path}")
        return

    print(f"Downloading PoseC3D NTU-60 xsub pretrained weights...")
    print(f"  URL: {POSEC3D_NTU60_URL}")
    print(f"  Destination: {out_path}")

    def _progress(block_count: int, block_size: int, total_size: int) -> None:
        downloaded = block_count * block_size
        if total_size > 0:
            pct = min(100, downloaded * 100 // total_size)
            print(f"\r  {pct:3d}%  ({downloaded // 1_048_576} / {total_size // 1_048_576} MB)", end="", flush=True)

    try:
        urllib.request.urlretrieve(POSEC3D_NTU60_URL, str(out_path), reporthook=_progress)
        print(f"\nPoseC3D weights downloaded: {out_path}")
    except Exception as e:
        if out_path.exists():
            out_path.unlink()
        print(f"\nERROR: Failed to download PoseC3D weights: {e}")
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Download pretrained model weights")
    ap.add_argument("--rtmpose", action="store_true", help="Download RTMPose-x only")
    ap.add_argument("--posec3d", action="store_true", help="Download PoseC3D only")
    args = ap.parse_args()

    if not args.rtmpose and not args.posec3d:
        download_rtmpose()
        download_posec3d()
    else:
        if args.rtmpose:
            download_rtmpose()
        if args.posec3d:
            download_posec3d()


if __name__ == "__main__":
    main()
