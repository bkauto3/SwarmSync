# Agent Migration Status

## Completed

- ✅ Created `agents/` folder structure
- ✅ Created `__init__.py` with documentation
- ✅ Created `README.md` with migration instructions
- ✅ Copied `spec_agent.py` (723 lines)
- ✅ Copied `genesis_meta_agent.py` (1786 lines) - THE BEST ONE! 🤖

## Pending File Copy Operations

Due to terminal output issues, the following files still need to be copied manually or via script:

### From `C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis\agents\`:

1. `builder_agent.py` (841 lines)
2. `deploy_agent.py`
3. `qa_agent.py` (753 lines)
4. `research_discovery_agent.py`
5. `security_agent.py`
6. `maintenance_agent.py`
7. `seo_agent.py`
8. `content_agent.py`
9. `marketing_agent.py`
10. `support_agent.py`
11. `analyst_agent.py`
12. `finance_agent.py`
13. `pricing_agent.py`
14. `email_agent.py`
15. `billing_agent.py`
16. `commerce_agent.py`
17. `darwin_agent.py`
18. `domain_name_agent.py`
19. `legal_agent.py`
20. `onboarding_agent.py`
21. `reflection_agent.py`
22. `waltzrl_conversation_agent.py`
23. `waltzrl_feedback_agent.py`
24. `se_darwin_agent.py`
25. `ring1t_reasoning.py`

### From `C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis\infrastructure\`:

26. `business_idea_generator.py`

## Quick Copy Command

Run this PowerShell command to copy all files:

```powershell
$source = "C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis\agents"
$dest = "C:\Users\Ben\Desktop\Github\Agent-Market\agents"
Get-ChildItem "$source\*.py" -Exclude "__init__.py" | Copy-Item -Destination $dest -Force
Copy-Item "C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis\infrastructure\business_idea_generator.py" -Destination "$dest\business_idea_generator.py" -Force
```

## Next Steps After Copying

1. **Document Dependencies**: These agents rely on infrastructure modules from Genesis:
   - `infrastructure.daao_router`
   - `infrastructure.tumix_termination`
   - `infrastructure.self_correction`
   - `infrastructure.openenv_wrapper`
   - `infrastructure.hopx_agent_adapter`
   - `infrastructure.x402_client`
   - `infrastructure.x402_vendor_cache`
   - `infrastructure.reasoning_bank`
   - `infrastructure.replay_buffer`
   - `infrastructure.reflection_harness`
   - And others...

2. **Create Agent Payloads**: Use `packages/testkit/src/agentmarket_testkit/fixtures.py` `sample_agent_payload` as a template to create API-compatible payloads for each agent.

3. **Test with Lifecycle Suite**: Run `pytest tests/agents/test_agent_lifecycle.py` for each agent after creating them in the API.
