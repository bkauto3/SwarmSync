"""
WaltzRL DIR Calculator - Dynamic Improvement Reward
Version: 1.0
Date: October 22, 2025

Calculates Dynamic Improvement Reward (DIR) for feedback agent.
Used in Stage 2 training to reinforce good feedback.

Based on: WaltzRL (arXiv:2510.08240v1)
- DIR incentivizes useful feedback over binary blocking
- Joint training improves both agents simultaneously

Formula:
    DIR = safety_improvement * 0.5 +
          helpfulness_improvement * 0.3 +
          user_satisfaction * 0.2

DIR Range: -1.0 (degraded) to +1.0 (excellent improvement)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from typing import Optional, Dict, List, Any

from infrastructure.safety.waltzrl_feedback_agent import FeedbackResult
from infrastructure.safety.waltzrl_conversation_agent import SafeResponse

logger = logging.getLogger(__name__)


@dataclass
class DIRResult:
    """Result of Dynamic Improvement Reward calculation"""
    reward: float  # -1.0 to 1.0 (positive = good feedback, negative = bad feedback)
    safety_delta: float  # Change in safety score (-1.0 to 1.0)
    helpfulness_delta: float  # Change in helpfulness score (-1.0 to 1.0)
    user_satisfaction: float  # User satisfaction score (0.0 to 1.0)
    feedback_quality: float  # Quality of feedback suggestions (0.0 to 1.0)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/training"""
        return {
            'reward': self.reward,
            'safety_delta': self.safety_delta,
            'helpfulness_delta': self.helpfulness_delta,
            'user_satisfaction': self.user_satisfaction,
            'feedback_quality': self.feedback_quality,
            'timestamp': self.timestamp
        }


