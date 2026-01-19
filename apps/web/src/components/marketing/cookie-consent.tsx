'use client';

import { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';

const AUTO_DISMISS_DELAY = 5000;

export function CookieConsent() {
  const [showConsent, setShowConsent] = useState(false);
  const scrollTimerRef = useRef<number | null>(null);
  const visibleRef = useRef(showConsent);

  useEffect(() => {
    const consent = localStorage.getItem('cookie-consent');
    if (!consent) {
      setShowConsent(true);
    }

    const handleScroll = () => {
      if (!visibleRef.current || scrollTimerRef.current) {
        return;
      }

      scrollTimerRef.current = window.setTimeout(() => {
        localStorage.setItem('cookie-consent', 'accepted');
        setShowConsent(false);
      }, AUTO_DISMISS_DELAY);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (scrollTimerRef.current) {
        clearTimeout(scrollTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    visibleRef.current = showConsent;
  }, [showConsent]);

  const handleAccept = () => {
    localStorage.setItem('cookie-consent', 'accepted');
    setShowConsent(false);
  };

  const handleDecline = () => {
    localStorage.setItem('cookie-consent', 'declined');
    setShowConsent(false);
  };

  if (!showConsent) {
    return null;
  }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 border-b border-white/20 bg-black/80 backdrop-blur py-3 shadow-lg">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 text-xs text-[var(--text-secondary)] md:flex-row md:items-center md:justify-between">
        <div className="flex-1 space-y-1 text-[0.75rem] leading-snug">
          <p className="font-semibold uppercase tracking-[0.3em] text-[var(--text-muted)]">Cookie Consent</p>
          <p>
            We use cookies to improve your experience, analyze usage, and assist marketing efforts. By clicking
            &ldquo;Accept&rdquo;, you consent to our use of cookies.{' '}
            <a href="/cookie-policy" className="underline" aria-label="Read our Cookie Policy">
              Read our Cookie Policy
            </a>
            {' or '}
            <a href="/privacy" className="underline" aria-label="Read our Privacy Policy">
              Privacy Policy
            </a>
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleDecline} className="min-w-[90px]">
            Decline
          </Button>
          <Button size="sm" onClick={handleAccept} className="min-w-[90px] bg-white text-black hover:bg-slate-200 focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-black">
            Accept
          </Button>
        </div>
      </div>
    </div>
  );
}
