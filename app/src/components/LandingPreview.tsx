import React from "react";
import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Ellipse, Line, Path, Rect } from "react-native-svg";

export function LandingPreview() {
  return (
    <View
      accessible
      accessibilityRole="image"
      accessibilityLabel="3D swing preview showing your movement, a suggested movement, and the ball path"
      style={styles.card}
    >
      <Svg
        pointerEvents="none"
        width="100%"
        height="100%"
        viewBox="0 0 360 208"
        preserveAspectRatio="xMidYMid slice"
      >
        <Rect width="360" height="208" rx="24" fill="#21163D" />
        <Path
          d="M-18 176 180 104l198 72M21 208l159-104 159 104M78 208l102-104 102 104M180 104v104M-5 183h370"
          fill="none"
          stroke="#B9A8E6"
          strokeOpacity=".28"
          strokeWidth="1.5"
        />
        <Path
          d="M178 70c36-37 72-39 112-25"
          fill="none"
          stroke="#FFC45C"
          strokeDasharray="5 7"
          strokeLinecap="round"
          strokeWidth="3"
        />
        <Circle cx="292" cy="45" r="7" fill="#C8EB45" />
        <Circle cx="292" cy="45" r="10" fill="none" stroke="#F5F0C7" />

        <Ellipse cx="170" cy="180" rx="35" ry="8" fill="#131025" />
        <Ellipse cx="198" cy="179" rx="33" ry="8" fill="#131025" />

        <Circle
          cx="145"
          cy="56"
          r="11"
          fill="none"
          stroke="#80BAFF"
          strokeOpacity=".82"
          strokeWidth="4"
        />
        <Path
          d="m145 69-1 38m-1-27-21 15m21-15 19-13m-18 40-15 35m15-35 18 30"
          fill="none"
          stroke="#80BAFF"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeOpacity=".8"
          strokeWidth="7"
        />
        <Path
          d="m132 80 24 8-5 25-23-8z"
          fill="none"
          stroke="#80BAFF"
          strokeOpacity=".6"
          strokeWidth="5"
        />

        <Circle cx="190" cy="48" r="12" fill="#E3C9A8" />
        <Circle cx="186" cy="46" r="1.6" fill="#281950" />
        <Circle cx="195" cy="46" r="1.6" fill="#281950" />
        <Path
          d="m187 52 4 2 4-2"
          fill="none"
          stroke="#805C50"
          strokeWidth="1.5"
        />
        <Path d="m175 65 29 1 8 46-45 1z" fill="#4DA77C" />
        <Path
          d="m175 72-20 17-18-3m57-14 17 12 16-14m-55 42-16 38-2 20m39-58 15 34-2 24"
          fill="none"
          stroke="#E3C9A8"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="9"
        />
        <Path d="m167 110 45 2-8 12-30-1z" fill="#6C5679" />
        <Circle
          cx="230"
          cy="71"
          r="18"
          fill="none"
          stroke="#EAE6D6"
          strokeWidth="3"
        />
        <Line
          x1="230"
          y1="88"
          x2="216"
          y2="111"
          stroke="#EAE6D6"
          strokeWidth="4"
        />
        <Line
          x1="216"
          y1="111"
          x2="207"
          y2="108"
          stroke="#EAE6D6"
          strokeWidth="4"
        />
        <Line
          x1="214"
          y1="75"
          x2="246"
          y2="66"
          stroke="#EAE6D6"
          strokeOpacity=".7"
          strokeWidth="1"
        />
        <Line
          x1="216"
          y1="82"
          x2="244"
          y2="74"
          stroke="#EAE6D6"
          strokeOpacity=".7"
          strokeWidth="1"
        />
      </Svg>

      <View style={styles.topLabel}>
        <Text style={styles.topLabelText}>A SWING, IN 3D</Text>
      </View>
      <View style={styles.legend}>
        <View style={styles.legendItem}>
          <View style={[styles.dot, styles.originalDot]} />
          <Text style={styles.legendText}>Your swing</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.dot, styles.suggestedDot]} />
          <Text style={styles.legendText}>Suggested</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    height: 208,
    borderRadius: 24,
    backgroundColor: "#21163D",
    overflow: "hidden",
  },
  topLabel: {
    position: "absolute",
    top: 12,
    left: 14,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: "rgba(255,255,255,0.12)",
  },
  topLabelText: {
    color: "#F6F3FF",
    fontFamily: "DMSans_700Bold",
    fontSize: 9,
    letterSpacing: 0.8,
  },
  legend: {
    position: "absolute",
    left: 14,
    bottom: 12,
    flexDirection: "row",
    gap: 12,
  },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 5 },
  dot: { width: 9, height: 9, borderRadius: 5 },
  originalDot: { backgroundColor: "#80BAFF" },
  suggestedDot: { backgroundColor: "#4DA77C" },
  legendText: {
    color: "#F6F3FF",
    fontFamily: "DMSans_600SemiBold",
    fontSize: 11,
  },
});
