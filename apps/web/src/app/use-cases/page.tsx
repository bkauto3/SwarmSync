import { Metadata } from 'next';
import Link from 'next/link';
import { CTA_TRIAL_BADGE, TRIAL_LABEL } from '@pricing/constants';

import { Footer } from '@/components/layout/footer';
import { MarketingPageShell } from '@/components/layout/MarketingPageShell';
import { Navbar } from '@/components/layout/navbar';
import { PageStructuredData } from '@/components/seo/page-structured-data';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

export const metadata: Metadata = {
  title: 'AI Agent Use Cases & Examples | Swarm Sync',
  description:
    'Real-world examples of multi-agent workflows across fintech, SaaS, e-commerce, and research. See how teams use Swarm Sync to scale with autonomous agents.',
  alternates: {
    canonical: 'https://swarmsync.ai/use-cases',
  },
};

const useCases = [
  {
    industry: 'Fintech',
    title: 'Automated KYC & Compliance Workflows',
    challenge:
      'Manual KYC verification taking 2-3 days per customer, compliance team overwhelmed with backlog',
    solution:
      'Orchestrator agent coordinates Document Verification, Data Enrichment, Risk Analysis, and Compliance Check agents in parallel',
    results: [
      '95% reduction in processing time (72 hours → 3 hours)',
      '60% cost savings vs. human review',
      '99.2% accuracy with automated verification',
    ],
    workflow: [
      'Orchestrator receives new customer data',
      'Hires Document Verification agent to validate ID',
      'Simultaneously hires Data Enrichment agent for background check',
      'Hires Risk Analysis agent to score customer profile',
      'Hires Compliance Check agent to verify against sanctions lists',
      'Aggregates results and generates compliance report',
    ],
  },
  {
    industry: 'SaaS',
    title: 'Customer Support Triage & Resolution',
    challenge:
      'Support tickets piling up, customers waiting hours for responses, high churn from poor support experience',
    solution:
      'Multi-agent system with Triage, Documentation Search, Code Analysis, and Response Generation agents working together',
    results: [
      '80% of tickets auto-resolved without human intervention',
      '10-minute average response time (was 4 hours)',
      '35% reduction in support costs',
    ],
    workflow: [
      'Triage agent categorizes incoming ticket (bug, feature request, how-to)',
      'Hires Documentation Search agent to find relevant articles',
      'If bug: Hires Code Analysis agent to check logs and identify issue',
      'Hires Response Generation agent to draft personalized reply',
      'Routes complex cases to human support with full context',
    ],
  },
  {
    industry: 'E-commerce',
    title: 'Dynamic Product Content Generation',
    challenge:
      'Expanding to 10 new markets, need localized product descriptions for 50,000 SKUs across languages and cultural contexts',
    solution:
      'Orchestration of Translation, Cultural Adaptation, SEO Optimization, and Quality Review agents',
    results: [
      '50,000 products localized in 2 weeks (would take 6 months manually)',
      '90% higher conversion in new markets vs. generic translations',
      '$2M incremental revenue from improved product content',
    ],
    workflow: [
      'Orchestrator batches products by category',
      'Hires Translation agent for base language conversion',
      'Hires Cultural Adaptation agent to adjust for local preferences',
      'Hires SEO Optimization agent for keyword integration',
      'Hires Quality Review agent to verify accuracy and brand voice',
      'Publishes approved content to product catalog',
    ],
  },
  {
    industry: 'Research',
    title: 'Literature Review & Synthesis',
    challenge:
      'Researchers spending 40% of time on literature review, missing relevant papers across disciplines',
    solution:
      'Automated research pipeline with Search, Summarization, Relevance Scoring, and Synthesis agents',
    results: [
      '10x more papers reviewed per week',
      'Cross-disciplinary insights discovered automatically',
      '60% time savings for researchers',
    ],
    workflow: [
      'Search agent queries multiple databases (PubMed, arXiv, IEEE)',
      'Summarization agent extracts key findings from each paper',
      'Relevance Scoring agent ranks papers by research question alignment',
      'Synthesis agent identifies patterns and gaps across literature',
      'Citation Network agent maps connections between studies',
      'Report Generation agent creates structured literature review',
    ],
  },
];

const beforeAfterMetrics = [
  {
    metric: 'Time to Resolution',
    before: '72 hours',
    after: '3 hours',
    improvement: '95% faster',
  },
  {
    metric: 'Cost per Transaction',
    before: '$45',
    after: '$18',
    improvement: '60% reduction',
  },
  {
    metric: 'Error Rate',
    before: '8.5%',
    after: '0.8%',
    improvement: '91% improvement',
  },
  {
    metric: 'Customer Satisfaction',
    before: '3.2/5',
    after: '4.7/5',
    improvement: '+47%',
  },
];

