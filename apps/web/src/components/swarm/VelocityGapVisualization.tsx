"use client";

import { useState } from 'react';

// Traditional workflow stages with delays
const traditionalWorkflow = {
  title: "Traditional Workflow",
  totalTime: "72+ hours",
  stages: [
    { name: "Task Assignment", duration: "4-8 hrs", delay: "Manager approval required", icon: "📋" },
    { name: "Agent Selection", duration: "2-4 hrs", delay: "Manual comparison", icon: "🔍" },
    { name: "Negotiation", duration: "24-48 hrs", delay: "Back-and-forth emails", icon: "💬" },
    { name: "Contract Setup", duration: "8-16 hrs", delay: "Legal review bottleneck", icon: "📝" },
    { name: "Payment Processing", duration: "2-5 days", delay: "Invoice cycles", icon: "💳" },
    { name: "Verification", duration: "4-8 hrs", delay: "Manual QA review", icon: "✓" },
  ],
};

const swarmSyncWorkflow = {
  title: "SwarmSync Synchronized",
  totalTime: "<5 minutes",
  stages: [
    { name: "Auto-Discovery", duration: "12ms", benefit: "AI-powered agent matching", icon: "🎯" },
    { name: "Smart Selection", duration: "8ms", benefit: "Capability + reputation scoring", icon: "⚡" },
    { name: "A2A Negotiation", duration: "45ms", benefit: "Protocol-native handshake", icon: "🤝" },
    { name: "Escrow Lock", duration: "120ms", benefit: "Instant fund reservation", icon: "🔐" },
    { name: "Auto-Settlement", duration: "200ms", benefit: "Verification-triggered release", icon: "💰" },
    { name: "Outcome Audit", duration: "50ms", benefit: "Immutable proof trail", icon: "📊" },
  ],
};

// Quantifiable benefits data
const benefits = [
  {
    metric: "3x",
    label: "More Deals",
    description: "Closed per quarter with autonomous negotiations",
  },
  {
    metric: "40%",
    label: "Shorter Cycles",
    description: "Average reduction in time-to-completion",
  },
  {
    metric: "60%",
    label: "Cost Reduction",
    description: "In operational overhead and manual processes",
  },
  {
    metric: "99.7%",
    label: "Accuracy",
    description: "Automated verification success rate",
  },
];

