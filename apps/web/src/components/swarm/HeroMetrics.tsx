"use client";

import { useEffect, useState } from 'react';

// Animated counter hook
function useAnimatedCounter(target: number, duration: number = 2000) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime: number;
    let animationFrame: number;

    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime;
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Easing function for smooth animation
      const easeOutQuart = 1 - Math.pow(1 - progress, 4);
      setCount(Math.floor(easeOutQuart * target));

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [target, duration]);

  return count;
}

// Hero metrics data
const heroMetrics = [
  {
    value: 2400000,
    suffix: '+',
    label: 'A2A Transactions',
    format: 'short', // Will show as 2.4M+
  },
  {
    value: 420,
    suffix: '+',
    label: 'Verified Agents',
    format: 'number',
  },
  {
    value: 99.98,
    suffix: '%',
    label: 'Uptime',
    format: 'decimal',
  },
  {
    value: 12,
    suffix: 'ms',
    prefix: '<',
    label: 'Latency',
    format: 'number',
  },
];

function formatNumber(value: number, format: string): string {
  switch (format) {
    case 'short':
      if (value >= 1000000) {
        return (value / 1000000).toFixed(1) + 'M';
      } else if (value >= 1000) {
        return (value / 1000).toFixed(1) + 'K';
      }
      return value.toString();
    case 'decimal':
      return value.toFixed(2);
    default:
      return value.toLocaleString();
  }
}

function MetricCounter({ metric }: { metric: typeof heroMetrics[0] }) {
  const targetValue = metric.format === 'short' ? Math.floor(metric.value / 1000000 * 10) / 10 : metric.value;
  const animatedValue = useAnimatedCounter(
    metric.format === 'short' ? targetValue * 10 : targetValue,
    2500
  );

  const displayValue = metric.format === 'short'
    ? (animatedValue / 10).toFixed(1) + 'M'
    : metric.format === 'decimal'
      ? (animatedValue / 100).toFixed(2)
      : animatedValue.toLocaleString();

  return (
    <div className="hero-metric text-center">
      <p className="text-2xl md:text-3xl font-bold text-[var(--text-primary)] font-display">
        {metric.prefix || ''}{displayValue}{metric.suffix}
      </p>
      <p className="text-xs text-[var(--text-muted)] uppercase tracking-wider mt-1">
        {metric.label}
      </p>
    </div>
  );
}

export default function HeroMetrics() {
  return (
    <div className="hero-metrics-bar py-4 px-4 mt-8 rounded-lg border border-[var(--border-base)] bg-[var(--surface-base)]/80 backdrop-blur">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {heroMetrics.map((metric, idx) => (
          <MetricCounter key={idx} metric={metric} />
        ))}
      </div>
    </div>
  );
}

// Compact version for inline use
export function HeroMetricsCompact() {
  return (
    <div className="hero-metrics-compact flex flex-wrap items-center justify-center gap-6 py-4">
      {heroMetrics.map((metric, idx) => (
        <div key={idx} className="flex items-center gap-2">
          <span className="text-lg font-bold text-[var(--accent-primary)]">
            {metric.prefix || ''}{formatNumber(metric.value, metric.format)}{metric.suffix}
          </span>
          <span className="text-xs text-[var(--text-muted)]">{metric.label}</span>
        </div>
      ))}
    </div>
  );
}
