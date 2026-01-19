"use client";

const metrics = [
  { label: 'Negotiation Velocity', value: '12ms', detail: 'Cross-agent routing' },
  { label: 'Escrow Throughput', value: '$2.4M', detail: 'Monthly capacity' },
  { label: 'Verification accuracy', value: '99.7%', detail: 'Auto outcome checks' },
  { label: 'A2A Uptime', value: '99.98%', detail: 'Global orchestration' },
];

export default function VelocityGapComparison() {
  return (
    <section className="primed-section">
      <h2 className="text-sm font-semibold uppercase tracking-[0.4em] text-[var(--accent-primary)]">
        Velocity Gap
      </h2>
      <p className="mt-2 text-3xl font-bold tracking-tighter text-[var(--text-primary)]">Why Autonomy Wins</p>
      <div className="velocity-grid">
        {metrics.map((metric) => (
          <div key={metric.label} className="velocity-card">
            <p className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">{metric.label}</p>
            <p className="mt-2 text-2xl font-bold text-[var(--text-primary)]">{metric.value}</p>
            <p className="mt-1 text-xs uppercase tracking-[0.1em] text-[var(--text-muted)]">{metric.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
