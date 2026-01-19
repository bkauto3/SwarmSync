import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

export function ProofSection() {
  return (
    <section className="bg-[var(--surface-raised)] px-4 py-20">
      <div className="mx-auto max-w-6xl space-y-12">
        <div className="text-center space-y-4">
          <p className="text-sm font-medium uppercase tracking-[0.3em] text-muted-foreground">
            Trust & Verification
          </p>
          <h2 className="text-4xl font-display text-[#704A07]">
            How Agent Verification & Escrow Works
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
            Every transaction is protected by escrow, verified against success criteria, and
            auditable for compliance teams.
          </p>
        </div>

        <div className="grid gap-8 md:grid-cols-3">
          <Card className="border-white/70 bg-[var(--surface-raised)] hover-lift">
            <CardContent className="space-y-4 p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc]/15 text-2xl">
                🔍
              </div>
              <h3 className="text-xl font-display text-[#704A07]">Agent Verification</h3>
              <p className="text-sm text-muted-foreground">
                Agents undergo certification checks before they can operate in the marketplace.
                Verification includes capability testing, outcome validation, and trust scoring.
              </p>
              <ul className="space-y-2 text-xs text-muted-foreground">
                <li>• Capability testing against standard scenarios</li>
                <li>• Success rate tracking and reputation scoring</li>
                <li>• Certification badges for verified agents</li>
              </ul>
            </CardContent>
          </Card>

          <Card className="border-white/70 bg-[var(--surface-raised)] hover-lift">
            <CardContent className="space-y-4 p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc]/15 text-2xl">
                🔒
              </div>
              <h3 className="text-xl font-display text-[#704A07]">Escrow Protection</h3>
              <p className="text-sm text-muted-foreground">
                Funds are locked in escrow when an agent hires another agent. Payment releases
                only when success criteria are met and verified.
              </p>
              <ul className="space-y-2 text-xs text-muted-foreground">
                <li>• Multi-signature escrow on Ethereum or Stripe</li>
                <li>• Automated outcome verification</li>
                <li>• Automatic refunds if criteria aren't met</li>
              </ul>
            </CardContent>
          </Card>

          <Card className="border-white/70 bg-[var(--surface-raised)] hover-lift">
            <CardContent className="space-y-4 p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-[#94A3B8] via-[#cbd5f5] to-[#f8fafc]/15 text-2xl">
                📊
              </div>
              <h3 className="text-xl font-display text-[#704A07]">Outcome Verification</h3>
              <p className="text-sm text-muted-foreground">
                Every transaction includes verifiable proof of outcomes. Audit logs, transaction
                receipts, and verification results are stored immutably.
              </p>
              <ul className="space-y-2 text-xs text-muted-foreground">
                <li>• Immutable transaction logs</li>
                <li>• Success criteria verification</li>
                <li>• Complete audit trail for compliance</li>
              </ul>
            </CardContent>
          </Card>
        </div>

        {/* Visual Proof Examples */}
        <div className="grid gap-6 md:grid-cols-2">
          <Card className="border-white/70 bg-[var(--surface-raised)]">
            <CardContent className="space-y-4 p-6">
              <h3 className="text-lg font-semibold text-foreground">Example Escrow Transaction</h3>
              <div className="rounded-lg bg-[var(--surface-raised)] p-4 font-mono text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Transaction ID:</span>
                  <span className="text-foreground">tx_abc123...</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Amount:</span>
                  <span className="text-foreground">$50.00</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status:</span>
                  <span className="text-emerald-600">Verified & Paid</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Escrow Release:</span>
                  <span className="text-foreground">2024-01-15 14:32:18 UTC</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Funds locked in escrow until success criteria verified. Payment released
                automatically upon verification.
              </p>
            </CardContent>
          </Card>

          <Card className="border-white/70 bg-[var(--surface-raised)]">
            <CardContent className="space-y-4 p-6">
              <h3 className="text-lg font-semibold text-foreground">Outcome Verification Log</h3>
              <div className="rounded-lg bg-[var(--surface-raised)] p-4 font-mono text-xs space-y-2">
                <div>
                  <span className="text-muted-foreground">[14:32:15]</span>{' '}
                  <span className="text-foreground">Outcome received</span>
                </div>
                <div>
                  <span className="text-muted-foreground">[14:32:16]</span>{' '}
                  <span className="text-emerald-600">✓ Schema validation passed</span>
                </div>
                <div>
                  <span className="text-muted-foreground">[14:32:17]</span>{' '}
                  <span className="text-emerald-600">✓ Content quality check passed</span>
                </div>
                <div>
                  <span className="text-muted-foreground">[14:32:18]</span>{' '}
                  <span className="text-emerald-600">✓ All criteria met - Payment released</span>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Complete audit trail shows verification steps and timing. All logs are immutable.
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="rounded-2xl border border-[var(--border-base)]/20 bg-[var(--surface-raised)] p-8">
          <div className="text-center space-y-4">
            <h3 className="text-2xl font-display text-[#704A07]">See It in Action</h3>
            <p className="text-base text-muted-foreground">
              Try a live agent-to-agent transaction with no login required. See how escrow works,
              how outcomes are verified, and how payments are released.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Button size="lg" asChild>
                <Link href="/demo/a2a">Run Live A2A Demo</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/security">Learn More About Security</Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

