"""
Test suite for Verifier Agent - Multi-Agent Evolve Phase 3

Based on arXiv:2510.23595 "Multi-Agent Evolve: LLM Self-Improve through Co-evolution"

Test Coverage:
- Verifier initialization
- Trajectory verification (multi-criteria)
- Correctness evaluation
- Quality evaluation
- Robustness evaluation
- Generalization evaluation
- Shortcut detection
- Feedback generation
- Reward computation
- Statistics tracking
- Edge case generation

Author: Hudson (Implementation Specialist)
Date: November 3, 2025
Status: Phase 3 Testing
"""

import pytest
from infrastructure.evolution.verifier_agent import (
    VerifierAgent,
    VerifierConfig,
    VerificationResult,
    get_verifier_agent
)


# ==================== Initialization Tests ====================

def test_verifier_initialization():
    """Test Verifier initialization with defaults."""
    verifier = VerifierAgent("qa_agent")

    assert verifier.agent_type == "qa_agent"
    assert verifier.config.correctness_weight == 0.4
    assert verifier.config.quality_weight == 0.3
    assert verifier.config.robustness_weight == 0.2
    assert verifier.config.generalization_weight == 0.1
    assert verifier.config.num_edge_cases == 5
    assert verifier.config.shortcut_detection_enabled is True
    assert verifier.verification_history == []


def test_verifier_initialization_with_custom_config():
    """Test Verifier initialization with custom config."""
    config = VerifierConfig(
        correctness_weight=0.5,
        quality_weight=0.25,
        robustness_weight=0.15,
        generalization_weight=0.1,
        num_edge_cases=10
    )
    verifier = VerifierAgent("builder_agent", config=config)

    assert verifier.agent_type == "builder_agent"
    assert verifier.config.correctness_weight == 0.5
    assert verifier.config.num_edge_cases == 10


def test_config_weight_validation():
    """Test that config weights must sum to 1.0."""
    # Valid config (sums to 1.0)
    config = VerifierConfig(
        correctness_weight=0.4,
        quality_weight=0.3,
        robustness_weight=0.2,
        generalization_weight=0.1
    )
    assert abs(sum([
        config.correctness_weight,
        config.quality_weight,
        config.robustness_weight,
        config.generalization_weight
    ]) - 1.0) < 0.01

    # Invalid config (does not sum to 1.0)
    with pytest.raises(ValueError, match="must sum to 1.0"):
        VerifierConfig(
            correctness_weight=0.5,
            quality_weight=0.5,
            robustness_weight=0.5,
            generalization_weight=0.5
        )


def test_config_validation_num_edge_cases():
    """Test validation of num_edge_cases."""
    # Valid
    config = VerifierConfig(num_edge_cases=5)
    assert config.num_edge_cases == 5

    # Invalid (< 1)
    with pytest.raises(ValueError, match="num_edge_cases must be >= 1"):
        VerifierConfig(num_edge_cases=0)


def test_factory_function():
    """Test get_verifier_agent factory function."""
    verifier = get_verifier_agent("qa_agent")
    assert isinstance(verifier, VerifierAgent)
    assert verifier.agent_type == "qa_agent"


# ==================== Verification Tests ====================

@pytest.mark.asyncio
async def test_verify_trajectory():
    """Test complete trajectory verification."""
    verifier = VerifierAgent("qa_agent")

    trajectory = {
        "trajectory_id": "test_123",
        "code": "def binary_search(arr, target):\n    # Implementation\n    left, right = 0, len(arr) - 1\n    return -1",
        "strategy": "baseline",
        "benchmark_score": 0.85
    }

    task = {
        "type": "code_generation",
        "description": "Implement binary search"
    }

    result = await verifier.verify_trajectory(trajectory, task)

    assert isinstance(result, VerificationResult)
    assert 0.0 <= result.verification_score <= 1.0
    assert result.correctness_score == 0.85
    assert len(result.feedback) >= 0
    assert result.edge_cases_tested == 5
    assert "task_type" in result.metadata
    assert "trajectory_id" in result.metadata


