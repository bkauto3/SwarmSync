"""
Compatibility wrapper for WaltzRL feedback agent.

Re-exports the implementation living under ``infrastructure.safety`` so legacy
imports from ``agents.waltzrl_feedback_agent`` continue to work without code
changes.
"""

from infrastructure.safety.waltzrl_feedback_agent import (
    FeedbackEvaluation,
    FeedbackResult,
    SafetyAnalysis,
    SafetyCategory,
    SafetyIssue,
    WaltzRLFeedbackAgent,
    get_waltzrl_feedback_agent,
)

__all__ = [
    "FeedbackEvaluation",
    "FeedbackResult",
    "SafetyAnalysis",
    "SafetyCategory",
    "SafetyIssue",
    "WaltzRLFeedbackAgent",
    "get_waltzrl_feedback_agent",
]
