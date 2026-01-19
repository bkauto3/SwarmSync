import { Injectable } from '@nestjs/common';
import { tasks } from '@trigger.dev/sdk/v3';

@Injectable()
export class TriggerService {
    private readonly enabled: boolean;

    constructor() {
        this.enabled = !!process.env.TRIGGER_SECRET_KEY;

        if (this.enabled) {
            console.log('[TriggerService] Trigger.dev integration enabled');
        } else {
            console.warn('[TriggerService] TRIGGER_SECRET_KEY not found. Background tasks disabled.');
        }
    }

    async triggerAgentVerification(agentId: string, ap2Endpoint?: string, inputSchema?: unknown, outputSchema?: unknown) {
        if (!this.enabled) {
            console.warn('[TriggerService] Skipping verification trigger - service disabled');
            return null;
        }

        try {
            const handle = await tasks.trigger('verify-agent', {
                agentId,
                ap2Endpoint,
                inputSchema,
                outputSchema,
            });

            console.log(`[TriggerService] Verification triggered for agent ${agentId}. Handle: ${handle.id}`);
            return handle;
        } catch (error) {
            console.error('[TriggerService] Failed to trigger verification:', error);
            return null;
        }
    }
}
