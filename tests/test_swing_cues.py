"""Cue copy must use each joint's own peak phase, never the primary's phase."""

from pathlib import Path
import numpy as np
from pipeline.stages.delta import compute_deltas
from pipeline.stages.phases import StrokePhases
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
    bent[children] = _rotate(bent[children], bent[mid], axis, np.radians(extra_deg))
    return bent

_PHASE_PHRASE = {
    "preparation": "during preparation",
    "backswing": "during the backswing",
    "contact": "around estimated contact",
    "follow_through": "during the follow-through",
}

_SWING_CUES = (
    Path(__file__).resolve().parents[1] / "app" / "src" / "components" / "SwingCues.tsx"
)


def _role_label(joint: str, handedness: str = "right") -> str:
    hitting = "left" if handedness == "left" else "right"
    free = "right" if handedness == "left" else "left"
    if joint == f"{hitting}_elbow":
        return "Hitting arm"
    if joint == f"{free}_elbow":
        return "Free arm"
    if joint == f"{hitting}_knee":
        return "Hitting-side leg"
    if joint == f"{free}_knee":
        return "Free-side leg"
    if joint == "hip_rotation":
        return "Torso turn"
    if joint.endswith("shoulder_abduction"):
        return "Serve reach"
    return joint.replace("_", " ")


def build_swing_cues(
    fault_joints,
    fault_label=None,
    fault_phase=None,
    fault_phases=None,
    handedness="right",
):
    """Mirror SwingCues.tsx: primary uses fault_phase; secondaries use fault_phases."""
    primary_joint = fault_label or (fault_joints[0] if fault_joints else None)
    secondary_joints = [joint for joint in fault_joints if joint != primary_joint]
    cues = []
    if primary_joint:
        phase_text = _PHASE_PHRASE.get(fault_phase or "", fault_phase) or "during this swing"
        role = _role_label(primary_joint, handedness)
        cues.append(
            {
                "title": role,
                "instruction": (
                    f"At the violet marker, copy the green model's {role.lower()} "
                    f"{phase_text}. Rehearse it slowly within a comfortable range."
                ),
                "secondary": False,
            }
        )
    for joint in secondary_joints[:2]:
        phase = (fault_phases or {}).get(joint)
        role = _role_label(joint, handedness)
        where = f" {_PHASE_PHRASE.get(phase, phase)}" if phase else ""
        cues.append(
            {
                "title": f"Secondary: {role}",
                "instruction": (
                    f"A smaller difference also showed up at the {role.lower()}"
                    f"{where}. Use it as extra context, not the main rehearsal."
                ),
                "secondary": True,
            }
        )
    return cues


def _knee_primary_elbow_contact(motion_sequence):
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
    return compute_deltas(user, ref, phases, "forehand")


def test_secondary_elbow_cue_does_not_borrow_primary_phase(motion_sequence):
    table = _knee_primary_elbow_contact(motion_sequence)
    assert table.primary is not None
    assert table.primary.joint == "right_knee"
    assert table.primary.phase == "preparation"
    assert table.fault_phases["right_elbow"] == "contact"

    cues = build_swing_cues(
        table.fault_joints,
        fault_label=table.primary.joint,
        fault_phase=table.primary.phase,
        fault_phases=table.fault_phases,
    )
    secondary = next(cue for cue in cues if cue["secondary"])
    assert "hitting arm" in secondary["instruction"]
    assert "around estimated contact" in secondary["instruction"]
    assert "during preparation" not in secondary["instruction"]

    omitted = build_swing_cues(
        table.fault_joints,
        fault_label=table.primary.joint,
        fault_phase=table.primary.phase,
        fault_phases=None,
    )
    omitted_secondary = next(cue for cue in omitted if cue["secondary"])
    assert "during preparation" not in omitted_secondary["instruction"]
    assert "around estimated contact" not in omitted_secondary["instruction"]

    text = recommend_3d(table)
    lowered = text.lower()
    assert "preparation" in lowered
    assert "hitting-side leg" in lowered or "knee" in lowered
    assert "estimated contact" not in lowered
    assert "hitting arm" not in lowered


def test_swing_cues_source_looks_up_per_joint_phases():
    source = _SWING_CUES.read_text()
    assert "faultPhases?.[joint]" in source
    assert "cueForJoint(joint, faultPhase" not in source
