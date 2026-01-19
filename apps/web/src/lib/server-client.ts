import { AgentMarketClient, createAgentMarketClient } from '@agent-market/sdk';
import { cookies } from 'next/headers';


const DEFAULT_PRODUCTION_API_ORIGIN = 'https://swarmsync-api.up.railway.app';

let cachedClient: AgentMarketClient | null = null;

export const getAgentMarketClient = (token?: string) => {
  if (!token && cachedClient) {
    return cachedClient;
  }

  // Allow server-side callers to read the JWT cookie automatically when an explicit
  // token is not passed in (avoids unauthenticated billing requests).
  const cookieToken =
    typeof window === 'undefined' ? cookies().get('auth_token')?.value : undefined;

  // In production, use the Railway API URL if environment variables aren't set
  const baseUrl =
    process.env.API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    (process.env.NODE_ENV === 'production' ? DEFAULT_PRODUCTION_API_ORIGIN : 'http://localhost:4000');

  const client = createAgentMarketClient({
    baseUrl,
    kyOptions:
      token || cookieToken
        ? {
            headers: {
              Authorization: `Bearer ${token || cookieToken}`,
            },
          }
        : undefined,
  });

  if (!token) {
    cachedClient = client;
  }

  return client;
};
