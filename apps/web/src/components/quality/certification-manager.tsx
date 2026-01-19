'use client';

import { AgentCertificationRecord, createAgentMarketClient } from '@agent-market/sdk';
import { useRouter } from 'next/navigation';
import { useState, useTransition } from 'react';

const CERTIFICATION_STATUSES = [
  'DRAFT',
  'SUBMITTED',
  'QA_TESTS',
  'SECURITY_REVIEW',
  'CERTIFIED',
  'EXPIRED',
  'REVOKED',
] as const;

interface CertificationManagerProps {
  agentId: string;
  certifications: AgentCertificationRecord[];
}

export function CertificationManager({ agentId, certifications }: CertificationManagerProps) {
  const router = useRouter();
  const [createNotes, setCreateNotes] = useState('');
  const [createChecklistId, setCreateChecklistId] = useState('');
  const [advanceCertificationId, setAdvanceCertificationId] = useState(
    certifications[0]?.id ?? '',
  );
  const [advanceStatus, setAdvanceStatus] = useState<string>('SUBMITTED');
  const [statusNotes, setStatusNotes] = useState('');
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const handleCreate = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    startTransition(async () => {
      try {
        setError(null);
        await createAgentMarketClient().createCertification({
          agentId,
          checklistId: createChecklistId || undefined,
          notes: createNotes || undefined,
        });
        setCreateNotes('');
        setCreateChecklistId('');
        router.refresh();
      } catch (err) {
        console.error(err);
        setError('Failed to create certification record.');
      }
    });
  };

  const handleAdvance = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!advanceCertificationId) {
      setError('Select a certification to advance.');
      return;
    }

    startTransition(async () => {
      try {
        setError(null);
        await createAgentMarketClient().advanceCertification(advanceCertificationId, {
          status: advanceStatus,
          notes: statusNotes || undefined,
        });
        setStatusNotes('');
        router.refresh();
      } catch (err) {
        console.error(err);
        setError('Failed to advance certification.');
      }
    });
  };

  return (
    <div className="card space-y-6 p-6">
      <div>
        <h2 className="text-lg font-display text-white">Certification Workflow</h2>
        <p className="text-sm text-[var(--text-muted)]">
          Track review cycles and advance agents through the quality gates defined in your
          checklist.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      <form onSubmit={handleCreate} className="space-y-3 rounded-lg border border-[var(--border-base)] p-4">
        <h3 className="text-sm font-semibold text-white">Create record</h3>
        <input
          placeholder="Checklist ID (optional)"
          className="w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
          value={createChecklistId}
          onChange={(event) => setCreateChecklistId(event.target.value)}
        />
        <textarea
          placeholder="Notes"
          className="w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
          value={createNotes}
          onChange={(event) => setCreateNotes(event.target.value)}
          rows={2}
        />
        <button
          type="submit"
          disabled={isPending}
          className="glass-button bg-accent px-4 py-2 text-xs font-semibold text-carrara disabled:cursor-not-allowed disabled:bg-white/10"
        >
          {isPending ? 'Creating...' : 'Create'}
        </button>
      </form>

      <form onSubmit={handleAdvance} className="space-y-3 rounded-lg border border-[var(--border-base)] p-4">
        <h3 className="text-sm font-semibold text-white">Advance status</h3>
        <select
          className="w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
          value={advanceCertificationId}
          onChange={(event) => setAdvanceCertificationId(event.target.value)}
        >
          <option value="">Select certification</option>
          {certifications.map((certification) => (
            <option key={certification.id} value={certification.id}>
              {certification.status} • {new Date(certification.updatedAt).toLocaleString()}
            </option>
          ))}
        </select>
        <select
          className="w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
          value={advanceStatus}
          onChange={(event) => setAdvanceStatus(event.target.value)}
        >
          {CERTIFICATION_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
        <textarea
          placeholder="Reviewer notes"
          className="w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
          value={statusNotes}
          onChange={(event) => setStatusNotes(event.target.value)}
          rows={2}
        />
        <button
          type="submit"
          disabled={isPending}
          className="glass-button bg-[var(--surface-raised)] px-4 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isPending ? 'Updating...' : 'Advance'}
        </button>
      </form>

      <div className="rounded-lg border border-[var(--border-base)] p-4">
        <h3 className="text-sm font-semibold text-white">Recent activity</h3>
        <ul className="mt-3 space-y-2 text-sm text-[var(--text-muted)]">
          {certifications.slice(0, 4).map((certification) => (
            <li key={certification.id} className="rounded-lg bg-[var(--surface-raised)] p-3">
              <div className="flex justify-between text-xs">
                <span className="font-semibold text-white">{certification.status}</span>
                <span>{new Date(certification.updatedAt).toLocaleDateString()}</span>
              </div>
              {certification.notes && (
                <p className="mt-1 text-xs text-[var(--text-muted)]">{certification.notes}</p>
              )}
            </li>
          ))}
          {certifications.length === 0 && (
            <li className="text-xs text-[var(--text-muted)]">No certification activity yet.</li>
          )}
        </ul>
      </div>
    </div>
  );
}
