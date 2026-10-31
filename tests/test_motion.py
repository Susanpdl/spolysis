from pathlib import Path
import numpy as np
import pytest
from pipeline.models.motionbert import MotionBERTLifter, coco_to_h36m, h36m_to_coco
from pipeline.runner import mirror_pose
from pipeline.stages.normalize3d import normalize_skeleton, _BONE_PAIRS
from pipeline.stages.phases import StrokePhases, detect_phases
from pipeline.stages.align import align_to_reference
from pipeline.stages.delta import compute_deltas, DeltaTable, JointDelta, angle_3d
from pipeline.stages.ik import apply_ik_correction
from pipeline.stages.recommend import recommend_3d


def _rotate(points, pivot, axis, radians):
    axis = axis / max(float(np.linalg.norm(axis)), 1e-9)
    vectors = points - pivot
    cosine, sine = np.cos(radians), np.sin(radians)
    return (
        pivot
        + vectors * cosine
        + np.cross(axis, vectors) * sine
        + (vectors @ axis)[..., None] * axis * (1 - cosine)
    )


def _bend_hinge(pose, root, mid, end, children, extra_deg):
    bent = pose.copy()
    axis = np.cross(bent[root] - bent[mid], bent[end] - bent[mid])
    bent[children] = _rotate(
        bent[children], bent[mid], axis, np.radians(extra_deg)
    )
    return bent


def test_joint_mapping_and_handedness():
    coco = np.arange(17 * 3, dtype=np.float32).reshape(1, 17, 3)
    h36m = coco_to_h36m(coco)
    np.testing.assert_equal(h36m[:, 1], coco[:, 12])
    np.testing.assert_equal(h36m[:, 13], coco[:, 9])
    root = (coco[:, 11:12] + coco[:, 12:13]) / 2
    expected = coco - root
    expected[..., 1] *= -1
    np.testing.assert_allclose(h36m_to_coco(h36m)[:, 5:], expected[:, 5:])
    np.testing.assert_equal(mirror_pose(mirror_pose(coco)), coco)


def test_missing_model_never_returns_untrained_output():
    with pytest.raises(RuntimeError, match="checkpoint is missing"):
        MotionBERTLifter("/nonexistent/checkpoint", device="cpu")


def test_same_motion_has_no_faults(motion_sequence):
    data = motion_sequence
    phases = detect_phases(data, "forehand")
    delta = compute_deltas(data, data, phases, "forehand")
    assert not delta.fault_joints
    out = apply_ik_correction(normalize_skeleton(data), delta, phases)
    np.testing.assert_equal(out.keypoints_3d, normalize_skeleton(data).keypoints_3d)
    assert not out.blend_weights.any()


def test_correction_preserves_bones_during_every_blend_frame(motion_sequence):
    data = motion_sequence
    skel = normalize_skeleton(data)
    phases = detect_phases(data, "forehand")
    table = DeltaTable(
        deltas=[
            JointDelta("right_elbow", "contact", 120, 90, 30),
            JointDelta("hip_rotation", "contact", 45, 20, 25),
        ],
        fault_joints=["right_elbow", "hip_rotation"],
        fault_frames=(30, 40),
        stroke_type="forehand",
    )
    out = apply_ik_correction(skel, table, phases)
    for a, b in _BONE_PAIRS.values():
        np.testing.assert_allclose(
            np.linalg.norm(out.keypoints_3d[:, a] - out.keypoints_3d[:, b], axis=1),
            np.linalg.norm(skel.keypoints_3d[:, a] - skel.keypoints_3d[:, b], axis=1),
            atol=1e-5,
        )
    np.testing.assert_equal(out.keypoints_3d[:22], skel.keypoints_3d[:22])
    t = 35
    before = angle_3d(*skel.keypoints_3d[t, [6, 8, 10]])
    after = angle_3d(*out.keypoints_3d[t, [6, 8, 10]])
    assert after == pytest.approx(np.clip(before - 30, 10, 175), abs=1e-3)


