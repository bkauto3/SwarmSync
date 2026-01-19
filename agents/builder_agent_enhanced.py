"""
Enhanced Builder Agent - Day 3 Learning-Enabled Version
Version: 4.0 (Day 3 Enhancement)
Last Updated: October 15, 2025

Learning-enabled code generation system with ReasoningBank and Replay Buffer integration.
This agent learns from every build attempt and improves over time.

Key Features:
- Query ReasoningBank for proven code patterns before building
- Record every build attempt as a trajectory in Replay Buffer
- Store successful patterns back to ReasoningBank for future reuse
- Self-improvement through experience accumulation
- Full observability and error handling

MODEL: Claude Sonnet 4 (via Azure fallback) or GPT-4o
OUTPUT: 20-30 complete code files + learning metadata
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from agent_framework.observability import setup_observability
from azure.identity.aio import AzureCliCredential

# Import learning infrastructure
from infrastructure.reasoning_bank import (
    ReasoningBank,
    get_reasoning_bank,
    MemoryType,
    OutcomeTag,
    StrategyNugget
)
from infrastructure.replay_buffer import (
    ReplayBuffer,
    get_replay_buffer,
    Trajectory,
    ActionStep
)

setup_observability(enable_sensitive_data=True)
# Import DAAO and TUMIX
from infrastructure.daao_router import get_daao_router, RoutingDecision
from infrastructure.tumix_termination import (
    get_tumix_termination,
    RefinementResult,
    TerminationDecision
)


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BuildAttempt:
    """
    Metadata for a single build attempt

    Tracks what was built, patterns used, and outcome
    """
    attempt_id: str
    business_id: str
    spec_summary: str
    patterns_queried: List[str] = field(default_factory=list)
    patterns_used: List[str] = field(default_factory=list)
    files_generated: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None


class EnhancedBuilderAgent:
    """
    Enhanced Builder Agent with Learning Capabilities

    Responsibilities:
    1. Generate complete Next.js/React applications from specifications
    2. Query ReasoningBank for proven code patterns before building
    3. Record every build attempt in Replay Buffer for learning
    4. Store successful patterns back to ReasoningBank
    5. Continuously improve through experience

    Learning Loop:
    - Before: Query ReasoningBank for similar successful builds
    - During: Record every tool call with reasoning as trajectory
    - After: Store successful patterns for future reuse

    Self-Improvement:
    - Learns from every build (success or failure)
    - Patterns accumulate over time
    - Later builds benefit from earlier experience
    """

    def __init__(self, business_id: str = "default"):
        """
        Initialize Enhanced Builder Agent

        Args:
            business_id: Unique identifier for the business being built
        """
        self.business_id = business_id
        self.agent = None
        self.executions = 0
        self.total_cost = 0.0

        # Learning infrastructure
        self.reasoning_bank: ReasoningBank = get_reasoning_bank()
        self.replay_buffer: ReplayBuffer = get_replay_buffer()

        # Current trajectory tracking
        self.current_trajectory: Optional[Trajectory] = None
        self.current_attempt: Optional[BuildAttempt] = None
        self.trajectory_steps: List[ActionStep] = []

        logger.info(f"✅ Enhanced Builder Agent initialized for business: {business_id}")
        logger.info("   Learning systems connected:")
        logger.info(f"   - ReasoningBank: {self.reasoning_bank.mongo_available and 'MongoDB' or 'In-Memory'}")
        logger.info(f"   - ReplayBuffer: {self.replay_buffer.mongo_available and 'MongoDB' or 'In-Memory'}")

        # Initialize DAAO router for cost optimization
        self.router = get_daao_router()

        # Initialize TUMIX for iterative refinement
        self.termination = get_tumix_termination(
            min_rounds=2,
            max_rounds=4,
            improvement_threshold=0.05
        )

        # Track refinement sessions for metrics
        self.refinement_history: List[List[RefinementResult]] = []

        logger.info(f"{{agent_name}} v4.0 initialized with DAAO + TUMIX for business: {{business_id}}")

    async def initialize(self):
        """Initialize the agent with Azure AI Agent Client"""
        cred = AzureCliCredential()
        client = AzureAIAgentClient(async_credential=cred)

        self.agent = ChatAgent(
            chat_client=client,
            instructions=self._get_system_instruction(),
            name="builder-agent-enhanced",
            tools=[
                self.generate_frontend,
                self.generate_backend,
                self.generate_database,
                self.generate_config,
                self.review_code
            ]
        )

        logger.info(f"🔨 Enhanced Builder Agent initialized for business: {self.business_id}")
        logger.info("   Model: Claude Sonnet 4 / GPT-4o")
        logger.info("   Learning: ENABLED (ReasoningBank + Replay Buffer)")
        logger.info("   Ready to generate production code with learning\n")

    def _get_system_instruction(self) -> str:
        """System instruction for enhanced builder agent"""
        return """You are an expert full-stack developer with learning capabilities.

