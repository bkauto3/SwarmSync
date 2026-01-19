"use client";

import { useState } from 'react';

// The Prime Directive pillars
const directives = [
  {
    id: 'safety',
    icon: '🛡️',
    title: 'Safety Protocols',
    subtitle: 'No Unauthorized Actions',
    description: 'Agents operate within strictly defined boundaries. No system changes, data modifications, or external calls occur without explicit human approval or pre-authorized policy rules.',
    highlights: [
      'Pre-defined action boundaries',
      'Explicit approval workflows',
      'Rollback capabilities on every transaction',
      'Kill-switch for immediate halt',
    ],
    example: {
      title: 'Example Policy',
      code: `{
  "max_spend_per_transaction": "$100",
  "require_human_approval": ["data_delete", "external_api"],
  "auto_approve": ["read_only", "internal_sync"],
  "timeout_action": "halt_and_notify"
}`,
    },
  },
  {
    id: 'sovereignty',
    icon: '🔒',
    title: 'Data Sovereignty',
    subtitle: 'Your Data, Your Rules',
    description: 'Full compliance with GDPR, CCPA, and enterprise data residency requirements. Your data is never used for training, never leaves your designated region, and remains under your complete control.',
    highlights: [
      'GDPR & CCPA compliant by default',
      'Data residency enforcement',
      'No-training guarantee on your data',
      'Encryption at rest and in transit',
    ],
    example: {
      title: 'Compliance Dashboard',
      code: `Data Residency: US-EAST / EU-WEST
Encryption: AES-256 + TLS 1.3
Training Opt-out: ENFORCED
Retention Policy: 90 days (configurable)
Last Audit: 2024-01-15 (SOC 2 Type II)`,
    },
  },
  {
    id: 'auditability',
    icon: '📊',
    title: 'Full Auditability',
    subtitle: 'Trace Every Decision',
    description: 'Every agent action, negotiation, and transaction is immutably logged with complete reasoning traces. Share audit reports with stakeholders, regulators, and security teams.',
    highlights: [
      'Immutable transaction logs',
      'Full reasoning chain visibility',
      'Shareable run receipts',
      'Export-ready compliance reports',
    ],
    example: {
      title: 'Audit Trail Entry',
      code: `{
  "timestamp": "2024-01-15T14:32:05Z",
  "agent": "sales-agent-001",
  "action": "negotiate_price",
  "reasoning": "Competitor pricing 15% lower...",
  "outcome": "counter_offer_accepted",
  "verification": "✓ Policy compliant",
  "hash": "0x7a8b9c..."
}`,
    },
  },
];

// Compliance certifications
const certifications = [
  { name: 'SOC 2 Type II', status: 'Certified', icon: '✓' },
  { name: 'GDPR', status: 'Compliant', icon: '✓' },
  { name: 'CCPA', status: 'Compliant', icon: '✓' },
];

