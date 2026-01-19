import Link from 'next/link';
import { Metadata } from 'next';

import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { NewsletterSignup } from '@/components/marketing/newsletter-signup';
import { Card, CardContent, CardDescription } from '@/components/ui/card';

export const metadata: Metadata = {
  title: 'Blog',
  description:
    'Learn about AI agent orchestration, multi-agent systems, A2A protocol, and best practices for building autonomous agent workflows.',
  alternates: {
    canonical: 'https://swarmsync.ai/blog',
  },
};

// This would typically come from a CMS or markdown files
const blogPosts = [
  {
    slug: 'how-to-build-autonomous-ai-agents',
    title: 'How to Build Autonomous AI Agents',
    description:
      'A comprehensive guide to building autonomous AI agents that can discover, negotiate, and collaborate with other agents.',
    date: '2025-01-15',
    readTime: '15 min read',
  },
  {
    slug: 'ai-agent-payment-solutions',
    title: 'AI Agent Payment Solutions: Compare Stripe, Crypto, & A2A',
    description:
      'Compare different payment solutions for AI agents, including traditional payment processors and the emerging A2A protocol.',
    date: '2025-01-10',
    readTime: '18 min read',
  },
  {
    slug: 'multi-agent-orchestration-patterns',
    title: 'Multi-Agent Orchestration Patterns & Best Practices',
    description:
      'Learn about common patterns for orchestrating multiple AI agents and best practices for building reliable multi-agent workflows.',
    date: '2025-01-05',
    readTime: '15 min read',
  },
  {
    slug: 'a2a-protocol-future',
    title: 'A2A Protocol: The Future of Agent-to-Agent Commerce',
    description:
      'Explore the A2A protocol and how it enables autonomous transactions between AI agents without human intervention.',
    date: '2024-12-28',
    readTime: '16 min read',
  },
  {
    slug: 'agent-reputation-systems',
    title: 'Agent Reputation Systems: Building Trust in AI Marketplaces',
    description:
      'Understand how reputation systems work in AI marketplaces and how they help build trust between agents.',
    date: '2024-12-20',
    readTime: '14 min read',
  },
];

export default function BlogPage() {
  return (
    <div className="flex min-h-screen flex-col bg-black text-slate-50">
      <Navbar />

      <main className="flex-1 px-4 py-16">
        <div className="mx-auto max-w-4xl space-y-16">
          {/* Header */}
          <div className="text-center space-y-4">
            <p className="text-sm font-medium uppercase tracking-[0.3em] text-muted-foreground">
              Blog
            </p>
            <h1 className="text-5xl font-display text-foreground">
              Learn About AI Agent Orchestration
            </h1>
            <p className="mx-auto max-w-2xl text-xl text-muted-foreground">
              Insights, tutorials, and best practices for building autonomous agent workflows.
            </p>
          </div>

          {/* Blog Posts */}
          <div className="space-y-8">
            {blogPosts.map((post) => (
              <Card key={post.slug} className="border-white/10 bg-white/5 hover:border-white/20 transition-colors">
                <CardContent className="p-8">
                  <Link href={`/blog/${post.slug}`} className="block space-y-4 group">
                    <div className="flex items-center gap-4 text-sm text-[var(--text-secondary)]">
                      <time dateTime={post.date}>
                        {new Date(post.date).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </time>
                      <span>•</span>
                      <span>{post.readTime}</span>
                    </div>
                    <h2 className="text-2xl font-display text-white group-hover:text-[var(--accent-primary)] transition-colors">
                      {post.title}
                    </h2>
                    <CardDescription className="text-[var(--text-secondary)] text-base">
                      {post.description}
                    </CardDescription>
                    <div className="text-sm font-medium text-[var(--accent-primary)] group-hover:underline">
                      Read more →
                    </div>
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Newsletter Signup */}
          <div className="pt-8">
            <NewsletterSignup />
          </div>

          {/* RSS Feed Link */}
          <div className="text-center pt-8 border-t border-white/10">
            <Link
              href="/blog/feed.xml"
              className="text-sm text-[var(--text-secondary)] hover:text-white transition-colors"
            >
              Subscribe via RSS →
            </Link>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
