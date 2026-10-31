import { StyleSheet } from "react-native";

export const typography = StyleSheet.create({
  h1: {
    fontFamily: "Fraunces_500Medium",
    fontSize: 34,
    letterSpacing: -1,
  },
  h2: {
    fontFamily: "Fraunces_500Medium",
    fontSize: 30,
    letterSpacing: -0.8,
  },
  h3: { fontFamily: "Fraunces_500Medium", fontSize: 22 },
  body: {
    fontFamily: "DMSans_400Regular",
    fontSize: 16,
    fontWeight: "400",
    lineHeight: 24,
  },
  bodySmall: {
    fontFamily: "DMSans_400Regular",
    fontSize: 14,
    fontWeight: "400",
    lineHeight: 20,
  },
  caption: {
    fontFamily: "DMSans_400Regular",
    fontSize: 12,
    fontWeight: "400",
    lineHeight: 16,
  },
  label: {
    fontFamily: "DMSans_700Bold",
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  mono: { fontSize: 14, fontFamily: "monospace" },
});
