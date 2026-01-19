#!/usr/bin/env python3
"""Copy infrastructure modules from Genesis to Agent-Market"""
import shutil
import sys
from pathlib import Path

genesis_infra = Path(r"C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis\infrastructure")
agent_market_infra = Path(r"C:\Users\Ben\Desktop\Github\Agent-Market\agents\infrastructure")

# Create target directory
agent_market_infra.mkdir(parents=True, exist_ok=True)

# Redirect output to file for debugging
log_file = agent_market_infra.parent / "extraction_log.txt"
with open(log_file, "w") as f:
    f.write("Infrastructure Extraction Log\n")
    f.write("=" * 50 + "\n\n")

# Core infrastructure files (always needed)
core_files = [
    "__init__.py",
    "load_env.py",
    "error_handler.py",
    "local_llm_client.py",
]

# All infrastructure modules found from agent imports
infra_modules = [
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
]

def log_and_print(msg):
    print(msg)
    with open(log_file, "a") as f:
        f.write(msg + "\n")

log_and_print("📦 Copying infrastructure modules...\n")

copied = 0
skipped = 0
errors = 0

# Copy core files
for file in core_files:
    src = genesis_infra / file
    dst = agent_market_infra / file
    if src.exists():
        try:
            shutil.copy2(src, dst)
            log_and_print(f"   ✅ Copied: {file}")
            copied += 1
        except Exception as e:
            log_and_print(f"   ❌ Error copying {file}: {e}")
            errors += 1
    else:
        log_and_print(f"   ⚠️  Not found: {file}")

# Copy infrastructure modules
for module in infra_modules:
    src = genesis_infra / module
    dst = agent_market_infra / module
    if src.exists():
        try:
            if not dst.exists():
                shutil.copy2(src, dst)
                log_and_print(f"   ✅ Copied: {module}")
                copied += 1
            else:
                log_and_print(f"   ⏭️  Skipped (exists): {module}")
                skipped += 1
        except Exception as e:
            log_and_print(f"   ❌ Error copying {module}: {e}")
            errors += 1
    else:
        log_and_print(f"   ⚠️  Not found: {module}")

# Copy directories recursively
for dir_name in infra_dirs:
    src = genesis_infra / dir_name
    dst = agent_market_infra / dir_name
    if src.exists() and src.is_dir():
        try:
            if not dst.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)
                log_and_print(f"   ✅ Copied directory: {dir_name}/")
                copied += 1
            else:
                log_and_print(f"   ⏭️  Skipped directory (exists): {dir_name}/")
                skipped += 1
        except Exception as e:
            log_and_print(f"   ❌ Error copying {dir_name}: {e}")
            errors += 1
    else:
        log_and_print(f"   ⚠️  Not found: {dir_name}/")

log_and_print(f"\n📊 Summary:")
log_and_print(f"   ✅ Copied: {copied}")
log_and_print(f"   ⏭️  Skipped: {skipped}")
log_and_print(f"   ❌ Errors: {errors}")
log_and_print(f"\n✅ Infrastructure extraction complete!")
log_and_print(f"   Location: {agent_market_infra}")

