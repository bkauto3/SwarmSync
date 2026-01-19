import * as React from 'react';

interface ProductSchemaProps {
  name: string;
  price: number;
  description: string | React.ReactNode;
  slug: string;
}

// Helper to extract text from ReactNode
function extractText(node: React.ReactNode): string {
  if (typeof node === 'string') return node;
  if (typeof node === 'number') return String(node);
  if (!node) return '';
  if (Array.isArray(node)) {
    return node.map(extractText).join(' ').trim();
  }
  if (React.isValidElement(node)) {
    if (node.props.children) {
      return extractText(node.props.children);
    }
  }
  return '';
}

export function ProductSchema({ name, price, description, slug }: ProductSchemaProps) {
  // Convert ReactNode to string for schema markup
  const descriptionText = typeof description === 'string' 
    ? description 
    : description 
      ? extractText(description) || 'AI agent orchestration platform'
      : 'AI agent orchestration platform';
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name,
    description: descriptionText,
    url: `https://swarmsync.ai/pricing#${slug}`,
    offers: {
      '@type': 'Offer',
      price: price.toString(),
      priceCurrency: 'USD',
      availability: 'https://schema.org/InStock',
      url: `https://swarmsync.ai/register?plan=${slug}`,
    },
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}
