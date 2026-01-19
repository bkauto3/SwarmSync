interface PageStructuredDataProps {
  title: string;
  description: string;
  url: string;
  type?: 'WebPage' | 'Article' | 'SoftwareApplication';
  breadcrumbs?: Array<{ name: string; url: string }>;
}

export function PageStructuredData({
  title,
  description,
  url,
  type = 'WebPage',
  breadcrumbs,
}: PageStructuredDataProps) {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace('/api', '') || 'https://www.swarmsync.ai';
  const fullUrl = `${baseUrl}${url}`;

  interface StructuredData {
    '@context': string;
    '@type': string;
    name: string;
    description: string;
    url: string;
    breadcrumb?: {
      '@type': string;
      itemListElement: Array<{
        '@type': string;
        position: number;
        name: string;
        item: string;
      }>;
    };
  }

  const structuredData: StructuredData = {
    '@context': 'https://schema.org',
    '@type': type,
    name: title,
    description: description,
    url: fullUrl,
  };

  if (breadcrumbs && breadcrumbs.length > 0) {
    structuredData.breadcrumb = {
      '@type': 'BreadcrumbList',
      itemListElement: breadcrumbs.map((crumb, index) => ({
        '@type': 'ListItem',
        position: index + 1,
        name: crumb.name,
        item: `${baseUrl}${crumb.url}`,
      })),
    };
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  );
}
