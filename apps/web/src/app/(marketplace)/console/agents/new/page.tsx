'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function ConsoleNewAgentRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/agents/new');
  }, [router]);

  return null;
}
