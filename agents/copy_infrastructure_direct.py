#!/usr/bin/env python3
"""Directly copy infrastructure modules from Genesis to Agent-Market"""
import shutil
from pathlib import Path

genesis_infra = Path(r"C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis\infrastructure")
agent_market_infra = Path(r"C:\Users\Ben\Desktop\Github\Agent-Market\agents\infrastructure")

# Create target directory
agent_market_infra.mkdir(parents=True, exist_ok=True)

# All infrastructure modules identified from agent imports
infra_modules = [
    # Core infrastructure
    "__init__.py",
    "load_env.py",
    "error_handler.py",
    "local_llm_client.py",
    
    # Agent dependencies
    "halo_router.py",
    "task_dag.py",
    "genesis_discord.py",
    "x402_client.py",
    "code_extractor.py",
    "business_monitor.py",
    "ap2_service.py",
    "genesis_discord_bot.py",
    "prompts.py",
    "llm_client.py",
    "hopx_agent_adapter.py",
    "x402_vendor_cache.py",
    "memory_os.py",
    "daao_router.py",
    "tumix_termination.py",
    "creative_asset_registry.py",
    "deepseek_ocr_compressor.py",
    "self_correction.py",
    "openenv_wrapper.py",
    "env_learning_agent.py",
    "memory_os_mongodb_adapter.py",
    "ap2_connector.py",
    "namecom_client.py",
    "rifl.py",
    "reasoning_bank.py",
    "replay_buffer.py",
    "reflection_harness.py",
    "observability.py",
    "context_profiles.py",
    "hallucination_control.py",
    "trajectory_pool.py",
    "se_operators.py",
    "benchmark_runner.py",
    "security_utils.py",
    "casebank.py",
    "openhands_integration.py",
    "judge.py",
    "oracle_hgm.py",
    "safety_layer.py",
]

# Directories to copy recursively
infra_dirs = [
    "ocr",
    "memory",
    "evolution",
    "safety",
    "prompts",  # prompts might be a directory
]

print("📦 Copying infrastructure modules directly...\n")

copied = 0
skipped = 0
errors = 0

# Copy individual modules
for module in infra_modules:
    src = genesis_infra / module
    dst = agent_market_infra / module
    
    if src.exists() and src.is_file():
        try:
            if not dst.exists():
                shutil.copy2(src, dst)
                print(f"   ✅ Copied: {module}")
                copied += 1
            else:
                print(f"   ⏭️  Skipped (exists): {module}")
                skipped += 1
        except Exception as e:
            print(f"   ❌ Error copying {module}: {e}")
            errors += 1
    else:
        print(f"   ⚠️  Not found: {module}")

# Copy directories recursively
for dir_name in infra_dirs:
    src = genesis_infra / dir_name
    dst = agent_market_infra / dir_name
    
    if src.exists() and src.is_dir():
        try:
            if not dst.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)
                file_count = len(list(dst.rglob("*")))
                print(f"   ✅ Copied directory: {dir_name}/ ({file_count} files)")
                copied += 1
            else:
                print(f"   ⏭️  Skipped directory (exists): {dir_name}/")
                skipped += 1
        except Exception as e:
            print(f"   ❌ Error copying {dir_name}: {e}")
            errors += 1
    else:
        print(f"   ⚠️  Not found: {dir_name}/")

print(f"\n📊 Summary:")
print(f"   ✅ Copied: {copied} items")
print(f"   ⏭️  Skipped: {skipped} items")
print(f"   ❌ Errors: {errors}")
print(f"\n✅ Infrastructure copy complete!")
print(f"   Location: {agent_market_infra}")

