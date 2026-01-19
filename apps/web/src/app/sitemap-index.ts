import { MetadataRoute } from 'next';

/**
 * Sitemap index for when we have many agent/profile pages.
 * This can be expanded to include dynamic agent sitemaps.
 */
export default function sitemapIndex(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'https://swarmsync.ai';

  return [
    {
      url: `${baseUrl}/sitemap.xml`,
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 1.0,
    },
    // Future: Add agent sitemaps here
    // {
    //   url: `${baseUrl}/sitemap-agents.xml`,
    //   lastModified: new Date(),
    //   changeFrequency: 'daily',
    //   priority: 0.9,
    // },
  ];
}

