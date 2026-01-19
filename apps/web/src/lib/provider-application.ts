export type ApplicationStatus = 'submitted' | 'approved' | 'rejected' | 'live' | 'paid';

export type ProviderLifecycleEvent =
  | 'agentSubmitted'
  | 'agentApproved'
  | 'agentRejected'
  | 'agentFirstHire'
  | 'agentPayout';

export type NotificationDetails = {
  feedback?: string;
  jobName?: string;
  amount?: string;
};

export type ProviderApplication = {
  id: string;
  name: string;
  email: string;
  agentName: string;
  agentDescription: string;
  category: string;
  pricingModel: string;
  endpointType: string;
  docsLink?: string;
  apiEndpoint?: string;
  pricingTiers: { title: string; price: string; description?: string }[];
  capabilityTags: string[];
  sampleOutputs: string[];
  status: ApplicationStatus;
  createdAt: string;
  updatedAt?: string;
  twitter?: string;
  notes?: string;
};

export function trendify(pricingModel: string) {
  const normalized = pricingModel.toLowerCase();
  if (normalized.includes('subscription')) return 'Monthly Access';
  if (normalized.includes('per-task')) return 'Per Task';
  return 'Custom Tier';
}
