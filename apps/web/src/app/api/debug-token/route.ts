import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth-options';
import { getToken } from 'next-auth/jwt';

export async function GET(request: Request) {
  try {
    // Get session (server-side)
    const session = await getServerSession(authOptions);

    // Get JWT token (like middleware does)
    const token = await getToken({
      req: request as any,
      secret: process.env.NEXTAUTH_SECRET,
    });

    return NextResponse.json({
      session: {
        user: session?.user ?? null,
        exists: !!session,
      },
      token: {
        email: token?.email ?? null,
        role: (token as any)?.role ?? null,
        betaAccess: (token as any)?.betaAccess ?? null,
        providerBeta: (token as any)?.providerBeta ?? null,
        exists: !!token,
        fullToken: token ?? null,
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to get token info', details: String(error) },
      { status: 500 }
    );
  }
}
