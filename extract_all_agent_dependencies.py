#!/usr/bin/env python3
"""
Extract dependencies for all agents and consolidate infrastructure files
"""
import subprocess
import sys
from pathlib import Path
from collections import set

genesis_dir = Path(r"C:\Users\Ben\Desktop\Github\Claude-Clean-Code-Genesis")
agent_market_agents = Path(r"C:\Users\Ben\Desktop\Github\Agent-Market\agents")
extract_script = genesis_dir / "scripts" / "extract_agent.py"

# All agents to extract
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

print(f"🔍 Extracting dependencies for {len(agents)} agents...\n")

# Create temp directory for extractions
temp_dir = agent_market_agents / "_extracted_temp"
temp_dir.mkdir(exist_ok=True)

# Infrastructure directory to consolidate into
infra_dir = agent_market_agents / "infrastructure"
infra_dir.mkdir(exist_ok=True)

all_infrastructure_files = set()

for agent in agents:
    print(f"📦 Extracting {agent}...")
    target = temp_dir / agent
    
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(extract_script),
                agent,
                str(target),
                "--source",
                str(genesis_dir)
            ],
            cwd=str(genesis_dir),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"   ✅ {agent} extracted successfully")
            # Collect infrastructure files
            infra_path = target / "infrastructure"
            if infra_path.exists():
                for file in infra_path.glob("*.py"):
                    all_infrastructure_files.add(file.name)
        else:
            print(f"   ⚠️  {agent} extraction had issues:")
            print(f"      {result.stderr[:200]}")
    except Exception as e:
        print(f"   ❌ {agent} extraction failed: {e}")

print(f"\n📊 Found {len(all_infrastructure_files)} unique infrastructure modules")
print(f"   Files: {sorted(all_infrastructure_files)}")

# Now copy all infrastructure files from the first successful extraction
print(f"\n📂 Consolidating infrastructure files...")
for agent in agents:
    agent_infra = temp_dir / agent / "infrastructure"
    if agent_infra.exists():
        for file in agent_infra.glob("*.py"):
            target_file = infra_dir / file.name
            if not target_file.exists():
                import shutil
                shutil.copy2(file, target_file)
                print(f"   ✅ Copied {file.name}")

print(f"\n✅ Dependency extraction complete!")
print(f"   Infrastructure files in: {infra_dir}")

