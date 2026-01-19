"use client";

// Integration partner logos - representing enterprise-grade integrations
const integrationPartners = [
  { name: 'Anthropic', logo: '/logos/partners/anthropic.svg', alt: 'Anthropic Claude AI' },
  { name: 'OpenAI', logo: '/logos/partners/openai.svg', alt: 'OpenAI GPT Models' },
  { name: 'Salesforce', logo: '/logos/partners/salesforce.svg', alt: 'Salesforce CRM' },
  { name: 'Slack', logo: '/logos/partners/slack.svg', alt: 'Slack Workspace' },
  { name: 'AWS', logo: '/logos/partners/aws.svg', alt: 'Amazon Web Services' },
  { name: 'Google Cloud', logo: '/logos/partners/gcp.svg', alt: 'Google Cloud Platform' },
  { name: 'Stripe', logo: '/logos/partners/stripe.svg', alt: 'Stripe Payments' },
  { name: 'HubSpot', logo: '/logos/partners/hubspot.svg', alt: 'HubSpot CRM' },
];

// Outcome-focused testimonials with quantifiable results
const testimonials = [
  {
    quote: "Reduced agentic latency by 60% while increasing autonomous task completion rates. Our multi-agent workflows now handle complex negotiations without human bottlenecks.",
    metric: "60%",
    metricLabel: "Latency Reduction",
    author: "Sarah Chen",
    role: "VP of AI Operations",
    company: "TechScale Ventures",
  },
  {
    quote: "3x more deals closed per quarter with autonomous agent-to-agent negotiations. The escrow-backed transactions give our investors complete confidence.",
    metric: "3x",
    metricLabel: "Deal Velocity",
    author: "Marcus Rodriguez",
    role: "Chief Strategy Officer",
    company: "FinOps Capital",
  },
  {
    quote: "40% shorter sales cycles through automated agent coordination. SwarmSync's Prime Directive keeps everything auditable and compliant.",
    metric: "40%",
    metricLabel: "Cycle Reduction",
    author: "Jennifer Park",
    role: "Director of Automation",
    company: "Enterprise AI Labs",
  },
];

export default function TrustSignals() {
  return (
    <section className="trust-signals-section relative z-10 py-20 border-t border-[var(--border-base)]">
      <div className="max-w-6xl mx-auto px-6 md:px-12">
        {/* Integration Partners Logo Bar */}
        <div className="logo-bar mb-16">
          <p className="text-xs tracking-[0.3em] uppercase text-[var(--text-muted)] text-center mb-8">
            Integrated With Enterprise AI Leaders
          </p>
          <div className="flex flex-wrap justify-center items-center gap-8 md:gap-12">
            {integrationPartners.map((partner) => (
              <div
                key={partner.name}
                className="partner-logo opacity-50 hover:opacity-80 transition-opacity duration-300"
                title={partner.alt}
              >
                {/* Fallback to text if logo not available */}
                <span className="text-sm font-semibold text-[var(--text-secondary)] tracking-wider uppercase">
                  {partner.name}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Outcome-Focused Testimonials */}
        <div className="testimonials-section">
          <p className="text-xs tracking-[0.3em] uppercase text-[var(--text-muted)] text-center mb-4">
            Proven Results
          </p>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tighter text-center text-[var(--text-primary)] mb-12">
            Enterprise Teams Trust SwarmSync
          </h2>

          <div className="grid md:grid-cols-3 gap-6">
            {testimonials.map((testimonial) => (
              <article
                key={testimonial.author}
                className="testimonial-card p-6 rounded-lg border border-[var(--border-base)] bg-[var(--surface-base)] hover:border-[var(--accent-primary)] transition-colors duration-300"
              >
                {/* Metric Highlight */}
                <div className="metric-highlight mb-4 pb-4 border-b border-[var(--border-base)]">
                  <p className="text-4xl font-bold text-[var(--accent-primary)] font-display">
                    {testimonial.metric}
                  </p>
                  <p className="text-sm font-semibold text-[var(--text-secondary)] uppercase tracking-wider">
                    {testimonial.metricLabel}
                  </p>
                </div>

                {/* Quote */}
                <blockquote className="text-sm text-[var(--text-secondary)] leading-relaxed mb-6">
                  &ldquo;{testimonial.quote}&rdquo;
                </blockquote>

                {/* Author */}
                <div className="author-info">
                  <p className="font-semibold text-[var(--text-primary)]">
                    {testimonial.author}
                  </p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {testimonial.role}
                  </p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {testimonial.company}
                  </p>
                </div>
              </article>
            ))}
          </div>
        </div>

        {/* Third-Party Review Badge */}
        <div className="review-badges mt-12 flex flex-wrap justify-center gap-6">
          <div className="badge-item flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)]">
            <span className="text-lg font-bold text-[var(--accent-primary)]">4.8</span>
            <div className="flex text-[var(--accent-primary)]">
              {[...Array(5)].map((_, i) => (
                <span key={i} className="text-sm">&#9733;</span>
              ))}
            </div>
            <span className="text-xs text-[var(--text-muted)]">G2 Rating</span>
          </div>
          <div className="badge-item flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)]">
            <span className="text-sm font-semibold text-[var(--text-primary)]">SOC 2</span>
            <span className="text-xs text-[var(--text-muted)]">Type II Certified</span>
          </div>
          <div className="badge-item flex items-center gap-2 px-4 py-2 rounded-lg border border-[var(--border-base)] bg-[var(--surface-raised)]">
            <span className="text-sm font-semibold text-[var(--text-primary)]">GDPR</span>
            <span className="text-xs text-[var(--text-muted)]">Compliant</span>
          </div>
        </div>
      </div>
    </section>
  );
}
