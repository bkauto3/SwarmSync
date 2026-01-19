'use client';

import { useRouter } from 'next/navigation';
import { signOut, useSession } from 'next-auth/react';
import { useEffect, useMemo, useState } from 'react';

import { clearStoredAuth, ensureAuthToken, getStoredAuth } from '@/lib/auth';
import { AUTH_TOKEN_KEY } from '@/lib/constants';
import { useAuthStore } from '@/stores/auth-store';

export function useAuth() {
  const router = useRouter();
  const { data: session, status } = useSession();
  const { user, token, setAuth, clearAuth } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);

  // Memoize sessionUser to prevent infinite loops
  const sessionUser = useMemo(() => {
    if (session?.user?.email && session?.user) {
      return {
        id: session.user.id || session.user.email,
        email: session.user.email,
        displayName: session.user.name || session.user.email,
      };
    }
    return null;
  }, [session?.user?.email, session?.user?.id, session?.user?.name]);

  // Keep local store in sync with NextAuth session or JWT login
  useEffect(() => {
    const restoredToken = ensureAuthToken();
    const stored = getStoredAuth();

    if (status === 'authenticated' && sessionUser) {
      // Only update if user has changed to prevent infinite loops
      if (!user || user.id !== sessionUser.id || user.email !== sessionUser.email) {
        setAuth(sessionUser, '');
      }
      setIsLoading(false);
      return;
    }

    if (stored) {
      // Only update if stored auth differs from current
      if (!user || user.id !== stored.user.id || user.email !== stored.user.email) {
        setAuth(stored.user, stored.token);
      }
    } else if (restoredToken && sessionUser) {
      // If token was restored from cookie but store is empty, hydrate it with session data
      setAuth(
        sessionUser,
        restoredToken,
      );
    } else if (status === 'unauthenticated') {
      if (user || token) {
        clearAuth();
        clearStoredAuth();
      }
    }

    setIsLoading(status === 'loading');
  }, [
    status,
    session?.user?.email,
    session?.user?.id,
    session?.user?.name,
    sessionUser,
    user,
    token,
    setAuth,
    clearAuth,
  ]);

  const logout = async () => {
    try {
      clearStoredAuth();

      clearAuth();
      await signOut({ callbackUrl: '/' });
    } catch (error) {
      console.error('Logout failed:', error);
      clearAuth();
      clearStoredAuth();
      router.push('/');
    }
  };

  const localToken =
    typeof window !== 'undefined' ? window.localStorage.getItem(AUTH_TOKEN_KEY) : null;
  const isAuthenticated =
    status === 'authenticated' || !!sessionUser || !!token || !!localToken;

  return {
    user: sessionUser || user,
    token: token || localToken,
    isAuthenticated,
    isLoading,
    login: () => {
      // Login is handled by EmailLoginForm or SocialLoginButtons
      console.warn('Use EmailLoginForm or SocialLoginButtons for login');
    },
    loginStatus: 'idle' as const,
    loginError: null,
    register: () => {
      // Registration is handled by EmailRegisterForm or SocialLoginButtons
      console.warn('Use EmailRegisterForm or SocialLoginButtons for registration');
    },
    registerStatus: 'idle' as const,
    registerError: null,
    logout,
  };
}
