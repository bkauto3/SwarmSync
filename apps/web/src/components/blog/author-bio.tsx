import Link from 'next/link';
import Image from 'next/image';

interface Author {
  name: string;
  bio: string;
  avatar?: string;
  url?: string;
  role?: string;
}

interface AuthorBioProps {
  author: Author;
}

export function AuthorBio({ author }: AuthorBioProps) {
  const AuthorContent = (
    <div className="flex gap-4 items-start p-6 rounded-lg border border-white/10 bg-white/5">
      {author.avatar && (
        <Image
          src={author.avatar}
          alt={`${author.name}'s avatar`}
          width={64}
          height={64}
          className="rounded-full flex-shrink-0"
        />
      )}
      <div className="flex-1 space-y-2">
        <div>
          <h3 className="font-display text-lg text-white">
            {author.url ? (
              <Link href={author.url} className="hover:text-[var(--accent-primary)] transition-colors">
                {author.name}
              </Link>
            ) : (
              author.name
            )}
          </h3>
          {author.role && (
            <p className="text-sm text-[var(--text-secondary)]">{author.role}</p>
          )}
        </div>
        <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{author.bio}</p>
      </div>
    </div>
  );

  return AuthorContent;
}
