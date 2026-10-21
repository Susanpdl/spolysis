import React, { useRef, useState } from "react";
import { View, Text, ViewStyle, StyleSheet } from "react-native";
import { WebView } from "react-native-webview";
import { viewerHtml } from "@/generated/viewerHtml";

export interface SkeletonData {
  schema_version: number;
  fps: number;
  frames: [number, number, number][][];
  original_frames?: [number, number, number][][];
  contact_frame?: number;
}
export function parseSkeleton(data: unknown): SkeletonData {
  const value = data as SkeletonData;
  const validFrames = (frames: unknown): boolean =>
    Array.isArray(frames) &&
    frames.length > 0 &&
    frames.length <= 9000 &&
    frames.every(
      (frame) =>
        Array.isArray(frame) &&
        frame.length === 17 &&
        frame.every(
          (joint) =>
            Array.isArray(joint) &&
            joint.length === 3 &&
            joint.every((n) => typeof n === "number" && Number.isFinite(n)),
        ),
    );
  if (
    !value ||
    !validFrames(value.frames) ||
    !Number.isFinite(value.fps) ||
    value.fps <= 0 ||
    value.fps > 120 ||
    (value.original_frames &&
      (!validFrames(value.original_frames) ||
        value.original_frames.length !== value.frames.length))
  ) {
    throw new Error(
      "The 3D motion data is incomplete. Please reload your analysis.",
    );
  }
  return value;
}
export default function ThreeJSViewer({
  skeletonData,
  style,
}: {
  skeletonData: SkeletonData;
  style?: ViewStyle;
}) {
  const web = useRef<WebView>(null);
  const [error, setError] = useState<string | null>(null);
  const inject = () =>
    web.current?.injectJavaScript(
      `window.setSkeleton(${JSON.stringify(skeletonData)});true;`,
    );
  return (
    <View style={[styles.container, style]}>
      {error ? (
        <Text style={styles.error}>{error}</Text>
      ) : (
        <WebView
          ref={web}
          source={{ html: viewerHtml }}
          originWhitelist={["about:blank"]}
          scrollEnabled={false}
          javaScriptEnabled
          style={styles.web}
          onError={() => setError("Unable to load the 3D viewer.")}
          onShouldStartLoadWithRequest={(request) =>
            request.url === "about:blank"
          }
          onMessage={(event) => {
            try {
              const message = JSON.parse(event.nativeEvent.data);
              if (message.ready) inject();
              if (message.error) setError(message.error);
            } catch {
              setError("Unable to read the 3D viewer response.");
            }
          }}
        />
      )}
    </View>
  );
}
const styles = StyleSheet.create({
  container: {
    height: 420,
    borderRadius: 16,
    overflow: "hidden",
    backgroundColor: "#101914",
  },
  web: { backgroundColor: "#101914" },
  error: { color: "#eaf5ed", padding: 24 },
});
