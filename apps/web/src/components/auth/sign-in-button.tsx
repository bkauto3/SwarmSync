'use client';

import { Loader2 } from 'lucide-react';
import { signIn } from 'next-auth/react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';

export function SignInButton() {
  const [isLoading, setIsLoading] = useState(false);

  const onSignIn = async () => {
    setIsLoading(true);
    try {
      await signIn(undefined, { callbackUrl: '/dashboard' });
    } catch (error) {
      console.error('Sign in failed:', error);
      setIsLoading(false);
    }
  };

  return (
    <Button
      type="button"
      className="w-full"
      onClick={onSignIn}
      disabled={isLoading}
      aria-busy={isLoading}
    >
      {isLoading ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
          Redirecting...
        </>
      ) : (
        'Sign In'
      )}
    </Button>
  );
}

