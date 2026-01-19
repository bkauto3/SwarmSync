import Link from 'next/link';

import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { SecurityBadges } from '@/components/marketing/security-badges';
import { StructuredData } from '@/components/seo/structured-data';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export const metadata = {
  title: 'Resources | Swarm Sync - AI Agent Orchestration Guides & Documentation',
  description:
    'Resources, guides, and documentation for building autonomous agent systems. Learn about agent orchestration, best practices, and integration patterns.',
  alternates: {
    canonical: 'https://swarmsync.ai/resources',
  },
};

const resources = [
  {
    category: 'Getting Started',
    items: [
      {
        title: 'Agent Orchestration Guide',
        description:
          'Comprehensive guide to orchestrating multiple AI agents, including patterns, best practices, and anti-patterns.',
        href: '/agent-orchestration-guide',
        type: 'Guide',
      },
      {
        title: 'Platform Overview',
        description:
          'Deep dive into the Swarm Sync platform architecture, features, and integration options.',
        href: '/platform',
        type: 'Documentation',
      },
      {
        title: 'Use Cases & Examples',
        description:
          'Real-world examples of agent orchestration across industries with ROI metrics and workflows.',
        href: '/use-cases',
        type: 'Case Studies',
      },
    ],
  },
  {
    category: 'Integration',
    items: [
      {
        title: 'API Documentation',
        description: 'Complete API reference for integrating Swarm Sync into your applications.',
        href: '/platform#api',
        type: 'API Docs',
        external: false,
      },
      {
        title: 'SDK Examples',
        description: 'Code examples and tutorials for using the Swarm Sync SDK in your projects.',
        href: '/platform#sdk',
        type: 'Code Examples',
        external: false,
      },
      {
        title: 'LangChain Integration',
        description: 'Step-by-step guide to integrating Swarm Sync with LangChain agents.',
        href: '/platform#integrations',
        type: 'Tutorial',
        external: false,
      },
    ],
  },
  {
    category: 'Security & Compliance',
    items: [
      {
        title: 'Security Overview',
        description:
          'Learn about our security features, compliance certifications, and data protection measures.',
        href: '/security',
        type: 'Security',
      },
      {
        title: 'Escrow System Explained',
        description: 'Technical deep dive into how our escrow-backed transaction system works.',
        href: '/security#escrow',
        type: 'Technical',
        external: false,
      },
    ],
  },
  {
    category: 'Business',
    items: [
      {
        title: 'Build vs. Buy Analysis',
        description: 'Compare building your own agent orchestration platform vs. using Swarm Sync.',
        href: '/vs/build-your-own',
        type: 'Analysis',
      },
      {
        title: 'Pricing & Plans',
        description:
          'View our pricing plans and understand which tier is right for your organization.',
        href: '/register',
        type: 'Pricing',
        external: false,
      },
    ],
  },
];

export default function ResourcesPage() {
  return (
    <>
      <StructuredData />
      <div className="flex min-h-screen flex-col bg-gradient-to-b from-black/0 via-black/25 to-black/60">
        <Navbar />
        <main className="flex-1">
          {/* Hero Section */}
          <section className="px-4 py-20">
            <div className="mx-auto max-w-6xl text-center">
              <p className="text-sm uppercase tracking-[0.3em] text-slate-400">
                Resources & Documentation
              </p>
              <h1 className="mt-6 text-4xl font-display leading-tight text-white sm:text-5xl lg:text-6xl">
                Everything You Need to Build with Agents
              </h1>
              <p className="mt-6 max-w-2xl mx-auto text-lg text-slate-400">
                Guides, tutorials, API documentation, and best practices for building autonomous
                agent systems.
              </p>
            </div>
          </section>

          {/* Resources Grid */}
          <section className="px-4 pb-20">
            <div className="mx-auto max-w-6xl space-y-16">
              {resources.map((category) => (
                <div key={category.category} className="space-y-6">
                  <h2 className="text-3xl font-display text-white">{category.category}</h2>
                  <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {category.items.map((resource) => (
                      <Card
                        key={resource.title}
                        className="border-white/20 bg-[var(--surface-base)] transition-all hover:shadow-brand-panel"
                      >
                        <CardHeader>
                          <div className="flex items-start justify-between">
                            <CardTitle className="text-xl font-display">{resource.title}</CardTitle>
                            <span className="text-xs uppercase tracking-wider text-slate-400">
                              {resource.type}
                            </span>
                          </div>
                          <CardDescription className="text-sm text-[var(--text-secondary)]">
                            {resource.description}
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <Button asChild variant="outline" className="w-full">
                            <Link href={resource.href}>
                              {resource.external ? 'Visit Resource →' : 'Read More →'}
                            </Link>
                          </Button>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* CTA Section */}
          <section className="bg-black px-4 py-20">
            <div className="mx-auto max-w-3xl text-center">
              <h2 className="text-3xl font-display text-white">Ready to Start Building?</h2>
              <p className="mt-4 text-lg text-slate-400">
                Get started with Swarm Sync today. No credit card required.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-4">
                <Button size="lg" asChild>
                  <Link href="/register">Start Free Trial</Link>
                </Button>
                <Button size="lg" variant="secondary" asChild>
                  <Link href="/platform">View Platform Docs</Link>
                </Button>
              </div>
            </div>
          </section>

          <SecurityBadges />
        </main>
        <Footer />
      </div>
    </>
  );
}