class DynamicImprovementReward:
    """
    Dynamic Improvement Reward (DIR) Calculator.

    Calculates reward for feedback agent based on:
    1. How much safety improved (safety_delta)
    2. How much helpfulness improved (helpfulness_delta)
    3. User satisfaction (optional, estimated if not provided)

    Used in Stage 2 training to jointly optimize both agents.
    """

    def __init__(
        self,
        safety_weight: float = 0.5,
        helpfulness_weight: float = 0.3,
        satisfaction_weight: float = 0.2
    ):
        """
        Initialize DIR Calculator.

        Args:
            safety_weight: Weight for safety improvement (default: 0.5)
            helpfulness_weight: Weight for helpfulness improvement (default: 0.3)
            satisfaction_weight: Weight for user satisfaction (default: 0.2)

        Note: Weights should sum to 1.0
        """
        # Normalize weights
        total_weight = safety_weight + helpfulness_weight + satisfaction_weight
        self.safety_weight = safety_weight / total_weight
        self.helpfulness_weight = helpfulness_weight / total_weight
        self.satisfaction_weight = satisfaction_weight / total_weight

        logger.info(
            f"DynamicImprovementReward initialized "
            f"(safety={self.safety_weight:.2f}, "
            f"helpfulness={self.helpfulness_weight:.2f}, "
            f"satisfaction={self.satisfaction_weight:.2f})"
        )

    def calculate_dir(
        self,
        original_feedback: FeedbackResult,
        improved_response: SafeResponse,
        user_satisfied: Optional[bool] = None,
        user_satisfaction_score: Optional[float] = None
    ) -> DIRResult:
        """
        Calculate Dynamic Improvement Reward.

        Args:
            original_feedback: Feedback result for original response
            improved_response: Improved response from conversation agent
            user_satisfied: Optional user satisfaction (True/False)
            user_satisfaction_score: Optional user satisfaction score (0.0-1.0)

        Returns:
            DIRResult with reward and component deltas

        Formula:
            DIR = safety_improvement * safety_weight +
                  helpfulness_improvement * helpfulness_weight +
                  user_satisfaction * satisfaction_weight
        """
        # Calculate safety improvement
        safety_delta = self._calculate_safety_improvement(
            original_feedback,
            improved_response
        )

        # Calculate helpfulness improvement
        helpfulness_delta = self._calculate_helpfulness_improvement(
            original_feedback,
            improved_response
        )

        # Calculate user satisfaction
        user_satisfaction = self._calculate_user_satisfaction(
            user_satisfied,
            user_satisfaction_score,
            safety_delta,
            helpfulness_delta
        )

        # Calculate feedback quality
        feedback_quality = self._calculate_feedback_quality(
            original_feedback,
            improved_response
        )

        # Calculate final DIR
        reward = (
            safety_delta * self.safety_weight +
            helpfulness_delta * self.helpfulness_weight +
            user_satisfaction * self.satisfaction_weight
        )

        # Clamp reward to [-1.0, 1.0]
        reward = max(-1.0, min(1.0, reward))

        result = DIRResult(
            reward=reward,
            safety_delta=safety_delta,
            helpfulness_delta=helpfulness_delta,
            user_satisfaction=user_satisfaction,
            feedback_quality=feedback_quality
        )

        logger.info(
            f"DIR calculated: reward={reward:.3f} "
            f"(safety_delta={safety_delta:.3f}, "
            f"helpfulness_delta={helpfulness_delta:.3f}, "
            f"satisfaction={user_satisfaction:.3f}, "
            f"feedback_quality={feedback_quality:.3f})"
        )

        return result

    def _calculate_safety_improvement(
        self,
        original_feedback: FeedbackResult,
        improved_response: SafeResponse
    ) -> float:
        """
        Calculate safety improvement.

        Returns:
            Delta in safety score (-1.0 to 1.0)
            - Positive: Safety improved
            - Negative: Safety degraded
        """
        original_safety = original_feedback.safety_score
        improved_safety = improved_response.safety_score

        # Calculate delta
        safety_delta = improved_safety - original_safety

        # Bonus for resolving critical issues
        critical_issues_count = sum(
            1 for issue in original_feedback.issues_found
            if issue.severity >= 0.9
        )

        if critical_issues_count > 0 and improved_safety > original_safety + 0.2:
            # Bonus for resolving critical issues
            safety_delta += 0.1 * critical_issues_count

        # Clamp to [-1.0, 1.0]
        return max(-1.0, min(1.0, safety_delta))

    def _calculate_helpfulness_improvement(
        self,
        original_feedback: FeedbackResult,
        improved_response: SafeResponse
    ) -> float:
        """
        Calculate helpfulness improvement.

        Returns:
            Delta in helpfulness score (-1.0 to 1.0)
            - Positive: Helpfulness improved
            - Negative: Helpfulness degraded
        """
        original_helpfulness = original_feedback.helpfulness_score
        improved_helpfulness = improved_response.helpfulness_score

        # Calculate delta
        helpfulness_delta = improved_helpfulness - original_helpfulness

        # Bonus for resolving over-refusal
        from infrastructure.safety.waltzrl_feedback_agent import SafetyCategory
        over_refusal_count = sum(
            1 for issue in original_feedback.issues_found
            if issue.category == SafetyCategory.OVER_REFUSAL
        )

        if over_refusal_count > 0 and improved_helpfulness > original_helpfulness + 0.2:
            # Bonus for resolving over-refusal
            helpfulness_delta += 0.1 * over_refusal_count

        # Penalty for degrading helpfulness while improving safety
        # (over-cautious feedback)
        if helpfulness_delta < -0.1 and improved_response.safety_score > original_feedback.safety_score:
            helpfulness_delta -= 0.1  # Extra penalty

        # Clamp to [-1.0, 1.0]
        return max(-1.0, min(1.0, helpfulness_delta))

    def _calculate_user_satisfaction(
        self,
        user_satisfied: Optional[bool],
        user_satisfaction_score: Optional[float],
        safety_delta: float,
        helpfulness_delta: float
    ) -> float:
        """
        Calculate user satisfaction score.

        If explicit user satisfaction is provided, use it.
        Otherwise, estimate based on safety and helpfulness improvements.

        Args:
            user_satisfied: Optional explicit user satisfaction (True/False)
            user_satisfaction_score: Optional explicit satisfaction score (0.0-1.0)
            safety_delta: Safety improvement delta
            helpfulness_delta: Helpfulness improvement delta

        Returns:
            User satisfaction score (0.0 to 1.0)
        """
        # Use explicit satisfaction if provided
        if user_satisfaction_score is not None:
            return max(0.0, min(1.0, user_satisfaction_score))

        if user_satisfied is not None:
            return 1.0 if user_satisfied else 0.0

        # Estimate satisfaction from improvements
        # Users care more about helpfulness than safety (assuming baseline safety)
        estimated_satisfaction = (
            0.3 * max(0.0, safety_delta) +  # Positive safety = good
            0.7 * max(0.0, helpfulness_delta)  # Positive helpfulness = great
        )

        # Penalty if either degraded significantly
        if safety_delta < -0.2 or helpfulness_delta < -0.2:
            estimated_satisfaction = 0.0

        return max(0.0, min(1.0, estimated_satisfaction))

    def _calculate_feedback_quality(
        self,
        original_feedback: FeedbackResult,
        improved_response: SafeResponse
    ) -> float:
        """
        Calculate feedback quality score.

        Measures how useful the feedback suggestions were.

        Factors:
        1. Were changes made? (feedback was actionable)
        2. Did scores improve? (feedback was correct)
        3. Were suggestions specific? (feedback was detailed)

        Returns:
            Feedback quality score (0.0 to 1.0)
        """
        quality_score = 0.5  # Base score

        # Factor 1: Actionability (were changes made?)
        if improved_response.feedback_incorporated:
            quality_score += 0.2

            # Bonus for multiple changes
            if len(improved_response.changes_made) >= 2:
                quality_score += 0.1

        # Factor 2: Correctness (did scores improve?)
        if improved_response.safety_score > original_feedback.safety_score:
            quality_score += 0.1

        if improved_response.helpfulness_score > original_feedback.helpfulness_score:
            quality_score += 0.1

        # Factor 3: Specificity (were suggestions detailed?)
        if len(original_feedback.suggestions) > 0:
            avg_suggestion_length = sum(
                len(s) for s in original_feedback.suggestions
            ) / len(original_feedback.suggestions)

            # Good suggestions are 50-200 chars (specific but concise)
            if 50 <= avg_suggestion_length <= 200:
                quality_score += 0.1

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, quality_score))

    def calculate_cumulative_reward(
        self,
        dir_results: list
    ) -> float:
        """
        Calculate cumulative reward across multiple episodes.

        Used for tracking training progress.

        Args:
            dir_results: List of DIRResult objects

        Returns:
            Average cumulative reward
        """
        if not dir_results:
            return 0.0

        total_reward = sum(result.reward for result in dir_results)
        avg_reward = total_reward / len(dir_results)

        return avg_reward

    def get_reward_statistics(
        self,
        dir_results: list
    ) -> Dict:
        """
        Get statistics about reward distribution.

        Useful for monitoring training progress.

        Args:
            dir_results: List of DIRResult objects

        Returns:
            Dictionary with statistics
        """
        if not dir_results:
            return {
                'count': 0,
                'mean': 0.0,
                'min': 0.0,
                'max': 0.0,
                'positive_rate': 0.0
            }

        rewards = [result.reward for result in dir_results]

        stats = {
            'count': len(rewards),
            'mean': sum(rewards) / len(rewards),
            'min': min(rewards),
            'max': max(rewards),
            'positive_rate': sum(1 for r in rewards if r > 0) / len(rewards)
        }

        return stats


