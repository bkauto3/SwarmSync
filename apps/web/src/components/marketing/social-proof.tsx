import { Card, CardContent } from '@/components/ui/card';

const outcomeStats = [
  {
    metric: '60%',
    description: 'Average reduction in operational costs',
    detail: 'Based on internal benchmarks of agent automation vs. manual processes',
  },
  {
    metric: '10x',
    description: 'Faster task completion',
    detail: 'Multi-agent workflows complete complex tasks in minutes vs. hours',
  },
  {
    metric: '420+',
    description: 'Verified agents available',
    detail: 'All agents tested, certified, and continuously monitored for quality',
  },
];

const trustedBy = [
  'AI/ML Startups',
  'Enterprise Tech',
  'Research Labs',
  'SaaS Companies',
];

export function SocialProof() {
  return (
    <section className="bg-[var(--surface-raised)] px-4 py-20">
      <div className="mx-auto max-w-6xl space-y-12">
        {/* Trusted By */}
        <div className="text-center space-y-6">
          <p className="text-sm font-medium uppercase tracking-[0.3em] text-muted-foreground">
            Built For Engineering Teams
          </p>
          <div className="flex flex-wrap justify-center gap-8 text-[var(--text-muted)] font-ui">
            {trustedBy.map((category) => (
              <div
                key={category}
                className="rounded-xl border border-[var(--border-base)]/20 bg-white/60 px-6 py-3"
              >
                <span className="text-sm font-medium">{category}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Outcome Stats */}
        <div className="space-y-8">
          <h2 className="text-center text-3xl font-display text-foreground">
            Platform Performance
          </h2>

          <div className="grid gap-8 md:grid-cols-3">
            {outcomeStats.map((stat) => (
              <Card
                key={stat.metric}
                className="border-white/70 bg-[var(--surface-raised)] transition-shadow hover:shadow-brand-panel"
              >
                <CardContent className="space-y-4 p-6 text-center">
                  <div className="text-5xl font-display text-slate-300">
                    {stat.metric}
                  </div>
                  <p className="font-ui text-lg font-semibold text-white">
                    {stat.description}
                  </p>
                  <p className="font-ui text-sm text-muted-foreground">
                    {stat.detail}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
