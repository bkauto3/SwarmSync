import { createHmac } from 'node:crypto';

import { Controller, Headers, HttpCode, HttpStatus, Logger, Post, Req, UnauthorizedException } from '@nestjs/common';

import { X402Service } from './x402.service.js';

import type { Request } from 'express';

interface X402WebhookEvent {
  type: 'payment.confirmed' | 'payment.failed' | 'payment.pending';
  transaction: {
    txHash: string;
    agentId?: string;
    buyerAddress: string;
    sellerAddress: string;
    amount: number;
    currency: string;
    network: string;
    status: 'PENDING' | 'CONFIRMED' | 'FAILED';
    confirmedAt?: string;
  };
  timestamp: number;
}

@Controller('webhooks/x402')
export class X402WebhookController {
  private readonly logger = new Logger(X402WebhookController.name);
  private readonly webhookSecret: string | undefined;

  constructor(private readonly x402Service: X402Service) {
    this.webhookSecret = process.env.AP2_WEBHOOK_SECRET;
  }

  @Post()
  @HttpCode(HttpStatus.OK)
  async handleWebhook(
    @Headers('x-webhook-signature') signature: string | undefined,
    @Req() req: Request & { rawBody?: string },
  ) {
    if (!this.webhookSecret) {
      this.logger.warn('X402 webhook received but AP2_WEBHOOK_SECRET is not configured.');
      throw new UnauthorizedException('Webhook secret not configured');
    }

    // Get raw body for signature verification (preserved by express.json verify option)
    const rawBody = req.rawBody || JSON.stringify(req.body);
    const body = typeof req.body === 'object' ? (req.body as X402WebhookEvent) : (JSON.parse(rawBody) as X402WebhookEvent);

    // Verify webhook signature
    if (signature) {
      const isValid = this.verifySignature(rawBody, signature);
      if (!isValid) {
        this.logger.error('X402 webhook signature verification failed');
        throw new UnauthorizedException('Invalid webhook signature');
      }
    } else if (process.env.AP2_REQUIRE_AUTH === 'true') {
      this.logger.error('X402 webhook missing signature header');
      throw new UnauthorizedException('Missing webhook signature');
    }

    try {
      await this.x402Service.handleWebhookEvent(body);
      return { received: true };
    } catch (error) {
      this.logger.error(
        `X402 webhook processing failed: ${error instanceof Error ? error.message : String(error)}`,
      );
      throw error;
    }
  }

  private verifySignature(payload: string, signature: string): boolean {
    if (!this.webhookSecret) {
      return false;
    }

    try {
      const hmac = createHmac('sha256', this.webhookSecret);
      const computedSignature = hmac.update(payload).digest('hex');
      const expectedSignature = `sha256=${computedSignature}`;

      // Use constant-time comparison to prevent timing attacks
      return this.constantTimeEqual(signature, expectedSignature);
    } catch (error) {
      this.logger.error(`Signature verification error: ${error instanceof Error ? error.message : String(error)}`);
      return false;
    }
  }

  private constantTimeEqual(a: string, b: string): boolean {
    if (a.length !== b.length) {
      return false;
    }

    let result = 0;
    for (let i = 0; i < a.length; i++) {
      result |= a.charCodeAt(i) ^ b.charCodeAt(i);
    }

    return result === 0;
  }
}

