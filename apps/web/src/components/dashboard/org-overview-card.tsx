import { OrganizationRoiSummary } from '@agent-market/sdk';

interface OrgOverviewCardProps {
  summary: OrganizationRoiSummary;
}

export function OrgOverviewCard({ summary }: OrgOverviewCardProps) {
  const { organization, grossMerchandiseVolume, totalAgents, verifiedOutcomes, averageCostPerOutcome } =
    summary;

  return (
    <section className="card grid gap-4 p-6 md:grid-cols-4">
      <div className="card-inner rounded-xl border border-[var(--border-base)] p-4">
        <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] font-ui">Organization</p>
        <h3 className="mt-2 text-xl font-semibold text-[var(--text-primary)] font-display">{organization.name}</h3>
        <p className="text-xs text-[var(--text-muted)] font-ui">Slug: {organization.slug}</p>
      </div>
      <div className="card-inner rounded-xl border border-[var(--border-base)] p-4">
        <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] font-ui">GMV</p>
        <h3 className="mt-2 text-3xl font-semibold text-[var(--text-primary)] font-display text-meta-numeric">${grossMerchandiseVolume}</h3>
        <p className="text-xs text-[var(--text-muted)] font-ui">Cumulative agent volume</p>
      </div>
      <div className="card-inner rounded-xl border border-[var(--border-base)] p-4">
        <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] font-ui">Verified outcomes</p>
        <h3 className="mt-2 text-3xl font-semibold text-emerald-400 font-display text-meta-numeric">{verifiedOutcomes}</h3>
        <p className="text-xs text-[var(--text-muted)] font-ui text-meta-numeric">
          Avg cost {averageCostPerOutcome ? `$${averageCostPerOutcome}` : 'n/a'}
        </p>
      </div>
      <div className="card-inner rounded-xl border border-[var(--border-base)] p-4">
        <p className="text-xs uppercase tracking-wide text-[var(--text-muted)] font-ui">Agents</p>
        <h3 className="mt-2 text-3xl font-semibold text-[var(--text-primary)] font-display text-meta-numeric">{totalAgents}</h3>
        <p className="text-xs text-[var(--text-muted)] font-ui">Connected to this org</p>
      </div>
    </section>
  );
}
