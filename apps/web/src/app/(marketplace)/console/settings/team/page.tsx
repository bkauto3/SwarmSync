'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks/use-auth';

export default function TeamSettingsPage() {
  const { user } = useAuth();
  const [email, setEmail] = useState('');
  const [isInviting, setIsInviting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleInvite = async () => {
    if (!email.trim()) {
      setMessage({ type: 'error', text: 'Please enter an email address' });
      return;
    }

    setIsInviting(true);
    setMessage(null);

    try {
      // TODO: Implement API call to invite team member
      // await inviteTeamMember({ email });

      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 500));

      setMessage({ type: 'success', text: `Invitation sent to ${email}` });
      setEmail('');
    } catch (error) {
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to send invitation',
      });
    } finally {
      setIsInviting(false);
    }
  };

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>Team Settings</h1>
        <p className="text-sm text-[var(--text-muted)]">Manage your team members and invitations</p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Invite Team Member</CardTitle>
          <CardDescription>
            Send an invitation to add a new member to your organization
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email Address</Label>
            <div className="flex gap-3">
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="colleague@example.com"
                className="flex-1"
              />
              <Button onClick={handleInvite} disabled={isInviting}>
                {isInviting ? 'Sending...' : 'Send Invite'}
              </Button>
            </div>
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Team Members</CardTitle>
          <CardDescription>Current members of your organization</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {user && (
              <div className="flex items-center justify-between rounded-lg border border-white/10 p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/10 text-sm font-semibold text-accent">
                    {user.displayName?.charAt(0) || user.email.charAt(0)}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-[var(--text-primary)]">
                      {user.displayName || 'You'}
                    </div>
                    <div className="text-xs text-[var(--text-muted)]">{user.email}</div>
                  </div>
                </div>
                <span className="rounded-full bg-accent/10 px-3 py-1 text-xs font-medium text-accent">
                  Owner
                </span>
              </div>
            )}

            <div className="rounded-lg border border-dashed border-white/10 p-6 text-center">
              <p className="text-sm text-[var(--text-muted)]">
                No other team members yet. Invite colleagues to collaborate on your agent
                marketplace.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Pending Invitations</CardTitle>
          <CardDescription>Invitations that haven&apos;t been accepted yet</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-dashed border-white/10 p-6 text-center">
            <p className="text-sm text-[var(--text-muted)]">No pending invitations</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
