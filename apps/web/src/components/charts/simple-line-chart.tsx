'use client';

interface TrendPoint {
  date: string;
  roi: number;
  successRate: number;
}

interface SimpleLineChartProps {
  data: TrendPoint[];
  metric?: 'roi' | 'successRate';
  height?: number;
}

export function SimpleLineChart({
  data,
  metric = 'roi',
  height = 200,
}: SimpleLineChartProps) {
  if (!data || data.length < 2) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center rounded-lg bg-[var(--surface-raised)] text-sm text-[var(--text-muted)]"
      >
        Not enough data points
      </div>
    );
  }

  const values = data.map((d) => d[metric]);
  const maxValue = Math.max(...values) || 1;
  const minValue = Math.min(...values, 0);
  const range = maxValue - minValue || 1;

  const padding = 40;
  const chartWidth = 600;
  const chartHeight = height;
  const pointSpacing = (chartWidth - 2 * padding) / (data.length - 1);

  // Generate SVG path for line
  const points = data.map((d, i) => {
    const x = padding + i * pointSpacing;
    const normalizedValue = (d[metric] - minValue) / range;
    const y = chartHeight - padding - normalizedValue * (chartHeight - 2 * padding);
    return `${x},${y}`;
  });

  const pathD = `M ${points.join(' L ')}`;

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((i) => (
          <line
            key={`grid-${i}`}
            x1={padding}
            y1={chartHeight - padding - i * (chartHeight - 2 * padding)}
            x2={chartWidth - padding}
            y2={chartHeight - padding - i * (chartHeight - 2 * padding)}
            stroke="#e5e7eb"
            strokeWidth="1"
          />
        ))}

        {/* X-axis */}
        <line
          x1={padding}
          y1={chartHeight - padding}
          x2={chartWidth - padding}
          y2={chartHeight - padding}
          stroke="#9ca3af"
          strokeWidth="2"
        />

        {/* Y-axis */}
        <line
          x1={padding}
          y1={padding}
          x2={padding}
          y2={chartHeight - padding}
          stroke="#9ca3af"
          strokeWidth="2"
        />

        {/* Chart line */}
        <path
          d={pathD}
          fill="none"
          stroke="#c77a2f"
          strokeWidth="3"
          vectorEffect="non-scaling-stroke"
        />

        {/* Data points */}
        {data.map((d, i) => {
          const x = padding + i * pointSpacing;
          const normalizedValue = (d[metric] - minValue) / range;
          const y = chartHeight - padding - normalizedValue * (chartHeight - 2 * padding);
          return (
            <circle
              key={`point-${i}`}
              cx={x}
              cy={y}
              r="4"
              fill="#c77a2f"
              opacity="0.7"
            />
          );
        })}

        {/* X-axis labels (every nth point to avoid clutter) */}
        {data.map((d, i) => {
          if (i % Math.ceil(data.length / 5) !== 0 && i !== data.length - 1)
            return null;
          const x = padding + i * pointSpacing;
          return (
            <text
              key={`label-${i}`}
              x={x}
              y={chartHeight - padding + 20}
              textAnchor="middle"
              fontSize="12"
              fill="#6b7280"
            >
              {d.date}
            </text>
          );
        })}

        {/* Y-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((i) => {
          const value = minValue + i * range;
          const y = chartHeight - padding - i * (chartHeight - 2 * padding);
          return (
            <text
              key={`y-label-${i}`}
              x={padding - 10}
              y={y + 4}
              textAnchor="end"
              fontSize="12"
              fill="#6b7280"
            >
              {value.toFixed(0)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
