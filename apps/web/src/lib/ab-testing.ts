/**
 * A/B Testing Infrastructure
 *
 * Lightweight A/B testing system integrated with Google Analytics.
 * Uses localStorage for variant persistence across sessions.
 */

import { trackEvent } from './analytics';

export type VariantId = 'A' | 'B';

export interface ABTest {
  id: string;
  name: string;
  variants: {
    A: {
      name: string;
      weight: number; // 0-100
    };
    B: {
      name: string;
      weight: number; // 0-100
    };
  };
  enabled: boolean;
}

// Active A/B tests configuration
export const AB_TESTS: Record<string, ABTest> = {
  'homepage-cta': {
    id: 'homepage-cta',
    name: 'Homepage CTA Copy',
    variants: {
      A: {
        name: 'Start Free Trial',
        weight: 50,
      },
      B: {
        name: 'See Agents in Action',
        weight: 50,
      },
    },
    enabled: false, // Enable when ready to test
  },
  'pricing-display': {
    id: 'pricing-display',
    name: 'Pricing Display Format',
    variants: {
      A: {
        name: 'Monthly Default',
        weight: 50,
      },
      B: {
        name: 'Annual Default',
        weight: 50,
      },
    },
    enabled: false,
  },
  'trial-length': {
    id: 'trial-length',
    name: 'Trial Period Length',
    variants: {
      A: {
        name: '14 Days',
        weight: 50,
      },
      B: {
        name: '30 Days',
        weight: 50,
      },
    },
    enabled: false,
  },
};

const STORAGE_KEY_PREFIX = 'ab_test_';

/**
 * Get the assigned variant for a test
 * Returns consistent variant for the same user across sessions
 */
export function getVariant(testId: string): VariantId {
  const test = AB_TESTS[testId];

  if (!test || !test.enabled) {
    return 'A'; // Default to control group if test disabled
  }

  // Check if user already has an assigned variant
  const storageKey = `${STORAGE_KEY_PREFIX}${testId}`;
  const stored = typeof window !== 'undefined' ? localStorage.getItem(storageKey) : null;

  if (stored === 'A' || stored === 'B') {
    return stored as VariantId;
  }

  // Assign new variant based on weights
  const variant = assignVariant(test.variants.A.weight, test.variants.B.weight);

  // Store variant
  if (typeof window !== 'undefined') {
    localStorage.setItem(storageKey, variant);

    // Track variant assignment
    trackEvent('ab_test_assigned', {
      test_id: testId,
      test_name: test.name,
      variant,
      variant_name: test.variants[variant].name,
    });
  }

  return variant;
}

/**
 * Assign variant based on weights
 */
function assignVariant(weightA: number, weightB: number): VariantId {
  const total = weightA + weightB;
  const random = Math.random() * total;

  return random < weightA ? 'A' : 'B';
}

/**
 * Track conversion for A/B test
 * Call this when a user completes the goal action (signup, purchase, etc.)
 */
export function trackABConversion(testId: string, conversionValue?: number) {
  const variant = getVariant(testId);
  const test = AB_TESTS[testId];

  if (!test) return;

  trackEvent('ab_test_conversion', {
    test_id: testId,
    test_name: test.name,
    variant,
    variant_name: test.variants[variant].name,
    value: conversionValue,
  });
}

/**
 * Hook for using A/B test variants in components
 *
 * @example
 * const variant = useABTest('homepage-cta');
 * return variant === 'A' ? <CTAButton1 /> : <CTAButton2 />;
 */
export function useABTest(testId: string): VariantId {
  if (typeof window === 'undefined') {
    return 'A'; // SSR default
  }

  return getVariant(testId);
}

/**
 * Reset all A/B test assignments (useful for testing)
 */
export function resetABTests() {
  if (typeof window === 'undefined') return;

  Object.keys(AB_TESTS).forEach((testId) => {
    localStorage.removeItem(`${STORAGE_KEY_PREFIX}${testId}`);
  });
}

/**
 * Get all active tests and their assignments
 */
export function getActiveTests(): Array<{
  id: string;
  name: string;
  variant: VariantId;
  variantName: string;
}> {
  return Object.values(AB_TESTS)
    .filter((test) => test.enabled)
    .map((test) => {
      const variant = getVariant(test.id);
      return {
        id: test.id,
        name: test.name,
        variant,
        variantName: test.variants[variant].name,
      };
    });
}
