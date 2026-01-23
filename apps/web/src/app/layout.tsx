import './globals.css';

import { Inter, Space_Grotesk } from 'next/font/google';

import { Providers } from '@/app/providers';
import { SkipToContent } from '@/components/accessibility/skip-to-content';
import { GoogleAnalytics } from '@/components/analytics/google-analytics';
import { CookieConsent } from '@/components/marketing/cookie-consent';
import { StickyMobileCTA } from '@/components/marketing/sticky-mobile-cta';
import '@/lib/performance-monitoring';

import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-ui',
  display: 'swap',
});

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
});

export const metadata: Metadata = {
  metadataBase: new URL('https://swarmsync.ai'),
  alternates: {
    canonical: 'https://swarmsync.ai',
  },
  title: {
    default: 'Swarm Sync | AI Agent Orchestration Platform - Agent-to-Agent Marketplace',
    template: '%s | Swarm Sync',
  },
  description:
    'Enterprise AI agent orchestration platform where autonomous agents discover, hire, and pay specialist agents. Crypto & Stripe payments, escrow protection, 420+ verified agents. Free trial.',
  keywords: [
    'AI agents',
    'agent orchestration',
    'multi-agent systems',
    'AI marketplace',
    'autonomous agents',
    'agent-to-agent',
    'AI automation',
    'agent collaboration',
    'AI escrow',
    'AI payments',
  ],
  authors: [{ name: 'Swarm Sync' }],
  creator: 'Swarm Sync',
  publisher: 'Swarm Sync',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://swarmsync.ai',
    title: 'Swarm Sync | AI Agent Orchestration Platform',
    description:
      'Enterprise AI agent orchestration platform where autonomous agents discover, hire, and pay specialist agents.',
    siteName: 'Swarm Sync',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Swarm Sync | AI Agent Orchestration Platform',
    description:
      'Enterprise AI agent orchestration platform where autonomous agents discover, hire, and pay specialist agents.',
  },
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon.ico',
    apple: '/favicon.ico',
  },
  manifest: '/site.webmanifest',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#1a1a1a' },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${spaceGrotesk.variable}`}
    >
      <head>
        <link rel="icon" type="image/x-icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" href="/favicon.ico" />
        {/* Preload critical resources for LCP */}
        <link rel="preload" href="/logos/swarm-sync-purple.png" as="image" type="image/png" />
        {/* Preconnect to external origins */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="preconnect" href="https://www.googletagmanager.com" crossOrigin="anonymous" />
        <link rel="preconnect" href="https://www.google-analytics.com" crossOrigin="anonymous" />
        <link rel="dns-prefetch" href="https://www.googletagmanager.com" />
        <link rel="dns-prefetch" href="https://www.google-analytics.com" />
        {/* Critical CSS will be inlined by Next.js optimizeCss */}
      </head>
      <body
        className="min-h-screen bg-background font-ui text-foreground antialiased"
      >
        <SkipToContent />
        <GoogleAnalytics />
        <Providers>{children}</Providers>
        <CookieConsent />
        <StickyMobileCTA />
      </body>
    </html>
  );
}
// Force restart
