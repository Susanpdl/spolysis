import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from "react-native";
import { AuthScreenProps } from "@/navigation/types";
import { Button } from "@/components/Button";
import { CharacterPortrait } from "@/components/CharacterPortrait";
import { LandingPreview } from "@/components/LandingPreview";
import { colors } from "@/theme";

const steps = [
  { number: "01", title: "Bring your swing.", copy: "Record a practice clip or choose one from your camera roll." },
  { number: "02", title: "See it differently.", copy: "Explore your movement in 3D, slow it down, and compare suggested corrections." },
  { number: "03", title: "Take it to the court.", copy: "Leave with simple cues to focus on in your next practice." },
];

export default function WelcomeScreen({ navigation }: AuthScreenProps<"Welcome">) {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.wordmark}>spolysis<Text style={styles.wordmarkDot}>.</Text></Text>
          <TouchableOpacity accessibilityRole="button" onPress={() => navigation.navigate("Login")} style={styles.signIn}>
            <Text style={styles.signInText}>Sign in ↗</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.hero}>
          <View style={styles.eyebrowRow}>
            <View style={styles.dot} />
            <Text style={styles.eyebrow}>A FRESH PERSPECTIVE ON YOUR GAME</Text>
          </View>
          <Text accessibilityRole="header" style={styles.headline}>A little insight.{"\n"}<Text style={styles.headlineAccent}>A better swing.</Text></Text>
          <Text style={styles.tagline}>Meet your game from a new angle. Turn a tennis clip into a 3D replay you can learn from.</Text>
          <Button title="Find your next move  ↗" onPress={() => navigation.navigate("Signup")} style={styles.startButton} />
          <Text style={styles.heroHint}>Your video. Your movement. Your next step.</Text>
        </View>

        <View style={styles.illustration}>
          <LandingPreview />
          <Text style={styles.caption}>A new way to see the game you love.</Text>
        </View>

        <View style={styles.journey}>
          <Text style={styles.sectionEyebrow}>FROM PRACTICE TO PROGRESS</Text>
          <Text accessibilityRole="header" style={styles.sectionTitle}>Small discoveries.{"\n"}Something to build on.</Text>
          {steps.map((step) => (
            <View key={step.number} style={styles.step}>
              <Text style={styles.stepNumber}>{step.number}</Text>
              <View style={styles.stepCopy}>
                <Text style={styles.stepTitle}>{step.title}</Text>
                <Text style={styles.stepDescription}>{step.copy}</Text>
              </View>
            </View>
          ))}
        </View>

        <View style={styles.invitation}>
          <CharacterPortrait character="pipkin" size={68} />
          <View style={styles.invitationCopy}>
            <Text style={styles.invitationTitle}>Every swing starts somewhere.</Text>
            <Text style={styles.invitationText}>Tennis today. More ways to play on the way.</Text>
          </View>
        </View>
        <Text style={styles.footer}>SPOLYSIS · STAY CURIOUS. KEEP PLAYING.</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F3F6EE" },
  content: { flexGrow: 1, paddingBottom: 28 },
  header: { paddingHorizontal: 24, paddingTop: 12, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  wordmark: { fontFamily: "Fraunces_600SemiBold", fontSize: 29, letterSpacing: -1.2, color: colors.text.primary },
  wordmarkDot: { color: colors.primary },
  signIn: { minHeight: 44, paddingHorizontal: 18, justifyContent: "center", borderRadius: 24, borderWidth: 1, borderColor: "#D6E1D1", backgroundColor: "#FFFFFF80" },
  signInText: { fontFamily: "DMSans_600SemiBold", fontSize: 13, color: colors.text.primary },
  hero: { paddingHorizontal: 26, paddingTop: 42, paddingBottom: 25 },
  eyebrowRow: { flexDirection: "row", alignItems: "center", gap: 7, marginBottom: 21 },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.primary },
  eyebrow: { flexShrink: 1, fontFamily: "DMSans_700Bold", fontSize: 9, letterSpacing: 1.1, color: colors.primary },
  headline: { fontFamily: "Fraunces_500Medium", fontSize: 43, lineHeight: 48, letterSpacing: -1.6, color: colors.text.primary },
  headlineAccent: { color: colors.primary },
  tagline: { marginTop: 20, maxWidth: 360, fontFamily: "DMSans_400Regular", fontSize: 16, lineHeight: 25, color: colors.text.secondary },
  startButton: { marginTop: 25, borderRadius: 28 },
  heroHint: { marginTop: 12, textAlign: "center", fontFamily: "DMSans_400Regular", fontSize: 11, color: colors.text.secondary },
  illustration: { paddingHorizontal: 12 },
  caption: { textAlign: "center", marginTop: 12, fontFamily: "Fraunces_500Medium", fontSize: 13, color: colors.text.secondary },
  journey: { marginTop: 38, paddingHorizontal: 26 },
  sectionEyebrow: { fontFamily: "DMSans_700Bold", fontSize: 9, letterSpacing: 1.3, color: colors.primary },
  sectionTitle: { marginTop: 12, marginBottom: 10, fontFamily: "Fraunces_500Medium", fontSize: 29, lineHeight: 35, letterSpacing: -0.6, color: colors.text.primary },
  step: { flexDirection: "row", gap: 18, paddingVertical: 22, borderBottomWidth: 1, borderColor: "#DCE5D7" },
  stepNumber: { fontFamily: "Fraunces_500Medium", fontSize: 23, color: "#7B967C", width: 32 },
  stepCopy: { flex: 1, gap: 6 },
  stepTitle: { fontFamily: "DMSans_700Bold", fontSize: 16, color: colors.text.primary },
  stepDescription: { fontFamily: "DMSans_400Regular", fontSize: 14, lineHeight: 22, color: colors.text.secondary },
  invitation: { marginHorizontal: 20, marginTop: 28, padding: 16, borderRadius: 22, backgroundColor: "#E5EEDC", flexDirection: "row", alignItems: "center", gap: 14 },
  invitationCopy: { flex: 1, gap: 6 },
  invitationTitle: { fontFamily: "Fraunces_500Medium", fontSize: 20, lineHeight: 25, color: colors.text.primary },
  invitationText: { fontFamily: "DMSans_400Regular", fontSize: 12, lineHeight: 19, color: colors.text.secondary },
  footer: { marginTop: 28, textAlign: "center", fontFamily: "DMSans_600SemiBold", fontSize: 8, letterSpacing: 1.3, color: colors.text.muted },
});
