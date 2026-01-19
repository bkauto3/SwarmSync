import { redirect } from 'next/navigation';

export default function ProfileRedirect() {
  redirect('/console/settings/profile');
}

