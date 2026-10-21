"""Deterministic coaching grounded in the reconstructed motion comparison."""


def recommend_3d(table, handedness: str = "right") -> str:
    """Ground feedback in measured differences, including their direction.

    A single-camera estimate cannot establish an ideal technique or ball contact.
    No speculative fault labels or ungrounded LLM findings are introduced.
    """
    candidates = [d for d in table.deltas if d.joint in table.fault_joints]
    if not candidates:
        return "Your measured joint angles are close to this reference swing. Review the 3D playback and keep practicing a smooth, comfortable motion."
    worst = max(candidates, key=lambda d: abs(d.delta_deg))
    name = worst.joint
    if handedness == "left":
        name = (
            name.replace("right_", "other_")
            .replace("left_", "right_")
            .replace("other_", "left_")
        )
    name = name.replace("_", " ").replace("hip rotation", "hip-to-shoulder separation")
    direction = "larger" if worst.delta_deg > 0 else "smaller"
    phase = worst.phase.replace("_", " ").replace("contact", "estimated contact")
    return (
        f"During {phase}, your {name} angle is about {abs(worst.delta_deg):.0f} degrees {direction} "
        "than this reference. Use the overlay to compare the movement, then rehearse it slowly within a comfortable range. "
        "These are video-based estimates, not a precise measurement or a requirement to match the reference."
    )
