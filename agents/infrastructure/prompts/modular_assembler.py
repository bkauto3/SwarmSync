"""Modular Prompt Assembler: 4-file split system for agent prompts

Implements the Context Engineering 2.0 pattern from https://arxiv.org/abs/2510.26493

Each agent has 4 modular files:
1. {agent}_policy.md: High-level goals and constraints
2. {agent}_schema.yaml: Input/output schemas and tool definitions
3. {agent}_memory.json: Persistent facts and learned patterns
4. {agent}_fewshots.yaml: Example interactions

This enables:
- Easy versioning and diffing of prompt components
- Hot-swapping of policy/examples without redeployment
- Clear separation of concerns
- Template-based dynamic prompt generation
"""

import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime
import hashlib
from jinja2 import Template, TemplateNotFound, UndefinedError

logger = logging.getLogger(__name__)


class ModularPromptAssembler:
    """Assemble 4-part modular prompts into single coherent prompt for agent execution."""

    def __init__(
        self,
        prompts_dir: str = "prompts/modular",
        cache_enabled: bool = True,
        template_dir: Optional[str] = None
    ):
        """
        Initialize the ModularPromptAssembler.

        Args:
            prompts_dir: Root directory containing modular prompt files
            cache_enabled: Whether to cache assembled prompts
            template_dir: Directory for Jinja2 templates (optional)
        """
        self.prompts_dir = Path(prompts_dir)
        self.cache_enabled = cache_enabled
        self.cache: Dict[str, str] = {}
        self.cache_timestamps: Dict[str, float] = {}
        self.template_dir = Path(template_dir) if template_dir else None

        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")

        logger.info(f"ModularPromptAssembler initialized with prompts_dir={self.prompts_dir}")

    def assemble(
        self,
        agent_id: str,
        variables: Optional[Dict[str, Any]] = None,
        include_sections: Optional[List[str]] = None,
        task_context: Optional[str] = None
    ) -> str:
        """
        Assemble a complete prompt from 4 modular files.

        Args:
            agent_id: Agent identifier (e.g., 'qa_agent')
            variables: Template variables for Jinja2 rendering
            include_sections: List of sections to include (default: all)
                Valid values: ['policy', 'schema', 'memory', 'fewshots']
            task_context: Additional task-specific context to append

        Returns:
            Assembled prompt string ready for LLM input

        Raises:
            FileNotFoundError: If any required prompt file is missing
            ValueError: If agent_id format is invalid
        """
        # Validate agent_id format
        if not self._is_valid_agent_id(agent_id):
            raise ValueError(f"Invalid agent_id format: {agent_id}")

        # Check cache first
        cache_key = self._make_cache_key(agent_id, include_sections)
        if self.cache_enabled and cache_key in self.cache:
            prompt = self.cache[cache_key]
            logger.debug(f"Using cached prompt for {agent_id}")
        else:
            # Load and assemble 4 files
            prompt = self._assemble_from_files(agent_id, include_sections)
            if self.cache_enabled:
                self.cache[cache_key] = prompt
                self.cache_timestamps[cache_key] = datetime.now().timestamp()

        # Apply template rendering if variables provided
        if variables:
            try:
                template = Template(prompt)
                prompt = template.render(**variables)
                logger.debug(f"Applied template rendering with {len(variables)} variables")
            except (TemplateNotFound, UndefinedError) as e:
                logger.warning(f"Template rendering failed: {e}")
                # Continue with unrendered prompt

        # Append task context if provided
        if task_context:
            prompt += f"\n\n# TASK CONTEXT\n{task_context}"

        return prompt

    def assemble_batch(
        self,
        agent_ids: List[str],
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Assemble prompts for multiple agents in one call.

        Args:
            agent_ids: List of agent identifiers
            variables: Shared template variables

        Returns:
            Dictionary mapping agent_id -> assembled prompt
        """
        prompts = {}
        for agent_id in agent_ids:
            try:
                prompts[agent_id] = self.assemble(agent_id, variables=variables)
            except Exception as e:
                logger.error(f"Failed to assemble prompt for {agent_id}: {e}")
                prompts[agent_id] = None

        return prompts

    def get_schema(self, agent_id: str) -> Dict[str, Any]:
        """Get schema definition for agent (tools and outputs)."""
        schema_file = self.prompts_dir / f"{agent_id}_schema.yaml"
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")

        with open(schema_file) as f:
            return yaml.safe_load(f)

    def get_memory(self, agent_id: str) -> Dict[str, Any]:
        """Get memory/context for agent."""
        memory_file = self.prompts_dir / f"{agent_id}_memory.json"
        if not memory_file.exists():
            raise FileNotFoundError(f"Memory file not found: {memory_file}")

        with open(memory_file) as f:
            return json.load(f)

    def get_policy(self, agent_id: str) -> str:
        """Get policy definition for agent."""
        policy_file = self.prompts_dir / f"{agent_id}_policy.md"
        if not policy_file.exists():
            raise FileNotFoundError(f"Policy file not found: {policy_file}")

        with open(policy_file) as f:
            return f.read()

    def get_fewshots(self, agent_id: str) -> Dict[str, Any]:
        """Get few-shot examples for agent."""
        fewshots_file = self.prompts_dir / f"{agent_id}_fewshots.yaml"
        if not fewshots_file.exists():
            raise FileNotFoundError(f"Fewshots file not found: {fewshots_file}")

        with open(fewshots_file) as f:
            return yaml.safe_load(f)

    def update_memory(self, agent_id: str, updates: Dict[str, Any]) -> None:
        """
        Update agent's memory with new facts/learnings.

        Args:
            agent_id: Agent identifier
            updates: Dictionary of updates to merge into existing memory
        """
        memory_file = self.prompts_dir / f"{agent_id}_memory.json"
        if not memory_file.exists():
            raise FileNotFoundError(f"Memory file not found: {memory_file}")

        # Load existing memory
        with open(memory_file) as f:
            memory = json.load(f)

        # Merge updates
        memory.update(updates)
        memory["last_updated"] = datetime.now().isoformat()

        # Write back
        with open(memory_file, "w") as f:
            json.dump(memory, f, indent=2)

        # Invalidate cache
        self._invalidate_cache(agent_id)
        logger.info(f"Updated memory for {agent_id}")

    def add_fewshot_example(self, agent_id: str, input_text: str, output_text: str) -> None:
        """
        Add a new few-shot example to agent's examples.

        Args:
            agent_id: Agent identifier
            input_text: Example input/query
            output_text: Example output/response
        """
        fewshots_file = self.prompts_dir / f"{agent_id}_fewshots.yaml"
        if not fewshots_file.exists():
            raise FileNotFoundError(f"Fewshots file not found: {fewshots_file}")

        with open(fewshots_file) as f:
            fewshots = yaml.safe_load(f)

        # Add new example
        if "examples" not in fewshots:
            fewshots["examples"] = []

        fewshots["examples"].append({"input": input_text, "output": output_text})

        # Write back
        with open(fewshots_file, "w") as f:
            yaml.dump(fewshots, f, default_flow_style=False)

        # Invalidate cache
        self._invalidate_cache(agent_id)
        logger.info(f"Added fewshot example to {agent_id}")

    def validate_agent_prompts(self, agent_id: str) -> Dict[str, bool]:
        """
        Validate that all 4 required files exist for an agent.

        Returns:
            Dictionary with validation results
        """
        required_files = ["policy", "schema", "memory", "fewshots"]
        results = {}

        for file_type in required_files:
            file_path = self.prompts_dir / f"{agent_id}_{file_type}.yaml" \
                if file_type in ["schema", "fewshots"] else \
                self.prompts_dir / f"{agent_id}_{file_type}.md" \
                if file_type == "policy" else \
                self.prompts_dir / f"{agent_id}_{file_type}.json"

            results[file_type] = file_path.exists()

        return results

    def list_agents(self) -> List[str]:
        """List all agents with defined prompts."""
        agents = set()
        for file_path in self.prompts_dir.glob("*_policy.md"):
            agent_id = file_path.name.replace("_policy.md", "")
            agents.add(agent_id)

        return sorted(list(agents))

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about modular prompts."""
        agents = self.list_agents()
        total_files = len(list(self.prompts_dir.glob("*_*")))

        stats = {
            "total_agents": len(agents),
            "total_files": total_files,
            "agents": agents,
            "cache_enabled": self.cache_enabled,
            "cache_size": len(self.cache),
            "prompts_dir": str(self.prompts_dir),
            "timestamp": datetime.now().isoformat()
        }

        return stats

    # ==================== PRIVATE METHODS ====================

    def _assemble_from_files(
        self,
        agent_id: str,
        include_sections: Optional[List[str]] = None
    ) -> str:
        """Assemble prompt from 4 modular files."""
        if include_sections is None:
            include_sections = ["policy", "schema", "memory", "fewshots"]

        sections = {}

        # Load policy
        if "policy" in include_sections:
            sections["policy"] = self._load_policy(agent_id)

        # Load schema
        if "schema" in include_sections:
            sections["schema"] = self._format_schema(self._load_schema(agent_id))

        # Load memory
        if "memory" in include_sections:
            sections["memory"] = self._format_memory(self._load_memory(agent_id))

        # Load fewshots
        if "fewshots" in include_sections:
            sections["fewshots"] = self._format_fewshots(self._load_fewshots(agent_id))

        # Assemble with delimiters
        prompt = self._compose_sections(agent_id, sections)
        return prompt

    def _load_policy(self, agent_id: str) -> str:
        """Load policy.md file."""
        policy_file = self.prompts_dir / f"{agent_id}_policy.md"
        if not policy_file.exists():
            raise FileNotFoundError(f"Policy file not found: {policy_file}")

        with open(policy_file) as f:
            return f.read()

    def _load_schema(self, agent_id: str) -> Dict[str, Any]:
        """Load schema.yaml file."""
        schema_file = self.prompts_dir / f"{agent_id}_schema.yaml"
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")

        with open(schema_file) as f:
            return yaml.safe_load(f)

    def _load_memory(self, agent_id: str) -> Dict[str, Any]:
        """Load memory.json file."""
        memory_file = self.prompts_dir / f"{agent_id}_memory.json"
        if not memory_file.exists():
            raise FileNotFoundError(f"Memory file not found: {memory_file}")

        with open(memory_file) as f:
            return json.load(f)

    def _load_fewshots(self, agent_id: str) -> Dict[str, Any]:
        """Load fewshots.yaml file."""
        fewshots_file = self.prompts_dir / f"{agent_id}_fewshots.yaml"
        if not fewshots_file.exists():
            raise FileNotFoundError(f"Fewshots file not found: {fewshots_file}")

        with open(fewshots_file) as f:
            return yaml.safe_load(f)

    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """Format schema data into readable text."""
        output = []

        if "tools" in schema:
            output.append("**Available Tools:**\n")
            for tool in schema["tools"]:
                output.append(f"- {tool['name']}")
                if "description" in tool:
                    output.append(f"  {tool['description']}")
                if "parameters" in tool:
                    for param, desc in tool["parameters"].items():
                        output.append(f"  • {param}: {desc}")

        if "outputs" in schema:
            output.append("\n**Expected Outputs:**\n")
            for out in schema["outputs"]:
                output.append(f"- {out['name']} ({out['format']})")
                if "fields" in out:
                    for field in out["fields"]:
                        output.append(f"  • {field}")

        return "\n".join(output)

    def _format_memory(self, memory: Dict[str, Any]) -> str:
        """Format memory data into readable text."""
        output = ["**Context from Past Runs:**\n"]
        for key, value in memory.items():
            if key in ["created_at", "last_updated"]:
                continue
            if isinstance(value, dict):
                output.append(f"- {key}:")
                for sub_key, sub_value in value.items():
                    output.append(f"  • {sub_key}: {sub_value}")
            elif isinstance(value, list):
                output.append(f"- {key}:")
                for item in value:
                    output.append(f"  • {item}")
            else:
                output.append(f"- {key}: {value}")

        return "\n".join(output)

    def _format_fewshots(self, fewshots: Dict[str, Any]) -> str:
        """Format few-shot examples into readable text."""
        output = []

        if "examples" in fewshots:
            for i, example in enumerate(fewshots["examples"], 1):
                output.append(f"**Example {i}:**")
                output.append(f"Input: {example.get('input', '')}")
                output.append(f"Output:\n{example.get('output', '')}\n")

        return "\n".join(output)

    def _compose_sections(self, agent_id: str, sections: Dict[str, str]) -> str:
        """Compose final prompt from sections."""
        parts = [
            f"# {agent_id.replace('_', ' ').title()} Prompt",
            f"Generated: {datetime.now().isoformat()}",
            ""
        ]

        if "policy" in sections:
            parts.append("# ============================================================")
            parts.append("# POLICY (Goals, Role, Constraints)")
            parts.append("# ============================================================")
            parts.append(sections["policy"])
            parts.append("")

        if "schema" in sections:
            parts.append("# ============================================================")
            parts.append("# SCHEMA (Tools & Outputs)")
            parts.append("# ============================================================")
            parts.append(sections["schema"])
            parts.append("")

        if "memory" in sections:
            parts.append("# ============================================================")
            parts.append("# MEMORY (Context from Past Runs)")
            parts.append("# ============================================================")
            parts.append(sections["memory"])
            parts.append("")

        if "fewshots" in sections:
            parts.append("# ============================================================")
            parts.append("# FEW-SHOT EXAMPLES")
            parts.append("# ============================================================")
            parts.append(sections["fewshots"])
            parts.append("")

        parts.append("# ============================================================")
        parts.append("# YOUR TASK")
        parts.append("# ============================================================")

        return "\n".join(parts)

    def _is_valid_agent_id(self, agent_id: str) -> bool:
        """Validate agent_id format."""
        if not isinstance(agent_id, str):
            return False
        if not agent_id or len(agent_id) > 100:
            return False
        if not all(c.isalnum() or c == "_" for c in agent_id):
            return False
        return True

    def _make_cache_key(
        self,
        agent_id: str,
        include_sections: Optional[List[str]] = None
    ) -> str:
        """Generate cache key for prompt."""
        sections_str = ",".join(sorted(include_sections or ["policy", "schema", "memory", "fewshots"]))
        key_str = f"{agent_id}:{sections_str}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _invalidate_cache(self, agent_id: str) -> None:
        """Invalidate cache entries for an agent."""
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(agent_id)]
        for key in keys_to_remove:
            del self.cache[key]
            if key in self.cache_timestamps:
                del self.cache_timestamps[key]

        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for {agent_id}")
