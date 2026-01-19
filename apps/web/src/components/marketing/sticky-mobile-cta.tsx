'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { X } from 'lucide-react';

import { Button } from '@/components/ui/button';

const STORAGE_KEY = 'sticky_cta_dismissed';
const DISMISS_DURATION = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

export function StickyMobileCTA() {
  const [isVisible, setIsVisible] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);
  const [mounted, setMounted] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;

    // Don't show on auth pages
    if (pathname === '/login' || pathname === '/register' || pathname?.startsWith('/auth/')) {
      return;
    }

    // Check if dismissed and if dismissal is still valid
    const dismissedAt = localStorage.getItem(STORAGE_KEY);
    if (dismissedAt) {
      const dismissedTime = parseInt(dismissedAt, 10);
      const now = Date.now();
      if (now - dismissedTime < DISMISS_DURATION) {
        setIsDismissed(true);
        return;
      } else {
        // Dismissal expired, remove it
        localStorage.removeItem(STORAGE_KEY);
      }
    }

    // Check if mobile viewport
    const checkMobile = () => {
      if (window.innerWidth < 768 && !isDismissed) {
        setIsVisible(true);
        // Track impression
        if (typeof window !== 'undefined' && (window as any).gtag) {
          (window as any).gtag('event', 'sticky_cta_shown', {
            event_category: 'engagement',
            event_label: 'mobile_sticky_cta',
          });
        }
      } else {
        setIsVisible(false);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, [isDismissed, mounted, pathname]);

  if (!mounted) return null;

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEY, Date.now().toString());
    setIsDismissed(true);
    setIsVisible(false);

    // Track dismissal
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'sticky_cta_dismissed', {
        event_category: 'engagement',
        event_label: 'mobile_sticky_cta',
      });
    }
  };

  const handleClick = () => {
    // Track click
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'sticky_cta_clicked', {
        event_category: 'engagement',
        event_label: 'mobile_sticky_cta',
      });
    }
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 md:hidden">
      <div className="bg-black/95 backdrop-blur-sm border-t border-white/10 px-4 py-3 shadow-lg">
        <div className="max-w-md mx-auto flex items-center gap-3">
          <Button
            asChild
            onClick={handleClick}
            className="flex-1 bg-gradient-to-r from-[var(--accent-primary)] to-[#FFD87E] text-black font-semibold hover:opacity-90 transition-opacity"
            size="lg"
          >
            <Link href="/register">Start Free Trial</Link>
          </Button>
          <button
            onClick={handleDismiss}
            className="p-2 text-slate-400 hover:text-white transition-colors"
            aria-label="Dismiss call-to-action banner"
            type="button"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}
