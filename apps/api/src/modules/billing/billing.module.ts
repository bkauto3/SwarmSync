import { Module } from '@nestjs/common';

import { BillingController } from './billing.controller.js';
import { BillingService } from './billing.service.js';
import { StripeWebhookController } from './stripe-webhook.controller.js';
import { DatabaseModule } from '../database/database.module.js';
import { PaymentsModule } from '../payments/payments.module.js';

@Module({
  imports: [DatabaseModule, PaymentsModule],
  controllers: [BillingController, StripeWebhookController],
  providers: [BillingService],
  exports: [BillingService],
})
export class BillingModule {}
