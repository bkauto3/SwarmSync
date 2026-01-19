'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

export function NewsletterSignup() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('loading');
    setMessage('');

    // TODO: Integrate with your email service provider (e.g., Mailchimp, ConvertKit, etc.)
    // For now, this is a placeholder that simulates success
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 500));
      
      // In production, replace this with actual API call:
      // const response = await fetch('/api/newsletter/subscribe', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ email }),
      // });
      // if (!response.ok) throw new Error('Subscription failed');

      setStatus('success');
      setMessage('Thanks for subscribing! Check your email to confirm.');
      setEmail('');
    } catch (error) {
      setStatus('error');
      setMessage('Something went wrong. Please try again.');
    }
  };

  return (
    <Card className="border-white/10 bg-white/5">
      <CardContent className="p-6 space-y-4">
        <div>
          <h3 className="text-xl font-display text-white mb-2">Stay Updated</h3>
          <p className="text-sm text-[var(--text-secondary)]">
            Get the latest articles on AI agent orchestration, multi-agent systems, and best practices delivered to your inbox.
          </p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex gap-2">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              required
              className="flex-1 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm text-white placeholder:text-[var(--text-muted)] focus:border-[var(--accent-primary)] focus:outline-none"
              disabled={status === 'loading' || status === 'success'}
            />
            <Button
              type="submit"
              disabled={status === 'loading' || status === 'success'}
              className="min-w-[100px]"
            >
              {status === 'loading' ? 'Subscribing...' : status === 'success' ? 'Subscribed!' : 'Subscribe'}
            </Button>
          </div>
          {message && (
            <p className={`text-sm ${status === 'success' ? 'text-emerald-400' : 'text-red-400'}`}>
              {message}
            </p>
          )}
        </form>
        <p className="text-xs text-[var(--text-muted)]">
          We respect your privacy. Unsubscribe at any time. See our{' '}
          <a href="/privacy" className="text-[var(--accent-primary)] hover:underline">
            Privacy Policy
          </a>
          .
        </p>
      </CardContent>
    </Card>
  );
}