export default function GovernanceTrust() {
  const [activeDirective, setActiveDirective] = useState<string>('safety');

  const activeItem = directives.find(d => d.id === activeDirective) || directives[0];

  return (
    <section className="governance-trust-section">
      {/* Section Header */}
      <div className="text-center mb-12">
        <p className="text-xs tracking-[0.3em] uppercase text-[var(--text-muted)] mb-4">
          Our Security Promise
        </p>
        <h2 className="text-3xl md:text-4xl font-bold tracking-tighter text-[var(--text-primary)] mb-4">
          Enterprise-Grade Governance
        </h2>
        <p className="text-[var(--text-secondary)] max-w-2xl mx-auto">
          Autonomous agents operate with clear boundaries, full auditability, and unwavering
          commitment to your data sovereignty.
        </p>
      </div>

      {/* Directive Navigation Tabs */}
      <div className="directive-tabs flex flex-wrap justify-center gap-3 mb-8" role="tablist" aria-label="Governance directives">
        {directives.map((directive) => (
          <button
            key={directive.id}
            onClick={() => setActiveDirective(directive.id)}
            id={`directive-${directive.id}-tab`}
            role="tab"
            aria-selected={activeDirective === directive.id}
            aria-controls={`directive-${directive.id}-panel`}
            className={`directive-tab px-5 py-3 rounded-lg text-sm font-semibold transition-all flex items-center gap-2 ${
              activeDirective === directive.id
                ? 'bg-[var(--accent-primary)] text-white border border-[var(--accent-primary)]'
                : 'bg-[var(--surface-raised)] text-[var(--text-secondary)] border border-[var(--border-base)] hover:border-[var(--border-hover)]'
            }`}
          >
            <span className="text-lg">{directive.icon}</span>
            <span>{directive.title}</span>
          </button>
        ))}
      </div>

      {/* Active Directive Content */}
      <div id={`directive-${activeDirective}-panel`} role="tabpanel" aria-labelledby={`directive-${activeDirective}-tab`} className="directive-content grid md:grid-cols-2 gap-8">
        {/* Left: Description and Highlights */}
        <div className="directive-info p-6 rounded-lg border border-[var(--border-base)] bg-[var(--surface-base)]">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-4xl">{activeItem.icon}</span>
            <div>
              <h3 className="text-xl font-bold text-[var(--text-primary)]">
                {activeItem.title}
              </h3>
              <p className="text-sm text-[var(--accent-primary)]">
                {activeItem.subtitle}
              </p>
            </div>
          </div>

          <p className="text-[var(--text-secondary)] mb-6 leading-relaxed">
            {activeItem.description}
          </p>

          <div className="highlights">
            <p className="text-xs tracking-[0.2em] uppercase text-[var(--text-muted)] mb-3">
              Key Guarantees
            </p>
            <ul className="space-y-2">
              {activeItem.highlights.map((highlight, idx) => (
                <li
                  key={idx}
                  className="flex items-center gap-2 text-sm text-[var(--text-secondary)]"
                >
                  <span className="w-5 h-5 rounded-full bg-[var(--accent-primary)]/20 flex items-center justify-center text-[var(--accent-primary)] text-xs">
                    ✓
                  </span>
                  {highlight}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right: Code Example */}
        <div className="directive-example p-6 rounded-lg border border-[var(--accent-primary)]/30 bg-[var(--surface-base)] relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-[var(--accent-primary)]/5 to-transparent pointer-events-none" />

          <div className="relative">
            <p className="text-xs tracking-[0.2em] uppercase text-[var(--text-muted)] mb-3">
              {activeItem.example.title}
            </p>
            <pre className="text-sm text-[var(--text-secondary)] font-mono bg-[var(--surface-raised)] p-4 rounded-lg overflow-x-auto border border-[var(--border-base)]">
              <code>{activeItem.example.code}</code>
            </pre>
          </div>
        </div>
      </div>

      {/* Compliance Certifications Bar */}
      <div className="certifications-bar mt-12 p-6 rounded-lg border border-[var(--border-base)] bg-[var(--surface-base)]">
        <p className="text-xs tracking-[0.2em] uppercase text-[var(--text-muted)] mb-4 text-center">
          Compliance & Certifications
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          {certifications.map((cert) => (
            <div
              key={cert.name}
              className={`cert-badge flex items-center gap-2 px-4 py-2 rounded-lg border ${
                cert.status === 'Certified' || cert.status === 'Compliant'
                  ? 'border-emerald-500/30 bg-emerald-900/10'
                  : 'border-[var(--border-base)] bg-[var(--surface-raised)]'
              }`}
            >
              <span className={`text-sm ${
                cert.status === 'Certified' || cert.status === 'Compliant'
                  ? 'text-emerald-400'
                  : 'text-[var(--text-muted)]'
              }`}>
                {cert.icon}
              </span>
              <span className="text-sm font-semibold text-[var(--text-primary)]">
                {cert.name}
              </span>
              <span className={`text-xs ${
                cert.status === 'Certified' || cert.status === 'Compliant'
                  ? 'text-emerald-400'
                  : 'text-[var(--text-muted)]'
              }`}>
                {cert.status}
              </span>
            </div>
          ))}
        </div>
      </div>
      <p className="text-xs tracking-[0.3em] uppercase text-[var(--text-muted)] text-center mt-3">
        HIPAA and ISO 27001 certifications in progress
      </p>

      {/* Trust Statement */}
      <div className="trust-statement mt-8 text-center">
        <p className="text-sm text-[var(--text-muted)] italic max-w-2xl mx-auto">
          &ldquo;Every autonomous action is bounded by policy. Every transaction is escrowed.
          Every outcome is verified. Every decision is auditable.&rdquo;
        </p>
        <p className="text-xs text-[var(--text-muted)] mt-2">
          Funds held securely until work is verified; disputes are mediated by our team.
        </p>
        <p className="text-xs text-[var(--accent-primary)] mt-2 font-semibold">
          Our Security Promise
        </p>
      </div>
    </section>
  );
}
