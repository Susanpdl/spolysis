import { SafeAreaView } from "react-native-safe-area-context";
import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity,
  Alert,
} from "react-native";
import { AuthScreenProps } from "@/navigation/types";
import { Button } from "@/components/Button";
import { colors, typography, spacing } from "@/theme";
import { authService } from "@/services/auth";

export default function LoginScreen({ navigation }: AuthScreenProps<"Login">) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email.trim() || !password) return;
    setLoading(true);
    let error: { message: string } | null = null;
    try {
      ({ error } = await authService.signIn(email.trim(), password));
    } catch {
      error = {
        message:
          "Unable to connect. Please check your connection and try again.",
      };
    }
    setLoading(false);
    if (error) Alert.alert("Sign in failed", error.message);
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        style={styles.inner}
      >
        <View style={styles.header}>
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityLabel="Back"
            onPress={() => navigation.goBack()}
            style={styles.backBtn}
          >
            <Text style={styles.backText}>← Back</Text>
          </TouchableOpacity>
          <Text style={[typography.h2, styles.title]}>Sign in</Text>
        </View>

        <View style={styles.form}>
          <View style={styles.field}>
            <Text style={[typography.label, styles.label]}>Email</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              placeholderTextColor={colors.text.muted}
              autoCapitalize="none"
              keyboardType="email-address"
              autoComplete="email"
            />
          </View>
          <View style={styles.field}>
            <Text style={[typography.label, styles.label]}>Password</Text>
            <TextInput
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              placeholderTextColor={colors.text.muted}
              secureTextEntry
              autoComplete="current-password"
            />
          </View>
          <Button
            title="Sign in"
            onPress={handleLogin}
            loading={loading}
            disabled={!email.trim() || !password}
            style={{ marginTop: spacing.sm }}
          />
        </View>

        <View style={styles.footer}>
          <Text
            style={[typography.bodySmall, { color: colors.text.secondary }]}
          >
            Don't have an account?{" "}
          </Text>
          <TouchableOpacity onPress={() => navigation.replace("Signup")}>
            <Text style={[typography.bodySmall, { color: colors.primary }]}>
              Create one
            </Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  inner: {
    flex: 1,
    paddingHorizontal: spacing.lg,
    justifyContent: "space-between",
    paddingVertical: spacing.xl,
  },
  header: { gap: spacing.md },
  backBtn: {
    alignSelf: "flex-start",
    backgroundColor: colors.surface,
    borderRadius: 999,
    paddingHorizontal: 15,
    paddingVertical: 10,
  },
  backText: {
    color: colors.primary,
    fontFamily: "DMSans_600SemiBold",
    fontSize: 14,
  },
  title: { color: colors.text.primary },
  form: {
    gap: spacing.md,
    padding: spacing.lg,
    borderRadius: 28,
    backgroundColor: colors.surface,
    shadowColor: "#281950",
    shadowOpacity: 0.04,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 6 },
    elevation: 1,
  },
  field: { gap: spacing.xs },
  label: { color: colors.text.secondary, letterSpacing: 0.5 },
  input: {
    backgroundColor: colors.background,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    paddingHorizontal: spacing.md,
    paddingVertical: 14,
    color: colors.text.primary,
    fontFamily: "DMSans_400Regular",
    fontSize: 16,
  },
  footer: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },
});
