"""
Tests for AOPValidator - Agent Orchestration Protocol Validation

Test Coverage:
1. Three-principle validation (solvability, completeness, non-redundancy)
2. Quality score calculation (reward model formula)
3. Edge cases and failure modes
4. Integration with HTDAG TaskDAG
"""
import pytest
import math
from infrastructure.aop_validator import (
    AOPValidator,
    ValidationResult,
    RoutingPlan,
    AgentCapability
)
from infrastructure.task_dag import TaskDAG, Task, TaskStatus


class TestAOPValidatorBasics:
    """Basic validation tests"""

    @pytest.mark.asyncio
    async def test_valid_plan_passes_all_checks(self):
        """Test that a properly structured plan passes all validation checks"""
        # Setup agent registry
        validator = AOPValidator(agent_registry={
            "builder_agent": AgentCapability(
                agent_name="builder_agent",
                supported_task_types=["implement", "code"],
                skills=["python", "javascript"],
                cost_tier="medium",
                success_rate=0.85
            ),
            "qa_agent": AgentCapability(
                agent_name="qa_agent",
                supported_task_types=["test", "validate"],
                skills=["testing", "pytest"],
                cost_tier="cheap",
                success_rate=0.90
            )
        })

        # Create DAG with 2 tasks
        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Write code"))
        dag.add_task(Task(task_id="task2", task_type="test", description="Test code"))

        # Create routing plan
        plan = RoutingPlan()
        plan.assignments = {
            "task1": "builder_agent",
            "task2": "qa_agent"
        }

        # Validate
        result = await validator.validate_routing_plan(plan, dag)

        # Assertions
        assert result.passed is True, f"Validation should pass: {result.issues}"
        assert result.solvability_passed is True
        assert result.completeness_passed is True
        assert result.redundancy_passed is True
        assert len(result.issues) == 0
        assert result.quality_score is not None
        assert 0.0 <= result.quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_empty_plan_fails_completeness(self):
        """Test that empty routing plan fails completeness check"""
        validator = AOPValidator()

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Code"))

        plan = RoutingPlan()
        plan.assignments = {}  # Empty!

        result = await validator.validate_routing_plan(plan, dag)

        assert result.passed is False
        assert result.completeness_passed is False
        assert len(result.issues) > 0
        assert any("unassigned" in issue.lower() for issue in result.issues)


