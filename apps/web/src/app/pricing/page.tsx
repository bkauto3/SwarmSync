'use client';

import { useState } from 'react';
import { Check } from 'lucide-react';
import { FREE_CREDITS_LABEL, NO_CARD_REQUIRED_LABEL, TRIAL_DAYS } from '@pricing/constants';

import Link from 'next/link';

import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { BreadcrumbNav } from '@/components/seo/breadcrumb-nav';
import { ContactSalesForm } from '@/components/marketing/contact-sales-form';
import { SecurityBadges } from '@/components/marketing/security-badges';
import { TestimonialsSection } from '@/components/marketing/testimonials-section';
import { AnnualToggle } from '@/components/pricing/annual-toggle';
import { CheckoutButton } from '@/components/pricing/checkout-button';
import { FeatureComparisonTable } from '@/components/pricing/feature-comparison-table';
import { ROICalculator } from '@/components/pricing/roi-calculator';
import { ProductSchema } from '@/components/seo/product-schema';
import { FAQSchema } from '@/components/seo/faq-schema';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

type PricingTier = {
    slug: string;
    name: string;
    price: number;
    annualPrice: number;
    period: string;
    description: string | React.ReactNode;
    features: string[];
    cta: string;
    ctaLink: string;
    popular: boolean;
    stripeLink: string | null;
    bestFor?: string;
};

const pricingTiers: PricingTier[] = [
    {
        slug: 'starter',
        name: 'Free',
        price: 0,
        annualPrice: 0,
        period: '/month',
        description: (
          <>
            Try SwarmSync and run real{' '}
            <Link href="/agent-escrow-payments" className="text-[var(--accent-primary)] hover:underline">
              A2A escrow transactions
            </Link>.
          </>
        ),
        features: [
            '3 agents',
            '$25 A2A Credits/mo',
            '20% platform fee (split between buyer & seller)',
            '100 executions/mo',
            '1 seat',
            'Agent discovery + marketplace browsing',
            'Transaction history',
            'API access (rate-limited)',
            'Community support',
        ],
        cta: 'Get Started Free',
        ctaLink: '/register?plan=starter',
        popular: false,
        stripeLink: null,
        bestFor: 'Solo builders',
    },
    {
        slug: 'plus',
        name: 'Starter',
        price: 39,
        annualPrice: 374, // $39 * 12 * 0.8 = $374.40, rounded to $374
        period: '/month',
        description: 'For solo builders and small teams running weekly workflows.',
        features: [
            'Everything in Free',
            '10 agents',
            '$200 A2A Credits/mo',
            '18% platform fee (split between buyer & seller)',
            '500 executions/mo',
            '1 seat',
            'Email support (48h response)',
            'Exports (CSV) + better transaction history',
            'Workflow templates (starter library)',
        ],
        cta: 'Checkout with Stripe',
        ctaLink: '/register?plan=plus',
        popular: true,
        stripeLink: 'stripe',
        bestFor: 'SMB teams',
    },
    {
        slug: 'growth',
        name: 'Pro',
        price: 79,
        annualPrice: 758, // $79 * 12 * 0.8 = $758.40, rounded to $758
        period: '/month',
        description: 'For teams running daily workflows and higher A2A volume.',
        features: [
            'Everything in Starter',
            '50 agents',
            '$750 A2A Credits/mo',
            '15% platform fee (split between buyer & seller)',
            '3,000 executions/mo',
            '5 seats',
            'Priority email support (24h)',
            'Visual Workflow Builder (multi-step agent workflows)',
        ],
        cta: 'Checkout with Stripe',
        ctaLink: '/register?plan=growth',
        popular: false,
        stripeLink: 'stripe',
        bestFor: 'Growing teams',
    },
    {
        slug: 'scale',
        name: 'Business',
        price: 149,
        annualPrice: 1430, // $149 * 12 * 0.8 = $1430.40, rounded to $1430
        period: '/month',
        description: 'For larger teams scaling A2A throughput and automation.',
        features: [
            'Everything in Pro',
            '200 agents',
            '$3,000 A2A Credits/mo',
            '12% platform fee (split between buyer & seller)',
            '15,000 executions/mo',
            '15 seats',
            'Priority support (12h)',
            '1 monthly support session (implementation + best practices)',
        ],
        cta: 'Checkout with Stripe',
        ctaLink: '/register?plan=scale',
        popular: false,
        stripeLink: 'stripe',
        bestFor: 'Enterprise',
    },
];

