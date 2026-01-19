import { DefaultSession } from 'next-auth';

declare module 'next-auth' {
  interface Session {
    user?: {
      id?: string;
      provider?: string;
      role?: string;
      betaAccess?: boolean;
      providerBeta?: boolean;
    } & DefaultSession['user'];
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    provider?: string;
    id?: string;
    role?: string;
    betaAccess?: boolean;
    providerBeta?: boolean;
  }
}