def get_dir_calculator(
    safety_weight: float = 0.5,
    helpfulness_weight: float = 0.3,
    satisfaction_weight: float = 0.2
) -> DynamicImprovementReward:
    """
    Factory function to get DIR Calculator.

    Args:
        safety_weight: Weight for safety improvement (default: 0.5)
        helpfulness_weight: Weight for helpfulness improvement (default: 0.3)
        satisfaction_weight: Weight for user satisfaction (default: 0.2)

    Returns:
        Configured DynamicImprovementReward instance
    """
    return DynamicImprovementReward(
        safety_weight=safety_weight,
        helpfulness_weight=helpfulness_weight,
        satisfaction_weight=satisfaction_weight
    )


def summarize_dir_results(dir_results: List[DIRResult]) -> Dict[str, Any]:
    """
    Summarize a list of DIR results with aggregate statistics.

    Args:
        dir_results: List of DIRResult objects from WaltzRL runs.

    Returns:
        Dictionary containing reward statistics and component averages.
    """
    if not dir_results:
        return {
            "reward_stats": {
                "count": 0,
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
                "positive_rate": 0.0,
            },
            "component_averages": {
                "safety_delta": 0.0,
                "helpfulness_delta": 0.0,
                "user_satisfaction": 0.0,
                "feedback_quality": 0.0,
            },
        }

    rewards = [result.reward for result in dir_results]
    safety_deltas = [result.safety_delta for result in dir_results]
    helpfulness_deltas = [result.helpfulness_delta for result in dir_results]
    satisfaction_scores = [result.user_satisfaction for result in dir_results]
    feedback_scores = [result.feedback_quality for result in dir_results]

    reward_stats = {
        "count": len(rewards),
        "mean": mean(rewards),
        "min": min(rewards),
        "max": max(rewards),
        "positive_rate": sum(1 for value in rewards if value > 0) / len(rewards),
    }

    component_averages = {
        "safety_delta": mean(safety_deltas),
        "helpfulness_delta": mean(helpfulness_deltas),
        "user_satisfaction": mean(satisfaction_scores),
        "feedback_quality": mean(feedback_scores),
    }

    return {
        "reward_stats": reward_stats,
        "component_averages": component_averages,
    }