def test_alignment_is_invariant_to_uniform_scale(tmp_path, motion_sequence):
    data = motion_sequence
    np.save(tmp_path / "reference_forehand.npy", data)
    phases = detect_phases(data, "forehand")
    alignment = align_to_reference(data * 3, phases, "forehand", str(tmp_path))
    assert alignment.ref_seq.shape == data.shape
    assert np.isfinite(alignment.ref_seq).all()
    # Joint-angle alignment must not collapse to a body-size magnitude signal.
    assert (
        abs(
            angle_3d(*alignment.ref_seq[phases.contact, [6, 8, 10]])
            - angle_3d(*data[phases.contact, [6, 8, 10]])
        )
        < 5
    )


def test_single_frame_fails_with_actionable_error():
    with pytest.raises(ValueError, match="three"):
        detect_phases(np.zeros((1, 17, 3)), "serve")


def test_video_render_roundtrip(tmp_path, motion_sequence):
    import cv2
    from pipeline.stages.render import render_overlay
    from pipeline.stages.extract import extract_frames

    data = normalize_skeleton(motion_sequence[:30]).keypoints_3d
    frames = []
    original2d = data.copy()
    original2d[..., :2] = data[..., :2] * [45, -45] + [160, 150]
    original2d[..., 2] = 1
    for i in range(len(data)):
        path = tmp_path / f"{i:04d}.jpg"
        cv2.imwrite(str(path), np.full((320, 320, 3), 60, dtype=np.uint8))
        frames.append(str(path))
    output = str(tmp_path / "overlay.mp4")
    render_overlay(
        frames,
        data,
        original2d,
        np.zeros((30, 4)),
        np.zeros((30, 3)),
        np.ones(30),
        output,
        original_3d=data,
    )
    extracted = extract_frames(output, output_dir=str(tmp_path / "extracted"))
    assert extracted.frame_count == 30
    assert Path(output).stat().st_size > 1000


