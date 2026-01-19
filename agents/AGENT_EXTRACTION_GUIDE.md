# Genesis Agent Extraction Guide

This guide explains how to extract Genesis agents to a new repository with all their dependencies.

## Quick Start

```bash
# Extract a single agent with all dependencies
python scripts/extract_agent.py builder_agent /path/to/new/repo

# Extract from custom source directory
python scripts/extract_agent.py qa_agent /path/to/new/repo --source /path/to/genesis
```

## What Gets Extracted

The extraction script automatically:

1. **Analyzes Dependencies:**
   - Recursively scans agent imports
   - Identifies required infrastructure modules
   - Maps complete dependency tree

2. **Copies Files:**
   - Target agent file (`agents/[agent_name].py`)
   - All infrastructure dependencies
   - Core infrastructure (error handler, env loader, LLM client)
   - Agent **init**.py files

3. **Creates Configuration:**
   - `.env.example` with required API keys
   - `.gitignore` for secrets protection
   - `requirements.txt` with dependencies
   - `README.md` with setup instructions

## Example: Extract Builder Agent

```bash
python scripts/extract_agent.py builder_agent ./standalone-builder
```

**Output:**

```
🔍 Analyzing dependencies for builder_agent...

📦 Found 12 files to copy:
   ✅ agents/builder_agent.py
   ✅ infrastructure/htdag_planner.py
   ✅ infrastructure/halo_router.py
   ✅ infrastructure/aop_validator.py
   ✅ infrastructure/local_llm_client.py
   ✅ infrastructure/error_handler.py
   ✅ infrastructure/load_env.py
   ... (and 5 more)

📂 Copying files to ./standalone-builder...
   ✅ Copied agents/builder_agent.py
   ✅ Copied infrastructure/htdag_planner.py
   ... (copying continues)

📦 Copying core infrastructure...
   ✅ Copied infrastructure/__init__.py
   ✅ Copied infrastructure/error_handler.py

⚙️  Copying configuration...
   ✅ Copied .env.example
   ✅ Copied .gitignore

📝 Creating requirements.txt...
📝 Creating README...

✅ Extraction complete!

📊 Summary:
   - Total files copied: 17
   - Agent files: 1
   - Infrastructure files: 12

📂 Target directory: /home/user/standalone-builder

🚀 Next steps:
   cd ./standalone-builder
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
```

## Agent Dependency Overview

Based on analysis of Genesis agents:

| Agent               | Infrastructure Dependencies | Core Modules                                       |
| ------------------- | --------------------------- | -------------------------------------------------- |
| **builder_agent**   | 8 modules                   | htdag, halo, aop, llm_client, error_handler        |
| **qa_agent**        | 10 modules                  | htdag, halo, aop, llm_client, trajectory_pool      |
| **deploy_agent**    | 8 modules                   | halo, llm_client, error_handler, namecom_client    |
| **marketing_agent** | 8 modules                   | halo, llm_client, error_handler, hybrid_automation |
| **seo_agent**       | 7 modules                   | halo, llm_client, tei_client, hybrid_rag           |
| **content_agent**   | 6 modules                   | halo, llm_client, error_handler                    |
| **finance_agent**   | 9 modules                   | halo, llm_client, x402_client, error_handler       |

**Common Dependencies (always needed):**

- `infrastructure/load_env.py` - Environment configuration
- `infrastructure/error_handler.py` - Error handling utilities
- `infrastructure/local_llm_client.py` - LLM client wrapper
- `agents/__init__.py` - Agent module initialization
- `.env.example` - Environment template
- `.gitignore` - Git exclusions

## Customization

### Extract Multiple Agents

```bash
# Extract builder + qa agents together
python scripts/extract_agent.py builder_agent ./my-agents
python scripts/extract_agent.py qa_agent ./my-agents
```

### Modify Extraction Script

Edit `scripts/extract_agent.py` to customize:

- **Line 107-113:** Core infrastructure files list
- **Line 125-128:** Configuration files to copy
- **Line 139-154:** requirements.txt dependencies
- **Line 159-196:** README template

### Add Custom Dependencies

If your agent needs additional files not auto-detected:

```python
# In extract_agent.py, add to core_files list (line 107)
core_files = [
    'infrastructure/__init__.py',
    'infrastructure/load_env.py',
    'infrastructure/error_handler.py',
    'infrastructure/local_llm_client.py',
    'agents/__init__.py',
    # Add your custom files here:
    'prompts/system_prompts.py',
    'config/agent_config.yaml',
]
```

## Troubleshooting

### Missing Dependencies

**Issue:** Agent imports module not copied

**Solution:** The script uses regex to detect imports. If it misses an import:

1. Check the import format is standard:

   ```python
   from infrastructure.module import Class  # ✅ Detected
   import infrastructure.module  # ✅ Detected
   from .local_module import func  # ❌ Not detected (relative import)
   ```

2. Add missing modules manually to `core_files` list

### Import Errors

**Issue:** `ModuleNotFoundError: No module named 'infrastructure'`

**Solution:** Ensure you installed dependencies:

```bash
cd extracted-agent-dir
pip install -r requirements.txt
```

### API Key Errors

**Issue:** Agent fails with missing API key

**Solution:** Copy `.env.example` to `.env` and add your keys:

```bash
cp .env.example .env
# Edit .env with your API keys
```

## Advanced Usage

### Analyze Dependencies Only

```python
from scripts.extract_agent import get_dependency_tree
from pathlib import Path

deps = get_dependency_tree(Path('agents/builder_agent.py'))
print(f"Found {len(deps)} dependencies:")
for dep in sorted(deps):
    print(f"  - {dep}")
```

### Custom Extraction Logic

```python
from scripts.extract_agent import extract_agent

# Extract with custom settings
extract_agent(
    agent_name='builder_agent',
    target_dir='/tmp/test-extraction',
    source_dir='.'  # Current Genesis repo
)
```

## Security Notes

- ✅ `.env.example` is copied (template only)
- ✅ `.env` is gitignored (secrets protected)
- ✅ API keys NOT included (must be added manually)
- ✅ `.gitignore` prevents accidental secret commits

## Next Steps

After extraction:

1. **Setup Environment:**

   ```bash
   cd extracted-agent-dir
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Secrets:**

   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Test Agent:**

   ```python
   from agents.builder_agent import get_builder_agent

   agent = get_builder_agent()
   result = agent.build_component(
       component_type="api_endpoint",
       spec={"name": "users", "methods": ["GET", "POST"]}
   )
   print(result)
   ```

4. **Deploy Standalone:**
   - Add to requirements.txt if needed
   - Create main.py entrypoint
   - Deploy to Railway/Render/etc.

## Support

For issues or questions:

- Check Genesis documentation: `CLAUDE.md`
- Review agent source code in `agents/`
- Check infrastructure modules in `infrastructure/`
