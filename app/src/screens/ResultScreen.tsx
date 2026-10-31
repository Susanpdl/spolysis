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
import { SwingCues, jointRoleLabel } from "@/components/SwingCues";
import { useJob } from "@/hooks/useJob";
import { colors, typography, spacing } from "@/theme";
import { recordingStore } from "@/store/recordingStore";

const STROKE_LABELS: Record<string, string> = {
  forehand: "Forehand",
  backhand: "Backhand",
  serve: "Serve",
  volley: "Volley",
};

type ResultTab = "video" | "3d";

export default function ResultScreen({
  route,
  navigation,
}: RecordingScreenProps<"Result">) {
  const { jobId } = route.params;
  const {
    result,
    job,
    isLoadingJob,
    isLoadingResult,
    refetch,
    refetchResult,
  } = useJob(jobId);
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
    navigation.navigate("Sports");
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

  const handedness = job?.handedness === "left" ? "left" : "right";
  const faultLabel = result.fault_label
    ? jointRoleLabel(result.fault_label, handedness)
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
              3D focus: {faultLabel}
            </Text>
          </View>
        )}

        <View style={styles.coachingCard}>
          <Text style={styles.coachingEyebrow}>WHAT TO REHEARSE</Text>
          <Text style={styles.coachingText}>{result.recommendation}</Text>
          <Text style={styles.limitsText}>
            Video-based estimates, not millimetre measurements or a clinical
            assessment. Contact is inferred from wrist motion.
          </Text>
        </View>

        {/* Result tabs */}
        {hasMotionData && (
          <View style={styles.tabBar}>
            <TouchableOpacity
              accessibilityRole="button"
              style={[styles.tab, activeTab === "video" && styles.tabActive]}
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
            </TouchableOpacity>
            <TouchableOpacity
              accessibilityRole="button"
              style={[styles.tab, activeTab === "3d" && styles.tabActive]}
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
            <View style={styles.motionGuide}>
              <Text style={[typography.h3, styles.motionGuideTitle]}>
                Follow the suggested swing
              </Text>
              <View style={styles.motionLegend}>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, styles.legendOriginal]} />
                  <Text style={styles.legendText}>Your swing</Text>
                </View>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, styles.legendSuggested]} />
                  <Text style={styles.legendText}>Suggested</Text>
                </View>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, styles.legendTrail]} />
                  <Text style={styles.legendText}>Racket path</Text>
                </View>
              </View>
              <Text style={styles.motionGuideText}>
                The green mannequin faces into the illustrative court. The gold
                line follows the racket grip. Play or scrub to follow the
                movement, or turn the view to inspect other angles. Court
                position is not tracked in your video.
              </Text>
              {!!result.fault_joints?.length && (
                <Text style={styles.focusGuideText}>
                  Violet rings mark the joints highlighted in this analysis.
                </Text>
              )}
            </View>
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
                    focusJoints={result.fault_joints ?? []}
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
            {result.skeleton_3d_url && result.delta_summary && (
              <SwingCues
                faultJoints={result.fault_joints ?? []}
                faultLabel={result.fault_label}
                faultPhase={result.fault_phase}
                handedness={handedness}
              />
            )}
          </>
        )}

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
  scroll: { padding: spacing.md, gap: spacing.md },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.surface,
    borderRadius: 24,
    padding: spacing.md,
    shadowColor: "#281950",
    shadowOpacity: 0.035,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 1,
  },
  confidencePill: {
    backgroundColor: "#E5F6EC",
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  confidenceText: {
    color: "#25804F",
    fontFamily: "DMSans_700Bold",
    fontSize: 12,
  },
  faultChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.xs,
    backgroundColor: "#F8EFE4",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 999,
    alignSelf: "flex-start",
  },
  faultDot: { color: colors.warning, fontSize: 10 },
  faultText: { color: colors.warning },
  coachingCard: {
    backgroundColor: colors.surface,
    borderRadius: 24,
    padding: spacing.md,
    gap: spacing.sm,
  },
  coachingEyebrow: {
    ...typography.label,
    color: colors.primary,
    fontSize: 10,
  },
  coachingText: {
    color: colors.text.primary,
    fontFamily: "DMSans_400Regular",
    fontSize: 16,
    lineHeight: 24,
  },
  limitsText: {
    color: colors.text.muted,
    fontFamily: "DMSans_400Regular",
    fontSize: 12,
    lineHeight: 18,
  },
  tabBar: {
    flexDirection: "row",
    backgroundColor: colors.surface,
    borderRadius: 999,
    overflow: "hidden",
    padding: 4,
  },
  tab: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 12,
    borderRadius: 999,
  },
  tabActive: { backgroundColor: colors.primary },
  tabLabelActive: {
    color: colors.text.inverse,
    fontFamily: "DMSans_700Bold",
  },
  tabLabelInactive: { color: colors.text.muted },
  videoSection: { gap: spacing.md },
  videoBlock: { gap: spacing.sm },
  sectionLabel: { color: colors.text.muted },
  videoOverlay: { height: 240, borderRadius: 24 },
  videoReference: { height: 200, borderRadius: 24 },
  motionGuide: {
    backgroundColor: colors.surface,
    borderRadius: 24,
    padding: spacing.md,
    gap: spacing.sm,
  },
  motionGuideTitle: { color: colors.text.primary },
  motionLegend: {
    flexDirection: "row",
    flexWrap: "wrap",
    columnGap: spacing.md,
    rowGap: spacing.sm,
  },
  legendItem: { flexDirection: "row", alignItems: "center", gap: spacing.xs },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendOriginal: {
    borderWidth: 2,
    borderColor: "#80baff",
    backgroundColor: "transparent",
  },
  legendSuggested: { backgroundColor: "#34A06A" },
  legendTrail: { backgroundColor: "#ffc45c" },
  legendText: {
    color: colors.text.secondary,
    fontFamily: "DMSans_600SemiBold",
    fontSize: 13,
  },
  motionGuideText: {
    color: colors.text.secondary,
    fontFamily: "DMSans_400Regular",
    lineHeight: 20,
  },
  focusGuideText: {
    color: colors.primary,
    fontFamily: "DMSans_600SemiBold",
    lineHeight: 18,
    fontSize: 12,
  },
  viewerSection: {},
  viewer: { height: 460, borderRadius: 24, overflow: "hidden" },
  viewerPlaceholder: {
    height: 320,
    borderRadius: 24,
    backgroundColor: colors.surface,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
    padding: spacing.md,
  },
  recoveryText: {
    color: colors.text.secondary,
    fontFamily: "DMSans_400Regular",
    textAlign: "center",
    lineHeight: 20,
  },
  actions: { gap: spacing.sm, paddingBottom: spacing.xl },
  shareBtn: {
    backgroundColor: colors.surface,
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.border,
  },
  shareBtnText: {
    color: colors.primary,
    fontFamily: "DMSans_700Bold",
    fontSize: 15,
  },
  doneBtn: {
    backgroundColor: colors.primary,
    borderRadius: 999,
    paddingVertical: 14,
    alignItems: "center",
  },
  doneBtnText: {
    color: colors.text.inverse,
    fontFamily: "DMSans_700Bold",
    fontSize: 15,
  },
});
