import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, typography, spacing } from '@/theme';

interface DeltaTableProps {
  deltaSummary: Record<string, number>;
  faultJoints: string[];
}

function toTitleCase(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function deltaColor(delta: number, isFault: boolean): string {
  if (isFault || Math.abs(delta) >= 20) return colors.error;
  if (Math.abs(delta) >= 10) return colors.warning;
  return colors.text.muted;
}

export default function DeltaTable({ deltaSummary, faultJoints }: DeltaTableProps) {
  const sorted = Object.entries(deltaSummary).sort(
    ([, a], [, b]) => Math.abs(b) - Math.abs(a),
  );

  return (
    <View style={styles.card}>
      <Text style={[typography.label, styles.title]}>Biomechanical analysis</Text>

      {sorted.map(([joint, delta]) => {
        const isFault = faultJoints.includes(joint);
        const sign = delta >= 0 ? '+' : '';
        const formatted = `${sign}${Math.round(delta)}°`;
        const textColor = deltaColor(delta, isFault);

        return (
          <View key={joint} style={[styles.row, isFault && styles.rowFault]}>
            <View style={styles.jointCell}>
              {isFault && <Text style={styles.faultMarker}>●</Text>}
              <Text style={[typography.bodySmall, styles.jointName]}>{toTitleCase(joint)}</Text>
            </View>
            <Text style={[typography.bodySmall, { color: textColor, fontWeight: '700' }]}>
              {formatted}
            </Text>
          </View>
        );
      })}

      <View style={styles.legendRow}>
        <Text style={[typography.caption, styles.legendText]}>● Fault detected</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: spacing.md,
    gap: spacing.xs,
  },
  title: {
    color: colors.text.muted,
    marginBottom: spacing.sm,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
    borderRadius: 8,
  },
  rowFault: {
    backgroundColor: colors.errorMuted,
  },
  jointCell: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    flex: 1,
  },
  faultMarker: {
    color: colors.error,
    fontSize: 8,
  },
  jointName: {
    color: colors.text.primary,
  },
  legendRow: {
    marginTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingTop: spacing.sm,
  },
  legendText: {
    color: colors.error,
  },
});
