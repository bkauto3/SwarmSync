"""
HALORouter: Hierarchical Agent Logic Orchestration
Based on HALO (arXiv:2505.13516)

Key Features:
- Logic-based declarative routing rules
- Explainable agent selection (traceable decisions)
- Capability-based matching
- Integration with TaskDAG for dependency-aware routing
- Support for Genesis 15-agent ensemble
- Agent authentication (VULN-002 fix)
- DAAO cost optimization (Phase 2 integration)
- CaseBank memory integration (Memento case-based reasoning)
"""
# Auto-load .env file for configuration
from infrastructure.load_env import load_genesis_env
load_genesis_env()

import logging
import os
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from infrastructure.task_dag import TaskDAG, Task, TaskStatus
from infrastructure.agent_auth_registry import AgentAuthRegistry, SecurityError

# WaltzRL Safety integration (optional)
try:
    from infrastructure.safety.waltzrl_wrapper import WaltzRLSafetyWrapper
    HAS_WALTZRL = True
except ImportError:
    try:
        from infrastructure.waltzrl_safety import WaltzRLSafety as WaltzRLSafetyWrapper
        HAS_WALTZRL = True
    except ImportError:
        HAS_WALTZRL = False
        WaltzRLSafetyWrapper = None

# Policy Cards and Capability Maps Integration (imported lazily to avoid circular imports)
# - Policy Cards: arXiv:2510.24383
# - Capability Maps: Pre-tool middleware validation

# CaseBank integration for learning from past routing decisions
try:
    from infrastructure.casebank import CaseBank, get_casebank
    HAS_CASEBANK = True
except ImportError:
    HAS_CASEBANK = False

# AgentScope Alias integration for dynamic agent identity resolution
try:
    from infrastructure.agentscope_alias import get_alias_registry, AliasRegistry
    HAS_ALIAS_REGISTRY = True
except ImportError:
    HAS_ALIAS_REGISTRY = False

logger = logging.getLogger(__name__)


@dataclass
class RoutingRule:
    """
    Declarative routing rule: IF condition THEN agent

    Example:
        RoutingRule(
            rule_id="deploy_to_cloud",
            condition={"task_type": "deploy", "platform": "cloud"},
            target_agent="deploy_agent",
            priority=10,
            explanation="Cloud deployment tasks route to Deploy Agent"
        )
    """
    rule_id: str
    condition: Dict[str, Any]  # Matching criteria
    target_agent: str
    priority: int = 0  # Higher priority = checked first
    explanation: str = ""  # Human-readable reasoning


@dataclass
class AgentCapability:
    """
    Agent capability profile for matching

    Defines what an agent can do, its cost tier, and historical success rate.
    Used for capability-based matching when no declarative rule matches.
    """
    agent_name: str
    supported_task_types: List[str]
    skills: List[str]
    cost_tier: str  # "cheap" (Flash), "medium" (GPT-4o), "expensive" (Claude)
    success_rate: float = 0.0  # Historical success rate (0.0-1.0)
    max_concurrent_tasks: int = 10  # Load balancing


@dataclass
class RoutingPlan:
    """
    Complete routing plan for a DAG

    Contains:
    - assignments: task_id -> agent_name mapping
    - explanations: task_id -> reasoning for selection
    - unassigned_tasks: tasks with no matching agent
    - metadata: Optional optimization metadata (DAAO Phase 2)
    """
    assignments: Dict[str, str] = field(default_factory=dict)  # task_id -> agent_name
    explanations: Dict[str, str] = field(default_factory=dict)  # task_id -> explanation
    unassigned_tasks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)  # DAAO optimization metadata

    def is_complete(self) -> bool:
        """Check if all tasks are assigned"""
        return len(self.unassigned_tasks) == 0

    def get_agent_workload(self) -> Dict[str, int]:
        """Get task count per agent"""
        workload = {}
        for agent in self.assignments.values():
            workload[agent] = workload.get(agent, 0) + 1
        return workload

@dataclass
class TeamValidationResult:
    """
    Result of validating a proposed multi-agent team.

    Attributes:
        is_valid: Whether the team satisfies HALO constraints.
        reasons: Human-readable explanations for any validation failures.
        required_capabilities: Capabilities the team was expected to satisfy.
    """

    is_valid: bool
    reasons: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)

