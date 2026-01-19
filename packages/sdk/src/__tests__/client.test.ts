import { describe, expect, it } from 'vitest';

import { AgentMarketClient } from '..';

describe('AgentMarketClient', () => {
  it('creates client with default base URL', () => {
    const client = new AgentMarketClient();

    expect(client).toBeInstanceOf(AgentMarketClient);
  });
});
