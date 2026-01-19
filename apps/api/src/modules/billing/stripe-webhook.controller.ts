import { Controller, Headers, Post, Req } from '@nestjs/common';

import { BillingService } from './billing.service.js';

import type { Request } from 'express';

@Controller('stripe')
export class StripeWebhookController {
  constructor(private readonly billingService: BillingService) {}

  @Post('webhook')
  async handleWebhook(@Headers('stripe-signature') signature: string, @Req() req: Request) {
    const payload = Buffer.isBuffer(req.body) ? (req.body as Buffer) : Buffer.from([]);
    await this.billingService.handleStripeWebhook(signature, payload);
    return { received: true };
  }
}