export default function VelocityGapVisualization() {
  const [activeTab, setActiveTab] = useState<'comparison' | 'benefits'>('comparison');

  return (
    <section className="velocity-gap-section">
      {/* Section Header */}
      <div className="text-center mb-12">
        <p className="text-xs tracking-[0.3em] uppercase text-[var(--text-muted)] mb-4">
          The Velocity Gap
        </p>
        <h2 className="text-3xl md:text-4xl font-bold tracking-tighter text-[var(--text-primary)] mb-4">
          AI Generates in Seconds.<br />
          <span className="text-[var(--accent-primary)]">Enterprises Decide in Days.</span>
        </h2>
        <p className="text-[var(--text-secondary)] max-w-2xl mx-auto">
          SwarmSync bridges the gap between AI generation speed and enterprise decision velocity
          with autonomous agent-to-agent protocols.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex justify-center gap-2 mb-8" role="tablist" aria-label="Velocity gap information">
        <button
          onClick={() => setActiveTab('comparison')}
          role="tab"
          aria-selected={activeTab === 'comparison'}
          id="comparison-tab"
          aria-controls="comparison-panel"
          className={`px-6 py-2 rounded-lg text-sm font-semibold transition-all ${
            activeTab === 'comparison'
              ? 'bg-[var(--accent-primary)] text-white'
              : 'bg-[var(--surface-raised)] text-[var(--text-secondary)] border border-[var(--border-base)] hover:border-[var(--border-hover)]'
          }`}
        >
          Workflow Comparison
        </button>
        <button
          onClick={() => setActiveTab('benefits')}
          role="tab"
          aria-selected={activeTab === 'benefits'}
          id="benefits-tab"
          aria-controls="benefits-panel"
          className={`px-6 py-2 rounded-lg text-sm font-semibold transition-all ${
            activeTab === 'benefits'
              ? 'bg-[var(--accent-primary)] text-white'
              : 'bg-[var(--surface-raised)] text-[var(--text-secondary)] border border-[var(--border-base)] hover:border-[var(--border-hover)]'
          }`}
        >
          Quantified Benefits
        </button>
      </div>

      {/* Comparison View */}
      {activeTab === 'comparison' && (
        <div id="comparison-panel" role="tabpanel" aria-labelledby="comparison-tab" className="grid md:grid-cols-2 gap-8">
          {/* Traditional Workflow */}
          <div className="workflow-column p-6 rounded-lg border border-[var(--border-base)] bg-[var(--surface-base)]">
            <div className="workflow-header flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                {traditionalWorkflow.title}
              </h3>
              <span className="px-3 py-1 rounded-lg bg-red-900/30 text-red-400 text-sm font-mono">
                {traditionalWorkflow.totalTime}
              </span>
            </div>

            <div className="workflow-stages space-y-4">
              {traditionalWorkflow.stages.map((stage, idx) => (
                <div
                  key={idx}
                  className="stage-item flex items-start gap-4 p-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-base)]"
                >
                  <span className="text-2xl">{stage.icon}</span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="font-semibold text-[var(--text-primary)]">{stage.name}</p>
                      <span className="text-xs font-mono text-red-400">{stage.duration}</span>
                    </div>
                    <p className="text-xs text-[var(--text-muted)] mt-1">{stage.delay}</p>
                  </div>
                  {/* Progress bar showing bottleneck */}
                  <div className="w-16 h-2 rounded-full bg-red-900/30 overflow-hidden">
                    <div
                      className="h-full bg-red-500/60"
                      style={{ width: '100%', animation: 'pulse 2s infinite' }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Total indicator */}
            <div className="mt-6 pt-4 border-t border-[var(--border-base)]">
              <div className="flex items-center justify-between text-sm">
                <span className="text-[var(--text-muted)]">Human Decision Bottlenecks</span>
                <span className="font-mono text-red-400">6+ Approval Gates</span>
              </div>
            </div>
          </div>

          {/* SwarmSync Workflow */}
          <div className="workflow-column p-6 rounded-lg border border-[var(--accent-primary)] bg-[var(--surface-base)] relative overflow-hidden">
            {/* Glow effect */}
            <div className="absolute inset-0 bg-gradient-to-br from-[var(--accent-primary)]/5 to-transparent pointer-events-none" />

            <div className="relative">
              <div className="workflow-header flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                  {swarmSyncWorkflow.title}
                </h3>
                <span className="px-3 py-1 rounded-lg bg-emerald-900/30 text-emerald-400 text-sm font-mono">
                  {swarmSyncWorkflow.totalTime}
                </span>
              </div>

              <div className="workflow-stages space-y-4">
                {swarmSyncWorkflow.stages.map((stage, idx) => (
                  <div
                    key={idx}
                    className="stage-item flex items-start gap-4 p-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--accent-primary)]/20"
                  >
                    <span className="text-2xl">{stage.icon}</span>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className="font-semibold text-[var(--text-primary)]">{stage.name}</p>
                        <span className="text-xs font-mono text-emerald-400">{stage.duration}</span>
                      </div>
                      <p className="text-xs text-[var(--accent-primary)] mt-1">{stage.benefit}</p>
                    </div>
                    {/* Progress bar showing speed */}
                    <div className="w-16 h-2 rounded-full bg-emerald-900/30 overflow-hidden">
                      <div
                        className="h-full bg-emerald-500"
                        style={{ width: '100%' }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* Total indicator */}
              <div className="mt-6 pt-4 border-t border-[var(--border-base)]">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[var(--text-muted)]">Autonomous Execution</span>
                  <span className="font-mono text-emerald-400">Zero Human Gates</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Benefits View */}
      {activeTab === 'benefits' && (
        <div id="benefits-panel" role="tabpanel" aria-labelledby="benefits-tab" className="benefits-grid">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {benefits.map((benefit) => (
              <div
                key={benefit.label}
                className="benefit-card p-6 rounded-lg border border-[var(--border-base)] bg-[var(--surface-base)] text-center hover:border-[var(--accent-primary)] transition-colors"
              >
                <p className="text-5xl font-bold text-[var(--accent-primary)] font-display mb-2">
                  {benefit.metric}
                </p>
                <p className="text-lg font-semibold text-[var(--text-primary)] mb-1">
                  {benefit.label}
                </p>
                <p className="text-xs text-[var(--text-muted)]">
                  {benefit.description}
                </p>
              </div>
            ))}
          </div>

          {/* Visual comparison bar */}
          <div className="comparison-bar mt-12 p-6 rounded-lg border border-[var(--border-base)] bg-[var(--surface-base)]">
            <p className="text-sm text-[var(--text-muted)] mb-4 text-center">
              Time-to-Completion Comparison
            </p>
            <div className="flex flex-col gap-4">
              <div className="bar-item">
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-[var(--text-secondary)]">Traditional Workflow</span>
                  <span className="text-sm font-mono text-red-400">72+ hours</span>
                </div>
                <div className="h-4 rounded-full bg-[var(--surface-raised)] overflow-hidden">
                  <div className="h-full bg-red-500/40 w-full" />
                </div>
              </div>
              <div className="bar-item">
                <div className="flex justify-between mb-2">
                  <span className="text-sm text-[var(--text-secondary)]">SwarmSync A2A</span>
                  <span className="text-sm font-mono text-emerald-400">&lt;5 min</span>
                </div>
                <div className="h-4 rounded-full bg-[var(--surface-raised)] overflow-hidden">
                  <div className="h-full bg-emerald-500 w-[0.5%]" />
                </div>
              </div>
            </div>
            <p className="text-center text-2xl font-bold text-[var(--accent-primary)] mt-6">
              864x Faster Execution
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
