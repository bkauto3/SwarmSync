import Image from 'next/image';
import Link from 'next/link';

import ChromeNetworkBackground from '@/components/swarm/ChromeNetworkBackground';
import DepthFieldOrbs from '@/components/swarm/DepthFieldOrbs';
import { Sidebar } from '@/components/layout/Sidebar';
import { WelcomeModal } from '@/components/onboarding/welcome-modal';
import { Walkthrough } from '@/components/onboarding/walkthrough';
import { requireAuth } from '@/lib/auth-guard';

import type { ReactNode } from 'react';

export default async function ConsoleLayout({ children }: { children: ReactNode }) {
  // Protect all console routes - redirect to login if not authenticated
  await requireAuth('/overview');

  return (
    <div className="console-page app-page flex min-h-screen w-full bg-black text-slate-50">
      <ChromeNetworkBackground />
      <DepthFieldOrbs />
      <Sidebar />
      <div className="flex-1 relative z-10">
        {/* Logo in top-right corner */}
        <div className="absolute top-6 right-6 z-10">
          <Link href="/console/overview">
            <Image
              src="/logos/swarm-sync-purple.png"
              alt="Swarm Sync logo"
              width={90}
              height={90}
              quality={75}
              className="h-24 w-auto cursor-pointer transition-opacity hover:opacity-80"
              priority
            />
          </Link>
        </div>
        <main className="flex-1 px-6 py-10 lg:px-12">
          <div className="mx-auto max-w-7xl space-y-12">{children}</div>
        </main>
      </div>
      <WelcomeModal />
      <Walkthrough />
    </div>
  );
}
