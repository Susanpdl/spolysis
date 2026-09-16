import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Share,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { RecordingScreenProps } from '@/navigation/types';
import { VideoPlayer } from '@/components/VideoPlayer';
import { PremiumGate } from '@/components/PremiumGate';
import ThreeJSViewer, { SkeletonFrame } from '@/components/ThreeJSViewer';
import DeltaTable from '@/components/DeltaTable';
import { useJob } from '@/hooks/useJob';
import { colors, typography, spacing } from '@/theme';
import { recordingStore } from '@/store/recordingStore';

const STROKE_LABELS: Record<string, string> = {
  forehand: 'Forehand',
  backhand: 'Backhand',
  serve: 'Serve',
  volley: 'Volley',
};

const FAULT_LABELS: Record<string, string> = {
  late_contact: 'Late contact',
  open_stance: 'Open stance',
  low_follow_through: 'Low follow-through',
  arm_only: 'Arm-only swing',
  no_hip_rotation: 'No hip rotation',
  grip_issue: 'Grip inconsistency',
  no_trophy_position: 'Missing trophy position',
  low_toss: 'Low ball toss',
};

type PremiumTab = 'video' | '3d';

export default function ResultScreen({ route, navigation }: RecordingScreenProps<'Result'>) {
  const { jobId } = route.params;
  const { job, result, isLoadingJob, isLoadingResult } = useJob(jobId);
  const reset = recordingStore((s) => s.reset);

  const [activeTab, setActiveTab] = useState<PremiumTab>('video');
  const [skeletonFrames, setSkeletonFrames] = useState<SkeletonFrame[] | null>(null);
  const [skeletonLoading, setSkeletonLoading] = useState(false);

  useEffect(() => {
    if (!result?.skeleton_3d_url) return;
    setSkeletonLoading(true);
    fetch(result.skeleton_3d_url)
      .then((r) => r.json())
      .then((data) => {
        setSkeletonFrames(data);
        setSkeletonLoading(false);
      })
      .catch(() => {
        setSkeletonFrames(null);
        setSkeletonLoading(false);
      });
  }, [result?.skeleton_3d_url]);

  const handleDone = () => {
    reset();
    navigation.navigate('Record');
  };

  const handleShare = async () => {
    if (!result) return;
    const text = result.overlay_video_url ?? result.reference_clip_url;
    if (text) {
      await Share.share({ message: `Check out my tennis analysis from Spolysis!\n${text}` });
    }
  };

  if (isLoadingJob || isLoadingResult) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loading}>
          <ActivityIndicator color={colors.primary} size="large" />
          <Text style={[typography.body, { color: colors.text.secondary }]}>Loading result...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!result) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loading}>
          <Text style={[typography.h3, { color: colors.text.primary, marginBottom: spacing.sm }]}>
            Could not load result
          </Text>
          <Text style={[typography.body, { color: colors.text.secondary, textAlign: 'center' }]}>
            Something went wrong fetching your analysis.
          </Text>
          <TouchableOpacity style={styles.doneBtn} onPress={handleDone}>
            <Text style={styles.doneBtnText}>Try again</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const faultLabel = result.fault_label ? FAULT_LABELS[result.fault_label] ?? result.fault_label : null;
  const confidence = Math.round(result.confidence * 100);

  const isPremium = job?.tier === 'premium';
  const hasPremiumData =
    isPremium &&
    (result.overlay_video_url != null ||
      result.skeleton_3d_url != null ||
      result.delta_summary != null);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={[typography.label, { color: colors.text.muted }]}>Stroke detected</Text>
            <Text style={[typography.h2, { color: colors.text.primary }]}>
              {STROKE_LABELS[result.stroke_type] ?? result.stroke_type}
            </Text>
          </View>
          <View style={styles.confidencePill}>
            <Text style={styles.confidenceText}>{confidence}%</Text>
          </View>
        </View>

        {/* Fault chip */}
        {faultLabel && (
          <View style={styles.faultChip}>
            <Text style={styles.faultDot}>●</Text>
            <Text style={[typography.bodySmall, styles.faultText]}>Fault: {faultLabel}</Text>
          </View>
        )}

        {/* Premium tab switcher */}
        {hasPremiumData && (
          <View style={styles.tabBar}>
            <TouchableOpacity
              style={styles.tab}
              onPress={() => setActiveTab('video')}
            >
              <Text style={[typography.label, activeTab === 'video' ? styles.tabLabelActive : styles.tabLabelInactive]}>
                Video
              </Text>
              {activeTab === 'video' && <View style={styles.tabUnderline} />}
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.tab}
              onPress={() => setActiveTab('3d')}
            >
              <Text style={[typography.label, activeTab === '3d' ? styles.tabLabelActive : styles.tabLabelInactive]}>
                3D View
              </Text>
              {activeTab === '3d' && <View style={styles.tabUnderline} />}
            </TouchableOpacity>
          </View>
        )}

        {/* Video tab - premium */}
        {hasPremiumData && activeTab === 'video' && (
          <PremiumGate fallback={null}>
            <View style={styles.videoSection}>
              {result.overlay_video_url && (
                <View style={styles.videoBlock}>
                  <Text style={[typography.label, styles.sectionLabel]}>Corrected overlay</Text>
                  <VideoPlayer uri={result.overlay_video_url} style={styles.videoOverlay} />
                </View>
              )}
              {result.reference_clip_url && (
                <View style={styles.videoBlock}>
                  <Text style={[typography.label, styles.sectionLabel]}>Pro reference</Text>
                  <VideoPlayer uri={result.reference_clip_url} style={styles.videoReference} />
                </View>
              )}
            </View>
          </PremiumGate>
        )}

        {/* 3D tab - premium */}
        {hasPremiumData && activeTab === '3d' && (
          <PremiumGate fallback={null}>
            <View style={styles.viewerSection}>
              {result.skeleton_3d_url ? (
                skeletonLoading ? (
                  <View style={styles.viewerPlaceholder}>
                    <ActivityIndicator color={colors.primary} />
                    <Text style={[typography.bodySmall, { color: colors.text.secondary }]}>
                      Loading 3D data...
                    </Text>
                  </View>
                ) : skeletonFrames ? (
                  <ThreeJSViewer skeletonData={skeletonFrames} style={styles.viewer} />
                ) : (
                  <View style={styles.viewerPlaceholder}>
                    <Text style={[typography.bodySmall, { color: colors.text.muted }]}>
                      3D viewer loading...
                    </Text>
                  </View>
                )
              ) : (
                <View style={styles.viewerPlaceholder}>
                  <Text style={[typography.bodySmall, { color: colors.text.muted }]}>
                    3D viewer loading...
                  </Text>
                </View>
              )}
            </View>
          </PremiumGate>
        )}

        {/* Free tier: reference clip only (no tabs) */}
        {!hasPremiumData && result.reference_clip_url && (
          <View style={styles.videoSection}>
            <View style={styles.videoBlock}>
              <Text style={[typography.label, styles.sectionLabel]}>Pro technique</Text>
              <VideoPlayer uri={result.reference_clip_url} style={styles.videoReference} />
            </View>
          </View>
        )}

        {/* Delta table - premium only */}
        {isPremium && result.delta_summary && result.fault_joints && (
          <DeltaTable
            deltaSummary={result.delta_summary}
            faultJoints={result.fault_joints}
          />
        )}

        {/* Coaching text */}
        <View style={styles.recommendationCard}>
          <Text style={[typography.label, styles.sectionLabel]}>Coaching note</Text>
          <Text style={[typography.body, styles.recommendationText]}>{result.recommendation}</Text>
        </View>

        {/* Actions */}
        <View style={styles.actions}>
          <TouchableOpacity style={styles.shareBtn} onPress={handleShare}>
            <Text style={styles.shareBtnText}>Share clip</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.doneBtn} onPress={handleDone}>
            <Text style={styles.doneBtnText}>Record another</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.lg },
  scroll: { padding: spacing.lg, gap: spacing.lg },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
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
  confidenceText: { color: colors.primary, fontWeight: '700', fontSize: 13 },
  faultChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    backgroundColor: colors.errorMuted,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: 10,
    alignSelf: 'flex-start',
  },
  faultDot: { color: colors.error, fontSize: 10 },
  faultText: { color: colors.error },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    borderRadius: 12,
    overflow: 'hidden',
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: spacing.sm + 2,
    position: 'relative',
  },
  tabLabelActive: { color: colors.primary },
  tabLabelInactive: { color: colors.text.muted },
  tabUnderline: {
    position: 'absolute',
    bottom: 0,
    left: '20%',
    right: '20%',
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
  viewer: { height: 320, borderRadius: 14, overflow: 'hidden' },
  viewerPlaceholder: {
    height: 320,
    borderRadius: 14,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
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
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.primary,
  },
  shareBtnText: { color: colors.primary, fontWeight: '700', fontSize: 15 },
  doneBtn: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  doneBtnText: { color: colors.text.inverse, fontWeight: '700', fontSize: 15 },
});
