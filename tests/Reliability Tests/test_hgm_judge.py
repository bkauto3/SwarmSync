"""
Test suite for HGM tree search and Agent-as-a-Judge integration

Tests:
1. Judge scoring (correctness, calibration)
2. HGM tree search (convergence, quality)
3. Safety layer (threshold enforcement)
4. CMP vs fitness comparison (quality improvement validation)
5. Integration with SE-Darwin agent
"""

import asyncio
import pytest
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

# Module under test
from infrastructure.judge import (
    AgentJudge,
    JudgeScore,
    CMPScore,
    EvaluationDimension,
    get_agent_judge
)
from infrastructure.oracle_hgm import (
    OracleHGM,
    TreeNode,
    CandidateEdit,
    EditStrategy,
    get_oracle_hgm
)
from infrastructure.safety_layer import (
    SafetyLayer,
    SafetyReport,
    ReleaseDecision,
    RiskLevel,
    SafetyStatus,
    get_safety_layer
)

# Genesis infrastructure for mocking
from infrastructure.llm_client import LLMClient
from infrastructure.casebank import CaseBank
from infrastructure.trajectory_pool import TrajectoryPool


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    client = Mock(spec=LLMClient)
    client.chat_completion = AsyncMock()
    return client


@pytest.fixture
def mock_casebank():
    """Mock CaseBank for testing"""
    casebank = Mock(spec=CaseBank)
    casebank.store_case = AsyncMock()
    casebank.retrieve_similar = AsyncMock(return_value=[])
    return casebank


@pytest.fixture
def mock_trajectory_pool():
    """Mock TrajectoryPool for testing"""
    pool = Mock(spec=TrajectoryPool)
    return pool


@pytest.fixture
def sample_code():
    """Sample code for testing"""
    return """
def calculate_sum(numbers):
    \"\"\"Calculate sum of a list of numbers.\"\"\"
    total = 0
    for num in numbers:
        total += num
    return total
"""


@pytest.fixture
def sample_task():
    """Sample task description"""
    return "Implement a function to calculate the sum of a list of numbers"


# ============================================================================
# AGENT JUDGE TESTS
# ============================================================================

