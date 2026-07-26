import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import Video from 'react-native-video';

interface VideoPlayerProps {
  uri: string;
  style?: ViewStyle;
}

export function VideoPlayer({ uri, style }: VideoPlayerProps) {
  return (
    <View style={[styles.container, style]}>
      <Video
        source={{ uri }}
        style={styles.video}
        resizeMode="contain"
        repeat
        muted
        playInBackground={false}
        playWhenInactive={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: '#000', borderRadius: 12, overflow: 'hidden' },
  video: { width: '100%', height: '100%' },
});
