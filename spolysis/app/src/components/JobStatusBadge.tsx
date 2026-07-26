import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography } from '@/theme';

type Status = 'pending' | 'processing' | 'completed' | 'failed' | 'rejected';

const STATUS_CONFIG: Record<Status, { label: string; bg: string; fg: string }> = {
  pending:    { label: 'Pending',    bg: colors.border,      fg: colors.text.secondary },
  processing: { label: 'Analyzing', bg: colors.primaryMuted, fg: colors.primary },
  completed:  { label: 'Done',      bg: colors.primaryMuted, fg: colors.primary },
  failed:     { label: 'Failed',    bg: colors.errorMuted,   fg: colors.error },
  rejected:   { label: 'Rejected',  bg: colors.errorMuted,   fg: colors.error },
};

export function JobStatusBadge({ status }: { status: Status }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  return (
    <View style={[styles.badge, { backgroundColor: cfg.bg }]}>
      <Text style={[typography.label, { color: cfg.fg }]}>{cfg.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
});
