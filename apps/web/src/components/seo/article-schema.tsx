interface ArticleSchemaProps {
  title: string;
  description: string;
  datePublished: string;
  dateModified?: string;
  author?: string;
  imageUrl?: string;
  url: string;
}

export function ArticleSchema({
  title,
  description,
  datePublished,
  dateModified,
  author = 'Swarm Sync',
  imageUrl,
  url,
}: ArticleSchemaProps) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: title,
    description,
    datePublished,
    dateModified: dateModified || datePublished,
    author: {
      '@type': 'Organization',
      name: author,
      url: 'https://swarmsync.ai',
    },
    publisher: {
      '@type': 'Organization',
      name: 'Swarm Sync',
      url: 'https://swarmsync.ai',
      logo: {
        '@type': 'ImageObject',
        url: 'https://swarmsync.ai/logos/swarm-sync-purple.png',
      },
    },
    ...(imageUrl && {
      image: {
        '@type': 'ImageObject',
        url: imageUrl,
      },
    }),
    url,
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}
