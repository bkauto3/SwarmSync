import { Metadata } from 'next';
import Link from 'next/link';
import Image from 'next/image';
import { notFound } from 'next/navigation';

import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { Card, CardContent } from '@/components/ui/card';

const authors: Record<
  string,
  {
    name: string;
    bio: string;
    role: string;
    avatar?: string;
    social?: {
      twitter?: string;
      linkedin?: string;
      github?: string;
    };
    posts: Array<{
      slug: string;
      title: string;
      date: string;
    }>;
  }
> = {
  'swarm-sync-team': {
    name: 'Swarm Sync Team',
    role: 'Engineering & Product',
    bio: 'We are a team of engineers and product builders passionate about autonomous AI systems and agent-to-agent commerce. We build the infrastructure that makes autonomous agent marketplaces possible.',
    posts: [
      { slug: 'how-to-build-autonomous-ai-agents', title: 'How to Build Autonomous AI Agents', date: '2025-01-15' },
      { slug: 'multi-agent-orchestration-patterns', title: 'Multi-Agent Orchestration Patterns & Best Practices', date: '2025-01-05' },
      { slug: 'a2a-protocol-future', title: 'A2A Protocol: The Future of Agent-to-Agent Commerce', date: '2024-12-28' },
    ],
  },
};

export async function generateStaticParams() {
  return Object.keys(authors).map((slug) => ({
    slug,
  }));
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const author = authors[params.slug];
  if (!author) {
    return {};
  }

  return {
    title: `${author.name} | Authors | Swarm Sync`,
    description: author.bio,
    alternates: {
      canonical: `https://swarmsync.ai/authors/${params.slug}`,
    },
  };
}

export default function AuthorPage({ params }: { params: { slug: string } }) {
  const author = authors[params.slug];

  if (!author) {
    notFound();
  }

  return (
    <div className="flex min-h-screen flex-col bg-black text-slate-50">
      <Navbar />

      <main className="flex-1 px-4 py-16">
        <div className="mx-auto max-w-4xl space-y-12">
          {/* Header */}
          <div className="space-y-4">
            <Link
              href="/blog"
              className="text-sm text-[var(--text-secondary)] hover:text-white transition-colors inline-block"
            >
              ← Back to Blog
            </Link>
            <div className="flex gap-6 items-start">
              {author.avatar && (
                <Image
                  src={author.avatar}
                  alt={`${author.name}'s avatar`}
                  width={128}
                  height={128}
                  className="rounded-full flex-shrink-0"
                />
              )}
              <div className="flex-1 space-y-2">
                <h1 className="text-4xl font-display text-white">{author.name}</h1>
                <p className="text-lg text-[var(--text-secondary)]">{author.role}</p>
                {author.social && (
                  <div className="flex gap-4 pt-2">
                    {author.social.twitter && (
                      <a
                        href={author.social.twitter}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--text-secondary)] hover:text-white transition-colors"
                      >
                        Twitter
                      </a>
                    )}
                    {author.social.linkedin && (
                      <a
                        href={author.social.linkedin}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--text-secondary)] hover:text-white transition-colors"
                      >
                        LinkedIn
                      </a>
                    )}
                    {author.social.github && (
                      <a
                        href={author.social.github}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--text-secondary)] hover:text-white transition-colors"
                      >
                        GitHub
                      </a>
                    )}
                  </div>
                )}
              </div>
            </div>
            <p className="text-lg text-[var(--text-secondary)] leading-relaxed">{author.bio}</p>
          </div>

          {/* Posts */}
          {author.posts.length > 0 && (
            <section className="space-y-6">
              <h2 className="text-2xl font-display text-white">Articles by {author.name}</h2>
              <div className="space-y-4">
                {author.posts.map((post) => (
                  <Card key={post.slug} className="border-white/10 bg-white/5 hover:border-white/20 transition-colors">
                    <CardContent className="p-6">
                      <Link href={`/blog/${post.slug}`} className="block space-y-2 group">
                        <h3 className="text-xl font-display text-white group-hover:text-[var(--accent-primary)] transition-colors">
                          {post.title}
                        </h3>
                        <time className="text-sm text-[var(--text-secondary)]">
                          {new Date(post.date).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                          })}
                        </time>
                      </Link>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </section>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
