'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Fragment } from 'react';

import { BrandLogo } from '@/components/brand/brand-logo';
import { useAuth } from '@/hooks/use-auth';

const sections = [
  {
    title: 'Home',
    items: [
      { label: 'Overview', href: '/console/overview' },
    ],
  },
  {
    title: 'Build',
    items: [
      { label: 'Agents', href: '/agents' },
      { label: 'Workflows', href: '/workflows' },
    ],
  },
  {
    title: 'Spend',
    items: [
      { label: 'Wallet', href: '/wallet' },
      { label: 'Billing', href: '/billing' },
    ],
  },
  {
    title: 'Quality',
    items: [
      { label: 'Test Library', href: '/console/quality/test-library' },
      { label: 'Outcomes', href: '/console/quality/outcomes' },
    ],
  },
  {
    title: 'System',
    items: [
      { label: 'Logs', href: '/console/analytics/logs' },
      { label: 'API Keys', href: '/console/settings/api-keys' },
      { label: 'Limits', href: '/console/settings/limits' },
      { label: 'Settings', href: '/console/settings/profile' },
      { label: 'Test A2A', href: '/console/test-a2a' },
    ],
  },
];

const navItemClass =
  'block rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-200 sidebar-link text-[var(--text-secondary)]';

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();

  return (
    <aside className="hidden min-h-screen w-64 flex-col justify-between border-r border-[var(--border-base)] bg-[var(--surface-base)] p-6 text-[var(--text-primary)] lg:flex z-10">
      <div className="space-y-6">
        <div className="space-y-1">
          <Link
            href="/console/overview"
            className="text-base font-semibold text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]"
          >
            Home
          </Link>
          <div className="h-px bg-[var(--border-base)]" />
        </div>

        {sections.map((section) => (
          <Fragment key={section.title}>
            <div className="sidebar-label text-[var(--text-muted)] border-b border-[var(--border-base)] pb-2 mb-2">
              {section.title}
            </div>
            <nav className="space-y-1">
              {section.items.map((item) => {
                const isActive =
                  item.href !== '#' && (pathname === item.href || pathname?.startsWith(item.href));

                return (
                  <Link
                    key={item.label}
                    href={item.href}
                    className={`${navItemClass} ${isActive ? 'sidebar-link-active text-[var(--accent-primary)] border-l-3 border-[var(--accent-primary)] bg-[rgba(124,92,255,0.08)]' : 'hover:text-[var(--text-primary)] hover:bg-[rgba(255,255,255,0.04)]'}`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </Fragment>
        ))}
      </div>

      {user && (
        <Link
          href="/console/settings/profile"
          className="block rounded-2xl border border-[var(--border-base)] bg-[var(--surface-raised)] p-4 transition-colors hover:border-[var(--border-hover)] cursor-pointer"
        >
          <div className="text-[0.65rem] uppercase tracking-wide text-[var(--text-muted)]">Signed in as</div>
          <div className="mt-2 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--surface-raised)] text-sm font-semibold text-[var(--text-primary)]">
              {user.displayName?.charAt(0) || user.email.charAt(0)}
            </div>
            <div>
              <div className="text-sm font-semibold text-[var(--text-primary)]">{user.displayName || 'User'}</div>
              <div className="text-xs text-[var(--text-secondary)]">{user.email}</div>
            </div>
          </div>
        </Link>
      )}
    </aside>
  );
}
