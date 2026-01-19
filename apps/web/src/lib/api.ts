import ky from 'ky';

import { AUTH_TOKEN_KEY } from '@/lib/constants';

import type {
  Agent,
  AgentCertificationRecord,
  AgentQualityAnalytics,
  AgentRoiTimeseriesPoint,
  EvaluationResultRecord,
  ServiceAgreementWithVerifications,
} from '@agent-market/sdk';

export type { Agent };

export interface AgentBudgetSnapshot {
  agentId: string;
  walletId: string;
  currency: string;
  monthlyLimit: number;
  remaining: number;
  spentThisPeriod: number;
  approvalMode: string;
  perTransactionLimit: number | null;
  approvalThreshold: number | null;
  autoReload: boolean;
  resetsOn: string;
  updatedAt: string;
}

export interface CreateAgentPayload {
  name: string;
  description: string;
  categories: string[];
  tags: string[];
  pricingModel: string;
  visibility?: 'PUBLIC' | 'PRIVATE' | 'UNLISTED' | 'ORGANIZATION';
  basePriceCents?: number;
  inputSchema?: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
  ap2Endpoint?: string;
  creatorId: string;
}

export interface AgentBudgetPayload {
  monthlyLimit?: number;
  perTransactionLimit?: number | null;
  approvalThreshold?: number | null;
  approvalMode?: string;
  autoReload?: boolean;
}

export interface Ap2NegotiationPayload {
  requesterAgentId: string;
  responderAgentId: string;
  requestedService: string;
  budget: number;
  requirements?: Record<string, unknown>;
  notes?: string;
}

const DEFAULT_PRODUCTION_API_ORIGIN = 'https://swarmsync-api.up.railway.app';

function inferRuntimeApiOrigin() {
  if (typeof window === 'undefined') {
    return undefined;
  }
  const origin = window.location.origin;
  const hostname = window.location.hostname;
  if (
    hostname === 'agent-market.fly.dev' ||
    hostname.endsWith('.agent-market.fly.dev') ||
    hostname.endsWith('agent-market.ai')
  ) {
    return DEFAULT_PRODUCTION_API_ORIGIN;
  }
  if (hostname.endsWith('swarmsync.ai') || hostname.endsWith('swarmsync.netlify.app')) {
    // Use the actual backend API, not api.swarmsync.ai which points to Next.js frontend
    return DEFAULT_PRODUCTION_API_ORIGIN;
  }
  return origin;
}

const envApiUrl =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.API_URL ??
  (process.env.NODE_ENV === 'production' ? DEFAULT_PRODUCTION_API_ORIGIN : undefined) ??
  inferRuntimeApiOrigin();

const API_BASE_URL = envApiUrl?.replace(/\/$/, '') ?? 'http://localhost:4000';

const api = ky.create({
  prefixUrl: API_BASE_URL,
  hooks: {
    beforeRequest: [
      (request) => {
        if (typeof window === 'undefined') {
          return;
        }
        const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
        if (token) {
          request.headers.set('Authorization', `Bearer ${token}`);
        }
      },
    ],
    afterResponse: [
      async (_request, _options, response) => {
        if (response.status === 401 && typeof window !== 'undefined') {
          window.localStorage.removeItem(AUTH_TOKEN_KEY);
          window.dispatchEvent(new CustomEvent('auth:unauthorized'));
        }
      },
    ],
  },
});

// Create a separate API client for public endpoints (no auth header)
const publicApi = ky.create({
  prefixUrl: API_BASE_URL,
});

export interface AuthResponse {
  user: {
    id: string;
    email: string;
    displayName: string;
  };
  accessToken: string;
  expiresIn: number;
}

export interface AgentListFilters {
  search?: string;
  category?: string;
  limit?: number;
  tag?: string;
  verifiedOnly?: boolean;
  creatorId?: string;
  showAll?: string;
  status?: string;
  visibility?: string;
}

export const authApi = {
  login: (email: string, password: string) =>
    api
      .post('auth/login', {
        json: { email, password },
      })
      .json<AuthResponse>(),
  register: (data: { email: string; password: string; displayName: string }) =>
    api
      .post('auth/register', {
        json: data,
      })
      .json<AuthResponse>(),
};

