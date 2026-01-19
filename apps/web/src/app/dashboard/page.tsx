import { redirect } from 'next/navigation';

export default function DashboardAliasPage() {
  // Many parts of the app (and auth callbacks) still use /dashboard.
  // The actual console landing page lives under /console/overview.
  redirect('/console/overview');
}