class TestAgentJudge:
    """Test Agent-as-a-Judge pattern"""

    @pytest.mark.asyncio
    async def test_judge_initialization(self, mock_llm_client, mock_casebank):
        """Test judge initialization"""
        judge = AgentJudge(
            llm_client=mock_llm_client,
            casebank=mock_casebank,
            judge_model="gpt-4o",
            coherence_weight=0.15
        )

        assert judge.llm_client == mock_llm_client
        assert judge.casebank == mock_casebank
        assert judge.judge_model == "gpt-4o"
        assert judge.coherence_weight == 0.15

    @pytest.mark.asyncio
    async def test_score_output_success(
        self,
        mock_llm_client,
        mock_casebank,
        sample_code,
        sample_task
    ):
        """Test successful code scoring"""
        # Mock LLM response
        mock_llm_client.chat_completion.return_value = """
{
    "correctness_score": 85.0,
    "completeness_score": 90.0,
    "efficiency_score": 75.0,
    "safety_score": 95.0,
    "reasoning": "Good implementation with room for optimization"
}
"""

        judge = AgentJudge(
            llm_client=mock_llm_client,
            casebank=mock_casebank
        )

        score = await judge.score_output(
            output=sample_code,
            criteria=sample_task,
            context={}
        )

        assert isinstance(score, JudgeScore)
        assert 0 <= score.score <= 100
        assert score.dimensions[EvaluationDimension.CORRECTNESS] == 85.0
        assert score.dimensions[EvaluationDimension.COMPLETENESS] == 90.0
        assert score.dimensions[EvaluationDimension.EFFICIENCY] == 75.0
        assert score.dimensions[EvaluationDimension.SAFETY] == 95.0
        assert score.reasoning != ""

    @pytest.mark.asyncio
    async def test_score_output_error_handling(
        self,
        mock_llm_client,
        mock_casebank,
        sample_code,
        sample_task
    ):
        """Test error handling in scoring"""
        # Mock LLM failure
        mock_llm_client.chat_completion.side_effect = Exception("LLM error")

        judge = AgentJudge(
            llm_client=mock_llm_client,
            casebank=mock_casebank
        )

        score = await judge.score_output(
            output=sample_code,
            criteria=sample_task,
            context={}
        )

        assert isinstance(score, JudgeScore)
        assert score.score == 0.0
        assert "failed" in score.reasoning.lower()

    @pytest.mark.asyncio
    async def test_batch_score(
        self,
        mock_llm_client,
        mock_casebank,
        sample_code,
        sample_task
    ):
        """Test batch scoring"""
        mock_llm_client.chat_completion.return_value = """
{
    "correctness_score": 80.0,
    "completeness_score": 85.0,
    "efficiency_score": 75.0,
    "safety_score": 90.0,
    "reasoning": "Good code"
}
"""

        judge = AgentJudge(
            llm_client=mock_llm_client,
            casebank=mock_casebank
        )

        outputs = [
            (sample_code, sample_task, {}),
            (sample_code, sample_task, {}),
            (sample_code, sample_task, {})
        ]

        scores = await judge.batch_score(outputs)

        assert len(scores) == 3
        assert all(isinstance(s, JudgeScore) for s in scores)

    def test_calculate_cmp_score_single(
        self,
        mock_llm_client,
        mock_casebank
    ):
        """Test CMP calculation with single judge score"""
        judge = AgentJudge(
            llm_client=mock_llm_client,
            casebank=mock_casebank,
            coherence_weight=0.15
        )

        judge_score = JudgeScore(
            score=85.0,
            reasoning="Good code",
            dimensions={
                EvaluationDimension.CORRECTNESS: 85.0,
                EvaluationDimension.COMPLETENESS: 90.0,
                EvaluationDimension.EFFICIENCY: 80.0,
                EvaluationDimension.SAFETY: 85.0
            }
        )

        cmp_score = judge.calculate_cmp_score([judge_score])

        assert isinstance(cmp_score, CMPScore)
        assert cmp_score.mean_score == 85.0
        assert cmp_score.coherence_penalty == 0.0  # Single score, no variance
        assert cmp_score.cmp_score == 85.0

    def test_calculate_cmp_score_multiple(
        self,
        mock_llm_client,
        mock_casebank
    ):
        """Test CMP calculation with multiple judge scores"""
        judge = AgentJudge(
            llm_client=mock_llm_client,
            casebank=mock_casebank,
            coherence_weight=0.15
        )

        judge_scores = [
            JudgeScore(
                score=85.0,
                reasoning="Good",
                dimensions={
                    EvaluationDimension.CORRECTNESS: 85.0,
                    EvaluationDimension.COMPLETENESS: 85.0,
                    EvaluationDimension.EFFICIENCY: 85.0,
                    EvaluationDimension.SAFETY: 85.0
                }
            ),
            JudgeScore(
                score=90.0,
                reasoning="Excellent",
                dimensions={
                    EvaluationDimension.CORRECTNESS: 90.0,
                    EvaluationDimension.COMPLETENESS: 90.0,
                    EvaluationDimension.EFFICIENCY: 90.0,
                    EvaluationDimension.SAFETY: 90.0
                }
            )
        ]

        cmp_score = judge.calculate_cmp_score(judge_scores)

        assert isinstance(cmp_score, CMPScore)
        assert cmp_score.mean_score == 87.5
        assert cmp_score.coherence_penalty > 0  # Should have some penalty
        assert cmp_score.cmp_score < cmp_score.mean_score  # Penalty applied

    @pytest.mark.asyncio
    async def test_store_to_casebank(
        self,
        mock_llm_client,
        mock_casebank,
        sample_code,
        sample_task
    ):
        """Test storing evaluation to CaseBank"""
        judge = AgentJudge(
            llm_client=mock_llm_client,
            casebank=mock_casebank
        )

        judge_score = JudgeScore(
            score=85.0,
            reasoning="Good code",
            dimensions={
                EvaluationDimension.CORRECTNESS: 85.0,
                EvaluationDimension.COMPLETENESS: 90.0,
                EvaluationDimension.EFFICIENCY: 80.0,
                EvaluationDimension.SAFETY: 85.0
            }
        )

        await judge.store_to_casebank(
            score=judge_score,
            output=sample_code,
            context={"criteria": sample_task}
        )

        mock_casebank.store_case.assert_called_once()


# ============================================================================
# ORACLE HGM TESTS
# ============================================================================

