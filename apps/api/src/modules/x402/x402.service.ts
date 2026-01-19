import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { JsonRpcProvider, TransactionReceipt, TransactionResponse, parseUnits } from 'ethers';

import { PrismaService } from '../database/prisma.service.js';

interface ExecuteWithX402Params {
  agentId: string;
  txHash: string;
  buyerAddress: string;
  amount: number;
  task: Record<string, unknown>;
}

interface VerifyPaymentParams {
  agentId: string;
  txHash: string;
  buyerAddress: string;
  amount: number;
}

@Injectable()
export class X402Service {
  private readonly facilitatorUrl: string;
  private readonly enabled: boolean;
  private readonly defaultNetwork: string;
  private readonly provider: JsonRpcProvider | null;

  constructor(private readonly prisma: PrismaService) {
    this.facilitatorUrl = process.env.X402_FACILITATOR_URL ?? 'https://x402.org/facilitator';
    this.defaultNetwork = process.env.DEFAULT_NETWORK ?? 'base-mainnet';
    this.enabled = (process.env.X402_ENABLED ?? 'false').toLowerCase() === 'true';

    const rpcUrl = process.env.BASE_RPC_URL ?? 'https://mainnet.base.org';
    this.provider = this.enabled ? new JsonRpcProvider(rpcUrl) : null;
  }

  async getPaymentMethods(agentId: string) {
    const agent = await this.prisma.agent.findUnique({
      where: { id: agentId },
    });

    if (!agent) {
      throw new NotFoundException('Agent not found');
    }

    const fiatAmount = this.resolveFiatAmount(agent.priceAmount, agent.basePriceCents);

    const methods: Array<Record<string, unknown>> = [
      {
        type: 'platform',
        currency: 'USD',
        amount: fiatAmount,
        description: 'Pay via AgentMarket (credit card, bank transfer)',
        enabled: true,
      },
    ];

    if (this.enabled && agent.x402Enabled && agent.x402WalletAddress) {
      methods.push({
        type: 'x402',
        currency: 'USDC',
        amount: agent.x402Price ?? fiatAmount,
        recipient: agent.x402WalletAddress,
        network: agent.x402Network ?? this.defaultNetwork,
        description: 'Pay directly with USDC (instant, low fees)',
        facilitator: this.facilitatorUrl,
        enabled: true,
      });
    }

    return methods;
  }

  async verifyPayment(params: VerifyPaymentParams) {
    if (!this.enabled) {
      throw new BadRequestException('x402 payments are not enabled');
    }

    if (!this.provider) {
      throw new BadRequestException('Blockchain provider not configured');
    }

    const { agentId, txHash, buyerAddress, amount } = params;

    const agent = await this.prisma.agent.findUnique({
      where: { id: agentId },
    });

    if (!agent || !agent.x402Enabled || !agent.x402WalletAddress) {
      throw new BadRequestException('Agent does not accept x402 payments');
    }

    const existing = await this.prisma.x402Transaction.findUnique({
      where: { txHash },
    });

    if (existing) {
      return { verified: existing.status === 'CONFIRMED', transaction: existing };
    }

    const tx: TransactionResponse | null = await this.provider.getTransaction(txHash);

    if (!tx) {
      throw new BadRequestException('Transaction not found');
    }

    const receipt: TransactionReceipt | null = await tx.wait(1);

    if (!receipt || receipt.status !== 1) {
      throw new BadRequestException('Transaction failed on-chain');
    }

    // Placeholder for deeper validation using token transfer logs.
    const _expectedAmount = parseUnits(amount.toString(), 6);
    void _expectedAmount;

    const x402Tx = await this.prisma.x402Transaction.create({
      data: {
        agentId,
        buyerAddress,
        sellerAddress: agent.x402WalletAddress,
        amount: new Prisma.Decimal(amount),
        currency: 'USDC',
        network: agent.x402Network ?? this.defaultNetwork,
        txHash,
        status: 'CONFIRMED',
        confirmedAt: new Date(),
      },
    });

    return { verified: true, transaction: x402Tx };
  }

  async executeWithX402(params: ExecuteWithX402Params) {
    const verification = await this.verifyPayment({
      agentId: params.agentId,
      txHash: params.txHash,
      buyerAddress: params.buyerAddress,
      amount: params.amount,
    });

    if (!verification.verified) {
      throw new BadRequestException('Payment verification failed');
    }

    const agent = await this.prisma.agent.findUnique({
      where: { id: params.agentId },
    });

    if (!agent || !agent.ap2Endpoint) {
      throw new BadRequestException('Agent endpoint not configured');
    }

    const response = await fetch(agent.ap2Endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-payment': JSON.stringify({
          type: 'x402',
          txHash: params.txHash,
          amount: params.amount,
          network: agent.x402Network ?? this.defaultNetwork,
        }),
      },
      body: JSON.stringify(params.task),
    });

    if (!response.ok) {
      throw new BadRequestException(`Agent execution failed: ${response.statusText}`);
    }

    return response.json();
  }

  async handleWebhookEvent(event: {
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
  }) {
    const { transaction } = event;

    // Find existing transaction by txHash
    const existing = await this.prisma.x402Transaction.findUnique({
      where: { txHash: transaction.txHash },
    });

    let status: 'PENDING' | 'CONFIRMED' | 'FAILED';
    switch (event.type) {
      case 'payment.confirmed':
        status = 'CONFIRMED';
        break;
      case 'payment.failed':
        status = 'FAILED';
        break;
      case 'payment.pending':
        status = 'PENDING';
        break;
      default:
        throw new BadRequestException(`Unknown webhook event type: ${event.type}`);
    }

    if (existing) {
      // Update existing transaction
      await this.prisma.x402Transaction.update({
        where: { txHash: transaction.txHash },
        data: {
          status,
          confirmedAt: status === 'CONFIRMED' ? (transaction.confirmedAt ? new Date(transaction.confirmedAt) : new Date()) : null,
        },
      });
    } else {
      // Create new transaction if it doesn't exist
      // We need agentId - try to find it by sellerAddress if not provided
      let agentId = transaction.agentId;
      if (!agentId) {
        const agent = await this.prisma.agent.findFirst({
          where: {
            x402Enabled: true,
            x402WalletAddress: transaction.sellerAddress,
          },
        });
        if (!agent) {
          throw new BadRequestException(
            `Cannot find agent for seller address ${transaction.sellerAddress}`,
          );
        }
        agentId = agent.id;
      }

      await this.prisma.x402Transaction.create({
        data: {
          agentId,
          buyerAddress: transaction.buyerAddress,
          sellerAddress: transaction.sellerAddress,
          amount: new Prisma.Decimal(transaction.amount),
          currency: transaction.currency,
          network: transaction.network,
          txHash: transaction.txHash,
          status,
          confirmedAt: status === 'CONFIRMED' ? (transaction.confirmedAt ? new Date(transaction.confirmedAt) : new Date()) : null,
        },
      });
    }
  }

  private resolveFiatAmount(priceAmount?: number | null, basePriceCents?: number | null) {
    if (typeof priceAmount === 'number') {
      return priceAmount;
    }

    if (typeof basePriceCents === 'number') {
      return basePriceCents / 100;
    }

    return null;
  }
}

