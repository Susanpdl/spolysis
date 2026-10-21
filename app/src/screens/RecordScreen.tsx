import React, { useEffect, useRef, useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Linking,
  AppState,
  ScrollView,
} from "react-native";
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
} from "react-native-vision-camera";
import { useIsFocused } from "@react-navigation/native";
import { SafeAreaView } from "react-native-safe-area-context";
import * as ImagePicker from "expo-image-picker";
import { RecordingScreenProps } from "@/navigation/types";
import { BodyOutline } from "@/components/BodyOutline";
import { Button } from "@/components/Button";
import { useLivePose } from "@/hooks/useLivePose";
import { usePoseValidation } from "@/hooks/usePoseValidation";
import { StrokeType } from "@/services/api";
import { colors, spacing } from "@/theme";

type Phase = "preview" | "countdown" | "recording" | "stopping";
export default function RecordScreen({
  navigation,
}: RecordingScreenProps<"Capture">) {
  const { hasPermission, requestPermission } = useCameraPermission();
  const device = useCameraDevice("back");
  const focused = useIsFocused();
  const camera = useRef<Camera>(null);
  const [phase, setPhase] = useState<Phase>("preview");
  const phaseRef = useRef<Phase>("preview");
  const [seconds, setSeconds] = useState(0);
  const [count, setCount] = useState(3);
  const [strokeType, setStroke] = useState<StrokeType>("forehand");
  const [handedness, setHand] = useState<"right" | "left">("right");
  const [active, setActive] = useState(true);
  const [initialized, setInitialized] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const { frameProcessor, pose, available } = useLivePose(
    focused && phase === "preview",
  );
  const validation = usePoseValidation(pose);
  const setRecordingPhase = useCallback((next: Phase) => {
    phaseRef.current = next;
    setPhase(next);
  }, []);
  const stop = useCallback(async () => {
    if (phaseRef.current !== "recording") return;
    setRecordingPhase("stopping");
    try {
      await camera.current?.stopRecording();
    } catch {
      setRecordingPhase("preview");
      Alert.alert("Recording stopped", "Please record your stroke again.");
    }
  }, [setRecordingPhase]);
  useEffect(() => {
    const sub = AppState.addEventListener("change", (state) => {
      setActive(state === "active");
      if (state !== "active") {
        if (phaseRef.current === "recording") void stop();
        else setRecordingPhase("preview");
      }
    });
    return () => sub.remove();
  }, [stop, setRecordingPhase]);
  useEffect(() => {
    if (!focused) {
      if (phaseRef.current === "recording") void stop();
      else setRecordingPhase("preview");
    }
  }, [focused, stop, setRecordingPhase]);
  useEffect(() => {
    if (phase !== "countdown") return;
    if (count > 0) {
      const timer = setTimeout(() => setCount((c) => c - 1), 1000);
      return () => clearTimeout(timer);
    }
    if (!camera.current || !focused || !active) {
      setRecordingPhase("preview");
      return;
    }
    setSeconds(0);
    setRecordingPhase("recording");
    try {
      camera.current.startRecording({
        fileType: "mp4",
        onRecordingFinished: (video) => {
          setRecordingPhase("preview");
          navigation.navigate("UploadProgress", {
            videoUri: `file://${video.path}`,
            strokeType,
            handedness,
            contentType: "video/mp4",
          });
        },
        onRecordingError: (error) => {
          setRecordingPhase("preview");
          Alert.alert("Recording failed", error.message);
        },
      });
    } catch {
      setRecordingPhase("preview");
      Alert.alert("Recording failed", "Please try again.");
    }
  }, [
    phase,
    count,
    focused,
    active,
    strokeType,
    handedness,
    navigation,
    setRecordingPhase,
  ]);
  useEffect(() => {
    if (phase !== "recording") return;
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [phase]);
  useEffect(() => {
    if (seconds >= 300 && phase === "recording") void stop();
  }, [seconds, phase, stop]);
  useEffect(
    () => () => {
      if (phaseRef.current === "recording")
        void camera.current?.cancelRecording();
    },
    [],
  );
  const importVideo = async () => {
    try {
      const permission =
        await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        Alert.alert(
          "Photo access needed",
          "Allow photo access in Settings to choose a video.",
        );
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["videos"],
        allowsEditing: false,
        videoMaxDuration: 300,
      });
      if (result.canceled) return;
      const asset = result.assets[0];
      if (
        asset.duration &&
        (asset.duration > 300000 || asset.duration < 1000)
      ) {
        Alert.alert(
          "Choose a shorter clip",
          "Videos must be between 1 second and 5 minutes.",
        );
        return;
      }
      if (asset.fileSize && asset.fileSize > 500 * 1024 * 1024) {
        Alert.alert("Video is too large", "Choose a video under 500 MB.");
        return;
      }
      navigation.navigate("UploadProgress", {
        videoUri: asset.uri,
        strokeType,
        handedness,
        contentType:
          asset.mimeType === "video/quicktime"
            ? "video/quicktime"
            : "video/mp4",
      });
    } catch {
      Alert.alert("Could not open video", "Please try again.");
    }
  };
  const ready = initialized && validation.isValid && available;
  const cameraVisible = hasPermission && !!device && !cameraError;
  return (
    <SafeAreaView style={styles.page}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>Your next better stroke</Text>
        <Text style={styles.subtitle}>
          Record one clear swing. Review your motion in 3D.
        </Text>
        <View style={styles.options}>
          {(["forehand", "backhand", "serve", "volley"] as StrokeType[]).map(
            (stroke) => (
              <TouchableOpacity
                accessibilityRole="button"
                accessibilityState={{
                  selected: strokeType === stroke,
                  disabled: phase !== "preview",
                }}
                disabled={phase !== "preview"}
                key={stroke}
                onPress={() => setStroke(stroke)}
                style={[
                  styles.choice,
                  strokeType === stroke && styles.selected,
                ]}
              >
                <Text style={styles.choiceText}>
                  {stroke[0].toUpperCase() + stroke.slice(1)}
                </Text>
              </TouchableOpacity>
            ),
          )}
        </View>
        <View style={styles.options}>
          {(["right", "left"] as const).map((hand) => (
            <TouchableOpacity
              accessibilityRole="button"
              accessibilityState={{ selected: handedness === hand }}
              disabled={phase !== "preview"}
              key={hand}
              style={[styles.choice, handedness === hand && styles.selected]}
              onPress={() => setHand(hand)}
            >
              <Text style={styles.choiceText}>
                {hand === "right" ? "Right-handed" : "Left-handed"}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
        <View style={[styles.preview, !cameraVisible && styles.previewEmpty]}>
          {cameraVisible ? (
            <>
              <Camera
                ref={camera}
                style={StyleSheet.absoluteFill}
                device={device!}
                isActive={focused && active}
                video
                audio={false}
                frameProcessor={available ? frameProcessor : undefined}
                onInitialized={() => setInitialized(true)}
                onError={(e) => setCameraError(e.message)}
              />
              <View pointerEvents="none" style={styles.outline}>
                <BodyOutline
                  width={180}
                  height={300}
                  valid={validation.isValid}
                />
              </View>
              <View style={styles.status}>
                <Text style={styles.statusText}>
                  {phase === "countdown"
                    ? `${count}`
                    : phase === "recording"
                      ? `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")} recording`
                      : available
                        ? validation.instructionText
                        : "Live framing is unavailable. Import a video below."}
                </Text>
              </View>
            </>
          ) : (
            <View style={styles.cameraEmpty}>
              <Text style={styles.emptyTitle}>
                {!hasPermission
                  ? "Set up your camera"
                  : cameraError
                    ? "Camera unavailable"
                    : "Import a tennis video"}
              </Text>
              <Text style={styles.subtitle}>
                {!hasPermission
                  ? "Allow camera access for guided recording."
                  : "You can analyse an existing recording from your photo library."}
              </Text>
              {!hasPermission && (
                <Button
                  title="Enable camera"
                  onPress={async () => {
                    if (!(await requestPermission()))
                      await Linking.openSettings();
                  }}
                />
              )}
            </View>
          )}
        </View>
        <Text style={styles.hint}>
          Keep your head, racket hand and feet in frame. Use a steady camera,
          good light and a slight side view. We analyse the clearest swing in
          your clip.
        </Text>
        {cameraVisible && (
          <Button
            title={
              phase === "recording"
                ? "Stop recording"
                : phase === "countdown"
                  ? `Starting in ${count}...`
                  : phase === "stopping"
                    ? "Saving recording..."
                    : "Record stroke"
            }
            disabled={phase === "preview" ? !ready : phase !== "recording"}
            onPress={() => {
              if (phase === "recording") void stop();
              else {
                setCount(3);
                setRecordingPhase("countdown");
              }
            }}
          />
        )}
        <Button
          title="Choose a video"
          variant="secondary"
          disabled={phase !== "preview"}
          onPress={importVideo}
        />
        <Text style={styles.hint}>
          Up to 5 minutes · MP4 or MOV · Private to your account
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.lg, gap: 16 },
  title: { color: colors.text.primary, fontSize: 26, fontWeight: "700" },
  subtitle: { color: colors.text.secondary, lineHeight: 22 },
  options: { flexDirection: "row", gap: 8, flexWrap: "wrap" },
  choice: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
  },
  selected: {
    backgroundColor: colors.primaryMuted,
    borderColor: colors.primary,
  },
  choiceText: { color: colors.text.primary, fontSize: 13 },
  preview: {
    height: 380,
    borderRadius: 20,
    overflow: "hidden",
    backgroundColor: colors.surface,
  },
  previewEmpty: { height: 220 },
  outline: {
    ...StyleSheet.absoluteFill,
    alignItems: "center",
    justifyContent: "center",
  },
  status: {
    position: "absolute",
    bottom: 12,
    left: 12,
    right: 12,
    padding: 12,
    backgroundColor: "#102018dd",
    borderRadius: 12,
  },
  statusText: { color: "#fff", textAlign: "center", fontWeight: "600" },
  cameraEmpty: { flex: 1, justifyContent: "center", padding: 24, gap: 18 },
  emptyTitle: { color: colors.text.primary, fontSize: 22, fontWeight: "600" },
  hint: { color: colors.text.muted, fontSize: 12, lineHeight: 18 },
});