class TestSolvabilityPrinciple:
    """Tests for Principle 1: Solvability"""

    @pytest.mark.asyncio
    async def test_agent_not_in_registry_fails(self):
        """Test that assigning unknown agent fails solvability"""
        validator = AOPValidator(agent_registry={})  # Empty registry

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Code"))

        plan = RoutingPlan()
        plan.assignments = {"task1": "unknown_agent"}

        result = await validator.validate_routing_plan(plan, dag)

        assert result.passed is False
        assert result.solvability_passed is False
        assert any("not in registry" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_agent_unsupported_task_type_fails(self):
        """Test that assigning task type agent doesn't support fails"""
        validator = AOPValidator(agent_registry={
            "builder": AgentCapability(
                agent_name="builder",
                supported_task_types=["implement", "code"],
                skills=[]
            )
        })

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="deploy", description="Deploy app"))

        plan = RoutingPlan()
        plan.assignments = {"task1": "builder"}

        result = await validator.validate_routing_plan(plan, dag)

        assert result.passed is False
        assert result.solvability_passed is False
        assert any("doesn't support" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_missing_required_skills_fails(self):
        """Test that missing required skills fails solvability"""
        validator = AOPValidator(agent_registry={
            "builder": AgentCapability(
                agent_name="builder",
                supported_task_types=["implement"],
                skills=["python"]  # Only Python
            )
        })

        dag = TaskDAG()
        task = Task(
            task_id="task1",
            task_type="implement",
            description="Build Rust service"
        )
        task.metadata["required_skills"] = ["rust", "wasm"]  # Needs Rust
        dag.add_task(task)

        plan = RoutingPlan()
        plan.assignments = {"task1": "builder"}

        result = await validator.validate_routing_plan(plan, dag)

        assert result.passed is False
        assert result.solvability_passed is False
        assert any("missing skills" in issue for issue in result.issues)


class TestDirIntegration:
    """Tests for WaltzRL DIR integration within AOP validation."""

    @staticmethod
    def _make_validator() -> AOPValidator:
        return AOPValidator(agent_registry={
            "safety_agent": AgentCapability(
                agent_name="safety_agent",
                supported_task_types=["safety_review"],
                skills=["analysis"],
                success_rate=0.9
            )
        })

    @staticmethod
    def _make_simple_plan() -> (RoutingPlan, TaskDAG):
        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="safety_review", description="Review response safety"))

        plan = RoutingPlan()
        plan.assignments = {"task1": "safety_agent"}
        return plan, dag

    @pytest.mark.asyncio
    async def test_dir_report_positive(self):
        """DIR report meeting thresholds should keep validation passing."""
        validator = self._make_validator()
        plan, dag = self._make_simple_plan()

        dir_report = {
            "reward_stats": {
                "count": 3,
                "mean": 0.42,
                "min": 0.30,
                "max": 0.55,
                "positive_rate": 0.8,
            },
            "component_averages": {
                "safety_delta": 0.09,
                "helpfulness_delta": 0.05,
                "user_satisfaction": 0.85,
                "feedback_quality": 0.72,
            },
            "improvements": {
                "unsafe_reduction": 0.38,
                "overrefusal_reduction": 0.36,
            },
        }

        result = await validator.validate_routing_plan(plan, dag, dir_report=dir_report)

        assert result.passed is True
        assert result.dir_validation_passed is True
        assert result.dir_report is dir_report

    @pytest.mark.asyncio
    async def test_dir_report_below_threshold_fails(self):
        """DIR report below thresholds should surface issues and fail validation."""
        validator = self._make_validator()
        plan, dag = self._make_simple_plan()

        dir_report = {
            "reward_stats": {
                "count": 3,
                "mean": 0.10,  # Too low
                "min": -0.05,
                "max": 0.2,
                "positive_rate": 0.3,  # Too low
            },
            "component_averages": {
                "safety_delta": 0.01,  # Too low
                "helpfulness_delta": 0.02,
                "user_satisfaction": 0.6,
                "feedback_quality": 0.55,
            },
            "improvements": {
                "unsafe_reduction": 0.10,   # Below target
                "overrefusal_reduction": 0.05,  # Below target
            },
        }

        result = await validator.validate_routing_plan(plan, dag, dir_report=dir_report)

        assert result.passed is False
        assert result.dir_validation_passed is False
        assert any("DIR reward mean" in issue for issue in result.issues)
        assert any("Unsafe reduction" in issue for issue in result.issues)


class TestCompletenessPrinciple:
    """Tests for Principle 2: Completeness"""

    @pytest.mark.asyncio
    async def test_missing_task_assignment_fails(self):
        """Test that unassigned tasks fail completeness"""
        validator = AOPValidator(agent_registry={
            "builder": AgentCapability(
                agent_name="builder",
                supported_task_types=["implement"],
                skills=[]
            )
        })

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Code"))
        dag.add_task(Task(task_id="task2", task_type="test", description="Test"))

        plan = RoutingPlan()
        plan.assignments = {"task1": "builder"}  # task2 missing!

        result = await validator.validate_routing_plan(plan, dag)

        assert result.passed is False
        assert result.completeness_passed is False
        assert any("unassigned" in issue.lower() for issue in result.issues)

    @pytest.mark.asyncio
    async def test_orphaned_assignment_fails(self):
        """Test that assignments to non-existent tasks fail"""
        validator = AOPValidator(agent_registry={
            "builder": AgentCapability(
                agent_name="builder",
                supported_task_types=["implement"],
                skills=[]
            )
        })

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Code"))

        plan = RoutingPlan()
        plan.assignments = {
            "task1": "builder",
            "task_nonexistent": "builder"  # Not in DAG!
        }

        result = await validator.validate_routing_plan(plan, dag)

        assert result.passed is False
        assert result.completeness_passed is False
        assert any("orphaned" in issue.lower() for issue in result.issues)

    @pytest.mark.asyncio
    async def test_unassigned_tasks_field_checked(self):
        """Test that routing_plan.unassigned_tasks field is checked"""
        validator = AOPValidator()

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Code"))

        plan = RoutingPlan()
        plan.assignments = {"task1": "builder"}
        plan.unassigned_tasks = ["task2"]  # Routing plan says task2 unassigned

        result = await validator.validate_routing_plan(plan, dag)

        assert result.passed is False
        assert result.completeness_passed is False