class TestOracleHGM:
    """Test HGM tree search"""

    @pytest.mark.asyncio
    async def test_oracle_initialization(
        self,
        mock_llm_client,
        mock_trajectory_pool
    ):
        """Test OracleHGM initialization"""
        oracle = OracleHGM(
            llm_client=mock_llm_client,
            trajectory_pool=mock_trajectory_pool,
            n_proposals=10,
            top_k=3,
            max_depth=5,
            cmp_threshold=70.0
        )

        assert oracle.llm_client == mock_llm_client
        assert oracle.trajectory_pool == mock_trajectory_pool
        assert oracle.n_proposals == 10
        assert oracle.top_k == 3
        assert oracle.max_depth == 5
        assert oracle.cmp_threshold == 70.0

    @pytest.mark.asyncio
    async def test_propose_edits_hypothesis_guided(
        self,
        mock_llm_client,
        mock_trajectory_pool,
        sample_code,
        sample_task
    ):
        """Test hypothesis-guided edit proposal"""
        # Mock LLM response
        mock_llm_client.chat_completion.return_value = """
{
    "hypotheses": [
        {
            "hypothesis": "Optimize with sum() builtin",
            "modified_code": "def calculate_sum(numbers):\\n    return sum(numbers)",
            "reasoning": "More Pythonic and efficient"
        },
        {
            "hypothesis": "Add input validation",
            "modified_code": "def calculate_sum(numbers):\\n    if not numbers:\\n        return 0\\n    return sum(numbers)",
            "reasoning": "Handle edge cases"
        }
    ]
}
"""

        oracle = OracleHGM(
            llm_client=mock_llm_client,
            trajectory_pool=mock_trajectory_pool
        )

        candidates = await oracle.propose_edits(
            code=sample_code,
            task=sample_task,
            n=2,
            strategy=EditStrategy.HYPOTHESIS_GUIDED
        )

        assert len(candidates) == 2
        assert all(isinstance(c, CandidateEdit) for c in candidates)
        assert all(c.strategy == EditStrategy.HYPOTHESIS_GUIDED for c in candidates)

    @pytest.mark.asyncio
    async def test_cmp_score_candidates(
        self,
        mock_llm_client,
        mock_casebank,
        mock_trajectory_pool,
        sample_task
    ):
        """Test CMP scoring of candidates"""
        # Mock judge
        mock_judge = Mock(spec=AgentJudge)
        mock_judge.score_output = AsyncMock(return_value=JudgeScore(
            score=85.0,
            reasoning="Good",
            dimensions={
                EvaluationDimension.CORRECTNESS: 85.0,
                EvaluationDimension.COMPLETENESS: 85.0,
                EvaluationDimension.EFFICIENCY: 85.0,
                EvaluationDimension.SAFETY: 85.0
            }
        ))
        mock_judge.calculate_cmp_score = Mock(return_value=CMPScore(
            mean_score=85.0,
            coherence_penalty=0.0,
            cmp_score=85.0,
            judge_scores=[],
            dimension_variance={}
        ))

        oracle = OracleHGM(
            llm_client=mock_llm_client,
            judge=mock_judge,
            trajectory_pool=mock_trajectory_pool
        )

        candidates = [
            CandidateEdit(
                code="def foo(): pass",
                hypothesis="Test 1",
                strategy=EditStrategy.HYPOTHESIS_GUIDED
            ),
            CandidateEdit(
                code="def bar(): pass",
                hypothesis="Test 2",
                strategy=EditStrategy.HYPOTHESIS_GUIDED
            )
        ]

        scored = await oracle.cmp_score(candidates, sample_task)

        assert len(scored) == 2
        assert all(isinstance(s[1], CMPScore) for s in scored)
        # Should be sorted by CMP score
        assert scored[0][1].cmp_score >= scored[1][1].cmp_score

    @pytest.mark.asyncio
    async def test_select_best(
        self,
        mock_llm_client,
        mock_trajectory_pool
    ):
        """Test top-K selection"""
        oracle = OracleHGM(
            llm_client=mock_llm_client,
            trajectory_pool=mock_trajectory_pool,
            top_k=2
        )

        scored_candidates = [
            (
                CandidateEdit(code="a", hypothesis="h1", strategy=EditStrategy.HYPOTHESIS_GUIDED),
                CMPScore(mean_score=90.0, coherence_penalty=0.0, cmp_score=90.0, judge_scores=[], dimension_variance={})
            ),
            (
                CandidateEdit(code="b", hypothesis="h2", strategy=EditStrategy.HYPOTHESIS_GUIDED),
                CMPScore(mean_score=85.0, coherence_penalty=0.0, cmp_score=85.0, judge_scores=[], dimension_variance={})
            ),
            (
                CandidateEdit(code="c", hypothesis="h3", strategy=EditStrategy.HYPOTHESIS_GUIDED),
                CMPScore(mean_score=80.0, coherence_penalty=0.0, cmp_score=80.0, judge_scores=[], dimension_variance={})
            )
        ]

        selected = await oracle.select_best(scored_candidates, k=2)

        assert len(selected) == 2
        assert selected[0][1].cmp_score == 90.0
        assert selected[1][1].cmp_score == 85.0


# ============================================================================
# SAFETY LAYER TESTS
# ============================================================================

