import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, Image } from 'react-native';
import { AuthScreenProps } from '@/navigation/types';
import { Button } from '@/components/Button';
import { colors, typography, spacing } from '@/theme';

export default function WelcomeScreen({ navigation }: AuthScreenProps<'Welcome'>) {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.hero}>
        <View style={styles.logoMark}>
          <Text style={styles.logoText}>SP</Text>
        </View>
        <Text style={[typography.h1, styles.appName]}>Spolysis</Text>
        <Text style={[typography.body, styles.tagline]}>
          See exactly what your body is doing wrong - and what it should do instead.
        </Text>
      </View>

      <View style={styles.featureList}>
        {[
          { icon: '🎾', text: 'Record your stroke with guided framing' },
          { icon: '🧠', text: '2D fault detection - free, instant' },
          { icon: '🏆', text: '3D IK correction on your own body - premium' },
        ].map(({ icon, text }) => (
          <View key={text} style={styles.featureRow}>
            <Text style={styles.featureIcon}>{icon}</Text>
            <Text style={[typography.bodySmall, styles.featureText]}>{text}</Text>
          </View>
        ))}
      </View>

      <View style={styles.actions}>
        <Button label="Create account" onPress={() => navigation.navigate('Signup')} />
        <Button
          label="Sign in"
          variant="outline"
          onPress={() => navigation.navigate('Login')}
          style={{ marginTop: spacing.sm }}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: spacing.lg,
    justifyContent: 'space-between',
    paddingVertical: spacing.xl,
  },
  hero: { alignItems: 'center', marginTop: spacing.xxl },
  logoMark: {
    width: 72,
    height: 72,
    borderRadius: 20,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  logoText: { fontSize: 28, fontWeight: '800', color: colors.text.inverse },
  appName: { color: colors.text.primary, marginBottom: spacing.sm },
  tagline: {
    color: colors.text.secondary,
    textAlign: 'center',
    maxWidth: 280,
    lineHeight: 24,
  },
  featureList: { gap: spacing.md },
  featureRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  featureIcon: { fontSize: 20, width: 28, textAlign: 'center' },
  featureText: { color: colors.text.secondary, flex: 1 },
  actions: { gap: 0 },
});
