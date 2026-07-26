from __future__ import annotations
import anthropic
import structlog
from pipeline.config import settings

log = structlog.get_logger(__name__)

FAULT_RULES: dict[str, dict] = {
    "late_contact": {
        "finding": "You are making contact with the ball behind your front hip",
        "ideal": "Contact should happen slightly in front of the lead hip, with your weight transferring forward",
        "severity": "high",
        "drill": "Shadow-swing drill: focus on stepping forward and meeting an imaginary ball in front of your body",
    },
    "open_stance": {
        "finding": "Your hips are facing the net at the point of contact",
        "ideal": "At contact, your hitting-side hip should be closed toward the side fence",
        "severity": "medium",
        "drill": "Use a resistance band around your thighs during shadow swings to feel hip engagement",
    },
    "low_follow_through": {
        "finding": "Your racket finishes low and across your body after contact",
        "ideal": "The racket should finish high, over the opposite shoulder, to generate topspin and control",
        "severity": "medium",
        "drill": "Finish every swing with your racket touching your opposite ear - this builds the high finish muscle memory",
    },
    "arm_only": {
        "finding": "Your swing is driven almost entirely by your arm with minimal hip or shoulder rotation",
        "ideal": "A powerful stroke starts from ground up: legs load, hips rotate 45-60 degrees, then shoulders and arm follow",
        "severity": "high",
        "drill": "Hold your non-dominant hand on your hip and focus on rotating that hip toward the net as you swing",
    },
    "no_hip_rotation": {
        "finding": "Your hips remain stationary through the entire swing",
        "ideal": "Hip rotation of 45-60 degrees through contact generates 60-70% of stroke power",
        "severity": "high",
        "drill": "Practice the 'hip snap' drill: turn your back hip toward the target as you make contact",
    },
    "grip_issue": {
        "finding": "Your wrist and forearm position suggest an inconsistent grip through the stroke",
        "ideal": "Maintain a consistent Eastern or Semi-Western grip through the full swing for control and spin",
        "severity": "medium",
        "drill": "Practice slow-motion strokes focusing on keeping your grip firm but relaxed through contact",
    },
    "no_trophy_position": {
        "finding": "Your arm does not reach the trophy position during the serve wind-up",
        "ideal": "At the trophy position, your hitting arm elbow should be at shoulder height with the racket pointing up",
        "severity": "high",
        "drill": "Serve in slow motion stopping at trophy position, hold for 2 seconds before continuing",
    },
    "low_toss": {
        "finding": "Your ball toss is too low, forcing you to reach down to make contact",
        "ideal": "Toss the ball to the peak of your reach plus racket length, slightly in front of your lead foot",
        "severity": "medium",
        "drill": "Toss-only drill: practice 20 tosses without swinging, aiming to hit a target above your head",
    },
}

CLAUDE_PROMPT = """\
You are a professional tennis coach reviewing a player's stroke analysis. \
The following specific biomechanical fault was detected:

Fault: {fault_label}
What was observed: {finding}
What should happen: {ideal}
Suggested drill: {drill}

Write 2-3 sentences of encouraging, specific coaching advice. \
Be concrete - name the exact body part and action to change. \
Include the drill in an actionable way. \
Under 65 words total. \
Do not mention AI, algorithms, video, or analysis software. \
Write as if you just watched the player hit.\
"""

NO_FAULT_PROMPT = """\
You are a professional tennis coach. A player just hit a {stroke_type} stroke that \
was technically sound - no major faults detected. \
Write 2 sentences of positive reinforcement and one small refinement tip to keep improving. \
Under 50 words. Do not mention AI, algorithms, or analysis.\
"""


def generate_recommendation(
    stroke_type: str,
    fault_label: str | None,
    confidence: float,
) -> str:
    """
    Generate a coaching recommendation using rules + Claude API.
    """
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    if fault_label and fault_label in FAULT_RULES:
        rule = FAULT_RULES[fault_label]
        prompt = CLAUDE_PROMPT.format(
            fault_label=fault_label.replace("_", " ").title(),
            finding=rule["finding"],
            ideal=rule["ideal"],
            drill=rule["drill"],
        )
    elif fault_label:
        # Unknown fault - generate generic advice
        prompt = f"You are a tennis coach. The player's {stroke_type} has a technical issue with {fault_label.replace('_', ' ')}. Write 2-3 sentences of specific improvement advice. Under 60 words."
    else:
        prompt = NO_FAULT_PROMPT.format(stroke_type=stroke_type)

    log.info("calling_claude_api", fault=fault_label, stroke=stroke_type)
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        log.info("claude_recommendation_generated", chars=len(text))
        return text
    except Exception as e:
        log.error("claude_api_failed", error=str(e))
        # Fallback to rule-based text
        if fault_label and fault_label in FAULT_RULES:
            rule = FAULT_RULES[fault_label]
            return f"{rule['finding']}. {rule['ideal']}. Try this: {rule['drill']}."
        return f"Your {stroke_type} is looking good! Focus on consistency and keep practicing."


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stroke", required=True)
    parser.add_argument("--fault")
    parser.add_argument("--confidence", type=float, default=0.8)
    args = parser.parse_args()
    rec = generate_recommendation(args.stroke, args.fault, args.confidence)
    print(f"Recommendation:\n{rec}")
