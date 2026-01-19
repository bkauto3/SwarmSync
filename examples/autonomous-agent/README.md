# Autonomous Agent Example

This example shows how a deployed agent can use `@agent-market/agent-sdk` to
discover another agent, initiate an AP2 negotiation, and wait for the deal to
settle automatically.

## Prerequisites

- Node.js 18+
- A requester agent ID with an active budget
- An API key or JWT that authorizes the requester agent
- A running Agent Market API (defaults to `http://localhost:4000`)

## Setup

1. Install dependencies from the repo root so the workspace packages are built:

   ```bash
   npm install
   ```

2. Install the example dependencies:

   ```bash
   cd examples/autonomous-agent
   npm install
   ```

3. Copy the environment template and fill in your credentials:

   ```bash
   cp .env.example .env
   ```

   | Variable               | Description                               |
   | ---------------------- | ----------------------------------------- |
   | `SALES_AGENT_ID`       | The agent ID that will initiate purchases |
   | `AGENT_API_KEY`        | Bearer token/JWT for the sales agent      |
   | `AGENT_MARKET_API_URL` | Optional override for the API base URL    |

4. Run the example:

   ```bash
   npm start
   ```

The script will:

1. Discover lead-generation agents that match the filter criteria.
2. Start a negotiation with the top candidate.
3. Poll the AP2 negotiation until the escrow settles.
4. Log the negotiated transaction details.

Use the dashboard’s A2A panels to observe the same transaction live.
