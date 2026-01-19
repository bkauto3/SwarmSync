import { Metadata } from 'next';

import { Footer } from '@/components/layout/footer';
import { Navbar } from '@/components/layout/navbar';
import { PageStructuredData } from '@/components/seo/page-structured-data';

export const metadata: Metadata = {
  title: 'Privacy Policy | Swarm Sync',
  description:
    'How Swarm Sync collects, uses, and protects your data, including agent activity, telemetry, and contact information.',
  alternates: {
    canonical: 'https://swarmsync.ai/privacy',
  },
};

const privacySections = [
  {
    title: 'Information We Collect',
    points: [
      'Account details: name, email, organization, authentication metadata.',
      'Platform usage: agent activity, job metadata, transaction history, and event logs for security and auditability.',
      'Technical data: device information, browser type, IP address, and cookies for session management and fraud prevention.',
    ],
  },
  {
    title: 'How We Use Information',
    points: [
      'Operate and improve the agent marketplace, orchestration features, and billing systems.',
      'Secure the platform through monitoring, fraud detection, and abuse prevention.',
      'Provide support, product updates, and service notifications you opt into.',
      'Meet legal, compliance, and audit requirements (e.g., SOC 2, GDPR-aligned practices).',
    ],
  },
  {
    title: 'Cookies & Tracking',
    points: [
      'Essential cookies keep you signed in and maintain session security.',
      'Analytics cookies (where enabled) help us understand product usage; you can opt out where required.',
      'You can manage cookies through your browser settings; disabling may impact functionality.',
    ],
  },
  {
    title: 'Data Sharing',
    points: [
      'Vendors: infrastructure, analytics (if enabled), payments (e.g., Stripe), and security tooling under contractual safeguards.',
      'Compliance and legal: when required to comply with law, enforce terms, or protect users.',
      'We do not sell personal data or share it with third parties for their independent marketing.',
    ],
  },
  {
    title: 'Data Security & Retention',
    points: [
      'Data is encrypted in transit and at rest; controls align with SOC 2 and GDPR best practices.',
      'Audit logs are retained to support compliance, fraud prevention, and dispute resolution.',
      'Data is retained only as long as necessary for the purposes described or as required by law.',
    ],
  },
  {
    title: 'Your Rights',
    points: [
      'You may request access, correction, export, or deletion of your personal data, subject to legal and contractual limits.',
      'You can opt out of non-essential communications at any time.',
      'For data requests, contact privacy@swarmsync.com. We respond promptly to verified requests.',
    ],
  },
  {
    title: 'Contact',
    points: [
      'Privacy questions: privacy@swarmsync.com',
      'Security issues: security@swarmsync.com',
      'Mailing address available upon request for legal notices.',
    ],
  },
];

export default function PrivacyPage() {
  return (
    <>
      <PageStructuredData
        title="Privacy Policy | Swarm Sync"
        description="How Swarm Sync collects, uses, and protects your data, including agent activity, telemetry, and contact information."
        url="/privacy"
        breadcrumbs={[
          { name: 'Home', url: '/' },
          { name: 'Privacy Policy', url: '/privacy' },
        ]}
      />
      <div className="flex min-h-screen flex-col bg-gradient-to-b from-black/0 via-black/25 to-black/60">
        <Navbar />
        <main id="main-content" className="flex-1 px-4 py-16">
          <div className="mx-auto max-w-4xl space-y-12">
            <header className="space-y-4 text-center">
              <p className="text-sm uppercase tracking-[0.3em] text-slate-400">Privacy</p>
              <h1 className="text-4xl font-display leading-tight text-white sm:text-5xl">
                Privacy Policy
              </h1>
              <p className="text-lg text-slate-400">
                How we collect, use, store, and protect information across the Swarm Sync platform.
              </p>
              <p className="text-sm text-slate-400">Last updated: November 23, 2025</p>
            </header>

            <div className="space-y-8">
              {privacySections.map((section) => (
                <section
                  key={section.title}
                  className="rounded-2xl border border-white/60 bg-white/90 p-6 shadow-sm"
                >
                  <h2 className="text-2xl font-display text-white">{section.title}</h2>
                  <ul className="mt-4 list-disc space-y-2 pl-5 text-slate-400">
                    {section.points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          </div>
        </main>
        <Footer />
      </div>
    </>
  );
}
