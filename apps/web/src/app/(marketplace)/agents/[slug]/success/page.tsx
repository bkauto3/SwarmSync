import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface SuccessPageProps {
  params: { slug: string };
  searchParams: { tx?: string };
}

export default function AgentPurchaseSuccessPage({ params, searchParams }: SuccessPageProps) {
  const txHash = searchParams?.tx;

  return (
    <div className="container mx-auto max-w-3xl py-12">
      <Card className="space-y-4 p-8 text-center">
        <h1 className="text-3xl font-bold">Payment Confirmed</h1>
        <p className="text-muted-foreground">
          Your transaction has been verified. The agent will begin processing your request shortly.
        </p>
        {txHash && (
          <p className="text-sm text-muted-foreground">
            Transaction reference: <span className="font-mono">{txHash}</span>
          </p>
        )}
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Button asChild>
            <Link href={`/agents/${params.slug}`}>Back to Agent</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href={`/agents/${params.slug}/purchase`}>Make Another Purchase</Link>
          </Button>
        </div>
      </Card>
    </div>
  );
}
