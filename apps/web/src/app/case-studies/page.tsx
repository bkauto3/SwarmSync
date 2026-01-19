import { Metadata } from 'next';
import Link from 'next/link';

import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

export const metadata: Metadata = {
  title: 'Case Studies | Real-World AI Agent Orchestration Results | Swarm Sync',
  description:
    'See how teams use Swarm Sync to scale AI operations. Case studies showing measurable outcomes, cost savings, and ROI from autonomous agent-to-agent workflows.',
  alternates: {
    canonical: 'https://swarmsync.ai/case-studies',
  },
  keywords: [
    'AI agent case studies',
    'agent orchestration results',
    'multi-agent system ROI',
    'autonomous agent workflows',
    'agent-to-agent success stories',
  ],
};

const caseStudies = [
  {
    id: 'fintech-kyc',
    industry: 'Fintech',
    company: 'Leading Digital Bank',
    challenge:
      'Manual KYC verification taking 2-3 days per customer, compliance team overwhelmed with backlog.',
    solution:
      'Orchestrator agent coordinates Document Verification, Data Enrichment, Risk Analysis, and Compliance Check agents in parallel.',
    results: [
      {
        metric: 'Processing Time',
        before: '72 hours',
        after: '3 hours',
        improvement: '95% reduction',
      },
      {
        metric: 'Cost Savings',
        value: '60%',
        description: 'vs. human review',
      },
      {
        metric: 'Accuracy',
        value: '99.2%',
        description: 'with automated verification',
      },
    ],
    workflow: [
      'Document Verification Agent processes ID documents',
      'Data Enrichment Agent pulls credit and identity data',
      'Risk Analysis Agent evaluates fraud signals',
      'Compliance Check Agent validates against regulations',
    ],
    agentsUsed: ['Document Verification', 'Data Enrichment', 'Risk Analysis', 'Compliance Check'],
  },
  {
    id: 'saas-support',
    industry: 'SaaS',
    company: 'Enterprise Software Company',
    challenge:
      'Support tickets increasing 300% YoY, response times degrading, customer satisfaction dropping.',
    solution:
      'Support Orchestrator routes tickets to specialized agents: Technical Support, Billing Inquiry, Feature Request, and Escalation agents.',
    results: [
      {
        metric: 'Response Time',
        before: '24 hours',
        after: '2 hours',
        improvement: '92% faster',
      },
      {
        metric: 'Resolution Rate',
        before: '65%',
        after: '89%',
        improvement: '+24%',
      },
      {
        metric: 'Customer Satisfaction',
        before: '3.2/5',
        after: '4.6/5',
        improvement: '+44%',
      },
    ],
    workflow: [
      'Support Orchestrator analyzes incoming ticket',
      'Routes to appropriate specialist agent',
      'Agent handles inquiry autonomously',
      'Escalation agent handles complex cases',
    ],
    agentsUsed: ['Support Orchestrator', 'Technical Support', 'Billing Inquiry', 'Escalation'],
  },
  {
    id: 'ecommerce-research',
    industry: 'E-commerce',
    company: 'Online Retailer',
    challenge:
      'Competitive intelligence research taking weeks, missing market opportunities, pricing decisions delayed.',
    solution:
      'Research Orchestrator coordinates Market Research, Competitor Analysis, Price Intelligence, and Trend Analysis agents.',
    results: [
      {
        metric: 'Research Time',
        before: '14 days',
        after: '4 hours',
        improvement: '97% faster',
      },
      {
        metric: 'Market Coverage',
        before: '5 competitors',
        after: '50+ competitors',
        improvement: '10x increase',
      },
      {
        metric: 'Decision Speed',
        value: 'Same-day',
        description: 'pricing and inventory decisions',
      },
    ],
    workflow: [
      'Research Orchestrator identifies research needs',
      'Market Research Agent gathers industry data',
      'Competitor Analysis Agent tracks competitor moves',
      'Price Intelligence Agent monitors pricing trends',
    ],
    agentsUsed: [
      'Research Orchestrator',
      'Market Research',
      'Competitor Analysis',
      'Price Intelligence',
    ],
  },
];

export default function CaseStudiesPage() {
  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-black/0 via-black/25 to-black/60">
      <Navbar />
      <main className="flex-1 px-4 py-20">
        <div className="mx-auto max-w-6xl space-y-16">
          {/* Hero */}
          <div className="text-center space-y-6">
            <p className="text-sm font-medium uppercase tracking-[0.3em] text-slate-400">
              Case Studies
            </p>
            <h1 className="text-5xl font-display text-white">
              Real-World Results from Agent Orchestration
            </h1>
            <p className="mx-auto max-w-3xl text-xl text-slate-400">
              See how teams use Swarm Sync to scale AI operations, reduce costs, and improve
              outcomes through autonomous agent-to-agent workflows.
            </p>
          </div>

          {/* Case Studies */}
          <div className="space-y-12">
            {caseStudies.map((study) => (
              <Card key={study.id} className="border-white/10 bg-white/5">
                <CardContent className="space-y-8 p-8">
                  {/* Header */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <span className="rounded-full bg-white/5 px-3 py-1 text-xs font-semibold text-slate-300">
                        {study.industry}
                      </span>
                      <span className="text-sm text-slate-400">{study.company}</span>
                    </div>
                    <h2 className="text-3xl font-display text-white">{study.challenge}</h2>
                  </div>

                  {/* Solution */}
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold text-white">Solution</h3>
                    <p className="text-slate-400">{study.solution}</p>
                  </div>

                  {/* Results */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-white">Results</h3>
                    <div className="grid gap-4 md:grid-cols-3">
                      {study.results.map((result, idx) => (
                        <div
                          key={idx}
                          className="rounded-lg border border-white/10 bg-black p-4 space-y-2"
                        >
                          <p className="text-xs uppercase tracking-wide text-slate-400">
                            {result.metric}
                          </p>
                          {result.before && result.after ? (
                            <>
                              <div className="flex items-baseline gap-2">
                                <span className="text-sm text-slate-400 line-through">
                                  {result.before}
                                </span>
                                <span className="text-xl font-semibold text-white">
                                  {result.after}
                                </span>
                              </div>
                              <p className="text-xs font-medium text-slate-300">
                                {result.improvement}
                              </p>
                            </>
                          ) : (
                            <>
                              <p className="text-xl font-semibold text-white">
                                {result.value}
                              </p>
                              <p className="text-xs text-slate-400">
                                {result.description}
                              </p>
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Workflow */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-white">Workflow</h3>
                    <ol className="space-y-2">
                      {study.workflow.map((step, idx) => (
                        <li key={idx} className="flex items-start gap-3 text-sm text-slate-400">
                          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/5 text-xs font-semibold text-slate-300">
                            {idx + 1}
                          </span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>

                  {/* Agents Used */}
                  <div className="space-y-2">
                    <h3 className="text-sm font-semibold text-white">Agents Used</h3>
                    <div className="flex flex-wrap gap-2">
                      {study.agentsUsed.map((agent) => (
                        <span
                          key={agent}
                          className="rounded-full bg-white/5 px-3 py-1 text-xs text-slate-400"
                        >
                          {agent}
                        </span>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* CTA */}
          <div className="rounded-3xl border border-white/10 bg-black p-12 text-center">
            <h2 className="text-3xl font-display text-white">
              Ready to See Similar Results?
            </h2>
            <p className="mt-4 text-lg text-slate-400">
              Start building your autonomous agent workflows today.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-4">
              <Button size="lg" asChild>
                <Link href="/register">Start Free Trial</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/use-cases">View More Use Cases</Link>
              </Button>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

