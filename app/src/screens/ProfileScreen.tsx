import React, { useState } from "react";
import { View, Text, StyleSheet, Alert, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { authStore } from "@/store/authStore";
import { authService } from "@/services/auth";
import { Button } from "@/components/Button";
import { colors, typography } from "@/theme";
export default function ProfileScreen() {
  const user = authStore((s) => s.user);
  const [signingOut, setSigningOut] = useState(false);
  const logout = async () => {
    if (signingOut) return;
    setSigningOut(true);
    try {
      const { error } = await authService.signOut();
      if (error) throw error;
    } catch {
      if (authStore.getState().accessToken) {
        Alert.alert(
          "Could not sign out",
          "Please check your connection and try again.",
        );
      } else {
        Alert.alert(
          "Signed out on this device",
          "Your local session was removed. We could not confirm sign-out with the service, so other sessions may still be active.",
        );
      }
    } finally {
      setSigningOut(false);
    }
  };
  return (
    <SafeAreaView style={styles.page}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={[typography.h2, styles.title]}>Your account</Text>
        <View style={styles.avatar}>
          <Text style={styles.initial}>
            {user?.email?.[0]?.toUpperCase() ?? "S"}
          </Text>
        </View>
        <Text style={styles.email}>{user?.email}</Text>
        <View style={styles.card}>
          <Text style={styles.heading}>Sports movement analysis</Text>
          <Text style={styles.text}>
            Tennis is the first available sport. Review your motion, compare
            joint angles, and explore a suggested correction on your recording.
          </Text>
        </View>
        <View style={styles.card}>
          <Text style={styles.heading}>Your recordings and data</Text>
          <Text style={styles.text}>
            Videos you submit are uploaded for cloud analysis. Your account
            gives you access to your recordings and results. Sharing exports a
            video when you choose to share it.
          </Text>
          <Text style={styles.text}>
            Signing out does not delete your uploaded videos, results, or
            account. Deleting recordings or your account is not currently
            available in the app.
          </Text>
        </View>
        <View style={styles.card}>
          <Text style={styles.heading}>About the reference motion</Text>
          <Text style={styles.text}>
            Reference motion comes from the Tennis-MoCap research dataset,
            provided under CC BY-SA 3.0. Comparisons use regional
            high-performance players. Single-camera 3D estimates are a practice
            aid, not precise measurements.
          </Text>
        </View>
        <Button
          title="Sign out"
          variant="secondary"
          loading={signingOut}
          onPress={() =>
            Alert.alert(
              "Sign out?",
              "Signing out does not delete your uploaded videos, results, or account.",
              [
                { text: "Cancel", style: "cancel" },
                { text: "Sign out", onPress: logout },
              ],
            )
          }
        />
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.background },
  content: { padding: 24, gap: 20 },
  title: { color: colors.text.primary },
  avatar: {
    width: 76,
    height: 76,
    borderRadius: 26,
    backgroundColor: colors.primaryMuted,
    alignItems: "center",
    justifyContent: "center",
  },
  initial: {
    fontFamily: "Fraunces_500Medium",
    fontSize: 30,
    color: colors.primary,
  },
  email: {
    color: colors.text.primary,
    fontFamily: "DMSans_600SemiBold",
    fontSize: 16,
  },
  card: {
    padding: 20,
    borderRadius: 24,
    backgroundColor: colors.surface,
    gap: 8,
  },
  heading: {
    color: colors.text.primary,
    fontFamily: "DMSans_700Bold",
    fontSize: 15,
  },
  text: {
    color: colors.text.secondary,
    fontFamily: "DMSans_400Regular",
    lineHeight: 21,
    fontSize: 14,
  },
});
