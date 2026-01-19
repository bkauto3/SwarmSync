"""
Compatibility wrapper for WaltzRL conversation agent.

Re-exports the implementation living under `infrastructure.safety` so imports
from `agents.waltzrl_conversation_agent` continue to work.
"""

from infrastructure.safety.waltzrl_conversation_agent import (
    CoachingContext,
    ConversationResponse,
    SafeResponse,
    WaltzRLConversationAgent,
    get_waltzrl_conversation_agent,
)

__all__ = [
    "CoachingContext",
    "ConversationResponse",
    "SafeResponse",
    "WaltzRLConversationAgent",
    "get_waltzrl_conversation_agent",
]
