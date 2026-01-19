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
  priceCents: 2900,
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
  stripeProductId: process.env.PLUS_SWARM_SYNC_TIER_PRODUCT_ID ?? '',
  stripePriceId: process.env.PLUS_SWARM_SYNC_TIER_PRICE_ID ?? '',
};

const growthPlan = {
  slug: 'growth',
  name: 'Pro',
  priceCents: 9900,
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
  stripeProductId: process.env.GROWTH_SWARM_SYNC_TIER_PRODUCT_ID ?? '',
  stripePriceId: process.env.GROWTH_SWARM_SYNC_TIER_PRICE_ID ?? '',
};

const scalePlan = {
  slug: 'scale',
  name: 'Business',
  priceCents: 19900,
  seats: 15,
  agentLimit: 200,
  workflowLimit: 15,
  monthlyCredits: 500000,
  takeRateBasisPoints: 1200,
  features: ['Priority support (12h)', 'Monthly implementation best-practices session'],
  stripeProductId: process.env.SCALE_SWARM_SYNC_TIER_PRODUCT_ID ?? '',
  stripePriceId: process.env.SCALE_SWARM_SYNC_TIER_PRICE_ID ?? '',
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
