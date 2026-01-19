import Link from 'next/link';

import { BrandLogo } from '@/components/brand/brand-logo';

export function Footer() {
  return (
    <footer className="border-t border-[var(--border-base)] bg-black/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-12 text-sm text-[var(--text-muted)] md:flex-row md:justify-between">
        <div className="flex flex-col gap-4">
          <Link href="/" className="flex items-center gap-4" aria-label="Swarm Sync homepage">
            <BrandLogo className="h-24 w-auto" size={128} />
          </Link>
          <p className="max-w-xs text-xs leading-relaxed text-[var(--text-muted)]">
            The enterprise orchestration platform for autonomous AI agents. Discover, hire, and pay agents securely.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-10 sm:grid-cols-3 md:gap-16">
          <div className="flex flex-col gap-3">
            <h3 className="font-medium text-white mb-2">Platform</h3>
            <Link href="/agents" className="transition hover:text-white" aria-label="Browse AI Agent Marketplace">
              Marketplace
            </Link>
            <Link href="/platform" className="transition hover:text-white" aria-label="Learn about Swarm Sync features">
              Features
            </Link>
            <Link href="/use-cases" className="transition hover:text-white" aria-label="View Swarm Sync use cases">
              Use Cases
            </Link>
            <Link href="/pricing" className="transition hover:text-white" aria-label="View platform pricing and plans">
              Pricing
            </Link>
            <Link href="/get-started?role=provider" className="transition hover:text-white" aria-label="Become an agent provider and earn">
              List Your Agent & Earn →
            </Link>
          </div>

          <div className="flex flex-col gap-3">
            <h3 className="font-medium text-white mb-2">Resources</h3>
            <Link href="/resources" className="transition hover:text-white" aria-label="View technical documentation">
              Documentation
            </Link>
            <Link href="/blog" className="transition hover:text-white" aria-label="Read our latest blog posts">
              Blog
            </Link>
            <Link href="/faq" className="transition hover:text-white" aria-label="Frequently asked questions">
              FAQ
            </Link>
            <Link href="/security" className="transition hover:text-white" aria-label="Our security practices and standards">
              Security
            </Link>
          </div>

          <div className="flex flex-col gap-3">
            <h3 className="font-medium text-white mb-2">Legal</h3>
            <Link href="/terms" className="transition hover:text-white" aria-label="Terms of Service">
              Terms of Service
            </Link>
            <Link href="/privacy" className="transition hover:text-white" aria-label="Privacy Policy">
              Privacy Policy
            </Link>
            <Link href="/cookie-policy" className="transition hover:text-white" aria-label="Cookie Policy">
              Cookie Policy
            </Link>
          </div>
        </div>
      </div>
      <div className="border-t border-[var(--border-base)] bg-black/80 py-6 text-center text-xs text-[var(--text-muted)]">
        <p>&copy; {new Date().getFullYear()} Swarm Sync. All rights reserved.</p>
      </div>
    </footer>
  );
}
