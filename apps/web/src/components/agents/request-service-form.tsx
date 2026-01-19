'use client';

import { useMutation } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/hooks/use-auth';
import { useOwnedAgents } from '@/hooks/use-owned-agents';
import { ap2Api } from '@/lib/api';

interface RequestServiceFormProps {
  responderAgentId: string;
  responderAgentName: string;
}

export function RequestServiceForm({ responderAgentId, responderAgentName }: RequestServiceFormProps) {
  const { isAuthenticated } = useAuth();
  const { data: ownedAgents = [], isLoading } = useOwnedAgents();
  const [requesterAgentId, setRequesterAgentId] = useState('');
  const [requestedService, setRequestedService] = useState(`Engage ${responderAgentName}`);
  const [budget, setBudget] = useState('250');
  const [notes, setNotes] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!requesterAgentId && ownedAgents.length > 0) {
      setRequesterAgentId(ownedAgents[0].id);
    }
  }, [ownedAgents, requesterAgentId]);

  const mutation = useMutation({
    mutationFn: () =>
      ap2Api.requestService({
        requesterAgentId,
        responderAgentId,
        requestedService,
        budget: Number(budget),
        notes,
      }),
    onSuccess: () => {
      setSuccessMessage('Negotiation created! Monitor progress from the console.');
      setErrorMessage('');
      setNotes('');
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : 'Unable to start negotiation. Try again.';
      setErrorMessage(message);
      setSuccessMessage('');
    },
  });

  if (!isAuthenticated) {
    return (
      <div className="space-y-3 rounded-2xl border border-[var(--border-base)] bg-[var(--surface-raised)] p-6 text-sm text-white">
        <p className="font-semibold">Sign in to request services</p>
        <p className="text-xs text-[var(--text-muted)]">
          Connect your organization wallet and agents to initiate AP2 negotiations directly from the
          marketplace.
        </p>
        <Button asChild>
          <a href="/login">Go to login</a>
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-[var(--border-base)] bg-[var(--surface-raised)] p-6 text-sm text-white">
        Loading your agents...
      </div>
    );
  }

  if (!ownedAgents.length) {
    return (
      <div className="space-y-3 rounded-2xl border border-dashed border-[var(--border-base)] bg-white/60 p-6 text-sm text-white">
        <p className="font-semibold">No requester agents found</p>
        <p className="text-xs text-[var(--text-muted)]">
          Deploy an agent from the console first, then return here to initiate AP2 negotiations.
        </p>
        <Button asChild>
          <a href="/agents/new">Create agent</a>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-[2rem] border border-[var(--border-base)] bg-[var(--surface-raised)] p-6 shadow-brand-panel">
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-[0.3em] text-muted-foreground">
          Request service
        </h3>
        <p className="text-xs text-muted-foreground">
          Pick which of your agents is requesting help, define the service, and set a provisional budget.
        </p>
      </div>

      <div className="space-y-2">
        <Label>Requester agent</Label>
        <Select value={requesterAgentId} onValueChange={setRequesterAgentId}>
          <SelectTrigger className="rounded-full">
            <SelectValue placeholder="Choose an agent" />
          </SelectTrigger>
          <SelectContent>
            {ownedAgents.map((agent) => (
              <SelectItem key={agent.id} value={agent.id}>
                {agent.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="requested-service">Requested service</Label>
        <Input
          id="requested-service"
          value={requestedService}
          onChange={(event) => setRequestedService(event.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="budget">Budget (USD)</Label>
        <Input
          id="budget"
          type="number"
          min="1"
          step="25"
          value={budget}
          onChange={(event) => setBudget(event.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="notes">Notes</Label>
        <Textarea
          id="notes"
          placeholder="Share requirements, SLA expectations, or payload hints."
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />
      </div>

      {successMessage && <p className="text-sm text-emerald-600">{successMessage}</p>}
      {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

      <Button
        className="w-full rounded-full"
        onClick={() => mutation.mutate()}
        disabled={
          mutation.isPending ||
          !requesterAgentId ||
          !requestedService.trim() ||
          Number.isNaN(Number(budget)) ||
          Number(budget) <= 0
        }
      >
        {mutation.isPending ? 'Sending...' : 'Send request'}
      </Button>
    </div>
  );
}
