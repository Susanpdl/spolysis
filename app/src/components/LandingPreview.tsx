import React from "react";
import { Image, StyleSheet } from "react-native";

export function LandingPreview() {
  return (
    <Image
      source={require("../../assets/illustrations/tennis-storybook.png")}
      accessibilityLabel="A cloud sprite swinging a tennis racket on a floating garden court, with an owl coach watching"
      resizeMode="contain"
      style={styles.artwork}
    />
  );
}

const styles = StyleSheet.create({
  artwork: {
    width: "100%",
    aspectRatio: 1.5,
    borderRadius: 24,
    backgroundColor: "#C4E9E2",
  },
});
