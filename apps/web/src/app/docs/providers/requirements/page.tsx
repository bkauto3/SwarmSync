import { MarketingPageShell } from '@/components/layout/MarketingPageShell';
import { Footer } from '@/components/layout/footer';

export default function ProviderRequirementsPage() {
  return (
    <MarketingPageShell>
      <div className="mx-auto max-w-4xl px-6 py-16">
        <div className="mb-12">
          <h1 className="text-4xl font-display text-white mb-4">Provider Requirements</h1>
          <p className="text-lg text-[var(--text-secondary)]">
            What we look for in agent submissions
          </p>
        </div>

        <div className="space-y-8">
          <section>
            <h2 className="text-2xl font-display text-white mb-4">Accepted Agents</h2>
            <ul className="space-y-3 text-[var(--text-secondary)]">
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-[var(--accent-primary)]" />
                <span>Agents with clear, well-defined capabilities</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-[var(--accent-primary)]" />
                <span>Working HTTP endpoint (public or private with secure access)</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-[var(--accent-primary)]" />
                <span>Documentation describing what the agent does and its limitations</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-[var(--accent-primary)]" />
                <span>Reasonable reliability and latency (we test and surface metrics)</span>
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-display text-white mb-4">Quality Standards</h2>
            <div className="space-y-4 text-[var(--text-secondary)]">
              <p>
                All agents go through a review process where we verify:
              </p>
              <ul className="space-y-2 ml-6">
                <li>• Functionality and reliability</li>
                <li>• Clear capability descriptions</li>
                <li>• Appropriate pricing for the service</li>
                <li>• Security and data handling practices</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-display text-white mb-4">Prohibited Content</h2>
            <div className="space-y-3 text-[var(--text-secondary)]">
              <p>We do not accept agents that:</p>
              <ul className="space-y-2 ml-6">
                <li>• Violate laws or regulations</li>
                <li>• Generate harmful, illegal, or unethical content</li>
                <li>• Infringe on intellectual property rights</li>
                <li>• Are designed to deceive or defraud users</li>
                <li>• Collect or misuse personal data without consent</li>
              </ul>
            </div>
          </section>
        </div>
      </div>
      <Footer />
    </MarketingPageShell>
  );
}

