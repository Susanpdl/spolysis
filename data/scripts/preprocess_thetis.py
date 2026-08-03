#!/usr/bin/env python3
"""
Extract RTMPose-x keypoints from THETIS RGB video clips.

THETIS actual structure (VIDEO_RGB/ subdirectory):
  VIDEO_RGB/
    forehand_flat/
      p1_foreflat_s1.avi
      p1_foreflat_s2.avi
      ...
      p55_foreflat_s3.avi
    backhand/
      p1_back_s1.avi
      ...
    backhand2hands/   (not backhand_2hands)
    forehand_openstands/  (not forehand_open_stance)
    ...

Players p1-p31 are beginners (fault label source).
Players p32-p55 are experts (reference motion).
Player number is embedded in the filename: p{N}_{abbrev}_s{N}.avi

Output per clip: an NPY file with shape (T, 17, 3) - x, y, confidence in pixel coords.
Stored in data/thetis/keypoints/<stroke_folder>/<clip_stem>.npy
(mirrors THETIS input structure, player number extractable from filename)

Usage:
  python data/scripts/preprocess_thetis.py \\
    --input  data/raw/THETIS/VIDEO_RGB/ \\
    --output data/thetis/keypoints/ \\

Requires mmpose and a GPU (or use --device cpu for slow CPU fallback).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

# Actual THETIS VIDEO_RGB folder names -> our canonical 4-class label
THETIS_STROKE_MAP: dict[str, str] = {
    "backhand":             "backhand",
    "backhand2hands":       "backhand",   # actual folder name (not backhand_2hands)
    "backhand_slice":       "backhand",
    "backhand_volley":      "volley",
    "forehand_flat":        "forehand",
    "forehand_openstands":  "forehand",   # actual folder name (not forehand_open_stance)
    "forehand_slice":       "forehand",
    "forehand_volley":      "volley",
    "flat_service":         "serve",
    "kick_service":         "serve",
    "slice_service":        "serve",
    "smash":                "serve",
}

EXPERT_THRESHOLD = 32  # players p32-p55 are experts

_PLAYER_RE = re.compile(r"^p(\d+)_")


def _extract_frames(video_path: str, output_dir: str, fps: float = 30.0) -> list[str]:
    """Extract frames from video using ffmpeg. Returns sorted frame paths."""
    pattern = os.path.join(output_dir, "frame_%06d.jpg")
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps={fps}",
        "-q:v", "2", "-y", pattern,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return sorted(str(p) for p in Path(output_dir).glob("*.jpg"))


def _run_rtmpose(frame_paths: list[str], device: str = "cuda") -> np.ndarray:
    """Run RTMPose-x on a list of frames. Returns (T, 17, 3)."""
    from mmpose.apis import MMPoseInferencer

    inferencer = MMPoseInferencer(
        pose2d="rtmpose-x_8xb256-420e_coco-256x192",
        device=device,
    )

    all_kps = []
    for frame_path in frame_paths:
        results = list(inferencer(frame_path, show=False, return_vis=False))
        if not results or not results[0].get("predictions"):
            all_kps.append(np.zeros((17, 3), dtype=np.float32))
            continue

        preds = results[0]["predictions"][0]
        if isinstance(preds, list):
            preds = sorted(preds, key=lambda p: p.get("bbox_score", 0), reverse=True)[0]

        kps = np.array(preds["keypoints"], dtype=np.float32)     # (17, 2)
        scores = np.array(preds["keypoint_scores"], dtype=np.float32)  # (17,)
        all_kps.append(np.concatenate([kps, scores[:, None]], axis=1))

    return np.stack(all_kps, axis=0)  # (T, 17, 3)


def process_clip(
    video_path: str,
    output_path: str,
    device: str,
    fps: float,
) -> tuple[str, bool, str]:
    """Process a single clip. Returns (video_path, success, error_msg)."""
    try:
        with tempfile.TemporaryDirectory() as frame_dir:
            frame_paths = _extract_frames(video_path, frame_dir, fps=fps)
            if not frame_paths:
                return video_path, False, "No frames extracted"
            keypoints = _run_rtmpose(frame_paths, device=device)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        np.save(output_path, keypoints)
        return video_path, True, ""
    except Exception as e:
        return video_path, False, str(e)


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract RTMPose-x keypoints from THETIS clips")
    ap.add_argument("--input", required=True, help="THETIS VIDEO_RGB directory (data/raw/THETIS/VIDEO_RGB/)")
    ap.add_argument("--output", required=True, help="Output directory for keypoint .npy files")
    ap.add_argument("--device", default="cuda", help="'cuda' or 'cpu'")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--overwrite", action="store_true", help="Re-process already-done clips")
    args = ap.parse_args()

    thetis_rgb = Path(args.input)
    output_root = Path(args.output)

    # Collect all clips - THETIS is organized by stroke type, player encoded in filename
    tasks: list[tuple[str, str]] = []  # (video_path, output_npy_path)
    for stroke_dir in sorted(thetis_rgb.iterdir()):
        if not stroke_dir.is_dir():
            continue
        stroke_folder = stroke_dir.name.lower()
        if stroke_folder not in THETIS_STROKE_MAP:
            continue
        for video_file in sorted(stroke_dir.glob("*.avi")):
            out_path = output_root / stroke_folder / f"{video_file.stem}.npy"
            if not args.overwrite and out_path.exists():
                continue
            tasks.append((str(video_file), str(out_path)))

    print(f"Clips to process: {len(tasks)}")
    if not tasks:
        print("Nothing to do.")
        return

    done = errors = 0
    # Process sequentially - RTMPose-x is already GPU-heavy, parallelism rarely helps
    for video_path, out_path in tasks:
        _, success, err = process_clip(video_path, out_path, device=args.device, fps=args.fps)
        if success:
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(tasks)} done")
        else:
            errors += 1
            print(f"  ERR {Path(video_path).name}: {err}")

    print(f"\nDone: {done} succeeded, {errors} failed")
    print(f"Keypoints saved to: {output_root}")


if __name__ == "__main__":
    main()
