"use client";

import ChromeNetworkBackground from '@/components/swarm/ChromeNetworkBackground';
import DepthFieldOrbs from '@/components/swarm/DepthFieldOrbs';

import type { ReactNode } from 'react';

interface MarketingPageShellProps {
  children: ReactNode;
  className?: string;
}

export function MarketingPageShell({ children, className = '' }: MarketingPageShellProps) {
  return (
    <div className={`marketing-page relative min-h-screen bg-black text-slate-50 overflow-x-hidden ${className}`}>
      <ChromeNetworkBackground />
      <DepthFieldOrbs />
      <div className="relative z-10">{children}</div>
    </div>
  );
}
