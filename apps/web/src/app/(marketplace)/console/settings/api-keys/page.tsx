'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Copy, Plus, Trash2, Eye, EyeOff, Check } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { serviceAccountsApi, type CreateServiceAccountPayload } from '@/lib/api';

export default function ApiKeysPage() {
  const queryClient = useQueryClient();
  const [isCreating, setIsCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyDescription, setNewKeyDescription] = useState('');
  const [newKeyScopes, setNewKeyScopes] = useState<string[]>([]);
  const [revealedKeys, setRevealedKeys] = useState<Set<string>>(new Set());
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ['service-accounts'],
    queryFn: () => serviceAccountsApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateServiceAccountPayload) => serviceAccountsApi.create(payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['service-accounts'] });
      setIsCreating(false);
      setNewKeyName('');
      setNewKeyDescription('');
      setNewKeyScopes([]);
      // Reveal the new key
      if (data.apiKey) {
        setRevealedKeys(new Set([data.id]));
      }
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => serviceAccountsApi.revoke(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['service-accounts'] });
    },
  });

  const handleCreate = () => {
    if (!newKeyName.trim()) return;
    createMutation.mutate({
      name: newKeyName.trim(),
      description: newKeyDescription.trim() || undefined,
      scopes: newKeyScopes,
    });
  };

  const copyToClipboard = async (text: string, keyId: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedKey(keyId);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const toggleReveal = (id: string) => {
    setRevealedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>API Keys</h1>
          <p className="mt-2 text-sm text-[var(--text-muted)]">
            Create and manage API keys for programmatic access to the Agent Market
          </p>
        </div>
        <Button onClick={() => setIsCreating(true)} disabled={isCreating}>
          <Plus className="mr-2 h-4 w-4" />
          Create API Key
        </Button>
      </header>

      {isCreating && (
        <Card>
          <CardHeader>
            <CardTitle>Create New API Key</CardTitle>
            <CardDescription>
              API keys allow programmatic access to the Agent Market API
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="key-name">Name *</Label>
              <Input
                id="key-name"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="e.g. Production API Key"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="key-description">Description</Label>
              <Textarea
                id="key-description"
                value={newKeyDescription}
                onChange={(e) => setNewKeyDescription(e.target.value)}
                placeholder="Optional description for this API key"
                rows={3}
              />
            </div>
            <div className="flex gap-3">
              <Button onClick={handleCreate} disabled={!newKeyName.trim() || createMutation.isPending}>
                {createMutation.isPending ? 'Creating...' : 'Create Key'}
              </Button>
              <Button variant="outline" onClick={() => setIsCreating(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <Card>
          <CardContent className="p-12 text-center text-[var(--text-muted)]">Loading API keys...</CardContent>
        </Card>
      ) : accounts.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <p className="text-[var(--text-muted)]">No API keys yet</p>
            <p className="mt-2 text-sm text-[var(--text-muted)]">
              Create your first API key to get started with programmatic access
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {accounts.map((account) => {
            const isRevealed = revealedKeys.has(account.id);
            const isCopied = copiedKey === account.id;
            // Find the account with the API key (only available immediately after creation)
            const accountWithKey = createMutation.data?.id === account.id ? createMutation.data : null;
            const apiKey = accountWithKey?.apiKey;

            return (
              <Card key={account.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle>{account.name}</CardTitle>
                      {account.description && (
                        <CardDescription className="mt-1">{account.description}</CardDescription>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-semibold ${
                          account.status === 'ACTIVE'
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {account.status}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => revokeMutation.mutate(account.id)}
                        disabled={account.status !== 'ACTIVE' || revokeMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {apiKey && (
                    <div className="space-y-2">
                      <Label>API Key (save this - it won&apos;t be shown again)</Label>
                      <div className="flex gap-2">
                        <Input
                          value={apiKey}
                          readOnly
                          className="font-mono text-sm"
                          type={isRevealed ? 'text' : 'password'}
                        />
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => toggleReveal(account.id)}
                        >
                          {isRevealed ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => copyToClipboard(apiKey, account.id)}
                        >
                          {isCopied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                        </Button>
                      </div>
                    </div>
                  )}
                  <div className="grid gap-4 text-sm md:grid-cols-2">
                    <div>
                      <Label className="text-xs text-[var(--text-muted)]">Scopes</Label>
                      <p className="mt-1">
                        {account.scopes.length > 0 ? account.scopes.join(', ') : 'No scopes'}
                      </p>
                    </div>
                    <div>
                      <Label className="text-xs text-[var(--text-muted)]">Created</Label>
                      <p className="mt-1">{new Date(account.createdAt).toLocaleDateString()}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
