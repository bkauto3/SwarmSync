'use client';

import { EmailLoginForm } from '@/components/auth/email-login-form';
import { SocialLoginButtons } from '@/components/auth/social-login-buttons';

export function LoginForm() {
  return (
    <div className="space-y-5">
      <EmailLoginForm />
      <SocialLoginButtons />
      <p className="text-xs text-center text-[var(--text-muted)]">
        By signing in, you agree to our{' '}
        <a href="/terms" className="text-slate-300 hover:text-white hover:underline font-medium">
          Terms of Service
        </a>{' '}
        and{' '}
        <a href="/privacy" className="text-slate-300 hover:text-white hover:underline font-medium">
          Privacy Policy
        </a>
      </p>
    </div>
  );
}
