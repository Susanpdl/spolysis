import React, { useState } from "react";
import { useIsFocused } from "@react-navigation/native";
import { View, Text, StyleSheet, ViewStyle } from "react-native";
import Video from "react-native-video";

interface VideoPlayerProps {
  uri: string;
  style?: ViewStyle;
}

export function VideoPlayer({ uri, style }: VideoPlayerProps) {
  const focused = useIsFocused();
  const [failed, setFailed] = useState(false);
  return (
    <View style={[styles.container, style]}>
      {failed ? (
        <Text style={{ color: "#fff", padding: 24 }}>
          Video could not load. Reload this analysis to refresh its link.
        </Text>
      ) : (
        <Video
          source={{ uri }}
          style={styles.video}
          resizeMode="contain"
          controls
          paused={!focused}
          onError={() => setFailed(true)}
          repeat
          muted
          playInBackground={false}
          playWhenInactive={false}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: "#000", borderRadius: 12, overflow: "hidden" },
  video: { width: "100%", height: "100%" },
});
