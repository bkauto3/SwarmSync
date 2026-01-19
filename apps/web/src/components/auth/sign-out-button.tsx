'use client';

import { Loader2 } from 'lucide-react';
import { signOut } from 'next-auth/react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { clearStoredAuth } from '@/lib/auth';
import { useAuthStore } from '@/stores/auth-store';

export function SignOutButton() {
  const [isLoading, setIsLoading] = useState(false);
  const clearAuth = useAuthStore((state) => state.clearAuth);

  const onSignOut = async () => {
    setIsLoading(true);
    try {
      clearStoredAuth();
      clearAuth();
      await signOut({ callbackUrl: '/' });
    } catch (error) {
      console.error('Sign out failed:', error);
      setIsLoading(false);
    }
  };

  return (
    <Button
      type="button"
      variant="outline"
      onClick={onSignOut}
      disabled={isLoading}
      aria-busy={isLoading}
    >
      {isLoading ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
          Signing out...
        </>
      ) : (
        'Sign Out'
      )}
    </Button>
  );
}

