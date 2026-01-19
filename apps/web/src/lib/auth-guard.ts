import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { getServerSession } from 'next-auth';

import { authOptions } from '@/lib/auth-options';

export interface AuthUser {
    id: string;
    email: string;
    displayName: string;
}

/**
 * Server-side authentication guard
 * Checks both JWT token (email/password) and NextAuth (OAuth) authentication
 * Redirects to login if not authenticated
 */
export async function requireAuth(redirectTo?: string) {
    // First check JWT token cookie (email/password auth)
    const cookieStore = await cookies();
    const jwtToken = cookieStore.get('auth_token')?.value;

    if (jwtToken) {
        return jwtToken;
    }

    // Check NextAuth session (OAuth - Google/GitHub)
    const session = await getServerSession(authOptions);
    if (session) {
        return 'nextauth';
    }

    // Not authenticated by either method
    const loginUrl = redirectTo ? `/login?from=${encodeURIComponent(redirectTo)}` : '/login';
    redirect(loginUrl);
}

/**
 * Check if user is authenticated without redirecting
 * Checks both JWT and NextAuth authentication
 */
export async function isAuthenticated(): Promise<boolean> {
    const cookieStore = await cookies();
    const jwtToken = cookieStore.get('auth_token')?.value;

    if (jwtToken) {
        return true;
    }

    const session = await getServerSession(authOptions);
    return Boolean(session);
}

/**
 * Get current authenticated user
 * Checks both JWT token and NextAuth session
 * Returns null if not authenticated or token is invalid
 */
export async function getCurrentUser(): Promise<AuthUser | null> {
    const cookieStore = await cookies();
    const jwtToken = cookieStore.get('auth_token')?.value;

    // First try JWT token (email/password auth)
    if (jwtToken) {
        try {
            const parts = jwtToken.split('.');
            if (parts.length === 3) {
                // Use atob for edge runtime compatibility
                const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
                const jsonPayload = decodeURIComponent(
                    atob(base64)
                        .split('')
                        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                        .join('')
                );
                const payload = JSON.parse(jsonPayload);
                return {
                    id: payload.sub || payload.id,
                    email: payload.email,
                    displayName: payload.displayName || payload.name || payload.email?.split('@')[0] || '',
                };
            }
        } catch (error) {
            console.error('Failed to decode JWT token:', error);
        }
    }

    // Try NextAuth session (OAuth)
    const session = await getServerSession(authOptions);
    if (session?.user?.email) {
        return {
            id: session.user.id || session.user.email,
            email: session.user.email,
            displayName: session.user.name || session.user.email,
        };
    }

    return null;
}
