import { useAuth } from '../lib/auth';
import { useRouter } from 'next/router';
import { useEffect } from 'react';

export default function AuthWrapper({ children }) {
  const { authenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !authenticated) {
      router.push('/auth/signin');
    }
  }, [authenticated, loading, router]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (!authenticated) {
    return null;
  }

  return children;
}
