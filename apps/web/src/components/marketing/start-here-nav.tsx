import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

export function StartHereNav() {
  const personas = [
    {
      title: 'Builders',
      description: 'Developers and engineers building agent systems',
      icon: '⚙️',
      links: [
        { href: '/platform', label: 'Platform Overview' },
        { href: '/agent-orchestration-guide', label: 'Orchestration Guide' },
        { href: '/resources', label: 'SDK & API Docs' },
      ],
    },
    {
      title: 'Operators',
      description: 'Teams running workflows and managing agents',
      icon: '🎯',
      links: [
        { href: '/use-cases', label: 'Use Cases' },
        { href: '/agents', label: 'Browse Marketplace' },
        { href: '/demo/workflows', label: 'Workflow Builder' },
      ],
    },
    {
      title: 'Finance & Compliance',
      description: 'Finance teams and compliance officers',
      icon: '📊',
      links: [
        { href: '/security', label: 'Security & Compliance' },
        { href: '/pricing', label: 'Pricing & Plans' },
        { href: '/faq', label: 'FAQ' },
      ],
    },
  ];

  return (
    <section className="bg-[var(--surface-raised)] px-4 py-20">
      <div className="mx-auto max-w-6xl space-y-12">
        <div className="text-center space-y-4">
          <p className="text-sm font-medium uppercase tracking-[0.3em] text-muted-foreground">
            Get Started
          </p>
          <h2 className="text-4xl font-display text-[#704A07]">Start Here</h2>
          <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
            Choose your path based on your role and goals
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {personas.map((persona) => (
            <Card key={persona.title} className="border-white/70 bg-[var(--surface-raised)] hover-lift">
              <CardContent className="space-y-4 p-6">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{persona.icon}</span>
                  <div>
                    <h3 className="text-xl font-display text-[#704A07]">{persona.title}</h3>
                    <p className="text-xs text-muted-foreground">{persona.description}</p>
                  </div>
                </div>
                <ul className="space-y-2">
                  {persona.links.map((link) => (
                    <li key={link.href}>
                      <Link
                        href={link.href}
                        className="text-sm text-slate-300 hover:underline font-medium"
                      >
                        → {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
                <Button variant="outline" size="sm" className="w-full" asChild>
                  <Link href={persona.links[0].href}>Get Started</Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}

