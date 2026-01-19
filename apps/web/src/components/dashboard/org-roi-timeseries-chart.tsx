import { OrganizationRoiTimeseriesPoint } from '@agent-market/sdk';

interface OrgRoiTimeseriesChartProps {
  points: OrganizationRoiTimeseriesPoint[];
}

export function OrgRoiTimeseriesChart({ points }: OrgRoiTimeseriesChartProps) {
  if (!points.length) {
    return (
      <div className="card p-6 text-sm text-[var(--text-muted)] font-ui">
        No organization spend recorded yet. Execute workflows to populate ROI data.
      </div>
    );
  }

  const maxValue = Math.max(
    ...points.map((point) => Number.parseFloat(point.grossMerchandiseVolume)),
    1,
  );

  return (
    <div className="card space-y-4 p-6">
      <div>
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-1 font-display">Org GMV Trend</h2>
        <p className="text-sm text-[var(--text-secondary)] font-ui">
          Daily gross merchandise volume plus verified outcomes for the selected organization.
        </p>
      </div>
      <div className="flex items-end gap-2">
        {points.map((point) => {
          const value = Number.parseFloat(point.grossMerchandiseVolume);
          const percentage = Math.round((value / maxValue) * 100);
          return (
            <div key={point.date} className="flex flex-1 flex-col items-center gap-2">
              <div className="flex h-32 w-full items-end rounded-lg bg-[var(--surface-raised)]">
                <div
                  className="w-full rounded-lg bg-gradient-to-t from-[var(--accent-primary)]/70 to-[var(--accent-primary)]/30"
                  style={{ height: `${percentage}%` }}
                  aria-label={`GMV $${point.grossMerchandiseVolume}`}
                />
              </div>
              <div className="text-center text-xs text-[var(--text-muted)] font-ui">
                <div className="font-semibold text-[var(--text-primary)] font-display text-meta-numeric">${point.grossMerchandiseVolume}</div>
                <div className="text-[10px] uppercase tracking-wide">
                  {new Date(point.date).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                  })}
                </div>
                <div className="text-[10px] text-emerald-400 text-meta-numeric">
                  {point.verifiedOutcomes} verified
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
