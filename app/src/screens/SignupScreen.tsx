import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { AuthScreenProps } from '@/navigation/types';
import { Button } from '@/components/Button';
import { colors, typography, spacing } from '@/theme';
import { authService } from '@/services/auth';

export default function SignupScreen({ navigation }: AuthScreenProps<'Signup'>) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);

  const isValid = email.trim().length > 0 && password.length >= 8 && password === confirm;

  const handleSignup = async () => {
    if (!isValid) return;
    setLoading(true);
    const { error } = await authService.signUp(email.trim(), password);
    setLoading(false);
    if (error) {
      Alert.alert('Sign up failed', error.message);
    } else {
      Alert.alert('Check your email', 'We sent you a confirmation link.');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.inner}
      >
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
            <Text style={styles.backText}>← Back</Text>
          </TouchableOpacity>
          <Text style={[typography.h2, styles.title]}>Create account</Text>
        </View>

        <View style={styles.form}>
          <View style={styles.field}>
            <Text style={[typography.label, styles.label]}>Email</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              placeholderTextColor={colors.text.muted}
              autoCapitalize="none"
              keyboardType="email-address"
              autoComplete="email"
            />
          </View>
          <View style={styles.field}>
            <Text style={[typography.label, styles.label]}>Password</Text>
            <TextInput
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder="At least 8 characters"
              placeholderTextColor={colors.text.muted}
              secureTextEntry
              autoComplete="new-password"
            />
          </View>
          <View style={styles.field}>
            <Text style={[typography.label, styles.label]}>Confirm password</Text>
            <TextInput
              style={[styles.input, confirm && confirm !== password && styles.inputError]}
              value={confirm}
              onChangeText={setConfirm}
              placeholder="••••••••"
              placeholderTextColor={colors.text.muted}
              secureTextEntry
              autoComplete="new-password"
            />
            {confirm !== '' && confirm !== password && (
              <Text style={styles.errorText}>Passwords don't match</Text>
            )}
          </View>
          <Button
            label="Create account"
            onPress={handleSignup}
            loading={loading}
            disabled={!isValid}
            style={{ marginTop: spacing.sm }}
          />
        </View>

        <View style={styles.footer}>
          <Text style={[typography.bodySmall, { color: colors.text.secondary }]}>
            Already have an account?{' '}
          </Text>
          <TouchableOpacity onPress={() => navigation.replace('Login')}>
            <Text style={[typography.bodySmall, { color: colors.primary }]}>Sign in</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  inner: { flex: 1, paddingHorizontal: spacing.lg, justifyContent: 'space-between', paddingVertical: spacing.xl },
  header: { gap: spacing.md },
  backBtn: { alignSelf: 'flex-start' },
  backText: { color: colors.text.secondary, fontSize: 16 },
  title: { color: colors.text.primary },
  form: { gap: spacing.md },
  field: { gap: spacing.xs },
  label: { color: colors.text.secondary },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: spacing.md,
    paddingVertical: 14,
    color: colors.text.primary,
    fontSize: 16,
  },
  inputError: { borderColor: colors.error },
  errorText: { color: colors.error, fontSize: 12, marginTop: 2 },
  footer: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center' },
});
