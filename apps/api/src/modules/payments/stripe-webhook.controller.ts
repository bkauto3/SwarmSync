import { Controller, Post, Body, Logger, HttpException, HttpStatus } from '@nestjs/common';

import { StripeConnectService } from './stripe-connect.service.js';

@Controller('webhooks/stripe')
export class StripeWebhookController {
  private readonly logger = new Logger(StripeWebhookController.name);

  constructor(private stripeConnectService: StripeConnectService) {}

  @Post('payout-updated')
  async handlePayoutUpdated(
    @Body() event: Record<string, unknown>,
  ) {
    try {
      if (event.type === 'payout.updated' || event.type === 'payout.paid') {
        const payout = (event.data as Record<string, unknown>)?.object as Record<string, unknown>;

        if (payout.id && payout.status) {
          await this.stripeConnectService.handlePayoutWebhook(
            String(payout.id),
            String(payout.status),
          );

          this.logger.log(`Payout ${payout.id} status: ${payout.status}`);
        }
      }

      return { received: true };
    } catch (err) {
      this.logger.error(`Webhook error: ${err instanceof Error ? err.message : String(err)}`);
      throw new HttpException(
        'Webhook processing failed',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }

  @Post('account-updated')
  async handleAccountUpdated(
    @Body() event: Record<string, unknown>,
  ) {
    try {
      if (event.type === 'account.updated') {
        const account = (event.data as Record<string, unknown>)?.object as Record<string, unknown>;

        this.logger.log(
          `Account ${account.id} updated. Charges: ${account.charges_enabled}, Payouts: ${account.payouts_enabled}`,
        );
      }

      return { received: true };
    } catch (err) {
      this.logger.error(`Account webhook error: ${err instanceof Error ? err.message : String(err)}`);
      throw new HttpException(
        'Webhook processing failed',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}
