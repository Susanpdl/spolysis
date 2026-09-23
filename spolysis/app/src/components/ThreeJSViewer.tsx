import React from 'react';
import { View, Text, ViewStyle, StyleSheet } from 'react-native';

export interface SkeletonFrame {
  joints: [number, number, number][];
}

interface ThreeJSViewerProps {
  skeletonData: SkeletonFrame[];
  style?: ViewStyle;
}

export default function ThreeJSViewer({ skeletonData, style }: ThreeJSViewerProps) {
  return (
    <View style={[styles.container, style]}>
      <Text style={styles.text}>3D Viewer</Text>
      <Text style={styles.sub}>{skeletonData.length} frames</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#0a0a0a',
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#1a1a1a',
  },
  text: {
    color: '#00c853',
    fontSize: 16,
    fontWeight: '600',
  },
  sub: {
    color: '#666',
    fontSize: 12,
    marginTop: 4,
  },
});
