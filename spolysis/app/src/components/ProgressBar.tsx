import React from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, { useAnimatedStyle, withTiming } from 'react-native-reanimated';
import { colors } from '@/theme';

interface ProgressBarProps {
  progress: number; // 0 to 1
}

export function ProgressBar({ progress }: ProgressBarProps) {
  const animStyle = useAnimatedStyle(() => ({
    width: `${withTiming(Math.min(Math.max(progress, 0), 1) * 100, { duration: 300 })}%` as `${number}%`,
  }));

  return (
    <View style={styles.track}>
      <Animated.View style={[styles.fill, animStyle]} />
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    height: 4,
    backgroundColor: colors.border,
    borderRadius: 2,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    backgroundColor: colors.primary,
    borderRadius: 2,
  },
});
