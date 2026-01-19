import { AUTH_TOKEN_KEY, AUTH_USER_KEY } from '@/lib/constants';

export interface StoredAuthUser {
  id: string;
  email: string;
  displayName: string;
}

export const persistAuth = (user: StoredAuthUser, token: string) => {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
  window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));

  // Also set cookie for server-side auth checks
  // Cookie expires in 1 hour (matching JWT expiry)
  const maxAge = 60 * 60; // 1 hour in seconds
  document.cookie = `auth_token=${token}; path=/; max-age=${maxAge}; SameSite=Lax`;
};

export const ensureAuthToken = () => {
  if (typeof document === 'undefined') {
    return null;
  }

  const existing = window.localStorage.getItem(AUTH_TOKEN_KEY);
  if (existing) {
    return existing;
  }

  // Try to restore from the auth cookie set during login
  const cookies = document.cookie.split(';').map((c) => c.trim());
  const authCookie = cookies.find((c) => c.startsWith('auth_token='));
  if (authCookie) {
    const token = authCookie.split('=')[1];
    if (token) {
      window.localStorage.setItem(AUTH_TOKEN_KEY, token);
      return token;
    }
  }

  return null;
};

export const clearStoredAuth = () => {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
  window.localStorage.removeItem(AUTH_USER_KEY);

  // Also clear the auth cookie
  document.cookie = 'auth_token=; path=/; max-age=0; SameSite=Lax';
};

export const getStoredAuth = () => {
  if (typeof window === 'undefined') {
    return null;
  }
  const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
  const userRaw = window.localStorage.getItem(AUTH_USER_KEY);
  if (!token || !userRaw) {
    return null;
  }

  try {
    const user = JSON.parse(userRaw) as StoredAuthUser;
    return { token, user };
  } catch {
    clearStoredAuth();
    return null;
  }
};
