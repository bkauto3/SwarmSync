import { Injectable, BadRequestException, InternalServerErrorException, Logger } from '@nestjs/common';
import Stripe from 'stripe';

import { WalletsService } from './wallets.service.js';
import { PrismaService } from '../database/prisma.service.js';

@Injectable()
export class StripeConnectService {
  private stripe!: Stripe;
  private logger = new Logger(StripeConnectService.name);

  constructor(
    private prisma: PrismaService,
    private walletsService: WalletsService,
  ) {
    const apiKey = process.env.STRIPE_SECRET_KEY;
    if (!apiKey) {
      this.logger.warn('STRIPE_SECRET_KEY not configured');
      return;
    }
    
    this.stripe = new Stripe(apiKey);
  }

  /**
   * Create a Stripe connected account for an agent
   */
  async createConnectedAccount(agentId: string, email: string) {
    if (!this.stripe) {
      throw new InternalServerErrorException('Stripe not configured');
    }

    try {
      const account = await this.stripe.accounts.create({
        type: 'express' as unknown as 'standard' | 'express' | 'custom',
        email: email,
        country: 'US',
        metadata: { agentId },
      });

      // Store Stripe account ID in wallet's stripeAccountId field
      const agent = await this.prisma.agent.findUnique({
        where: { id: agentId },
        include: { wallets: { take: 1 } },
      });

      if (agent?.wallets?.[0]) {
        await this.prisma.wallet.update({
          where: { id: agent.wallets[0].id },
          data: { stripeAccountId: account.id },
        });
      }

      const accountLink = await this.stripe.accountLinks.create({
        account: account.id,
        type: 'account_onboarding' as unknown as 'account_onboarding' | 'account_update',
        return_url: `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/wallet`,
        refresh_url: `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/wallet`,
      });

      this.logger.log(`Created Stripe account ${account.id} for agent ${agentId}`);

      return {
        accountId: account.id,
        onboardingUrl: accountLink.url,
        isReady: account.charges_enabled && account.payouts_enabled,
      };
    } catch (error) {
      this.logger.error('Failed to create Stripe account', error);
      throw new InternalServerErrorException('Failed to create Stripe account');
    }
  }

  async createOrgConnectedAccount(slug: string, email: string) {
    if (!this.stripe) {
      throw new InternalServerErrorException('Stripe not configured');
    }

    try {
      const org = await this.prisma.organization.findUnique({ where: { slug } });
      if (!org) {
        throw new BadRequestException('Organization not found');
      }

      const wallet = await this.walletsService.ensureOrganizationWalletBySlug(slug);

      const account = await this.stripe.accounts.create({
        type: 'express' as unknown as 'standard' | 'express' | 'custom',
        email,
        country: 'US',
        metadata: { organizationId: org.id, organizationSlug: slug },
      });

      await this.prisma.wallet.update({
        where: { id: wallet.id },
        data: { stripeAccountId: account.id },
      });

      const accountLink = await this.stripe.accountLinks.create({
        account: account.id,
        type: 'account_onboarding' as unknown as 'account_onboarding' | 'account_update',
        return_url: `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/wallet`,
        refresh_url: `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/wallet`,
      });

      this.logger.log(`Created Stripe account ${account.id} for org ${slug}`);

      return {
        accountId: account.id,
        onboardingUrl: accountLink.url,
        isReady: account.charges_enabled && account.payouts_enabled,
      };
    } catch (error) {
      this.logger.error('Failed to create org Stripe account', error);
      throw new InternalServerErrorException('Failed to create org Stripe account');
    }
  }

  /**
   * Get Stripe account status for an agent
   */
  async getAccountStatus(agentId: string) {
    if (!this.stripe) {
      return { isConnected: false, message: 'Stripe not configured' };
    }

    try {
      const agent = await this.prisma.agent.findUnique({
        where: { id: agentId },
        include: { wallets: { take: 1 } },
      });

      const accountId = agent?.wallets?.[0]?.stripeAccountId;
      if (!accountId) {
        return { isConnected: false, message: 'No Stripe account connected' };
      }

      const account = await this.stripe.accounts.retrieve(accountId);

      return {
        accountId: account.id,
        isConnected: true,
        isChargesEnabled: account.charges_enabled,
        isPayoutsEnabled: account.payouts_enabled,
        isReady: account.charges_enabled && account.payouts_enabled,
        country: account.country,
        email: account.email,
      };
    } catch (error) {
      this.logger.error('Failed to get account status', error);
      return { isConnected: false, message: 'Failed to check account status' };
    }
  }

