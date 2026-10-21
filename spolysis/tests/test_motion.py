from pathlib import Path
import numpy as np
import pytest
from pipeline.models.motionbert import MotionBERTLifter, coco_to_h36m, h36m_to_coco
from pipeline.runner import mirror_pose
from pipeline.stages.normalize3d import normalize_skeleton, _BONE_PAIRS
from pipeline.stages.phases import detect_phases
from pipeline.stages.align import align_to_reference
from pipeline.stages.delta import compute_deltas, DeltaTable, JointDelta, angle_3d
from pipeline.stages.ik import apply_ik_correction


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
    assert not check_quality(str(tmp_path), keypoints).passed
