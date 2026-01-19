# Infrastructure Extraction Instructions

## Overview

The agents in this directory depend on infrastructure modules from the Genesis project. To make them work in Agent-Market, we need to extract all the infrastructure dependencies.

## What Needs to Be Done

Based on the `Agent_extraction_guide.md`, you need to run the extraction script for each agent. The script will:

1. Analyze each agent's imports
2. Recursively find all infrastructure dependencies
3. Copy those files to a target directory

## How to Run

### Option 1: Extract All Agents (Recommended)

Run this PowerShell script from the Agent-Market root:

```powershell
$genesisDir = "C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis"
$targetBase = "C:\Users\Ben\Desktop\Github\Agent-Market\agents\infrastructure"

# Create infrastructure directory
New-Item -ItemType Directory -Force -Path $targetBase | Out-Null

$agents = @(
    "genesis_meta_agent",
    "builder_agent",
    "qa_agent",
    "spec_agent",
    "deploy_agent",
    "research_discovery_agent",
    "security_agent",
    "maintenance_agent",
    "seo_agent",
    "content_agent",
    "marketing_agent",
    "support_agent",
    "analyst_agent",
    "finance_agent",
    "pricing_agent",
    "email_agent",
    "billing_agent",
    "commerce_agent",
    "darwin_agent",
    "domain_name_agent",
    "legal_agent",
    "onboarding_agent",
    "reflection_agent",
    "waltzrl_conversation_agent",
    "waltzrl_feedback_agent",
    "se_darwin_agent",
    "ring1t_reasoning",
    "business_idea_generator"
)

foreach ($agent in $agents) {
    Write-Host "Extracting $agent..."
    $tempTarget = "$targetBase\_temp_$agent"
    python "$genesisDir\scripts\extract_agent.py" $agent $tempTarget --source $genesisDir

    # Copy infrastructure files from temp to main infrastructure
    if (Test-Path "$tempTarget\infrastructure") {
        Get-ChildItem "$tempTarget\infrastructure" -Recurse | ForEach-Object {
            $targetPath = $targetBase + $_.FullName.Substring($tempTarget.Length)
            $targetPath = $targetPath -replace "\\_temp_$agent", ""
            New-Item -ItemType Directory -Force -Path (Split-Path $targetPath) | Out-Null
            Copy-Item $_.FullName -Destination $targetPath -Force
        }
    }
}
```

### Option 2: Extract One Agent at a Time

For each agent, run:

```bash
cd C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis
python scripts/extract_agent.py <agent_name> C:\Users\Ben\Desktop\Github\Agent-Market\agents\infrastructure --source .
```

Replace `<agent_name>` with one of:

- `genesis_meta_agent`
- `builder_agent`
- `qa_agent`
- `spec_agent`
- etc.

## Infrastructure Modules Identified

From analyzing the agent imports, these infrastructure modules are needed:

### Core Infrastructure (Always Required)

- `__init__.py`
- `load_env.py`
- `error_handler.py`
- `local_llm_client.py`

### Agent-Specific Infrastructure

- `halo_router.py` - HALO routing system
- `task_dag.py` - Task dependency graph
- `genesis_discord.py` - Discord integration
- `x402_client.py` - Crypto payment client
- `code_extractor.py` - Code extraction utilities
- `business_monitor.py` - Business monitoring
- `ap2_service.py` - AP2 payment service
- `genesis_discord_bot.py` - Discord bot
- `prompts.py` - Modular prompt system
- `llm_client.py` - LLM client factory
- `hopx_agent_adapter.py` - HopX integration
- `x402_vendor_cache.py` - Payment vendor cache
- `memory_os.py` - Memory operating system
- `daao_router.py` - DAAO routing
- `tumix_termination.py` - TUMIX termination logic
- `creative_asset_registry.py` - Asset registry
- `deepseek_ocr_compressor.py` - OCR compression
- `self_correction.py` - Self-correction utilities
- `openenv_wrapper.py` - Environment wrapper
- `env_learning_agent.py` - Environment learning
- `memory_os_mongodb_adapter.py` - MongoDB memory adapter
- `ap2_connector.py` - AP2 connector
- `namecom_client.py` - Name.com client
- `rifl.py` - RIFL system
- `reasoning_bank.py` - Reasoning bank
- `replay_buffer.py` - Replay buffer
- `reflection_harness.py` - Reflection harness
- `observability.py` - Observability
- `context_profiles.py` - Context profiles
- `hallucination_control.py` - Hallucination control
- `trajectory_pool.py` - Trajectory pool
- `se_operators.py` - SE operators
- `benchmark_runner.py` - Benchmark runner
- `security_utils.py` - Security utilities
- `casebank.py` - Case bank
- `openhands_integration.py` - OpenHands integration
- `judge.py` - Judge system
- `oracle_hgm.py` - Oracle HGM
- `safety_layer.py` - Safety layer

### Infrastructure Directories (Copy Recursively)

- `ocr/` - OCR tools and services
- `memory/` - Memory systems
- `evolution/` - Evolution strategies
- `safety/` - Safety wrappers

## After Extraction

1. **Verify Files**: Check that `agents/infrastructure/` contains all the modules
2. **Update Imports**: Some agents may need import path adjustments
3. **Document Dependencies**: Create a `requirements.txt` for Python dependencies
4. **Test Imports**: Try importing agents to verify infrastructure is available

## Notes

- The extraction script automatically handles recursive dependencies
- It will copy core infrastructure files even if not explicitly imported
- Configuration files (`.env.example`, `.gitignore`) will also be copied
- Each extraction creates a `requirements.txt` and `README.md` in the target directory
