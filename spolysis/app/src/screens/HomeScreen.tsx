import React from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { api, Job } from '@/services/api';
import { JobStatusBadge } from '@/components/JobStatusBadge';
import { colors, typography, spacing } from '@/theme';
import type { RecordingStackParams } from '@/navigation/types';

type Nav = NativeStackNavigationProp<RecordingStackParams>;

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function JobRow({ job }: { job: Job }) {
  const navigation = useNavigation<Nav>();

  const handlePress = () => {
    if (job.status === 'completed') {
      navigation.navigate('Result', { jobId: job.id });
    }
  };

  return (
    <TouchableOpacity
      style={styles.row}
      onPress={handlePress}
      disabled={job.status !== 'completed'}
      activeOpacity={job.status === 'completed' ? 0.7 : 1}
    >
      <View style={styles.rowLeft}>
        <View style={styles.tierBadge}>
          <Text style={styles.tierText}>{job.tier === 'premium' ? '3D' : '2D'}</Text>
        </View>
        <View>
          <Text style={[typography.body, styles.rowTitle]}>
            {job.tier === 'premium' ? 'Premium analysis' : 'Free analysis'}
          </Text>
          <Text style={[typography.caption, styles.rowDate]}>{formatDate(job.created_at)}</Text>
        </View>
      </View>
      <JobStatusBadge status={job.status} />
    </TouchableOpacity>
  );
}

export default function HomeScreen() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => api.jobs.list(1),
    refetchInterval: 5000,
  });

  const jobs = data?.jobs ?? [];

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={[typography.h2, { color: colors.text.primary }]}>Your analyses</Text>
        <Text style={[typography.caption, { color: colors.text.muted }]}>
          {data?.total ?? 0} total
        </Text>
      </View>

      {isLoading && (
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
        </View>
      )}

      {isError && (
        <View style={styles.center}>
          <Text style={[typography.body, { color: colors.text.secondary }]}>
            Couldn't load analyses.
          </Text>
          <TouchableOpacity onPress={() => refetch()} style={styles.retryBtn}>
            <Text style={{ color: colors.primary }}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      {!isLoading && jobs.length === 0 && !isError && (
        <View style={styles.empty}>
          <Text style={styles.emptyIcon}>🎾</Text>
          <Text style={[typography.h3, { color: colors.text.primary, textAlign: 'center' }]}>
            No analyses yet
          </Text>
          <Text style={[typography.body, styles.emptySubtitle]}>
            Tap Record to analyse your first stroke.
          </Text>
        </View>
      )}

      <FlatList
        data={jobs}
        keyExtractor={(j) => j.id}
        renderItem={({ item }) => <JobRow job={item} />}
        contentContainerStyle={styles.list}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  header: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.md,
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
  },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.md },
  retryBtn: { paddingVertical: spacing.sm },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.md, paddingHorizontal: spacing.xl },
  emptyIcon: { fontSize: 48 },
  emptySubtitle: { color: colors.text.secondary, textAlign: 'center' },
  list: { paddingHorizontal: spacing.lg, paddingBottom: spacing.lg },
  row: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  rowLeft: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  tierBadge: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: colors.primaryMuted,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tierText: { color: colors.primary, fontWeight: '700', fontSize: 13 },
  rowTitle: { color: colors.text.primary },
  rowDate: { color: colors.text.muted, marginTop: 2 },
  separator: { height: spacing.sm },
});
