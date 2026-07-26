import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  ScrollView,
} from 'react-native';
import Purchases, { PurchasesPackage } from 'react-native-purchases';
import { colors, typography, spacing } from '@/theme';

const FEATURES = [
  'Full 3D reconstruction of your motion',
  'Phase-aligned comparison vs. pro reference',
  'Corrected skeleton overlaid on your footage',
  'Interactive 3D viewer - scrub and rotate',
  'Exact joint angles and timing deltas',
];

interface PaywallScreenProps {
  onDismiss: () => void;
}

export default function PaywallScreen({ onDismiss }: PaywallScreenProps) {
  const [packages, setPackages] = useState<PurchasesPackage[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);

  useEffect(() => {
    Purchases.getOfferings()
      .then((offerings) => {
        const pkgs = offerings.current?.availablePackages ?? [];
        setPackages(pkgs);
        if (pkgs.length > 0) setSelected(pkgs[0].identifier);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handlePurchase = async () => {
    if (!selected) return;
    const pkg = packages.find((p) => p.identifier === selected);
    if (!pkg) return;
    setPurchasing(true);
    try {
      await Purchases.purchasePackage(pkg);
      onDismiss();
    } catch (err: any) {
      if (!err.userCancelled) {
        Alert.alert('Purchase failed', err.message ?? 'Please try again.');
      }
    } finally {
      setPurchasing(false);
    }
  };

  const handleRestore = async () => {
    setPurchasing(true);
    try {
      const info = await Purchases.restorePurchases();
      const isActive = info.entitlements.active['premium'] !== undefined;
      if (isActive) {
        onDismiss();
      } else {
        Alert.alert('No purchases found', 'No active premium subscription found for this Apple ID.');
      }
    } catch {
      Alert.alert('Restore failed', 'Could not restore purchases.');
    } finally {
      setPurchasing(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <TouchableOpacity style={styles.closeBtn} onPress={onDismiss}>
          <Text style={styles.closeText}>✕</Text>
        </TouchableOpacity>

        <View style={styles.badge}>
          <Text style={styles.badgeText}>PREMIUM</Text>
        </View>
        <Text style={[typography.h2, styles.title]}>See exactly what to fix</Text>
        <Text style={[typography.body, styles.subtitle]}>
          The 3D analysis shows your own body - corrected - overlaid on your footage.
          Not a score. Not a stickman. Your actual joints, where they should have been.
        </Text>

        <View style={styles.features}>
          {FEATURES.map((f) => (
            <View key={f} style={styles.featureRow}>
              <Text style={styles.check}>✓</Text>
              <Text style={[typography.body, styles.featureText]}>{f}</Text>
            </View>
          ))}
        </View>

        {loading ? (
          <ActivityIndicator color={colors.primary} style={{ marginVertical: spacing.xl }} />
        ) : (
          <View style={styles.packages}>
            {packages.map((pkg) => {
              const isSelected = pkg.identifier === selected;
              return (
                <TouchableOpacity
                  key={pkg.identifier}
                  style={[styles.packageCard, isSelected && styles.packageCardSelected]}
                  onPress={() => setSelected(pkg.identifier)}
                >
                  <View>
                    <Text style={[typography.body, styles.packageTitle]}>
                      {pkg.packageType}
                    </Text>
                    <Text style={[typography.caption, styles.packageDesc]}>
                      {pkg.product.description}
                    </Text>
                  </View>
                  <Text style={[typography.h3, styles.packagePrice]}>
                    {pkg.product.priceString}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        )}

        <TouchableOpacity
          style={[styles.purchaseBtn, (purchasing || !selected) && styles.purchaseBtnDisabled]}
          onPress={handlePurchase}
          disabled={purchasing || !selected}
        >
          {purchasing ? (
            <ActivityIndicator color={colors.text.inverse} />
          ) : (
            <Text style={styles.purchaseBtnText}>Subscribe now</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity style={styles.restoreBtn} onPress={handleRestore} disabled={purchasing}>
          <Text style={styles.restoreText}>Restore purchases</Text>
        </TouchableOpacity>

        <Text style={styles.legal}>
          Subscription renews automatically. Cancel anytime in Settings.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  scroll: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.xxl, gap: spacing.lg },
  closeBtn: { alignSelf: 'flex-end', padding: spacing.sm },
  closeText: { color: colors.text.muted, fontSize: 18 },
  badge: {
    backgroundColor: colors.primaryMuted,
    alignSelf: 'flex-start',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  badgeText: { color: colors.primary, fontWeight: '700', fontSize: 11, letterSpacing: 1.2 },
  title: { color: colors.text.primary },
  subtitle: { color: colors.text.secondary, lineHeight: 24 },
  features: { gap: spacing.sm, backgroundColor: colors.surface, borderRadius: 14, padding: spacing.md },
  featureRow: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.sm },
  check: { color: colors.primary, fontWeight: '700', fontSize: 15, marginTop: 2 },
  featureText: { color: colors.text.primary, flex: 1, lineHeight: 24 },
  packages: { gap: spacing.sm },
  packageCard: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 1.5,
    borderColor: colors.border,
  },
  packageCardSelected: { borderColor: colors.primary, backgroundColor: colors.primaryMuted },
  packageTitle: { color: colors.text.primary, fontWeight: '600' },
  packageDesc: { color: colors.text.muted, marginTop: 2 },
  packagePrice: { color: colors.primary },
  purchaseBtn: {
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  purchaseBtnDisabled: { opacity: 0.5 },
  purchaseBtnText: { color: colors.text.inverse, fontWeight: '700', fontSize: 16 },
  restoreBtn: { alignSelf: 'center', paddingVertical: spacing.sm },
  restoreText: { color: colors.text.secondary, fontSize: 14 },
  legal: { color: colors.text.muted, fontSize: 11, textAlign: 'center', lineHeight: 16 },
});
