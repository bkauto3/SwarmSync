import { redirect } from 'next/navigation';

export default function ApiKeysRedirect() {
  redirect('/console/settings/api-keys');
}

