'use client';

import Link from 'next/link';
import { User, Key, Gauge, Users, ChevronRight } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const settingsSections = [
  {
    title: 'Profile',
    description: 'Manage your account information and display preferences',
    href: '/console/settings/profile',
    icon: User,
  },
  {
    title: 'API Keys',
    description: 'Create and manage API keys for programmatic access',
    href: '/console/settings/api-keys',
    icon: Key,
  },
  {
    title: 'Limits',
    description: 'View and configure your usage limits and quotas',
    href: '/console/settings/limits',
    icon: Gauge,
  },
  {
    title: 'Team',
    description: 'Manage team members and organization settings',
    href: '/console/settings/team',
    icon: Users,
  },
];

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>
          Settings
        </h1>
        <p className="text-sm text-[var(--text-muted)]">
          Manage your account, API access, and organization preferences
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        {settingsSections.map((section) => {
          const Icon = section.icon;
          return (
            <Link key={section.href} href={section.href}>
              <Card className="h-full cursor-pointer transition-all hover:border-[var(--accent)] hover:bg-white/5">
                <CardHeader className="flex flex-row items-center gap-4">
                  <div className="rounded-lg bg-white/10 p-3">
                    <Icon className="h-6 w-6 text-[var(--accent)]" />
                  </div>
                  <div className="flex-1">
                    <CardTitle className="flex items-center justify-between">
                      {section.title}
                      <ChevronRight className="h-5 w-5 text-[var(--text-muted)]" />
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {section.description}
                    </CardDescription>
                  </div>
                </CardHeader>
              </Card>
            </Link>
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Need Help?</CardTitle>
          <CardDescription>
            If you need assistance with your account or have questions about settings, check out our documentation or contact support.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Link
              href="/resources"
              className="text-sm text-[var(--accent)] hover:underline"
            >
              View Documentation
            </Link>
            <span className="text-[var(--text-muted)]">|</span>
            <a
              href="mailto:support@swarmsync.ai"
              className="text-sm text-[var(--accent)] hover:underline"
            >
              Contact Support
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