@pytest.mark.asyncio
async def test_verify_trajectory_with_shortcuts():
    """Test verification detects shortcuts."""
    verifier = VerifierAgent("qa_agent")

    trajectory = {
        "trajectory_id": "test_456",
        "code": "def solve():\n    return 42  # hardcoded\n    if test_mode:\n        return 'test'",
        "strategy": "baseline",
        "benchmark_score": 0.9
    }

    task = {
        "type": "problem_solving",
        "description": "Solve the problem"
    }

    result = await verifier.verify_trajectory(trajectory, task)

    assert len(result.shortcuts_detected) >= 1
    assert any("hardcoded" in s or "test_mode" in s for s in result.shortcuts_detected)
    assert any(fb["area"] == "shortcuts" for fb in result.feedback)


# ==================== Correctness Tests ====================

@pytest.mark.asyncio
async def test_correctness_evaluation():
    """Test correctness evaluation."""
    verifier = VerifierAgent("qa_agent")

    trajectory = {"benchmark_score": 0.9, "code": "def test(): pass"}
    task = {"type": "test"}

    score = await verifier._evaluate_correctness(trajectory, task)

    assert score == 0.9
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_correctness_evaluation_bounds():
    """Test correctness score stays in bounds."""
    verifier = VerifierAgent("qa_agent")

    # Test upper bound
    trajectory_high = {"benchmark_score": 1.5, "code": "def test(): pass"}
    task = {"type": "test"}
    score_high = await verifier._evaluate_correctness(trajectory_high, task)
    assert score_high == 1.0

    # Test lower bound
    trajectory_low = {"benchmark_score": -0.5, "code": "def test(): pass"}
    score_low = await verifier._evaluate_correctness(trajectory_low, task)
    assert score_low == 0.0


# ==================== Quality Tests ====================

@pytest.mark.asyncio
async def test_quality_evaluation():
    """Test quality evaluation."""
    verifier = VerifierAgent("qa_agent")

    # Good quality code
    good_trajectory = {
        "code": '''def binary_search(arr, target):
    """Binary search implementation."""
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1'''
    }

    task = {"type": "code_generation"}

    score = await verifier._evaluate_quality(good_trajectory, task)
    assert score >= 0.7
    assert score <= 1.0


@pytest.mark.asyncio
async def test_quality_evaluation_poor_code():
    """Test quality evaluation penalizes poor code."""
    verifier = VerifierAgent("qa_agent")

    # Good quality code for comparison
    good_trajectory = {
        "code": '''def binary_search(arr, target):
    """Binary search implementation."""
    left, right = 0, len(arr) - 1
    return -1'''
    }

    # Poor quality code (too short, no docs, no structure)
    poor_trajectory = {"code": "x=42"}

    task = {"type": "code_generation"}

    score_good = await verifier._evaluate_quality(good_trajectory, task)
    score_poor = await verifier._evaluate_quality(poor_trajectory, task)

    assert score_poor < score_good
    assert score_poor < 0.7


@pytest.mark.asyncio
async def test_quality_penalties():
    """Test specific quality penalties."""
    verifier = VerifierAgent("qa_agent")
    task = {"type": "test"}

    # No documentation penalty
    no_docs = {"code": "def func():\n    x = 1\n    return x"}
    score_no_docs = await verifier._evaluate_quality(no_docs, task)
    assert score_no_docs < 1.0

    # With documentation
    with_docs = {"code": 'def func():\n    """Docstring"""\n    x = 1\n    return x'}
    score_with_docs = await verifier._evaluate_quality(with_docs, task)
    assert score_with_docs > score_no_docs


# ==================== Robustness Tests ====================

@pytest.mark.asyncio
async def test_robustness_evaluation():
    """Test robustness evaluation."""
    verifier = VerifierAgent("qa_agent")

    trajectory = {"code": "def test(): pass", "trajectory_id": "test_123"}
    task = {"type": "test"}

    score = await verifier._evaluate_robustness(trajectory, task)

    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_robustness_evaluation_deterministic():
    """Test robustness evaluation is deterministic."""
    verifier = VerifierAgent("qa_agent")

    trajectory = {"code": "def test(): pass", "trajectory_id": "test_456"}
    task = {"type": "test"}

    # Run twice, should get same score
    score1 = await verifier._evaluate_robustness(trajectory, task)
    score2 = await verifier._evaluate_robustness(trajectory, task)

    assert score1 == score2


# ==================== Generalization Tests ====================