def test_quality_rejects_defocused_frames(tmp_path):
    import re
    import cv2
    from pipeline.stages.quality import check_quality

    # Crisp blocks and their defocused version have identical framing.
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    for y in range(0, 480, 16):
        for x in range(0, 640, 16):
            image[y : y + 16, x : x + 16] = 255 if (x // 16 + y // 16) % 2 else 0
    keypoints = np.ones((1, 17, 3), dtype=np.float32)
    cv2.imwrite(str(tmp_path / "frame.jpg"), image)
    assert check_quality(str(tmp_path), keypoints).passed
    cv2.imwrite(str(tmp_path / "frame.jpg"), cv2.GaussianBlur(image, (51, 51), 12))
    result = check_quality(str(tmp_path), keypoints)
    assert not result.passed
    reason = result.reason or ""
    lowered = reason.lower()
    assert "blurry" in lowered
    assert "lighting" in lowered
    assert "stable" in lowered
    assert "score" not in lowered
    assert "sharpness" not in lowered
    assert re.search(r"\d", reason) is None


def test_quality_framing_reject_asks_for_recapture(tmp_path):
    import cv2
    from pipeline.stages.quality import check_quality

    image = np.zeros((480, 640, 3), dtype=np.uint8)
    for y in range(0, 480, 16):
        for x in range(0, 640, 16):
            image[y : y + 16, x : x + 16] = 255 if (x // 16 + y // 16) % 2 else 0
    cv2.imwrite(str(tmp_path / "frame.jpg"), image)
    keypoints = np.zeros((10, 17, 3), dtype=np.float32)
    keypoints[:, :, 2] = 0.1
    result = check_quality(str(tmp_path), keypoints)
    assert not result.passed
    lowered = (result.reason or "").lower()
    assert "body" in lowered or "frame" in lowered
    assert "retry this clip" not in lowered


def test_primary_finding_is_largest_threshold_crossing_pair(motion_sequence):
    """Knee in preparation outranks a smaller elbow difference at estimated contact."""
    ref = motion_sequence.copy()
    user = ref.copy()
    total = len(ref)
    phases = StrokePhases(
        preparation=(0, 24),
        backswing=(25, 44),
        contact=45,
        follow_through=(46, total - 1),
        total_frames=total,
    )
    for frame in range(0, 25):
        user[frame] = _bend_hinge(user[frame], 12, 14, 16, [16], -50)
    user[45] = _bend_hinge(user[45], 6, 8, 10, [10], 25)

    table = compute_deltas(user, ref, phases, "forehand")
    assert table.primary is not None
    assert table.primary.joint == "right_knee"
    assert table.primary.phase == "preparation"
    assert table.fault_joints[0] == "right_knee"
    assert "right_elbow" in table.fault_joints
    start, end = table.fault_frames
    assert start <= 24
    assert end >= 0
    assert min(end, 24) >= max(start, 0)

    text = recommend_3d(table)
    lowered = text.lower()
    assert "preparation" in lowered
    assert "hitting-side leg" in lowered or "knee" in lowered
    assert "estimated contact" not in lowered
    assert "mm" not in lowered
    assert "clinical" not in lowered


def test_service_failure_asks_to_retry_this_clip():
    from pipeline.temporal.workflows import PLAYER_SERVICE_FAILURE

    lowered = PLAYER_SERVICE_FAILURE.lower()
    assert "retry this clip" in lowered
    assert "try again later" in lowered
    assert "new recording" not in lowered
    assert "record again" not in lowered


def test_rtmpose_missing_weights_fail_closed(tmp_path, monkeypatch):
    import inspect
    from pipeline.stages import pose2d
    from pipeline.stages.pose2d import run_pose_estimation

    source = inspect.getsource(pose2d)
    assert "rtmpose-l" not in source
    assert "metafile" not in source

    (tmp_path / "frame_000001.jpg").write_bytes(b"not-an-image")
    monkeypatch.setattr("pipeline.stages.pose2d.os.path.isfile", lambda path: False)
    with pytest.raises(RuntimeError, match="RTMPose-x"):
        run_pose_estimation(str(tmp_path))


def test_rtmpose_cuda_fallback_keeps_baked_checkpoint():
    from pipeline.stages.pose2d import (
        _BAKED_CONFIG,
        _BAKED_WEIGHTS,
        _build_rtmpose_inferencer,
    )

    calls = []

    class FakeInferencer:
        def __init__(self, pose2d, pose2d_weights, device):
            calls.append((pose2d, pose2d_weights, device))
            if device == "cuda":
                raise RuntimeError("CUDA not available")

    inferencer = _build_rtmpose_inferencer(
        FakeInferencer, _BAKED_CONFIG, _BAKED_WEIGHTS
    )
    assert isinstance(inferencer, FakeInferencer)
    assert calls == [
        (_BAKED_CONFIG, _BAKED_WEIGHTS, "cuda"),
        (_BAKED_CONFIG, _BAKED_WEIGHTS, "cpu"),
    ]
    assert all("rtmpose-l" not in pose2d for pose2d, _, _ in calls)


def test_missing_reference_is_failure_not_quality_reject(tmp_path, motion_sequence):
    phases = detect_phases(motion_sequence, "forehand")
    with pytest.raises(FileNotFoundError, match="Reference"):
        align_to_reference(
            motion_sequence, phases, "forehand", str(tmp_path / "missing-refs")
        )


def test_overlay_marks_primary_joint_without_index_labels(monkeypatch):
    import cv2
    from pipeline.stages.render import _draw_skeleton, _primary_joint_indices

    assert _primary_joint_indices("right_elbow") == (8,)
    assert _primary_joint_indices("hip_rotation") == (11, 12)
    assert _primary_joint_indices("right_shoulder_abduction") == (6,)
    assert _primary_joint_indices("left_elbow") == (7,)
    assert _primary_joint_indices(None) == ()

    labels = []
    original = cv2.putText

    def capture_text(img, text, *args, **kwargs):
        labels.append(str(text))
        return original(img, text, *args, **kwargs)

    monkeypatch.setattr(cv2, "putText", capture_text)

    canvas = np.zeros((240, 240, 3), dtype=np.uint8)
    kps = np.zeros((17, 2), dtype=np.float32)
    kps[8] = [60, 60]
    kps[10] = [180, 180]
    for joint in range(17):
        if joint not in {8, 10}:
            kps[joint] = [20.0, 20.0 + joint * 8]
    _draw_skeleton(canvas, kps, (0, 220, 100), 1.0, primary_joints=(8,))
    assert labels == []

    def painted(xy, radius=16):
        x, y = int(xy[0]), int(xy[1])
        region = canvas[
            max(0, y - radius) : y + radius + 1, max(0, x - radius) : x + radius + 1
        ]
        return int((region > 0).any(axis=2).sum())

    assert painted(kps[8]) > painted(kps[10])