Your role:
1. Generate production-ready, complete code
2. Learn from past successful builds (query ReasoningBank)
3. Record your decisions for future improvement
4. Use best practices (TypeScript, error handling, loading states)
5. Create clean, maintainable, well-documented code
6. Follow modern frameworks: Next.js 14, React 18, Tailwind CSS, Supabase

You are:
- Learning: Query proven patterns before building
- Thorough: Every file is complete and production-ready
- Modern: Use latest framework features and patterns
- Practical: Code that actually works, not tutorials
- Security-conscious: Proper auth, validation, error handling
- Self-improving: Record every decision for future learning

Always return structured JSON with file paths and content."""

    def _start_trajectory(self, task_description: str, initial_state: Dict[str, Any]) -> str:
        """
        Start recording a new trajectory

        Args:
            task_description: Human-readable task description
            initial_state: Initial state/context for the task

        Returns:
            Trajectory ID
        """
        trajectory_id = f"traj_{self.business_id}_{int(time.time() * 1000)}"

        self.current_trajectory = None  # Will be created when finalized
        self.trajectory_steps = []

        # Create build attempt metadata
        self.current_attempt = BuildAttempt(
            attempt_id=trajectory_id,
            business_id=self.business_id,
            spec_summary=task_description,
            start_time=time.time()
        )

        logger.info(f"📝 Started trajectory recording: {trajectory_id}")
        logger.info(f"   Task: {task_description}")

        return trajectory_id

    def _check_anti_patterns(self, spec: str) -> List[Dict[str, Any]]:
        """
        Check for known failure patterns (anti-patterns) before building

        Query Replay Buffer for similar task failures to avoid repeating mistakes.

        Args:
            spec: Build specification to check

        Returns:
            List of anti-pattern dictionaries with failure details
        """
        try:
            # Extract task type from spec
            task_type = "build"
            if "frontend" in spec.lower():
                task_type = "frontend"
            elif "backend" in spec.lower():
                task_type = "backend"
            elif "database" in spec.lower():
                task_type = "database"

            # Query anti-patterns from Replay Buffer
            anti_patterns = self.replay_buffer.query_anti_patterns(
                task_type=task_type,
                top_n=5
            )

            if anti_patterns:
                logger.warning(f"⚠️  Found {len(anti_patterns)} known failure patterns for {task_type} tasks")
                for pattern in anti_patterns:
                    logger.warning(f"   - {pattern['failure_rationale']}")
                    if pattern.get('fix_applied'):
                        logger.info(f"     Fix: {pattern['fix_applied']}")

            return anti_patterns

        except Exception as e:
            logger.warning(f"Failed to check anti-patterns: {e}")
            return []

    def _record_action(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_result: Any,
        agent_reasoning: str
    ):
        """
        Record an action step in the current trajectory

        Args:
            tool_name: Name of tool called
            tool_args: Arguments passed to tool
            tool_result: Result returned from tool
            agent_reasoning: Why the agent chose this action
        """
        if self.current_attempt is None:
            logger.warning("⚠️  No active trajectory - cannot record action")
            return

        step = ActionStep(
            timestamp=datetime.now(timezone.utc).isoformat(),
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            agent_reasoning=agent_reasoning
        )

        self.trajectory_steps.append(step)

        logger.debug(f"📌 Recorded action: {tool_name}")

    def _finalize_trajectory(
        self,
        outcome: OutcomeTag,
        reward: float,
        metadata: Optional[Dict[str, Any]] = None,
        failure_rationale: Optional[str] = None,
        error_category: Optional[str] = None,
        fix_applied: Optional[str] = None
    ) -> str:
        """
        Finalize and store trajectory in Replay Buffer with failure tracking

        Args:
            outcome: Final outcome (SUCCESS, FAILURE, PARTIAL)
            reward: Reward score 0.0-1.0
            metadata: Additional metadata
            failure_rationale: WHY the failure occurred (for FAILURE outcomes)
            error_category: Error classification (configuration, validation, network, timeout, etc.)
            fix_applied: How the issue was resolved

        Returns:
            Trajectory ID
        """
        if self.current_attempt is None:
            logger.warning("⚠️  No active trajectory to finalize")
            return ""

        self.current_attempt.end_time = time.time()
        duration = self.current_attempt.end_time - self.current_attempt.start_time

        # Create trajectory object with failure tracking
        trajectory = Trajectory(
            trajectory_id=self.current_attempt.attempt_id,
            agent_id=f"builder_agent_{self.business_id}",
            task_description=self.current_attempt.spec_summary,
            initial_state={
                "business_id": self.business_id,
                "patterns_available": len(self.current_attempt.patterns_queried)
            },
            steps=tuple(self.trajectory_steps),
            final_outcome=outcome.value,
            reward=reward,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc).isoformat(),
            duration_seconds=duration,
            failure_rationale=failure_rationale,
            error_category=error_category,
            fix_applied=fix_applied
        )

        # Store in Replay Buffer (will auto-store anti-pattern if FAILURE with rationale)
        trajectory_id = self.replay_buffer.store_trajectory(trajectory)

        logger.info(f"✅ Trajectory finalized and stored: {trajectory_id}")
        logger.info(f"   Outcome: {outcome.value}, Reward: {reward:.2f}, Duration: {duration:.2f}s")
        logger.info(f"   Steps recorded: {len(self.trajectory_steps)}")
        if failure_rationale:
            logger.info(f"   Failure rationale: {failure_rationale}")
            logger.info(f"   Error category: {error_category}")

        # Reset current tracking
        self.current_trajectory = None
        self.current_attempt = None
        self.trajectory_steps = []

        return trajectory_id

    def _query_code_patterns(
        self,
        component_type: str,
        context: str = ""
    ) -> List[StrategyNugget]:
        """
        Query ReasoningBank for relevant code patterns

        Args:
            component_type: Type of component (frontend, backend, database, config)
            context: Additional context for matching

        Returns:
            List of relevant strategy nuggets
        """
        search_query = f"{component_type} {context} code generation"

        try:
            strategies = self.reasoning_bank.search_strategies(
                task_context=search_query,
                top_n=3,
                min_win_rate=0.5  # Only use proven patterns
            )

            if self.current_attempt:
                self.current_attempt.patterns_queried.extend([s.strategy_id for s in strategies])

            if strategies:
                logger.info(f"🔍 Found {len(strategies)} proven patterns for {component_type}")
                for s in strategies:
                    logger.debug(f"   - {s.description} (win_rate: {s.win_rate:.2f})")
            else:
                logger.info(f"🔍 No proven patterns found for {component_type} (cold start)")

            return strategies
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"❌ Database connection error querying patterns: {e}")
            return []
        except ValueError as e:
            logger.error(f"❌ Invalid query parameters: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error querying patterns: {e}")
            return []

    def _store_successful_pattern(
        self,
        pattern_type: str,
        description: str,
        code_snippet: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Store successful code pattern in ReasoningBank

        Args:
            pattern_type: Type of pattern (frontend, backend, etc.)
            description: Human-readable description
            code_snippet: The actual code pattern
            metadata: Additional metadata

        Returns:
            Strategy ID
        """
        try:
            strategy_id = self.reasoning_bank.store_strategy(
                description=description,
                context=f"{pattern_type} code generation pattern",
                task_metadata={
                    "pattern_type": pattern_type,
                    "business_id": self.business_id,
                    **metadata
                },
                environment="Next.js 14 + React 18 + TypeScript",
                tools_used=["generate_" + pattern_type],
                outcome=OutcomeTag.SUCCESS,
                steps=[code_snippet],
                learned_from=[self.current_attempt.attempt_id if self.current_attempt else "unknown"]
            )

            logger.info(f"💾 Stored successful pattern: {pattern_type}")
            logger.debug(f"   Strategy ID: {strategy_id}")

            if self.current_attempt:
                self.current_attempt.patterns_used.append(strategy_id)

            return strategy_id
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"❌ Database connection error storing pattern: {e}")
            return ""
        except ValueError as e:
            logger.error(f"❌ Invalid pattern data: {e}")
            return ""
        except Exception as e:
            logger.error(f"❌ Unexpected error storing pattern: {e}")
            return ""

    async def build_from_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main build method with learning capabilities

        This is the core method that orchestrates the entire build process:
        1. Start trajectory recording
        2. Query ReasoningBank for proven patterns
        3. Generate code using patterns + agent intelligence
        4. Record all actions with reasoning
        5. Store successful patterns for future use
        6. Finalize trajectory in Replay Buffer

        Args:
            spec: Business specification dictionary

        Returns:
            Build result with metadata:
            {
                "success": bool,
                "files_generated": List[str],
                "patterns_used": List[str],
                "patterns_stored": List[str],
                "trajectory_id": str,
                "duration_seconds": float,
                "error_message": Optional[str]
            }
        """
        logger.info(f"🏗️  Starting build from specification")
        logger.info(f"   Business: {spec.get('business_name', 'Unknown')}")
        logger.info(f"   Description: {spec.get('business_description', 'No description')}")

        # Start trajectory recording
        task_description = f"Build {spec.get('business_name', 'application')} from specification"
        trajectory_id = self._start_trajectory(
            task_description=task_description,
            initial_state={"spec_id": spec.get("specification_id", "unknown")}
        )

        result = {
            "success": False,
            "files_generated": [],
            "patterns_used": [],
            "patterns_stored": [],
            "trajectory_id": trajectory_id,
            "duration_seconds": 0.0,
            "error_message": None
        }

        try:
            # Extract spec details
            app_name = spec.get("business_name", "App")
            features = spec.get("executive_summary", {}).get("core_features", [])
            tech_stack = spec.get("architecture", {}).get("tech_stack", {})

            # 1. FRONTEND GENERATION with pattern learning
            logger.info("\n📱 Generating frontend...")
            frontend_patterns = self._query_code_patterns("frontend", "React Next.js components")

            frontend_reasoning = (
                f"Generating frontend for {app_name} with features: {', '.join(features[:3])}. "
                f"Using {len(frontend_patterns)} proven patterns from ReasoningBank."
            )

            frontend_result = self.generate_frontend(
                app_name=app_name,
                features=features,
                pages=["Home", "Dashboard", "Settings"]
            )

            self._record_action(
                tool_name="generate_frontend",
                tool_args={"app_name": app_name, "features": features, "pages": ["Home", "Dashboard", "Settings"]},
                tool_result=frontend_result,
                agent_reasoning=frontend_reasoning
            )

            frontend_data = json.loads(frontend_result)
            result["files_generated"].extend(frontend_data.get("files", {}).keys())

            # Store successful pattern
            if frontend_data.get("file_count", 0) > 0:
                pattern_id = self._store_successful_pattern(
                    pattern_type="frontend",
                    description=f"Next.js frontend with {len(features)} features",
                    code_snippet=frontend_result[:500],  # Store sample
                    metadata={
                        "features_count": len(features),
                        "framework": "Next.js 14",
                        "file_count": frontend_data.get("file_count", 0)
                    }
                )
                result["patterns_stored"].append(pattern_id)

            # 2. BACKEND GENERATION with pattern learning
            logger.info("\n🔧 Generating backend...")
            backend_patterns = self._query_code_patterns("backend", "API routes FastAPI")

            backend_reasoning = (
                f"Generating backend API routes for {app_name}. "
                f"Using {len(backend_patterns)} proven patterns. "
                f"Auth required: True"
            )

            api_routes = ["tasks", "projects", "users", "analytics"]
            backend_result = self.generate_backend(
                app_name=app_name,
                api_routes=api_routes,
                auth_required=True
            )

            self._record_action(
                tool_name="generate_backend",
                tool_args={"app_name": app_name, "api_routes": api_routes, "auth_required": True},
                tool_result=backend_result,
                agent_reasoning=backend_reasoning
            )

            backend_data = json.loads(backend_result)
            result["files_generated"].extend(backend_data.get("files", {}).keys())

            # Store successful pattern
            if backend_data.get("file_count", 0) > 0:
                pattern_id = self._store_successful_pattern(
                    pattern_type="backend",
                    description=f"FastAPI backend with {len(api_routes)} routes",
                    code_snippet=backend_result[:500],
                    metadata={
                        "routes_count": len(api_routes),
                        "auth_enabled": True,
                        "file_count": backend_data.get("file_count", 0)
                    }
                )
                result["patterns_stored"].append(pattern_id)

            # 3. DATABASE GENERATION with pattern learning
            logger.info("\n🗄️  Generating database schema...")
            db_patterns = self._query_code_patterns("database", "PostgreSQL schema migrations")

            db_reasoning = (
                f"Generating database schema for {app_name}. "
                f"Using {len(db_patterns)} proven patterns. "
                f"Tables: Users, Projects, Tasks, Analytics"
            )

            tables = ["Users", "Projects", "Tasks", "Analytics"]
            database_result = self.generate_database(
                app_name=app_name,
                tables=tables,
                relationships=True
            )

            self._record_action(
                tool_name="generate_database",
                tool_args={"app_name": app_name, "tables": tables, "relationships": True},
                tool_result=database_result,
                agent_reasoning=db_reasoning
            )

            database_data = json.loads(database_result)
            result["files_generated"].extend(database_data.get("files", {}).keys())

            # Store successful pattern
            if database_data.get("file_count", 0) > 0:
                pattern_id = self._store_successful_pattern(
                    pattern_type="database",
                    description=f"PostgreSQL schema with {len(tables)} tables",
                    code_snippet=database_result[:500],
                    metadata={
                        "tables_count": len(tables),
                        "database": "PostgreSQL",
                        "file_count": database_data.get("file_count", 0)
                    }
                )
                result["patterns_stored"].append(pattern_id)

            # 4. CONFIG GENERATION with pattern learning
            logger.info("\n⚙️  Generating configuration...")
            config_patterns = self._query_code_patterns("config", "package.json tsconfig environment")

            config_reasoning = (
                f"Generating configuration files for {app_name}. "
                f"Using {len(config_patterns)} proven patterns. "
                f"Includes: package.json, tsconfig, env vars"
            )

            env_vars = [
                "DATABASE_URL",
                "REDIS_URL",
                "JWT_SECRET",
                "NEXT_PUBLIC_API_URL"
            ]
            config_result = self.generate_config(
                app_name=app_name,
                env_vars=env_vars
            )

            self._record_action(
                tool_name="generate_config",
                tool_args={"app_name": app_name, "env_vars": env_vars},
                tool_result=config_result,
                agent_reasoning=config_reasoning
            )

            config_data = json.loads(config_result)
            result["files_generated"].extend(config_data.get("files", {}).keys())

            # Store successful pattern
            if config_data.get("file_count", 0) > 0:
                pattern_id = self._store_successful_pattern(
                    pattern_type="config",
                    description=f"Next.js configuration with {len(env_vars)} env vars",
                    code_snippet=config_result[:500],
                    metadata={
                        "env_vars_count": len(env_vars),
                        "framework": "Next.js 14",
                        "file_count": config_data.get("file_count", 0)
                    }
                )
                result["patterns_stored"].append(pattern_id)

            # Build successful!
            result["success"] = True
            result["patterns_used"] = self.current_attempt.patterns_queried if self.current_attempt else []

            # Finalize trajectory with SUCCESS
            duration = time.time() - (self.current_attempt.start_time if self.current_attempt else time.time())
            result["duration_seconds"] = duration

            self._finalize_trajectory(
                outcome=OutcomeTag.SUCCESS,
                reward=1.0,  # Full reward for complete success
                metadata={
                    "files_generated": len(result["files_generated"]),
                    "patterns_used": len(result["patterns_used"]),
                    "patterns_stored": len(result["patterns_stored"]),
                    "spec_id": spec.get("specification_id", "unknown")
                }
            )

            logger.info(f"\n✅ Build completed successfully!")
            logger.info(f"   Files generated: {len(result['files_generated'])}")
            logger.info(f"   Patterns used: {len(result['patterns_used'])}")
            logger.info(f"   Patterns stored: {len(result['patterns_stored'])}")
            logger.info(f"   Duration: {duration:.2f}s")

        except (ConnectionError, TimeoutError) as e:
            # Database/network failure
            logger.error(f"\n❌ Build failed (database/network): {e}")
            result["error_message"] = f"Database/network error: {str(e)}"

            duration = time.time() - (self.current_attempt.start_time if self.current_attempt else time.time())
            result["duration_seconds"] = duration

            self._finalize_trajectory(
                outcome=OutcomeTag.FAILURE,
                reward=0.0,
                metadata={
                    "error_type": "connection",
                    "error": str(e),
                    "files_generated": len(result["files_generated"]),
                    "spec_id": spec.get("specification_id", "unknown")
                }
            )

        except ValueError as e:
            # Invalid specification data
            logger.error(f"\n❌ Build failed (invalid spec): {e}")
            result["error_message"] = f"Invalid specification: {str(e)}"

            duration = time.time() - (self.current_attempt.start_time if self.current_attempt else time.time())
            result["duration_seconds"] = duration

            self._finalize_trajectory(
                outcome=OutcomeTag.FAILURE,
                reward=0.0,
                metadata={
                    "error_type": "validation",
                    "error": str(e),
                    "files_generated": len(result["files_generated"]),
                    "spec_id": spec.get("specification_id", "unknown")
                }
            )

        except Exception as e:
            # Unexpected build failure
            logger.error(f"\n❌ Build failed (unexpected): {e}")
            result["error_message"] = str(e)

            duration = time.time() - (self.current_attempt.start_time if self.current_attempt else time.time())
            result["duration_seconds"] = duration

            self._finalize_trajectory(
                outcome=OutcomeTag.FAILURE,
                reward=0.0,
                metadata={
                    "error_type": "unexpected",
                    "error": str(e),
                    "files_generated": len(result["files_generated"]),
                    "spec_id": spec.get("specification_id", "unknown")
                }
            )

        return result

    # Original tool methods from BuilderAgent (unchanged)

    def generate_frontend(self, app_name: str, features: List[str], pages: List[str]) -> str:
        """
        Generate React/Next.js frontend code.

        Args:
            app_name: Name of the application
            features: List of features to implement
            pages: List of pages to create

        Returns:
            JSON string with frontend file structure and code
        """
        files = {}

        # Generate main app layout
        files["app/layout.tsx"] = f'''import type {{ Metadata }} from 'next'
import './globals.css'

export const metadata: Metadata = {{
  title: '{app_name}',
  description: 'Built with Genesis Agent System',
}}

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode
}}) {{
  return (
    <html lang="en">
      <body>{{children}}</body>
    </html>
  )
}}'''

        # Generate pages
        for page in pages:
            page_name = page.lower().replace(" ", "-")
            files[f"app/{page_name}/page.tsx"] = f'''export default function {page.replace(" ", "")}Page() {{
  return (
    <div className="min-h-screen p-8">
      <h1 className="text-4xl font-bold mb-4">{page}</h1>
      <p>Welcome to {page}</p>
    </div>
  )
}}'''

        # Generate components for features
        for feature in features:
            component_name = feature.replace(" ", "")
            files[f"components/{component_name}.tsx"] = f'''interface {component_name}Props {{
  // Add props here
}}

export function {component_name}(props: {component_name}Props) {{
  return (
    <div className="p-4 border rounded-lg">
      <h2 className="text-2xl font-semibold">{feature}</h2>
    </div>
  )
}}'''

        result = {
            "app_name": app_name,
            "framework": "Next.js 14 + React 18 + TypeScript",
            "files": files,
            "file_count": len(files),
            "features_implemented": features,
            "pages_created": pages,
            "created_at": datetime.now().isoformat()
        }

        return json.dumps(result, indent=2)

    def generate_backend(self, app_name: str, api_routes: List[str], auth_required: bool = True) -> str:
        """
        Generate API routes and backend logic.

        Args:
            app_name: Name of the application
            api_routes: List of API endpoints to create
            auth_required: Whether authentication is required

        Returns:
            JSON string with backend API files
        """
        files = {}

        # Generate API routes
        for route in api_routes:
            route_name = route.lower().replace(" ", "-")
            files[f"app/api/{route_name}/route.ts"] = f'''import {{ NextRequest, NextResponse }} from 'next/server'

export async function GET(request: NextRequest) {{
  try {{
    // Implement {route} GET logic
    return NextResponse.json({{
      message: '{route} endpoint',
      data: []
    }})
  }} catch (error) {{
    return NextResponse.json(
      {{ error: 'Failed to fetch {route}' }},
      {{ status: 500 }}
    )
  }}
}}

export async function POST(request: NextRequest) {{
  try {{
    const body = await request.json()
    // Implement {route} POST logic
    return NextResponse.json({{
      message: '{route} created',
      data: body
    }})
  }} catch (error) {{
    return NextResponse.json(
      {{ error: 'Failed to create {route}' }},
      {{ status: 500 }}
    )
  }}
}}'''

        # Generate auth middleware if required
        if auth_required:
            files["middleware.ts"] = '''import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth-token')

  if (!token && request.nextUrl.pathname.startsWith('/api')) {
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    )
  }

  return NextResponse.next()
}

export const config = {
  matcher: '/api/:path*',
}'''

        result = {
            "app_name": app_name,
            "files": files,
            "file_count": len(files),
            "api_routes": api_routes,
            "auth_enabled": auth_required,
            "created_at": datetime.now().isoformat()
        }

        return json.dumps(result, indent=2)

    def generate_database(self, app_name: str, tables: List[str], relationships: bool = True) -> str:
        """
        Generate database schemas and migrations.

        Args:
            app_name: Name of the application
            tables: List of database tables to create
            relationships: Whether to include table relationships

        Returns:
            JSON string with database schema files
        """
        files = {}

        # Generate Supabase schema
        schema_sql = "-- Database Schema for " + app_name + "\n\n"

        for table in tables:
            table_name = table.lower().replace(" ", "_")
            schema_sql += f'''-- {table} table
CREATE TABLE {table_name} (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Users can read own {table_name}"
  ON {table_name}
  FOR SELECT
  USING (auth.uid() = user_id);

'''

        files["supabase/migrations/001_initial_schema.sql"] = schema_sql

        # Generate TypeScript types
        types = "// Database Types\n\n"
        for table in tables:
            type_name = table.replace(" ", "")
            types += f'''export interface {type_name} {{
  id: string
  created_at: string
  updated_at: string
}}

'''

        files["types/database.ts"] = types

        result = {
            "app_name": app_name,
            "database": "Supabase (PostgreSQL)",
            "files": files,
            "file_count": len(files),
            "tables": tables,
            "row_level_security": True,
            "created_at": datetime.now().isoformat()
        }

        return json.dumps(result, indent=2)

    def generate_config(self, app_name: str, env_vars: List[str]) -> str:
        """
        Generate configuration files (package.json, tsconfig, env, etc.).

        Args:
            app_name: Name of the application
            env_vars: List of environment variables needed

        Returns:
            JSON string with configuration files
        """
        files = {}

        # package.json
        files["package.json"] = json.dumps({
            "name": app_name.lower().replace(" ", "-"),
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint"
            },
            "dependencies": {
                "next": "14.2.0",
                "react": "^18.3.0",
                "react-dom": "^18.3.0",
                "@supabase/supabase-js": "^2.39.0"
            },
            "devDependencies": {
                "@types/node": "^20",
                "@types/react": "^18",
                "@types/react-dom": "^18",
                "typescript": "^5",
                "tailwindcss": "^3.4.0",
                "autoprefixer": "^10.4.0",
                "postcss": "^8.4.0"
            }
        }, indent=2)

        # .env.example
        env_example = "\n".join([f"{var}=" for var in env_vars])
        files[".env.example"] = env_example

        # tsconfig.json
        files["tsconfig.json"] = json.dumps({
            "compilerOptions": {
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [{"name": "next"}],
                "paths": {
                    "@/*": ["./*"]
                }
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
            "exclude": ["node_modules"]
        }, indent=2)

        # tailwind.config.js
        files["tailwind.config.js"] = '''module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}'''

        result = {
            "app_name": app_name,
            "files": files,
            "file_count": len(files),
            "env_vars": env_vars,
            "created_at": datetime.now().isoformat()
        }

        return json.dumps(result, indent=2)

    def review_code(self, file_path: str, code_content: str) -> str:
        """
        Review code and provide quality suggestions.

        Args:
            file_path: Path to the file being reviewed
            code_content: Content of the code to review

        Returns:
            JSON string with code review feedback
        """
        issues = []
        suggestions = []

        # Basic static analysis
        if "any" in code_content:
            issues.append("Avoid using 'any' type - specify proper TypeScript types")

        if "console.log" in code_content:
            issues.append("Remove console.log statements before production")

        if "// TODO" in code_content or "// FIXME" in code_content:
            issues.append("Complete TODO/FIXME items")

        if not "try" in code_content and ("fetch" in code_content or "async" in code_content):
            issues.append("Add error handling (try/catch) for async operations")

        # Suggestions
        suggestions.append("Consider adding unit tests")
        suggestions.append("Add JSDoc comments for complex functions")
        suggestions.append("Ensure proper TypeScript types for all parameters")

        quality_score = max(0, 100 - (len(issues) * 10))

        result = {
            "file_path": file_path,
            "quality_score": quality_score,
            "issues_found": len(issues),
            "issues": issues,
            "suggestions": suggestions,
            "status": "pass" if quality_score >= 70 else "needs_improvement",
            "reviewed_at": datetime.now().isoformat()
        }

        return json.dumps(result, indent=2)

    # A2A Communication Interface
    def route_task(self, task_description: str, priority: float = 0.5) -> RoutingDecision:
        """
        Route task to appropriate model using DAAO

        Args:
            task_description: Description of the task
            priority: Task priority (0.0-1.0)

        Returns:
            RoutingDecision with model selection and cost estimate
        """
        task = {
            'id': f'enhancedbuilder-{{datetime.now().strftime("%Y%m%d%H%M%S")}}',
            'description': task_description,
            'priority': priority,
            'required_tools': []
        }

        decision = self.router.route_task(task, budget_conscious=True)

        logger.info(
            f"Task routed: {decision.reasoning}",
            extra={
                'agent': 'EnhancedBuilderAgent',
                'model': decision.model,
                'difficulty': decision.difficulty.value,
                'estimated_cost': decision.estimated_cost
            }
        )

        return decision

    def get_cost_metrics(self) -> Dict:
        """Get cumulative cost savings from DAAO and TUMIX"""
        if not self.refinement_history:
            return {
                'agent': 'EnhancedBuilderAgent',
                'tumix_sessions': 0,
                'tumix_savings_percent': 0.0,
                'message': 'No refinement sessions recorded yet'
            }

        tumix_savings = self.termination.estimate_cost_savings(
            [
                [r for r in session]
                for session in self.refinement_history
            ],
            cost_per_round=0.001
        )

        return {
            'agent': 'EnhancedBuilderAgent',
            'tumix_sessions': tumix_savings['sessions'],
            'tumix_baseline_rounds': tumix_savings['baseline_rounds'],
            'tumix_actual_rounds': tumix_savings['tumix_rounds'],
            'tumix_savings_percent': tumix_savings['savings_percent'],
            'tumix_total_saved': tumix_savings['savings'],
            'daao_info': 'DAAO routing automatically applied to all tasks'
        }

async def get_enhanced_builder_agent(business_id: str = "default") -> EnhancedBuilderAgent:
    """Factory function to create and initialize enhanced builder agent"""
    agent = EnhancedBuilderAgent(business_id=business_id)
    await agent.initialize()
    return agent