class TestRedundancyPrinciple:
    """Tests for Principle 3: Non-redundancy"""

    @pytest.mark.asyncio
    async def test_duplicate_tasks_flagged(self):
        """Test that duplicate tasks generate warnings"""
        validator = AOPValidator(agent_registry={
            "builder": AgentCapability(
                agent_name="builder",
                supported_task_types=["implement"],
                skills=[]
            )
        })

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Write API"))
        dag.add_task(Task(task_id="task2", task_type="implement", description="Write API"))

        plan = RoutingPlan()
        plan.assignments = {
            "task1": "builder",
            "task2": "builder"
        }

        result = await validator.validate_routing_plan(plan, dag)

        # Redundancy generates warnings, may fail if high confidence
        assert len(result.warnings) > 0
        assert any("redundancy" in warning.lower() for warning in result.warnings)

    @pytest.mark.asyncio
    async def test_similar_descriptions_high_confidence(self):
        """Test that similar descriptions trigger high confidence duplicate flag"""
        validator = AOPValidator(agent_registry={
            "builder": AgentCapability(
                agent_name="builder",
                supported_task_types=["implement"],
                skills=[]
            )
        })

        dag = TaskDAG()
        # Identical descriptions
        dag.add_task(Task(task_id="task1", task_type="implement", description="Build REST API endpoint"))
        dag.add_task(Task(task_id="task2", task_type="implement", description="Build REST API endpoint"))

        plan = RoutingPlan()
        plan.assignments = {
            "task1": "builder",
            "task2": "builder"
        }

        result = await validator.validate_routing_plan(plan, dag)

        # High confidence duplicates should fail
        assert result.passed is False
        assert any("High probability" in warning for warning in result.warnings)

    @pytest.mark.asyncio
    async def test_different_task_types_no_redundancy(self):
        """Test that different task types don't trigger redundancy"""
        validator = AOPValidator(agent_registry={
            "builder": AgentCapability(
                agent_name="builder",
                supported_task_types=["implement", "test"],
                skills=[]
            )
        })

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Code"))
        dag.add_task(Task(task_id="task2", task_type="test", description="Test"))

        plan = RoutingPlan()
        plan.assignments = {
            "task1": "builder",
            "task2": "builder"
        }

        result = await validator.validate_routing_plan(plan, dag)

        # Different task types = no redundancy warning
        assert result.passed is True
        assert result.redundancy_passed is True


