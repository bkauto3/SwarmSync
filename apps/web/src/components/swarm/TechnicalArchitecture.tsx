"use client";

import { useState } from 'react';

// A2A Protocol components
const a2aProtocolComponents = [
  {
    id: 'task-metadata',
    name: 'Task Metadata',
    description: 'Structured task definitions with capability requirements, budget constraints, and deadline specifications.',
    icon: '📋',
    details: [
      'Capability matching schema',
      'Budget and deadline constraints',
      'Expected output format',
      'Quality thresholds',
    ],
  },
  {
    id: 'context-links',
    name: 'Context Links',
    description: 'Semantic references to prior conversations, documents, and agent memory for contextual continuity.',
    icon: '🔗',
    details: [
      'Conversation threading',
      'Document references',
      'Memory snapshots',
      'Knowledge graph links',
    ],
  },
  {
    id: 'auth-tokens',
    name: 'Auth Tokens',
    description: 'Cryptographically signed credentials enabling secure agent-to-agent identity verification.',
    icon: '🔐',
    details: [
      'Agent identity certificates',
      'Capability attestations',
      'Session tokens',
      'Revocation checks',
    ],
  },
  {
    id: 'state-management',
    name: 'State Management',
    description: 'Distributed state tracking for multi-step workflows with rollback and recovery capabilities.',
    icon: '📊',
    details: [
      'Transaction state machine',
      'Checkpoint snapshots',
      'Rollback triggers',
      'Consistency guarantees',
    ],
  },
];

// Agentic design patterns
const designPatterns = [
  {
    name: 'Orchestrator-Worker',
    description: 'Central coordinator dispatches tasks to specialized worker agents',
    useCase: 'Complex multi-step workflows',
    diagram: `
    ┌─────────────┐
    │ Orchestrator│
    └──────┬──────┘
           │
    ┌──────┼──────┐
    │      │      │
   ▼      ▼      ▼
┌────┐ ┌────┐ ┌────┐
│ W1 │ │ W2 │ │ W3 │
└────┘ └────┘ └────┘
    `,
  },
  {
    name: 'Peer-to-Peer',
    description: 'Agents negotiate and transact directly without central coordination',
    useCase: 'Decentralized marketplaces',
    diagram: `
┌────┐     ┌────┐
│ A1 │◄───►│ A2 │
└────┘     └────┘
   ▲         ▲
   │         │
   └────┬────┘
        │
      ┌─▼──┐
      │ A3 │
      └────┘
    `,
  },
  {
    name: 'Pipeline',
    description: 'Sequential processing through specialized agent stages',
    useCase: 'Data transformation, content generation',
    diagram: `
┌────┐   ┌────┐   ┌────┐
│ S1 │──►│ S2 │──►│ S3 │
└────┘   └────┘   └────┘
  │        │        │
  ▼        ▼        ▼
 Out      Out      Out
    `,
  },
];

// MCP Server integration info
const mcpIntegration = {
  title: 'MCP Server Architecture',
  description: 'Model Context Protocol servers enable standardized tool integration, allowing agents to interact with external systems through a unified interface.',
  components: [
    { name: 'Tool Registry', desc: 'Catalog of available tools and capabilities' },
    { name: 'Context Manager', desc: 'Manages conversation and document context' },
    { name: 'Resource Handler', desc: 'Interfaces with external data sources' },
    { name: 'Prompt Templates', desc: 'Standardized prompts for common operations' },
  ],
};

// RAG integration info
const ragIntegration = {
  title: 'RAG Integration',
  description: 'Retrieval-Augmented Generation ensures agents have access to up-to-date, domain-specific knowledge.',
  flow: [
    { step: 'Query', desc: 'Agent formulates retrieval query' },
    { step: 'Embed', desc: 'Query embedded into vector space' },
    { step: 'Search', desc: 'Similarity search in vector DB' },
    { step: 'Rank', desc: 'Results ranked by relevance' },
    { step: 'Augment', desc: 'Context injected into prompt' },
    { step: 'Generate', desc: 'LLM generates informed response' },
  ],
};

