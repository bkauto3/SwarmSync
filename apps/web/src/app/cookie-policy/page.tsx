import { Metadata } from 'next';

import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { Card, CardContent } from '@/components/ui/card';

export const metadata: Metadata = {
  title: 'Cookie Policy | Swarm Sync',
  description:
    'Learn about how Swarm Sync uses cookies and similar technologies to improve your experience, analyze usage, and assist with marketing efforts.',
  alternates: {
    canonical: 'https://swarmsync.ai/cookie-policy',
  },
};

const cookieTypes = [
  {
    category: 'Essential Cookies',
    purpose: 'Required for the website to function properly',
    examples: [
      'Session management and authentication',
      'Security and fraud prevention',
      'Load balancing and performance',
    ],
    retention: 'Session or until logout',
    canDisable: false,
  },
  {
    category: 'Analytics Cookies',
    purpose: 'Help us understand how visitors interact with our website',
    examples: [
      'Page views and navigation patterns',
      'Feature usage and engagement metrics',
      'Error tracking and performance monitoring',
    ],
    retention: 'Up to 2 years',
    canDisable: true,
  },
  {
    category: 'Functional Cookies',
    purpose: 'Enable enhanced functionality and personalization',
    examples: [
      'Language preferences',
      'Theme settings (dark/light mode)',
      'Onboarding progress and preferences',
    ],
    retention: 'Up to 1 year',
    canDisable: true,
  },
  {
    category: 'Marketing Cookies',
    purpose: 'Used to deliver relevant advertisements and track campaign effectiveness',
    examples: [
      'Conversion tracking',
      'Retargeting campaigns',
      'Social media integration',
    ],
    retention: 'Up to 2 years',
    canDisable: true,
  },
];

export default function CookiePolicyPage() {
  return (
    <div className="flex min-h-screen flex-col bg-black text-slate-50">
      <Navbar />

      <main className="flex-1 px-4 py-16">
        <div className="mx-auto max-w-4xl space-y-12">
          {/* Header */}
          <div className="space-y-4">
            <p className="text-sm font-medium uppercase tracking-[0.3em] text-muted-foreground">
              Cookie Policy
            </p>
            <h1 className="text-4xl md:text-5xl font-display text-white">
              Cookie Policy & Tracking Technologies
            </h1>
            <p className="text-lg text-slate-400">
              Last updated: {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
            </p>
          </div>

          {/* Introduction */}
          <section className="space-y-4">
            <h2 className="text-2xl font-display text-white">What Are Cookies?</h2>
            <p className="text-slate-300 leading-relaxed">
              Cookies are small text files that are placed on your device when you visit our website. They help us
              provide you with a better experience by remembering your preferences, analyzing how you use our site, and
              assisting with our marketing efforts.
            </p>
            <p className="text-slate-300 leading-relaxed">
              Swarm Sync uses cookies and similar tracking technologies (such as web beacons, pixels, and local storage)
              to operate our platform, improve your experience, and understand how our services are used.
            </p>
          </section>

          {/* Cookie Types */}
          <section className="space-y-6">
            <h2 className="text-2xl font-display text-white">Types of Cookies We Use</h2>
            <div className="space-y-4">
              {cookieTypes.map((type) => (
                <Card key={type.category} className="border-white/10 bg-white/5">
                  <CardContent className="p-6 space-y-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-xl font-semibold text-white mb-2">{type.category}</h3>
                        <p className="text-slate-300">{type.purpose}</p>
                      </div>
                      {type.canDisable && (
                        <span className="text-xs text-emerald-400 font-medium">Optional</span>
                      )}
                      {!type.canDisable && (
                        <span className="text-xs text-slate-400 font-medium">Required</span>
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-300 mb-2">Examples:</p>
                      <ul className="list-disc list-inside space-y-1 text-sm text-slate-400">
                        {type.examples.map((example, idx) => (
                          <li key={idx}>{example}</li>
                        ))}
                      </ul>
                    </div>
                    <p className="text-xs text-slate-400">
                      <strong>Retention:</strong> {type.retention}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>

          {/* Managing Cookies */}
          <section className="space-y-4">
            <h2 className="text-2xl font-display text-white">Managing Your Cookie Preferences</h2>
            <div className="space-y-4 text-slate-300">
              <p>
                You can control and manage cookies in several ways:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>
                  <strong>Browser Settings:</strong> Most browsers allow you to refuse or accept cookies. You can also
                  delete cookies that have already been set. However, disabling essential cookies may impact your
                  ability to use certain features of our platform.
                </li>
                <li>
                  <strong>Cookie Consent Banner:</strong> When you first visit our site, you can accept or decline
                  non-essential cookies through our cookie consent banner.
                </li>
                <li>
                  <strong>Account Settings:</strong> If you have an account, you can manage certain preferences in
                  your account settings.
                </li>
              </ul>
              <p className="text-sm text-slate-400">
                Note: Essential cookies cannot be disabled as they are necessary for the website to function properly.
              </p>
            </div>
          </section>

          {/* Third-Party Cookies */}
          <section className="space-y-4">
            <h2 className="text-2xl font-display text-white">Third-Party Cookies</h2>
            <p className="text-slate-300 leading-relaxed">
              We use third-party services that may set cookies on your device:
            </p>
            <ul className="list-disc list-inside space-y-2 text-slate-300 ml-4">
              <li>
                <strong>Google Analytics:</strong> Helps us understand website usage and improve our services
              </li>
              <li>
                <strong>Stripe:</strong> Payment processing and fraud prevention
              </li>
              <li>
                <strong>Authentication Providers:</strong> OAuth providers (Google, GitHub) for login functionality
              </li>
            </ul>
            <p className="text-sm text-slate-400">
              These third parties have their own privacy policies and cookie practices. We encourage you to review their
              policies.
            </p>
          </section>

          {/* Updates */}
          <section className="space-y-4">
            <h2 className="text-2xl font-display text-white">Updates to This Policy</h2>
            <p className="text-slate-300 leading-relaxed">
              We may update this Cookie Policy from time to time to reflect changes in our practices or for other
              operational, legal, or regulatory reasons. We will notify you of any material changes by posting the new
              Cookie Policy on this page and updating the &quot;Last updated&quot; date.
            </p>
          </section>

          {/* Contact */}
          <section className="space-y-4">
            <h2 className="text-2xl font-display text-white">Questions?</h2>
            <p className="text-slate-300">
              If you have questions about our use of cookies, please contact us at{' '}
              <a href="mailto:privacy@swarmsync.ai" className="text-[var(--accent-primary)] hover:underline">
                privacy@swarmsync.ai
              </a>
              .
            </p>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}