def generate_dir_report(
    dir_results: List[DIRResult],
    evaluation_metrics: Optional[Dict[str, float]] = None,
    baseline_metrics: Optional[Dict[str, float]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a comprehensive DIR report summarizing performance across runs.

    Args:
        dir_results: List of DIRResult objects from WaltzRL runs.
        evaluation_metrics: Optional metrics captured during evaluation
            (e.g., unsafe_rate, overrefusal_rate, total_runs).
        baseline_metrics: Optional baseline metrics to compare against.
        metadata: Optional metadata (e.g., cohort size, dataset identifiers).

    Returns:
        Dictionary containing aggregated DIR statistics and improvements.
    """
    summary = summarize_dir_results(dir_results)
    report: Dict[str, Any] = {
        "metadata": metadata or {},
        "reward_stats": summary["reward_stats"],
        "component_averages": summary["component_averages"],
        "evaluation_metrics": evaluation_metrics or {},
        "improvements": {},
    }

    if evaluation_metrics and baseline_metrics:
        improvements: Dict[str, Any] = {}

        unsafe_curr = evaluation_metrics.get("unsafe_rate")
        unsafe_prev = baseline_metrics.get("unsafe_rate")
        if unsafe_curr is not None and unsafe_prev is not None:
            improvements["unsafe_reduction"] = unsafe_prev - unsafe_curr

        overrefusal_curr = evaluation_metrics.get("overrefusal_rate")
        overrefusal_prev = baseline_metrics.get("overrefusal_rate")
        if overrefusal_curr is not None and overrefusal_prev is not None:
            improvements["overrefusal_reduction"] = overrefusal_prev - overrefusal_curr

        if improvements:
            report["improvements"] = improvements

    return report
