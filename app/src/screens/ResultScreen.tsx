import { SafeAreaView } from "react-native-safe-area-context";
import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Alert,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { RecordingScreenProps } from "@/navigation/types";
import { VideoPlayer } from "@/components/VideoPlayer";
import { Button } from "@/components/Button";
import { File, Paths } from "expo-file-system";
import * as Sharing from "expo-sharing";
import ThreeJSViewer, {
  SkeletonData,
  parseSkeleton,
} from "@/components/ThreeJSViewer";
import DeltaTable from "@/components/DeltaTable";
import { useJob } from "@/hooks/useJob";
import { colors, typography, spacing } from "@/theme";
import { recordingStore } from "@/store/recordingStore";

const STROKE_LABELS: Record<string, string> = {
  forehand: "Forehand",
  backhand: "Backhand",
  serve: "Serve",
  volley: "Volley",
};

const FAULT_LABELS: Record<string, string> = {
  late_contact: "Late contact",
  open_stance: "Open stance",
  low_follow_through: "Low follow-through",
  arm_only: "Arm-only swing",
  no_hip_rotation: "No hip rotation",
  grip_issue: "Grip inconsistency",
  no_trophy_position: "Missing trophy position",
  low_toss: "Low ball toss",
};

type ResultTab = "video" | "3d";

