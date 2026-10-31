import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { CharacterPortrait } from "@/components/CharacterPortrait";
import { colors, spacing, typography } from "@/theme";

type Cue = { title: string; instruction: string };

const cueByJoint: Record<string, Cue> = {
  hip_rotation: {
    title: "Turn through the shot",
    instruction:
      "At the violet waist marker, follow the green model's smooth hip-and-shoulder turn as the racket comes through.",
  },
  right_elbow: {
    title: "Let the hitting arm flow",
    instruction:
      "At the violet elbow marker, copy the green model's arm shape. Keep it relaxed as the racket extends through contact.",
  },
  left_elbow: {
    title: "Use your free arm for balance",
    instruction:
      "Compare the violet elbow with green. Let your free arm balance the turn through the swing.",
  },
  right_knee: {
    title: "Drive from your legs",
    instruction:
      "Watch the violet knee. Follow the green model's bend on setup, then drive smoothly through the shot.",
  },
  right_shoulder_abduction: {
    title: "Find a relaxed serve reach",
    instruction:
      "Follow the green shoulder and arm into the serve setup. Reach smoothly without forcing the shoulder.",
  },
};

function uniqueCues(faultJoints: string[]): Cue[] {
  const seen = new Set<string>();
  return faultJoints
    .filter((joint) => {
      if (seen.has(joint)) return false;
      seen.add(joint);
      return true;
    })
    .map(
      (joint) =>
        cueByJoint[joint] ?? {
          title: joint.replace(/_/g, " "),
          instruction:
            "Use the violet marker to find this movement. Rehearse the smooth path shown by the green model.",
        },
    )
    .slice(0, 3);
}

export function SwingCues({ faultJoints }: { faultJoints: string[] }) {
  const cues = uniqueCues(faultJoints);
  const hasFocus = cues.length > 0;

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <CharacterPortrait character="marlow" size={64} />
        <View style={styles.headerCopy}>
          <Text style={styles.eyebrow}>YOUR NEXT PRACTICE</Text>
          <Text accessibilityRole="header" style={styles.title}>
            {hasFocus ? "Try these swing cues" : "Keep building your rhythm"}
          </Text>
        </View>
      </View>

      {hasFocus ? (
        cues.map((cue, index) => (
          <View key={`${cue.title}-${index}`} style={styles.cueRow}>
            <View style={styles.bullet}>
              <Text style={styles.bulletText}>{index + 1}</Text>
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
          through contact and keep the swing smooth and comfortable.
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
