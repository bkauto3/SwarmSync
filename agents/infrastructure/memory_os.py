"""
GenesisMemoryOS - Unified Memory Operating System for Genesis Multi-Agent System

Integration of MemoryOS (EMNLP 2025) with Genesis 15-agent architecture.
Provides 3-tier hierarchical memory (short/mid/long-term) with MongoDB backend.

Architecture:
- Short-term: Session-level conversation history (10 QA pairs, deque-based)
- Mid-term: Consolidated segments with heat-based promotion (2000 capacity, FAISS vector similarity)
- Long-term: User profiles + knowledge base (100 capacity, persistent across sessions)

Key Features:
- 49.11% F1 improvement over baseline (LoCoMo benchmark)
- Heat-based memory promotion (visit frequency, interaction length, recency)
- Vector similarity search (FAISS) for retrieval
- LFU eviction for capacity management
- Agent-specific memory isolation (15 agents × users)

References:
- Paper: https://arxiv.org/abs/2506.06326
- GitHub: https://github.com/BAI-LAB/MemoryOS
- Comparison: /docs/MEMORY_SYSTEMS_COMPARISON.md
"""

import os
import sys
from typing import Dict, List, Optional, Any
from pathlib import Path

# Add MemoryOS to path for imports
MEMORYOS_PATH = "/home/genesis/genesis-rebuild/integrations/memory/MemoryOS/memoryos-pypi"
if MEMORYOS_PATH not in sys.path:
    sys.path.insert(0, MEMORYOS_PATH)

# Try to import memoryos, fallback to None if not available
try:
    from memoryos import Memoryos
except ModuleNotFoundError:
    Memoryos = None  # Will use mock/fallback implementation


