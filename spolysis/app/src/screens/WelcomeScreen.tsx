import { SafeAreaView } from "react-native-safe-area-context";
import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { AuthScreenProps } from "@/navigation/types";
import { Button } from "@/components/Button";
import { colors, typography, spacing } from "@/theme";

export default function WelcomeScreen({
  navigation,
}: AuthScreenProps<"Welcome">) {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.hero}>
          <View style={styles.logoMark}>
            <Text style={styles.logoText}>SP</Text>
          </View>
          <Text style={[typography.h1, styles.appName]}>Spolysis</Text>
          <Text style={[typography.body, styles.tagline]}>
            Explore your stroke in 3D and find a clearer path to better
            technique.
          </Text>
        </View>

        <View style={styles.featureList}>
          {[
            { icon: "🎾", text: "Record your stroke with guided framing" },
            { icon: "🧠", text: "Explore your movement in 3D" },
            {
              icon: "🏆",
              text: "Compare your technique and review corrections",
            },
          ].map(({ icon, text }) => (
            <View key={text} style={styles.featureRow}>
              <Text style={styles.featureIcon}>{icon}</Text>
              <Text style={[typography.bodySmall, styles.featureText]}>
                {text}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.actions}>
          <Button
            title="Create account"
            onPress={() => navigation.navigate("Signup")}
          />
          <Button
            title="Sign in"
            variant="secondary"
            onPress={() => navigation.navigate("Login")}
            style={{ marginTop: spacing.sm }}
          />
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    flex: 1,
    paddingHorizontal: spacing.lg,
    justifyContent: "space-between",
    paddingVertical: spacing.xl,
  },
  hero: { alignItems: "center", marginTop: spacing.xxl },
  logoMark: {
    width: 72,
    height: 72,
    borderRadius: 20,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing.md,
  },
  logoText: { fontSize: 28, fontWeight: "800", color: colors.text.inverse },
  appName: { color: colors.text.primary, marginBottom: spacing.sm },
  tagline: {
    color: colors.text.secondary,
    textAlign: "center",
    maxWidth: 280,
    lineHeight: 24,
  },
  featureList: { gap: spacing.md },
  featureRow: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  featureIcon: { fontSize: 20, width: 28, textAlign: "center" },
  featureText: { color: colors.text.secondary, flex: 1 },
  actions: { gap: 0 },
});
