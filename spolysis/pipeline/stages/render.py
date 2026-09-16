from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from dataclasses import dataclass

import cv2
import numpy as np
import structlog

from pipeline.utils.skeleton import (
    L_SHOULDER, R_SHOULDER,
    L_HIP, R_HIP,
    SKELETON_EDGES,
)

log = structlog.get_logger(__name__)

# Radius of joint circles drawn on overlay frames
_JOINT_RADIUS = 5

# Line thickness for skeleton bones
_BONE_THICKNESS = 3

# Font used for joint index labels
_LABEL_FONT = cv2.FONT_HERSHEY_SIMPLEX
_LABEL_SCALE = 0.35
_LABEL_THICKNESS = 1

# Minimum keypoint confidence to draw a label
_LABEL_CONF_THRESHOLD = 0.5

# Height of the blend-weight indicator bar at the bottom of each frame, in pixels
_BLEND_BAR_HEIGHT = 8

# Color of the blend bar (green channel dominant to signal active correction)
_BLEND_BAR_COLOR_ACTIVE = (0, 200, 80)
_BLEND_BAR_COLOR_BG = (60, 60, 60)


@dataclass
class RenderResult:
    video_path: str
    fps: float
    frame_count: int
    width: int
    height: int


def _spine_length_2d(kps_2d: np.ndarray) -> float:
    """
    Compute spine length in pixels from a single (17, 3) RTMPose keypoint array
    (x, y, confidence).  Returns 0 if joints are degenerate.
    """
    hip_mid = (kps_2d[L_HIP, :2] + kps_2d[R_HIP, :2]) / 2.0
    shoulder_mid = (kps_2d[L_SHOULDER, :2] + kps_2d[R_SHOULDER, :2]) / 2.0
    dist = float(np.linalg.norm(shoulder_mid - hip_mid))
    return dist


def _spine_length_3d(kps_3d: np.ndarray) -> float:
    """
    Compute spine length in mm from a single (17, 3) root-relative 3D keypoint
    array.  Returns 0 if joints are degenerate.
    """
    hip_mid = (kps_3d[L_HIP] + kps_3d[R_HIP]) / 2.0
    shoulder_mid = (kps_3d[L_SHOULDER] + kps_3d[R_SHOULDER]) / 2.0
    dist = float(np.linalg.norm(shoulder_mid - hip_mid))
    return dist


def _project_corrected_to_pixels(
    corrected_3d_frame: np.ndarray,  # (17, 3) root-relative mm
    original_2d_frame: np.ndarray,   # (17, 3) pixel coords + confidence
) -> np.ndarray:
    """
    Weak-perspective projection of the corrected 3D skeleton onto 2D pixel coords.

    The root (hip midpoint) 2D position is known from the original RTMPose output
    and is used as the translation anchor.  Scale (pixels-per-mm) is estimated
    from the spine length ratio between 2D pixels and 3D mm.

    Axis mapping for a side-facing camera:
      - 3D X -> pixel X (lateral, left/right across the frame)
      - 3D Y -> pixel Y negated (Y is up in 3D space, down in image coords)
      - 3D Z (depth) is ignored in this projection

    Returns (17, 2) pixel coordinates for the corrected skeleton.
    """
    root_2d = (original_2d_frame[L_HIP, :2] + original_2d_frame[R_HIP, :2]) / 2.0

    spine_2d = _spine_length_2d(original_2d_frame)
    spine_3d = _spine_length_3d(corrected_3d_frame)

    if spine_3d < 1e-6 or spine_2d < 1e-6:
        # Fallback scale when spine is degenerate: assume 1 mm = 0.5 px, a
        # rough approximation for a full-body shot on a typical phone recording.
        scale = 0.5
    else:
        scale = spine_2d / spine_3d

    # Root in 3D is (0, 0, 0) since the skeleton is root-centered.
    # Project each joint relative to root, then offset by root_2d.
    pixel_coords = np.zeros((17, 2), dtype=np.float32)
    for j in range(17):
        jx = corrected_3d_frame[j, 0]
        jy = corrected_3d_frame[j, 1]
        pixel_coords[j, 0] = root_2d[0] + jx * scale
        pixel_coords[j, 1] = root_2d[1] + (-jy) * scale

    return pixel_coords


