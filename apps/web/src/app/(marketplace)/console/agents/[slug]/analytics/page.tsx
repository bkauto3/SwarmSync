'use client';

import { useRouter, useParams } from 'next/navigation';
import { useEffect } from 'react';

export default function ConsoleAgentAnalyticsRedirect() {
  const router = useRouter();
  const params = useParams();

  useEffect(() => {
    if (params?.slug) {
      router.replace(`/agents/${params.slug}/analytics`);
    }
  }, [router, params?.slug]);

  return null;
}
