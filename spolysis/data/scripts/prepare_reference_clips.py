#!/usr/bin/env python3
"""
Prepare canonical reference clips from THETIS expert players for R2 upload.

Uses the first usable clip from player p32 (first expert) for each stroke type.
These are placeholder clips for Phase 1 launch - good enough to ship.
Replace with licensed pro footage before public launch.

Source: data/raw/THETIS/VIDEO_RGB/
Output: data/clips/reference/<stroke_type>/canonical.mp4

Then upload to R2:
  aws s3 cp data/clips/reference/ s3://spolysis/clips/ --recursive \\
    --endpoint-url https://<account-id>.r2.cloudflarestorage.com

Usage:
  python data/scripts/prepare_reference_clips.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

THETIS_RGB = Path("data/raw/THETIS/VIDEO_RGB")
OUT_DIR = Path("data/clips/reference")

# Best source clip per canonical stroke type
# Using p32 (first expert) s1 (first take) for each
CLIP_SOURCES: dict[str, tuple[str, str]] = {
    "forehand": ("forehand_flat",    "p32_foreflat_s1.avi"),
    "backhand": ("backhand",         "p32_backhand_s1.avi"),
    "serve":    ("flat_service",     "p32_serflat_s1.avi"),
    "volley":   ("forehand_volley",  "p32_fvolley_s1.avi"),
}


def convert_clip(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-movflags", "+faststart",
        "-an",  # no audio
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"  ERR: {result.stderr.decode()[:200]}")
        return False
    return True


def main() -> None:
    errors = 0
    for stroke, (folder, filename) in CLIP_SOURCES.items():
        src = THETIS_RGB / folder / filename
        dst = OUT_DIR / stroke / "canonical.mp4"

        if not src.exists():
            # Try s2 as fallback
            fallback = src.parent / filename.replace("s1", "s2")
            if fallback.exists():
                src = fallback
            else:
                print(f"  SKIP {stroke}: source not found ({src})")
                errors += 1
                continue

        print(f"  {stroke}: {src.name} -> {dst}")
        if not convert_clip(src, dst):
            errors += 1
        else:
            size_kb = dst.stat().st_size // 1024
            print(f"    ok ({size_kb} KB)")

    print(f"\nDone. {len(CLIP_SOURCES) - errors}/{len(CLIP_SOURCES)} clips prepared.")
    print(f"Output: {OUT_DIR.resolve()}")
    print("\nUpload to R2:")
    print(
        "  aws s3 cp data/clips/reference/ s3://spolysis/clips/ --recursive \\\n"
        "    --endpoint-url https://<account-id>.r2.cloudflarestorage.com"
    )


if __name__ == "__main__":
    if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
        print("ERROR: ffmpeg not found. Install with: brew install ffmpeg")
        sys.exit(1)
    main()