class TestSafetyLayer:
    """Test safety layer for code release gating"""

    def test_safety_layer_initialization(self):
        """Test SafetyLayer initialization"""
        safety = SafetyLayer(
            cmp_threshold=70.0,
            strict_mode=False
        )

        assert safety.cmp_threshold == 70.0
        assert safety.strict_mode is False

    @pytest.mark.asyncio
    async def test_safety_check_pass(self, sample_code):
        """Test safety check that passes"""
        safety = SafetyLayer(cmp_threshold=70.0)

        cmp_score = CMPScore(
            mean_score=85.0,
            coherence_penalty=0.0,
            cmp_score=85.0,
            judge_scores=[],
            dimension_variance={}
        )

        report = await safety.safety_check(sample_code, cmp_score)

        assert isinstance(report, SafetyReport)
        assert report.status in [SafetyStatus.PASSED, SafetyStatus.NEEDS_REVIEW]
        assert report.cmp_score.cmp_score >= 70.0

    @pytest.mark.asyncio
    async def test_safety_check_fail_cmp_threshold(self):
        """Test safety check fails on low CMP score"""
        safety = SafetyLayer(cmp_threshold=80.0)

        code = "def foo(): pass"
        cmp_score = CMPScore(
            mean_score=60.0,
            coherence_penalty=0.0,
            cmp_score=60.0,
            judge_scores=[],
            dimension_variance={}
        )

        report = await safety.safety_check(code, cmp_score)

        assert report.status == SafetyStatus.FAILED
        assert not report.all_checks_passed

    @pytest.mark.asyncio
    async def test_safety_check_dangerous_patterns(self):
        """Test dangerous pattern detection"""
        safety = SafetyLayer(cmp_threshold=70.0)

        dangerous_code = """
def execute_command(cmd):
    import os
    os.system(cmd)  # Dangerous!
"""

        cmp_score = CMPScore(
            mean_score=85.0,
            coherence_penalty=0.0,
            cmp_score=85.0,
            judge_scores=[],
            dimension_variance={}
        )

        report = await safety.safety_check(dangerous_code, cmp_score)

        # Should detect dangerous pattern
        pattern_check = next(
            (c for c in report.checks if c.check_name == "dangerous_patterns"),
            None
        )
        assert pattern_check is not None
        assert not pattern_check.passed

    @pytest.mark.asyncio
    async def test_validate_release_approved(self, sample_code):
        """Test release approval"""
        safety = SafetyLayer(cmp_threshold=70.0)

        cmp_score = CMPScore(
            mean_score=85.0,
            coherence_penalty=0.0,
            cmp_score=85.0,
            judge_scores=[],
            dimension_variance={}
        )

        decision = await safety.validate_release(sample_code, cmp_score)

        assert isinstance(decision, ReleaseDecision)
        assert decision.approved or decision.report.requires_human_approval

    @pytest.mark.asyncio
    async def test_validate_release_rejected(self):
        """Test release rejection"""
        safety = SafetyLayer(cmp_threshold=80.0, strict_mode=False)

        bad_code = "def foo():\n  syntax error here!"
        cmp_score = CMPScore(
            mean_score=50.0,
            coherence_penalty=0.0,
            cmp_score=50.0,
            judge_scores=[],
            dimension_variance={}
        )

        decision = await safety.validate_release(bad_code, cmp_score)

        assert not decision.approved


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestHGMJudgeIntegration:
    """Integration tests for HGM + Judge + Safety Layer"""

    @pytest.mark.asyncio
    async def test_end_to_end_evolution(
        self,
        mock_llm_client,
        mock_casebank,
        mock_trajectory_pool,
        sample_code,
        sample_task
    ):
        """Test end-to-end evolution with CMP scoring"""
        # Mock LLM responses
        mock_llm_client.chat_completion.side_effect = [
            # Hypothesis generation
            """
{
    "hypotheses": [
        {
            "hypothesis": "Use sum() builtin",
            "modified_code": "def calculate_sum(numbers):\\n    return sum(numbers)",
            "reasoning": "More efficient"
        }
    ]
}
""",
            # Judge scoring
            """
{
    "correctness_score": 90.0,
    "completeness_score": 90.0,
    "efficiency_score": 95.0,
    "safety_score": 90.0,
    "reasoning": "Excellent implementation"
}
"""
        ]

        # Initialize components
        judge = AgentJudge(
            llm_client=mock_llm_client,
            casebank=mock_casebank
        )

        oracle = OracleHGM(
            llm_client=mock_llm_client,
            judge=judge,
            trajectory_pool=mock_trajectory_pool,
            n_proposals=1,
            top_k=1
        )

        safety = SafetyLayer(cmp_threshold=70.0)

        # Generate candidates
        candidates = await oracle.propose_edits(
            code=sample_code,
            task=sample_task,
            n=1
        )

        assert len(candidates) >= 1

        # Score candidates
        scored = await oracle.cmp_score(candidates, sample_task)

        assert len(scored) >= 1
        assert scored[0][1].cmp_score > 0

        # Validate with safety layer
        best_candidate, best_cmp = scored[0]
        decision = await safety.validate_release(
            best_candidate.code,
            best_cmp
        )

        assert isinstance(decision, ReleaseDecision)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
