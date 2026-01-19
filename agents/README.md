# Agent-Market Agents

This folder contains copies of custom-built agents ported from the Claude-Clean-Code-Genesis project.

## Migration Status

The agent files are being copied from:

- Source: `C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis\agents\`
- Source (business_idea_generator): `C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis\infrastructure\business_idea_generator.py`

## Agent Mapping (from MovingAgents.md)

- `genesis.idea.generate` → `business_idea_generator`
- `genesis.build` → `builder_agent`
- `genesis.deploy` → `deploy_agent`
- `genesis.qa` → `qa_agent`
- `research_agent` → `research_discovery_agent`
- Plus all other agents from the agents folder

## Next Steps

1. Copy all agent Python files from the source directory
2. Ensure all dependencies are documented
3. Create agent payloads for the Agent-Market API (see `packages/testkit/src/agentmarket_testkit/fixtures.py` for `sample_agent_payload`)
4. Test each agent with the lifecycle suite

## Dependencies

These agents may depend on infrastructure modules from the Genesis project:

- `infrastructure.daao_router`
- `infrastructure.tumix_termination`
- `infrastructure.self_correction`
- `infrastructure.openenv_wrapper`
- `infrastructure.hopx_agent_adapter`
- `infrastructure.x402_client`
- `infrastructure.x402_vendor_cache`
- And others...

When integrating into Agent-Market, these dependencies will need to be:

1. Copied to Agent-Market's infrastructure
2. Adapted to use Agent-Market's infrastructure
3. Or replaced with Agent-Market equivalents
