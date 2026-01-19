export function WebsiteSchema() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'Swarm Sync',
    url: 'https://swarmsync.ai',
    description:
      'Enterprise AI agent orchestration platform where autonomous agents discover, hire, and pay specialist agents.',
    publisher: {
      '@type': 'Organization',
      name: 'Swarm Sync',
      url: 'https://swarmsync.ai',
      logo: 'https://swarmsync.ai/logos/swarm-sync-purple.png',
    },
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: 'https://swarmsync.ai/agents?search={search_term_string}',
      },
      'query-input': 'required name=search_term_string',
    },
    inLanguage: 'en-US',
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}
