'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2 } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { trackTrialSignupStarted, trackTrialSignupCompleted } from '@/lib/analytics';
import { authApi } from '@/lib/api';
import { persistAuth } from '@/lib/auth';
import { useAuthStore } from '@/stores/auth-store';

const registerSchema = z
  .object({
    email: z.string().email('Please enter a valid email address'),
    displayName: z.string().min(3, 'Name must be at least 3 characters'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

interface EmailRegisterFormProps {
  selectedPlan?: string;
}

export function EmailRegisterForm({ selectedPlan }: EmailRegisterFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setAuth = useAuthStore((state) => state.setAuth);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    mode: 'onSubmit',
    reValidateMode: 'onSubmit',
  });

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true);
    setError(null);

    // Track signup attempt
    trackTrialSignupStarted();

    try {
      const response = await authApi.register({
        email: data.email,
        password: data.password,
        displayName: data.displayName,
      });

      // Store token in localStorage and cookie
      persistAuth(response.user, response.accessToken);

      // Update auth store
      setAuth(response.user, response.accessToken);

      // Track successful signup
      trackTrialSignupCompleted();

      // Redirect to dashboard (or pricing if plan was selected)
      if (selectedPlan || searchParams.get('plan')) {
        router.push(`/billing?plan=${selectedPlan || searchParams.get('plan')}`);
      } else {
        router.push('/dashboard');
      }
    } catch (err: unknown) {
      console.error('Registration error:', err);
      let message = 'Registration failed. Please try again.';
      
      if (err && typeof err === 'object') {
        // Handle ky HTTPError
        if ('response' in err && err.response && typeof err.response === 'object') {
          const httpError = err as { response: { status: number; statusText: string } };
          const status = httpError.response.status;
          
          if (status === 401 || status === 409) {
            message = 'Email already registered. Please sign in instead.';
          } else if (status === 400) {
            message = 'Invalid registration data. Please check your information.';
          } else if (status >= 500) {
            message = 'Server error. Please try again later.';
          } else {
            message = httpError.response.statusText || 'Registration failed. Please try again.';
          }
        } else if ('message' in err && typeof err.message === 'string') {
          message = err.message;
        } else if (err instanceof Error) {
          message = err.message;
        }
      } else if (err instanceof Error) {
        message = err.message;
      }
      
      setError(message);
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="displayName">Full Name</Label>
        <Input
          id="displayName"
          type="text"
          placeholder="John Doe"
          {...register('displayName')}
          disabled={isLoading}
          aria-invalid={errors.displayName ? 'true' : 'false'}
        />
        {errors.displayName && (
          <p className="text-xs text-red-600" role="alert">
            {errors.displayName.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          placeholder="you@example.com"
          {...register('email')}
          disabled={isLoading}
          aria-invalid={errors.email ? 'true' : 'false'}
        />
        {errors.email && (
          <p className="text-xs text-red-600" role="alert">
            {errors.email.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          placeholder="••••••••"
          {...register('password')}
          disabled={isLoading}
          aria-invalid={errors.password ? 'true' : 'false'}
        />
        {errors.password && (
          <p className="text-xs text-red-600" role="alert">
            {errors.password.message}
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="confirmPassword">Confirm Password</Label>
        <Input
          id="confirmPassword"
          type="password"
          placeholder="••••••••"
          {...register('confirmPassword')}
          disabled={isLoading}
          aria-invalid={errors.confirmPassword ? 'true' : 'false'}
        />
        {errors.confirmPassword && (
          <p className="text-xs text-red-600" role="alert">
            {errors.confirmPassword.message}
          </p>
        )}
      </div>

      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
            Creating account...
          </>
        ) : (
          'Create Account'
        )}
      </Button>
    </form>
  );
}

