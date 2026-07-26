import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { authStore } from '@/store/authStore';
import { authService } from '@/services/auth';
import { useSubscription } from '@/hooks/useSubscription';
import { Button } from '@/components/Button';
import { colors, typography, spacing } from '@/theme';

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={[typography.caption, styles.rowLabel]}>{label}</Text>
      <Text style={[typography.body, styles.rowValue]}>{value}</Text>
    </View>
  );
}

export default function ProfileScreen() {
  const user = authStore((s) => s.user);
  const { isPremium, restorePurchases } = useSubscription();

  const handleLogout = () => {
    Alert.alert('Sign out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign out',
        style: 'destructive',
        onPress: async () => {
          await authService.signOut();
        },
      },
    ]);
  };

  const handleRestore = async () => {
    try {
      await restorePurchases();
      Alert.alert('Purchases restored', isPremium ? 'Premium is active.' : 'No active purchases found.');
    } catch {
      Alert.alert('Restore failed', 'Could not restore purchases. Try again later.');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.inner}>
        <View style={styles.header}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{(user?.email?.[0] ?? '?').toUpperCase()}</Text>
          </View>
          <Text style={[typography.h3, { color: colors.text.primary }]}>
            {user?.email ?? 'Unknown'}
          </Text>
        </View>

        <View style={styles.card}>
          <Row label="Account" value={user?.email ?? '-'} />
          <View style={styles.divider} />
          <Row label="Subscription" value={isPremium ? 'Premium - 3D analysis' : 'Free - 2D analysis'} />
        </View>

        <View style={styles.actions}>
          {!isPremium && (
            <TouchableOpacity style={styles.upgradeBtn}>
              <Text style={styles.upgradeBtnText}>Upgrade to Premium</Text>
            </TouchableOpacity>
          )}
          <Button label="Restore purchases" variant="outline" onPress={handleRestore} />
          <Button label="Sign out" variant="outline" onPress={handleLogout} style={styles.signOutBtn} />
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  inner: { flex: 1, paddingHorizontal: spacing.lg, paddingTop: spacing.lg },
  header: { alignItems: 'center', gap: spacing.md, marginBottom: spacing.xl },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colors.primaryMuted,
    borderWidth: 2,
    borderColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { fontSize: 28, fontWeight: '700', color: colors.primary },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 14,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  row: { paddingVertical: spacing.sm },
  rowLabel: { color: colors.text.muted, marginBottom: 2 },
  rowValue: { color: colors.text.primary },
  divider: { height: 1, backgroundColor: colors.border },
  actions: { gap: spacing.sm },
  upgradeBtn: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  upgradeBtnText: {
    color: colors.text.inverse,
    fontWeight: '700',
    fontSize: 16,
    letterSpacing: 0.2,
  },
  signOutBtn: { borderColor: colors.error },
});
