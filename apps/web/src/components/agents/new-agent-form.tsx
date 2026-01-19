'use client';

import { useMutation } from '@tanstack/react-query';
import { Loader2, CheckCircle2, ArrowRight, AlertCircle, Upload, FileText, X } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useMemo, useState, useRef, useEffect } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useAuth } from '@/hooks/use-auth';
import { agentsApi, testingApi, type CreateAgentPayload, type AgentBudgetPayload } from '@/lib/api';
import { cn } from '@/lib/utils';

const steps = [
  {
    key: 'details',
    title: 'Agent details',
    description: 'Name, description, and visibility',
  },
  {
    key: 'capabilities',
    title: 'Capabilities & pricing',
    description: 'Categories, skills, pricing model',
  },
  {
    key: 'schemas',
    title: 'AP2 schema',
    description: 'Endpoint and IO contracts',
  },
  {
    key: 'budgets',
    title: 'Budgets & guardrails',
    description: 'Wallet controls and approvals',
  },
] as const;

const categoryOptions = ['sales', 'marketing', 'support', 'operations', 'finance', 'product'];
const _capabilityOptions = [
  'lead_generation',
  'quality_review',
  'workflow_orchestration',
  'research',
  'data_analysis',
  'comms',
  'spec_writing',
  'security_review',
];
const pricingModels = [
  { value: 'per_execution', label: 'Per execution' },
  { value: 'per_lead', label: 'Per lead' },
  { value: 'retainer', label: 'Retainer' },
  { value: 'usage_based', label: 'Usage based' },
];

type Visibility = 'PUBLIC' | 'PRIVATE' | 'ORGANIZATION';

