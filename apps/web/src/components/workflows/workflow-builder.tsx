'use client';

import { createAgentMarketClient } from '@agent-market/sdk';
import { Plus, Save, Trash2 } from 'lucide-react';
import { useCallback, useState, useTransition } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const clientCache: { instance?: ReturnType<typeof createAgentMarketClient> } = {};

const getClient = () => {
  if (!clientCache.instance) {
    clientCache.instance = createAgentMarketClient({
      baseUrl: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:4000',
    });
  }
  return clientCache.instance;
};

const defaultSteps = JSON.stringify(
  [
    { agentId: 'AGENT_ID_1', jobReference: 'research', budget: 5 },
    { agentId: 'AGENT_ID_2', jobReference: 'analysis', budget: 5 },
  ],
  null,
  2,
);

export const WorkflowBuilder = () => {
  const [name, setName] = useState('Sample orchestration');
  const [description, setDescription] = useState('Two-stage research and analysis flow.');
  const [budget, setBudget] = useState(10);
  const [steps, setSteps] = useState(defaultSteps);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  // Pre-filled with authenticated user ID (Ben Stone)
  const [creatorId, setCreatorId] = useState('e9b91865-be00-4b76-a293-446e1be9151c');
  const [parsedSteps, setParsedSteps] = useState<Array<{ agentId: string; jobReference: string; budget: number }>>([]);

  const handleAddStep = useCallback(() => {
    const newSteps = [...parsedSteps, { agentId: '', jobReference: '', budget: 5 }];
    setParsedSteps(newSteps);
    setSteps(JSON.stringify(newSteps, null, 2));
  }, [parsedSteps]);

  const handleRemoveStep = useCallback((index: number) => {
    const newSteps = parsedSteps.filter((_, i) => i !== index);
    setParsedSteps(newSteps);
    setSteps(JSON.stringify(newSteps, null, 2));
  }, [parsedSteps]);

  const handleUpdateStep = useCallback(
    (index: number, field: 'agentId' | 'jobReference' | 'budget', value: string | number) => {
      const newSteps = [...parsedSteps];
      if (field === 'budget') {
        newSteps[index] = { ...newSteps[index], [field]: Number(value) };
      } else {
        newSteps[index] = { ...newSteps[index], [field]: value };
      }
      setParsedSteps(newSteps);
      setSteps(JSON.stringify(newSteps, null, 2));
    },
    [parsedSteps],
  );

  const handleSubmit = () => {
    // Clear previous messages
    setError(null);
    setMessage(null);

    // Validate required fields
    const validationErrors: string[] = [];

    if (!name.trim()) {
      validationErrors.push('Workflow name is required');
    }

    if (!creatorId.trim()) {
      validationErrors.push('Creator ID is required');
    }

    if (budget <= 0) {
      validationErrors.push('Budget must be greater than 0');
    }

    // Parse and validate steps
    let parsed: unknown;
    try {
      parsed = JSON.parse(steps);
      if (!Array.isArray(parsed)) {
        validationErrors.push('Steps must be a JSON array');
      } else if (parsed.length === 0) {
        validationErrors.push('At least one workflow step is required');
      } else {
        // Validate each step
        for (let i = 0; i < parsed.length; i++) {
          const step = parsed[i] as { agentId?: string; jobReference?: string; budget?: number };
          if (!step.agentId || !step.agentId.trim()) {
            validationErrors.push(`Step ${i + 1}: Agent ID is required`);
          }
          if (!step.jobReference || !step.jobReference.trim()) {
            validationErrors.push(`Step ${i + 1}: Job Reference is required`);
          }
          if (step.budget === undefined || step.budget < 0) {
            validationErrors.push(`Step ${i + 1}: Budget must be 0 or greater`);
          }
        }
        setParsedSteps(parsed as Array<{ agentId: string; jobReference: string; budget: number }>);
      }
    } catch (err) {
      validationErrors.push('Steps must be valid JSON. Check syntax and try again.');
    }

    // Show validation errors if any
    if (validationErrors.length > 0) {
      setError(validationErrors.join('. '));
      return;
    }

    startTransition(async () => {
      try {
        const workflow = await getClient().createWorkflow({
          name,
          description,
          creatorId,
          budget,
          steps: parsedSteps,
        });
        setMessage(`Workflow "${workflow.name}" created successfully! You can now run it from the list below.`);
        // Reset form after successful creation
        setName('Sample orchestration');
        setDescription('Two-stage research and analysis flow.');
        setBudget(10);
        setCreatorId('');
        setParsedSteps([]);
        setSteps(defaultSteps);
      } catch (err) {
        console.error('Workflow creation error:', err);
        // Extract more helpful error message
        let errorMessage = 'Failed to create workflow. ';
        if (err instanceof Error) {
          if (err.message.includes('network') || err.message.includes('fetch')) {
            errorMessage += 'Network error - please check your connection and try again.';
          } else if (err.message.includes('401') || err.message.includes('unauthorized')) {
            errorMessage += 'You must be logged in to create workflows.';
          } else if (err.message.includes('403') || err.message.includes('forbidden')) {
            errorMessage += 'You do not have permission to create workflows.';
          } else if (err.message.includes('400')) {
            errorMessage += 'Invalid workflow data. Please check all fields and try again.';
          } else {
            errorMessage += err.message;
          }
        } else {
          errorMessage += 'An unexpected error occurred. Please try again.';
        }
        setError(errorMessage);
      }
    });
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="space-y-2">
        <h2 className="text-4xl font-display text-white">Create Workflow</h2>
        <p className="text-sm text-[var(--text-muted)]">
          Build multi-agent workflows by connecting agents in sequence or parallel. Set budgets,
          define handoffs, and test execution.
        </p>
      </header>

      {/* Main Configuration */}
      <Card className="border-white/70 bg-[var(--surface-raised)]">
        <CardHeader>
          <CardTitle className="font-display">Workflow Details</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-6 md:grid-cols-2">
          <div>
            <label htmlFor="workflow-creator" className="block text-xs uppercase tracking-wide text-[var(--text-muted)] mb-2">
              Creator ID
            </label>
            <input
              id="workflow-creator"
              value={creatorId}
              onChange={(event) => setCreatorId(event.target.value)}
              placeholder="UUID of the workflow owner"
              className="w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)]/50 focus:border-white/40 focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="workflow-name" className="block text-xs uppercase tracking-wide text-[var(--text-muted)] mb-2">
              Workflow Name
            </label>
            <input
              id="workflow-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g., Research → Analysis → Archive"
              className="w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)]/50 focus:border-white/40 focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="workflow-budget" className="block text-xs uppercase tracking-wide text-[var(--text-muted)] mb-2">
              Total Budget (credits)
            </label>
            <input
              id="workflow-budget"
              type="number"
              value={budget}
              onChange={(event) => setBudget(Number(event.target.value))}
              min={1}
              className="w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white focus:border-white/40 focus:outline-none"
            />
          </div>
          <div className="md:col-span-2">
            <label htmlFor="workflow-desc" className="block text-xs uppercase tracking-wide text-[var(--text-muted)] mb-2">
              Description
            </label>
            <textarea
              id="workflow-desc"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
              placeholder="What is this workflow designed to do?"
              className="w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-white placeholder:text-[var(--text-muted)]/50 focus:border-white/40 focus:outline-none"
            />
          </div>
        </CardContent>
      </Card>

      {/* Workflow Steps Builder */}
      <Card className="border-white/70 bg-[var(--surface-raised)]">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="font-display">Workflow Steps</CardTitle>
          <Button size="sm" onClick={handleAddStep} variant="secondary">
            <Plus className="h-4 w-4" />
            Add Step
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {parsedSteps.length === 0 ? (
            <p className="text-sm text-[var(--text-muted)] italic">No steps yet. Click &quot;Add Step&quot; to start building.</p>
          ) : (
            <div className="space-y-3">
              {parsedSteps.map((step, index) => (
                <div key={index} className="flex items-end gap-3 rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] p-4">
                  <div className="flex-1">
                    <label htmlFor={`step-${index}-agent`} className="block text-xs uppercase tracking-wide text-[var(--text-muted)] mb-1">
                      Agent ID
                    </label>
                    <input
                      id={`step-${index}-agent`}
                      value={step.agentId}
                      onChange={(e) => handleUpdateStep(index, 'agentId', e.target.value)}
                      placeholder="e.g., agent_research_001"
                      className="w-full rounded border border-[var(--border-base)] bg-[var(--surface-raised)] px-2 py-1 text-xs text-white placeholder:text-[var(--text-muted)]/50"
                    />
                  </div>
                  <div className="flex-1">
                    <label htmlFor={`step-${index}-job`} className="block text-xs uppercase tracking-wide text-[var(--text-muted)] mb-1">
                      Job Reference
                    </label>
                    <input
                      id={`step-${index}-job`}
                      value={step.jobReference}
                      onChange={(e) => handleUpdateStep(index, 'jobReference', e.target.value)}
                      placeholder="e.g., research"
                      className="w-full rounded border border-[var(--border-base)] bg-[var(--surface-raised)] px-2 py-1 text-xs text-white placeholder:text-[var(--text-muted)]/50"
                    />
                  </div>
                  <div className="w-24">
                    <label htmlFor={`step-${index}-budget`} className="block text-xs uppercase tracking-wide text-[var(--text-muted)] mb-1">
                      Budget
                    </label>
                    <input
                      id={`step-${index}-budget`}
                      type="number"
                      value={step.budget}
                      onChange={(e) => handleUpdateStep(index, 'budget', e.target.value)}
                      min={0}
                      className="w-full rounded border border-[var(--border-base)] bg-white px-2 py-1 text-xs text-white"
                    />
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleRemoveStep(index)}
                    className="text-red-600 hover:bg-red-50"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* JSON Editor (Advanced) */}
      <Card className="border-white/70 bg-[var(--surface-raised)]">
        <CardHeader>
          <CardTitle className="font-display">Advanced: Raw JSON</CardTitle>
        </CardHeader>
        <CardContent>
          <label className="block text-xs uppercase tracking-wide text-[var(--text-muted)] mb-2">
            Steps (JSON Array)
          </label>
          <textarea
            value={steps}
            onChange={(event) => {
              setSteps(event.target.value);
              try {
                const parsed = JSON.parse(event.target.value);
                if (Array.isArray(parsed)) {
                  setParsedSteps(parsed);
                }
              } catch (e) {
                // Ignore parsing errors while typing
              }
            }}
            rows={6}
            className="w-full rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)] px-3 py-2 font-mono text-xs text-white focus:border-white/40 focus:outline-none"
          />
        </CardContent>
      </Card>

      {/* Messages */}
      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {message && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {message}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          onClick={handleSubmit}
          disabled={isPending}
          className="flex-1 rounded-full"
        >
          <Save className="h-4 w-4" />
          {isPending ? 'Creating...' : 'Create Workflow'}
        </Button>
      </div>
    </div>
  );
};

