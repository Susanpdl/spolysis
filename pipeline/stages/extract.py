from __future__ import annotations
import subprocess
import os
import tempfile
from dataclasses import dataclass
import structlog

log = structlog.get_logger(__name__)


@dataclass
class ExtractionResult:
    frame_dir: str
    frame_count: int
    fps: float
    duration_seconds: float


def extract_frames(video_path: str, fps: float = 30.0, output_dir: str | None = None) -> ExtractionResult:
    """
    Extract frames from a video file using ffmpeg.

    Args:
        video_path: Path to the input video file.
        fps: Target frames per second.
        output_dir: Directory to write frames into. Creates a temp dir if None.

    Returns:
        ExtractionResult with frame directory, count, and metadata.
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="spolysis_frames_")

    os.makedirs(output_dir, exist_ok=True)
    frame_pattern = os.path.join(output_dir, "frame_%06d.jpg")

    # Probe video duration and native fps
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-select_streams", "v:0", video_path,
    ]
    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
    duration = 0.0
    if probe_result.returncode == 0:
        import json
        info = json.loads(probe_result.stdout)
        streams = info.get("streams", [])
        if streams:
            duration = float(streams[0].get("duration", 0))

    # Extract at target fps
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps={fps}",
        "-q:v", "2",  # high quality JPEG
        "-y",
        frame_pattern,
    ]
    log.info("extracting_frames", video=video_path, fps=fps, output=output_dir)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed:\n{result.stderr}")

    frames = sorted(f for f in os.listdir(output_dir) if f.endswith(".jpg"))
    frame_count = len(frames)
    log.info("frames_extracted", count=frame_count, duration=duration)

    return ExtractionResult(
        frame_dir=output_dir,
        frame_count=frame_count,
        fps=fps,
        duration_seconds=duration,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract frames from a video")
    parser.add_argument("--input", required=True, help="Input video path")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--fps", type=float, default=30.0)
    args = parser.parse_args()

    result = extract_frames(args.input, fps=args.fps, output_dir=args.output)
    print(f"Extracted {result.frame_count} frames to {result.frame_dir}")