class TestQualityScoreCalculation:
    """Tests for reward model quality score"""

    @pytest.mark.asyncio
    async def test_quality_score_in_range(self):
        """Test that quality score is always in [0, 1]"""
        validator = AOPValidator(agent_registry={
            "builder": AgentCapability(
                agent_name="builder",
                supported_task_types=["implement"],
                skills=["python"],
                cost_tier="cheap",
                success_rate=0.95
            )
        })

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Code"))

        plan = RoutingPlan()
        plan.assignments = {"task1": "builder"}

        result = await validator.validate_routing_plan(plan, dag)

        assert result.quality_score is not None
        assert 0.0 <= result.quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_high_success_rate_improves_score(self):
        """Test that higher agent success rates improve quality score"""
        # Agent with high success rate
        agent_high = AgentCapability(
            agent_name="expert",
            supported_task_types=["implement"],
            skills=[],
            cost_tier="medium",
            success_rate=0.95
        )

        # Agent with low success rate
        agent_low = AgentCapability(
            agent_name="junior",
            supported_task_types=["implement"],
            skills=[],
            cost_tier="medium",
            success_rate=0.60
        )

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Code"))

        # Test high success rate
        validator_high = AOPValidator(agent_registry={"expert": agent_high})
        plan_high = RoutingPlan(assignments={"task1": "expert"})
        result_high = await validator_high.validate_routing_plan(plan_high, dag)

        # Test low success rate
        validator_low = AOPValidator(agent_registry={"junior": agent_low})
        plan_low = RoutingPlan(assignments={"task1": "junior"})
        result_low = await validator_low.validate_routing_plan(plan_low, dag)

        # High success rate should have higher quality score
        assert result_high.quality_score > result_low.quality_score

    @pytest.mark.asyncio
    async def test_cheaper_agents_improve_score(self):
        """Test that cheaper agents improve cost component of score"""
        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Code"))

        # Cheap agent
        validator_cheap = AOPValidator(agent_registry={
            "cheap_agent": AgentCapability(
                agent_name="cheap_agent",
                supported_task_types=["implement"],
                skills=[],
                cost_tier="cheap",
                success_rate=0.85
            )
        })
        plan_cheap = RoutingPlan(assignments={"task1": "cheap_agent"})
        result_cheap = await validator_cheap.validate_routing_plan(plan_cheap, dag)

        # Expensive agent
        validator_expensive = AOPValidator(agent_registry={
            "expensive_agent": AgentCapability(
                agent_name="expensive_agent",
                supported_task_types=["implement"],
                skills=[],
                cost_tier="expensive",
                success_rate=0.85  # Same success rate
            )
        })
        plan_expensive = RoutingPlan(assignments={"task1": "expensive_agent"})
        result_expensive = await validator_expensive.validate_routing_plan(plan_expensive, dag)

        # Cheaper agent should have higher score (cost efficiency)
        assert result_cheap.quality_score > result_expensive.quality_score

    @pytest.mark.asyncio
    async def test_quality_score_formula_weights(self):
        """Test that quality score follows reward model formula"""
        validator = AOPValidator(agent_registry={
            "builder": AgentCapability(
                agent_name="builder",
                supported_task_types=["implement"],
                skills=["python"],
                cost_tier="medium",
                success_rate=0.8
            )
        })

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Code"))

        plan = RoutingPlan(assignments={"task1": "builder"})
        result = await validator.validate_routing_plan(plan, dag)

        # Verify weights sum to 1.0
        weights = [
            validator.weight_success,
            validator.weight_quality,
            validator.weight_cost,
            validator.weight_time
        ]
        assert math.isclose(sum(weights), 1.0, abs_tol=0.01)

        # Verify score is weighted combination
        # (exact calculation depends on internal metrics)
        assert result.quality_score is not None


