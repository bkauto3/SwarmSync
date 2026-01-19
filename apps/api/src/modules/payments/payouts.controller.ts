import { Controller, Post, Get, Body, Param } from '@nestjs/common';

import { StripeConnectService } from './stripe-connect.service.js';

@Controller('payouts')
export class PayoutsController {
  constructor(private readonly stripeConnectService: StripeConnectService) {}

  @Post('setup')
  async setupConnectedAccount(
    @Body() dto: { agentId: string; email: string },
  ) {
    return this.stripeConnectService.createConnectedAccount(
      dto.agentId,
      dto.email,
    );
  }

  @Get('account-status/:agentId')
  async getAccountStatus(@Param('agentId') agentId: string) {
    return this.stripeConnectService.getAccountStatus(agentId);
  }

  @Post('request')
  async requestPayout(@Body() dto: { agentId: string; amountCents: number }) {
    return this.stripeConnectService.requestPayout(dto.agentId, dto.amountCents);
  }

  @Get('history/:agentId')
  async getPayoutHistory(@Param('agentId') agentId: string) {
    return this.stripeConnectService.getPayoutHistory(agentId);
  }

  @Post('org/setup')
  async setupOrgAccount(@Body() dto: { organizationSlug: string; email: string }) {
    return this.stripeConnectService.createOrgConnectedAccount(dto.organizationSlug, dto.email);
  }

  @Get('org/account-status/:slug')
  async getOrgAccountStatus(@Param('slug') slug: string) {
    return this.stripeConnectService.getOrgAccountStatus(slug);
  }

  @Post('org/request')
  async requestOrgPayout(@Body() dto: { organizationSlug: string; amountCents: number }) {
    return this.stripeConnectService.requestOrgPayout(dto.organizationSlug, dto.amountCents);
  }

  @Get('org/history/:slug')
  async getOrgPayoutHistory(@Param('slug') slug: string) {
    return this.stripeConnectService.getOrgPayoutHistory(slug);
  }
}