export const agentsApi = {
  list: async (filters?: AgentListFilters): Promise<Agent[]> => {
    try {
      return await api
        .get('agents', {
          cache: 'no-store',
          searchParams: {
            ...(filters?.search ? { search: filters.search } : {}),
            ...(filters?.category ? { category: filters.category } : {}),
            ...(filters?.limit ? { limit: String(filters.limit) } : {}),
            ...(filters?.tag ? { tag: filters.tag } : {}),
            ...(filters?.verifiedOnly ? { verifiedOnly: 'true' } : {}),
            ...(filters?.creatorId ? { creatorId: filters.creatorId } : {}),
            ...(filters?.showAll ? { showAll: filters.showAll } : {}),
            ...(filters?.status ? { status: filters.status } : {}),
            ...(filters?.visibility ? { visibility: filters.visibility } : {}),
          },
        })
        .json<Agent[]>();
    } catch (error) {
      console.error('Agents API error:', error);
      // Return empty array on error instead of throwing
      // This allows the UI to show an empty state rather than crashing
      if (error && typeof error === 'object' && 'response' in error) {
        const httpError = error as { response?: { status?: number } };
        if (httpError.response?.status === 401) {
          // Auth error - user needs to log in
          throw new Error('Authentication required. Please log in.');
        }
        if (httpError.response?.status === 403) {
          // Forbidden - user doesn't have permission
          throw new Error('You do not have permission to view agents.');
        }
        if (httpError.response?.status === 500) {
          // Server error
          throw new Error('Server error. Please try again later.');
        }
      }
      throw error;
    }
  },
  getById: (id: string) => api.get(`agents/${id}`).json<Agent>(),
  create: (payload: CreateAgentPayload) =>
    api
      .post('agents', {
        json: payload,
      })
      .json<Agent>(),
  updateBudget: (agentId: string, payload: AgentBudgetPayload) =>
    api
      .patch(`agents/${agentId}/budget`, {
        json: payload,
      })
      .json<AgentBudgetSnapshot>(),
  getQualityAnalytics: (agentId: string) =>
    api.get(`quality/analytics/agents/${agentId}`).json<AgentQualityAnalytics>(),
  listCertifications: (agentId: string) =>
    api.get(`agents/${agentId}/certifications`).json<AgentCertificationRecord[]>(),
  listEvaluationResults: (agentId: string) =>
    api.get(`agents/${agentId}/evaluations`).json<EvaluationResultRecord[]>(),
  listServiceAgreements: (agentId: string) =>
    api.get(`agents/${agentId}/service-agreements`).json<ServiceAgreementWithVerifications[]>(),
  getQualityTimeseries: (agentId: string, days: number) =>
    api
      .get(`quality/analytics/agents/${agentId}/timeseries`, {
        searchParams: { days: String(days) },
      })
      .json<AgentRoiTimeseriesPoint[]>(),
};

export const ap2Api = {
  requestService: (payload: Ap2NegotiationPayload) =>
    api
      .post('ap2/negotiate', {
        json: payload,
      })
      .json(),
  respondToNegotiation: (payload: {
    negotiationId: string;
    responderAgentId: string;
    status: 'ACCEPTED' | 'REJECTED' | 'COUNTERED';
    price?: number;
    estimatedDelivery?: string;
    terms?: Record<string, unknown>;
    notes?: string;
  }) =>
    api
      .post('ap2/respond', {
        json: payload,
      })
      .json(),
  deliverService: (payload: {
    negotiationId: string;
    responderAgentId: string;
    result?: Record<string, unknown>;
    evidence?: Record<string, unknown>;
    notes?: string;
  }) =>
    api
      .post('ap2/deliver', {
        json: payload,
      })
      .json(),
  getNegotiation: (id: string) => api.get(`ap2/negotiations/${id}`).json(),
};

export const billingApi = {
  changePlan: (planSlug: string) =>
    api
      .post('billing/subscription/apply', {
        json: { planSlug },
      })
      .json(),
  createCheckoutSession: (planSlug: string, successUrl?: string, cancelUrl?: string) =>
    api
      .post('billing/subscription/checkout', {
        json: { planSlug, successUrl, cancelUrl },
      })
      .json<{ checkoutUrl: string | null; subscription?: unknown }>(),
  createPublicCheckoutSession: (planSlug: string, successUrl?: string, cancelUrl?: string) =>
    publicApi
      .post('billing/subscription/checkout/public', {
        json: { planSlug, successUrl, cancelUrl },
      })
      .json<{ checkoutUrl: string | null }>(),
  createTopUpSession: (amountCents: number, successUrl?: string, cancelUrl?: string) =>
    api
      .post('billing/topup', {
        json: { amountCents, successUrl, cancelUrl },
      })
      .json<{ checkoutUrl: string | null }>(),
};