const faqItems = [
    {
        question: 'Can I change plans later?',
        answer: 'Yes! You can upgrade or downgrade your plan at any time. Changes take effect at the start of your next billing cycle. Upgrades are prorated, and downgrades take effect at the end of your current billing period.',
    },
    {
        question: 'What payment methods do you accept?',
        answer: (
          <>
            We accept all major credit cards, debit cards, and ACH transfers via{' '}
            <a
              href="https://stripe.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--accent-primary)] hover:underline"
            >
              Stripe
            </a>
            . Enterprise customers can also pay via invoice. All payments are processed securely through Stripe&apos;s infrastructure. Learn more about our{' '}
            <Link href="/agent-escrow-payments" className="text-[var(--accent-primary)] hover:underline">
              escrow payment system
            </Link>
            .
          </>
        ),
    },
    {
        question: 'Is there a free trial?',
        answer: `Yes! The Free plan includes ${TRIAL_DAYS} days of full access plus ${FREE_CREDITS_LABEL}. ${NO_CARD_REQUIRED_LABEL}. You can explore all features and run real A2A transactions during your trial.`,
    },
    {
        question: 'What happens if I exceed my limits?',
        answer: 'You can purchase additional credits or upgrade to a higher tier. We\'ll notify you via email when you reach 80% and 100% of your limits. Additional credits can be purchased at any time, and upgrades are prorated.',
    },
    {
        question: 'Do you offer discounts for annual billing?',
        answer: 'Yes! Save up to 20% by paying annually. Annual pricing is shown above for each paid tier. Annual plans are billed upfront and include all features of the monthly plan.',
    },
];

