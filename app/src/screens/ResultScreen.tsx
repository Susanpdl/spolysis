import React from 'react';
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

export default function ResultScreen({ route, navigation }: RecordingScreenProps<'Result'>) {
  const { jobId } = route.params;
  const { job, result, isLoadingJob, isLoadingResult } = useJob(jobId);
  const reset = recordingStore((s) => s.reset);

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

        {/* Premium: overlay video */}
        <PremiumGate
          fallback={null}
        >
          {result.overlay_video_url && (
            <View style={styles.videoSection}>
              <Text style={[typography.label, styles.sectionLabel]}>Corrected overlay</Text>
              <VideoPlayer uri={result.overlay_video_url} style={styles.video} />
            </View>
          )}
        </PremiumGate>

        {/* Reference clip */}
        {result.reference_clip_url && (
          <View style={styles.videoSection}>
            <Text style={[typography.label, styles.sectionLabel]}>
              {job?.tier === 'premium' ? 'Pro reference' : 'Pro technique'}
            </Text>
            <VideoPlayer uri={result.reference_clip_url} style={styles.video} />
          </View>
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
  videoSection: { gap: spacing.sm },
  sectionLabel: { color: colors.text.muted },
  video: { height: 220, borderRadius: 14 },
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
