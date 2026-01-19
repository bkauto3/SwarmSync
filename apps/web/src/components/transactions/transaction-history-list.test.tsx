import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { TransactionHistoryList } from './transaction-history-list';

const baseDate = new Date('2024-02-01T00:00:00Z').toISOString();
const newerDate = new Date('2024-02-02T12:34:56Z').toISOString();

describe('TransactionHistoryList', () => {
  it('renders labels for both platform and x402 rails', () => {
    const markup = renderToStaticMarkup(
      <TransactionHistoryList
        transactions={[
          {
            id: 'platform-1',
            type: 'CREDIT',
            amount: 25,
            currency: 'USD',
            status: 'SETTLED',
            createdAt: baseDate,
            rail: 'platform',
            reference: 'charge_123',
          },
          {
            id: 'crypto-1',
            type: 'X402',
            amount: 12.5,
            currency: 'USDC',
            status: 'CONFIRMED',
            createdAt: newerDate,
            rail: 'x402',
            txHash: '0xabc',
            buyerAddress: '0xbuyer',
            sellerAddress: '0xseller',
            network: 'base-mainnet',
          },
        ]}
      />,
    );

    expect(markup).toContain('x402');
    expect(markup).toContain('$25.00');
    expect(markup).toContain('12.50 USDC');
    expect(markup).toContain('charge_123');
    expect(markup).toContain('0xabc');
  });
});