def _draw_skeleton(
    canvas: np.ndarray,
    kps_2d: np.ndarray,        # (17, 2) pixel coords
    color: tuple[int, int, int],
    alpha: float,
    draw_labels: bool = False,
    conf: np.ndarray | None = None,  # (17,) confidence scores, optional
) -> None:
    """
    Draw skeleton bones and joints onto canvas in-place using alpha blending.

    A temporary overlay image is composited onto canvas so the alpha value
    controls overall skeleton transparency without requiring per-pixel masking.
    """
    if alpha < 1e-4:
        return

    overlay = canvas.copy()

    for a_idx, b_idx in SKELETON_EDGES:
        a = kps_2d[a_idx]
        b = kps_2d[b_idx]
        ax, ay = int(round(a[0])), int(round(a[1]))
        bx, by = int(round(b[0])), int(round(b[1]))
        cv2.line(overlay, (ax, ay), (bx, by), color, _BONE_THICKNESS, cv2.LINE_AA)

    for j in range(17):
        px, py = int(round(kps_2d[j, 0])), int(round(kps_2d[j, 1]))
        cv2.circle(overlay, (px, py), _JOINT_RADIUS, color, -1, cv2.LINE_AA)

        if draw_labels and conf is not None and float(conf[j]) > _LABEL_CONF_THRESHOLD:
            cv2.putText(
                overlay,
                str(j),
                (px + _JOINT_RADIUS + 1, py - _JOINT_RADIUS - 1),
                _LABEL_FONT,
                _LABEL_SCALE,
                color,
                _LABEL_THICKNESS,
                cv2.LINE_AA,
            )

    cv2.addWeighted(overlay, alpha, canvas, 1.0 - alpha, 0, canvas)


def _draw_blend_bar(
    canvas: np.ndarray,
    blend_weight: float,
    width: int,
    height: int,
) -> None:
    """
    Draw a thin progress bar at the bottom of canvas showing blend_weight.

    Green fill = correction active, dark background = inactive portion.
    Giving the viewer a passive indicator of the correction window prevents
    confusion about why parts of the overlay look different from the rest.
    """
    bar_y_start = height - _BLEND_BAR_HEIGHT
    bar_y_end = height

    # Background bar
    cv2.rectangle(canvas, (0, bar_y_start), (width, bar_y_end), _BLEND_BAR_COLOR_BG, -1)

    # Active fill proportional to blend weight
    fill_width = int(round(blend_weight * width))
    if fill_width > 0:
        cv2.rectangle(
            canvas,
            (0, bar_y_start),
            (fill_width, bar_y_end),
            _BLEND_BAR_COLOR_ACTIVE,
            -1,
        )


