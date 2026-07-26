import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL ?? '';
const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ?? '';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export const authService = {
  signUp: (email: string, password: string) =>
    supabase.auth.signUp({ email, password }),
  signIn: (email: string, password: string) =>
    supabase.auth.signInWithPassword({ email, password }),
  signOut: () => supabase.auth.signOut(),
  getSession: () => supabase.auth.getSession(),
  onAuthStateChange: (
    callback: Parameters<typeof supabase.auth.onAuthStateChange>[0],
  ) => supabase.auth.onAuthStateChange(callback),
};
