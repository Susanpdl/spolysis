import React, { useState } from "react";
import { useIsFocused } from "@react-navigation/native";
import {
  View,
  Text,
  StyleSheet,
  ViewStyle,
  ActivityIndicator,
} from "react-native";
import Video from "react-native-video";
import { Button } from "@/components/Button";
import { colors } from "@/theme";

interface VideoPlayerProps {
  uri: string;
  style?: ViewStyle;
  onRetry: () => void;
  retrying: boolean;
  retryError: string | null;
}

export function VideoPlayer({
  uri,
  style,
  onRetry,
  retrying,
  retryError,
}: VideoPlayerProps) {
  const focused = useIsFocused();
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  return (
    <View
      style={[styles.container, style]}
      testID={loaded && !failed ? "Analysis video ready" : undefined}
    >
      {failed ? (
        <View style={styles.failure}>
          <Text style={styles.title}>Video could not load</Text>
          <Text style={styles.message} accessibilityLiveRegion="polite">
            {retryError ??
              "Check your connection, then retry to refresh the video link."}
          </Text>
          <Button title="Retry video" onPress={onRetry} loading={retrying} />
        </View>
      ) : (
        <>
          <Video
            source={{ uri }}
            style={styles.video}
            resizeMode="contain"
            controls
            paused={!focused}
            onError={() => setFailed(true)}
            onLoad={() => setLoaded(true)}
            repeat
            muted
            playInBackground={false}
            playWhenInactive={false}
          />
          {!loaded && (
            <View pointerEvents="none" style={styles.loading}>
              <ActivityIndicator
                color={colors.primary}
                accessibilityLabel="Loading video"
              />
            </View>
          )}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: "#000", borderRadius: 12, overflow: "hidden" },
  video: { width: "100%", height: "100%" },
  loading: {
    ...StyleSheet.absoluteFill,
    alignItems: "center",
    justifyContent: "center",
  },
  failure: { flex: 1, justifyContent: "center", padding: 16, gap: 12 },
  title: { color: colors.text.primary, fontWeight: "600", textAlign: "center" },
  message: {
    color: colors.text.secondary,
    textAlign: "center",
    lineHeight: 20,
  },
});
