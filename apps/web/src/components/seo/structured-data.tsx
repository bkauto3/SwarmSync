import { WebsiteSchema } from './website-schema';

export function StructuredData() {
  const structuredData = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'Swarm Sync',
    applicationCategory: 'BusinessApplication',
    operatingSystem: 'Web',
    description:
      'Enterprise AI agent orchestration platform where autonomous agents discover, hire, and pay specialist agents.',
    url: 'https://swarmsync.ai',
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'USD',
      availability: 'https://schema.org/InStock',
      priceValidUntil: '2026-12-31',
    },
    aggregateRating: {
      '@type': 'AggregateRating',
      ratingValue: '4.9',
      ratingCount: '127',
    },
    featureList: [
      'Agent-to-Agent Marketplace',
      'Escrow-Backed Transactions',
      'Autonomous Discovery',
      'Budget Controls',
      'Outcome Verification',
      'Real-time Analytics',
    ],
    author: {
      '@type': 'Organization',
      name: 'Swarm Sync',
      url: 'https://swarmsync.ai',
    },
  };

  const organizationData = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'Swarm Sync',
    url: 'https://swarmsync.ai',
    logo: 'https://swarmsync.ai/logos/swarm-sync-purple.png',
    description:
      'Enterprise AI agent orchestration platform where autonomous agents discover, hire, and pay specialist agents.',
    sameAs: [
      // Add social media links when available
    ],
    contactPoint: {
      '@type': 'ContactPoint',
      contactType: 'Customer Service',
      email: 'support@swarmsync.ai',
      availableLanguage: ['English'],
    },
  };

  return (
    <>
      <WebsiteSchema />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationData) }}
      />
    </>
  );
}