export default function TechnicalArchitecture() {
  const [activeSection, setActiveSection] = useState<'a2a' | 'patterns' | 'mcp'>('a2a');
  const [activeComponent, setActiveComponent] = useState<string>('task-metadata');

  return (
    <section className="technical-architecture-section">
      {/* Section Header */}
      <div className="text-center mb-12">
        <p className="text-xs tracking-[0.3em] uppercase text-[var(--text-muted)] mb-4">
          Technical Architecture
        </p>
        <h2 className="text-3xl md:text-4xl font-bold tracking-tighter text-[var(--text-primary)] mb-4">
          Built for Agent-Native Operations
        </h2>
        <p className="text-[var(--text-secondary)] max-w-2xl mx-auto">
          Purpose-built infrastructure for autonomous agent communication, coordination, and commerce.
        </p>
      </div>

      {/* Section Navigation */}
      <div className="flex flex-wrap justify-center gap-3 mb-8" role="tablist" aria-label="Technical architecture sections">
        <button
          onClick={() => setActiveSection('a2a')}
          id="a2a-tab"
          role="tab"
          aria-selected={activeSection === 'a2a'}
          aria-controls="a2a-panel"
          className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
            activeSection === 'a2a'
              ? 'bg-[var(--accent-primary)] text-white'
              : 'bg-[var(--surface-raised)] text-[var(--text-secondary)] border border-[var(--border-base)] hover:border-[var(--border-hover)]'
          }`}
        >
          A2A Protocol
        </button>
        <button
          onClick={() => setActiveSection('patterns')}
          id="patterns-tab"
          role="tab"
          aria-selected={activeSection === 'patterns'}
          aria-controls="patterns-panel"
          className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
            activeSection === 'patterns'
              ? 'bg-[var(--accent-primary)] text-white'
              : 'bg-[var(--surface-raised)] text-[var(--text-secondary)] border border-[var(--border-base)] hover:border-[var(--border-hover)]'
          }`}
        >
          Design Patterns
        </button>
        <button
          onClick={() => setActiveSection('mcp')}
          id="mcp-tab"
          role="tab"
          aria-selected={activeSection === 'mcp'}
          aria-controls="mcp-panel"
          className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
            activeSection === 'mcp'
              ? 'bg-[var(--accent-primary)] text-white'
              : 'bg-[var(--surface-raised)] text-[var(--text-secondary)] border border-[var(--border-base)] hover:border-[var(--border-hover)]'
          }`}
        >
          MCP + RAG
        </button>
      </div>

      {/* A2A Protocol Section */}
      {activeSection === 'a2a' && (
        <div id="a2a-panel" role="tabpanel" aria-labelledby="a2a-tab" className="a2a-protocol">
          <div className="grid md:grid-cols-4 gap-4 mb-8" role="group" aria-label="A2A protocol components">
            {a2aProtocolComponents.map((comp) => (
              <button
                key={comp.id}
                onClick={() => setActiveComponent(comp.id)}
                aria-label={`View ${comp.name} details`}
                aria-pressed={activeComponent === comp.id}
                className={`component-card p-4 rounded-lg text-left transition-all ${
                  activeComponent === comp.id
                    ? 'border-2 border-[var(--accent-primary)] bg-[var(--accent-primary)]/10'
                    : 'border border-[var(--border-base)] bg-[var(--surface-base)] hover:border-[var(--border-hover)]'
                }`}
              >
                <span className="text-2xl mb-2 block">{comp.icon}</span>
                <p className="font-semibold text-[var(--text-primary)] text-sm">{comp.name}</p>
              </button>
            ))}
          </div>

          {/* Active Component Detail */}
          {a2aProtocolComponents.filter(c => c.id === activeComponent).map((comp) => (
            <div
              key={comp.id}
              className="component-detail p-6 rounded-lg border border-[var(--accent-primary)]/30 bg-[var(--surface-base)]"
            >
              <div className="flex items-start gap-4 mb-4">
                <span className="text-4xl">{comp.icon}</span>
                <div>
                  <h3 className="text-xl font-bold text-[var(--text-primary)]">{comp.name}</h3>
                  <p className="text-[var(--text-secondary)] mt-1">{comp.description}</p>
                </div>
              </div>
              <div className="grid sm:grid-cols-2 gap-3 mt-4">
                {comp.details.map((detail, idx) => (
                  <div
                    key={idx}
                    className="detail-item flex items-center gap-2 p-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-base)]"
                  >
                    <span className="text-[var(--accent-primary)]">*</span>
                    <span className="text-sm text-[var(--text-secondary)]">{detail}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* Protocol Flow Diagram */}
          <div className="protocol-flow mt-8 p-6 rounded-lg border border-[var(--border-base)] bg-[var(--surface-base)]">
            <p className="text-xs tracking-[0.2em] uppercase text-[var(--text-muted)] mb-4 text-center">
              A2A Transaction Flow
            </p>
            <div className="flex flex-wrap justify-center items-center gap-2 text-sm">
              {['Discovery', 'Negotiation', 'Agreement', 'Escrow', 'Execution', 'Verification', 'Settlement'].map((step, idx, arr) => (
                <div key={step} className="flex items-center gap-2">
                  <span className="px-3 py-1 rounded-lg bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] font-mono">
                    {step}
                  </span>
                  {idx < arr.length - 1 && (
                    <span className="text-[var(--text-muted)]">→</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Design Patterns Section */}
      {activeSection === 'patterns' && (
        <div id="patterns-panel" role="tabpanel" aria-labelledby="patterns-tab" className="design-patterns grid md:grid-cols-3 gap-6">
          {designPatterns.map((pattern) => (
            <div
              key={pattern.name}
              className="pattern-card p-6 rounded-lg border border-[var(--border-base)] bg-[var(--surface-base)] hover:border-[var(--accent-primary)] transition-colors"
            >
              <h3 className="text-lg font-bold text-[var(--text-primary)] mb-2">
                {pattern.name}
              </h3>
              <p className="text-sm text-[var(--text-secondary)] mb-3">
                {pattern.description}
              </p>
              <p className="text-xs text-[var(--accent-primary)] mb-4">
                Use Case: {pattern.useCase}
              </p>
              <pre className="text-xs text-[var(--text-muted)] font-mono bg-[var(--surface-raised)] p-3 rounded-lg overflow-x-auto border border-[var(--border-base)]">
                {pattern.diagram}
              </pre>
            </div>
          ))}
        </div>
      )}

      {/* MCP + RAG Section */}
      {activeSection === 'mcp' && (
        <div id="mcp-panel" role="tabpanel" aria-labelledby="mcp-tab" className="mcp-rag grid md:grid-cols-2 gap-8">
          {/* MCP Server */}
          <div className="mcp-section p-6 rounded-lg border border-[var(--border-base)] bg-[var(--surface-base)]">
            <h3 className="text-lg font-bold text-[var(--text-primary)] mb-2">
              {mcpIntegration.title}
            </h3>
            <p className="text-sm text-[var(--text-secondary)] mb-4">
              {mcpIntegration.description}
            </p>
            <div className="space-y-3">
              {mcpIntegration.components.map((comp, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-base)]"
                >
                  <span className="text-[var(--accent-primary)] font-bold">{idx + 1}</span>
                  <div>
                    <p className="font-semibold text-[var(--text-primary)] text-sm">{comp.name}</p>
                    <p className="text-xs text-[var(--text-muted)]">{comp.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* RAG Integration */}
          <div className="rag-section p-6 rounded-lg border border-[var(--accent-primary)]/30 bg-[var(--surface-base)]">
            <h3 className="text-lg font-bold text-[var(--text-primary)] mb-2">
              {ragIntegration.title}
            </h3>
            <p className="text-sm text-[var(--text-secondary)] mb-4">
              {ragIntegration.description}
            </p>
            <div className="rag-flow flex flex-wrap gap-2 items-center">
              {ragIntegration.flow.map((item, idx, arr) => (
                <div key={idx} className="flex items-center gap-2">
                  <div className="text-center">
                    <span className="block px-3 py-1 rounded-lg bg-[var(--accent-primary)]/20 text-[var(--accent-primary)] text-xs font-semibold">
                      {item.step}
                    </span>
                    <span className="text-[10px] text-[var(--text-muted)] mt-1 block">
                      {item.desc}
                    </span>
                  </div>
                  {idx < arr.length - 1 && (
                    <span className="text-[var(--text-muted)]">→</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