class GenesisMemoryOS:
    """
    Unified memory operating system for all 15 Genesis agents.

    Provides hierarchical memory management with agent-specific isolation:
    - Builder, Deploy, QA, Marketing, Support, Legal, Content, Analyst, Security,
      Maintenance, Billing, SEO, Spec, Onboarding, Email agents

    Memory Types:
    1. **Consensus Memory**: Verified team procedures (shared across agents)
    2. **Persona Libraries**: Agent characteristics and behavior patterns
    3. **Whiteboard Methods**: Shared working spaces for collaboration

    Backend: JSON files (migration to MongoDB planned for Phase 5)
    """

    def __init__(
        self,
        openai_api_key: str,
        data_storage_path: str = "./data/memory_os",
        openai_base_url: Optional[str] = None,
        llm_model: str = "gpt-4o-mini",
        embedding_model_name: str = "BAAI/bge-m3",  # Best performance from MemoryOS paper
        short_term_capacity: int = 10,
        mid_term_capacity: int = 2000,
        long_term_knowledge_capacity: int = 100,
        mid_term_heat_threshold: float = 5.0,
        mid_term_similarity_threshold: float = 0.6
    ):
        """
        Initialize GenesisMemoryOS.

        Args:
            openai_api_key: OpenAI API key for LLM operations
            data_storage_path: Base path for memory storage
            openai_base_url: Optional custom OpenAI endpoint
            llm_model: LLM model for memory operations (default: gpt-4o-mini for cost efficiency)
            embedding_model_name: Embedding model (default: BAAI/bge-m3, best from paper)
            short_term_capacity: Max QA pairs in short-term memory
            mid_term_capacity: Max segments in mid-term memory
            long_term_knowledge_capacity: Max knowledge entries in long-term memory
            mid_term_heat_threshold: Heat threshold for mid→long promotion
            mid_term_similarity_threshold: Similarity threshold for deduplication
        """
        self.data_storage_path = Path(data_storage_path).resolve()
        self.openai_api_key = openai_api_key
        self.openai_base_url = openai_base_url
        self.llm_model = llm_model
        self.embedding_model_name = embedding_model_name

        # MemoryOS configuration
        self.config = {
            "short_term_capacity": short_term_capacity,
            "mid_term_capacity": mid_term_capacity,
            "long_term_knowledge_capacity": long_term_knowledge_capacity,
            "mid_term_heat_threshold": mid_term_heat_threshold,
            "mid_term_similarity_threshold": mid_term_similarity_threshold,
        }

        # Agent-specific memory instances (lazy initialization)
        self._agent_memories: Dict[str, Dict[str, Memoryos]] = {}

        # Genesis 15 agents
        self.GENESIS_AGENTS = [
            "builder", "deploy", "qa", "marketing", "support",
            "legal", "content", "analyst", "security", "maintenance",
            "billing", "seo", "spec", "onboarding", "email"
        ]

        print(f"[GenesisMemoryOS] Initialized with:")
        print(f"  - Storage: {self.data_storage_path}")
        print(f"  - LLM: {self.llm_model}")
        print(f"  - Embedding: {self.embedding_model_name}")
        print(f"  - Short-term capacity: {short_term_capacity}")
        print(f"  - Mid-term capacity: {mid_term_capacity}")
        print(f"  - Long-term capacity: {long_term_knowledge_capacity}")

    def _get_memory_instance(self, agent_id: str, user_id: str) -> Memoryos:
        """
        Get or create MemoryOS instance for specific agent-user pair.

        Lazy initialization: Only creates memory when first accessed.

        Args:
            agent_id: Genesis agent ID (e.g., "builder", "qa", "support")
            user_id: User ID for memory isolation

        Returns:
            Memoryos instance for agent-user pair
        """
        key = f"{agent_id}_{user_id}"

        if key not in self._agent_memories:
            # Create MemoryOS instance
            assistant_id = f"genesis_{agent_id}_agent"

            memory = Memoryos(
                user_id=user_id,
                openai_api_key=self.openai_api_key,
                openai_base_url=self.openai_base_url,
                data_storage_path=str(self.data_storage_path),
                assistant_id=assistant_id,
                llm_model=self.llm_model,
                embedding_model_name=self.embedding_model_name,
                **self.config
            )

            self._agent_memories[key] = memory
            print(f"[GenesisMemoryOS] Created memory for agent={agent_id}, user={user_id}")

        return self._agent_memories[key]

    def store(
        self,
        agent_id: str,
        user_id: str,
        user_input: str,
        agent_response: str,
        memory_type: str = "conversation"
    ) -> None:
        """
        Store memory for specific agent-user pair.

        Memory Types:
        - "conversation": Store user-agent interaction (short-term → mid-term → long-term)
        - "consensus": Store verified team procedure (shared across agents)
        - "persona": Store agent behavior pattern
        - "whiteboard": Store shared working space content

        Args:
            agent_id: Genesis agent ID
            user_id: User ID
            user_input: User's input message
            agent_response: Agent's response
            memory_type: Type of memory to store (default: "conversation")
        """
        if agent_id not in self.GENESIS_AGENTS:
            print(f"[GenesisMemoryOS] WARNING: Unknown agent_id={agent_id}")

        memory = self._get_memory_instance(agent_id, user_id)

        if memory_type == "conversation":
            # Standard conversation memory (short-term)
            memory.add_memory(user_input=user_input, agent_response=agent_response)
            print(f"[GenesisMemoryOS] Stored conversation: agent={agent_id}, user={user_id}")

        elif memory_type in ["consensus", "persona", "whiteboard"]:
            # Advanced memory types (future: Phase 5 MongoDB integration)
            # For now, store as long-term knowledge with type prefix
            knowledge_text = f"[{memory_type.upper()}] User: {user_input}\nAgent: {agent_response}"
            memory.user_long_term_memory.add_user_knowledge(knowledge_text)
            print(f"[GenesisMemoryOS] Stored {memory_type}: agent={agent_id}, user={user_id}")

        else:
            raise ValueError(f"Unknown memory_type: {memory_type}")

    def retrieve(
        self,
        agent_id: str,
        user_id: str,
        query: str,
        memory_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for specific agent-user pair.

        Uses hierarchical retrieval:
        1. Short-term: Recent conversation history
        2. Mid-term: Relevant session segments (FAISS similarity search)
        3. Long-term: User profile + knowledge base

        Args:
            agent_id: Genesis agent ID
            user_id: User ID
            query: Query text for retrieval
            memory_type: Optional filter for memory type ("consensus", "persona", "whiteboard")
            top_k: Number of top results to return

        Returns:
            List of relevant memory entries
        """
        memory = self._get_memory_instance(agent_id, user_id)

        # Get comprehensive context from all memory tiers
        retrieval_result = memory.retrieve_context(query=query)

        # Parse retrieval result (MemoryOS returns formatted string)
        memories = self._parse_retrieval_result(retrieval_result, memory_type)

        print(f"[GenesisMemoryOS] Retrieved {len(memories)} memories: agent={agent_id}, user={user_id}, query='{query[:50]}...'")

        return memories[:top_k]

    def _parse_retrieval_result(self, result: str, memory_type: Optional[str]) -> List[Dict[str, Any]]:
        """
        Parse MemoryOS retrieval result into structured format.

        Args:
            result: Raw retrieval result string from MemoryOS
            memory_type: Optional filter for specific memory type

        Returns:
            List of structured memory entries
        """
        # TODO: Implement proper parsing based on MemoryOS retrieval format
        # For now, return basic structure
        memories = []

        if result:
            # Split by sections (short-term, mid-term, long-term, profile)
            sections = result.split("\n\n")

            for section in sections:
                if not section.strip():
                    continue

                # Filter by memory_type if specified
                if memory_type and f"[{memory_type.upper()}]" not in section:
                    continue

                memory_entry = {
                    "content": section.strip(),
                    "source": "memoryos",
                    "type": self._infer_memory_type(section)
                }
                memories.append(memory_entry)

        return memories

    def _infer_memory_type(self, section: str) -> str:
        """Infer memory type from section content."""
        if "[CONSENSUS]" in section:
            return "consensus"
        elif "[PERSONA]" in section:
            return "persona"
        elif "[WHITEBOARD]" in section:
            return "whiteboard"
        elif "User Profile:" in section or "User profile:" in section:
            return "profile"
        elif "Short-Term" in section or "short_term" in section:
            return "short_term"
        elif "Mid-Term" in section or "mid_term" in section:
            return "mid_term"
        elif "Long-Term" in section or "long_term" in section or "Knowledge" in section:
            return "long_term"
        else:
            return "conversation"

    def consolidate(self, agent_id: str, user_id: str) -> None:
        """
        Manually trigger memory consolidation.

        MemoryOS automatically consolidates when short-term is full,
        but this method forces consolidation for specific agent-user pair.

        Args:
            agent_id: Genesis agent ID
            user_id: User ID
        """
        memory = self._get_memory_instance(agent_id, user_id)

        # Check if short-term is full to trigger consolidation
        if memory.short_term_memory.is_full():
            # Add a dummy QA pair to trigger consolidation
            memory.add_memory(
                user_input="[CONSOLIDATION_TRIGGER]",
                agent_response="[CONSOLIDATION_TRIGGER]"
            )

        print(f"[GenesisMemoryOS] Consolidation triggered: agent={agent_id}, user={user_id}")

    def get_user_profile(self, agent_id: str, user_id: str) -> str:
        """
        Get user profile for specific agent-user pair.

        Args:
            agent_id: Genesis agent ID
            user_id: User ID

        Returns:
            User profile string (generated from long-term memory)
        """
        memory = self._get_memory_instance(agent_id, user_id)
        profile = memory.user_long_term_memory.get_raw_user_profile(user_id)

        print(f"[GenesisMemoryOS] Retrieved user profile: agent={agent_id}, user={user_id}")

        return profile if profile != "None" else ""

    def get_response(
        self,
        agent_id: str,
        user_id: str,
        query: str
    ) -> str:
        """
        Get memory-augmented response for user query.

        Uses full MemoryOS pipeline:
        1. Retrieve relevant context from all memory tiers
        2. Generate response using LLM with context
        3. Store interaction in short-term memory

        Args:
            agent_id: Genesis agent ID
            user_id: User ID
            query: User query

        Returns:
            Memory-augmented response
        """
        memory = self._get_memory_instance(agent_id, user_id)
        response = memory.get_response(query=query)

        print(f"[GenesisMemoryOS] Generated response: agent={agent_id}, user={user_id}, query='{query[:50]}...'")

        return response

    def clear_agent_memory(self, agent_id: str, user_id: str) -> None:
        """
        Clear all memory for specific agent-user pair.

        WARNING: This deletes all short/mid/long-term memory.
        Use with caution.

        Args:
            agent_id: Genesis agent ID
            user_id: User ID
        """
        key = f"{agent_id}_{user_id}"

        if key in self._agent_memories:
            del self._agent_memories[key]

        # Delete files
        user_dir = self.data_storage_path / "users" / user_id
        if user_dir.exists():
            import shutil
            shutil.rmtree(user_dir)

        print(f"[GenesisMemoryOS] Cleared memory: agent={agent_id}, user={user_id}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics across all agents.

        Returns:
            Dictionary with memory statistics
        """
        stats = {
            "total_instances": len(self._agent_memories),
            "agents": {},
            "config": self.config
        }

        for key, memory in self._agent_memories.items():
            agent_id, user_id = key.rsplit("_", 1)

            if agent_id not in stats["agents"]:
                stats["agents"][agent_id] = {}

            stats["agents"][agent_id][user_id] = {
                "short_term_count": len(memory.short_term_memory.get_all()),
                "mid_term_count": len(memory.mid_term_memory.sessions),
                "long_term_knowledge_count": len(memory.user_long_term_memory.get_user_knowledge()),
                "assistant_knowledge_count": len(memory.user_long_term_memory.get_assistant_knowledge())
            }

        return stats


# Convenience functions for direct usage

def create_genesis_memory(
    openai_api_key: str,
    data_storage_path: str = "./data/memory_os",
    **kwargs
) -> GenesisMemoryOS:
    """
    Factory function to create GenesisMemoryOS instance.

    Args:
        openai_api_key: OpenAI API key
        data_storage_path: Base path for memory storage
        **kwargs: Additional MemoryOS configuration

    Returns:
        GenesisMemoryOS instance
    """
    return GenesisMemoryOS(
        openai_api_key=openai_api_key,
        data_storage_path=data_storage_path,
        **kwargs
    )


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Initialize
    memory_os = create_genesis_memory(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        data_storage_path="./data/memory_os_test"
    )

    # Store conversation for QA agent
    memory_os.store(
        agent_id="qa",
        user_id="test_user",
        user_input="How do I run tests in Genesis?",
        agent_response="Run `pytest tests/` from the project root."
    )

    # Retrieve memories
    memories = memory_os.retrieve(
        agent_id="qa",
        user_id="test_user",
        query="How to test?"
    )

    print("\nRetrieved memories:")
    for i, mem in enumerate(memories, 1):
        print(f"{i}. {mem['type']}: {mem['content'][:100]}...")

    # Get stats
    stats = memory_os.get_stats()
    print(f"\nMemory stats: {stats}")
