import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
} from "react-native";
import { AuthScreenProps } from "@/navigation/types";
import { Button } from "@/components/Button";
import { CharacterPortrait } from "@/components/CharacterPortrait";
import { GettingStarted } from "@/components/GettingStarted";
import { LandingPreview } from "@/components/LandingPreview";
import { colors, typography, spacing } from "@/theme";

export default function WelcomeScreen({
  navigation,
}: AuthScreenProps<"Welcome">) {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <View style={styles.wordmark}>
            <View style={styles.logoMark}>
              <Text style={styles.logoText}>S</Text>
            </View>
            <Text style={styles.appName}>Spolysis</Text>
          </View>
          <TouchableOpacity
            accessibilityRole="button"
            onPress={() => navigation.navigate("Login")}
            style={styles.signInLink}
          >
            <Text style={styles.signInText}>Sign in</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.heroCard}>
          <View style={styles.heroTopline}>
            <Text style={styles.eyebrow}>TENNIS · MOTION REVIEW</Text>
            <CharacterPortrait character="pipkin" size={76} />
          </View>
          <Text accessibilityRole="header" style={styles.headline}>
            See the swing. Find your next move.
          </Text>
          <Text style={[typography.body, styles.tagline]}>
            Turn a practice clip into a clear 3D replay and one useful thing to
            work on.
          </Text>
          <Button
            title="Get Started"
            onPress={() => navigation.navigate("Signup")}
            style={styles.startButton}
          />
        </View>

        <LandingPreview />

        <GettingStarted />

        <Text style={styles.accountHint}>
          Create an account to save your analyses.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    flexGrow: 1,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    gap: spacing.md,
  },
  header: {
    minHeight: 44,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  wordmark: { flexDirection: "row", alignItems: "center", gap: 9 },
  logoMark: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: colors.mustard,
    alignItems: "center",
    justifyContent: "center",
  },
  logoText: {
    fontFamily: "Fraunces_600SemiBold",
    fontSize: 19,
    color: colors.text.primary,
  },
  appName: {
    color: colors.text.primary,
    fontFamily: "Fraunces_500Medium",
    fontSize: 21,
  },
  signInLink: {
    paddingHorizontal: 17,
    paddingVertical: 10,
    borderRadius: 999,
    backgroundColor: colors.surface,
  },
  signInText: {
    color: colors.text.primary,
    fontFamily: "DMSans_700Bold",
    fontSize: 13,
  },
  heroCard: {
    padding: spacing.lg,
    gap: spacing.md,
    borderRadius: 28,
    backgroundColor: colors.primaryMuted,
  },
  heroTopline: {
    minHeight: 76,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  eyebrow: {
    flex: 1,
    color: colors.primary,
    fontFamily: "DMSans_700Bold",
    fontSize: 10,
    letterSpacing: 0.8,
  },
  headline: {
    color: colors.text.primary,
    fontFamily: "Fraunces_500Medium",
    fontSize: 40,
    letterSpacing: -1.1,
    lineHeight: 44,
  },
  tagline: {
    color: colors.text.secondary,
    lineHeight: 23,
  },
  startButton: { marginTop: spacing.xs },
  accountHint: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: "center",
    paddingBottom: spacing.md,
  },
});
