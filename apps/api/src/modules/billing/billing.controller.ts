import { Body, Controller, Get, Post } from '@nestjs/common';
import { IsInt, IsOptional, IsString, Min } from 'class-validator';

import { BillingService } from './billing.service.js';
import { Public } from '../auth/decorators/public.decorator.js';

class CheckoutRequestDto {
  @IsString()
  planSlug!: string;

  @IsOptional()
  @IsString()
  successUrl?: string;

  @IsOptional()
  @IsString()
  cancelUrl?: string;
}

class TopUpRequestDto {
  @IsInt()
  @Min(1000)
  amountCents!: number;

  @IsOptional()
  @IsString()
  successUrl?: string;

  @IsOptional()
  @IsString()
  cancelUrl?: string;
}

@Controller('billing')
export class BillingController {
  constructor(private readonly billingService: BillingService) {}

  @Get('plans')
  listPlans() {
    return this.billingService.listPlans();
  }

  @Get('subscription')
  getSubscription() {
    return this.billingService.getOrganizationSubscription();
  }

  @Post('subscription/apply')
  applyPlan(@Body() body: CheckoutRequestDto) {
    return this.billingService.applyPlan(body.planSlug);
  }

  @Post('subscription/checkout')
  createCheckout(@Body() body: CheckoutRequestDto) {
    return this.billingService.createCheckoutSession(body.planSlug, body.successUrl, body.cancelUrl);
  }

  @Public()
  @Post('subscription/checkout/public')
  createPublicCheckout(@Body() body: CheckoutRequestDto) {
    return this.billingService.createPublicCheckoutSession(body.planSlug, body.successUrl, body.cancelUrl);
  }

  @Post('topup')
  createTopUp(@Body() body: TopUpRequestDto) {
    return this.billingService.createTopUpSession(body.amountCents, body.successUrl, body.cancelUrl);
  }
}
