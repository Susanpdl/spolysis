import { SafeAreaView } from "react-native-safe-area-context";
import React from "react";
import { View, Text, ScrollView, StyleSheet } from "react-native";
import { AuthScreenProps } from "@/navigation/types";
import { Button } from "@/components/Button";
import { GettingStarted } from "@/components/GettingStarted";
import { colors, typography, spacing } from "@/theme";

export default function WelcomeScreen({
  navigation,
}: AuthScreenProps<"Welcome">) {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
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

        <GettingStarted />

        <View style={styles.actions}>
          <Button
            title="Get Started"
            onPress={() => navigation.navigate("Signup")}
          />
          <Button
            title="Sign in"
            variant="secondary"
            onPress={() => navigation.navigate("Login")}
          />
          <Text style={styles.accountHint}>
            Create an account to save your analyses.
          </Text>
        </View>
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
    justifyContent: "space-between",
    paddingVertical: spacing.lg,
    gap: spacing.lg,
  },
  hero: { alignItems: "center", marginTop: spacing.md },
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
  actions: { gap: spacing.sm },
  accountHint: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: "center",
    marginTop: spacing.xs,
  },
});
