'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { BackgroundToggle } from '@/components/settings/background-toggle';
import { useAuth } from '@/hooks/use-auth';

export default function ProfileSettingsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [displayName, setDisplayName] = useState(user?.displayName || '');
  const [email, setEmail] = useState(user?.email || '');
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleSave = async () => {
    setIsSaving(true);
    setMessage(null);

    try {
      // TODO: Implement API call to update user profile
      // await updateUserProfile({ displayName, email });
      
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 500));
      
      setMessage({ type: 'success', text: 'Profile updated successfully' });
    } catch (error) {
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to update profile',
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>Profile Settings</h1>
        <p className="text-sm text-[var(--text-muted)]">Manage your account information and preferences</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Personal Information</CardTitle>
          <CardDescription>Update your name and email address</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="displayName">Display Name</Label>
            <Input
              id="displayName"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your display name"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your.email@example.com"
              disabled
            />
            <p className="text-xs text-[var(--text-muted)]">
              Email cannot be changed. Contact support if you need to update your email.
            </p>
          </div>

          {message && (
            <div
              className={`rounded-lg border px-4 py-3 text-sm ${
                message.type === 'success'
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                  : 'border-destructive/40 bg-destructive/5 text-destructive'
              }`}
            >
              {message.text}
            </div>
          )}

          <div className="flex gap-3">
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? 'Saving...' : 'Save Changes'}
            </Button>
            <Button variant="outline" onClick={() => router.push('/dashboard')}>
              Cancel
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Account Information</CardTitle>
          <CardDescription>View your account details</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label className="text-xs text-[var(--text-muted)]">User ID</Label>
              <p className="mt-1 text-sm font-mono text-[var(--text-primary)]">{user?.id || 'N/A'}</p>
            </div>
            <div>
              <Label className="text-xs text-[var(--text-muted)]">Account Status</Label>
              <p className="mt-1 text-sm text-[var(--text-primary)]">Active</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle font-display>Display Preferences</CardTitle>
          <CardDescription font-ui>Customize your interface appearance</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <BackgroundToggle />
        </CardContent>
      </Card>
    </div>
  );
}

