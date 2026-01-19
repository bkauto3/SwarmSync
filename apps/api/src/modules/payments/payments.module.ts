import { Module } from '@nestjs/common';

import { Ap2Controller } from './ap2.controller.js';
import { Ap2Service } from './ap2.service.js';
import { PayoutsController } from './payouts.controller.js';
import { StripeConnectService } from './stripe-connect.service.js';
import { StripeWebhookController } from './stripe-webhook.controller.js';
import { WalletsController } from './wallets.controller.js';
import { WalletsService } from './wallets.service.js';
import { AuthModule } from '../auth/auth.module.js';

@Module({
  imports: [AuthModule],
  controllers: [WalletsController, Ap2Controller, PayoutsController, StripeWebhookController],
  providers: [WalletsService, Ap2Service, StripeConnectService],
  exports: [WalletsService, Ap2Service, StripeConnectService],
})
export class PaymentsModule {}
