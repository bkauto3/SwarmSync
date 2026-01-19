// Layout for demo routes - prevents static generation
export const dynamic = 'force-dynamic';
export const dynamicParams = true;
export const revalidate = 0;

import type { ReactNode } from 'react';

export default function DemoLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}

