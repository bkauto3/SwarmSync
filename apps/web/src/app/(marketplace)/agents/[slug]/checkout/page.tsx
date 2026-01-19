import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface CheckoutPageProps {
  params: { slug: string };
}

export default function AgentCheckoutPlaceholder({ params }: CheckoutPageProps) {
  return (
    <div className="container mx-auto max-w-3xl py-12">
      <Card className="space-y-4 p-8 text-center">
        <h1 className="text-3xl font-bold">Platform Checkout</h1>
        <p className="text-muted-foreground">
          Redirecting to the existing Stripe/escrow checkout flow will be implemented here. For now,
          please return to the agent page to complete your purchase.
        </p>
        <Button asChild>
          <Link href={`/agents/${params.slug}`}>Back to Agent</Link>
        </Button>
      </Card>
    </div>
  );
}
