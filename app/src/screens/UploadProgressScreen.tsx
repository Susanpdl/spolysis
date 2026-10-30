import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useIsFocused } from "@react-navigation/native";
import { useQueryClient } from "@tanstack/react-query";
import { RecordingScreenProps } from "@/navigation/types";
import { ProgressBar } from "@/components/ProgressBar";
import { Button } from "@/components/Button";
import { useJob } from "@/hooks/useJob";
import { api, ApiError } from "@/services/api";
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
  const focused = useIsFocused();
  const [starting, setStarting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [videoUnavailable, setVideoUnavailable] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const uploaded = useRef<string | null>(null);
  const {
    job,
    result,
    jobError,
    resultError,
    isFetchingResult,
    refetchResult,
    refetch,
  } = useJob(jobId);
  const queryClient = useQueryClient();
  useEffect(() => {
    if (route.params.jobId) return;
    let alive = true;
    let task: ReturnType<typeof createVideoUpload> | undefined;
    const run = async () => {
      setError(null);
      setVideoUnavailable(false);
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
        if (alive) {
          if (uploaded.current && e instanceof ApiError && e.status === 400) {
            uploaded.current = null;
            setVideoUnavailable(true);
          }
          setError(
            e instanceof Error ? e.message : "Upload failed. Please try again.",
          );
        }
      }
    };
    void run();
    return () => {
      alive = false;
      task?.cancel();
    };
  }, [attempt, route.params, queryClient]);
  useEffect(() => {
    if (focused && job?.status === "completed" && result)
      navigation.replace("Result", { jobId: job.id });
  }, [focused, job?.status, job?.id, result, navigation]);
  const retryStart = async () => {
    if (!jobId || starting) return;
    setStarting(true);
    setError(null);
    try {
      await api.uploads.confirm(jobId);
      await refetch();
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    } catch (e) {
      if (e instanceof ApiError && e.status === 400) setVideoUnavailable(true);
      setError(
        e instanceof Error
          ? e.message
          : "Could not start analysis. Please retry.",
      );
    } finally {
      setStarting(false);
    }
  };
  const confirmationError = !!error && stage === "confirm" && !videoUnavailable;
  const awaitingStart = stage === "analysis" && job?.status === "pending";
  const canRetryStart =
    !!route.params.jobId && awaitingStart && !videoUnavailable;
  const failed = job?.status === "failed" || job?.status === "rejected";
  const resultUnavailable =
    job?.status === "completed" && !!resultError && !result;
  const message =
    error ??
    (resultUnavailable
      ? "Your analysis is saved, but its result could not be downloaded. Check your connection and retry. You do not need to upload again."
      : failed
        ? (job.rejection_reason ??
          job.error_message ??
          "Analysis could not finish.")
        : jobError
          ? "Connection interrupted. We will keep checking."
          : stage === "upload"
            ? `Uploading video · ${Math.round(progress * 100)}%`
            : stage === "confirm"
              ? "Starting your analysis..."
              : job?.status === "completed"
                ? "Loading your completed analysis..."
                : job?.status === "pending"
                  ? "Your analysis has not started yet."
                  : "Reconstructing your stroke in 3D...");
  return (
    <SafeAreaView style={styles.page}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.card}>
          {!error && !failed && !resultUnavailable && !awaitingStart && (
            <ActivityIndicator size="large" color={colors.primary} />
          )}
          <Text style={styles.title}>
            {videoUnavailable
              ? "Video needs to be uploaded again"
              : error
                ? confirmationError
                  ? "Video uploaded, analysis not started"
                  : canRetryStart
                    ? "Could not start analysis"
                    : "Upload interrupted"
                : resultUnavailable
                  ? "Analysis ready, result unavailable"
                  : failed
                    ? "Try another recording"
                    : awaitingStart
                      ? "Analysis not started"
                      : "Your stroke, in focus"}
          </Text>
          <Text style={styles.text}>{message}</Text>
          {stage === "upload" && !error && <ProgressBar progress={progress} />}
          {!error &&
            !failed &&
            !resultUnavailable &&
            !awaitingStart &&
            job?.status !== "completed" && (
              <Text style={styles.caption}>
                We check the recording, reconstruct your movement and compare
                the clearest swing with a reference. This can take several
                minutes.
              </Text>
            )}
          {confirmationError && (
            <Text style={styles.text}>
              Your video was uploaded. Retry starting the analysis without
              uploading it again.
            </Text>
          )}
          {videoUnavailable && (
            <Text style={styles.text}>
              {route.params.videoUri
                ? "Retry uploading the video you chose, or choose another recording."
                : "Choose your original video again to create a new analysis. Retrying the start request cannot restore the video."}
            </Text>
          )}
          {error && !route.params.jobId && (
            <Button
              title={
                confirmationError ? "Start analysis again" : "Retry upload"
              }
              onPress={() => setAttempt((a) => a + 1)}
            />
          )}
          {canRetryStart && (
            <>
              {!error && (
                <Text style={styles.caption}>
                  If your upload finished, retry starting this analysis. We will
                  check the saved video first.
                </Text>
              )}
              <Button
                title="Retry starting analysis"
                loading={starting}
                onPress={() => void retryStart()}
              />
            </>
          )}
          {resultUnavailable && (
            <Button
              title="Retry result"
              loading={isFetchingResult}
              onPress={() => void refetchResult()}
            />
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
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  page: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    flexGrow: 1,
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
