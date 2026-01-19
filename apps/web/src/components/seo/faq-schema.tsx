import * as React from 'react';

interface FAQItem {
  question: string;
  answer: string | React.ReactNode;
}

interface FAQSchemaProps {
  faqs: FAQItem[];
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

export function FAQSchema({ faqs }: FAQSchemaProps) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map((faq) => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: typeof faq.answer === 'string' 
          ? faq.answer 
          : extractText(faq.answer) || '',
      },
    })),
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}
