import { MetadataRoute } from 'next';

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://swarmsync.ai';

  // Public marketing pages only - exclude auth and console routes
  const routes = [
    '',
    '/pricing',
    '/agents',
    '/platform',
    '/use-cases',
    '/agent-orchestration-guide',
    '/vs/build-your-own',
    '/security',
    '/resources',
    '/faq',
    '/privacy',
    '/terms',
    '/about',
    '/agent-marketplace',
    '/agent-escrow-payments',
    '/case-studies',
    '/methodology',
    '/cookie-policy',
    '/blog',
    '/authors/swarm-sync-team',
    '/blog/how-to-build-autonomous-ai-agents',
    '/blog/ai-agent-payment-solutions',
    '/blog/multi-agent-orchestration-patterns',
    '/blog/a2a-protocol-future',
    '/blog/agent-reputation-systems',
  ];

  return routes.map((route) => {
    const isBlogPost = route.startsWith('/blog/') && route !== '/blog';
    return {
      url: `${baseUrl}${route}`,
      lastModified: new Date(),
      changeFrequency: route === '' || isBlogPost ? ('weekly' as const) : ('monthly' as const),
      priority:
        route === ''
          ? 1.0
          : route === '/pricing' || route === '/agents'
            ? 0.9
            : route === '/blog'
              ? 0.8
              : isBlogPost
                ? 0.7
                : route.startsWith('/platform') || route.startsWith('/use-cases')
                  ? 0.8
                  : 0.7,
    };
  });
}
