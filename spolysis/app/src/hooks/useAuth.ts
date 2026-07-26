import { useEffect } from 'react';
import { authStore } from '@/store/authStore';
import { authService } from '@/services/auth';

export function useAuth() {
  const { accessToken, user, isLoading, setAuth, clearAuth, setLoading } = authStore();

  useEffect(() => {
    authService.getSession().then(({ data }) => {
      if (data.session) {
        setAuth(data.session.access_token, {
          id: data.session.user.id,
          email: data.session.user.email ?? '',
        });
      } else {
        setLoading(false);
      }
    });

    const { data: sub } = authService.onAuthStateChange((_event, session) => {
      if (session) {
        setAuth(session.access_token, {
          id: session.user.id,
          email: session.user.email ?? '',
        });
      } else {
        clearAuth();
      }
    });

    return () => sub.subscription.unsubscribe();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { accessToken, user, isLoading, isAuthenticated: !!accessToken };
}
