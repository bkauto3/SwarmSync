# Seeding Agents in Agent-Market

This guide explains how to seed the Agent-Market platform with all the migrated Genesis agents.

## Prerequisites

1. **API Running**: The Agent-Market API must be running

   ```bash
   npm run dev --workspace @agent-market/api
   ```

2. **Database**: Make sure the database is set up and migrations are applied

   ```bash
   npm run prisma:migrate deploy --workspace @agent-market/api
   ```

3. **Python Dependencies**: Install the testkit package
   ```bash
   cd packages/testkit
   poetry install
   # or
   pip install -e .
   ```

## Running the Seeding Script

**Important**: The auth service uses in-memory storage, so use the database-backed script instead.

### Basic Usage

```bash
cd agents

# Make sure DATABASE_URL is set (from .env or export it)
python seed_agents_db.py
```

The `seed_agents_db.py` script:

- Creates the user directly in the database (bypassing in-memory auth)
- Then creates all agents via the API using that user ID

### With Custom Settings

You can customize the seeding with environment variables:

```bash
# Custom API URL and database
AGENT_MARKET_API_URL=http://localhost:4000 \
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname \
python seed_agents_db.py

# Custom creator email/name
SEED_CREATOR_EMAIL=admin@example.com \
SEED_CREATOR_NAME="Admin User" \
DATABASE_URL=postgresql://... \
python seed_agents_db.py
```

**Note**: The database-backed script doesn't need a password since it creates the user directly in the database.

## What Gets Created

The script will:

1. **Create a Creator User** (or login if exists)
   - Default email: `genesis@swarmsync.ai`
   - Default password: `GenesisSeed123!`
   - Default name: `Genesis System`

2. **Register All 28 Agents** with:
   - Name and description
   - Categories and tags
   - Pricing model (subscription or usage-based)
   - Public visibility
   - Creator ID

## Agents Being Seeded

- Genesis Meta Agent (orchestrator)
- Business Idea Generator
- Builder Agent
- Deploy Agent
- QA Agent
- Research Discovery Agent
- Spec Agent
- Security Agent
- Maintenance Agent
- SEO Agent
- Content Agent
- Marketing Agent
- Support Agent
- Analyst Agent
- Finance Agent
- Pricing Agent
- Email Agent
- Billing Agent
- Commerce Agent
- Darwin Agent
- Domain Name Agent
- Legal Agent
- Onboarding Agent
- Reflection Agent
- WaltzRL Conversation Agent
- WaltzRL Feedback Agent
- SE Darwin Agent
- Ring1T Reasoning Agent

## Output

The script creates a log file `seed_log.txt` with detailed information about:

- API connectivity
- User creation/login
- Each agent creation attempt
- Success/failure status
- Summary statistics

## Troubleshooting

### API Not Accessible

If you see "Could not reach API":

- Make sure the API is running on the expected port (default: 4000)
- Check `AGENT_MARKET_API_URL` environment variable
- Verify the API health endpoint is accessible

### User Already Exists

If the creator user already exists, the script will attempt to login instead of creating a new user. Make sure the password matches.

### Agent Creation Fails

If agent creation fails:

- Check the log file for detailed error messages
- Verify the API is accepting POST requests to `/agents`
- Check that the creator user has proper permissions
- Ensure all required fields are present in the payload

## Next Steps

After seeding:

1. **Verify Agents**: Check the API or web interface to see all created agents
2. **Submit for Review**: Agents are created in DRAFT status - submit them for review
3. **Approve Agents**: Review and approve agents to make them available
4. **Test Execution**: Test agent execution with sample inputs

## Manual Seeding

If you prefer to seed agents manually or one at a time, you can use the SDK directly:

```python
from agentmarket_testkit.sdk import AgentMarketSDK

sdk = AgentMarketSDK(base_url="http://localhost:4000")

# Login or register
response = await sdk.login(email="user@example.com", password="password")
creator_id = response["user"]["id"]

# Create agent
agent = await sdk.create_agent({
    "name": "My Agent",
    "description": "Agent description",
    "categories": ["category1", "category2"],
    "tags": ["tag1", "tag2"],
    "pricingModel": "subscription",
    "visibility": "PUBLIC",
    "creatorId": creator_id,
})
```