@pytest.mark.asyncio
async def test_generalization_evaluation():
    """Test generalization evaluation."""
    verifier = VerifierAgent("qa_agent")

    # Generic approach (should score higher)
    generic_trajectory = {
        "code": "def generic_solution(x, y):\n    result = compute(x, y)\n    return result",
        "strategy": "general_approach"
    }
    task = {"type": "test"}

    score_generic = await verifier._evaluate_generalization(generic_trajectory, task)

    # Specific approach (should score lower)
    specific_trajectory = {
        "code": "def specific_solution():\n    return 42",
        "strategy": "specific_hardcoded"
    }

    score_specific = await verifier._evaluate_generalization(specific_trajectory, task)

    assert score_generic > score_specific
    assert 0.0 <= score_generic <= 1.0
    assert 0.0 <= score_specific <= 1.0


@pytest.mark.asyncio
async def test_generalization_parameterization_bonus():
    """Test generalization rewards parameterized functions."""
    verifier = VerifierAgent("qa_agent")

    # Parameterized (good)
    param_trajectory = {
        "code": "def solve(input_data, config):\n    return process(input_data, config)",
        "strategy": "baseline"
    }

    # Non-parameterized (worse)
    no_param_trajectory = {
        "code": "x = 42\ny = 100\nprint(x + y)",
        "strategy": "baseline"
    }

    task = {"type": "test"}

    score_param = await verifier._evaluate_generalization(param_trajectory, task)
    score_no_param = await verifier._evaluate_generalization(no_param_trajectory, task)

    assert score_param > score_no_param


# ==================== Shortcut Detection Tests ====================

@pytest.mark.asyncio
async def test_shortcut_detection():
    """Test shortcut detection."""
    verifier = VerifierAgent("qa_agent")

    # Code with shortcuts
    shortcut_trajectory = {
        "code": "def solve():\n    return 42  # hardcoded\n    if test_mode:\n        return 'test'",
        "strategy": "baseline"
    }
    task = {"type": "test", "description": "Solve problem"}

    shortcuts = await verifier._detect_shortcuts(shortcut_trajectory, task)

    assert len(shortcuts) >= 1
    assert "hardcoded_values" in shortcuts or "test_mode_detection" in shortcuts


@pytest.mark.asyncio
async def test_shortcut_detection_clean_code():
    """Test shortcut detection on clean code."""
    verifier = VerifierAgent("qa_agent")

    # Clean code without shortcuts
    clean_trajectory = {
        "code": '''def solve(input_data, parameters):
    """Solve the problem generically."""
    result = compute_solution(input_data, parameters)
    validate_result(result)
    return result''',
        "strategy": "baseline"
    }

    task = {"type": "test", "description": "Solve problem"}

    shortcuts_clean = await verifier._detect_shortcuts(clean_trajectory, task)
    assert len(shortcuts_clean) == 0


@pytest.mark.asyncio
async def test_shortcut_detection_patterns():
    """Test detection of specific shortcut patterns."""
    verifier = VerifierAgent("qa_agent")
    task = {"type": "test", "description": "Test task"}

    # Test hardcoded values
    hardcoded = {"code": "def f(): return 42", "strategy": "baseline"}
    shortcuts_hc = await verifier._detect_shortcuts(hardcoded, task)
    assert "hardcoded_values" in shortcuts_hc

    # Test test mode detection
    test_mode = {"code": "if test_mode: return True", "strategy": "baseline"}
    shortcuts_tm = await verifier._detect_shortcuts(test_mode, task)
    assert "test_mode_detection" in shortcuts_tm

    # Test trivial implementation
    trivial = {"code": "x=1", "strategy": "baseline"}
    shortcuts_tr = await verifier._detect_shortcuts(trivial, task)
    assert "trivial_implementation" in shortcuts_tr


# ==================== Feedback Generation Tests ====================

def test_feedback_generation():
    """Test feedback generation."""
    verifier = VerifierAgent("qa_agent")

    feedback = verifier._generate_feedback(
        correctness=0.5,  # Low
        quality=0.9,      # High
        robustness=0.6,   # Medium
        generalization=0.4,  # Low
        shortcuts=["hardcoded_values"]
    )

    assert len(feedback) >= 2  # At least correctness + shortcut feedback

    # Check feedback structure
    for item in feedback:
        assert "area" in item
        assert "confidence" in item
        assert "severity" in item
        assert "message" in item
        assert item["area"] in ["correctness", "quality", "robustness", "generalization", "shortcuts"]
        assert item["severity"] in ["high", "medium", "low"]
        assert 0.0 <= item["confidence"] <= 1.0