export default function ResultScreen({
  route,
  navigation,
}: RecordingScreenProps<"Result">) {
  const { jobId } = route.params;
  const { result, isLoadingJob, isLoadingResult, refetch, refetchResult } =
    useJob(jobId);
  const reset = recordingStore((s) => s.reset);

  const [activeTab, setActiveTab] = useState<ResultTab>("video");
  const [skeletonFrames, setSkeletonFrames] = useState<SkeletonData | null>(
    null,
  );
  const [skeletonLoading, setSkeletonLoading] = useState(false);
  const [mediaAttempt, setMediaAttempt] = useState(0);
  const [mediaRefreshing, setMediaRefreshing] = useState(false);
  const [mediaRefreshError, setMediaRefreshError] = useState<string | null>(
    null,
  );

  const retryMedia = async () => {
    if (mediaRefreshing) return;
    setMediaRefreshing(true);
    setMediaRefreshError(null);
    try {
      const response = await refetchResult();
      if (response.error) throw response.error;
      // A refresh may return the same signed URL, so remount the failed player
      // and retry the motion download even when the URL has not changed.
      setMediaAttempt((attempt) => attempt + 1);
    } catch {
      setMediaRefreshError(
        "Could not refresh the link. Check your connection and retry.",
      );
    } finally {
      setMediaRefreshing(false);
    }
  };

  useEffect(() => {
    setSkeletonFrames(null);
    if (!result?.skeleton_3d_url) return;
    let alive = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    setSkeletonLoading(true);
    fetch(result.skeleton_3d_url, { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error("Could not download motion");
        return r.json();
      })
      .then((data) => {
        const skeleton = parseSkeleton(data);
        if (alive) setSkeletonFrames(skeleton);
      })
      .catch(() => {
        if (alive) setSkeletonFrames(null);
      })
      .finally(() => {
        clearTimeout(timeout);
        if (alive) setSkeletonLoading(false);
      });
    return () => {
      alive = false;
      clearTimeout(timeout);
      controller.abort();
    };
  }, [jobId, result?.skeleton_3d_url, mediaAttempt]);

  const handleDone = () => {
    reset();
    navigation.navigate("Capture");
  };

  const handleShare = async () => {
    if (!result) return;
    if (!result.overlay_video_url) return;
    try {
      const target = new File(Paths.cache, `spolysis-${jobId}.mp4`);
      await File.downloadFileAsync(result.overlay_video_url, target, {
        idempotent: true,
      });
      await Sharing.shareAsync(target.uri, {
        mimeType: "video/mp4",
        UTI: "public.mpeg-4",
      });
    } catch {
      Alert.alert(
        "Sharing failed",
        "Please try again when your connection is available.",
      );
    }
  };

  if (isLoadingJob || isLoadingResult) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loading}>
          <ActivityIndicator color={colors.primary} size="large" />
          <Text style={[typography.body, { color: colors.text.secondary }]}>
            Loading result...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!result) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loading}>
          <Text
            style={[
              typography.h3,
              { color: colors.text.primary, marginBottom: spacing.sm },
            ]}
          >
            Could not load result
          </Text>
          <Text
            style={[
              typography.body,
              { color: colors.text.secondary, textAlign: "center" },
            ]}
          >
            Something went wrong fetching your analysis.
          </Text>
          <TouchableOpacity
            style={styles.doneBtn}
            onPress={() => void refetch()}
          >
            <Text style={styles.doneBtnText}>Try again</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const faultLabel = result.fault_label
    ? (FAULT_LABELS[result.fault_label] ?? result.fault_label)
    : null;
  const confidence = Math.round(result.confidence * 100);

  const hasMotionData =
    result.overlay_video_url != null ||
    result.skeleton_3d_url != null ||
    result.delta_summary != null;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={[typography.label, { color: colors.text.muted }]}>
              Selected stroke
            </Text>
            <Text style={[typography.h2, { color: colors.text.primary }]}>
              {STROKE_LABELS[result.stroke_type] ?? result.stroke_type}
            </Text>
          </View>
          <View style={styles.confidencePill}>
            <Text style={styles.confidenceText}>
              {confidence}% pose visibility
            </Text>
          </View>
        </View>

        {/* Fault chip */}
        {faultLabel && (
          <View style={styles.faultChip}>
            <Text style={styles.faultDot}>●</Text>
            <Text style={[typography.bodySmall, styles.faultText]}>
              Compare: {faultLabel.replace(/_/g, " ")}
            </Text>
          </View>
        )}

        {/* Result tabs */}
        {hasMotionData && (
          <View style={styles.tabBar}>
            <TouchableOpacity
              accessibilityRole="button"
              style={styles.tab}
              onPress={() => setActiveTab("video")}
            >
              <Text
                style={[
                  typography.label,
                  activeTab === "video"
                    ? styles.tabLabelActive
                    : styles.tabLabelInactive,
                ]}
              >
                Video
              </Text>
              {activeTab === "video" && <View style={styles.tabUnderline} />}
            </TouchableOpacity>
            <TouchableOpacity
              accessibilityRole="button"
              style={styles.tab}
              onPress={() => setActiveTab("3d")}
            >
              <Text
                style={[
                  typography.label,
                  activeTab === "3d"
                    ? styles.tabLabelActive
                    : styles.tabLabelInactive,
                ]}
              >
                3D View
              </Text>
              {activeTab === "3d" && <View style={styles.tabUnderline} />}
            </TouchableOpacity>
          </View>
        )}

        {/* Video tab */}
        {hasMotionData && activeTab === "video" && (
          <>
            <View style={styles.videoSection}>
              {result.overlay_video_url && (
                <View style={styles.videoBlock}>
                  <Text style={[typography.label, styles.sectionLabel]}>
                    Corrected overlay
                  </Text>
                  <VideoPlayer
                    key={`overlay:${mediaAttempt}:${result.overlay_video_url}`}
                    uri={result.overlay_video_url}
                    style={styles.videoOverlay}
                    onRetry={() => void retryMedia()}
                    retrying={mediaRefreshing}
                    retryError={mediaRefreshError}
                  />
                </View>
              )}
              {result.reference_clip_url && (
                <View style={styles.videoBlock}>
                  <Text style={[typography.label, styles.sectionLabel]}>
                    Reference motion
                  </Text>
                  <VideoPlayer
                    key={`reference:${mediaAttempt}:${result.reference_clip_url}`}
                    uri={result.reference_clip_url}
                    style={styles.videoReference}
                    onRetry={() => void retryMedia()}
                    retrying={mediaRefreshing}
                    retryError={mediaRefreshError}
                  />
                </View>
              )}
            </View>
          </>
        )}

        {/* 3D tab */}
        {hasMotionData && activeTab === "3d" && (
          <>
            <View style={styles.viewerSection}>
              {result.skeleton_3d_url ? (
                skeletonLoading ? (
                  <View style={styles.viewerPlaceholder}>
                    <ActivityIndicator color={colors.primary} />
                    <Text
                      style={[
                        typography.bodySmall,
                        { color: colors.text.secondary },
                      ]}
                    >
                      Loading 3D data...
                    </Text>
                  </View>
                ) : skeletonFrames ? (
                  <ThreeJSViewer
                    skeletonData={skeletonFrames}
                    style={styles.viewer}
                  />
                ) : (
                  <View style={styles.viewerPlaceholder}>
                    <Text
                      style={[
                        typography.bodySmall,
                        { color: colors.text.muted },
                      ]}
                    >
                      3D motion could not load
                    </Text>
                    <Text
                      style={styles.recoveryText}
                      accessibilityLiveRegion="polite"
                    >
                      {mediaRefreshError ??
                        "Check your connection, then retry to refresh the motion link."}
                    </Text>
                    <Button
                      title="Retry 3D view"
                      loading={mediaRefreshing}
                      onPress={() => void retryMedia()}
                    />
                  </View>
                )
              ) : (
                <View style={styles.viewerPlaceholder}>
                  <Text
                    style={[typography.bodySmall, { color: colors.text.muted }]}
                  >
                    This analysis has no 3D motion attached.
                  </Text>
                  <Button
                    title="Refresh analysis"
                    loading={mediaRefreshing}
                    onPress={() => void retryMedia()}
                  />
                </View>
              )}
            </View>
          </>
        )}

        {/* Joint angle comparison */}
        {result.delta_summary && result.fault_joints && (
          <DeltaTable
            deltaSummary={result.delta_summary}
            faultJoints={result.fault_joints}
          />
        )}

        {/* Coaching text */}
        <View style={styles.recommendationCard}>
          <Text style={[typography.label, styles.sectionLabel]}>
            Coaching note
          </Text>
          <Text style={[typography.body, styles.recommendationText]}>
            {result.recommendation}
          </Text>
        </View>

        {/* Actions */}
        <View style={styles.actions}>
          <TouchableOpacity
            accessibilityRole="button"
            style={styles.shareBtn}
            onPress={handleShare}
          >
            <Text style={styles.shareBtnText}>Share clip</Text>
          </TouchableOpacity>
          <TouchableOpacity
            accessibilityRole="button"
            style={styles.doneBtn}
            onPress={handleDone}
          >
            <Text style={styles.doneBtnText}>Record another</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.lg,
  },
  scroll: { padding: spacing.lg, gap: spacing.lg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: spacing.md,
  },
  confidencePill: {
    backgroundColor: colors.primaryMuted,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  confidenceText: { color: colors.primary, fontWeight: "700", fontSize: 13 },
  faultChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
    backgroundColor: colors.errorMuted,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 10,
    alignSelf: "flex-start",
  },
  faultDot: { color: colors.error, fontSize: 10 },
  faultText: { color: colors.error },
  tabBar: {
    flexDirection: "row",
    backgroundColor: colors.surface,
    borderRadius: 12,
    overflow: "hidden",
  },
  tab: {
    flex: 1,
    alignItems: "center",
    paddingVertical: spacing.sm + 2,
    position: "relative",
  },
  tabLabelActive: { color: colors.primary },
  tabLabelInactive: { color: colors.text.muted },
  tabUnderline: {
    position: "absolute",
    bottom: 0,
    left: "20%",
    right: "20%",
    height: 2,
    backgroundColor: colors.primary,
    borderRadius: 2,
  },
  videoSection: { gap: spacing.md },
  videoBlock: { gap: spacing.sm },
  sectionLabel: { color: colors.text.muted },
  videoOverlay: { height: 240, borderRadius: 14 },
  videoReference: { height: 200, borderRadius: 14 },
  viewerSection: {},
  viewer: { height: 420, borderRadius: 14, overflow: "hidden" },
  viewerPlaceholder: {
    height: 320,
    borderRadius: 14,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    padding: spacing.md,
  },
  recoveryText: {
    color: colors.text.secondary,
    textAlign: "center",
    lineHeight: 20,
  },
  recommendationCard: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: spacing.md,
    gap: spacing.sm,
    borderLeftWidth: 3,
    borderLeftColor: colors.primary,
  },
  recommendationText: { color: colors.text.primary, lineHeight: 24 },
  actions: { gap: spacing.sm, paddingBottom: spacing.xl },
  shareBtn: {
    backgroundColor: colors.primaryMuted,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.primary,
  },
  shareBtnText: { color: colors.primary, fontWeight: "700", fontSize: 15 },
  doneBtn: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  doneBtnText: { color: colors.text.inverse, fontWeight: "700", fontSize: 15 },
});
