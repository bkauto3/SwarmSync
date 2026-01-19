'use client';

import { AgentRoiTimeseriesPoint } from '@agent-market/sdk';

interface RoiTimeseriesChartProps {
  points: AgentRoiTimeseriesPoint[];
}

export function RoiTimeseriesChart({ points }: RoiTimeseriesChartProps) {
  if (points.length === 0) {
    return (
      <div className="card p-6 text-sm text-[var(--text-muted)]">
        No history yet. Run evaluations or track transactions to populate ROI trends.
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
        <h2 className="text-lg font-display text-white">ROI Trend (last {points.length} days)</h2>
        <p className="text-sm text-[var(--text-muted)]">
          Tracks gross merchandise volume and verified outcomes to highlight ROI health.
        </p>
      </div>
      <div className="flex items-end gap-2">
        {points.map((point) => {
          const value = Number.parseFloat(point.grossMerchandiseVolume);
          const percentage = Math.round((value / maxValue) * 100);
          return (
            <div key={point.date} className="flex flex-1 flex-col items-center gap-2">
              <div
                className="flex h-32 w-full items-end rounded-lg bg-[var(--surface-raised)]"
                aria-label={`GMV $${point.grossMerchandiseVolume}`}
              >
                <div
                  className="w-full rounded-lg bg-gradient-to-t from-accent/70 to-accent/30"
                  style={{ height: `${percentage}%` }}
                />
              </div>
              <div className="text-center text-xs text-[var(--text-muted)]">
                <div className="font-semibold text-white">${point.grossMerchandiseVolume}</div>
                <div className="text-[10px] uppercase tracking-wide">
                  {new Date(point.date).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                  })}
                </div>
                <div className="text-[10px] text-emerald-400">{point.verifiedOutcomes} verified</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
