import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Session } from "@supabase/supabase-js";
import { authStore } from "@/store/authStore";
import { authService } from "@/services/auth";

export function useAuth() {
  const { accessToken, user, isLoading, setAuth, clearAuth, setLoading } =
    authStore();
  const queries = useQueryClient();

  useEffect(() => {
    const applySession = (session: Session | null) => {
      // Clear private results before publishing a removed or different identity.
      // Token refreshes for the same athlete keep their active queries.
      if (!session || authStore.getState().user?.id !== session.user.id) {
        queries.clear();
      }
      if (session) {
        setAuth(session.access_token, {
          id: session.user.id,
          email: session.user.email ?? "",
        });
      } else {
        clearAuth();
      }
    };

    authService
      .getSession()
      .then(({ data }) => applySession(data.session))
      .catch(() => setLoading(false));

    const { data: sub } = authService.onAuthStateChange(
      async (_event, session) => applySession(session),
    );

    return () => sub.subscription.unsubscribe();
  }, [queries, setAuth, clearAuth, setLoading]);

  return { accessToken, user, isLoading, isAuthenticated: !!accessToken };
}
