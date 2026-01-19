import { Prisma } from '@prisma/client';

import { AgentsService } from './agents.service.js';
import { PrismaService } from '../database/prisma.service.js';
import { Ap2Service } from '../payments/ap2.service.js';
import { WalletsService } from '../payments/wallets.service.js';

const mockDate = (value: string) => new Date(value);

describe('AgentsService.getAgentPaymentHistory', () => {
  let service: AgentsService;
  let prisma: {
    agent: { count: jest.Mock };
    wallet: { findMany: jest.Mock };
    x402Transaction: { findMany: jest.Mock };
  };

  beforeEach(() => {
    prisma = {
      agent: { count: jest.fn().mockResolvedValue(1) },
      wallet: { findMany: jest.fn() },
      x402Transaction: { findMany: jest.fn() },
    };

    service = new AgentsService(
      prisma as unknown as PrismaService,
      {} as WalletsService,
      {} as Ap2Service,
    );
  });

  it('merges platform and x402 transactions ordered by newest first', async () => {
    prisma.wallet.findMany.mockResolvedValue([
      {
        id: 'wallet-1',
        currency: 'USD',
        transactions: [
          {
            id: 'platform-1',
            type: 'CREDIT',
            amount: new Prisma.Decimal(25),
            status: 'SETTLED',
            reference: 'charge_123',
            metadata: null,
            createdAt: mockDate('2024-02-01T10:00:00Z'),
          },
        ],
      },
    ]);

    prisma.x402Transaction.findMany.mockResolvedValue([
      {
        id: 'x402-1',
        agentId: 'agent-1',
        buyerAddress: '0xbuyer',
        sellerAddress: '0xseller',
        amount: new Prisma.Decimal(12.5),
        currency: 'USDC',
        network: 'base-mainnet',
        txHash: '0xabc',
        status: 'CONFIRMED',
        createdAt: mockDate('2024-02-02T12:00:00Z'),
        confirmedAt: mockDate('2024-02-02T12:05:00Z'),
      },
    ]);

    const history = await service.getAgentPaymentHistory('agent-1');

    expect(history).toHaveLength(2);
    expect(history[0]).toMatchObject({
      id: 'x402-1',
      rail: 'x402',
      amount: 12.5,
      currency: 'USDC',
      txHash: '0xabc',
      buyerAddress: '0xbuyer',
      sellerAddress: '0xseller',
    });
    expect(history[1]).toMatchObject({
      id: 'platform-1',
      rail: 'platform',
      amount: 25,
      currency: 'USD',
      walletId: 'wallet-1',
      reference: 'charge_123',
    });
    expect(history[0].createdAt.getTime()).toBeGreaterThan(history[1].createdAt.getTime());
  });

  it('handles cases with missing wallet transactions', async () => {
    prisma.wallet.findMany.mockResolvedValue([]);
    prisma.x402Transaction.findMany.mockResolvedValue([]);

    const history = await service.getAgentPaymentHistory('agent-1');

    expect(history).toEqual([]);
  });
});

