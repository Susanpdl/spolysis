import React, { useEffect, useRef } from "react";
import { Animated, View, StyleSheet } from "react-native";
import { colors } from "@/theme";

export function ProgressBar({ progress }: { progress: number }) {
  const value = useRef(new Animated.Value(0)).current;
  const clamped = Math.min(Math.max(progress, 0), 1);
  useEffect(() => {
    const animation = Animated.timing(value, {
      toValue: clamped,
      duration: 250,
      useNativeDriver: false,
    });
    animation.start();
    return () => animation.stop();
  }, [clamped, value]);
  return (
    <View
      style={styles.track}
      accessibilityRole="progressbar"
      accessibilityLabel="Video upload"
      accessibilityValue={{ min: 0, max: 100, now: Math.round(clamped * 100) }}
    >
      <Animated.View
        style={[
          styles.fill,
          {
            width: value.interpolate({
              inputRange: [0, 1],
              outputRange: ["0%", "100%"],
            }),
          },
        ]}
      />
    </View>
  );
}
const styles = StyleSheet.create({
  track: {
    height: 4,
    backgroundColor: colors.border,
    borderRadius: 2,
    overflow: "hidden",
  },
  fill: { height: "100%", backgroundColor: colors.primary, borderRadius: 2 },
});
