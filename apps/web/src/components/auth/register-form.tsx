'use client';

import { EmailRegisterForm } from '@/components/auth/email-register-form';
import { SocialLoginButtons } from '@/components/auth/social-login-buttons';

interface RegisterFormProps {
  selectedPlan?: string;
}

export function RegisterForm({ selectedPlan }: RegisterFormProps) {
  return (
    <div className="space-y-5">
      <EmailRegisterForm selectedPlan={selectedPlan} />
      <SocialLoginButtons />
      <p className="text-xs text-center text-[var(--text-muted)]">
        By creating an account, you agree to our{' '}
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
