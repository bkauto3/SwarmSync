#!/usr/bin/env python3
"""Extract infrastructure dependencies for all agents"""
import subprocess
import shutil
import sys
from pathlib import Path
from datetime import datetime

genesis_dir = Path(r"C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis")
target_base = Path(r"C:\Users\Ben\Desktop\Github\Agent-Market\agents\infrastructure")
extract_script = genesis_dir / "scripts" / "extract_agent.py"
log_file = Path(r"C:\Users\Ben\Desktop\Github\Agent-Market\agents\extraction_log.txt")

def log(msg):
    """Log to both console and file"""
    print(msg)
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')} - {msg}\n")
    except Exception as e:
        print(f"Log error: {e}")

agents = [
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
    "business_idea_generator",
]

# Create target directory
target_base.mkdir(parents=True, exist_ok=True)

# Initialize log file
with open(log_file, "w", encoding="utf-8") as f:
    f.write(f"Infrastructure Extraction Log - {datetime.now()}\n")
    f.write("=" * 60 + "\n\n")

log(f"🔍 Extracting infrastructure dependencies for {len(agents)} agents...\n")

copied_files = set()
errors = []

for i, agent in enumerate(agents, 1):
    log(f"[{i}/{len(agents)}] Extracting {agent}...")
    
    temp_target = target_base / f"_temp_{agent}"
    
    # Check if extraction script exists
    if not extract_script.exists():
        log(f"   ❌ Extraction script not found: {extract_script}")
        errors.append((agent, "Extraction script not found"))
        continue
    
    try:
        # Check if agent exists in agents/ or infrastructure/
        agent_in_agents = (genesis_dir / "agents" / f"{agent}.py").exists()
        agent_in_infra = (genesis_dir / "infrastructure" / f"{agent}.py").exists()
        
        if not agent_in_agents and not agent_in_infra:
            log(f"   ⚠️  Agent file not found in agents/ or infrastructure/")
            errors.append((agent, "Agent file not found"))
            continue
        
        # Run extraction script
        log(f"   Running: python {extract_script} {agent} {temp_target} --source {genesis_dir}")
        result = subprocess.run(
            [
                sys.executable,
                str(extract_script),
                agent,
                str(temp_target),
                "--source",
                str(genesis_dir),
            ],
            cwd=str(genesis_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        log(f"   Return code: {result.returncode}")
        
        # If extraction failed, log the full error
        if result.returncode != 0:
            full_error = result.stderr if result.stderr else result.stdout
            log(f"   Full error: {full_error[:500]}")
        
        if result.returncode == 0:
            # Copy infrastructure files
            agent_infra = temp_target / "infrastructure"
            if agent_infra.exists():
                for file_path in agent_infra.rglob("*"):
                    if file_path.is_file():
                        rel_path = file_path.relative_to(agent_infra)
                        target_path = target_base / rel_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, target_path)
                        copied_files.add(str(rel_path))
                file_count = len([f for f in agent_infra.rglob('*') if f.is_file()])
                log(f"   ✅ Copied {file_count} files")
            else:
                log("   ⚠️  No infrastructure found")
        else:
            error_msg = result.stderr[:200] if result.stderr else "Unknown error"
            log(f"   ❌ Error: {error_msg}")
            errors.append((agent, error_msg))
        
        # Clean up temp directory
        if temp_target.exists():
            shutil.rmtree(temp_target, ignore_errors=True)
            
    except subprocess.TimeoutExpired:
        log(f"   ⏱️  Timeout after 120 seconds")
        errors.append((agent, "Timeout"))
        if temp_target.exists():
            shutil.rmtree(temp_target, ignore_errors=True)
    except Exception as e:
        log(f"   ❌ Exception: {str(e)}")
        errors.append((agent, str(e)))
        if temp_target.exists():
            shutil.rmtree(temp_target, ignore_errors=True)

log(f"\n📊 Summary:")
log(f"   ✅ Copied {len(copied_files)} unique infrastructure files")
log(f"   ❌ {len(errors)} errors")

if errors:
    log(f"\n⚠️  Errors encountered:")
    for agent, error in errors:
        log(f"   - {agent}: {error}")

log(f"\n✅ Infrastructure extraction complete!")
log(f"   Location: {target_base}")
log(f"\n📁 Sample files copied:")
for file in sorted(copied_files)[:30]:
    log(f"   - {file}")
if len(copied_files) > 30:
    log(f"   ... and {len(copied_files) - 30} more files")

