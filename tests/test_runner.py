"""Full stage integration with external storage and neural inference isolated."""

from pathlib import Path
import numpy as np
import pytest
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


def _stub_upload_path(monkeypatch, tmp_path, motion_sequence):
    import cv2

    motion = motion_sequence
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
    monkeypatch.setattr(runner.r2, "put_json", lambda key, data: None)
    monkeypatch.setattr(runner.r2, "upload_file", lambda *a, **k: None)
    monkeypatch.setattr(runner, "extract_frames", lambda *a, **k: None)
    monkeypatch.setattr(
        runner,
        "run_pose_estimation",
        lambda *a: Pose2DResult(
            points, frames, np.tile([0, 0, 320, 320], (len(frames), 1))
        ),
    )
    return frames


def test_quality_reject_stays_rejected_with_recapture_reason(
    tmp_path, monkeypatch, motion_sequence
):
    _stub_upload_path(monkeypatch, tmp_path, motion_sequence)
    monkeypatch.setattr(
        runner,
        "check_quality",
        lambda *a: QualityResult(
            False,
            "Video is too blurry. Try recording in better lighting or keep the camera stable.",
        ),
    )
    result = runner.run_analysis("test-job", "input.mp4", "forehand")
    assert result["status"] == "rejected"
    assert "blurry" in result["reason"].lower()
    assert "lighting" in result["reason"].lower()
    assert "retry this clip" not in result["reason"].lower()


def test_missing_pose_weights_remain_failures(tmp_path, monkeypatch, motion_sequence):
    _stub_upload_path(monkeypatch, tmp_path, motion_sequence)

    def missing_weights(*a):
        raise RuntimeError(
            "The trained RTMPose-x checkpoint is missing: "
            "/opt/mmpose/rtmpose-x_body7.pth. Analysis cannot substitute another pose model."
        )

    monkeypatch.setattr(runner, "run_pose_estimation", missing_weights)
    with pytest.raises(RuntimeError, match="RTMPose-x"):
        runner.run_analysis("test-job", "input.mp4", "forehand")


def test_ffmpeg_failure_remains_a_service_failure(
    tmp_path, monkeypatch, motion_sequence
):
    reference_dir = tmp_path / "references"
    reference_dir.mkdir()
    np.save(reference_dir / "fixture_forehand.npy", motion_sequence)
    _stub_upload_path(monkeypatch, tmp_path, motion_sequence)
    monkeypatch.setattr(runner, "check_quality", lambda *a: QualityResult(True))
    monkeypatch.setattr(
        runner,
        "lift_to_3d",
        lambda pose, **k: LiftResult(
            motion_sequence[: len(pose.keypoints)].copy(), "test-fixture", 30
        ),
    )
    monkeypatch.setattr(
        runner,
        "render_overlay",
        lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("ffmpeg exited with code 1.\nstderr: encoder failed")
        ),
    )
    with pytest.raises(RuntimeError, match="ffmpeg"):
        runner.run_analysis(
            "test-job",
            "input.mp4",
            "forehand",
            reference_motion_dir=str(reference_dir),
        )


def test_runner_remaps_fault_phase_keys_for_left_handed(
    tmp_path, monkeypatch, motion_sequence
):
    from pipeline.stages.delta import DeltaTable, JointDelta

    motion = motion_sequence
    reference_dir = tmp_path / "references"
    reference_dir.mkdir()
    np.save(reference_dir / "fixture_forehand.npy", motion)
    _stub_upload_path(monkeypatch, tmp_path, motion_sequence)
    points = motion.copy()
    points[..., :2] = motion[..., :2] * [120, -120] + [160, 230]
    points[:, 9] = points[:, 10]
    points[..., 2] = 0.95
    frames = [
        str(tmp_path / f"{i:04d}.jpg") for i in range(len(motion))
    ]
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
    monkeypatch.setattr(runner.r2, "upload_file", lambda *a, **k: None)
    monkeypatch.setattr(
        runner,
        "render_overlay",
        lambda *a, **k: Path(a[6]).write_bytes(b"overlay"),
    )
    table = DeltaTable(
        deltas=[
            JointDelta("right_knee", "preparation", 140, 90, -50),
            JointDelta("right_elbow", "contact", 115, 90, 25),
        ],
        fault_joints=["right_knee", "right_elbow"],
        fault_frames=(0, 10),
        stroke_type="forehand",
        primary=JointDelta("right_knee", "preparation", 140, 90, -50),
        fault_phases={"right_knee": "preparation", "right_elbow": "contact"},
    )
    monkeypatch.setattr(runner, "compute_deltas", lambda *a, **k: table)
    result = runner.run_analysis(
        "test-job",
        "input.mp4",
        "forehand",
        handedness="left",
        reference_motion_dir=str(reference_dir),
    )
    assert result["fault_label"] == "left_knee"
    assert result["fault_phase"] == "preparation"
    assert result["fault_joints"] == ["left_knee", "left_elbow"]
    assert result["fault_phases"] == {
        "left_knee": "preparation",
        "left_elbow": "contact",
    }
    assert result["fault_phases"]["left_elbow"] != result["fault_phase"]
