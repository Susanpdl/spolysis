import React from "react";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { RecordingScreenProps } from "@/navigation/types";
import { SPORTS } from "@/sports/catalog";
import { colors, spacing } from "@/theme";

export default function SportSelectionScreen({
  navigation,
}: RecordingScreenProps<"Sports">) {
  return (
    <SafeAreaView style={styles.page}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.brandChip}>
          <View style={styles.brandDot} />
          <Text style={styles.brandText}>SPOLYSIS</Text>
        </View>
        <Text style={styles.title}>Choose your game.</Text>
        <Text style={styles.subtitle}>
          Pick a sport to explore your movement. Tennis analysis is ready to go.
        </Text>
        <View style={styles.list}>
          <Text style={styles.sectionLabel}>YOUR SPORTS</Text>
          {SPORTS.map((sport) => (
            <TouchableOpacity
              key={sport.id}
              accessibilityRole="button"
              accessibilityLabel={`${sport.name}, ${sport.available ? "available" : "coming soon"}`}
              accessibilityState={{ disabled: !sport.available }}
              disabled={!sport.available}
              activeOpacity={0.78}
              onPress={() =>
                navigation.navigate("Capture", { sportId: sport.id })
              }
              style={[styles.card, !sport.available && styles.cardDisabled]}
            >
              <View style={styles.cardTop}>
                <View
                  style={[
                    styles.sportIcon,
                    sport.available && styles.sportIconAvailable,
                    sport.id === "table-tennis" && styles.sportIconTeal,
                    sport.id === "soccer" && styles.sportIconSage,
                    sport.id === "basketball" && styles.sportIconCoral,
                  ]}
                >
                  <Text style={styles.iconText}>{sport.icon}</Text>
                </View>
                <View style={styles.copy}>
                  <View style={styles.nameRow}>
                    <Text style={styles.name}>{sport.name}</Text>
                    <View
                      style={[
                        styles.status,
                        sport.available ? styles.available : styles.comingSoon,
                      ]}
                    >
                      <Text
                        style={[
                          styles.statusText,
                          sport.available
                            ? styles.availableText
                            : styles.comingSoonText,
                        ]}
                      >
                        {sport.available ? "AVAILABLE" : "COMING SOON"}
                      </Text>
                    </View>
                  </View>
                  <Text style={styles.description}>{sport.description}</Text>
                </View>
                {sport.available ? <Text style={styles.chevron}>›</Text> : null}
              </View>
            </TouchableOpacity>
          ))}
        </View>
        <Text style={styles.footnote}>
          Each sport will have its own movement types, analysis rules, and
          coaching.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, paddingTop: spacing.xl, gap: spacing.md },
  brandChip: {
    height: 36,
    alignSelf: "flex-start",
    paddingHorizontal: 11,
    borderRadius: 13,
    backgroundColor: colors.surface,
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
  },
  brandDot: {
    width: 9,
    height: 9,
    borderRadius: 5,
    backgroundColor: colors.primary,
  },
  brandText: {
    color: colors.text.primary,
    fontFamily: "DMSans_700Bold",
    fontSize: 10,
    letterSpacing: 1,
  },
  sectionLabel: {
    marginBottom: 2,
    color: colors.text.muted,
    fontFamily: "DMSans_700Bold",
    fontSize: 10,
    letterSpacing: 1,
  },
  title: {
    color: colors.text.primary,
    fontFamily: "Fraunces_500Medium",
    fontSize: 34,
    letterSpacing: -0.8,
  },
  subtitle: {
    color: colors.text.secondary,
    fontFamily: "DMSans_400Regular",
    fontSize: 15,
    lineHeight: 22,
    marginBottom: spacing.sm,
  },
  list: { gap: spacing.sm },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: 24,
    padding: spacing.md,
    shadowColor: "#281950",
    shadowOpacity: 0.04,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 5 },
    elevation: 1,
  },
  cardDisabled: { backgroundColor: colors.background },
  cardTop: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  sportIcon: {
    height: 58,
    width: 58,
    borderRadius: 20,
    backgroundColor: colors.surfaceElevated,
    justifyContent: "center",
    alignItems: "center",
  },
  sportIconAvailable: { backgroundColor: "#F8EFE4" },
  sportIconTeal: { backgroundColor: "#E4F6F2" },
  sportIconSage: { backgroundColor: "#E9F2E4" },
  sportIconCoral: { backgroundColor: "#F8E9ED" },
  iconText: { fontSize: 27 },
  copy: { flex: 1, gap: 6 },
  nameRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    gap: 8,
  },
  name: {
    color: colors.text.primary,
    fontFamily: "Fraunces_500Medium",
    fontSize: 21,
  },
  status: { borderRadius: 99, paddingHorizontal: 8, paddingVertical: 4 },
  available: { backgroundColor: "#173b2a" },
  comingSoon: { backgroundColor: colors.background },
  statusText: {
    fontFamily: "DMSans_700Bold",
    fontSize: 9,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
  availableText: { color: colors.primary },
  comingSoonText: { color: colors.text.muted },
  description: {
    color: colors.text.secondary,
    fontFamily: "DMSans_400Regular",
    fontSize: 13,
    lineHeight: 18,
  },
  chevron: { color: colors.primary, fontSize: 30, paddingLeft: 2 },
  footnote: {
    color: colors.text.muted,
    fontFamily: "DMSans_400Regular",
    fontSize: 12,
    lineHeight: 18,
    marginTop: spacing.sm,
  },
});
