"""Deterministic coaching grounded in the reconstructed motion comparison."""

_ROLE_NAMES = {
    "right_elbow": "hitting arm",
    "left_elbow": "free arm",
    "right_knee": "hitting-side leg",
    "left_knee": "free-side leg",
    "hip_rotation": "hip-to-shoulder separation",
    "right_shoulder_abduction": "hitting-arm reach",
    "left_shoulder_abduction": "free-arm reach",
}

_PHASE_NAMES = {
    "preparation": "preparation",
    "backswing": "the backswing",
    "contact": "estimated contact",
    "follow_through": "the follow-through",
}


def _role_name(joint: str) -> str:
    """Map analysis-space joints to handedness-independent role language.

    Reconstruction always compares a right-handed pose, including mirrored
    left-handed swings, so right_* is the hitting side.
    """
    if joint in _ROLE_NAMES:
        return _ROLE_NAMES[joint]
    return joint.replace("_", " ")


def recommend_3d(table, handedness: str = "right") -> str:
    """Ground feedback in the primary measured difference and its direction.

    A single-camera estimate cannot establish an ideal technique or ball contact.
    Role names stay independent of stored left/right bone indices.
    """
    del handedness
    worst = getattr(table, "primary", None)
    if worst is None:
        candidates = [d for d in table.deltas if d.joint in table.fault_joints]
        if not candidates:
            return (
                "Your measured joint angles are close to this reference swing. "
                "Review the 3D playback and keep practicing a smooth, comfortable motion."
            )
        worst = max(candidates, key=lambda d: abs(d.delta_deg))
    name = _role_name(worst.joint)
    direction = "larger" if worst.delta_deg > 0 else "smaller"
    phase = _PHASE_NAMES.get(worst.phase, worst.phase.replace("_", " "))
    return (
        f"During {phase}, your {name} angle is about {abs(worst.delta_deg):.0f} degrees {direction} "
        "than this reference. Use the overlay to compare the movement, then rehearse it slowly within a comfortable range."
    )
