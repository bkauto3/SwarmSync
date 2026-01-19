import { billingPlanConfigs } from '@agent-market/config';
import { Injectable, Logger, NotFoundException, BadRequestException } from '@nestjs/common';
import { InvoiceStatus, Prisma, SubscriptionStatus } from '@prisma/client';
import Stripe from 'stripe';

import { PrismaService } from '../database/prisma.service.js';
import { WalletsService } from '../payments/wallets.service.js';

const DEFAULT_ORG_SLUG = process.env.DEFAULT_ORG_SLUG ?? 'genesis';
const STRIPE_WEB_URL = process.env.STRIPE_WEB_URL ?? process.env.WEB_URL ?? 'http://localhost:3000';
type BillingPlanConfig = (typeof billingPlanConfigs)[number] & { stripePriceId?: string };
const planConfigList = billingPlanConfigs as BillingPlanConfig[];

@Injectable()
export class BillingService {
  private readonly stripe: Stripe | null;
  private readonly webhookSecret?: string;
  private readonly logger = new Logger(BillingService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly walletsService: WalletsService,
  ) {
    const secret = process.env.STRIPE_SECRET_KEY;
    this.stripe = secret ? new Stripe(secret, { apiVersion: '2025-10-29.clover' }) : null;
    this.webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  }

  async listPlans() {
    await this.ensurePlansSeeded();
    return this.prisma.billingPlan.findMany({
      orderBy: { priceCents: 'asc' },
    });
  }

  async getOrganizationSubscription() {
    const organization = await this.getDefaultOrganization();
    const subscription = await this.prisma.organizationSubscription.findUnique({
      where: { organizationId: organization.id },
      include: { plan: true },
    });

    if (!subscription) {
      return null;
    }

    return subscription;
  }

  async applyPlan(planSlug: string) {
    await this.ensurePlansSeeded();
    const plan = await this.prisma.billingPlan.findUnique({ where: { slug: planSlug } });
    if (!plan) {
      throw new NotFoundException('Plan not found');
    }

    const organization = await this.getDefaultOrganization();
    const now = new Date();
    const nextMonth = new Date(now);
    nextMonth.setMonth(nextMonth.getMonth() + 1);

    return this.prisma.organizationSubscription.upsert({
      where: { organizationId: organization.id },
      update: {
        planSlug: plan.slug,
        status: 'ACTIVE',
        currentPeriodStart: now,
        currentPeriodEnd: nextMonth,
        creditAllowance: plan.monthlyCredits,
        creditUsed: 0,
      },
      create: {
        organizationId: organization.id,
        planSlug: plan.slug,
        status: 'ACTIVE',
        currentPeriodStart: now,
        currentPeriodEnd: nextMonth,
        creditAllowance: plan.monthlyCredits,
      },
      include: { plan: true },
    });
  }

  async createCheckoutSession(planSlug: string, successUrl?: string, cancelUrl?: string) {
    await this.ensurePlansSeeded();
    const plan = await this.prisma.billingPlan.findUnique({ where: { slug: planSlug } });
    if (!plan) {
      throw new NotFoundException('Plan not found');
    }

    const planConfig = this.findPlanConfigBySlug(plan.slug);

    if (plan.priceCents === 0) {
      const subscription = await this.applyPlan(planSlug);
      return {
        checkoutUrl: null,
        subscription,
      };
    }

    if (!this.stripe) {
      throw new Error('Stripe is not configured');
    }

    const organization = await this.getDefaultOrganization();
    const stripeCustomerId = await this.ensureStripeCustomer(organization.id);

    const stripePriceId = planConfig?.stripePriceId;
    if (!stripePriceId) {
      throw new Error(`Stripe price ID missing for plan ${plan.slug}`);
    }

    const session = await this.stripe.checkout.sessions.create({
      mode: 'subscription',
      customer: stripeCustomerId,
      success_url: successUrl ?? `${STRIPE_WEB_URL}/billing?status=success`,
      cancel_url: cancelUrl ?? `${STRIPE_WEB_URL}/billing?status=cancel`,
      line_items: [
        {
          price: stripePriceId,
          quantity: 1,
        },
      ],
      metadata: {
        organizationId: organization.id,
        planSlug: plan.slug,
      },
      subscription_data: {
        metadata: {
          organizationId: organization.id,
          planSlug: plan.slug,
        },
      },
    });

    return { checkoutUrl: session.url };
  }

