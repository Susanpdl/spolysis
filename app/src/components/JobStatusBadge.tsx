import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors } from "@/theme";

type Status = "pending" | "processing" | "completed" | "failed" | "rejected";

const STATUS_CONFIG: Record<Status, { label: string; bg: string; fg: string }> =
  {
    pending: {
      label: "Queued",
      bg: colors.surfaceElevated,
      fg: colors.text.secondary,
    },
    processing: {
      label: "In progress",
      bg: colors.primaryMuted,
      fg: colors.primary,
    },
    completed: {
      label: "Ready",
      bg: "#E5F6EC",
      fg: "#25804F",
    },
    failed: { label: "Failed", bg: colors.errorMuted, fg: colors.error },
    rejected: { label: "Rejected", bg: colors.errorMuted, fg: colors.error },
  };

export function JobStatusBadge({ status }: { status: Status }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  return (
    <View style={[styles.badge, { backgroundColor: cfg.bg }]}>
      <Text style={[styles.label, { color: cfg.fg }]}>{cfg.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: { paddingHorizontal: 11, paddingVertical: 6, borderRadius: 999 },
  label: {
    color: colors.text.secondary,
    fontFamily: "DMSans_700Bold",
    fontSize: 11,
  },
});
