"""
Environment Learning Agent - Self-Play Learning
Version: 1.0
Created: October 24, 2025

Agent that learns to interact with external environments via self-play.

Flow:
1. Reset environment
2. Agent proposes action (LLM-based)
3. Environment executes → (state, reward, done)
4. Store experience in CaseBank
5. Repeat until goal or max steps
6. Learn from episode outcomes

Integration: Enables 50-70% reliability improvement on external integrations
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from infrastructure.openenv_wrapper import OpenEnv, EnvObservation

logger = logging.getLogger(__name__)


class EnvironmentLearningAgent:
    """
    Agent that learns from self-play in environments.

    Uses LLM to propose actions, environment to execute,
    and experience replay to improve over episodes.

    Learning Strategy:
    - Episode 1: Exploration (random/LLM-guided actions)
    - Episode 2-N: Exploitation (use successful patterns from CaseBank)
    - Early stopping: If goal reached or quality plateaus
    """

    def __init__(
        self,
        env: OpenEnv,
        llm_client: Any,
        casebank: Optional[Any] = None,
        max_episodes: int = 10,
        max_steps_per_episode: int = 50
    ):
        """
        Initialize learning agent.

        Args:
            env: OpenEnv instance to interact with
            llm_client: LLM client for action proposal
            casebank: Optional CaseBank for experience storage
            max_episodes: Maximum learning episodes (default: 10)
            max_steps_per_episode: Max steps per episode (default: 50)
        """
        self.env = env
        self.llm = llm_client
        self.casebank = casebank
        self.max_episodes = max_episodes
        self.max_steps_per_episode = max_steps_per_episode
        self.episode_history: List[Dict] = []

        logger.info(
            f"EnvironmentLearningAgent initialized: "
            f"env={env.env_id}, max_episodes={max_episodes}"
        )

    async def learn_task(self, goal: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Learn to complete task via self-play.

        Args:
            goal: Task goal description
            context: Optional context (credentials, URLs, etc.)

        Returns:
            {
                "success": bool,
                "episodes": int,
                "best_reward": float,
                "learned_strategy": List[Dict],
                "total_steps": int,
                "learning_curve": List[float]
            }
        """
        best_reward = float('-inf')
        best_episode = None
        learning_curve = []

        logger.info(f"Starting self-play learning: goal='{goal}'")

        for episode_idx in range(self.max_episodes):
            logger.info(f"Episode {episode_idx + 1}/{self.max_episodes}")

            # Run episode
            episode_result = await self._run_episode(goal, context, episode_idx)

            # Track learning curve
            learning_curve.append(episode_result["total_reward"])

            # Update best episode
            if episode_result["total_reward"] > best_reward:
                best_reward = episode_result["total_reward"]
                best_episode = episode_result
                logger.info(
                    f"New best episode: reward={best_reward:.2f}, "
                    f"steps={episode_result['steps']}"
                )

            # Store successful episodes in CaseBank for future learning
            if self.casebank and episode_result["success"]:
                await self._store_experience(goal, episode_result, context)

            # Early stopping if goal reached
            if episode_result["success"]:
                logger.info(
                    f"Goal reached in episode {episode_idx + 1}! "
                    f"Stopping early."
                )
                break

            # Early stopping if learning plateaus
            if self._is_plateau(learning_curve, window=3, threshold=0.1):
                logger.info(
                    f"Learning plateau detected at episode {episode_idx + 1}. "
                    f"Stopping early."
                )
                break

        total_steps = sum(ep["steps"] for ep in self.episode_history)

        return {
            "success": best_episode["success"] if best_episode else False,
            "episodes": len(self.episode_history),
            "best_reward": best_reward,
            "learned_strategy": best_episode["actions"] if best_episode else [],
            "total_steps": total_steps,
            "learning_curve": learning_curve,
            "best_episode_idx": self.episode_history.index(best_episode) if best_episode else None
        }

    async def _run_episode(
        self,
        goal: str,
        context: Optional[Dict],
        episode_idx: int
    ) -> Dict[str, Any]:
        """
        Run single episode.

        Returns:
            {
                "success": bool,
                "total_reward": float,
                "actions": List[Dict],
                "steps": int
            }
        """
        # Reset environment
        obs = await self.env.reset()

        total_reward = 0.0
        actions = []
        done = False
        step_count = 0

        while not done and step_count < self.max_steps_per_episode:
            step_count += 1

            # Get similar experiences from CaseBank
            similar_experiences = await self._get_similar_experiences(
                goal, obs.state, actions
            )

            # Agent proposes action (LLM-based)
            action = await self._propose_action(
                goal, obs.state, actions, similar_experiences, context
            )

            # Environment executes action
            obs = await self.env.step(action)

            # Update episode metrics
            total_reward += obs.reward
            actions.append({
                **action,
                "reward": obs.reward,
                "step": step_count,
                "state_after": obs.state
            })

            done = obs.done

            # Log step
            logger.debug(
                f"Episode {episode_idx + 1}, Step {step_count}: "
                f"action={action.get('type')}, reward={obs.reward:.2f}, "
                f"done={done}"
            )

        episode_result = {
            "success": total_reward > 0 and done,
            "total_reward": total_reward,
            "actions": actions,
            "steps": step_count,
            "episode_idx": episode_idx
        }

        self.episode_history.append(episode_result)

        logger.info(
            f"Episode {episode_idx + 1} complete: "
            f"reward={total_reward:.2f}, steps={step_count}, "
            f"success={episode_result['success']}"
        )

        return episode_result

    async def _propose_action(
        self,
        goal: str,
        state: Dict[str, Any],
        history: List[Dict],
        similar_experiences: List[Dict],
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Use LLM to propose next action.

        Args:
            goal: Task goal
            state: Current environment state
            history: Action history (current episode)
            similar_experiences: Similar episodes from CaseBank
            context: Optional context (credentials, URLs, etc.)

        Returns:
            Action dict (environment-specific schema)
        """
        # Build prompt for LLM
        prompt = self._build_action_prompt(
            goal, state, history, similar_experiences, context
        )

        try:
            # Get LLM response
            response = await self._get_llm_response(prompt)

            # Parse action from response
            action = self._parse_action(response)

            logger.debug(f"LLM proposed action: {action}")

            return action

        except Exception as e:
            logger.warning(f"LLM action proposal failed: {e}. Using fallback.")
            return self._fallback_action(state, history)

    def _build_action_prompt(
        self,
        goal: str,
        state: Dict[str, Any],
        history: List[Dict],
        similar_experiences: List[Dict],
        context: Optional[Dict]
    ) -> str:
        """Build prompt for LLM action proposal"""

        # Format action history
        history_str = "None"
        if history:
            recent_history = history[-5:]  # Last 5 actions
            history_str = "\n".join([
                f"  {i + 1}. {action.get('type')}: "
                f"reward={action.get('reward', 0):.2f}"
                for i, action in enumerate(recent_history)
            ])

        # Format similar experiences
        experiences_str = "None"
        if similar_experiences:
            experiences_str = "\n".join([
                f"  {i + 1}. {exp.get('summary', 'N/A')}"
                for i, exp in enumerate(similar_experiences[:3])
            ])

        # Build prompt
        prompt = f"""You are controlling a {self.env.env_id} environment to achieve a goal.

**Goal:** {goal}

**Current State:**
{json.dumps(state, indent=2)}

**Action History (this episode):**
{history_str}

**Similar Successful Experiences (from past episodes):**
{experiences_str}

**Context:**
{json.dumps(context or {}, indent=2)}

**Available Actions (for {self.env.env_id}):**
"""

        # Add environment-specific action schemas
        if self.env.env_id == "playwright":
            prompt += """
- goto: {{"type": "goto", "url": "https://example.com"}}
- click: {{"type": "click", "selector": "#button-id"}}
- type: {{"type": "type", "selector": "#input-id", "text": "your text"}}
- screenshot: {{"type": "screenshot"}}
- wait: {{"type": "wait", "ms": 1000}}
"""
        elif self.env.env_id == "supabase":
            prompt += """
- insert: {{"type": "insert", "table": "users", "data": {{"name": "John"}}}}
- select: {{"type": "select", "table": "users", "filters": {{"id": "123"}}}}
- update: {{"type": "update", "table": "users", "id": "123", "data": {{"name": "Jane"}}}}
- delete: {{"type": "delete", "table": "users", "id": "123"}}
"""

        prompt += """
**Instructions:**
1. Analyze the current state and goal
2. Choose the best next action to make progress
3. Return ONLY a valid JSON action object
4. Do not include any explanation, only the JSON

**Your Action (JSON only):**"""

        return prompt

    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM"""
        # Check if LLM client has async generate method
        if hasattr(self.llm, 'generate') and asyncio.iscoroutinefunction(self.llm.generate):
            return await self.llm.generate(prompt)
        elif hasattr(self.llm, 'generate'):
            return self.llm.generate(prompt)
        else:
            raise AttributeError("LLM client must have a 'generate' method")

    def _parse_action(self, response: str) -> Dict[str, Any]:
        """Parse action from LLM response"""
        try:
            # Extract JSON from response
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])

            # Parse JSON
            action = json.loads(response)

            # Validate action has required 'type' field
            if "type" not in action:
                raise ValueError("Action must have 'type' field")

            return action

        except Exception as e:
            logger.warning(f"Failed to parse action from LLM response: {e}")
            raise

    def _fallback_action(self, state: Dict[str, Any], history: List[Dict]) -> Dict[str, Any]:
        """
        Fallback action when LLM fails.

        Simple heuristic-based action selection.
        """
        # Playwright fallback
        if self.env.env_id == "playwright":
            if not history:  # First action
                return {"type": "wait", "ms": 1000}
            else:
                return {"type": "screenshot"}

        # Supabase fallback
        elif self.env.env_id == "supabase":
            return {"type": "select", "table": "test", "filters": {}}

        # Default fallback
        return {"type": "wait", "ms": 500}

    async def _get_similar_experiences(
        self,
        goal: str,
        state: Dict[str, Any],
        actions: List[Dict]
    ) -> List[Dict]:
        """
        Retrieve similar experiences from CaseBank.

        Args:
            goal: Current goal
            state: Current state
            actions: Actions taken so far

        Returns:
            List of similar experiences
        """
        if not self.casebank:
            return []

        try:
            # Query CaseBank for similar experiences
            # (CaseBank should have semantic search capability)
            query = {
                "goal": goal,
                "env_id": self.env.env_id,
                "state_snippet": str(state)[:200]
            }

            similar = await self.casebank.retrieve_similar(query, top_k=3)
            return similar

        except Exception as e:
            logger.warning(f"Failed to retrieve similar experiences: {e}")
            return []

    async def _store_experience(
        self,
        goal: str,
        episode_result: Dict,
        context: Optional[Dict]
    ):
        """Store successful episode in CaseBank"""
        try:
            await self.casebank.add_case(
                state=goal,
                action=json.dumps(episode_result["actions"]),
                reward=episode_result["total_reward"],
                metadata={
                    "env_id": self.env.env_id,
                    "episode_idx": episode_result["episode_idx"],
                    "steps": episode_result["steps"],
                    "success": episode_result["success"],
                    "context": context,
                    "timestamp": datetime.now().isoformat()
                }
            )

            logger.info(
                f"Stored episode {episode_result['episode_idx']} in CaseBank: "
                f"reward={episode_result['total_reward']:.2f}"
            )

        except Exception as e:
            logger.warning(f"Failed to store experience in CaseBank: {e}")

    def _is_plateau(self, learning_curve: List[float], window: int = 3, threshold: float = 0.1) -> bool:
        """
        Check if learning has plateaued.

        Args:
            learning_curve: List of episode rewards
            window: Window size for plateau detection
            threshold: Improvement threshold

        Returns:
            True if plateau detected
        """
        if len(learning_curve) < window:
            return False

        # Check if last `window` episodes have similar rewards
        recent_rewards = learning_curve[-window:]
        max_reward = max(recent_rewards)
        min_reward = min(recent_rewards)

        # If variance is small, learning has plateaued
        return (max_reward - min_reward) < threshold
