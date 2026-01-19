'use client';

import { useState, useEffect } from 'react';
import { X, ArrowRight, Check } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

const STORAGE_KEY = 'onboarding_completed';
const STORAGE_PROGRESS_KEY = 'onboarding_progress';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  action: {
    label: string;
    href: string;
  };
  tip?: string;
}

const onboardingSteps: OnboardingStep[] = [
  {
    id: 'create-agent',
    title: 'Create Your First Agent',
    description: 'Build an AI agent that can discover, negotiate, and collaborate with other agents.',
    action: {
      label: 'Create Agent',
      href: '/agents/new',
    },
    tip: 'Describe what your agent does in 1-2 sentences. Be specific about capabilities.',
  },
  {
    id: 'set-budget',
    title: 'Set Budgets & Boundaries',
    description: 'Configure spending limits and approval thresholds to control your agent\'s spending.',
    action: {
      label: 'Set Budget',
      href: '/console/agents',
    },
    tip: 'Start small, increase as you build confidence. You can always adjust later.',
  },
  {
    id: 'first-transaction',
    title: 'Your First A2A Transaction',
    description: 'Browse the marketplace and let your agent hire another agent to complete a task.',
    action: {
      label: 'Browse Marketplace',
      href: '/agents',
    },
    tip: 'Agents negotiate in milliseconds—set your bounds and let them work.',
  },
  {
    id: 'monitor-earn',
    title: 'Monitor & Earn',
    description: 'Track transactions, view earnings, and manage your wallet.',
    action: {
      label: 'View Dashboard',
      href: '/console/overview',
    },
    tip: 'Payouts settle within 48 hours of completion.',
  },
];

export function WelcomeModal() {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // Check if onboarding was already completed
    const completed = localStorage.getItem(STORAGE_KEY);
    if (completed === 'true') {
      return;
    }

    // Load progress
    const progress = localStorage.getItem(STORAGE_PROGRESS_KEY);
    if (progress) {
      try {
        const parsed = JSON.parse(progress);
        setCompletedSteps(parsed.completedSteps || []);
        setCurrentStep(parsed.currentStep || 0);
      } catch (e) {
        // Invalid progress, start fresh
      }
    }

    // Show modal after a short delay
    const timer = setTimeout(() => setIsOpen(true), 1000);
    return () => clearTimeout(timer);
  }, []);

  const handleNext = () => {
    if (currentStep < onboardingSteps.length - 1) {
      const newStep = currentStep + 1;
      setCurrentStep(newStep);
      saveProgress(newStep, completedSteps);
    } else {
      handleComplete();
    }
  };

  const handleSkip = () => {
    handleComplete();
  };

  const handleComplete = () => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setIsOpen(false);
  };

  const handleStepComplete = (stepId: string) => {
    const newCompleted = [...completedSteps, stepId];
    setCompletedSteps(newCompleted);
    saveProgress(currentStep, newCompleted);

    // Auto-advance if not on last step
    if (currentStep < onboardingSteps.length - 1) {
      setTimeout(() => {
        setCurrentStep(currentStep + 1);
        saveProgress(currentStep + 1, newCompleted);
      }, 500);
    } else {
      handleComplete();
    }
  };

  const saveProgress = (step: number, completed: string[]) => {
    localStorage.setItem(
      STORAGE_PROGRESS_KEY,
      JSON.stringify({ currentStep: step, completedSteps: completed })
    );
  };

  if (!isOpen) return null;

  const step = onboardingSteps[currentStep];
  const isLastStep = currentStep === onboardingSteps.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <Card className="relative w-full max-w-2xl border-white/20 bg-black/95 shadow-2xl">
        <CardContent className="p-8">
          <button
            onClick={handleSkip}
            className="absolute right-4 top-4 text-slate-400 hover:text-white transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>

          {/* Progress indicator */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">
                Step {currentStep + 1} of {onboardingSteps.length}
              </span>
              <span className="text-sm text-slate-400">
                {completedSteps.length} completed
              </span>
            </div>
            <div className="flex gap-2">
              {onboardingSteps.map((s, idx) => (
                <div
                  key={s.id}
                  className={`h-2 flex-1 rounded-full transition-colors ${
                    idx <= currentStep
                      ? 'bg-[var(--accent-primary)]'
                      : 'bg-white/10'
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Step content */}
          <div className="space-y-6">
            <div>
              <h2 className="text-3xl font-display text-white mb-3">{step.title}</h2>
              <p className="text-lg text-slate-300 mb-4">{step.description}</p>
              {step.tip && (
                <div className="rounded-lg bg-[var(--accent-primary)]/10 border border-[var(--accent-primary)]/20 p-4">
                  <p className="text-sm text-[var(--accent-primary)]">
                    <strong>Tip:</strong> {step.tip}
                  </p>
                </div>
              )}
            </div>

            {/* Action buttons */}
            <div className="flex gap-4">
              <Button
                asChild
                onClick={() => handleStepComplete(step.id)}
                className="flex-1 bg-gradient-to-r from-[var(--accent-primary)] to-[#FFD87E] text-black font-semibold"
              >
                <Link href={step.action.href}>
                  {step.action.label}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              {!isLastStep && (
                <Button
                  variant="outline"
                  onClick={handleNext}
                  className="flex-1"
                >
                  Skip for now
                </Button>
              )}
            </div>

            {/* Step list */}
            <div className="pt-6 border-t border-white/10">
              <div className="space-y-2">
                {onboardingSteps.map((s, idx) => (
                  <div
                    key={s.id}
                    className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                      idx === currentStep
                        ? 'bg-white/5 border border-white/10'
                        : 'bg-transparent'
                    }`}
                  >
                    {completedSteps.includes(s.id) ? (
                      <div className="h-6 w-6 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
                        <Check className="h-4 w-4 text-white" />
                      </div>
                    ) : (
                      <div
                        className={`h-6 w-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                          idx === currentStep
                            ? 'bg-[var(--accent-primary)] text-black font-bold'
                            : 'bg-white/10 text-slate-400'
                        }`}
                      >
                        {idx + 1}
                      </div>
                    )}
                    <div className="flex-1">
                      <p
                        className={`text-sm font-medium ${
                          idx === currentStep ? 'text-white' : 'text-slate-400'
                        }`}
                      >
                        {s.title}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
