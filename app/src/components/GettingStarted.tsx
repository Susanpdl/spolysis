import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors, spacing, typography } from "@/theme";

const steps = [
  {
    title: "Choose your stroke",
    description: "Select your stroke type and playing hand.",
  },
  {
    title: "Record or import a video",
    description: "Keep your full body and racket in view, with good lighting.",
  },
  {
    title: "Explore your swing in 3D",
    description: "Review your motion and compare suggested corrections.",
  },
];

export function GettingStarted() {
  return (
    <View style={styles.card}>
      <Text accessibilityRole="header" style={styles.heading}>
        Your first analysis
      </Text>
      {steps.map((step, index) => (
        <View key={step.title} style={styles.step}>
          <View style={styles.numberBadge}>
            <Text style={styles.number}>{index + 1}</Text>
          </View>
          <View style={styles.copy}>
            <Text style={styles.title}>{step.title}</Text>
            <Text style={styles.description}>{step.description}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: spacing.lg,
  },
  heading: { ...typography.h3, color: colors.text.primary },
  step: { flexDirection: "row", alignItems: "flex-start", gap: spacing.md },
  numberBadge: {
    minWidth: 28,
    minHeight: 28,
    padding: spacing.xs,
    borderRadius: 14,
    backgroundColor: colors.primaryMuted,
    alignItems: "center",
    justifyContent: "center",
  },
  number: { ...typography.bodySmall, fontWeight: "700", color: colors.primary },
  copy: { flex: 1, gap: spacing.xs },
  title: { ...typography.bodySmall, fontWeight: "600", color: colors.text.primary },
  description: { ...typography.bodySmall, color: colors.text.secondary },
});