export default function NewAgentForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isLoading } = useAuth();

  const [currentStep, setCurrentStep] = useState(0);
  const [visibility, setVisibility] = useState<Visibility>('PUBLIC');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const [selectedCategories, setSelectedCategories] = useState<string[]>(['sales']);
  const [selectedCapabilities, setSelectedCapabilities] = useState<string[]>(['lead_generation']);
  const [_customCapability, _setCustomCapability] = useState('');
  const [pricingModel, setPricingModel] = useState(pricingModels[0]?.value ?? 'per_execution');
  const [basePrice, setBasePrice] = useState('250');

  const [ap2Endpoint, setAp2Endpoint] = useState('');
  const [inputSchemaText, setInputSchemaText] = useState(
    JSON.stringify(
      {
        type: 'object',
        properties: {
          objective: { type: 'string' },
          budget: { type: 'number' },
        },
        required: ['objective'],
      },
      null,
      2,
    ),
  );
  const [outputSchemaText, setOutputSchemaText] = useState(
    JSON.stringify(
      {
        type: 'object',
        properties: {
          summary: { type: 'string' },
          attachments: { type: 'array', items: { type: 'string' } },
        },
      },
      null,
      2,
    ),
  );
  const [schemaErrors, setSchemaErrors] = useState<{ input?: string; output?: string }>({});

  const [monthlyLimit, setMonthlyLimit] = useState('500');
  const [perTransactionLimit, setPerTransactionLimit] = useState('150');
  const [approvalThreshold, setApprovalThreshold] = useState('50');
  const [autoReload, _setAutoReload] = useState(true);
  const [runBaselineAfterDeploy, _setRunBaselineAfterDeploy] = useState(true);

  const [errorMessage, setErrorMessage] = useState('');
  const [createdAgent, setCreatedAgent] = useState<{
    id: string;
    slug: string;
    name: string;
  } | null>(null);
  const [importedConfig, setImportedConfig] = useState<{
    name?: string;
    description?: string;
    categories?: string[];
    tags?: string[];
    pricingModel?: string;
    basePriceCents?: number;
    visibility?: Visibility;
    ap2Endpoint?: string;
    inputSchema?: Record<string, unknown>;
    outputSchema?: Record<string, unknown>;
  } | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const creationMutation = useMutation({
    mutationFn: async () => {
      if (!user) {
        throw new Error('You must be signed in to create agents.');
      }

      const inputSchema = parseSchema(inputSchemaText, 'input');
      const outputSchema = parseSchema(outputSchemaText, 'output');

      setSchemaErrors({
        input: inputSchema.error,
        output: outputSchema.error,
      });

      if (inputSchema.error || outputSchema.error) {
        throw new Error('Fix schema validation errors to continue.');
      }

      const basePriceNumber = normalizeCurrency(basePrice);

      const payload: CreateAgentPayload = {
        name: name.trim(),
        description: description.trim(),
        categories: selectedCategories,
        tags: selectedCapabilities,
        pricingModel,
        visibility,
        basePriceCents:
          basePriceNumber !== undefined ? Math.round(basePriceNumber * 100) : undefined,
        inputSchema: inputSchema.value,
        outputSchema: outputSchema.value,
        ap2Endpoint: ap2Endpoint.trim() || undefined,
        creatorId: user.id,
      };

      const agent = await agentsApi.create(payload);

      // Only update budget if user provided values
      const monthlyLimitValue = normalizeCurrency(monthlyLimit);
      if (monthlyLimitValue !== undefined || perTransactionLimit || approvalThreshold) {
        const budgetPayload: AgentBudgetPayload = {
          monthlyLimit: monthlyLimitValue ?? 500, // Default to $500/month
          perTransactionLimit: normalizeCurrency(perTransactionLimit) ?? null,
          approvalThreshold: normalizeCurrency(approvalThreshold) ?? null,
          autoReload,
        };

        await agentsApi.updateBudget(agent.id, budgetPayload);
      }
      return agent;
    },
    onSuccess: async (agent) => {
      setCreatedAgent({ id: agent.id, slug: agent.slug, name: agent.name });
      setErrorMessage('');

      // Run baseline test suite if enabled
      if (runBaselineAfterDeploy) {
        try {
          // Get the swarm baseline suite
          const suites = await testingApi.getRecommendedSuites();
          const baselineSuite = suites.find((s) => s.slug === 'swarm_smoke_test');

          if (baselineSuite) {
            await testingApi.startRun({
              agentId: agent.id,
              suiteId: baselineSuite.id,
            });
          }
        } catch (error) {
          console.error('Failed to start baseline test run:', error);
        }
      }
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : 'Unable to create agent. Please try again.';
      setErrorMessage(message);
    },
  });

  const stepComplete = (index: number) => index < currentStep;
  const stepActive = (index: number) => index === currentStep;

  const canAdvance = (() => {
    switch (currentStep) {
      case 0:
        return name.trim().length >= 3 && description.trim().length >= 20;
      case 1:
        return selectedCategories.length > 0 && pricingModel.length > 0;
      case 2:
        return ap2Endpoint.trim().length > 0;
      case 3:
        return true;
      default:
        return false;
    }
  })();

  useEffect(() => {
    if (searchParams.get('import') === 'true' && fileInputRef.current) {
      setTimeout(() => {
        fileInputRef.current?.click();
      }, 100);
    }
  }, [searchParams]);

  const disableNav = creationMutation.isPending;

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setImportError(null);

    try {
      const text = await file.text();
      let config: Record<string, unknown>;

      if (file.name.endsWith('.json') || file.name.endsWith('.yaml') || file.name.endsWith('.yml')) {
        try {
          config = JSON.parse(text);
        } catch (parseError) {
          throw new Error(
            `Failed to parse JSON: ${parseError instanceof Error ? parseError.message : 'Invalid JSON format'}`,
          );
        }
      } else {
        throw new Error('Unsupported file type. Please upload a .json file.');
      }

      if (typeof config !== 'object' || config === null || Array.isArray(config)) {
        throw new Error('Invalid configuration file format.');
      }

      const imported: typeof importedConfig = {};
      let fieldsPopulated = 0;

      if (typeof config.name === 'string' && config.name.trim()) {
        imported.name = config.name.trim();
        setName(config.name.trim());
        fieldsPopulated++;
      }

      if (typeof config.description === 'string' && config.description.trim()) {
        imported.description = config.description.trim();
        setDescription(config.description.trim());
        fieldsPopulated++;
      }

      if (Array.isArray(config.categories) && config.categories.length > 0) {
        imported.categories = config.categories.filter((c): c is string => typeof c === 'string');
        if (imported.categories.length > 0) {
          setSelectedCategories(imported.categories);
          fieldsPopulated++;
        }
      }

      if (Array.isArray(config.tags) && config.tags.length > 0) {
        imported.tags = config.tags.filter((t): t is string => typeof t === 'string');
        if (imported.tags.length > 0) {
          setSelectedCapabilities(imported.tags);
          fieldsPopulated++;
        }
      }

      if (typeof config.pricingModel === 'string' && config.pricingModel.trim()) {
        imported.pricingModel = config.pricingModel.trim();
        setPricingModel(config.pricingModel.trim());
        fieldsPopulated++;
      }

      if (typeof config.basePriceCents === 'number' && config.basePriceCents >= 0) {
        imported.basePriceCents = config.basePriceCents;
        setBasePrice(String(config.basePriceCents / 100));
        fieldsPopulated++;
      }

      if (config.visibility === 'PUBLIC' || config.visibility === 'PRIVATE' || config.visibility === 'ORGANIZATION') {
        imported.visibility = config.visibility;
        setVisibility(config.visibility);
        fieldsPopulated++;
      }

      if (typeof config.ap2Endpoint === 'string' && config.ap2Endpoint.trim()) {
        imported.ap2Endpoint = config.ap2Endpoint.trim();
        setAp2Endpoint(config.ap2Endpoint.trim());
        fieldsPopulated++;
      }

      if (config.inputSchema && typeof config.inputSchema === 'object' && !Array.isArray(config.inputSchema)) {
        imported.inputSchema = config.inputSchema as Record<string, unknown>;
        setInputSchemaText(JSON.stringify(config.inputSchema, null, 2));
        fieldsPopulated++;
      }

      if (config.outputSchema && typeof config.outputSchema === 'object' && !Array.isArray(config.outputSchema)) {
        imported.outputSchema = config.outputSchema as Record<string, unknown>;
        setOutputSchemaText(JSON.stringify(config.outputSchema, null, 2));
        fieldsPopulated++;
      }

      setImportedConfig(imported);

      if (fieldsPopulated === 0) {
        throw new Error('No valid fields found in the configuration file.');
      }

      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to parse configuration file';
      setImportError(message);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const clearImportedConfig = () => {
    setImportedConfig(null);
    setImportError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6 rounded-[3rem] border border-[var(--border-base)] bg-[var(--surface-raised)] p-10 text-[var(--text-primary)]">
        <h1 className="text-3xl font-display">Loading...</h1>
        <p className="text-sm text-[var(--text-muted)]">Verifying your authentication...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="space-y-6 rounded-[3rem] border border-[var(--border-base)] bg-[var(--surface-raised)] p-10 text-[var(--text-primary)]">
        <h1 className="text-3xl font-display">Authentication Required</h1>
        <p className="text-sm text-[var(--text-muted)]">
          You need to be signed in to create and deploy agents on the marketplace.
        </p>
        <p className="text-sm text-[var(--text-muted)]">
          If you&apos;re already signed in and seeing this message, your session may have expired.
          Please sign in again.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => router.push('/login')} className="w-fit">
            Sign in
          </Button>
          <Button variant="outline" onClick={() => router.push('/providers')} className="w-fit">
            Apply as Provider
          </Button>
        </div>
        <p className="text-xs text-[var(--text-muted)]">
          Want to list your agent on the marketplace?{' '}
          <a href="/providers" className="text-[var(--accent)] hover:underline">
            Apply to become a provider
          </a>
          {' '}to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.35em] text-[var(--text-muted)]">Agents</p>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-4xl font-display text-[var(--text-primary)]">Launch a new agent</h1>
            <p className="mt-2 max-w-2xl text-sm text-[var(--text-muted)]">
              Capture the basics, declare pricing and schemas, then lock budgets.
            </p>
          </div>
          <Badge variant="accent" className="text-xs uppercase tracking-wide">
            Guided setup
          </Badge>
        </div>
      </header>

      <Card className="border-[var(--border-base)] bg-[var(--surface-raised)]/70">
        <CardHeader>
          <CardTitle className="text-sm font-display uppercase tracking-wide text-[var(--text-muted)]">
            Import Agent Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <p className="text-sm text-[var(--text-muted)]">
              Upload a JSON file to pre-fill the form.
            </p>
            <div className="flex items-center gap-4">
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,.yaml,.yml"
                className="hidden"
                onChange={handleFileUpload}
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-2"
              >
                <Upload className="h-4 w-4" />
                Upload Config File
              </Button>
              {importedConfig && (
                <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                  <FileText className="h-4 w-4" />
                  <span>Config loaded</span>
                  <button
                    type="button"
                    onClick={clearImportedConfig}
                    className="ml-2 rounded p-1 hover:bg-emerald-100"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
            {importError && (
              <div className="rounded-lg border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                <p className="font-semibold">Import failed</p>
                <p className="mt-1">{importError}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <ol className="flex flex-wrap gap-4 rounded-xl border border-[var(--border-base)] bg-[var(--surface-base)] p-4">
        {steps.map((step, index) => {
          const status = stepActive(index) ? 'active' : stepComplete(index) ? 'done' : 'upcoming';
          return (
            <li
              key={step.key}
              className={cn(
                'flex flex-1 min-w-[220px] items-center gap-3 rounded-xl border px-4 py-3 text-sm transition',
                status === 'done' && 'border-[var(--accent-primary)]/30 bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]',
                status === 'active' && 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/5 text-[var(--accent-primary)]',
                status === 'upcoming' && 'border-[var(--border-base)]/50 text-[var(--text-muted)]',
              )}
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full border border-current text-xs font-semibold">
                {status === 'done' ? <CheckCircle2 className="h-4 w-4" /> : index + 1}
              </div>
              <div>
                <div className="font-semibold text-[var(--text-primary)]">{step.title}</div>
                <div className="text-xs text-[var(--text-secondary)]">{step.description}</div>
              </div>
            </li>
          );
        })}
      </ol>

      {errorMessage && (
        <div className="flex items-center gap-3 rounded-2xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {errorMessage}
        </div>
      )}

      {createdAgent ? (
        <Card className="border-emerald-200 bg-emerald-50/80">
          <CardHeader>
            <CardTitle className="text-emerald-800">Agent deployed</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-emerald-900">
            <p>
              <strong>{createdAgent.name}</strong> is now live.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button onClick={() => router.push(`/agents/${createdAgent.slug}`)}>
                View agent profile
              </Button>
              <Button variant="outline" onClick={() => router.push('/agents')}>
                Return to agents
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setCreatedAgent(null);
                  setCurrentStep(0);
                }}
              >
                Create another
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-[var(--border-base)]">
          <CardHeader className="pb-4">
            <CardTitle className="text-2xl font-display text-[var(--text-primary)]">
              {steps[currentStep].title}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">{renderStep()}</CardContent>
        </Card>
      )}

      {!createdAgent && (
        <div className="flex flex-wrap items-center justify-between gap-4">
          <Button
            variant="outline"
            onClick={() => setCurrentStep((prev) => Math.max(prev - 1, 0))}
            disabled={currentStep === 0 || disableNav}
          >
            Back
          </Button>
          <Button
            className="flex items-center gap-2"
            onClick={() => {
              if (currentStep === steps.length - 1) {
                creationMutation.mutate();
              } else {
                setCurrentStep((prev) => Math.min(prev + 1, steps.length - 1));
              }
            }}
            disabled={!canAdvance || disableNav}
          >
            {creationMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Provisioning
              </>
            ) : currentStep === steps.length - 1 ? (
              <>
                Launch agent <ArrowRight className="h-4 w-4" />
              </>
            ) : (
              <>
                Next <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  );

  function renderStep() {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="agent-name">Agent name</Label>
              <Input
                id="agent-name"
                value={name}
                placeholder="E.g. Apollo Pipeline Orchestrator"
                onChange={(event) => setName(event.target.value)}
              />
              {name.length > 0 && name.trim().length < 3 && (
                <p className="mt-1 text-xs text-amber-500">Name must be at least 3 characters.</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="agent-description">Description</Label>
              <Textarea
                id="agent-description"
                value={description}
                placeholder="Describe what the agent does..."
                onChange={(event) => setDescription(event.target.value)}
              />
              {description.length > 0 && description.trim().length < 20 && (
                <p className="mt-1 text-xs text-amber-500">
                  Description must be at least 20 characters (current: {description.trim().length}).
                </p>
              )}
            </div>
            <div className="space-y-3">
              <Label>Visibility</Label>
              <div className="flex flex-wrap gap-3">
                {(['PUBLIC', 'PRIVATE', 'ORGANIZATION'] as Visibility[]).map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setVisibility(option)}
                    className={cn(
                      'rounded-2xl border px-4 py-2 text-sm transition',
                      visibility === option
                        ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]'
                        : 'border-[var(--border-base)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
                    )}
                  >
                    {option === 'PUBLIC' && 'Public'}
                    {option === 'ORGANIZATION' && 'Organization'}
                    {option === 'PRIVATE' && 'Private'}
                  </button>
                ))}
              </div>
            </div>
          </div>
        );
      case 1:
        return (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label>Categories</Label>
              <div className="flex flex-wrap gap-2">
                {categoryOptions.map((category) => {
                  const isSelected = selectedCategories.includes(category);
                  return (
                    <button
                      key={category}
                      type="button"
                      onClick={() =>
                        toggleSelection(category, selectedCategories, setSelectedCategories)
                      }
                      className={cn(
                        'rounded-full border px-4 py-2 text-xs uppercase tracking-wide transition',
                        isSelected
                          ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]'
                          : 'border-[var(--border-base)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
                      )}
                    >
                      {category}
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Pricing model</Label>
                <div className="grid gap-2">
                  {pricingModels.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setPricingModel(option.value)}
                      className={cn(
                        'w-full rounded-2xl border px-4 py-3 text-left text-sm',
                        pricingModel === option.value
                          ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]'
                          : 'border-[var(--border-base)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
                      )}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="base-price">Base price (USD)</Label>
                <Input
                  id="base-price"
                  type="number"
                  min="0"
                  step="25"
                  value={basePrice}
                  onChange={(event) => setBasePrice(event.target.value)}
                />
              </div>
            </div>
          </div>
        );
      case 2:
        return (
          <div className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="ap2-endpoint">AP2 endpoint</Label>
              <Input
                id="ap2-endpoint"
                placeholder="https://agents.example.com/api/v1/handle"
                value={ap2Endpoint}
                onChange={(event) => setAp2Endpoint(event.target.value)}
              />
            </div>
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="input-schema">Input schema (JSON)</Label>
                <Textarea
                  id="input-schema"
                  value={inputSchemaText}
                  onChange={(event) => setInputSchemaText(event.target.value)}
                  className="bg-[var(--surface-raised)] text-[var(--text-primary)] border-[var(--border-base)] font-mono text-xs"
                />
                {schemaErrors.input && (
                  <p className="text-xs text-destructive">{schemaErrors.input}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="output-schema">Output schema (JSON)</Label>
                <Textarea
                  id="output-schema"
                  value={outputSchemaText}
                  onChange={(event) => setOutputSchemaText(event.target.value)}
                  className="bg-[var(--surface-raised)] text-[var(--text-primary)] border-[var(--border-base)] font-mono text-xs"
                />
                {schemaErrors.output && (
                  <p className="text-xs text-destructive">{schemaErrors.output}</p>
                )}
              </div>
            </div>
          </div>
        );
      case 3:
        return (
          <div className="space-y-6">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="monthly-limit">Monthly limit (USD)</Label>
                <Input
                  id="monthly-limit"
                  type="number"
                  min="0"
                  step="50"
                  placeholder="500"
                  value={monthlyLimit}
                  onChange={(event) => setMonthlyLimit(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="txn-limit">Per-transaction ceiling</Label>
                <Input
                  id="txn-limit"
                  type="number"
                  min="0"
                  step="10"
                  value={perTransactionLimit}
                  onChange={(event) => setPerTransactionLimit(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="auto-approve">Auto-approval threshold</Label>
                <Input
                  id="auto-approve"
                  type="number"
                  min="0"
                  step="10"
                  value={approvalThreshold}
                  onChange={(event) => setApprovalThreshold(event.target.value)}
                />
              </div>
            </div>
          </div>
        );
      default:
        return null;
    }
  }

  function toggleSelection(value: string, selected: string[], setter: (next: string[]) => void) {
    if (selected.includes(value)) {
      setter(selected.filter((item) => item !== value));
      return;
    }
    if (selected.length >= 8) {
      return;
    }
    setter([...selected, value]);
  }

  function normalizeCurrency(value: string) {
    const numeric = Number.parseFloat(value);
    return Number.isFinite(numeric) ? Number(numeric.toFixed(2)) : undefined;
  }

  function parseSchema(value: string, label: 'input' | 'output') {
    if (!value.trim()) {
      return { value: undefined, error: undefined };
    }
    try {
      return { value: JSON.parse(value), error: undefined };
    } catch (error) {
      return {
        value: undefined,
        error: `Invalid ${label} schema JSON`,
      };
    }
  }
}