def test_feedback_generation_correctness():
    """Test correctness feedback generation."""
    verifier = VerifierAgent("qa_agent")

    # Low correctness
    feedback_low = verifier._generate_feedback(
        correctness=0.5,
        quality=1.0,
        robustness=1.0,
        generalization=1.0,
        shortcuts=[]
    )
    correctness_feedback = [f for f in feedback_low if f["area"] == "correctness"]
    assert len(correctness_feedback) >= 1
    assert correctness_feedback[0]["severity"] == "high"


def test_feedback_generation_quality():
    """Test quality feedback generation."""
    verifier = VerifierAgent("qa_agent")

    # Low quality
    feedback = verifier._generate_feedback(
        correctness=1.0,
        quality=0.5,
        robustness=1.0,
        generalization=1.0,
        shortcuts=[]
    )
    quality_feedback = [f for f in feedback if f["area"] == "quality"]
    assert len(quality_feedback) >= 1


def test_feedback_generation_shortcuts():
    """Test shortcut feedback is always high severity."""
    verifier = VerifierAgent("qa_agent")

    feedback = verifier._generate_feedback(
        correctness=1.0,
        quality=1.0,
        robustness=1.0,
        generalization=1.0,
        shortcuts=["hardcoded_values", "test_mode_detection"]
    )

    shortcut_feedback = [f for f in feedback if f["area"] == "shortcuts"]
    assert len(shortcut_feedback) == 2
    for fb in shortcut_feedback:
        assert fb["severity"] == "high"
        assert fb["confidence"] == 1.0


# ==================== Reward Computation Tests ====================

def test_verifier_reward_computation():
    """Test Verifier reward function."""
    verifier = VerifierAgent("qa_agent")

    # Low verification score = high reward (found many errors)
    reward_high = verifier.compute_verifier_reward(
        verification_score=0.3,
        previous_verification_score=0.8
    )

    # High verification score = low reward (found few errors)
    reward_low = verifier.compute_verifier_reward(
        verification_score=0.9,
        previous_verification_score=0.8
    )

    assert reward_high > reward_low
    assert 0.0 <= reward_high <= 1.0
    assert 0.0 <= reward_low <= 1.0


def test_verifier_reward_error_component():
    """Test Verifier reward error component."""
    verifier = VerifierAgent("qa_agent")

    # Reward should be high when verification score is low (many errors found)
    reward_many_errors = verifier.compute_verifier_reward(verification_score=0.2)
    reward_few_errors = verifier.compute_verifier_reward(verification_score=0.9)

    assert reward_many_errors > reward_few_errors


def test_verifier_reward_challenge_component():
    """Test Verifier reward challenge component."""
    verifier = VerifierAgent("qa_agent")

    # Reward bonus when score decreases (Verifier getting better)
    reward_with_improvement = verifier.compute_verifier_reward(
        verification_score=0.5,
        previous_verification_score=0.8
    )

    # No bonus when score increases
    reward_without_improvement = verifier.compute_verifier_reward(
        verification_score=0.8,
        previous_verification_score=0.5
    )

    assert reward_with_improvement > reward_without_improvement


# ==================== Statistics Tests ====================

@pytest.mark.asyncio
async def test_verification_history():
    """Test verification history tracking."""
    verifier = VerifierAgent("qa_agent")

    trajectory = {
        "trajectory_id": "test_1",
        "code": "def test(): pass",
        "benchmark_score": 0.8
    }
    task = {"type": "test"}

    # Verify 3 trajectories
    for i in range(3):
        trajectory["trajectory_id"] = f"test_{i}"
        await verifier.verify_trajectory(trajectory, task)

    assert len(verifier.verification_history) == 3

    stats = verifier.get_stats()
    assert stats["total_verifications"] == 3
    assert 0.0 <= stats["average_score"] <= 1.0


