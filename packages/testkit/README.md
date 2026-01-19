# AgentMarket Testkit

Lightweight helpers for exercising the AgentMarket API from end-to-end pytest suites.

## Features
- AgentMarketSDK: async client wrapping the public REST endpoints
- Pytest fixtures for bootstrapping users and sample agent payloads
- Retry decorator to smooth out transient API startup delays

## Quickstart
`ash
cd packages/testkit
poetry install
`

Within the monorepo you normally don't need a separate virtualenv. The top-level test command wires these fixtures automatically:
`ash
pytest tests/agents/test_agent_lifecycle.py
`

Set AGENT_MARKET_API_URL if your API is not running on http://localhost:4000.
