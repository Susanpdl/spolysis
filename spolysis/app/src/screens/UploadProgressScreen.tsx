import React, { useEffect, useRef, useState } from "react";
import { View, Text, StyleSheet, ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useQueryClient } from "@tanstack/react-query";
import { RecordingScreenProps } from "@/navigation/types";
import { ProgressBar } from "@/components/ProgressBar";
import { Button } from "@/components/Button";
import { useJob } from "@/hooks/useJob";
import { api } from "@/services/api";
import { createVideoUpload } from "@/services/upload";
import { colors } from "@/theme";

export default function UploadProgressScreen({
  route,
  navigation,
}: RecordingScreenProps<"UploadProgress">) {
  const [jobId, setJobId] = useState<string | null>(route.params.jobId ?? null);
  const [stage, setStage] = useState<"upload" | "confirm" | "analysis">(
    route.params.jobId ? "analysis" : "upload",
  );
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const uploaded = useRef<string | null>(null);
  const { job, result, jobError } = useJob(jobId);
  const queryClient = useQueryClient();
  useEffect(() => {
    if (route.params.jobId) return;
    let alive = true;
    let task: ReturnType<typeof createVideoUpload> | undefined;
    const run = async () => {
      setError(null);
      try {
        let id = uploaded.current;
        if (!id) {
          setStage("upload");
          setProgress(0);
          const {
            videoUri,
            strokeType,
            handedness,
            contentType = "video/mp4",
          } = route.params;
          if (!videoUri || !strokeType)
            throw new Error("Choose a video and stroke type first.");
          const response = await api.uploads.getUrl(
            "stroke.mp4",
            strokeType,
            handedness ?? "right",
            contentType,
          );
          if (!alive) return;
          id = response.job_id;
          setJobId(id);
          task = createVideoUpload(
            videoUri,
            response.upload_url,
            contentType,
            (p) => {
              if (alive) setProgress(p);
            },
          );
          const upload = await task.uploadAsync();
          if (!alive) return;
          if (!upload || upload.status < 200 || upload.status >= 300)
            throw new Error(
              "Video upload failed. Check your connection and retry.",
            );
          uploaded.current = id;
        }
        if (!alive) return;
        setStage("confirm");
        await api.uploads.confirm(id);
        if (alive) {
          setStage("analysis");
          void queryClient.invalidateQueries({ queryKey: ["jobs"] });
        }
      } catch (e) {
        if (alive)
          setError(
            e instanceof Error ? e.message : "Upload failed. Please try again.",
          );
      }
    };
    void run();
    return () => {
      alive = false;
      task?.cancel();
    };
  }, [attempt, route.params, queryClient]);
  useEffect(() => {
    if (job?.status === "completed" && result)
      navigation.replace("Result", { jobId: job.id });
  }, [job?.status, job?.id, result, navigation]);
  const failed = job?.status === "failed" || job?.status === "rejected";
  const message =
    error ??
    (failed
      ? (job.rejection_reason ??
        job.error_message ??
        "Analysis could not finish.")
      : jobError
        ? "Connection interrupted. We will keep checking."
        : stage === "upload"
          ? `Uploading video · ${Math.round(progress * 100)}%`
          : stage === "confirm"
            ? "Starting your analysis..."
            : job?.status === "pending"
              ? "Your analysis is queued."
              : "Reconstructing your stroke in 3D...");
  return (
    <SafeAreaView style={styles.page}>
      <View style={styles.card}>
        {!error && !failed && (
          <ActivityIndicator size="large" color={colors.primary} />
        )}
        <Text style={styles.title}>
          {error
            ? "Upload interrupted"
            : failed
              ? "Try another recording"
              : "Your stroke, in focus"}
        </Text>
        <Text style={styles.text}>{message}</Text>
        {stage === "upload" && !error && <ProgressBar progress={progress} />}
        {!error && !failed && (
          <Text style={styles.caption}>
            We check the recording, reconstruct your movement and compare the
            clearest swing with a reference. This can take several minutes.
          </Text>
        )}
        {error && (
          <Button title="Retry" onPress={() => setAttempt((a) => a + 1)} />
        )}
        {(failed || error) && (
          <Button
            title="Choose another video"
            variant="secondary"
            onPress={() => navigation.replace("Capture")}
          />
        )}
        {stage === "analysis" && !error && !failed && (
          <Button
            title="Back to analyses"
            variant="secondary"
            onPress={() => navigation.getParent()?.navigate("Home")}
          />
        )}
      </View>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: colors.background,
    justifyContent: "center",
    padding: 24,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 20,
    padding: 24,
    gap: 22,
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: colors.text.primary,
    textAlign: "center",
  },
  text: { color: colors.text.secondary, textAlign: "center", lineHeight: 22 },
  caption: {
    color: colors.text.muted,
    fontSize: 13,
    lineHeight: 20,
    textAlign: "center",
  },
});
