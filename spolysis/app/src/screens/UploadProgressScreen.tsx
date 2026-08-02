import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { RecordingScreenProps } from '@/navigation/types';
import { ProgressBar } from '@/components/ProgressBar';
import { JobStatusBadge } from '@/components/JobStatusBadge';
import { useJob } from '@/hooks/useJob';
import { recordingStore } from '@/store/recordingStore';
import { api } from '@/services/api';
import { uploadService } from '@/services/upload';
import { colors, typography, spacing } from '@/theme';

export default function UploadProgressScreen({
  route,
  navigation,
}: RecordingScreenProps<'UploadProgress'>) {
  const { videoUri } = route.params;
  const { jobId, isUploading, uploadProgress, setJobId, setUploading, setUploadProgress, reset } =
    recordingStore();
  const { job, result } = useJob(jobId);
  const didStart = useRef(false);

  useEffect(() => {
    if (didStart.current) return;
    didStart.current = true;

    const run = async () => {
      try {
        setUploading(true);
        const filename = `recording_${Date.now()}.mp4`;
        const { upload_url, job_id } = await api.uploads.getUrl('free', filename);
        setJobId(job_id);
        await uploadService.upload(videoUri, upload_url, (p) => setUploadProgress(p));
        // Upload to R2 is complete - now tell the server to start the analysis workflow
        await api.uploads.confirm(job_id);
        setUploading(false);
      } catch (err: any) {
        setUploading(false);
        Alert.alert('Upload failed', err.message ?? 'Please try again.', [
          { text: 'OK', onPress: () => navigation.goBack() },
        ]);
      }
    };

    run();
  }, []);

  useEffect(() => {
    if (job?.status === 'completed' && result) {
      navigation.replace('Result', { jobId: job.id });
    }
  }, [job?.status, result]);

  const handleCancel = () => {
    reset();
    navigation.navigate('Record');
  };

  const statusMessage = (() => {
    if (isUploading) return `Uploading... ${Math.round(uploadProgress * 100)}%`;
    if (!jobId) return 'Preparing upload...';
    switch (job?.status) {
      case 'pending': return 'Queued for analysis...';
      case 'processing': return 'Analysing your stroke...';
      case 'failed': return 'Analysis failed.';
      case 'rejected': return job.rejection_reason ?? 'Video was rejected.';
      default: return 'Waiting...';
    }
  })();

  const isFailed = job?.status === 'failed' || job?.status === 'rejected';
  const phase = isUploading ? 'upload' : 'analysis';

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.inner}>
        <View style={styles.card}>
          {isFailed ? (
            <Text style={styles.failIcon}>⚠️</Text>
          ) : (
            <ActivityIndicator color={colors.primary} size="large" style={{ marginBottom: spacing.lg }} />
          )}

          <Text style={[typography.h3, styles.title]}>
            {isFailed ? 'Something went wrong' : phase === 'upload' ? 'Uploading' : 'Analysing'}
          </Text>
          <Text style={[typography.body, styles.subtitle]}>{statusMessage}</Text>

          {isUploading && (
            <View style={styles.progressWrap}>
              <ProgressBar progress={uploadProgress} />
            </View>
          )}

          {job && (
            <View style={styles.badgeRow}>
              <JobStatusBadge status={job.status} />
            </View>
          )}

          {isFailed && (
            <View style={styles.failActions}>
              {job?.status === 'rejected' && (
                <Text style={[typography.bodySmall, styles.rejectHint]}>
                  Make sure you are fully visible in frame, well-lit, and not moving too fast at
                  the start of recording.
                </Text>
              )}
              <TouchableOpacity style={styles.retryBtn} onPress={handleCancel}>
                <Text style={styles.retryText}>Record again</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>

        {!isFailed && (
          <TouchableOpacity onPress={handleCancel} style={styles.cancelBtn}>
            <Text style={styles.cancelText}>Cancel</Text>
          </TouchableOpacity>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  inner: { flex: 1, paddingHorizontal: spacing.lg, justifyContent: 'center', gap: spacing.xl },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: spacing.xl,
    alignItems: 'center',
  },
  failIcon: { fontSize: 48, marginBottom: spacing.lg },
  title: { color: colors.text.primary, marginBottom: spacing.sm, textAlign: 'center' },
  subtitle: { color: colors.text.secondary, textAlign: 'center' },
  progressWrap: { width: '100%', marginTop: spacing.lg },
  badgeRow: { marginTop: spacing.md },
  failActions: { width: '100%', gap: spacing.md, marginTop: spacing.lg, alignItems: 'center' },
  rejectHint: { color: colors.text.secondary, textAlign: 'center', lineHeight: 20 },
  retryBtn: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: spacing.xl,
  },
  retryText: { color: colors.text.inverse, fontWeight: '700', fontSize: 15 },
  cancelBtn: { alignSelf: 'center', paddingVertical: spacing.sm },
  cancelText: { color: colors.text.muted, fontSize: 15 },
});
