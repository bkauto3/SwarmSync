'use client';

import Link from 'next/link';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

interface WorkflowStep {
  id: string;
  agentId: string;
  agentName: string;
  input: Record<string, unknown>;
  output?: Record<string, unknown>;
}

interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  steps: WorkflowStep[];
  budget: number;
}

const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
  {
    id: 'research-summary',
    name: 'Research → Summary',
    description: 'Research a topic and generate a comprehensive summary',
    budget: 50,
    steps: [
      {
        id: 'step-1',
        agentId: 'research-agent',
        agentName: 'Research Agent',
        input: {
          topic: 'Latest AI trends in 2024',
          depth: 'comprehensive',
        },
      },
      {
        id: 'step-2',
        agentId: 'summary-agent',
        agentName: 'Summary Agent',
        input: {
          format: 'executive summary',
          length: '1-2 pages',
        },
      },
    ],
  },
  {
    id: 'support-triage',
    name: 'Support Triage → Draft Response',
    description: 'Analyze support ticket and draft a response',
    budget: 30,
    steps: [
      {
        id: 'step-1',
        agentId: 'triage-agent',
        agentName: 'Support Triage Agent',
        input: {
          ticket: {
            subject: 'Customer inquiry',
            priority: 'high',
          },
        },
      },
      {
        id: 'step-2',
        agentId: 'response-agent',
        agentName: 'Response Drafting Agent',
        input: {
          tone: 'professional',
          includeSolution: true,
        },
      },
    ],
  },
  {
    id: 'seo-audit',
    name: 'SEO Audit → Content Plan',
    description: 'Audit website SEO and generate content improvement plan',
    budget: 75,
    steps: [
      {
        id: 'step-1',
        agentId: 'seo-audit-agent',
        agentName: 'SEO Audit Agent',
        input: {
          url: 'https://example.com',
          focusAreas: ['on-page', 'technical', 'content'],
        },
      },
      {
        id: 'step-2',
        agentId: 'content-plan-agent',
        agentName: 'Content Planning Agent',
        input: {
          recommendations: true,
          priority: 'high-impact',
        },
      },
    ],
  },
];

export default function DemoWorkflowsPage() {
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplate | null>(null);
  const [workflowJson, setWorkflowJson] = useState<string>('');
  const [isExporting, setIsExporting] = useState(false);

  const handleSelectTemplate = (template: WorkflowTemplate) => {
    setSelectedTemplate(template);
    setWorkflowJson(
      JSON.stringify(
        {
          name: template.name,
          description: template.description,
          budget: template.budget,
          steps: template.steps,
        },
        null,
        2,
      ),
    );
  };

  const handleExport = () => {
    setIsExporting(true);
    
    // Create downloadable JSON file
    const blob = new Blob([workflowJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `workflow-${selectedTemplate?.id || 'custom'}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    setTimeout(() => setIsExporting(false), 500);
  };

  return (
    <div className="min-h-screen bg-black text-slate-50">
      <div className="mx-auto max-w-6xl space-y-8 px-4 py-12">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-white">🔄 Workflow Builder Demo</h1>
          <p className="text-lg text-slate-400">
            Design and export agent workflows — no signup required
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Templates Sidebar */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-white">Workflow Templates</h2>
            <div className="space-y-3">
              {WORKFLOW_TEMPLATES.map((template) => (
                <Card
                  key={template.id}
                  className={`cursor-pointer transition hover:shadow-lg border-white/10 bg-white/5 ${
                    selectedTemplate?.id === template.id ? 'border-white/30 border-2' : ''
                  }`}
                  onClick={() => handleSelectTemplate(template)}
                >
                  <CardContent className="p-4">
                    <h3 className="font-semibold text-white">{template.name}</h3>
                    <p className="text-sm text-slate-400 mt-1">{template.description}</p>
                    <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                      <span>{template.steps.length} steps</span>
                      <span>${template.budget} budget</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Workflow Editor */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-white">Workflow JSON</h2>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setWorkflowJson('');
                    setSelectedTemplate(null);
                  }}
                  disabled={!workflowJson}
                >
                  Clear
                </Button>
                <Button
                  onClick={handleExport}
                  disabled={!workflowJson || isExporting}
                  className="bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc] text-black hover:shadow-[0_20px_45px_-15px_rgba(0,0,0,0.75)]"
                >
                  {isExporting ? 'Exporting...' : 'Export JSON'}
                </Button>
              </div>
            </div>

            {selectedTemplate && (
              <div className="rounded-lg border border-white/10 bg-white/5 p-4">
                <h3 className="font-semibold text-white mb-2">{selectedTemplate.name}</h3>
                <div className="space-y-2 text-sm text-slate-300">
                  {selectedTemplate.steps.map((step, index) => (
                    <div key={step.id} className="flex items-center gap-2">
                      <span className="font-semibold">{index + 1}.</span>
                      <span>{step.agentName}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <textarea
              value={workflowJson}
              onChange={(e) => setWorkflowJson(e.target.value)}
              placeholder="Select a template or write your own workflow JSON..."
              rows={20}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-4 py-3 font-mono text-sm text-white focus:border-white/30 focus:outline-none placeholder:text-slate-500"
            />

            {workflowJson && (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
                <p className="text-sm text-amber-300">
                  💡 <strong>Note:</strong> To run this workflow, please{' '}
                  <Link href="/register" className="font-semibold underline text-amber-200 hover:text-white">
                    create an account
                  </Link>
                  . You can export the JSON now and import it later.
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="text-center space-y-2">
          <Link href="/" className="text-sm text-slate-400 hover:text-white underline">
            ← Back to Home
          </Link>
          <p className="text-xs text-slate-500">
            Workflow builder is read-only for unauthenticated users. Sign up to execute workflows.
          </p>
        </div>
      </div>
    </div>
  );
}

