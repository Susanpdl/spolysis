import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { CharacterPortrait } from "@/components/CharacterPortrait";
import { colors, spacing, typography } from "@/theme";

type Cue = { title: string; instruction: string; secondary?: boolean };

const PHASE_PHRASE: Record<string, string> = {
  preparation: "during preparation",
  backswing: "during the backswing",
  contact: "around estimated contact",
  follow_through: "during the follow-through",
};

export function jointRoleLabel(
  joint: string,
  handedness: "right" | "left" = "right",
): string {
  const hitting = handedness === "left" ? "left" : "right";
  const free = handedness === "left" ? "right" : "left";
  if (joint === `${hitting}_elbow`) return "Hitting arm";
  if (joint === `${free}_elbow`) return "Free arm";
  if (joint === `${hitting}_knee`) return "Hitting-side leg";
  if (joint === `${free}_knee`) return "Free-side leg";
  if (joint === "hip_rotation") return "Torso turn";
  if (joint.endsWith("shoulder_abduction")) return "Serve reach";
  return joint.replace(/_/g, " ");
}

function phasePhrase(phase?: string | null): string {
  if (!phase) return "during this swing";
  return PHASE_PHRASE[phase] ?? phase.replace(/_/g, " ");
}

function cueForJoint(
  joint: string,
  phase: string | null | undefined,
  handedness: "right" | "left",
  secondary: boolean,
): Cue {
  const role = jointRoleLabel(joint, handedness);
  return {
    title: secondary ? `Secondary: ${role}` : role,
    instruction: secondary
      ? `A smaller difference also showed up at the ${role.toLowerCase()}. Use it as extra context, not the main rehearsal.`
      : `At the violet marker, copy the green model's ${role.toLowerCase()} ${phasePhrase(phase)}. Rehearse it slowly within a comfortable range.`,
    secondary,
  };
}

export function SwingCues({
  faultJoints,
  faultLabel,
  faultPhase,
  handedness = "right",
}: {
  faultJoints: string[];
  faultLabel?: string | null;
  faultPhase?: string | null;
  handedness?: "right" | "left";
}) {
  const primaryJoint = faultLabel || faultJoints[0];
  const secondaryJoints = faultJoints.filter((joint) => joint !== primaryJoint);
  const cues: Cue[] = [];
  if (primaryJoint) {
    cues.push(cueForJoint(primaryJoint, faultPhase, handedness, false));
  }
  for (const joint of secondaryJoints.slice(0, 2)) {
    cues.push(cueForJoint(joint, faultPhase, handedness, true));
  }
  const hasFocus = cues.length > 0;

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <CharacterPortrait character="marlow" size={64} />
        <View style={styles.headerCopy}>
          <Text style={styles.eyebrow}>YOUR NEXT PRACTICE</Text>
          <Text accessibilityRole="header" style={styles.title}>
            {hasFocus ? "Rehearse this swing cue" : "Keep building your rhythm"}
          </Text>
        </View>
      </View>

      {hasFocus ? (
        cues.map((cue, index) => (
          <View key={`${cue.title}-${index}`} style={styles.cueRow}>
            <View
              style={[styles.bullet, cue.secondary && styles.secondaryBullet]}
            >
              <Text style={styles.bulletText}>
                {cue.secondary ? "S" : "1"}
              </Text>
            </View>
            <View style={styles.cueCopy}>
              <Text style={styles.cueTitle}>{cue.title}</Text>
              <Text style={styles.instruction}>{cue.instruction}</Text>
            </View>
          </View>
        ))
      ) : (
        <Text style={styles.instruction}>
          No single movement stood out in this comparison. Watch the green model
          and keep the swing smooth and comfortable.
        </Text>
      )}

      <Text style={styles.footnote}>
        Use the green mannequin and violet markers in the 3D replay as your
        guide. These are practice cues, not precise measurements.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.primaryMuted,
    borderRadius: 24,
    padding: spacing.md,
    gap: spacing.md,
  },
  header: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  headerCopy: { flex: 1, gap: spacing.xs },
  eyebrow: {
    ...typography.label,
    color: colors.primary,
    fontSize: 10,
  },
  title: {
    color: colors.text.primary,
    fontFamily: "Fraunces_500Medium",
    fontSize: 21,
    lineHeight: 26,
  },
  cueRow: { flexDirection: "row", alignItems: "flex-start", gap: spacing.sm },
  bullet: {
    width: 23,
    height: 23,
    borderRadius: 12,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 1,
  },
  secondaryBullet: { backgroundColor: colors.text.muted },
  bulletText: {
    color: colors.text.inverse,
    fontFamily: "DMSans_700Bold",
    fontSize: 12,
  },
  cueCopy: { flex: 1, gap: 3 },
  cueTitle: {
    color: colors.text.primary,
    fontFamily: "DMSans_700Bold",
    fontSize: 14,
  },
  instruction: {
    color: colors.text.secondary,
    fontFamily: "DMSans_400Regular",
    fontSize: 13,
    lineHeight: 19,
  },
  footnote: {
    color: colors.text.muted,
    fontFamily: "DMSans_400Regular",
    fontSize: 11,
    lineHeight: 16,
    borderTopWidth: 1,
    borderTopColor: "rgba(40,25,80,0.12)",
    paddingTop: spacing.sm,
  },
});