class HALORouter:
    """
    Logic-based hierarchical agent routing

    Implements HALO paper's three-level architecture:
    1. High-Level Planning: Analyzes DAG structure
    2. Mid-Level Role Design: Selects agents via logic rules
    3. Low-Level Inference: Prepares for execution

    Routing Algorithm:
    1. Apply declarative rules (priority order)
    2. Fall back to capability-based matching
    3. Consider agent workload for load balancing
    4. Log explainable reasoning for every decision
    """

    def __init__(
        self,
        agent_registry: Optional[Dict[str, AgentCapability]] = None,
        auth_registry: Optional[AgentAuthRegistry] = None,
        enable_cost_optimization: bool = False,
        cost_profiler = None,
        daao_optimizer = None,
        enable_casebank: bool = True,
        model_registry = None,
        middlewares: Optional[List] = None
    ):
        """
        Initialize HALORouter

        Args:
            agent_registry: Optional custom agent registry (defaults to Genesis 15-agent ensemble)
            auth_registry: Optional authentication registry (VULN-002 fix)
            enable_cost_optimization: Enable DAAO cost optimization (Phase 2 feature)
            cost_profiler: Optional CostProfiler instance
            daao_optimizer: Optional DAAOOptimizer instance
            enable_casebank: Enable case-based learning from past routing decisions
            model_registry: Optional ModelRegistry instance for fine-tuned models
            middlewares: Optional list of AgentMiddleware instances (defaults to all middleware)
        """
        self.agent_registry = agent_registry or self._get_genesis_15_agents()
        self.routing_rules = self._initialize_routing_rules()
        self.agent_workload: Dict[str, int] = {agent: 0 for agent in self.agent_registry.keys()}

        # Middleware integration (NEW: Task 7 - Phase 5)
        self.middlewares = middlewares
        if self.middlewares is None:
            # Default: Load all middleware
            self._initialize_default_middlewares()

        logger.info(f"HALORouter initialized with {len(self.middlewares) if self.middlewares else 0} middleware")

        # VULN-002 FIX: Agent authentication
        self.auth_registry = auth_registry or AgentAuthRegistry()

        # DAAO Phase 2: Cost optimization
        self.enable_cost_optimization = enable_cost_optimization
        self.cost_profiler = cost_profiler
        self.daao_optimizer = daao_optimizer

        # Fine-tuned model registry integration
        self.model_registry = model_registry
        if self.model_registry:
            logger.info("ModelRegistry integrated with HALO router")

        # Vertex AI routing integration (NEW: Production fine-tuned models)
        self.use_vertex_ai = os.getenv('ENABLE_VERTEX_AI', 'false').lower() == 'true'
        self.vertex_router = None
        if self.use_vertex_ai:
            try:
                from infrastructure.vertex_router import VertexModelRouter
                self.vertex_router = VertexModelRouter(
                    project_id=os.getenv('VERTEX_PROJECT_ID', 'genesis-finetuning-prod'),
                    location=os.getenv('VERTEX_LOCATION', 'us-central1'),
                    enable_cost_tracking=True,
                    enable_latency_tracking=True
                )
                
                # Register 6 fine-tuned agent endpoints
                # NOTE: Only register if env var is set AND is a valid endpoint format
                # Invalid endpoints cause "Resource X is not a valid resource id" errors
                model_mappings = {
                    # "qa_agent": os.getenv('GENESIS_QA_MODEL'),  # TODO: Fix endpoint format
                    "support_agent": os.getenv('GENESIS_SUPPORT_MODEL'),
                    "analyst_agent": os.getenv('GENESIS_ANALYST_MODEL'),
                    "legal_agent": os.getenv('GENESIS_LEGAL_MODEL'),
                    "content_agent": os.getenv('GENESIS_CONTENT_MODEL'),
                    "security_agent": os.getenv('GENESIS_SECURITY_MODEL'),
                }
                
                registered_count = 0
                for agent_role, model_resource in model_mappings.items():
                    if model_resource:
                        self.vertex_router.register_endpoint(agent_role, model_resource, weight=100)
                        registered_count += 1
                
                logger.info(f"✅ Vertex AI router enabled ({registered_count} fine-tuned models registered)")
            except ImportError as e:
                logger.warning(f"Vertex AI router requested but not available: {e}")
                self.use_vertex_ai = False
            except Exception as e:
                logger.error(f"Vertex AI router initialization failed: {e}")
                self.use_vertex_ai = False

        # CaseBank integration: Learn from past routing successes/failures
        self.enable_casebank = enable_casebank and HAS_CASEBANK
        if self.enable_casebank:
            self.casebank = get_casebank()
            logger.info("CaseBank enabled for HALO router")
        else:
            self.casebank = None

        # AgentScope Alias integration: Dynamic agent identity resolution
        self.alias_registry: Optional[AliasRegistry] = None
        if HAS_ALIAS_REGISTRY:
            try:
                self.alias_registry = get_alias_registry()
                logger.info("AgentScope alias registry enabled for dynamic agent resolution")
            except Exception as e:
                logger.warning(f"Failed to initialize alias registry: {e}")

        # OPTIMIZATION 1: Cache sorted rules (avoid re-sorting on every task)
        self._sorted_rules_cache = sorted(self.routing_rules, key=lambda r: r.priority, reverse=True)

        # OPTIMIZATION 2: Build task_type -> rules index for O(1) lookups
        # Sort rules by priority first
        self._task_type_index: Dict[str, List[RoutingRule]] = {}
        for rule in self._sorted_rules_cache:
            task_type = rule.condition.get("task_type")
            if task_type:
                if task_type not in self._task_type_index:
                    self._task_type_index[task_type] = []
                self._task_type_index[task_type].append(rule)

        # OPTIMIZATION 3: Build task_type -> agents index for capability matching
        self._capability_index: Dict[str, List[tuple]] = {}
        for agent_name, agent_cap in self.agent_registry.items():
            for task_type in agent_cap.supported_task_types:
                if task_type not in self._capability_index:
                    self._capability_index[task_type] = []
                self._capability_index[task_type].append((agent_name, agent_cap))

        # WaltzRL safety integration
        self.enable_waltzrl = os.getenv("ENABLE_WALTZRL", "true").lower() == "true" and HAS_WALTZRL
        self._safety_wrapper = None
        if self.enable_waltzrl and HAS_WALTZRL:
            try:
                self._safety_wrapper = WaltzRLSafetyWrapper(feedback_only_mode=False)
                logger.info("WaltzRL safety wrapper enabled for HALO router")
            except Exception as e:
                logger.warning(f"Failed to initialize WaltzRL safety wrapper: {e}")
                self.enable_waltzrl = False
        elif not HAS_WALTZRL:
            logger.debug("WaltzRL safety wrapper not available - running without safety checks (expected in Railway)")

        # Gemini fallback client cache
        self._gemini_client = None
        self._gemini_generate_config_cls = None
        self._gemini_model = os.getenv("GENESIS_HALO_GEMINI_MODEL", "gemini-2.0-flash")

        self.logger = logger
        self.logger.info(
            f"Initialized HALORouter with {len(self.agent_registry)} agents "
            f"(cost_optimization={'enabled' if enable_cost_optimization else 'disabled'}, "
            f"middlewares={len(self.middlewares) if self.middlewares else 0})"
        )

    def _initialize_default_middlewares(self) -> None:
        """
        Initialize default middleware stack.

        Default stack (in execution order):
        1. PolicyCardMiddleware: Enforce policy cards
        2. CapabilityMapMiddleware: Validate capabilities
        3. ToolRMMiddleware: Score tool executions

        This can be overridden by passing custom middlewares to __init__.
        """
        try:
            from infrastructure.middleware import (
                PolicyCardMiddleware,
                CapabilityMapMiddleware,
                ToolRMMiddleware,
            )

            self.middlewares = [
                PolicyCardMiddleware(policy_dir=".policy_cards"),
                CapabilityMapMiddleware(maps_dir="maps/capabilities"),
                ToolRMMiddleware(
                    reasoning_bank_dir="data/reasoning_bank",
                    enable_reflection=True,
                ),
            ]
            logger.info("✅ Default middleware stack initialized (Policy + Capability + ToolRM)")
        except ImportError as e:
            logger.warning(f"Failed to load middleware: {e}, running without middleware")
            self.middlewares = []

    def validate_team_composition(
        self,
        agent_names: List[str],
        task_type: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
        required_security_level: str = "standard"
    ) -> TeamValidationResult:
        """
        Validate a proposed team composition against HALO constraints.

        Checks performed:
            - Agents exist in registry and authentication store
            - No duplicate agents
            - Claimed capabilities cover required capabilities
            - Security-sensitive tasks include appropriate agents
        """
        reasons: List[str] = []
        required_capabilities = required_capabilities or []

        if not agent_names:
            reasons.append("Team must include at least one agent.")
            return TeamValidationResult(False, reasons, required_capabilities)

        # Duplicate detection
        if len(set(agent_names)) != len(agent_names):
            reasons.append("Duplicate agents detected in team.")

        # Capability aggregation
        available_capabilities: List[str] = []

        for agent_name in agent_names:
            capability = self.agent_registry.get(agent_name)
            if capability is None:
                reasons.append(f"Unknown agent '{agent_name}' not registered in HALO.")
                continue

            # Authentication check (if registry available)
            if not self.auth_registry.is_registered(agent_name):
                reasons.append(f"Agent '{agent_name}' is not authenticated with HALO.")

            available_capabilities.extend(capability.skills)

        # Required capabilities coverage
        missing = sorted({cap for cap in required_capabilities if cap not in available_capabilities})
        if missing:
            reasons.append(
                "Team missing required capabilities: " + ", ".join(missing)
            )

        # Security requirements
        security_required = required_security_level.lower() == "high" or (
            task_type and any(keyword in task_type.lower() for keyword in ("finance", "security", "compliance"))
        )
        if security_required and "security_agent" not in agent_names:
            reasons.append("High-security task requires inclusion of security_agent.")

        return TeamValidationResult(len(reasons) == 0, reasons, required_capabilities)

    def _get_genesis_15_agents(self) -> Dict[str, AgentCapability]:
        """
        Get Genesis 15-agent registry

        Based on CLAUDE.md architecture:
        - Spec/Architect agents: Planning & design
        - Builder agents: Implementation
        - QA/Test agents: Validation
        - Deploy agents: Infrastructure
        - Marketing agents: Go-to-market
        - Support agents: Customer service
        - Analytics agents: Monitoring
        - Security agents: Vulnerability scanning
        """
        return {
            # Design & Planning (cheap, fast)
            "spec_agent": AgentCapability(
                agent_name="spec_agent",
                supported_task_types=["design", "requirements", "architecture", "planning"],
                skills=["specification", "planning", "requirements_analysis"],
                cost_tier="cheap",
                success_rate=0.85
            ),
            "architect_agent": AgentCapability(
                agent_name="architect_agent",
                supported_task_types=["architecture", "system_design", "technical_spec"],
                skills=["system_design", "architecture", "scalability"],
                cost_tier="medium",
                success_rate=0.88
            ),

            # Implementation (medium cost, Claude for code)
            "builder_agent": AgentCapability(
                agent_name="builder_agent",
                supported_task_types=["implement", "code", "build", "develop", "generic", "api_call", "file_write"],
                skills=["coding", "debugging", "refactoring"],
                cost_tier="medium",
                success_rate=0.82
            ),
            "frontend_agent": AgentCapability(
                agent_name="frontend_agent",
                supported_task_types=["frontend", "ui", "design_implementation"],
                skills=["react", "vue", "css", "javascript"],
                cost_tier="medium",
                success_rate=0.80
            ),
            "backend_agent": AgentCapability(
                agent_name="backend_agent",
                supported_task_types=["backend", "api", "database"],
                skills=["python", "node", "sql", "api_design"],
                cost_tier="medium",
                success_rate=0.83
            ),

            # Testing & QA (cheap, high volume)
            "qa_agent": AgentCapability(
                agent_name="qa_agent",
                supported_task_types=["test", "validation", "qa", "quality_assurance", "test_run"],
                skills=["testing", "test_automation", "quality_assurance"],
                cost_tier="cheap",
                success_rate=0.87
            ),
            "security_agent": AgentCapability(
                agent_name="security_agent",
                supported_task_types=["security", "vulnerability_scan", "penetration_test"],
                skills=["security", "vulnerability_analysis", "compliance"],
                cost_tier="medium",
                success_rate=0.90
            ),

            # Infrastructure & Deployment (medium cost)
            "deploy_agent": AgentCapability(
                agent_name="deploy_agent",
                supported_task_types=["deploy", "infrastructure", "devops"],
                skills=["devops", "cloud", "kubernetes", "ci_cd"],
                cost_tier="medium",
                success_rate=0.84
            ),
            "monitoring_agent": AgentCapability(
                agent_name="monitoring_agent",
                supported_task_types=["monitor", "observability", "metrics"],
                skills=["monitoring", "alerting", "performance_analysis"],
                cost_tier="cheap",
                success_rate=0.86
            ),

            # Go-to-Market (cheap, content generation)
            "marketing_agent": AgentCapability(
                agent_name="marketing_agent",
                supported_task_types=["marketing", "promotion", "content"],
                skills=["marketing", "advertising", "content_creation"],
                cost_tier="cheap",
                success_rate=0.78
            ),
            "sales_agent": AgentCapability(
                agent_name="sales_agent",
                supported_task_types=["sales", "outreach", "lead_generation"],
                skills=["sales", "outreach", "prospecting"],
                cost_tier="cheap",
                success_rate=0.75
            ),

            # Customer Success (cheap, conversational)
            "support_agent": AgentCapability(
                agent_name="support_agent",
                supported_task_types=["support", "customer_service", "help"],
                skills=["customer_support", "troubleshooting", "documentation"],
                cost_tier="cheap",
                success_rate=0.82
            ),

            # Analytics & Optimization (medium cost, data analysis)
            "analytics_agent": AgentCapability(
                agent_name="analytics_agent",
                supported_task_types=["analytics", "reporting", "data_analysis"],
                skills=["data_analysis", "reporting", "visualization"],
                cost_tier="medium",
                success_rate=0.85
            ),

            # Research & Discovery (medium cost, deep reasoning)
            "research_agent": AgentCapability(
                agent_name="research_agent",
                supported_task_types=["research", "discovery", "investigation"],
                skills=["research", "analysis", "competitive_intelligence"],
                cost_tier="medium",
                success_rate=0.81
            ),

            # Financial Operations (medium cost, precision required)
            "finance_agent": AgentCapability(
                agent_name="finance_agent",
                supported_task_types=["finance", "accounting", "budgeting"],
                skills=["finance", "accounting", "budgeting", "pricing"],
                cost_tier="medium",
                success_rate=0.88
            ),

            # Domain Registration & DNS Management (cheap, infrastructure)
            "domain_name_agent": AgentCapability(
                agent_name="domain_name_agent",
                supported_task_types=["domain_registration", "domain_search", "dns_config"],
                skills=["domain_search", "domain_register", "dns_management", "github_pages_config"],
                cost_tier="cheap",  # $10-50 per domain registration
                success_rate=0.0,  # Will learn over time
                max_concurrent_tasks=5  # Can handle multiple domain checks concurrently
            ),

            # Self-Improvement & Evolution (expensive, meta-programming)
            "darwin_agent": AgentCapability(
                agent_name="darwin_agent",
                supported_task_types=["evolution", "improve_agent", "fix_bug", "optimize"],
                skills=["self_improvement", "code_generation", "benchmark_validation", "agent_evolution", "meta_programming"],
                cost_tier="expensive",  # Uses GPT-4o/Claude for meta-programming
                success_rate=0.0,  # Will learn over time
                max_concurrent_tasks=3  # Evolution is resource-intensive
            ),
        }

    def _initialize_routing_rules(self) -> List[RoutingRule]:
        """
        Define declarative routing rules

        Rules are checked in priority order (highest first).
        Rules match on task_type and optional metadata fields.

        Example rule logic:
        - IF task_type="deploy" AND platform="cloud" THEN deploy_agent
        - IF task_type="implement" AND language="python" THEN backend_agent
        """
        return [
            # Design & Planning Rules
            RoutingRule(
                rule_id="rule_design",
                condition={"task_type": "design"},
                target_agent="spec_agent",
                priority=10,
                explanation="Design tasks route to Spec Agent (requirements, architecture)"
            ),
            RoutingRule(
                rule_id="rule_architecture",
                condition={"task_type": "architecture"},
                target_agent="architect_agent",
                priority=10,
                explanation="Architecture tasks route to Architect Agent (system design)"
            ),
            RoutingRule(
                rule_id="rule_requirements",
                condition={"task_type": "requirements"},
                target_agent="spec_agent",
                priority=10,
                explanation="Requirements gathering routes to Spec Agent"
            ),

            # Implementation Rules
            RoutingRule(
                rule_id="rule_implement",
                condition={"task_type": "implement"},
                target_agent="builder_agent",
                priority=10,
                explanation="Implementation tasks route to Builder Agent (coding)"
            ),
            RoutingRule(
                rule_id="rule_frontend",
                condition={"task_type": "frontend"},
                target_agent="frontend_agent",
                priority=15,
                explanation="Frontend tasks route to Frontend Agent (UI/UX)"
            ),
            RoutingRule(
                rule_id="rule_backend",
                condition={"task_type": "backend"},
                target_agent="backend_agent",
                priority=15,
                explanation="Backend tasks route to Backend Agent (API/DB)"
            ),
            RoutingRule(
                rule_id="rule_code",
                condition={"task_type": "code"},
                target_agent="builder_agent",
                priority=10,
                explanation="Generic code tasks route to Builder Agent"
            ),

            # Testing Rules
            RoutingRule(
                rule_id="rule_test",
                condition={"task_type": "test"},
                target_agent="qa_agent",
                priority=10,
                explanation="Testing tasks route to QA Agent (validation)"
            ),
            RoutingRule(
                rule_id="rule_security",
                condition={"task_type": "security"},
                target_agent="security_agent",
                priority=10,
                explanation="Security tasks route to Security Agent (vulnerability scanning)"
            ),

            # Infrastructure Rules
            RoutingRule(
                rule_id="rule_deploy",
                condition={"task_type": "deploy"},
                target_agent="deploy_agent",
                priority=10,
                explanation="Deployment tasks route to Deploy Agent (infrastructure)"
            ),
            RoutingRule(
                rule_id="rule_infrastructure",
                condition={"task_type": "infrastructure"},
                target_agent="deploy_agent",
                priority=10,
                explanation="Infrastructure tasks route to Deploy Agent (DevOps)"
            ),
            RoutingRule(
                rule_id="rule_monitoring",
                condition={"task_type": "monitor"},
                target_agent="monitoring_agent",
                priority=10,
                explanation="Monitoring tasks route to Monitoring Agent (observability)"
            ),
            RoutingRule(
                rule_id="rule_domain_registration",
                condition={"task_type": "domain_registration"},
                target_agent="domain_name_agent",
                priority=10,
                explanation="Domain registration tasks route to Domain Name Agent"
            ),
            RoutingRule(
                rule_id="rule_domain_search",
                condition={"task_type": "domain_search"},
                target_agent="domain_name_agent",
                priority=10,
                explanation="Domain search/availability tasks route to Domain Name Agent"
            ),
            RoutingRule(
                rule_id="rule_dns_config",
                condition={"task_type": "dns_config"},
                target_agent="domain_name_agent",
                priority=10,
                explanation="DNS configuration tasks route to Domain Name Agent"
            ),

            # Marketing Rules
            RoutingRule(
                rule_id="rule_marketing",
                condition={"task_type": "marketing"},
                target_agent="marketing_agent",
                priority=10,
                explanation="Marketing tasks route to Marketing Agent (promotion)"
            ),
            RoutingRule(
                rule_id="rule_sales",
                condition={"task_type": "sales"},
                target_agent="sales_agent",
                priority=10,
                explanation="Sales tasks route to Sales Agent (lead generation)"
            ),

            # Support Rules
            RoutingRule(
                rule_id="rule_support",
                condition={"task_type": "support"},
                target_agent="support_agent",
                priority=10,
                explanation="Support tasks route to Support Agent (customer service)"
            ),

            # Analytics Rules
            RoutingRule(
                rule_id="rule_analytics",
                condition={"task_type": "analytics"},
                target_agent="analytics_agent",
                priority=10,
                explanation="Analytics tasks route to Analytics Agent (reporting)"
            ),

            # Research Rules
            RoutingRule(
                rule_id="rule_research",
                condition={"task_type": "research"},
                target_agent="research_agent",
                priority=10,
                explanation="Research tasks route to Research Agent (discovery)"
            ),

            # Finance Rules
            RoutingRule(
                rule_id="rule_finance",
                condition={"task_type": "finance"},
                target_agent="finance_agent",
                priority=10,
                explanation="Finance tasks route to Finance Agent (accounting)"
            ),

            # Atomic Task Types
            RoutingRule(
                rule_id="rule_api_call",
                condition={"task_type": "api_call"},
                target_agent="builder_agent",
                priority=15,
                explanation="API call tasks route to Builder Agent (execution)"
            ),
            RoutingRule(
                rule_id="rule_file_write",
                condition={"task_type": "file_write"},
                target_agent="builder_agent",
                priority=15,
                explanation="File write tasks route to Builder Agent (file operations)"
            ),
            RoutingRule(
                rule_id="rule_test_run",
                condition={"task_type": "test_run"},
                target_agent="qa_agent",
                priority=15,
                explanation="Test execution routes to QA Agent (testing)"
            ),

            # Generic/Fallback Rules
            RoutingRule(
                rule_id="rule_generic",
                condition={"task_type": "generic"},
                target_agent="builder_agent",
                priority=5,
                explanation="Generic tasks route to Builder Agent as default handler"
            ),

            # Darwin Evolution Rules (SE-Darwin Integration)
            RoutingRule(
                rule_id="evolution_general",
                condition={"task_type": "evolution"},
                target_agent="darwin_agent",
                priority=20,
                explanation="General evolution tasks route to Darwin for self-improvement"
            ),
            RoutingRule(
                rule_id="evolution_agent_improvement",
                condition={"task_type": "improve_agent"},
                target_agent="darwin_agent",
                priority=20,
                explanation="Agent improvement requests route to Darwin"
            ),
            RoutingRule(
                rule_id="evolution_bug_fix",
                condition={"task_type": "fix_bug", "target": "agent_code"},
                target_agent="darwin_agent",
                priority=15,
                explanation="Agent bug fixes route to Darwin for code evolution"
            ),
            RoutingRule(
                rule_id="evolution_performance",
                condition={"task_type": "optimize", "target": "agent_performance"},
                target_agent="darwin_agent",
                priority=15,
                explanation="Agent performance optimization routes to Darwin"
            ),
        ]

    async def route_tasks(
        self,
        dag_or_tasks: Union[TaskDAG, List[Task]],
        available_agents: Optional[List[str]] = None,
        agent_tokens: Optional[Dict[str, str]] = None,
        optimization_constraints = None
    ) -> RoutingPlan:
        """
        Route all tasks in DAG to optimal agents

        Algorithm (with DAAO Phase 2 integration):
        1. TYPE CONVERSION: Accept TaskDAG or List[Task] for API flexibility
        2. VERIFY agent identities (VULN-002 fix)
        3. For each task in DAG (topological order - respects dependencies)
        4. Apply routing rules (priority order)
        5. If no rule matches, use capability matching
        6. Consider agent workload for load balancing
        7. [PHASE 2] Apply DAAO cost optimization (if enabled)
        8. If no agent found, mark as unassigned
        9. Log explanation for each decision (EXPLAINABILITY)

        Args:
            dag_or_tasks: Either a TaskDAG object or a list of Task objects
            available_agents: Optional list of available agent names (defaults to all)
            agent_tokens: Optional dict of agent_name -> auth_token (VULN-002 fix)
            optimization_constraints: Optional DAAO optimization constraints (Phase 2)

        Returns:
            RoutingPlan with assignments, explanations, and unassigned tasks

        Raises:
            SecurityError: If agent authentication fails
            TypeError: If dag_or_tasks is neither TaskDAG nor List[Task]
        """
        # TYPE CONVERSION: Normalize input to TaskDAG
        if isinstance(dag_or_tasks, TaskDAG):
            dag = dag_or_tasks
        elif isinstance(dag_or_tasks, list):
            # Convert List[Task] to TaskDAG
            dag = TaskDAG()
            for task in dag_or_tasks:
                if not isinstance(task, Task):
                    raise TypeError(f"Expected Task object, got {type(task)}")
                dag.add_task(task)
        else:
            raise TypeError(
                f"Expected TaskDAG or List[Task], got {type(dag_or_tasks).__name__}. "
                f"Usage: route_tasks(dag) or route_tasks([task1, task2]) or route_tasks(dag.get_all_tasks())"
            )

        self.logger.info(f"Routing {len(dag)} tasks from DAG")

        available_agents = available_agents or list(self.agent_registry.keys())

        # VULN-002 FIX: Verify all agents are authenticated
        if agent_tokens:
            self._verify_agents(available_agents, agent_tokens)

        routing_plan = RoutingPlan()

        # Reset workload tracking
        self.agent_workload = {agent: 0 for agent in self.agent_registry.keys()}

        # Process tasks in topological order (respects dependencies)
        try:
            task_order = dag.topological_sort()
        except (ValueError, Exception) as e:
            # Catch both ValueError from our DAG and NetworkXUnfeasible from networkx
            self.logger.error(f"DAG has cycles or invalid structure: {e}")
            return routing_plan

        for task_id in task_order:
            task = dag.tasks[task_id]

            # Skip if already completed
            if task.status == TaskStatus.COMPLETED:
                self.logger.debug(f"Skipping completed task {task_id}")
                continue

            # Try routing logic
            agent, explanation = self._apply_routing_logic(task, available_agents)

            if agent:
                routing_plan.assignments[task_id] = agent
                routing_plan.explanations[task_id] = explanation
                self.agent_workload[agent] += 1

                # Update task assignment
                dag.tasks[task_id].agent_assigned = agent

                self.logger.info(f"Routed {task_id} → {agent}: {explanation}")
            else:
                routing_plan.unassigned_tasks.append(task_id)
                self.logger.warning(f"No agent found for {task_id} (type={task.task_type})")

        # PHASE 2: Apply DAAO cost optimization (if enabled)
        if self.enable_cost_optimization and self.daao_optimizer and routing_plan.assignments:
            try:
                self.logger.info("Applying DAAO cost optimization...")
                optimized_plan = await self.daao_optimizer.optimize_routing_plan(
                    initial_plan=routing_plan.assignments,
                    dag=dag,
                    constraints=optimization_constraints
                )

                # Update routing plan with optimized assignments
                original_assignments = routing_plan.assignments.copy()
                routing_plan.assignments = optimized_plan.assignments

                # Update explanations for changed assignments
                changes = 0
                for task_id, optimized_agent in optimized_plan.assignments.items():
                    original_agent = original_assignments.get(task_id)
                    if original_agent != optimized_agent:
                        changes += 1
                        routing_plan.explanations[task_id] = (
                            f"DAAO optimized: {original_agent} → {optimized_agent} "
                            f"(cost saving: ${optimized_plan.cost_savings:.4f})"
                        )

                # Add optimization metadata to routing plan
                routing_plan.metadata["daao_optimized"] = True
                routing_plan.metadata["cost_savings"] = optimized_plan.cost_savings
                routing_plan.metadata["estimated_cost"] = optimized_plan.estimated_cost
                routing_plan.metadata["changes_made"] = changes

                self.logger.info(
                    f"DAAO optimization complete: {changes} assignments changed, "
                    f"saved ${optimized_plan.cost_savings:.4f} "
                    f"({optimized_plan.optimization_details.get('savings_pct', 0):.1f}%)"
                )

            except Exception as e:
                self.logger.error(f"DAAO optimization failed: {e}, using baseline routing")

        # Log final routing statistics
        self._log_routing_stats(routing_plan)

        # NEW: Integrate with ToolRM for tool usage tracking
        self._integrate_toolrm(routing_plan)

        return routing_plan

    def _apply_routing_logic(
        self,
        task: Task,
        available_agents: List[str]
    ) -> Tuple[Optional[str], str]:
        """
        Apply routing rules to select agent

        Priority order:
        1. Declarative rules (highest priority first)
        2. Capability-based matching
        3. Load balancing consideration

        Returns:
            (agent_name, explanation) or (None, "reason")

        OPTIMIZATIONS:
        - Use pre-cached sorted rules (avoid re-sorting)
        - Use task_type index for O(1) rule lookup
        - Use capability index for O(1) agent lookup
        - Early exit on first match
        """

        # OPTIMIZATION 4: Use task_type index for fast rule lookup (O(1) instead of O(n))
        task_type = task.task_type
        candidate_rules = self._task_type_index.get(task_type, [])

        # Step 1: Try declarative rules using index (much faster)
        for rule in candidate_rules:
            if self._rule_matches_fast(rule, task):
                if rule.target_agent in available_agents:
                    # Check if agent is overloaded
                    agent_cap = self.agent_registry[rule.target_agent]
                    if self.agent_workload[rule.target_agent] < agent_cap.max_concurrent_tasks:
                        return rule.target_agent, f"Rule {rule.rule_id}: {rule.explanation}"
                    # else: continue to next rule or fallback

        # Step 1.5: Try alias registry resolution (if available)
        if self.alias_registry:
            try:
                resolved_agent = self.alias_registry.resolve_agent_for_task(
                    task_type=task_type,
                    required_capabilities=task.metadata.get("required_capabilities")
                )
                if resolved_agent and resolved_agent in available_agents:
                    agent_cap = self.agent_registry.get(resolved_agent)
                    if agent_cap and self.agent_workload[resolved_agent] < agent_cap.max_concurrent_tasks:
                        return (
                            resolved_agent,
                            f"Alias registry resolution: {resolved_agent} matched via role={task_type}"
                        )
            except Exception as e:
                self.logger.debug(f"Alias registry resolution failed: {e}")

        # Step 2: Capability-based matching using index (O(1) instead of O(n))
        candidate_agents_from_index = self._capability_index.get(task_type, [])

        # Filter by availability and workload
        candidate_agents = [
            (agent_name, agent_cap)
            for agent_name, agent_cap in candidate_agents_from_index
            if agent_name in available_agents
            and self.agent_workload[agent_name] < agent_cap.max_concurrent_tasks
        ]

        if candidate_agents:
            # Select best candidate (highest success rate, then lowest workload)
            best_agent = max(
                candidate_agents,
                key=lambda x: (x[1].success_rate, -self.agent_workload[x[0]])
            )
            agent_name, agent_cap = best_agent
            return (
                agent_name,
                f"Capability match: {agent_name} supports {task.task_type} "
                f"(success_rate={agent_cap.success_rate:.2f}, workload={self.agent_workload[agent_name]})"
            )

        # Step 3: No match found
        return None, f"No matching agent for task_type={task.task_type}"

    def _rule_matches(self, rule: RoutingRule, task: Task) -> bool:
        """
        Check if routing rule matches task

        A rule matches if ALL conditions are satisfied:
        - condition["task_type"] matches task.task_type
        - All other condition keys match task.metadata values
        """
        for key, value in rule.condition.items():
            if key == "task_type":
                if task.task_type != value:
                    return False
            elif key in task.metadata:
                if task.metadata[key] != value:
                    return False
            else:
                # Condition key not found in task metadata
                return False
        return True

    def _rule_matches_fast(self, rule: RoutingRule, task: Task) -> bool:
        """
        OPTIMIZATION 5: Fast rule matching with early exit

        Optimized version of _rule_matches with:
        - Early exit on first mismatch
        - Reduced function call overhead
        - task_type already checked via index
        """
        # Since we're using task_type index, we know task_type matches
        # Only need to check metadata conditions
        for key, value in rule.condition.items():
            if key == "task_type":
                continue  # Already matched via index
            elif key in task.metadata:
                if task.metadata[key] != value:
                    return False
            else:
                return False
        return True

    def _log_routing_stats(self, routing_plan: RoutingPlan) -> None:
        """Log routing statistics"""
        total_tasks = len(routing_plan.assignments) + len(routing_plan.unassigned_tasks)
        assigned_pct = (len(routing_plan.assignments) / total_tasks * 100) if total_tasks > 0 else 0

        self.logger.info(f"Routing complete: {len(routing_plan.assignments)}/{total_tasks} tasks assigned ({assigned_pct:.1f}%)")

        if routing_plan.unassigned_tasks:
            self.logger.warning(f"Unassigned tasks: {routing_plan.unassigned_tasks}")

        workload = routing_plan.get_agent_workload()
        if workload:
            self.logger.info(f"Agent workload: {workload}")

    async def route_with_safety(
        self,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute ``task`` using the provided executor while applying WaltzRL safety.

        Args:
            task: Task payload (must include a ``description`` or ``query`` field).
            context: Optional dictionary containing an ``execute`` coroutine that
                performs the underlying task execution and returns a draft result.

        Returns:
            The executor result augmented with a ``safety`` payload when WaltzRL is
            enabled.  If WaltzRL is disabled the draft result is returned unchanged.
        """
        context = context or {}
        executor = context.get("execute")

        if executor is None or not callable(executor):
            raise ValueError(
                "route_with_safety requires a callable 'execute' entry in the context"
            )

        draft_result = await executor(task)

        if not self.enable_waltzrl or self._safety_wrapper is None:
            return draft_result

        response_text = draft_result.get("response", "")
        if not response_text:
            return draft_result

        agent_name = draft_result.get("agent") or draft_result.get("agent_name") or "unknown"
        query = task.get("description") or task.get("query", "")

        wrapped = self._safety_wrapper.wrap_agent_response(
            agent_name=agent_name,
            query=query,
            response=response_text,
            agent_metadata=draft_result,
        )

        draft_result["response"] = wrapped.response
        draft_result["safety"] = wrapped.to_dict()

        return draft_result

    async def create_specialized_agent(
        self,
        task: Task,
        agent_creator=None
    ) -> Optional[str]:
        """
        Dynamically create agent if no existing agent matches (AATC Phase 2)

        This implements HALO's "dynamic agent creation" capability using AATC.

        Algorithm:
        1. Use DynamicAgentCreator to generate new agent with custom tools
        2. Register agent in HALORouter's agent_registry
        3. Return agent name for routing

        Args:
            task: Task that needs specialized agent
            agent_creator: DynamicAgentCreator instance (optional)

        Returns:
            Agent name if created successfully, None otherwise
        """
        if agent_creator is None:
            self.logger.info(f"Dynamic agent creation requested for {task.task_id} (no creator provided)")
            return None

        try:
            # Step 1: Create dynamic agent with AATC
            dynamic_agent = await agent_creator.create_agent_for_task(
                task_description=task.description,
                context={"task_type": task.task_type, "metadata": task.metadata}
            )

            # Step 2: Convert to AgentCapability and register
            agent_capability = agent_creator.convert_to_agent_capability(dynamic_agent)
            self.agent_registry[dynamic_agent.agent_id] = agent_capability

            # Initialize workload tracking
            self.agent_workload[dynamic_agent.agent_id] = 0

            self.logger.info(
                f"Created and registered dynamic agent '{dynamic_agent.name}' "
                f"({dynamic_agent.agent_id}) for task {task.task_id}"
            )

            # Step 3: Return agent name for routing
            return dynamic_agent.agent_id

        except Exception as e:
            self.logger.error(f"Failed to create dynamic agent for {task.task_id}: {e}")
            return None

    def add_routing_rule(self, rule: RoutingRule) -> None:
        """
        Add custom routing rule

        Allows runtime addition of new routing rules.
        Useful for domain-specific routing logic.

        OPTIMIZATION: Updates caches when adding new rules
        """
        self.routing_rules.append(rule)

        # Update sorted cache (re-sort to maintain priority order)
        self._sorted_rules_cache = sorted(self.routing_rules, key=lambda r: r.priority, reverse=True)

        # Update task_type index (rebuild to maintain priority order)
        task_type = rule.condition.get("task_type")
        if task_type:
            # Rebuild index for this task_type to maintain sort order
            self._task_type_index[task_type] = [
                r for r in self._sorted_rules_cache
                if r.condition.get("task_type") == task_type
            ]

        self.logger.info(f"Added routing rule: {rule.rule_id} (priority={rule.priority})")

    def get_agent_workload(self) -> Dict[str, int]:
        """
        Get current task count per agent (for load balancing)

        Returns:
            Dict mapping agent_name to current task count
        """
        return dict(self.agent_workload)

    def update_agent_capability(
        self,
        agent_name: str,
        success_rate: Optional[float] = None,
        cost_tier: Optional[str] = None
    ) -> None:
        """
        Update agent capability profile (for learning/adaptation)

        Allows runtime updates to agent profiles based on:
        - Historical success rates
        - Cost optimizations
        - Performance monitoring
        """
        if agent_name not in self.agent_registry:
            self.logger.warning(f"Agent {agent_name} not in registry")
            return

        agent_cap = self.agent_registry[agent_name]

        if success_rate is not None:
            old_rate = agent_cap.success_rate
            agent_cap.success_rate = success_rate
            self.logger.info(f"Updated {agent_name} success_rate: {old_rate:.2f} → {success_rate:.2f}")

        if cost_tier is not None:
            old_tier = agent_cap.cost_tier
            agent_cap.cost_tier = cost_tier
            self.logger.info(f"Updated {agent_name} cost_tier: {old_tier} → {cost_tier}")

    def get_routing_explanation(self, task_id: str, routing_plan: RoutingPlan) -> str:
        """
        Get human-readable explanation for routing decision

        Provides full explainability for debugging and auditing.
        """
        if task_id in routing_plan.assignments:
            agent = routing_plan.assignments[task_id]
            explanation = routing_plan.explanations[task_id]
            return f"Task '{task_id}' was routed to '{agent}': {explanation}"
        elif task_id in routing_plan.unassigned_tasks:
            return f"Task '{task_id}' could not be assigned (no matching agent)"
        else:
            return f"Task '{task_id}' not found in routing plan"

    # VULN-002 FIX: Agent authentication methods

    def register_agent(
        self,
        agent_name: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> tuple[str, str]:
        """
        Register agent with cryptographic authentication

        Args:
            agent_name: Agent name to register
            metadata: Optional metadata (version, capabilities, etc.)

        Returns:
            (agent_id, auth_token) - Store auth_token securely

        Raises:
            ValueError: If agent already registered
        """
        return self.auth_registry.register_agent(agent_name, metadata)

    def _verify_agents(
        self,
        agent_names: List[str],
        agent_tokens: Dict[str, str]
    ) -> None:
        """
        Verify all agents are authenticated

        Args:
            agent_names: List of agent names to verify
            agent_tokens: Dict of agent_name -> auth_token

        Raises:
            SecurityError: If any agent fails verification
        """
        for agent_name in agent_names:
            # Check if agent is in registry
            if agent_name not in self.agent_registry:
                raise SecurityError(f"Unknown agent: '{agent_name}'")

            # Get token
            if agent_name not in agent_tokens:
                raise SecurityError(f"No authentication token provided for agent: '{agent_name}'")

            auth_token = agent_tokens[agent_name]

            # Verify
            if not self.auth_registry.verify_agent(agent_name, auth_token):
                raise SecurityError(f"Agent authentication failed: '{agent_name}'")

        self.logger.info(f"All {len(agent_names)} agents verified successfully")

    def is_agent_registered(self, agent_name: str) -> bool:
        """Check if agent is registered with authentication"""
        return self.auth_registry.is_registered(agent_name)

    def revoke_agent(self, agent_name: str) -> bool:
        """Revoke agent authentication"""
        return self.auth_registry.revoke_agent(agent_name)

    # Vertex AI Integration (NEW: Nov 4, 2025)

    def execute_with_llm(
        self,
        agent_name: str,
        prompt: str,
        fallback_to_cloud: bool = True,
        prefer_local: bool = False,  # Changed to False for Railway deployment
        **kwargs
    ) -> Optional[str]:
        """
        Execute task using best available LLM with cost optimization

        RAILWAY DEPLOYMENT ROUTING STRATEGY:
        1. Try Vertex AI first (fine-tuned models with service account)
        2. Fall back to Claude/GPT if Vertex fails
        3. Local LLM disabled for Railway (no GPU/large models)

        Args:
            agent_name: Agent to execute task (qa_agent, support_agent, etc.)
            prompt: Task prompt/description
            fallback_to_cloud: Allow fallback to cloud LLMs if local fails
            prefer_local: Prefer local LLM for cost savings (default: False for Railway)
            **kwargs: Additional arguments for model inference

        Returns:
            Generated response string or None if failed
        """
        # RAILWAY: FORCE DISABLE local LLM completely (no CPU inference on Railway)
        # CRITICAL: Local LLM (Qwen 7B) requires GPU and fails on Railway CPU-only instances
        # All routing goes directly to cloud APIs (Vertex AI → Claude/GPT)
        if prefer_local:
            logger.debug(f"Local LLM disabled for Railway deployment - forcing cloud APIs for {agent_name}")

        # Skip local LLM entirely - Railway doesn't have GPU support for Qwen
        # The code below is commented out to prevent ANY attempts to load local models
        # if prefer_local:
        #     try:
        #         logger.info(f"🟢 Routing {agent_name} to Local LLM (Qwen 7B, cost: $0)")
        #         ...local LLM code removed for Railway...
        #     except Exception as e:
        #         logger.warning(f"Local LLM failed for {agent_name}: {e}")

        # Fallback 1: Try Vertex AI (fine-tuned models or base Gemini) - TEMPORARILY DISABLED due to permission issues
        if False and fallback_to_cloud and self.use_vertex_ai and self.vertex_router:
            # Check if this agent has a Vertex AI endpoint
            endpoints = self.vertex_router.list_endpoints()
            if agent_name in endpoints and len(endpoints[agent_name]) > 0:
                try:
                    logger.info(f"🔷 Routing {agent_name} to Vertex AI (fine-tuned Gemini)")
                    response = self.vertex_router.route(
                        role=agent_name,  # Fixed: parameter is 'role' not 'agent_role'
                        prompt=prompt,
                        temperature=kwargs.get('temperature', 0.7),
                        endpoint_override=kwargs.get('endpoint_override', None)
                    )
                    
                    if response:
                        # Track usage stats
                        stats = self.vertex_router.get_usage_stats(agent_name)
                        logger.info(
                            f"Vertex AI response received: "
                            f"tokens={stats.get('total_tokens', 0)}, "
                            f"cost=${stats.get('total_cost', 0):.4f}, "
                            f"latency={stats.get('avg_latency', 0):.2f}ms"
                        )
                        return response
                    
                except Exception as e:
                    logger.warning(f"Vertex AI routing failed for {agent_name}: {e}")
                    if not fallback_to_cloud:
                        raise
            else:
                # No fine-tuned model, but try Vertex AI base model (Gemini Flash)
                if self.use_vertex_ai and self.vertex_router and self.vertex_router._use_vertex:
                    try:
                        logger.info(f"🔷 Routing {agent_name} to Vertex AI Base Model (Gemini 2.0 Flash)")
                        # Use base model for agents without fine-tuned models
                        response = self.vertex_router.route(
                            role=agent_name,
                            prompt=prompt,
                            temperature=kwargs.get('temperature', 0.7),
                            endpoint_override=None  # Will use base Gemini fallback
                        )
                        
                        if response:
                            logger.info(f"Vertex AI base model response received for {agent_name}")
                            return response
                    except Exception as e:
                        logger.warning(f"Vertex AI base model failed for {agent_name}: {e}")
          
                logger.debug(f"No Vertex AI model for {agent_name}, trying Claude/GPT fallback")

        # Fallback 2: Gemini Primary → Gemini Secondary → Mistral
        if fallback_to_cloud:
            # Try Gemini Primary first (GEMINI_API_KEY)
            gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            try:
                if self._gemini_client is None:
                    from google import genai  # type: ignore
                    from google.genai import types as genai_types  # type: ignore

                    self._gemini_client = genai.Client(api_key=gemini_api_key)
                    self._gemini_generate_config_cls = genai_types.GenerateContentConfig
                    logger.info(
                        "✅ Gemini fallback enabled (model=%s)",
                        self._gemini_model,
                    )

                config = None
                if self._gemini_generate_config_cls is not None:
                    try:
                        config = self._gemini_generate_config_cls(
                            temperature=kwargs.get('temperature', 0.7),
                            max_output_tokens=kwargs.get('max_tokens', 2048),
                        )
                    except Exception:
                        config = None

                logger.info(f"🔷 Routing {agent_name} to Gemini (model={self._gemini_model})")
                gemini_response = self._gemini_client.models.generate_content(
                    model=self._gemini_model,
                    contents=prompt,
                    config=config,
                )

                text = getattr(gemini_response, "text", None)
                if not text and getattr(gemini_response, "candidates", None):
                    try:
                        text = gemini_response.candidates[0].content.parts[0].text  # type: ignore[attr-defined]
                    except Exception:
                        text = None

                if text:
                    logger.info(f"✅ Gemini Primary success for {agent_name}")
                    return text
                raise ValueError("Gemini returned empty response")
            except Exception as e:
                logger.warning(f"Gemini Primary fallback failed for {agent_name}: {e}")

            # Try Gemini Secondary (GOOGLE_API_KEY)
            gemini_api_key_2 = os.getenv("GOOGLE_API_KEY")
            if gemini_api_key_2 and gemini_api_key_2 != gemini_api_key:
                try:
                    from google import genai
                    from google.genai import types as genai_types

                    logger.info(f"🔷 Routing {agent_name} to Gemini Secondary (GOOGLE_API_KEY)")
                    client2 = genai.Client(api_key=gemini_api_key_2)
                    config = genai_types.GenerateContentConfig(
                        temperature=kwargs.get('temperature', 0.7),
                        max_output_tokens=kwargs.get('max_tokens', 2048),
                    )
                    response2 = client2.models.generate_content(
                        model=self._gemini_model,
                        contents=prompt,
                        config=config,
                    )
                    text2 = getattr(response2, "text", None)
                    if not text2 and getattr(response2, "candidates", None):
                        text2 = response2.candidates[0].content.parts[0].text
                    if text2:
                        logger.info(f"✅ Gemini Secondary success for {agent_name}")
                        return text2
                except Exception as e:
                    logger.warning(f"Gemini Secondary fallback failed for {agent_name}: {e}")

            # Try Mistral as final fallback
            if os.getenv('MISTRAL_API_KEY'):
                try:
                    logger.info(f"🟡 Routing {agent_name} to Mistral (final fallback)")
                    from mistralai import Mistral
                    client = Mistral(api_key=os.getenv('MISTRAL_API_KEY'))
                    response = client.chat.complete(
                        model="mistral-large-latest",
                        max_tokens=kwargs.get('max_tokens', 2048),
                        temperature=kwargs.get('temperature', 0.7),
                        messages=[{"role": "user", "content": prompt}]
                    )
                    if response and response.choices:
                        logger.info(f"✅ Mistral fallback success for {agent_name}")
                        return response.choices[0].message.content
                except Exception as e:
                    logger.warning(f"Mistral fallback failed: {e}")

        logger.error(f"All inference options exhausted for {agent_name}. No response generated.")

        return None

    @classmethod 
    def create_with_integrations(
        cls,
        enable_policy_cards: bool = True,
        enable_capability_maps: bool = True,
        policy_cards_dir: str = ".policy_cards",
        capability_maps_dir: str = "maps/capabilities",
        **kwargs
    ) -> Union['HALORouter', 'PolicyAwareHALORouter', 'HALOCapabilityBridge']:
        """
        Factory method to create HALO Router with integrated systems.

        This integrates three research-backed systems:
        1. Policy Cards (arXiv:2510.24383): Runtime governance
        2. Capability Maps: Pre-tool middleware validation
        3. Base HALO Router (arXiv:2505.13516): Logic-based routing

        Args:
            enable_policy_cards: Enable Policy Card enforcement
            enable_capability_maps: Enable Capability Map validation
            policy_cards_dir: Directory containing policy card YAML files
            capability_maps_dir: Directory containing capability map YAML files
            **kwargs: Additional arguments for HALORouter initialization

        Returns:
            HALORouter with requested integrations (wrapped)

        Example:
            # All integrations enabled (recommended)
            router = HALORouter.create_with_integrations()

            # Only policy cards
            router = HALORouter.create_with_integrations(enable_capability_maps=False)

            # Base HALO only
            router = HALORouter.create_with_integrations(
                enable_policy_cards=False,
                enable_capability_maps=False
            )
        """
        # Create base HALO router
        base_router = cls(**kwargs)

        # Layer 1: Wrap with Policy Cards (if enabled)
        # Lazy import to avoid circular import issues
        if enable_policy_cards:
            try:
                from infrastructure.policy_cards.middleware import PolicyEnforcer
                from infrastructure.policy_cards.halo_integration import PolicyAwareHALORouter

                policy_enforcer = PolicyEnforcer(cards_dir=policy_cards_dir)
                policy_router = PolicyAwareHALORouter(
                    halo_router=base_router,
                    policy_enforcer=policy_enforcer
                )
                logger.info(f"✅ Policy Cards integration enabled (dir: {policy_cards_dir})")
            except Exception as e:
                logger.warning(f"Policy Cards integration failed: {e}, using base router")
                policy_router = base_router
        else:
            policy_router = base_router

        # Layer 2: Wrap with Capability Maps (if enabled)
        # Lazy import to avoid circular import issues
        if enable_capability_maps:
            try:
                from infrastructure.middleware.halo_capability_integration import HALOCapabilityBridge

                capability_bridge = HALOCapabilityBridge(
                    halo_router=policy_router,
                    capabilities_dir=capability_maps_dir
                )
                logger.info(f"✅ Capability Maps integration enabled (dir: {capability_maps_dir})")
                return capability_bridge
            except Exception as e:
                logger.warning(f"Capability Maps integration failed: {e}, returning policy router")
                return policy_router

        return policy_router

    def get_vertex_usage_stats(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Vertex AI usage statistics
        
        Args:
            agent_name: Optional agent name to filter stats (None = all agents)
        
        Returns:
            Usage statistics dict (requests, tokens, cost, latency)
        """
        if not self.vertex_router:
            return {}
        
        if agent_name:
            return self.vertex_router.get_usage_stats(agent_name)
        
        # Return aggregated stats for all agents
        all_stats = {}
        total_cost = self.vertex_router.get_total_cost()
        
        for agent in ["qa_agent", "support_agent", "analyst_agent", "legal_agent", "content_agent", "security_agent"]:
            stats = self.vertex_router.get_usage_stats(agent)
            if stats.get('total_requests', 0) > 0:
                all_stats[agent] = stats
        
        all_stats['total_cost_usd'] = total_cost
        return all_stats

    def _integrate_toolrm(self, routing_plan: RoutingPlan) -> None:
        """
        Integrate with ToolRM for tool usage tracking (Task 7).

        Logs routing decisions as "tool calls" for quality tracking.
        """
        try:
            from infrastructure.full_system_integrator import get_integrator
            integrator = get_integrator()

            toolrm = integrator.systems.get('toolrm')
            if not toolrm or not toolrm.initialized:
                return

            logger = toolrm.instance['logger']

            # Log each agent assignment as a "tool call"
            for task_id, agent_name in routing_plan.assignments.items():
                try:
                    explanation = routing_plan.explanations.get(task_id, '')

                    # Log the routing decision
                    logger.log_tool_call(
                        agent_id="halo_router",
                        tool_name=f"route_to_{agent_name}",
                        success=True,
                        latency_ms=0.0,  # Routing is fast
                        output_quality=0.9,  # Default high quality
                        metadata={
                            'task_id': task_id,
                            'explanation': explanation,
                            'routing_type': 'rule_based'
                        }
                    )
                except Exception as e:
                    self.logger.debug(f"ToolRM logging failed for task {task_id}: {e}")

            self.logger.info(f"✅ ToolRM: Logged {len(routing_plan.assignments)} routing decisions")

        except Exception as e:
            # Don't fail routing if ToolRM integration fails
            self.logger.debug(f"ToolRM integration failed: {e}")

    async def execute_with_middleware(
        self,
        tool_name: str,
        agent_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        executor = None
    ) -> Any:
        """
        Execute tool with middleware hooks.

        This wraps tool execution with the middleware lifecycle:
        1. on_tool_call() - Pre-execution validation (policy, capability)
        2. [Tool executes]
        3. on_tool_result() - Post-execution scoring (ToolRM)
        4. on_tool_error() - Error handling

        Args:
            tool_name: Tool to execute
            agent_name: Agent executing the tool
            arguments: Tool arguments
            context: Execution context (optional)
            executor: Callable that executes the tool (optional)

        Returns:
            Tool execution result

        Raises:
            PolicyViolation: If policy check fails
            CapabilityError: If capability check fails
            Any exception from tool execution
        """
        from infrastructure.middleware.base import ToolCall, ToolResult
        import time

        # Create tool call
        call = ToolCall(
            tool_name=tool_name,
            agent_name=agent_name,
            arguments=arguments,
            context=context or {},
        )

        # PRE-TOOL: Run all middleware on_tool_call hooks
        if self.middlewares:
            for middleware in self.middlewares:
                try:
                    await middleware.on_tool_call(call)
                except Exception as e:
                    self.logger.error(
                        f"Middleware {middleware.__class__.__name__} on_tool_call failed: {e}"
                    )
                    raise

        # EXECUTE TOOL
        start_time = time.time()
        try:
            # Use provided executor or fall back to execute_with_llm
            if executor:
                result_data = await executor(call)
            else:
                # Fallback to LLM execution
                result_data = self.execute_with_llm(
                    agent_name=agent_name,
                    prompt=f"Execute {tool_name} with args: {arguments}",
                    **arguments,
                )

            execution_time = (time.time() - start_time) * 1000

            result = ToolResult(
                tool_name=tool_name,
                agent_name=agent_name,
                result=result_data,
                execution_time_ms=execution_time,
                success=True,
            )

            # POST-TOOL: Run all middleware on_tool_result hooks
            if self.middlewares:
                for middleware in self.middlewares:
                    try:
                        await middleware.on_tool_result(result)
                    except Exception as e:
                        self.logger.warning(
                            f"Middleware {middleware.__class__.__name__} on_tool_result failed: {e}"
                        )

            return result_data

        except Exception as error:
            execution_time = (time.time() - start_time) * 1000

            # ERROR: Run all middleware on_tool_error hooks
            if self.middlewares:
                for middleware in self.middlewares:
                    try:
                        await middleware.on_tool_error(call, error)
                    except Exception as e:
                        self.logger.warning(
                            f"Middleware {middleware.__class__.__name__} on_tool_error failed: {e}"
                        )

            raise
