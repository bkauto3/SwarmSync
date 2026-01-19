import crypto from 'crypto';

import { PrismaAdapter } from '@next-auth/prisma-adapter';
import GithubProvider from 'next-auth/providers/github';
import GoogleProvider from 'next-auth/providers/google';

import { prisma } from './prisma';

import type { NextAuthOptions } from 'next-auth';

function resolveEnv(
  label: string,
  keys: string[],
  fallbackValue: string,
) {
  for (const key of keys) {
    const val = process.env[key];
    if (val) {
      return val;
    }
  }
  console.warn(
    `[auth] ${label} is not set. Checked: ${keys.join(
      ', ',
    )}. Using fallback; set the real secret in env for production.`,
  );
  return fallbackValue;
}

const googleClientId = resolveEnv(
  'GOOGLE_CLIENT_ID',
  [
    'GOOGLE_CLIENT_ID',
    'NEXT_PUBLIC_GOOGLE_CLIENT_ID',
    'NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID',
  ],
  'missing-google-client-id',
);

const googleClientSecret = resolveEnv(
  'GOOGLE_CLIENT_SECRET',
  [
    'GOOGLE_CLIENT_SECRET',
    'GOOGLE_OAUTH_CLIENT_SECRET',
    'NEXT_PUBLIC_GOOGLE_CLIENT_SECRET',
  ],
  'missing-google-client-secret',
);

const githubClientId = resolveEnv(
  'GITHUB_CLIENT_ID',
  ['GITHUB_ID', 'GITHUB_CLIENT_ID', 'NEXT_PUBLIC_GITHUB_CLIENT_ID'],
  'missing-github-client-id',
);

const githubClientSecret = resolveEnv(
  'GITHUB_CLIENT_SECRET',
  ['GITHUB_SECRET', 'GITHUB_CLIENT_SECRET', 'NEXT_PUBLIC_GITHUB_CLIENT_SECRET'],
  'missing-github-client-secret',
);

const nextAuthSecret = resolveEnv(
  'NEXTAUTH_SECRET',
  ['NEXTAUTH_SECRET', 'JWT_SECRET'],
  crypto.randomBytes(32).toString('hex'),
);

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  secret: nextAuthSecret,
  session: {
    strategy: 'database', // Use database sessions with PrismaAdapter
  },
  providers: [
    GoogleProvider({
      clientId: googleClientId,
      clientSecret: googleClientSecret,
      allowDangerousEmailAccountLinking: true,
    }),
    GithubProvider({
      clientId: githubClientId,
      clientSecret: githubClientSecret,
      allowDangerousEmailAccountLinking: true,
      authorization: {
        params: {
          scope: 'read:user user:email',
        },
      },
    }),
  ],
  callbacks: {
    async redirect({ url, baseUrl }) {
      // Allows relative callback URLs
      if (url.startsWith("/")) return `${baseUrl}${url}`
      // Allows callback URLs on the same origin
      else if (new URL(url).origin === baseUrl) return url
      return baseUrl
    },
    async signIn({ user, profile }) {
      // Normalize display name for our Prisma schema
      const displayName =
        (profile as { name?: string })?.name ??
        user.name ??
        user.email ??
        'User';

      // Upsert the user into our Prisma User table to satisfy API FKs
      await prisma.user.upsert({
        where: { email: user.email! },
        update: {
          displayName,
          image: user.image ?? null,
          emailVerified: new Date(),
        },
        create: {
          email: user.email!,
          displayName,
          image: user.image ?? null,
          emailVerified: new Date(),
          password: null,
        },
      });
      return true;
    },
    async session({ session, user }) {
      // user is the Prisma User model when using database sessions
      if (session.user && user) {
        session.user.id = user.id;
        session.user.email = user.email;
        session.user.name = (user as { displayName?: string }).displayName ?? user.name ?? user.email;
        session.user.image = user.image ?? undefined;
      }
      return session;
    },
  },
  pages: {
    signIn: '/login',
    error: '/auth/error',
  },
};
