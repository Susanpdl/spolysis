import { create } from 'zustand';

interface AuthState {
  accessToken: string | null;
  user: { id: string; email: string } | null;
  isLoading: boolean;
  setAuth: (token: string, user: { id: string; email: string }) => void;
  clearAuth: () => void;
  setLoading: (loading: boolean) => void;
}

export const authStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  isLoading: true,
  setAuth: (accessToken, user) => set({ accessToken, user, isLoading: false }),
  clearAuth: () => set({ accessToken: null, user: null, isLoading: false }),
  setLoading: (isLoading) => set({ isLoading }),
}));