class TestEdgeCases:
    """Edge case and integration tests"""

    @pytest.mark.asyncio
    async def test_empty_dag_empty_plan(self):
        """Test validation with empty DAG and plan"""
        validator = AOPValidator()

        dag = TaskDAG()  # Empty
        plan = RoutingPlan()  # Empty

        result = await validator.validate_routing_plan(plan, dag)

        # Empty DAG with empty plan should pass (vacuous truth)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_complex_dag_with_dependencies(self):
        """Test validation with complex DAG structure"""
        validator = AOPValidator(agent_registry={
            "spec": AgentCapability(
                agent_name="spec",
                supported_task_types=["design"],
                skills=[]
            ),
            "builder": AgentCapability(
                agent_name="builder",
                supported_task_types=["implement"],
                skills=[]
            ),
            "qa": AgentCapability(
                agent_name="qa",
                supported_task_types=["test"],
                skills=[]
            ),
            "deploy": AgentCapability(
                agent_name="deploy",
                supported_task_types=["deploy"],
                skills=[]
            )
        })

        # Create complex DAG: design -> implement -> test -> deploy
        dag = TaskDAG()
        dag.add_task(Task(task_id="t1", task_type="design", description="Design"))
        dag.add_task(Task(task_id="t2", task_type="implement", description="Code"))
        dag.add_task(Task(task_id="t3", task_type="test", description="Test"))
        dag.add_task(Task(task_id="t4", task_type="deploy", description="Deploy"))

        dag.add_dependency("t1", "t2")  # design -> implement
        dag.add_dependency("t2", "t3")  # implement -> test
        dag.add_dependency("t3", "t4")  # test -> deploy

        plan = RoutingPlan(assignments={
            "t1": "spec",
            "t2": "builder",
            "t3": "qa",
            "t4": "deploy"
        })

        result = await validator.validate_routing_plan(plan, dag)

        assert result.passed is True
        assert result.quality_score is not None

        # Deeper DAG should have lower time score (more steps)
        assert dag.max_depth() == 3  # 4 nodes, max path length 3

    @pytest.mark.asyncio
    async def test_validation_result_string_representation(self):
        """Test that ValidationResult has useful string representation"""
        validator = AOPValidator(agent_registry={
            "builder": AgentCapability(
                agent_name="builder",
                supported_task_types=["implement"],
                skills=[]
            )
        })

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Code"))

        plan = RoutingPlan(assignments={"task1": "builder"})
        result = await validator.validate_routing_plan(plan, dag)

        result_str = str(result)
        assert "ValidationResult" in result_str
        assert "PASSED" in result_str or "FAILED" in result_str
        assert "Solvability" in result_str
        assert "Completeness" in result_str
        assert "Non-redundancy" in result_str

    @pytest.mark.asyncio
    async def test_multiple_agents_success_probability_product(self):
        """Test that success probability is product of individual rates"""
        validator = AOPValidator(agent_registry={
            "agent1": AgentCapability(
                agent_name="agent1",
                supported_task_types=["implement"],
                skills=[],
                success_rate=0.9
            ),
            "agent2": AgentCapability(
                agent_name="agent2",
                supported_task_types=["test"],
                skills=[],
                success_rate=0.8
            )
        })

        dag = TaskDAG()
        dag.add_task(Task(task_id="task1", task_type="implement", description="Code"))
        dag.add_task(Task(task_id="task2", task_type="test", description="Test"))

        plan = RoutingPlan(assignments={
            "task1": "agent1",
            "task2": "agent2"
        })

        # Calculate expected success probability: 0.9 * 0.8 = 0.72
        expected_prob = 0.9 * 0.8

        # Get actual success probability
        actual_prob = validator._estimate_success_probability(plan, dag)

        assert math.isclose(actual_prob, expected_prob, abs_tol=0.01)

    @pytest.mark.asyncio
    async def test_validation_with_zero_quality_agents(self):
        """Test validation with zero-quality agents (extreme edge case)"""
        validator = AOPValidator(agent_registry={
            "zero_agent": AgentCapability(
                agent_name="zero_agent",
                supported_task_types=["implement"],
                skills=[],  # No skills (0% quality match)
                cost_tier="cheap",
                success_rate=0.0  # Zero success rate
            )
        })

        dag = TaskDAG()
        dag.add_task(Task(
            task_id="task1",
            task_type="implement",
            description="Requires Python and JavaScript skills"
        ))

        plan = RoutingPlan(assignments={"task1": "zero_agent"})
        result = await validator.validate_routing_plan(plan, dag)

        # Should still pass validation (agent exists and supports task type)
        assert result.passed is True
        assert result.solvability_passed is True
        assert result.completeness_passed is True
        assert result.quality_score is not None
        # Quality score will still be positive due to cost and time factors
        # (0.4 * 0.0 + 0.3 * quality + 0.2 * cost + 0.1 * time)
        # Even with 0 success rate, cost and time contribute ~0.3 * (0.2 + 0.1)
        assert 0.0 <= result.quality_score <= 1.0  # Valid range


