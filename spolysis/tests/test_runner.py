"""Full stage integration with external storage and neural inference isolated."""

from pathlib import Path
import numpy as np
from pipeline import runner
from pipeline.stages.pose2d import Pose2DResult
from pipeline.stages.lift import LiftResult
from pipeline.stages.quality import QualityResult


def test_3d_runner_publishes_viewer_schema_and_overlay(
    tmp_path, monkeypatch, motion_sequence
):
    import cv2

    motion = motion_sequence
    reference_dir = tmp_path / "references"
    reference_dir.mkdir()
    np.save(reference_dir / "fixture_forehand.npy", motion)
    points = motion.copy()
    points[..., :2] = motion[..., :2] * [120, -120] + [160, 230]
    points[..., 2] = 0.95
    frames = []
    for i in range(len(motion)):
        file = tmp_path / f"{i:04d}.jpg"
        cv2.imwrite(str(file), np.full((320, 320, 3), 80, dtype=np.uint8))
        frames.append(str(file))
    monkeypatch.setattr(runner.r2, "key_exists", lambda key: False)
    monkeypatch.setattr(runner.r2, "download_file", lambda *a: None)
    monkeypatch.setattr(runner, "extract_frames", lambda *a, **k: None)
    monkeypatch.setattr(
        runner,
        "run_pose_estimation",
        lambda *a: Pose2DResult(
            points, frames, np.tile([0, 0, 320, 320], (len(frames), 1))
        ),
    )
    monkeypatch.setattr(runner, "check_quality", lambda *a: QualityResult(True))
    monkeypatch.setattr(
        runner,
        "lift_to_3d",
        lambda pose, **k: LiftResult(
            motion[: len(pose.keypoints)].copy(), "test-fixture", 30
        ),
    )
    objects = {}
    monkeypatch.setattr(
        runner.r2, "put_json", lambda key, data: objects.__setitem__(key, data)
    )

    def upload(path, key, content_type):
        assert Path(path).stat().st_size > 1000
        objects[key] = content_type

    monkeypatch.setattr(runner.r2, "upload_file", upload)
    result = runner.run_analysis(
        "test-job", "input.mp4", "forehand", reference_motion_dir=str(reference_dir)
    )
    assert result.get("stroke_type") == "forehand", result
    assert result["overlay_video_url"] == "results/test-job/overlay.mp4"
    skeleton = objects["results/test-job/skeleton_3d.json"]
    assert skeleton["schema_version"] == 1
    assert np.asarray(skeleton["frames"]).shape[1:] == (17, 3)
    assert len(skeleton["original_frames"]) == len(skeleton["frames"])
    assert objects["results/test-job/result.json"] == result
