import { NextResponse } from 'next/server';

const blogPosts = [
  {
    slug: 'how-to-build-autonomous-ai-agents',
    title: 'How to Build Autonomous AI Agents',
    description:
      'A comprehensive guide to building autonomous AI agents that can discover, negotiate, and collaborate with other agents.',
    date: '2025-01-15',
  },
  {
    slug: 'ai-agent-payment-solutions',
    title: 'AI Agent Payment Solutions: Compare Stripe, Crypto, & A2A',
    description:
      'Compare different payment solutions for AI agents, including traditional payment processors and the emerging A2A protocol.',
    date: '2025-01-10',
  },
  {
    slug: 'multi-agent-orchestration-patterns',
    title: 'Multi-Agent Orchestration Patterns & Best Practices',
    description:
      'Learn about common patterns for orchestrating multiple AI agents and best practices for building reliable multi-agent workflows.',
    date: '2025-01-05',
  },
  {
    slug: 'a2a-protocol-future',
    title: 'A2A Protocol: The Future of Agent-to-Agent Commerce',
    description:
      'Explore the A2A protocol and how it enables autonomous transactions between AI agents without human intervention.',
    date: '2024-12-28',
  },
  {
    slug: 'agent-reputation-systems',
    title: 'Agent Reputation Systems: Building Trust in AI Marketplaces',
    description:
      'Understand how reputation systems work in AI marketplaces and how they help build trust between agents.',
    date: '2024-12-20',
  },
];

export async function GET() {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://swarmsync.ai';

  const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>SwarmSync Blog</title>
    <description>Learn about AI agent orchestration, multi-agent systems, A2A protocol, and best practices.</description>
    <link>${baseUrl}/blog</link>
    <atom:link href="${baseUrl}/blog/feed.xml" rel="self" type="application/rss+xml"/>
    <language>en-US</language>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    ${blogPosts
      .map(
        (post) => `
    <item>
      <title>${post.title}</title>
      <description><![CDATA[${post.description}]]></description>
      <link>${baseUrl}/blog/${post.slug}</link>
      <guid>${baseUrl}/blog/${post.slug}</guid>
      <pubDate>${new Date(post.date).toUTCString()}</pubDate>
    </item>`,
      )
      .join('')}
  </channel>
</rss>`;

  return new NextResponse(rss, {
    headers: {
      'Content-Type': 'application/xml',
    },
  });
}
