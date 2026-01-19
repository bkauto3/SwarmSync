# Stripe Webhook Configuration & Testing

Use this checklist to wire Stripe events into the `/stripe/webhook` endpoint and verify our DB + wallets update correctly.

## 1. Environment

1. Ensure `.env` (and Fly secrets) include:
   ```bash
   STRIPE_SECRET_KEY=sk_live_or_test
   STRIPE_WEBHOOK_SECRET=whsec_from_dashboard_or_cli
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_or_test
   ```
2. Deploy the API so `https://api.swarmsync.ai/stripe/webhook` is reachable (or expose your local tunnel).

## 2. Connect Stripe Events

### Option A: Stripe Dashboard

1. In the **Developers → Webhooks** tab, add a new endpoint:  
   `https://api.swarmsync.co/stripe/webhook`
2. Subscribe to these event types:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
3. Copy the **Signing secret** and place it in `STRIPE_WEBHOOK_SECRET`.

### Option B: Stripe CLI (local testing)

```bash
stripe login
stripe listen \
  --events checkout.session.completed,customer.subscription.created,customer.subscription.updated,customer.subscription.deleted,invoice.payment_succeeded,invoice.payment_failed \
  --forward-to http://localhost:4000/stripe/webhook
```

Paste the CLI-provided signing secret into `STRIPE_WEBHOOK_SECRET` before running the API.

## 3. Run a Test Checkout

1. In the Swarm Sync dashboard, go to **Console → Billing**.
2. Pick a paid plan or use the new **Credit Top-Up** form and submit a test card (4242…).
3. Stripe will redirect back to `/billing`.

## 4. Verify Persistence

1. Inspect the DB (Neon console or `npx prisma studio`):
   - `organizationSubscription` should reflect the plan, `stripeSubscriptionId`, and refreshed period dates.
   - `invoice` table will store Stripe invoices (if event includes a subscription).
2. For top-ups, the organization wallet should increase:
   ```sql
   select id, balance from "Wallet" where "organizationId" = '<your_org_id>';
   ```
3. Tail API logs to confirm the webhook processed:
   ```bash
   fly logs -a agent-market | rg "Stripe"
   ```
4. Optional: run `stripe events list --limit 10` to see the events delivered to the endpoint.

Once you see the DB rows and wallet balance change, the webhook integration is confirmed. Keep the CLI listener running in staging/dev; for production rely on the Dashboard webhook with the live secret.
