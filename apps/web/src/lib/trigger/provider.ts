import { configure, tasks } from '@trigger.dev/sdk/v3';
import type {
  NotificationDetails,
  ProviderApplication,
  ProviderLifecycleEvent,
} from '@/lib/provider-application';

const accessToken =
  process.env.TRIGGER_DEV_ACCESS_TOKEN ?? process.env.TRIGGER_SECRET_KEY;
const baseURL = process.env.TRIGGER_DEV_API_URL ?? 'https://api.trigger.dev';
const providerTaskId =
  process.env.TRIGGER_DEV_PROVIDER_TASK_ID ?? 'provider-lifecycle';

let configured = false;

function ensureConfigured() {
  if (configured || !accessToken) {
    return;
  }

  configure({
    accessToken,
    baseURL,
  });

  configured = true;
}

export async function triggerProviderLifecycleEvent(
  application: ProviderApplication,
  event: ProviderLifecycleEvent,
  details: NotificationDetails = {}
) {
  if (!accessToken) {
    return null;
  }

  ensureConfigured();

  try {
    return await tasks.trigger(providerTaskId, {
      event,
      details,
      application,
      triggeredAt: new Date().toISOString(),
    }, {
      tags: ['provider', `event:${event}`],
      metadata: {
        agent: application.agentName,
        category: application.category,
      },
    });
  } catch (error) {
    console.error('[Trigger.dev] failed to trigger provider lifecycle task', error);
    return null;
  }
}
