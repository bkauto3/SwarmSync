const starterPlan = {
  slug: 'starter',
  name: 'Free',
  priceCents: 0,
  seats: 1,
  agentLimit: 3,
  workflowLimit: 1,
  monthlyCredits: 2500,
  takeRateBasisPoints: 2000,
  features: [
    'Agent discovery + marketplace browsing',
    'Transaction history',
    'API access (rate-limited)',
    'Community support',
  ],
};

const plusPlan = {
  slug: 'plus',
  name: 'Starter',
  priceCents: 3900,
  seats: 1,
  agentLimit: 10,
  workflowLimit: 3,
  monthlyCredits: 20000,
  takeRateBasisPoints: 1800,
  features: [
    'Everything in Free',
    'Email support (48h response)',
    'Exports (CSV) + better transaction history',
    'Workflow templates (starter library)',
  ],
  stripeProductId: process.env.STARTER_SWARM_SYNC_TIER_PRODUCT_ID ?? '',
  stripePriceId: process.env.STARTER_SWARM_SYNC_TIER_PRICE_ID ?? '',
};

const growthPlan = {
  slug: 'growth',
  name: 'Pro',
  priceCents: 4900,
  seats: 5,
  agentLimit: 50,
  workflowLimit: 5,
  monthlyCredits: 100000,
  takeRateBasisPoints: 1500,
  features: [
    'Everything in Starter',
    'Priority email support (24h)',
    'Visual Workflow Builder (multi-step agent workflows)',
  ],
  stripeProductId: process.env.PRO_SWARM_SYNC_TIER_PRODUCT_ID ?? '',
  stripePriceId: process.env.PRO_SWARM_SYNC_TIER_PRICE_ID ?? '',
};

const scalePlan = {
  slug: 'scale',
  name: 'Business',
  priceCents: 14900,
  seats: 15,
  agentLimit: 200,
  workflowLimit: 15,
  monthlyCredits: 300000,
  takeRateBasisPoints: 1200,
  features: ['Priority support (12h)', 'Monthly implementation best-practices session'],
  stripeProductId: process.env.BUSINESS_SWARM_SYNC_TIER_PRODUCT_ID ?? '',
  stripePriceId: process.env.BUSINESS_SWARM_SYNC_TIER_PRICE_ID ?? '',
};

const enterprisePlan = {
  slug: 'enterprise',
  name: 'Enterprise',
  priceCents: 0,
  seats: 0,
  agentLimit: 0,
  workflowLimit: 0,
  monthlyCredits: 0,
  takeRateBasisPoints: 200,
  features: ['Dedicated CSM', 'Compliance pack', 'Custom SLAs', 'Private VPC'],
};

export const billingPlanConfigs = [
  starterPlan,
  plusPlan,
  growthPlan,
  scalePlan,
  enterprisePlan,
];