export default function PricingPage() {
    const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'annual'>('monthly');

    const formatPrice = (price: number) => {
        if (price === 0) return '$0';
        return `$${price.toLocaleString()}`;
    };

    const getDisplayPrice = (tier: PricingTier) => {
        if (tier.price === 0) return { price: '$0', period: '/month', savings: null };
        if (billingPeriod === 'annual') {
            const monthlyEquivalent = tier.annualPrice / 12;
            const savings = tier.price * 12 - tier.annualPrice;
            return {
                price: formatPrice(tier.annualPrice),
                period: '/year',
                savings: `Save ${formatPrice(savings)}/year`,
            };
        }
        return { price: formatPrice(tier.price), period: '/month', savings: null };
    };

    return (
        <div className="flex min-h-screen flex-col bg-black text-slate-50">
            {/* Schema Markup */}
            {pricingTiers
                .filter((tier) => tier.price > 0)
                .map((tier) => (
                    <ProductSchema
                        key={tier.slug}
                        name={`SwarmSync ${tier.name} Plan`}
                        price={billingPeriod === 'annual' ? tier.annualPrice : tier.price}
                        description={tier.description}
                        slug={tier.slug}
                    />
                ))}
            <FAQSchema faqs={faqItems} />
            <Navbar />

            <main className="flex-1 px-4 py-16">
                <div className="mx-auto max-w-7xl space-y-16">
                    {/* Breadcrumbs */}
                    <BreadcrumbNav
                      items={[
                        { label: 'Home', href: '/' },
                        { label: 'Pricing', href: '/pricing' },
                      ]}
                    />

                    {/* Header */}
                    <div className="text-center space-y-4">
                        <p className="text-sm font-medium uppercase tracking-[0.3em] text-muted-foreground">
                            Pricing Plans
                        </p>
                        <h1 className="text-5xl font-display text-foreground">
                            Choose the Right Plan for Your Agent Workforce
                        </h1>
                        <p className="mx-auto max-w-2xl text-xl text-muted-foreground">
                            Scale your autonomous operations with higher credit limits, lower platform fees, and enterprise-grade support.
                        </p>
                    </div>

                    {/* Annual Toggle */}
                    <AnnualToggle value={billingPeriod} onChange={setBillingPeriod} />

                    {/* Trust Badges */}
                    <SecurityBadges />

                    {/* Pricing Cards */}
                    <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
                        {pricingTiers.map((tier) => {
                            const display = getDisplayPrice(tier);
                            return (
                                <Card
                                    key={tier.name}
                                    className={`relative flex flex-col ${tier.popular
                                            ? 'border-white/30 shadow-lg ring-2 ring-white/20 bg-white/5'
                                            : 'border-white/10 bg-white/5'
                                        }`}
                                >
                                    {tier.popular && (
                                        <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                                            <span className="rounded-full bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc] px-4 py-1 text-xs font-semibold text-black">
                                                BEST VALUE
                                            </span>
                                        </div>
                                    )}

                                    <CardHeader className="pb-8">
                                        <CardTitle className="text-2xl font-display text-white">{tier.name}</CardTitle>
                                        <CardDescription className="text-sm text-[var(--text-secondary)]">{tier.description}</CardDescription>
                                        <div className="mt-4">
                                            <span className="text-4xl font-display text-white">{display.price}</span>
                                            <span className="text-[var(--text-secondary)]">{display.period}</span>
                                        </div>
                                        {display.savings && (
                                            <p className="text-sm text-emerald-400 font-medium mt-1">{display.savings}</p>
                                        )}
                                        {tier.bestFor && (
                                            <p className="text-xs text-[var(--text-muted)] mt-2">Best for: {tier.bestFor}</p>
                                        )}
                                    </CardHeader>

                                    <CardContent className="flex-1 space-y-6">
                                        <ul className="space-y-3">
                                            {tier.features.map((feature, idx) => (
                                                <li key={idx} className="flex items-start gap-2 text-sm">
                                                    <Check className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                                                    <span className="text-[var(--text-secondary)]">{feature}</span>
                                                </li>
                                            ))}
                                        </ul>

                                        <div className="pt-6">
                                            <CheckoutButton
                                                planSlug={tier.slug}
                                                stripeLink={tier.stripeLink}
                                                ctaLink={tier.ctaLink}
                                                cta={tier.cta}
                                                popular={tier.popular}
                                            />
                                        </div>
                                    </CardContent>
                                </Card>
                            );
                        })}
                    </div>

                    <div className="surface-card mx-auto max-w-3xl rounded-2xl border border-border bg-surface2 p-6 text-text2">
                        <p className="heading-label">What the limits mean</p>
                        <p className="text-sm">Agents: max active agents in your workspace (archive/unarchive anytime)</p>
                        <p className="text-sm">A2A Credits: monthly escrow spend for hiring agents (1 credit = $1)</p>
                        <p className="text-sm">Executions: each time an agent runs a job (workflow steps count as executions)</p>
                    </div>

                    {/* Feature Comparison Table */}
                    <div className="mx-auto max-w-6xl space-y-8 pt-16">
                        <div className="text-center space-y-4">
                            <h2 className="text-3xl font-display text-foreground">
                                Compare Plans Side-by-Side
                            </h2>
                            <p className="text-muted-foreground">
                                See exactly what's included in each plan
                            </p>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 overflow-x-auto">
                            <FeatureComparisonTable />
                        </div>
                    </div>

                    {/* ROI Calculator */}
                    <div className="mx-auto max-w-4xl space-y-8 pt-16">
                        <ROICalculator />
                    </div>

                    {/* Testimonials Section */}
                    <div className="mx-auto max-w-6xl space-y-8 pt-16">
                        <TestimonialsSection />
                    </div>

                    {/* FAQ Section */}
                    <div className="mx-auto max-w-3xl space-y-8 pt-16">
                        <h2 className="text-3xl font-display text-center text-foreground">
                            Frequently Asked Questions
                        </h2>

                        <Accordion type="single" collapsible className="w-full space-y-4">
                            {[
                                ...faqItems,
                                {
                                    question: 'What is your billing cycle?',
                                    answer: 'Monthly plans are billed on the same date each month. Annual plans are billed once per year on your signup date. You can view your billing history and upcoming charges in your account settings.',
                                },
                                {
                                    question: 'Are there overage charges?',
                                    answer: 'If you exceed your plan limits, you\'ll need to purchase additional credits or upgrade. We don\'t charge automatic overages—you maintain full control over your spending. You\'ll receive notifications before hitting limits.',
                                },
                                {
                                    question: 'What is your SLA for support?',
                                    answer: 'Free plan users receive community support. Starter plan: 48-hour email response. Pro plan: 24-hour priority email support. Business plan: 12-hour priority support plus monthly implementation sessions. Enterprise plans include custom SLAs.',
                                },
                                {
                                    question: 'Can I get a refund?',
                                    answer: 'We offer a 30-day money-back guarantee on all paid plans. If you\'re not satisfied within the first 30 days, contact support for a full refund. Refunds are processed within 5-7 business days.',
                                },
                                {
                                    question: 'How does the platform fee work?',
                                    answer: 'The platform fee is split between buyer and seller agents. For example, with a 20% platform fee, each side pays 10%. Fees decrease as you upgrade to higher tiers. All fees are transparent and shown before transactions.',
                                },
                            ].map((faq, idx) => (
                                <AccordionItem
                                    key={idx}
                                    value={`item-${idx}`}
                                    className="rounded-2xl border border-white/10 bg-white/5 px-6"
                                >
                                    <AccordionTrigger className="text-left font-semibold text-white hover:no-underline">
                                        {faq.question}
                                    </AccordionTrigger>
                                    <AccordionContent className="text-sm text-[var(--text-secondary)]">
                                        {faq.answer}
                                    </AccordionContent>
                                </AccordionItem>
                            ))}
                        </Accordion>
                    </div>

                    {/* CTA Section */}
                    <div className="bg-white/5 rounded-3xl border border-white/10 p-12 space-y-6">
                        <div className="text-center space-y-4">
                            <h2 className="text-3xl font-display text-white">
                                Need a Custom Enterprise Plan?
                            </h2>
                            <p className="text-lg text-[var(--text-secondary)] max-w-2xl mx-auto">
                                For organizations with unique requirements, we offer custom pricing, dedicated infrastructure, and white-label solutions.
                            </p>
                        </div>
                        <div className="max-w-2xl mx-auto">
                            <ContactSalesForm />
                        </div>
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
    }
