import React from "react";
import { View, Text, StyleSheet, Alert, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useQueryClient } from "@tanstack/react-query";
import { authStore } from "@/store/authStore";
import { authService } from "@/services/auth";
import { Button } from "@/components/Button";
import { colors } from "@/theme";
export default function ProfileScreen() {
  const user = authStore((s) => s.user);
  const queries = useQueryClient();
  const logout = async () => {
    try {
      const { error } = await authService.signOut();
      if (error) throw error;
      queries.clear();
    } catch {
      Alert.alert(
        "Could not sign out",
        "Please check your connection and try again.",
      );
    }
  };
  return (
    <SafeAreaView style={styles.page}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Your account</Text>
        <View style={styles.avatar}>
          <Text style={styles.initial}>
            {user?.email?.[0]?.toUpperCase() ?? "S"}
          </Text>
        </View>
        <Text style={styles.email}>{user?.email}</Text>
        <View style={styles.card}>
          <Text style={styles.heading}>3D stroke analysis</Text>
          <Text style={styles.text}>
            Review your motion, compare joint angles and explore a suggested
            correction on your own recording.
          </Text>
        </View>
        <View style={styles.card}>
          <Text style={styles.heading}>Private by default</Text>
          <Text style={styles.text}>
            Your recordings and results are accessible through your account.
            Sharing exports a video only when you choose to share it.
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
          onPress={() =>
            Alert.alert(
              "Sign out?",
              "Your completed analyses will remain in your account.",
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
  title: { fontSize: 28, fontWeight: "700", color: colors.text.primary },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 20,
    backgroundColor: colors.primaryMuted,
    alignItems: "center",
    justifyContent: "center",
  },
  initial: { fontSize: 28, color: colors.primary, fontWeight: "700" },
  email: { color: colors.text.primary, fontSize: 16 },
  card: {
    padding: 18,
    borderRadius: 16,
    backgroundColor: colors.surface,
    gap: 8,
  },
  heading: { color: colors.text.primary, fontWeight: "600", fontSize: 16 },
  text: { color: colors.text.secondary, lineHeight: 21, fontSize: 14 },
});
