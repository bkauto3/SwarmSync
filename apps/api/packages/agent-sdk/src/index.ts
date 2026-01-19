import {
  AgentMarketClient,
  createAgentMarketClient,
  type AgentDiscoveryFilters,
  type AgentDiscoveryResponse,
  type AgentSchemaDefinition,
  type Ap2NegotiationRecord,
  type Ap2TransactionRecord,
  type CreateAp2NegotiationRequest,
  type RespondAp2NegotiationRequest,
  type ServiceDeliveryPayload,
} from '@agent-market/sdk';

export interface AgentSDKConfig {
  agentId: string;
  apiKey?: string;
  baseUrl?: string;
}

export interface ServiceRequestOptions {
  targetAgentId: string;
  service: string;
  budget: number;
  requirements?: Record<string, unknown>;
  notes?: string;
}

export interface NegotiationResponseOptions {
  negotiationId: string;
  status: 'ACCEPTED' | 'REJECTED' | 'COUNTERED';
  price?: number;
  estimatedDelivery?: string;
  terms?: Record<string, unknown>;
  notes?: string;
}

export interface DeliveryOptions {
  negotiationId: string;
  result: Record<string, unknown>;
  evidence?: Record<string, unknown>;
  notes?: string;
}

export interface WaitOptions {
  intervalMs?: number;
  timeoutMs?: number;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export class AgentMarketSDK {
  private readonly agentId: string;

  private readonly client: AgentMarketClient;

  private readonly clientOptions: { baseUrl?: string; apiKey?: string };

  constructor(config: AgentSDKConfig) {
    this.agentId = config.agentId;
    this.clientOptions = {
      baseUrl: config.baseUrl,
      apiKey: config.apiKey,
    };
    this.client = createAgentMarketClient(this.clientOptions);
  }

  discover(filters?: AgentDiscoveryFilters): Promise<AgentDiscoveryResponse> {
    return this.client.discoverAgents(filters);
  }

  getAgentSchema(agentId: string): Promise<AgentSchemaDefinition> {
    return this.client.getAgentSchema(agentId);
  }

  requestService(options: ServiceRequestOptions): Promise<Ap2NegotiationRecord> {
    const payload: CreateAp2NegotiationRequest = {
      requesterAgentId: this.agentId,
      responderAgentId: options.targetAgentId,
      requestedService: options.service,
      budget: options.budget,
      requirements: options.requirements,
      notes: options.notes,
    };

    return this.client.initiateAp2Negotiation(payload);
  }

  respondToRequest(options: NegotiationResponseOptions): Promise<Ap2NegotiationRecord> {
    const payload: RespondAp2NegotiationRequest = {
      negotiationId: options.negotiationId,
      responderAgentId: this.agentId,
      status: options.status,
      price: options.price,
      estimatedDelivery: options.estimatedDelivery,
      terms: options.terms,
      notes: options.notes,
    };

    return this.client.respondToAp2Negotiation(payload);
  }

  deliverService(options: DeliveryOptions) {
    const payload: ServiceDeliveryPayload = {
      negotiationId: options.negotiationId,
      responderAgentId: this.agentId,
      result: options.result,
      evidence: options.evidence,
      notes: options.notes,
    };

    return this.client.deliverAp2Service(payload);
  }

  listTransactions(): Promise<Ap2TransactionRecord[]> {
    return this.client.listAp2Transactions(this.agentId);
  }

  listNegotiations(): Promise<Ap2NegotiationRecord[]> {
    return this.client.listAp2Negotiations(this.agentId);
  }

  getNegotiation(id: string): Promise<Ap2NegotiationRecord> {
    return this.client.getAp2Negotiation(id);
  }

  async waitForCompletion(
    negotiationId: string,
    options?: WaitOptions,
  ): Promise<Ap2NegotiationRecord> {
    const interval = options?.intervalMs ?? 2000;
    const timeout = options?.timeoutMs ?? 120000;
    const deadline = Date.now() + timeout;

    while (Date.now() <= deadline) {
      const negotiation = await this.client.getAp2Negotiation(negotiationId);

      if (this.isTerminal(negotiation)) {
        return negotiation;
      }

      await sleep(interval);
    }

    throw new Error(`Timed out waiting for negotiation ${negotiationId}`);
  }

  async waitForSettlement(negotiationId: string, options?: WaitOptions) {
    return this.waitForCompletion(negotiationId, options);
  }

  private isTerminal(negotiation: Ap2NegotiationRecord) {
    const verificationStatus = negotiation.verificationStatus ?? null;
    if (
      verificationStatus === 'VERIFIED' ||
      verificationStatus === 'REJECTED' ||
      verificationStatus === 'DISPUTED'
    ) {
      return true;
    }

    const transactionStatus = negotiation.transaction?.status ?? null;
    if (
      transactionStatus &&
      transactionStatus !== 'PENDING' &&
      transactionStatus !== 'AUTHORIZED'
    ) {
      return true;
    }

    if (negotiation.status === 'DECLINED' || negotiation.status === 'CANCELLED') {
      return true;
    }

    return false;
  }
}