def test_get_statistics_empty():
    """Test statistics with no verifications."""
    verifier = VerifierAgent("qa_agent")

    stats = verifier.get_stats()

    assert stats["total_verifications"] == 0
    assert stats["average_score"] == 0.0
    assert stats["shortcuts_detected_total"] == 0


@pytest.mark.asyncio
async def test_get_statistics_with_data():
    """Test statistics computation with verification data."""
    verifier = VerifierAgent("qa_agent")

    # Run several verifications
    for i in range(5):
        trajectory = {
            "trajectory_id": f"test_{i}",
            "code": "def test(): pass",
            "benchmark_score": 0.7 + (i * 0.05)
        }
        task = {"type": "test"}
        await verifier.verify_trajectory(trajectory, task)

    stats = verifier.get_stats()

    assert stats["total_verifications"] == 5
    assert 0.0 <= stats["average_score"] <= 1.0
    assert 0.0 <= stats["average_correctness"] <= 1.0
    assert 0.0 <= stats["average_quality"] <= 1.0
    assert 0.0 <= stats["average_robustness"] <= 1.0
    assert 0.0 <= stats["average_generalization"] <= 1.0
    assert stats["shortcuts_detected_total"] >= 0
    assert stats["feedback_items_total"] >= 0


# ==================== Edge Case Tests ====================

def test_edge_case_generation():
    """Test edge case generation."""
    verifier = VerifierAgent("qa_agent")

    trajectory = {"code": "def test(): pass"}
    task = {"type": "code_generation"}

    edge_cases = verifier._generate_edge_cases(trajectory, task)

    assert len(edge_cases) >= 5
    assert "empty_input" in edge_cases
    assert "null_value" in edge_cases
    assert "boundary_min" in edge_cases
    assert "boundary_max" in edge_cases


def test_edge_case_generation_task_specific():
    """Test task-specific edge case generation."""
    verifier = VerifierAgent("qa_agent")

    trajectory = {"code": "def test(): pass"}

    # Search task
    task_search = {"type": "search_algorithm"}
    edge_cases_search = verifier._generate_edge_cases(trajectory, task_search)
    assert "not_found" in edge_cases_search or len(edge_cases_search) > 10

    # Sort task
    task_sort = {"type": "sorting"}
    edge_cases_sort = verifier._generate_edge_cases(trajectory, task_sort)
    assert "already_sorted" in edge_cases_sort or len(edge_cases_sort) > 10


# ==================== Integration Tests ====================

@pytest.mark.asyncio
async def test_multi_criteria_weights():
    """Test that all criteria weights sum to 1.0."""
    config = VerifierConfig()

    total_weight = (
        config.correctness_weight +
        config.quality_weight +
        config.robustness_weight +
        config.generalization_weight
    )

    assert abs(total_weight - 1.0) < 0.01  # Allow small floating point error


@pytest.mark.asyncio
async def test_verification_result_serialization():
    """Test VerificationResult can be serialized."""
    verifier = VerifierAgent("qa_agent")

    trajectory = {
        "trajectory_id": "test_123",
        "code": "def test(): pass",
        "benchmark_score": 0.8
    }
    task = {"type": "test"}

    result = await verifier.verify_trajectory(trajectory, task)
    result_dict = result.to_dict()

    assert isinstance(result_dict, dict)
    assert "verification_score" in result_dict
    assert "correctness_score" in result_dict
    assert "quality_score" in result_dict
    assert "feedback" in result_dict
    assert "metadata" in result_dict


@pytest.mark.asyncio
async def test_verifier_with_solver_trajectory():
    """Test Verifier works with Solver trajectory format."""
    verifier = VerifierAgent("qa_agent")

    # Simulate Solver trajectory format
    solver_trajectory = {
        "trajectory_id": "solver_abc123",
        "code": '''def binary_search(arr, target):
    """Binary search implementation."""
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1''',
        "strategy": "baseline",
        "benchmark_score": 0.92,
        "operator": "baseline",
        "generation": 0
    }

    task = {
        "type": "code_generation",
        "description": "Implement binary search algorithm"
    }

    result = await verifier.verify_trajectory(solver_trajectory, task)

    assert result.correctness_score == 0.92
    assert result.verification_score > 0.0
    assert len(result.feedback) >= 0  # May have feedback even for good code
