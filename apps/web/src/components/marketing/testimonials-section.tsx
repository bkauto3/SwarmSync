import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

const testimonials = [
  {
    quote:
      'Swarm Sync reduced our KYC processing time from 72 hours to 3 hours. The autonomous agent workflows handle 95% of cases without human intervention.',
    author: 'Sarah Chen',
    role: 'Head of Operations',
    company: 'Digital Bank',
    industry: 'Fintech',
  },
  {
    quote:
      'We went from manually researching 5 competitors to automatically tracking 50+ with same-day pricing decisions. Game changer for our e-commerce operations.',
    author: 'Marcus Rodriguez',
    role: 'VP of Strategy',
    company: 'Online Retailer',
    industry: 'E-commerce',
  },
  {
    quote:
      'Support ticket resolution improved from 65% to 89% with autonomous routing. Customer satisfaction scores jumped 44% in just 3 months.',
    author: 'Jennifer Park',
    role: 'Director of Customer Success',
    company: 'SaaS Platform',
    industry: 'SaaS',
  },
];

export function TestimonialsSection() {
  return (
    <section className="px-4 py-20">
      <div className="mx-auto max-w-6xl space-y-12">
        <div className="text-center space-y-4">
          <p className="text-sm font-medium uppercase tracking-[0.3em] text-muted-foreground">
            Customer Success
          </p>
          <h2 className="text-4xl font-display text-white">
            Trusted by Teams Scaling AI Operations
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
            See how teams use Swarm Sync to scale autonomous agent workflows and achieve measurable
            results.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {testimonials.map((testimonial, idx) => (
            <Card key={idx} className="border-white/10 bg-white/5 hover:border-white/20 transition-colors">
              <CardContent className="space-y-4 p-6">
                <div className="flex items-start gap-1">
                  {[...Array(5)].map((_, i) => (
                    <span key={i} className="text-yellow-400 text-lg">
                      ★
                    </span>
                  ))}
                </div>
                <p className="text-sm text-slate-300 italic">&ldquo;{testimonial.quote}&rdquo;</p>
                <div className="pt-4 border-t border-white/10">
                  <p className="font-semibold text-white">{testimonial.author}</p>
                  <p className="text-xs text-slate-400">{testimonial.role}</p>
                  <p className="text-xs text-slate-300">{testimonial.company}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="text-center">
          <Button variant="outline" size="lg" asChild>
            <Link href="/case-studies">Read Full Case Studies</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}

