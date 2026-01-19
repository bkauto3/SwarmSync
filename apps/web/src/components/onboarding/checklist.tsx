'use client';

import { ArrowRight, Check, Zap } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  action: string;
  href: string;
}

const steps: OnboardingStep[] = [
  {
    id: 'wallet',
    title: 'Fund Your Wallet',
    description: 'Add credits to start hiring agents or purchasing agent services.',
    icon: <Zap className="h-6 w-6" />,
    action: 'Add Credits',
    href: '/console/billing?tab=overview',
  },
  {
    id: 'explore',
    title: 'Explore Agents',
    description: 'Browse our marketplace and find agents that match your needs.',
    icon: <Check className="h-6 w-6" />,
    action: 'Browse Agents',
    href: '/agents',
  },
  {
    id: 'hire',
    title: 'Hire Your First Agent',
    description: 'Request service from an agent or build an automated workflow.',
    icon: <ArrowRight className="h-6 w-6" />,
    action: 'Start Workflow',
    href: '/console/workflows/new',
  },
];

export function OnboardingChecklist({ completedSteps = [] }: { completedSteps?: string[] }) {
  const router = useRouter();
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  const progress = (completedSteps.length / steps.length) * 100;

  return (
    <div className="rounded-2xl border border-[var(--border-base)] bg-gradient-to-r from-white/5 to-transparent p-6 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-display text-lg text-white">Welcome to Swarm Sync!</h3>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            Complete these steps to get the most out of the marketplace
          </p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-[var(--text-muted)] hover:text-white transition-colors text-sm"
        >
          Dismiss
        </button>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-[var(--text-muted)]">Progress</span>
          <span className="font-semibold text-white">{completedSteps.length} of 3</span>
        </div>
        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc] transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {steps.map((step) => {
          const isCompleted = completedSteps.includes(step.id);
          return (
            <div
              key={step.id}
              className="flex items-start gap-4 p-3 rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)]0 hover:bg-[var(--surface-raised)] transition"
            >
              {/* Icon */}
              <div
                className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center text-lg mt-0.5 ${
                  isCompleted
                    ? 'bg-emerald-100 text-emerald-600'
                    : 'bg-[var(--surface-raised)] text-slate-300'
                }`}
              >
                {isCompleted ? <Check className="h-4 w-4" /> : step.icon}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <h4
                  className={`font-semibold text-sm ${
                    isCompleted ? 'text-[var(--text-muted)] line-through' : 'text-white'
                  }`}
                >
                  {step.title}
                </h4>
                <p className="text-xs text-[var(--text-muted)] mt-0.5">{step.description}</p>
              </div>

              {/* Action */}
              {!isCompleted && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => router.push(step.href)}
                  className="flex-shrink-0 text-slate-300 hover:text-slate-300 hover:bg-[var(--surface-raised)]"
                >
                  {step.action}
                  <ArrowRight className="h-3 w-3 ml-1" />
                </Button>
              )}
            </div>
          );
        })}
      </div>

      {/* Completion Message */}
      {completedSteps.length === 3 && (
        <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-4 text-center">
          <p className="text-sm font-semibold text-emerald-900">
            🎉 You&apos;re all set! Start exploring and collaborating with agents.
          </p>
        </div>
      )}
    </div>
  );
}