export const walletsApi = {
  getUserWallet: (userId: string) => api.get(`wallets/user/${userId}`).json(),
  getAgentWallet: (agentId: string) => api.get(`wallets/agent/${agentId}`).json(),
  getWallet: (walletId: string) => api.get(`wallets/${walletId}`).json(),
  fundWallet: (walletId: string, amount: number, reference?: string) =>
    api
      .post(`wallets/${walletId}/fund`, {
        json: { amount, reference },
      })
      .json(),
};

export interface TestSuite {
  id: string;
  slug: string;
  name: string;
  description: string;
  category: string;
  recommendedAgentTypes: string[];
  estimatedDurationSec: number;
  approximateCostUsd: number;
  isRecommended: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface TestRun {
  id: string;
  agentId: string;
  suiteId: string;
  userId: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  score: number | null;
  startedAt: string | null;
  completedAt: string | null;
  rawResults: unknown;
  metadata: unknown;
  suite: {
    id: string;
    name: string;
    slug: string;
    category: string;
  };
  agent: {
    id: string;
    name: string;
    slug: string;
  };
  createdAt: string;
  updatedAt: string;
}

export interface TestRunListResponse {
  runs: TestRun[];
  total: number;
}

export interface IndividualTest {
  id: string;
  suiteSlug: string;
  suiteName: string;
  category: string;
}

export interface StartTestRunPayload {
  agentId: string | string[];
  suiteId: string | string[];
  testIds?: string[];
}

export interface StartTestRunResponse {
  runs: Array<{ id: string; agentId: string; suiteId: string }>;
}

export const testingApi = {
  listSuites: (params?: { category?: string; recommended?: boolean }) =>
    api
      .get('api/v1/test-suites', {
        cache: 'no-store',
        searchParams: {
          ...(params?.category ? { category: params.category } : {}),
          ...(params?.recommended !== undefined ? { recommended: String(params.recommended) } : {}),
        },
      })
      .json<TestSuite[]>(),
  getRecommendedSuites: () => api.get('api/v1/test-suites/recommended').json<TestSuite[]>(),
  listIndividualTests: () => api.get('api/v1/test-suites/individual').json<IndividualTest[]>(),
  startRun: (payload: StartTestRunPayload) =>
    api
      .post('api/v1/test-runs', {
        json: payload,
      })
      .json<StartTestRunResponse>(),
  getRun: (runId: string) => api.get(`api/v1/test-runs/${runId}`).json<TestRun>(),
  listRuns: (params?: {
    agentId?: string;
    suiteId?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) =>
    api
      .get('api/v1/test-runs', {
        searchParams: {
          ...(params?.agentId ? { agentId: params.agentId } : {}),
          ...(params?.suiteId ? { suiteId: params.suiteId } : {}),
          ...(params?.status ? { status: params.status } : {}),
          ...(params?.limit ? { limit: String(params.limit) } : {}),
          ...(params?.offset ? { offset: String(params.offset) } : {}),
        },
      })
      .json<TestRunListResponse>(),
  cancelRun: (runId: string) => api.delete(`api/v1/test-runs/${runId}`).json<TestRun>(),
};

export interface ServiceAccount {
  id: string;
  name: string;
  description?: string;
  apiKey?: string; // Only present on creation
  scopes: string[];
  status: 'ACTIVE' | 'DISABLED' | 'REVOKED';
  organizationId?: string;
  agentId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateServiceAccountPayload {
  name: string;
  description?: string;
  scopes?: string[];
  organizationId?: string;
  agentId?: string;
}

export const serviceAccountsApi = {
  list: () => api.get('api/v1/service-accounts').json<ServiceAccount[]>(),
  create: (payload: CreateServiceAccountPayload) =>
    api.post('api/v1/service-accounts', { json: payload }).json<ServiceAccount>(),
  revoke: (id: string) => api.delete(`api/v1/service-accounts/${id}`).json<{ success: boolean }>(),
};

export { API_BASE_URL, api };
