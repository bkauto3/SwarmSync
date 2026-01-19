import { createAgentMarketClient } from '@agent-market/sdk';
import { expect, test } from '@playwright/test';

const shouldRunSmoke =
  process.env.RUN_STRIPE_SMOKE === '1' || process.env.RUN_STRIPE_SMOKE === 'true';

const apiBaseUrl =
  process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:4000';

const vitest = (import.meta as any).vitest as
  | {
      describe: {
        skip: (name: string, fn: () => void) => void;
      };
    }
  | undefined;

if (vitest) {
  vitest.describe.skip('Stripe legacy checkout (Playwright-only)', () => {});
} else {
  test.describe('Stripe legacy checkout', () => {
    test.skip(!shouldRunSmoke, 'Set RUN_STRIPE_SMOKE=1 to enable the Stripe smoke test.');

    test('completes legacy checkout flow and records fiat payment', async ({ page }) => {
      const agentId = process.env.TEST_AGENT_ID;
      test.skip(!agentId, 'Set TEST_AGENT_ID to a Stripe-enabled agent.');

      const client = createAgentMarketClient({ baseUrl: apiBaseUrl });
      const agent = await client.getAgent(agentId!);

      await page.goto(`/agents/${agent.slug}/purchase`);
      await page.getByText('AgentMarket Balance').click();
      await page.getByRole('button', { name: 'Continue to Checkout' }).click();

      const stripeFrame = page.frameLocator('iframe[name="stripe_checkout_app"]');
      await stripeFrame.getByPlaceholder('Card number').fill('4242424242424242');
      await stripeFrame.getByPlaceholder('MM / YY').fill('12 / 34');
      await stripeFrame.getByPlaceholder('CVC').fill('123');
      await stripeFrame.getByRole('button', { name: /pay/i }).click();

      await expect(page).toHaveURL(/success/i, { timeout: 60_000 });

      const history = await client.getAgentPaymentHistory(agent.id);
      const legacyTransaction = history.find(
        (entry) => entry.rail === 'platform' && entry.reference?.startsWith('ch_'),
      );

      expect(legacyTransaction).toBeDefined();
    });
  });
}