  async createPublicCheckoutSession(planSlug: string, successUrl?: string, cancelUrl?: string) {
    await this.ensurePlansSeeded();
    const plan = await this.prisma.billingPlan.findUnique({ where: { slug: planSlug } });
    if (!plan) {
      throw new NotFoundException('Plan not found');
    }

    const planConfig = this.findPlanConfigBySlug(plan.slug);

    if (plan.priceCents === 0) {
      // For free plans, redirect to registration
      return {
        checkoutUrl: `${STRIPE_WEB_URL}/register?plan=${planSlug}`,
      };
    }

    if (!this.stripe) {
      throw new Error('Stripe is not configured');
    }

    const stripePriceId = planConfig?.stripePriceId;
    if (!stripePriceId) {
      throw new Error(`Stripe price ID missing for plan ${plan.slug}`);
    }

    // Create checkout session without requiring authentication
    // User will provide email during checkout, and we'll create account after payment
    const session = await this.stripe.checkout.sessions.create({
      mode: 'subscription',
      customer_email: undefined, // Let Stripe collect email
      success_url: successUrl ?? `${STRIPE_WEB_URL}/register?status=success&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: cancelUrl ?? `${STRIPE_WEB_URL}/pricing?status=cancel`,
      line_items: [
        {
          price: stripePriceId,
          quantity: 1,
        },
      ],
      metadata: {
        planSlug: plan.slug,
        isPublicCheckout: 'true',
      },
      subscription_data: {
        metadata: {
          planSlug: plan.slug,
        },
      },
      allow_promotion_codes: true,
      billing_address_collection: 'auto',
    });

    return { checkoutUrl: session.url };
  }

  async handleStripeWebhook(signature: string | undefined, payload: Buffer) {
    if (!this.stripe || !this.webhookSecret) {
      this.logger.warn('Stripe webhook received but Stripe is not configured.');
      return;
    }

    if (!signature) {
      throw new BadRequestException('Missing Stripe signature header');
    }

    let event: Stripe.Event;
    try {
      event = this.stripe.webhooks.constructEvent(payload, signature, this.webhookSecret);
    } catch (error) {
      this.logger.error('Stripe webhook signature verification failed', error as Error);
      throw new BadRequestException('Invalid Stripe signature');
    }

    switch (event.type) {
      case 'checkout.session.completed':
        await this.handleCheckoutCompleted(event.data.object as Stripe.Checkout.Session);
        break;
      case 'customer.subscription.created':
      case 'customer.subscription.updated':
      case 'customer.subscription.deleted':
        await this.syncSubscriptionFromStripe(event.data.object as Stripe.Subscription);
        break;
      case 'invoice.payment_succeeded':
      case 'invoice.payment_failed':
        await this.recordInvoice(event.data.object as Stripe.Invoice);
        break;
      default:
        this.logger.debug(`Unhandled Stripe event type ${event.type}`);
    }

    return { received: true };
  }

  async createTopUpSession(amountCents: number, successUrl?: string, cancelUrl?: string) {
    if (!this.stripe) {
      throw new Error('Stripe is not configured');
    }

    const organization = await this.getDefaultOrganization();
    const stripeCustomerId = await this.ensureStripeCustomer(organization.id);

    const session = await this.stripe.checkout.sessions.create({
      mode: 'payment',
      customer: stripeCustomerId,
      success_url: successUrl ?? `${STRIPE_WEB_URL}/billing?status=topup-success`,
      cancel_url: cancelUrl ?? `${STRIPE_WEB_URL}/billing?status=topup-cancel`,
      line_items: [
        {
          price_data: {
            currency: 'usd',
            product_data: {
              name: 'Marketplace credit top-up',
            },
            unit_amount: amountCents,
          },
          quantity: 1,
        },
      ],
      metadata: {
        organizationId: organization.id,
        topUpAmountCents: String(amountCents),
      },
    });

    return { checkoutUrl: session.url };
  }

  private async ensureStripeCustomer(orgId: string) {
    const organization = await this.prisma.organization.findUnique({
      where: { id: orgId },
    });
    if (!organization) {
      throw new NotFoundException('Organization not found');
    }

    if (organization.stripeCustomerId) {
      return organization.stripeCustomerId;
    }

    if (!this.stripe) {
      throw new Error('Stripe not configured');
    }

    const customer = await this.stripe.customers.create({
      name: organization.name,
      metadata: {
        organizationId: organization.id,
      },
    });

    await this.prisma.organization.update({
      where: { id: orgId },
      data: {
        stripeCustomerId: customer.id,
      },
    });

    return customer.id;
  }

  private async getDefaultOrganization() {
    let organization = await this.prisma.organization.findUnique({
      where: { slug: DEFAULT_ORG_SLUG },
    });

    if (!organization) {
      organization = await this.prisma.organization.findFirst({
        orderBy: { createdAt: 'asc' },
      });
    }

    // Auto-create the default organization if none exists
    if (!organization) {
      this.logger.log(`Creating default organization with slug: ${DEFAULT_ORG_SLUG}`);
      organization = await this.prisma.organization.create({
        data: {
          slug: DEFAULT_ORG_SLUG,
          name: 'Genesis Organization',
        },
      });
    }

    return organization;
  }

  private async ensurePlansSeeded() {
    await Promise.all(
      billingPlanConfigs.map((plan) =>
        this.prisma.billingPlan.upsert({
          where: { slug: plan.slug },
          update: {
            name: plan.name,
            priceCents: plan.priceCents,
            seats: plan.seats,
            agentLimit: plan.agentLimit,
            workflowLimit: plan.workflowLimit,
            monthlyCredits: plan.monthlyCredits,
            takeRateBasisPoints: plan.takeRateBasisPoints,
            features: plan.features,
          },
          create: {
            id: plan.slug.toUpperCase(),
            slug: plan.slug,
            name: plan.name,
            priceCents: plan.priceCents,
            seats: plan.seats,
            agentLimit: plan.agentLimit,
            workflowLimit: plan.workflowLimit,
            monthlyCredits: plan.monthlyCredits,
            takeRateBasisPoints: plan.takeRateBasisPoints,
            features: plan.features,
          },
        }),
      ),
    );
  }

  private async handleCheckoutCompleted(session: Stripe.Checkout.Session) {
    const subscriptionId =
      typeof session.subscription === 'string'
        ? session.subscription
        : session.subscription?.id ?? null;
    const planSlug = session.metadata?.planSlug;
    const organizationId = session.metadata?.organizationId;

    if (subscriptionId && this.stripe) {
      const subscription = await this.stripe.subscriptions.retrieve(subscriptionId);
      await this.syncSubscriptionFromStripe(subscription);
    } else if (planSlug && organizationId) {
      await this.applyPlan(planSlug);
    }

    const topUpAmount = session.metadata?.topUpAmountCents;
    if (topUpAmount && organizationId) {
      await this.applyTopUp(organizationId, Number(topUpAmount), session.id);
    }
  }

  private async syncSubscriptionFromStripe(stripeSubscription: Stripe.Subscription) {
    const organization = await this.resolveOrganizationFromStripeSubscription(stripeSubscription);
    if (!organization) {
      this.logger.warn('Unable to resolve organization for subscription', {
        subscriptionId: stripeSubscription.id,
      });
      return;
    }

    const price = stripeSubscription.items.data[0]?.price;
    const priceId =
      typeof price === 'string' ? price : price?.id ?? stripeSubscription.metadata?.priceId;

    if (!priceId) {
      this.logger.warn('Subscription missing price data', { subscriptionId: stripeSubscription.id });
      return;
    }

    const configMatch = this.findPlanConfigByPriceId(priceId);
    if (!configMatch) {
      this.logger.warn('No billing plan matches Stripe price', { priceId });
      return;
    }

    const plan = await this.prisma.billingPlan.findUnique({
      where: { slug: configMatch.slug },
    });

    if (!plan) {
      this.logger.warn('Configured plan missing in database', { slug: configMatch.slug });
      return;
    }

    const {
      current_period_start: currentPeriodStart,
      current_period_end: currentPeriodEnd,
    } = stripeSubscription as Stripe.Subscription & {
      current_period_start: number;
      current_period_end: number;
    };
    const start = new Date(currentPeriodStart * 1000);
    const end = new Date(currentPeriodEnd * 1000);

    await this.prisma.organizationSubscription.upsert({
      where: { organizationId: organization.id },
      update: {
        planSlug: plan.slug,
        status: this.mapSubscriptionStatus(stripeSubscription.status),
        currentPeriodStart: start,
        currentPeriodEnd: end,
        stripeSubscriptionId: stripeSubscription.id,
        creditAllowance: plan.monthlyCredits,
      },
      create: {
        organizationId: organization.id,
        planSlug: plan.slug,
        status: this.mapSubscriptionStatus(stripeSubscription.status),
        currentPeriodStart: start,
        currentPeriodEnd: end,
        stripeSubscriptionId: stripeSubscription.id,
        creditAllowance: plan.monthlyCredits,
      },
    });

    if (
      typeof stripeSubscription.customer === 'string' &&
      organization.stripeCustomerId !== stripeSubscription.customer
    ) {
      await this.prisma.organization.update({
        where: { id: organization.id },
        data: { stripeCustomerId: stripeSubscription.customer },
      });
    }
  }

  private async recordInvoice(invoice: Stripe.Invoice) {
    const subscriptionId = this.extractSubscriptionId(invoice);
    if (!subscriptionId) {
      return;
    }

    const subscription = await this.prisma.organizationSubscription.findFirst({
      where: { stripeSubscriptionId: subscriptionId },
    });
    if (!subscription) {
      this.logger.warn('Invoice for unknown subscription', { subscriptionId });
      return;
    }

    const status = invoice.status === 'paid' ? InvoiceStatus.PAID : InvoiceStatus.OPEN;
    const paidAt = invoice.status_transitions?.paid_at
      ? new Date(invoice.status_transitions.paid_at * 1000)
      : null;
    const baseData = {
      subscriptionId: subscription.id,
      amountCents: invoice.amount_due ?? invoice.amount_paid ?? 0,
      issuedAt: new Date(invoice.created * 1000),
      dueAt: invoice.due_date ? new Date(invoice.due_date * 1000) : new Date(),
      status,
      lineItems: (invoice.lines?.data ?? []) as unknown as Prisma.InputJsonValue,
      stripeInvoiceId: invoice.id,
      currency: invoice.currency?.toUpperCase() ?? 'USD',
      paidAt,
    };

    const existing = await this.prisma.invoice.findFirst({
      where: { stripeInvoiceId: invoice.id },
    });

    if (existing) {
      await this.prisma.invoice.update({
        where: { id: existing.id },
        data: {
          amountCents: baseData.amountCents,
          status,
          paidAt,
          lineItems: baseData.lineItems,
          currency: baseData.currency,
          dueAt: baseData.dueAt,
        },
      });
      return;
    }

    await this.prisma.invoice.create({ data: baseData });
  }

  private async resolveOrganizationFromStripeSubscription(
    subscription: Stripe.Subscription,
  ) {
    const metadataOrgId = subscription.metadata?.organizationId;
    if (metadataOrgId) {
      const org = await this.prisma.organization.findUnique({
        where: { id: metadataOrgId },
      });
      if (org) {
        return org;
      }
    }

    if (typeof subscription.customer === 'string') {
      return this.prisma.organization.findFirst({
        where: { stripeCustomerId: subscription.customer },
      });
    }

    return null;
  }

  private findPlanConfigBySlug(slug: string): BillingPlanConfig | undefined {
    return planConfigList.find((plan) => plan.slug === slug);
  }

  private findPlanConfigByPriceId(priceId: string): BillingPlanConfig | undefined {
    return planConfigList.find(
      (plan) => plan.stripePriceId && plan.stripePriceId === priceId,
    );
  }

  private mapSubscriptionStatus(status: Stripe.Subscription.Status): SubscriptionStatus {
    switch (status) {
      case 'past_due':
      case 'unpaid':
        return SubscriptionStatus.PAST_DUE;
      case 'canceled':
        return SubscriptionStatus.CANCELED;
      case 'trialing':
        return SubscriptionStatus.TRIALING;
      default:
        return SubscriptionStatus.ACTIVE;
    }
  }

  private async applyTopUp(organizationId: string, amountCents: number, reference: string) {
    if (!Number.isFinite(amountCents) || amountCents <= 0) {
      return;
    }

    const wallet = await this.walletsService.ensureOrganizationWallet(organizationId);
    await this.walletsService.fundWallet(wallet.id, {
      amount: amountCents / 100,
      reference: `stripe-topup:${reference}`,
    });
  }

  private extractSubscriptionId(invoice: Stripe.Invoice) {
    const raw =
      (invoice as Stripe.Invoice & {
        subscription?: string | Stripe.Subscription;
      }).subscription ?? null;
    if (!raw) {
      return null;
    }
    if (typeof raw === 'string') {
      return raw;
    }
    return raw.id ?? null;
  }
}
