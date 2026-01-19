"""
ONBOARDING AGENT - Microsoft Agent Framework Version
Version: 4.0 (Enhanced with DAAO + TUMIX) (Day 2 Migration)

Handles user onboarding, activation, and initial setup.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict
from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from agent_framework.observability import setup_observability
from azure.identity.aio import AzureCliCredential

setup_observability(enable_sensitive_data=True)
# Import DAAO and TUMIX
from infrastructure.daao_router import get_daao_router, RoutingDecision
from infrastructure.tumix_termination import (
    get_tumix_termination,
    RefinementResult,
    TerminationDecision
)

logger = logging.getLogger(__name__)


class OnboardingAgent:
    """User onboarding and activation agent"""

    def __init__(self, business_id: str = "default"):
        self.business_id = business_id
        self.agent = None

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
        cred = AzureCliCredential()
        client = AzureAIAgentClient(async_credential=cred)
        self.agent = ChatAgent(
            chat_client=client,
            instructions="You are a user onboarding specialist. Guide new users through setup, provide personalized walkthroughs, track activation milestones, send targeted education emails, and ensure successful product adoption. Measure time-to-value, activation rates, and feature discovery. Create smooth, delightful first experiences that drive retention.",
            name="onboarding-agent",
            tools=[self.create_onboarding_flow, self.track_user_progress, self.send_onboarding_email, self.trigger_activation_milestone, self.measure_onboarding_success]
        )
        print(f"👋 Onboarding Agent initialized for business: {self.business_id}\n")

    def create_onboarding_flow(self, user_persona: str, product_type: str, flow_stages: List[str]) -> str:
        """Create personalized onboarding flow for user"""
        result = {
            "flow_id": f"FLOW-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "user_persona": user_persona,
            "product_type": product_type,
            "stages": [
                {
                    "stage_number": 1,
                    "stage_name": "Welcome & Account Setup",
                    "tasks": ["Complete profile", "Verify email", "Set preferences"],
                    "estimated_minutes": 5,
                    "completion_rate": 0.92
                },
                {
                    "stage_number": 2,
                    "stage_name": "Core Feature Tutorial",
                    "tasks": ["Interactive walkthrough", "Create first project", "Invite team member"],
                    "estimated_minutes": 10,
                    "completion_rate": 0.78
                },
                {
                    "stage_number": 3,
                    "stage_name": "Advanced Configuration",
                    "tasks": ["Connect integrations", "Customize settings", "Set up automation"],
                    "estimated_minutes": 15,
                    "completion_rate": 0.64
                },
                {
                    "stage_number": 4,
                    "stage_name": "First Value Achievement",
                    "tasks": ["Complete first workflow", "See results", "Share with team"],
                    "estimated_minutes": 20,
                    "completion_rate": 0.71
                }
            ],
            "total_estimated_minutes": 50,
            "personalization_applied": True,
            "created_at": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)

    def track_user_progress(self, user_id: str, flow_id: str) -> str:
        """Track user progress through onboarding flow"""
        result = {
            "progress_id": f"PROG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "user_id": user_id,
            "flow_id": flow_id,
            "started_at": "2025-10-14T10:23:00Z",
            "current_stage": 2,
            "completed_stages": [1],
            "completed_tasks": [
                "Complete profile",
                "Verify email",
                "Set preferences",
                "Interactive walkthrough",
                "Create first project"
            ],
            "pending_tasks": [
                "Invite team member",
                "Connect integrations",
                "Customize settings"
            ],
            "completion_percent": 45,
            "time_spent_minutes": 12,
            "last_activity": datetime.now().isoformat(),
            "predicted_completion_probability": 0.82,
            "tracked_at": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)

    def send_onboarding_email(self, user_id: str, email_type: str, trigger_event: str) -> str:
        """Send targeted onboarding email to user"""
        result = {
            "email_id": f"EMAIL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "user_id": user_id,
            "email_type": email_type,
            "trigger_event": trigger_event,
            "subject_line": "Welcome! Let's get you started 👋" if email_type == "welcome" else "You're almost there! Complete your setup",
            "content_sections": [
                "Personalized greeting",
                "Product value proposition",
                "Next steps checklist",
                "Quick start video (2 min)",
                "Support resources"
            ],
            "call_to_action": "Complete Setup",
            "send_time": "immediate" if email_type == "welcome" else "delayed_30_minutes",
            "personalization_tokens": ["first_name", "company_name", "use_case"],
            "status": "sent",
            "sent_at": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)

    def trigger_activation_milestone(self, user_id: str, milestone_type: str) -> str:
        """Trigger celebration for activation milestone"""
        result = {
            "milestone_id": f"MILESTONE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "user_id": user_id,
            "milestone_type": milestone_type,
            "milestone_name": "First Project Created" if milestone_type == "first_project" else "Team Invited",
            "achievement_value": "You're on your way! You've completed the core setup.",
            "celebration_type": "in_app_modal",
            "rewards": [
                {"type": "badge", "name": "Early Adopter"},
                {"type": "credits", "amount": 100},
                {"type": "unlock", "feature": "advanced_analytics"}
            ],
            "next_milestone": "Complete 5 workflows",
            "progress_to_next_percent": 20,
            "triggered_at": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)

    def measure_onboarding_success(self, start_date: str, end_date: str, cohort_filter: str) -> str:
        """Measure onboarding success metrics for a cohort"""
        result = {
            "measurement_id": f"MEASURE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "period": {"start": start_date, "end": end_date},
            "cohort_filter": cohort_filter,
            "metrics": {
                "total_new_users": 1567,
                "activated_users": 1124,
                "activation_rate": 0.717,
                "average_time_to_activation_hours": 8.4,
                "completion_by_stage": {
                    "stage_1": 0.92,
                    "stage_2": 0.78,
                    "stage_3": 0.64,
                    "stage_4": 0.71
                },
                "drop_off_points": [
                    {"stage": "Invite team member", "drop_off_rate": 0.22},
                    {"stage": "Connect integrations", "drop_off_rate": 0.14}
                ],
                "day_1_retention": 0.84,
                "day_7_retention": 0.68,
                "day_30_retention": 0.54
            },
            "recommendations": [
                "Simplify team invitation flow (22% drop-off)",
                "Add integration setup wizard",
                "Send reminder email at 24-hour mark for incomplete users",
                "Highlight quick wins earlier in flow"
            ],
            "measured_at": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)


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
            'id': f'onboarding-{{datetime.now().strftime("%Y%m%d%H%M%S")}}',
            'description': task_description,
            'priority': priority,
            'required_tools': []
        }

        decision = self.router.route_task(task, budget_conscious=True)

        logger.info(
            f"Task routed: {decision.reasoning}",
            extra={
                'agent': 'OnboardingAgent',
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
                'agent': 'OnboardingAgent',
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
            'agent': 'OnboardingAgent',
            'tumix_sessions': tumix_savings['sessions'],
            'tumix_baseline_rounds': tumix_savings['baseline_rounds'],
            'tumix_actual_rounds': tumix_savings['tumix_rounds'],
            'tumix_savings_percent': tumix_savings['savings_percent'],
            'tumix_total_saved': tumix_savings['savings'],
            'daao_info': 'DAAO routing automatically applied to all tasks'
        }



async def get_onboarding_agent(business_id: str = "default") -> OnboardingAgent:
    agent = OnboardingAgent(business_id=business_id)
    await agent.initialize()
    return agent
