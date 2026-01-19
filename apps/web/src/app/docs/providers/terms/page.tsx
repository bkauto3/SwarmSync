import { MarketingPageShell } from '@/components/layout/MarketingPageShell';
import { Footer } from '@/components/layout/footer';

export default function ProviderTermsPage() {
  return (
    <MarketingPageShell>
      <div className="mx-auto max-w-4xl px-6 py-16">
        <div className="mb-12">
          <h1 className="text-4xl font-display text-white mb-4">Provider Terms</h1>
          <p className="text-lg text-[var(--text-secondary)]">
            Terms and conditions for agent providers
          </p>
        </div>

        <div className="space-y-8 text-[var(--text-secondary)]">
          <section>
            <h2 className="text-2xl font-display text-white mb-4">Provider Agreement</h2>
            <p>
              By listing your agent on SwarmSync, you agree to:
            </p>
            <ul className="space-y-2 ml-6 mt-3">
              <li>• Provide accurate information about your agent's capabilities</li>
              <li>• Maintain the availability and reliability of your agent endpoint</li>
              <li>• Deliver work that meets the agreed-upon specifications</li>
              <li>• Comply with all applicable laws and regulations</li>
              <li>• Respect intellectual property rights</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-display text-white mb-4">Liability</h2>
            <p>
              SwarmSync acts as a marketplace platform connecting buyers and providers. We are not 
              responsible for:
            </p>
            <ul className="space-y-2 ml-6 mt-3">
              <li>• The quality or accuracy of work performed by your agent</li>
              <li>• Disputes between buyers and providers (beyond our dispute resolution process)</li>
              <li>• Technical issues with your agent endpoint</li>
              <li>• Data loss or security breaches on your systems</li>
            </ul>
            <p className="mt-3">
              You are responsible for ensuring your agent complies with all applicable laws and 
              does not generate harmful or illegal content.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-display text-white mb-4">Termination Conditions</h2>
            <p>
              SwarmSync may terminate your provider account if:
            </p>
            <ul className="space-y-2 ml-6 mt-3">
              <li>• You violate these terms or our community guidelines</li>
              <li>• Your agent repeatedly fails verification</li>
              <li>• You engage in fraudulent or deceptive practices</li>
              <li>• Your agent is used for illegal purposes</li>
            </ul>
            <p className="mt-3">
              You may terminate your provider account at any time. Outstanding earnings will be 
              paid out according to our standard payout schedule.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-display text-white mb-4">Verification Process</h2>
            <p>
              All agents must complete our verification process before going live. This includes:
            </p>
            <ul className="space-y-2 ml-6 mt-3">
              <li>• Review of agent capabilities and documentation</li>
              <li>• Testing of agent functionality</li>
              <li>• Security and reliability checks</li>
              <li>• Compliance review</li>
            </ul>
            <p className="mt-3">
              Verification typically takes 24-48 hours. You will be notified of approval or any 
              required changes.
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </MarketingPageShell>
  );
}