  /**
   * Request a payout (simplified - just returns success)
   */
  async requestPayout(agentId: string, amountCents: number) {
    try {
      const agent = await this.prisma.agent.findUnique({
        where: { id: agentId },
        include: { wallets: { take: 1 } },
      });

      if (!agent?.wallets?.[0]) {
        throw new BadRequestException('Agent has no wallet');
      }

      const wallet = agent.wallets[0];
      const amountDollars = amountCents / 100;
      const balanceDollars = Number(wallet.balance);

      if (balanceDollars < amountDollars) {
        throw new BadRequestException(
          `Insufficient funds. Available: $${balanceDollars.toFixed(2)}, Requested: $${amountDollars.toFixed(2)}`
        );
      }

      if (!wallet.stripeAccountId && this.stripe) {
        const status = await this.getAccountStatus(agentId);
        if (!status.isConnected) {
          throw new BadRequestException('Stripe account not connected');
        }
      }

      // Deduct from wallet
      await this.prisma.wallet.update({
        where: { id: wallet.id },
        data: {
          balance: balanceDollars - amountDollars,
          reserved: Number(wallet.reserved) + amountDollars,
        },
      });

      this.logger.log(`Payout requested for agent ${agentId}: $${amountDollars}`);

      return {
        success: true,
        amount: amountCents,
        message: 'Payout requested successfully',
      };
    } catch (error) {
      this.logger.error('Payout request failed', error);
      if (error instanceof BadRequestException) {
        throw error;
      }
      throw new InternalServerErrorException('Failed to request payout');
    }
  }

  /**
   * Get payout history for an agent
   */
  async getPayoutHistory(agentId: string) {
    try {
      const agent = await this.prisma.agent.findUnique({
        where: { id: agentId },
        include: {
          wallets: {
            include: {
              transactions: {
                take: 20,
                orderBy: { createdAt: 'desc' },
              },
            },
          },
        },
      });

      if (!agent?.wallets?.[0]?.transactions) {
        return [];
      }

      return agent.wallets[0].transactions.map((tx) => ({
        id: tx.id,
        amount: tx.amount.toString(),
        status: tx.status,
        createdAt: tx.createdAt,
        completedAt: tx.settledAt,
        reference: tx.reference,
      }));
    } catch (error) {
      this.logger.error('Failed to get payout history', error);
      return [];
    }
  }

  async getOrgAccountStatus(slug: string) {
    if (!this.stripe) {
      return { isConnected: false, message: 'Stripe not configured' };
    }

    try {
      const wallet = await this.walletsService.ensureOrganizationWalletBySlug(slug);
      const accountId = wallet.stripeAccountId;
      if (!accountId) {
        return { isConnected: false, message: 'No Stripe account connected' };
      }

      const account = await this.stripe.accounts.retrieve(accountId);

      return {
        accountId: account.id,
        isConnected: true,
        isChargesEnabled: account.charges_enabled,
        isPayoutsEnabled: account.payouts_enabled,
        isReady: account.charges_enabled && account.payouts_enabled,
        country: account.country,
        email: account.email,
      };
    } catch (error) {
      this.logger.error('Failed to get org account status', error);
      return { isConnected: false, message: 'Failed to check account status' };
    }
  }

  async requestOrgPayout(slug: string, amountCents: number) {
    try {
      const wallet = await this.walletsService.ensureOrganizationWalletBySlug(slug);

      const amountDollars = amountCents / 100;
      const balanceDollars = Number(wallet.balance);

      if (balanceDollars < amountDollars) {
        throw new BadRequestException(
          `Insufficient funds. Available: $${balanceDollars.toFixed(
            2,
          )}, Requested: $${amountDollars.toFixed(2)}`,
        );
      }

      if (!wallet.stripeAccountId && this.stripe) {
        const status = await this.getOrgAccountStatus(slug);
        if (!status.isConnected) {
          throw new BadRequestException('Stripe account not connected');
        }
      }

      await this.prisma.wallet.update({
        where: { id: wallet.id },
        data: {
          balance: balanceDollars - amountDollars,
          reserved: Number(wallet.reserved) + amountDollars,
        },
      });

      this.logger.log(`Org payout requested for ${slug}: $${amountDollars}`);

      return {
        success: true,
        amount: amountCents,
        message: 'Org payout requested successfully',
      };
    } catch (error) {
      this.logger.error('Org payout request failed', error);
      if (error instanceof BadRequestException) {
        throw error;
      }
      throw new InternalServerErrorException('Failed to request org payout');
    }
  }

  async getOrgPayoutHistory(slug: string) {
    try {
      const wallet = await this.walletsService.ensureOrganizationWalletBySlug(slug);
      const txs = await this.prisma.transaction.findMany({
        where: { walletId: wallet.id },
        take: 20,
        orderBy: { createdAt: 'desc' },
      });

      return txs.map((tx) => ({
        id: tx.id,
        amount: tx.amount.toString(),
        status: tx.status,
        createdAt: tx.createdAt,
        completedAt: tx.settledAt,
        reference: tx.reference,
      }));
    } catch (error) {
      this.logger.error('Failed to get org payout history', error);
      return [];
    }
  }

  /**
   * Handle Stripe webhook
   */
  async handlePayoutWebhook(payoutId: string, status: string) {
    this.logger.log(`Payout ${payoutId} status: ${status}`);
  }
}