def render_overlay(
    frame_paths: list[str],
    corrected_3d: np.ndarray,           # (T, 17, 3) corrected, mm root-relative
    original_2d_kps: np.ndarray,        # (T, 17, 3) pixel coords + confidence
    bboxes: np.ndarray,                 # (T, 4) player bbox, pixel coords (unused by projection but kept for future crop support)
    root_trajectory: np.ndarray,        # (T, 3) from NormalizedSkeleton
    blend_weights: np.ndarray,          # (T,) from CorrectedSequence
    output_path: str,
    fps: float = 30.0,
    skeleton_color: tuple[int, int, int] = (0, 220, 100),
    original_color: tuple[int, int, int] = (255, 100, 50),
    skeleton_alpha: float = 0.75,
) -> RenderResult:
    """
    Composite the corrected skeleton onto original video frames and encode to H.264.

    Two overlays are drawn per frame:
      - Corrected skeleton in skeleton_color, faded in/out with blend_weights.
      - Original 2D skeleton in original_color, faded out as correction fades in.
        This keeps the viewer oriented to where the user actually was before the
        correction takes over visually.

    Args:
        frame_paths:     ordered list of paths to original video frames
        corrected_3d:    (T, 17, 3) corrected 3D keypoints, mm root-relative
        original_2d_kps: (T, 17, 3) RTMPose keypoints in pixel coords
        bboxes:          (T, 4) player bounding boxes (x1, y1, x2, y2)
        root_trajectory: (T, 3) from NormalizedSkeleton (for future re-projection uses)
        blend_weights:   (T,) ease-in/out blend weights from apply_ik_correction
        output_path:     output .mp4 file path
        fps:             frame rate for encoding
        skeleton_color:  BGR color for corrected skeleton
        original_color:  BGR color for original skeleton
        skeleton_alpha:  max opacity for the corrected skeleton overlay

    Returns:
        RenderResult with output video metadata.
    """
    T_frames = len(frame_paths)
    T_kps = corrected_3d.shape[0]

    if T_frames == 0:
        raise ValueError("frame_paths is empty")
    if T_frames != T_kps:
        raise ValueError(
            f"frame_paths length {T_frames} does not match corrected_3d frames {T_kps}"
        )
    if corrected_3d.ndim != 3 or corrected_3d.shape[1:] != (17, 3):
        raise ValueError(f"corrected_3d must be (T, 17, 3), got {corrected_3d.shape}")
    if original_2d_kps.shape != corrected_3d.shape:
        raise ValueError(
            f"original_2d_kps shape {original_2d_kps.shape} must match corrected_3d shape"
        )
    if blend_weights.shape != (T_frames,):
        raise ValueError(
            f"blend_weights shape {blend_weights.shape} must be ({T_frames},)"
        )

    # Probe frame dimensions from the first image
    first_frame = cv2.imread(frame_paths[0])
    if first_frame is None:
        raise FileNotFoundError(f"Cannot read first frame: {frame_paths[0]}")
    height, width = first_frame.shape[:2]

    log.info(
        "render_overlay_start",
        frames=T_frames,
        width=width,
        height=height,
        fps=fps,
        output_path=output_path,
    )

    with tempfile.TemporaryDirectory() as frame_dir:
        for t in range(T_frames):
            img = cv2.imread(frame_paths[t])
            if img is None:
                log.warning("frame_read_failed_using_blank", frame_index=t, path=frame_paths[t])
                img = np.zeros((height, width, 3), dtype=np.uint8)

            w = float(blend_weights[t])

            # Project corrected 3D skeleton to pixel space for this frame
            corrected_2d = _project_corrected_to_pixels(corrected_3d[t], original_2d_kps[t])

            # Original skeleton confidence scores (third column of RTMPose output)
            orig_conf = original_2d_kps[t, :, 2] if original_2d_kps.shape[2] == 3 else None

            # Draw original skeleton where correction is not fully active.
            # Fades out as blend weight increases so the two skeletons don't fight.
            orig_alpha = (1.0 - w) * 0.5
            if orig_alpha > 1e-4:
                _draw_skeleton(
                    img,
                    original_2d_kps[t, :, :2],
                    original_color,
                    orig_alpha,
                    draw_labels=False,
                    conf=orig_conf,
                )

            # Draw corrected skeleton, opacity scales with blend weight
            corr_alpha = w * skeleton_alpha
            if corr_alpha > 1e-4:
                _draw_skeleton(
                    img,
                    corrected_2d,
                    skeleton_color,
                    corr_alpha,
                    draw_labels=True,
                    conf=None,  # corrected skeleton has no per-joint confidence
                )

            _draw_blend_bar(img, w, width, height)

            out_frame_path = os.path.join(frame_dir, f"{t:06d}.jpg")
            cv2.imwrite(out_frame_path, img, [cv2.IMWRITE_JPEG_QUALITY, 92])

        log.info("render_overlay_encoding_start", output_path=output_path)

        # Ensure output directory exists
        out_dir = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(out_dir, exist_ok=True)

        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-r", str(fps),
            "-i", os.path.join(frame_dir, "%06d.jpg"),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            output_path,
        ]

        proc = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            log.error(
                "ffmpeg_failed",
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
            raise RuntimeError(
                f"ffmpeg exited with code {proc.returncode}.\n"
                f"stderr: {proc.stderr}"
            )

    if not os.path.exists(output_path):
        raise RuntimeError(f"ffmpeg did not produce output file: {output_path}")

    out_size = os.path.getsize(output_path)
    if out_size == 0:
        raise RuntimeError(f"ffmpeg produced an empty output file: {output_path}")

    log.info(
        "render_overlay_done",
        output_path=output_path,
        size_bytes=out_size,
        frames=T_frames,
        fps=fps,
        width=width,
        height=height,
    )

    return RenderResult(
        video_path=output_path,
        fps=fps,
        frame_count=T_frames,
        width=width,
        height=height,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Render corrected skeleton overlay onto original video frames"
    )
    parser.add_argument(
        "--frame-dir",
        required=True,
        help="Directory containing original frame images (sorted by name)",
    )
    parser.add_argument(
        "--corrected-3d",
        required=True,
        help="Path to .npy file of shape (T, 17, 3) - corrected 3D keypoints (mm, root-relative)",
    )
    parser.add_argument(
        "--original-2d",
        required=True,
        help="Path to .npy file of shape (T, 17, 3) - original RTMPose-x keypoints (pixel coords + confidence)",
    )
    parser.add_argument(
        "--bboxes",
        required=True,
        help="Path to .npy file of shape (T, 4) - player bounding boxes in pixel coords",
    )
    parser.add_argument(
        "--root-traj",
        required=True,
        help="Path to .npy file of shape (T, 3) - root trajectory from NormalizedSkeleton",
    )
    parser.add_argument(
        "--blend-weights",
        required=True,
        help="Path to .npy file of shape (T,) - per-frame blend weights from ik.py",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output .mp4 file path",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
        help="Frame rate for output video (default: 30.0)",
    )
    args = parser.parse_args()

    # Collect frames from directory, sorted lexicographically so frame order
    # matches the original extraction order from ffmpeg.
    supported_exts = {".jpg", ".jpeg", ".png"}
    all_files = sorted(
        f for f in os.listdir(args.frame_dir)
        if os.path.splitext(f)[1].lower() in supported_exts
    )
    if not all_files:
        raise SystemExit(f"No image files found in {args.frame_dir}")

    fps_frame_paths = [os.path.join(args.frame_dir, f) for f in all_files]

    corrected_3d = np.load(args.corrected_3d)
    original_2d = np.load(args.original_2d)
    bboxes = np.load(args.bboxes)
    root_traj = np.load(args.root_traj)
    blend_weights = np.load(args.blend_weights)

    result = render_overlay(
        frame_paths=fps_frame_paths,
        corrected_3d=corrected_3d,
        original_2d_kps=original_2d,
        bboxes=bboxes,
        root_trajectory=root_traj,
        blend_weights=blend_weights,
        output_path=args.output,
        fps=args.fps,
    )

    print(f"Output video: {result.video_path}")
    print(f"Dimensions:   {result.width}x{result.height}")
    print(f"Frames:       {result.frame_count} @ {result.fps} fps")
