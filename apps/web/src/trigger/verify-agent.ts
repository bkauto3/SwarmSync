import { task } from "@trigger.dev/sdk/v3";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

export const verifyAgentTask = task({
    id: "verify-agent",
    // Set a reasonable timeout for verification
    maxDuration: 300,
    run: async (payload: { agentId: string; ap2Endpoint?: string; inputSchema?: unknown; outputSchema?: unknown }) => {
        const { agentId, ap2Endpoint, inputSchema } = payload;

        console.log(`Starting verification for Agent ${agentId} at ${ap2Endpoint}`);

        let verificationStatus: 'VERIFIED' | 'REJECTED' = 'VERIFIED';
        let notes: string[] = [];

        // 1. Check Reachability
        if (!ap2Endpoint) {
            verificationStatus = 'REJECTED';
            notes.push("Missing AP2 Endpoint.");
        } else {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

                // Try HEAD first, fall back to GET
                let response = await fetch(ap2Endpoint, { method: 'HEAD', signal: controller.signal });
                if (!response.ok && response.status !== 405) {
                    // If HEAD fails (and not just method not allowed), try GET
                    response = await fetch(ap2Endpoint, { method: 'GET', signal: controller.signal });
                }

                clearTimeout(timeoutId);

                if (!response.ok) {
                    verificationStatus = 'REJECTED';
                    notes.push(`Endpoint unreachable. Status: ${response.status}`);
                }
            } catch (error: unknown) {
                const errorMessage = error instanceof Error ? error.message : 'Unknown error';
                verificationStatus = 'REJECTED';
                notes.push(`Endpoint connection failed: ${errorMessage}`);
            }
        }

        // 2. Check Schema Validity (Basic)
        if (inputSchema) {
            // Just checking if it looks like a JSON schema object
            if (typeof inputSchema !== 'object' || Array.isArray(inputSchema)) {
                verificationStatus = 'REJECTED';
                notes.push("Input Schema must be a valid JSON object.");
            }
        }

        // 3. Update Status
        console.log(`Verification completed. Status: ${verificationStatus}`);

        await prisma.agent.update({
            where: { id: agentId },
            data: {
                verificationStatus: verificationStatus,
                // If verified, also approve the agent so it goes live
                status: verificationStatus === 'VERIFIED' ? 'APPROVED' : 'PENDING'
            }
        });

        // 4. Log Review
        await prisma.agentReview.create({
            data: {
                agentId: agentId,
                reviewerId: 'system-verifier', // Represents autonomous system
                status: verificationStatus === 'VERIFIED' ? 'APPROVED' : 'NEEDS_WORK',
                notes: notes.length > 0 ? notes.join(" | ") : "Autonomous verification passed.",
            }
        });

        return {
            status: verificationStatus,
            notes
        };
    },
});