class TestIntegrationScenarios:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_realistic_business_deployment_scenario(self):
        """Test realistic business deployment workflow validation"""
        # Setup agent registry with realistic agents
        validator = AOPValidator(agent_registry={
            "spec_agent": AgentCapability(
                agent_name="spec_agent",
                supported_task_types=["design", "requirements"],
                skills=["system_design", "architecture"],
                cost_tier="expensive",
                success_rate=0.90
            ),
            "builder_agent": AgentCapability(
                agent_name="builder_agent",
                supported_task_types=["implement", "code"],
                skills=["python", "javascript", "react"],
                cost_tier="medium",
                success_rate=0.85
            ),
            "qa_agent": AgentCapability(
                agent_name="qa_agent",
                supported_task_types=["test", "validate"],
                skills=["pytest", "jest", "integration_testing"],
                cost_tier="cheap",
                success_rate=0.88
            ),
            "deploy_agent": AgentCapability(
                agent_name="deploy_agent",
                supported_task_types=["deploy", "infra"],
                skills=["docker", "kubernetes", "cicd"],
                cost_tier="medium",
                success_rate=0.92
            )
        })

        # Create realistic DAG for business deployment
        dag = TaskDAG()
        dag.add_task(Task(
            task_id="design",
            task_type="design",
            description="Design system architecture and API specs"
        ))
        dag.add_task(Task(
            task_id="implement_backend",
            task_type="implement",
            description="Implement backend API with FastAPI"
        ))
        dag.add_task(Task(
            task_id="implement_frontend",
            task_type="implement",
            description="Implement React frontend"
        ))
        dag.add_task(Task(
            task_id="test_backend",
            task_type="test",
            description="Run backend integration tests"
        ))
        dag.add_task(Task(
            task_id="test_frontend",
            task_type="test",
            description="Run frontend E2E tests"
        ))
        dag.add_task(Task(
            task_id="deploy_prod",
            task_type="deploy",
            description="Deploy to production with Docker"
        ))

        # Add dependencies
        dag.add_dependency("design", "implement_backend")
        dag.add_dependency("design", "implement_frontend")
        dag.add_dependency("implement_backend", "test_backend")
        dag.add_dependency("implement_frontend", "test_frontend")
        dag.add_dependency("test_backend", "deploy_prod")
        dag.add_dependency("test_frontend", "deploy_prod")

        # Create routing plan
        plan = RoutingPlan(assignments={
            "design": "spec_agent",
            "implement_backend": "builder_agent",
            "implement_frontend": "builder_agent",
            "test_backend": "qa_agent",
            "test_frontend": "qa_agent",
            "deploy_prod": "deploy_agent"
        })

        # Validate
        result = await validator.validate_routing_plan(plan, dag)

        # Assertions
        assert result.passed is True, f"Realistic scenario should pass: {result.issues}"
        assert result.quality_score is not None
        assert result.quality_score > 0.6, "High-quality plan should score >0.6"

        # Log result for inspection
        print(f"\n{result}")
        print(f"Quality Score: {result.quality_score:.3f}")

        # Additional validation checks
        assert result.solvability_passed is True
        assert result.completeness_passed is True
        assert result.redundancy_passed is True


if __name__ == "__main__":
    # Run with: pytest tests/test_aop_validator.py -v
    pytest.main([__file__, "-v", "-s"])