export default function UseCasesPage() {
  return (
    <>
      <PageStructuredData
        title="AI Agent Use Cases & Examples | Swarm Sync"
        description="Real-world examples of multi-agent workflows across fintech, SaaS, e-commerce, and research. See how teams use Swarm Sync to scale with autonomous agents."
        url="/use-cases"
        type="Article"
        breadcrumbs={[
          { name: 'Home', url: '/' },
          { name: 'Use Cases', url: '/use-cases' },
        ]}
      />
      <MarketingPageShell className="flex flex-col">
        <Navbar />

        <main className="flex-1">
          {/* Hero */}
          <section className="relative overflow-hidden bg-black px-4 pb-20 pt-24">
            <div className="mx-auto max-w-5xl text-center">
              <p className="text-sm font-medium uppercase tracking-[0.3em] text-slate-400">
                Use Cases & Examples
              </p>
              <h1 className="mt-6 text-5xl font-display leading-tight text-white lg:text-6xl">
                Real-World Multi-Agent Workflows
              </h1>
              <p className="mt-6 text-xl font-ui text-slate-400">
                See how teams across fintech, SaaS, e-commerce, and research use Swarm Sync to scale
                operations with autonomous agents.
              </p>
            </div>
          </section>

          {/* Before/After Metrics */}
          <section className="bg-black px-4 py-16">
            <div className="mx-auto max-w-6xl">
              <h2 className="mb-12 text-center text-3xl font-display text-white">
                Typical Results Across Industries
              </h2>
              <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
                {beforeAfterMetrics.map((item) => (
                  <Card key={item.metric} className="border-white/10 bg-white/5 text-center">
                    <CardContent className="space-y-4 p-6">
                      <p className="font-display text-lg text-white">{item.metric}</p>
                      <div className="space-y-2 text-sm font-ui text-slate-400">
                        <div>
                          <span className="opacity-60">Before:</span> {item.before}
                        </div>
                        <div>
                          <span className="font-semibold text-white">After:</span>{' '}
                          <span className="font-semibold text-success">{item.after}</span>
                        </div>
                      </div>
                      <div className="rounded-full bg-success/10 px-3 py-1 text-xs font-medium text-success">
                        {item.improvement}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </section>

          {/* Use Case Details */}
          {useCases.map((useCase, idx) => (
            <section
              key={useCase.title}
              className={`px-4 py-20 ${idx % 2 === 0 ? 'bg-black' : 'bg-black'}`}
            >
              <div className="mx-auto max-w-5xl space-y-8">
                {/* Header */}
                <div className="space-y-4">
                  <div className="inline-block rounded-full bg-white/10 px-4 py-1 text-sm font-medium text-slate-300">
                    {useCase.industry}
                  </div>
                  <h2 className="text-4xl font-display text-white">{useCase.title}</h2>
                </div>

                {/* Challenge/Solution */}
                <div className="grid gap-8 lg:grid-cols-2">
                  <Card className="border-destructive/20 bg-destructive/5">
                    <CardContent className="space-y-2 p-6">
                      <p className="font-display text-sm uppercase tracking-wide text-destructive">
                        The Challenge
                      </p>
                      <p className="font-ui text-white">{useCase.challenge}</p>
                    </CardContent>
                  </Card>

                  <Card className="border-success/20 bg-success/5">
                    <CardContent className="space-y-2 p-6">
                      <p className="font-display text-sm uppercase tracking-wide text-success">
                        The Solution
                      </p>
                      <p className="font-ui text-white">{useCase.solution}</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Results */}
                <Card className="border-white/10/20 bg-black">
                  <CardContent className="space-y-4 p-8">
                    <p className="font-display text-lg text-white">Results</p>
                    <ul className="space-y-2 font-ui text-slate-300">
                      {useCase.results.map((result) => (
                        <li key={result} className="flex items-start gap-2">
                          <span className="text-success">✓</span>
                          <span>{result}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                {/* Workflow */}
                <div className="space-y-4">
                  <p className="font-display text-xl text-white">How It Works</p>
                  <div className="space-y-3">
                    {useCase.workflow.map((step, stepIdx) => (
                      <Card key={stepIdx} className="border-white/10 bg-white/5">
                        <CardContent className="flex gap-4 p-4">
                          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-white/10 text-sm font-display text-slate-300">
                            {stepIdx + 1}
                          </div>
                          <p className="font-ui text-slate-400">{step}</p>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              </div>
            </section>
          ))}

          {/* CTA */}
          <section className="bg-black px-4 py-20">
            <div className="mx-auto max-w-4xl text-center space-y-8">
              <h2 className="text-4xl font-display text-white">
                Ready to Build Your Agent Workflow?
              </h2>
              <p className="text-lg font-ui text-slate-400">
                Start with {TRIAL_LABEL} and see how Swarm Sync can transform your operations with
                autonomous agents.
              </p>
              <div className="flex flex-wrap justify-center gap-4">
                <Button size="lg" asChild>
                  <Link href="/register">Start Free Trial</Link>
                </Button>
                <Button size="lg" variant="outline" asChild>
                  <Link href="/platform">Explore Platform</Link>
                </Button>
              </div>
              <p className="text-sm font-ui text-slate-400">
                {CTA_TRIAL_BADGE}
              </p>
            </div>
          </section>
        </main>

        <Footer />
      </MarketingPageShell>
    </>
  );
}
