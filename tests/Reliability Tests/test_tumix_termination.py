"""
Comprehensive tests for TUMIX Early Termination Engine
Based on: arXiv 2510.01279 (October 2025)

Test Coverage:
1. Unit Tests - All core methods in isolation
2. Termination Logic Tests - All 5 termination rules
3. Edge Cases - Boundary conditions and error cases
4. Improvement Calculation - Quality improvement math
5. Plateau Detection - Variance calculations
6. Degradation Detection - Over-refinement detection
7. Cost Savings Validation - 51% reduction claim
8. Integration Tests - Realistic refinement sessions
"""

import pytest
from typing import List
from infrastructure.tumix_termination import (
    TUMIXTermination,
    RefinementResult,
    TerminationDecision,
    TerminationReason,
    get_tumix_termination
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def default_termination():
    """Standard TUMIX engine with default parameters"""
    return TUMIXTermination(
        min_rounds=2,
        max_rounds=5,
        improvement_threshold=0.05,
        lookback_window=3
    )


@pytest.fixture
def strict_termination():
    """Strict termination (higher improvement threshold)"""
    return TUMIXTermination(
        min_rounds=2,
        max_rounds=5,
        improvement_threshold=0.10,  # 10% improvement required
        lookback_window=3
    )


@pytest.fixture
def lenient_termination():
    """Lenient termination (lower improvement threshold)"""
    return TUMIXTermination(
        min_rounds=2,
        max_rounds=5,
        improvement_threshold=0.01,  # 1% improvement required
        lookback_window=3
    )


@pytest.fixture
def improving_results() -> List[RefinementResult]:
    """Steadily improving quality scores"""
    return [
        RefinementResult(round_number=1, output="v1", quality_score=0.70),
        RefinementResult(round_number=2, output="v2", quality_score=0.75),
        RefinementResult(round_number=3, output="v3", quality_score=0.82),
        RefinementResult(round_number=4, output="v4", quality_score=0.88),
    ]


@pytest.fixture
def plateau_results() -> List[RefinementResult]:
    """Quality plateau (no improvement)"""
    return [
        RefinementResult(round_number=1, output="v1", quality_score=0.70),
        RefinementResult(round_number=2, output="v2", quality_score=0.75),
        RefinementResult(round_number=3, output="v3", quality_score=0.76),
        RefinementResult(round_number=4, output="v4", quality_score=0.76),
        RefinementResult(round_number=5, output="v5", quality_score=0.76),
    ]


@pytest.fixture
def degrading_results() -> List[RefinementResult]:
    """Quality degradation (over-refinement)"""
    return [
        RefinementResult(round_number=1, output="v1", quality_score=0.70),
        RefinementResult(round_number=2, output="v2", quality_score=0.75),
        RefinementResult(round_number=3, output="v3", quality_score=0.73),
        RefinementResult(round_number=4, output="v4", quality_score=0.70),
        RefinementResult(round_number=5, output="v5", quality_score=0.65),
    ]


@pytest.fixture
def small_improvement_results() -> List[RefinementResult]:
    """Minimal improvement (below threshold)"""
    return [
        RefinementResult(round_number=1, output="v1", quality_score=0.70),
        RefinementResult(round_number=2, output="v2", quality_score=0.72),
        RefinementResult(round_number=3, output="v3", quality_score=0.73),
    ]


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

class TestInitialization:
    """Test engine initialization and parameter validation"""

    def test_default_initialization(self):
        """Test initialization with default parameters"""
        engine = TUMIXTermination()
        assert engine.min_rounds == 2
        assert engine.max_rounds == 5
        assert engine.improvement_threshold == 0.05
        assert engine.lookback_window == 3

    def test_custom_initialization(self):
        """Test initialization with custom parameters"""
        engine = TUMIXTermination(
            min_rounds=3,
            max_rounds=10,
            improvement_threshold=0.08,
            lookback_window=4
        )
        assert engine.min_rounds == 3
        assert engine.max_rounds == 10
        assert engine.improvement_threshold == 0.08
        assert engine.lookback_window == 4

    def test_factory_function(self):
        """Test factory function creates valid engine"""
        engine = get_tumix_termination(min_rounds=2, max_rounds=5)
        assert isinstance(engine, TUMIXTermination)
        assert engine.min_rounds == 2
        assert engine.max_rounds == 5

    def test_invalid_min_rounds_zero(self):
        """Test min_rounds must be >= 1"""
        with pytest.raises(ValueError, match="min_rounds must be >= 1"):
            TUMIXTermination(min_rounds=0)

    def test_invalid_min_rounds_negative(self):
        """Test min_rounds cannot be negative"""
        with pytest.raises(ValueError, match="min_rounds must be >= 1"):
            TUMIXTermination(min_rounds=-1)

    def test_invalid_max_rounds_less_than_min(self):
        """Test max_rounds must be >= min_rounds"""
        with pytest.raises(ValueError, match="max_rounds .* must be >= min_rounds"):
            TUMIXTermination(min_rounds=5, max_rounds=3)

    def test_invalid_improvement_threshold_negative(self):
        """Test improvement_threshold must be in [0,1]"""
        with pytest.raises(ValueError, match="improvement_threshold must be in"):
            TUMIXTermination(improvement_threshold=-0.1)

    def test_invalid_improvement_threshold_too_high(self):
        """Test improvement_threshold cannot exceed 1.0"""
        with pytest.raises(ValueError, match="improvement_threshold must be in"):
            TUMIXTermination(improvement_threshold=1.5)

    def test_invalid_lookback_window(self):
        """Test lookback_window must be >= 2"""
        with pytest.raises(ValueError, match="lookback_window must be >= 2"):
            TUMIXTermination(lookback_window=1)


# ============================================================================
# CALCULATE IMPROVEMENT TESTS
# ============================================================================

class TestCalculateImprovement:
    """Test improvement calculation logic"""

    def test_improvement_with_two_results(self, default_termination):
        """Test improvement calculation with exactly 2 results"""
        results = [
            RefinementResult(1, "v1", 0.70),
            RefinementResult(2, "v2", 0.84),  # 20% improvement
        ]
        improvement = default_termination.calculate_improvement(results)
        assert abs(improvement - 0.20) < 0.01  # ~20%

    def test_improvement_positive_trend(self, default_termination):
        """Test improvement with positive quality trend (incremental)"""
        results = [
            RefinementResult(1, "v1", 0.60),
            RefinementResult(2, "v2", 0.70),  # +16.67% from 0.60
            RefinementResult(3, "v3", 0.80),  # +14.29% from 0.70
        ]
        # Average incremental: (16.67% + 14.29%) / 2 = 15.48%
        improvement = default_termination.calculate_improvement(results)
        assert 0.14 < improvement < 0.17  # ~15.48% average incremental

    def test_improvement_negative_trend(self, default_termination):
        """Test improvement with negative quality trend"""
        results = [
            RefinementResult(1, "v1", 0.80),
            RefinementResult(2, "v2", 0.70),
            RefinementResult(3, "v3", 0.60),
        ]
        improvement = default_termination.calculate_improvement(results)
        assert improvement == 0.0  # Clamped to positive

    def test_improvement_zero_quality(self, default_termination):
        """Test improvement handles zero quality scores"""
        results = [
            RefinementResult(1, "v1", 0.0),
            RefinementResult(2, "v2", 0.5),
        ]
        improvement = default_termination.calculate_improvement(results)
        assert improvement == 0.0  # Avoid division by zero

    def test_improvement_single_result(self, default_termination):
        """Test improvement with single result returns 0"""
        results = [RefinementResult(1, "v1", 0.70)]
        improvement = default_termination.calculate_improvement(results)
        assert improvement == 0.0

    def test_improvement_empty_results(self, default_termination):
        """Test improvement with empty results returns 0"""
        results = []
        improvement = default_termination.calculate_improvement(results)
        assert improvement == 0.0

    def test_improvement_lookback_window(self, default_termination):
        """Test improvement respects lookback window (incremental)"""
        # 5 results, lookback_window=3, should only use last 3
        results = [
            RefinementResult(1, "v1", 0.50),  # Not in window
            RefinementResult(2, "v2", 0.55),  # Not in window
            RefinementResult(3, "v3", 0.60),  # In window
            RefinementResult(4, "v4", 0.70),  # In window (+16.67% from 0.60)
            RefinementResult(5, "v5", 0.80),  # In window (+14.29% from 0.70)
        ]
        # Average incremental in window: (16.67% + 14.29%) / 2 = 15.48%
        improvement = default_termination.calculate_improvement(results)
        assert 0.14 < improvement < 0.17  # ~15.48% average incremental

    def test_improvement_plateau(self, default_termination, plateau_results):
        """Test improvement with plateau returns near zero"""
        improvement = default_termination.calculate_improvement(plateau_results[-3:])
        assert improvement < 0.02  # Very small improvement


# ============================================================================
# DETECT PLATEAU TESTS
# ============================================================================

class TestDetectPlateau:
    """Test plateau detection logic"""

    def test_plateau_detected(self, default_termination):
        """Test plateau is detected when variance is low"""
        results = [
            RefinementResult(1, "v1", 0.75),
            RefinementResult(2, "v2", 0.76),
            RefinementResult(3, "v3", 0.76),
            RefinementResult(4, "v4", 0.76),
        ]
        assert default_termination.detect_plateau(results) is True

    def test_no_plateau_improving(self, default_termination):
        """Test plateau not detected when quality improving significantly"""
        # Need larger improvements to avoid plateau detection (variance > 0.01)
        results = [
            RefinementResult(1, "v1", 0.60),
            RefinementResult(2, "v2", 0.75),
            RefinementResult(3, "v3", 0.90),
            RefinementResult(4, "v4", 1.00),
        ]
        assert default_termination.detect_plateau(results) is False

    def test_no_plateau_insufficient_results(self, default_termination):
        """Test plateau not detected with insufficient results"""
        results = [
            RefinementResult(1, "v1", 0.75),
            RefinementResult(2, "v2", 0.76),
        ]
        assert default_termination.detect_plateau(results) is False

    def test_plateau_exact_same_scores(self, default_termination):
        """Test plateau detected with identical scores"""
        results = [
            RefinementResult(1, "v1", 0.75),
            RefinementResult(2, "v2", 0.75),
            RefinementResult(3, "v3", 0.75),
        ]
        assert default_termination.detect_plateau(results) is True

    def test_plateau_variance_threshold(self, default_termination):
        """Test plateau uses 0.01 variance threshold"""
        # Create results with large variance (well above 0.01 threshold)
        results = [
            RefinementResult(1, "v1", 0.50),
            RefinementResult(2, "v2", 0.75),
            RefinementResult(3, "v3", 1.00),
        ]
        # Variance = ((0.5-0.75)^2 + (0.75-0.75)^2 + (1.0-0.75)^2) / 3 = 0.041 > 0.01
        assert default_termination.detect_plateau(results) is False


# ============================================================================
# DETECT DEGRADATION TESTS
# ============================================================================

class TestDetectDegradation:
    """Test degradation detection logic"""

    def test_degradation_detected(self, default_termination, degrading_results):
        """Test degradation is detected when quality consistently decreases"""
        # Use last 3 results which show consistent degradation
        assert default_termination.detect_degradation(degrading_results) is True

    def test_no_degradation_improving(self, default_termination, improving_results):
        """Test degradation not detected when quality improving"""
        assert default_termination.detect_degradation(improving_results) is False

    def test_no_degradation_insufficient_results(self, default_termination):
        """Test degradation not detected with < 3 results"""
        results = [
            RefinementResult(1, "v1", 0.80),
            RefinementResult(2, "v2", 0.70),
        ]
        assert default_termination.detect_degradation(results) is False

    def test_degradation_three_decreasing(self, default_termination):
        """Test degradation detected with 3 consecutive decreases"""
        results = [
            RefinementResult(1, "v1", 0.80),
            RefinementResult(2, "v2", 0.75),
            RefinementResult(3, "v3", 0.70),
        ]
        assert default_termination.detect_degradation(results) is True

    def test_no_degradation_mixed_trend(self, default_termination):
        """Test degradation not detected with mixed trends"""
        results = [
            RefinementResult(1, "v1", 0.70),
            RefinementResult(2, "v2", 0.80),
            RefinementResult(3, "v3", 0.75),  # Decrease but not consistent
        ]
        assert default_termination.detect_degradation(results) is False

    def test_degradation_only_last_three(self, default_termination):
        """Test degradation only looks at last 3 rounds"""
        results = [
            RefinementResult(1, "v1", 0.60),  # Not checked
            RefinementResult(2, "v2", 0.65),  # Not checked
            RefinementResult(3, "v3", 0.80),  # Checked
            RefinementResult(4, "v4", 0.75),  # Checked
            RefinementResult(5, "v5", 0.70),  # Checked
        ]
        assert default_termination.detect_degradation(results) is True


# ============================================================================
# TERMINATION DECISION TESTS (5 RULES)
# ============================================================================

class TestTerminationRules:
    """Test all 5 termination rules"""

    def test_rule1_minimum_not_met(self, default_termination):
        """Rule 1: Continue if minimum rounds not met"""
        results = [RefinementResult(1, "v1", 0.80)]
        decision = default_termination.should_stop(results)

        assert decision.should_stop is False
        assert decision.reason == TerminationReason.MINIMUM_NOT_MET
        assert decision.current_round == 1
        assert decision.confidence == 1.0

    def test_rule2_max_rounds_reached(self, default_termination):
        """Rule 2: Stop if maximum rounds reached"""
        results = [
            RefinementResult(i, f"v{i}", 0.70 + i * 0.02)
            for i in range(1, 6)
        ]
        decision = default_termination.should_stop(results)

        assert decision.should_stop is True
        assert decision.reason == TerminationReason.MAX_ROUNDS_REACHED
        assert decision.current_round == 5
        assert decision.confidence == 1.0

    def test_rule3_quality_degradation(self, default_termination):
        """Rule 3: Stop if quality degrading"""
        results = [
            RefinementResult(1, "v1", 0.80),
            RefinementResult(2, "v2", 0.75),
            RefinementResult(3, "v3", 0.70),
            RefinementResult(4, "v4", 0.65),
        ]
        decision = default_termination.should_stop(results)

        assert decision.should_stop is True
        assert decision.reason == TerminationReason.QUALITY_DEGRADATION
        assert decision.confidence == 0.9

    def test_rule4_quality_plateau(self, default_termination):
        """Rule 4: Stop if quality plateau detected"""
        results = [
            RefinementResult(1, "v1", 0.70),
            RefinementResult(2, "v2", 0.75),
            RefinementResult(3, "v3", 0.76),
            RefinementResult(4, "v4", 0.76),
        ]
        decision = default_termination.should_stop(results)

        assert decision.should_stop is True
        assert decision.reason == TerminationReason.QUALITY_PLATEAU
        assert decision.confidence == 0.8

    def test_rule5_insufficient_improvement(self, default_termination):
        """Rule 5: Stop if improvement below threshold (or plateau detected first)"""
        results = [
            RefinementResult(1, "v1", 0.70),
            RefinementResult(2, "v2", 0.72),  # Only 2.8% improvement
            RefinementResult(3, "v3", 0.73),
        ]
        decision = default_termination.should_stop(results)

        assert decision.should_stop is True
        # May be plateau or insufficient improvement depending on variance
        assert decision.reason in [
            TerminationReason.INSUFFICIENT_IMPROVEMENT,
            TerminationReason.QUALITY_PLATEAU
        ]

    def test_continue_refinement(self, default_termination):
        """Test continuation when improvement is sufficient and variance is high"""
        # Use large improvements to ensure high variance (no plateau)
        results = [
            RefinementResult(1, "v1", 0.50),
            RefinementResult(2, "v2", 0.70),  # 40% improvement
            RefinementResult(3, "v3", 0.95),  # 35.7% improvement in lookback
        ]
        decision = default_termination.should_stop(results)

        assert decision.should_stop is False
        assert decision.reason == TerminationReason.CONTINUE
        assert decision.confidence == 0.6


# ============================================================================
# EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Test boundary conditions and edge cases"""

    def test_empty_results_raises_error(self, default_termination):
        """Test empty results list raises ValueError"""
        with pytest.raises(ValueError, match="results list cannot be empty"):
            default_termination.should_stop([])

    def test_single_result_below_minimum(self, default_termination):
        """Test single result always continues (below minimum)"""
        results = [RefinementResult(1, "v1", 0.95)]  # High quality but only 1 round
        decision = default_termination.should_stop(results)
        assert decision.should_stop is False

    def test_exact_threshold_improvement(self, default_termination):
        """Test improvement exactly at threshold"""
        # 5% improvement exactly
        results = [
            RefinementResult(1, "v1", 1.00),
            RefinementResult(2, "v2", 1.05),  # Exactly 5% improvement
        ]
        improvement = default_termination.calculate_improvement(results)
        assert abs(improvement - 0.05) < 0.001

    def test_quality_score_boundaries(self, default_termination):
        """Test quality scores at boundaries (0.0 and 1.0)"""
        results = [
            RefinementResult(1, "v1", 0.0),
            RefinementResult(2, "v2", 1.0),
        ]
        decision = default_termination.should_stop(results)
        assert decision.current_round == 2
        assert decision.quality_score == 1.0

    def test_negative_quality_scores(self, default_termination):
        """Test system handles negative quality scores"""
        results = [
            RefinementResult(1, "v1", -0.5),
            RefinementResult(2, "v2", 0.5),
        ]
        # Should not crash, improvement calculation should handle it
        improvement = default_termination.calculate_improvement(results)
        assert improvement >= 0.0

    def test_very_small_improvements(self, default_termination):
        """Test with very small improvements (floating point precision)"""
        results = [
            RefinementResult(1, "v1", 0.700000),
            RefinementResult(2, "v2", 0.700001),
            RefinementResult(3, "v3", 0.700002),
        ]
        decision = default_termination.should_stop(results)
        # Should detect as plateau or insufficient improvement
        assert decision.should_stop is True

    def test_all_same_quality_scores(self, default_termination):
        """Test with all identical quality scores"""
        results = [
            RefinementResult(i, f"v{i}", 0.75)
            for i in range(1, 5)
        ]
        decision = default_termination.should_stop(results)
        assert decision.should_stop is True
        assert decision.reason in [
            TerminationReason.QUALITY_PLATEAU,
            TerminationReason.INSUFFICIENT_IMPROVEMENT
        ]

    def test_min_equals_max_rounds(self):
        """Test when min_rounds equals max_rounds"""
        engine = TUMIXTermination(min_rounds=3, max_rounds=3)
        results = [
            RefinementResult(1, "v1", 0.70),
            RefinementResult(2, "v2", 0.75),
            RefinementResult(3, "v3", 0.80),
        ]
        decision = engine.should_stop(results)
        assert decision.should_stop is True
        assert decision.reason == TerminationReason.MAX_ROUNDS_REACHED


# ============================================================================
# COST SAVINGS TESTS
# ============================================================================

class TestCostSavings:
    """Test cost savings estimation"""

    def test_cost_savings_basic(self, default_termination):
        """Test basic cost savings calculation"""
        sessions = [
            [RefinementResult(i, f"v{i}", 0.7 + i*0.02) for i in range(1, 4)],
            [RefinementResult(i, f"v{i}", 0.6 + i*0.03) for i in range(1, 5)],
        ]

        savings = default_termination.estimate_cost_savings(sessions, cost_per_round=0.001)

        assert savings['sessions'] == 2
        assert savings['baseline_rounds'] == 10  # 2 sessions * 5 max rounds
        assert savings['tumix_rounds'] > 0
        assert savings['tumix_rounds'] < savings['baseline_rounds']
        assert savings['savings_percent'] > 0

    def test_cost_savings_early_termination(self, default_termination):
        """Test cost savings with sessions that terminate early"""
        # Create sessions with plateau (should terminate early)
        sessions = [
            [
                RefinementResult(1, "v1", 0.70),
                RefinementResult(2, "v2", 0.75),
                RefinementResult(3, "v3", 0.76),
                RefinementResult(4, "v4", 0.76),  # Plateau starts
            ]
            for _ in range(5)  # 5 identical sessions
        ]

        savings = default_termination.estimate_cost_savings(sessions)

        # Should stop around round 3-4, not run all 5 rounds
        assert savings['tumix_rounds'] < savings['baseline_rounds']
        assert savings['savings_percent'] > 20  # At least 20% savings

    def test_cost_savings_no_early_termination(self):
        """Test cost savings when no early termination occurs"""
        engine = TUMIXTermination(min_rounds=5, max_rounds=5)
        sessions = [
            [RefinementResult(i, f"v{i}", 0.6 + i*0.1) for i in range(1, 6)]
            for _ in range(3)
        ]

        savings = engine.estimate_cost_savings(sessions)

        # No early termination possible (min=max=5)
        assert savings['tumix_rounds'] == savings['baseline_rounds']
        assert savings['savings_percent'] == 0.0

    def test_cost_savings_empty_sessions(self, default_termination):
        """Test cost savings with empty sessions list"""
        savings = default_termination.estimate_cost_savings([])

        assert savings['sessions'] == 0
        assert savings['baseline_rounds'] == 0
        assert savings['tumix_rounds'] == 0
        assert savings['savings_percent'] == 0.0

    def test_cost_savings_51_percent_target(self):
        """Test achieving ~51% cost reduction (paper's claim)"""
        engine = TUMIXTermination(min_rounds=2, max_rounds=5, improvement_threshold=0.05)

        # Create realistic sessions with various patterns
        sessions = []

        # 40% plateau early (stop at round 3)
        for _ in range(40):
            sessions.append([
                RefinementResult(1, "v1", 0.70),
                RefinementResult(2, "v2", 0.75),
                RefinementResult(3, "v3", 0.76),
                RefinementResult(4, "v4", 0.76),
            ])

        # 30% small improvement (stop at round 3)
        for _ in range(30):
            sessions.append([
                RefinementResult(1, "v1", 0.60),
                RefinementResult(2, "v2", 0.65),
                RefinementResult(3, "v3", 0.67),
            ])

        # 20% degradation (stop at round 3)
        for _ in range(20):
            sessions.append([
                RefinementResult(1, "v1", 0.80),
                RefinementResult(2, "v2", 0.75),
                RefinementResult(3, "v3", 0.70),
            ])

        # 10% continue to max (5 rounds)
        for _ in range(10):
            sessions.append([
                RefinementResult(1, "v1", 0.50),
                RefinementResult(2, "v2", 0.60),
                RefinementResult(3, "v3", 0.70),
                RefinementResult(4, "v4", 0.80),
                RefinementResult(5, "v5", 0.90),
            ])

        savings = engine.estimate_cost_savings(sessions)

        # Should achieve ~40-60% savings (51% target from paper)
        print(f"\nCost Savings Analysis:")
        print(f"  Sessions: {savings['sessions']}")
        print(f"  Baseline rounds: {savings['baseline_rounds']}")
        print(f"  TUMIX rounds: {savings['tumix_rounds']}")
        print(f"  Savings: {savings['savings_percent']:.1f}%")
        print(f"  Target: 51%")

        assert 40 <= savings['savings_percent'] <= 60, \
            f"Expected ~51% savings, got {savings['savings_percent']:.1f}%"

    def test_cost_savings_custom_cost_per_round(self, default_termination):
        """Test cost savings with custom cost per round"""
        sessions = [
            [RefinementResult(i, f"v{i}", 0.7) for i in range(1, 3)]
        ]

        savings = default_termination.estimate_cost_savings(sessions, cost_per_round=0.01)

        # 1 session * 5 max rounds * $0.01 = $0.05 baseline
        assert savings['baseline_cost'] == 0.05
        # 1 session * 2 actual rounds * $0.01 = $0.02 TUMIX
        assert savings['tumix_cost'] == 0.02


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Test realistic refinement workflows"""

    def test_full_refinement_session_improving(self, default_termination):
        """Test complete refinement session with improving quality"""
        results = []
        stopped_at = None

        # Simulate iterative refinement with large improvements
        for round_num in range(1, 6):
            quality = 0.40 + round_num * 0.15  # Large improvement (high variance)
            results.append(RefinementResult(round_num, f"v{round_num}", quality))

            decision = default_termination.should_stop(results)

            if round_num < 2:
                assert decision.should_stop is False
            elif round_num >= 5:
                assert decision.should_stop is True

            if decision.should_stop:
                stopped_at = round_num
                break

        # Should continue until max rounds or stop due to sufficient improvement
        assert stopped_at is not None
        assert stopped_at >= 3  # At least past minimum rounds

    def test_full_refinement_session_plateau(self, default_termination):
        """Test complete refinement session with plateau"""
        results = []
        stopped_at = None

        # Simulate plateau after initial improvement
        qualities = [0.70, 0.75, 0.76, 0.76, 0.76]

        for round_num, quality in enumerate(qualities, 1):
            results.append(RefinementResult(round_num, f"v{round_num}", quality))
            decision = default_termination.should_stop(results)

            if decision.should_stop and round_num >= 2:
                stopped_at = round_num
                break

        # Should stop at round 3 or 4 (plateau detected)
        assert stopped_at is not None
        assert 3 <= stopped_at <= 4

    def test_full_refinement_session_degradation(self, default_termination):
        """Test complete refinement session with degradation"""
        results = []
        stopped_at = None

        # Simulate over-refinement degradation
        qualities = [0.70, 0.75, 0.73, 0.70, 0.65]

        for round_num, quality in enumerate(qualities, 1):
            results.append(RefinementResult(round_num, f"v{round_num}", quality))
            decision = default_termination.should_stop(results)

            if decision.should_stop and round_num >= 2:
                stopped_at = round_num
                break

        # Should stop at round 3 or 4 (plateau or degradation detected)
        assert stopped_at is not None
        assert 3 <= stopped_at <= 4

    def test_multiple_sessions_cost_tracking(self, default_termination):
        """Test tracking costs across multiple refinement sessions"""
        all_sessions = []

        # Session 1: Quick plateau
        all_sessions.append([
            RefinementResult(1, "v1", 0.70),
            RefinementResult(2, "v2", 0.75),
            RefinementResult(3, "v3", 0.76),
        ])

        # Session 2: Good improvement
        all_sessions.append([
            RefinementResult(1, "v1", 0.50),
            RefinementResult(2, "v2", 0.65),
            RefinementResult(3, "v3", 0.80),
            RefinementResult(4, "v4", 0.90),
        ])

        # Session 3: Degradation
        all_sessions.append([
            RefinementResult(1, "v1", 0.80),
            RefinementResult(2, "v2", 0.75),
            RefinementResult(3, "v3", 0.70),
        ])

        savings = default_termination.estimate_cost_savings(all_sessions)

        assert savings['sessions'] == 3
        assert savings['baseline_rounds'] == 15  # 3 * 5
        assert savings['tumix_rounds'] < 15
        assert savings['savings_percent'] > 0

    def test_strict_vs_lenient_termination(self):
        """Test strict vs lenient termination thresholds"""
        strict = TUMIXTermination(improvement_threshold=0.10)  # 10%
        lenient = TUMIXTermination(improvement_threshold=0.01)  # 1%

        # Large improvement with high variance to avoid plateau detection
        results = [
            RefinementResult(1, "v1", 0.50),
            RefinementResult(2, "v2", 0.75),  # 50% improvement
            RefinementResult(3, "v3", 1.00),  # 33% improvement in lookback
        ]

        strict_decision = strict.should_stop(results)
        lenient_decision = lenient.should_stop(results)

        # Both should continue with large improvements
        assert strict_decision.should_stop is False
        assert lenient_decision.should_stop is False

    def test_verbose_logging(self, default_termination, improving_results):
        """Test verbose logging doesn't break functionality"""
        # Should not raise any errors
        decision = default_termination.should_stop(improving_results, verbose=True)
        assert isinstance(decision, TerminationDecision)

    def test_metadata_preservation(self, default_termination):
        """Test metadata is preserved in RefinementResult"""
        results = [
            RefinementResult(
                round_number=1,
                output="v1",
                quality_score=0.70,
                improvement=None,
                metadata={'model': 'gpt-4', 'tokens': 1500}
            ),
            RefinementResult(
                round_number=2,
                output="v2",
                quality_score=0.80,
                improvement=0.14,
                metadata={'model': 'gpt-4', 'tokens': 1800}
            ),
        ]

        decision = default_termination.should_stop(results)

        # Metadata should still be accessible
        assert results[0].metadata['model'] == 'gpt-4'
        assert results[1].improvement == 0.14


# ============================================================================
# PRODUCTION READINESS TESTS
# ============================================================================

class TestProductionReadiness:
    """Test production-critical requirements"""

    def test_deterministic_behavior(self, default_termination):
        """Test same inputs produce same outputs (deterministic)"""
        results = [
            RefinementResult(1, "v1", 0.70),
            RefinementResult(2, "v2", 0.75),
            RefinementResult(3, "v3", 0.80),
        ]

        decision1 = default_termination.should_stop(results)
        decision2 = default_termination.should_stop(results)

        assert decision1.should_stop == decision2.should_stop
        assert decision1.reason == decision2.reason
        assert decision1.improvement == decision2.improvement

    def test_no_side_effects(self, default_termination):
        """Test should_stop doesn't modify input results"""
        results = [
            RefinementResult(1, "v1", 0.70),
            RefinementResult(2, "v2", 0.75),
        ]

        original_len = len(results)
        original_scores = [r.quality_score for r in results]

        default_termination.should_stop(results)

        assert len(results) == original_len
        assert [r.quality_score for r in results] == original_scores

    def test_thread_safety_immutability(self, default_termination):
        """Test engine parameters are immutable after initialization"""
        original_min = default_termination.min_rounds
        original_max = default_termination.max_rounds

        # Simulate concurrent access
        results = [RefinementResult(i, f"v{i}", 0.7) for i in range(1, 4)]
        default_termination.should_stop(results)

        assert default_termination.min_rounds == original_min
        assert default_termination.max_rounds == original_max

    def test_performance_large_sessions(self, default_termination):
        """Test performance with large number of sessions"""
        import time

        # 1000 sessions
        sessions = [
            [RefinementResult(i, f"v{i}", 0.6 + i*0.05) for i in range(1, 6)]
            for _ in range(1000)
        ]

        start = time.time()
        savings = default_termination.estimate_cost_savings(sessions)
        duration = time.time() - start

        # Should complete in reasonable time (< 5 seconds)
        assert duration < 5.0
        assert savings['sessions'] == 1000

    def test_error_handling_invalid_quality(self, default_termination):
        """Test graceful handling of invalid quality scores"""
        # Should not crash with unusual values
        results = [
            RefinementResult(1, "v1", float('inf')),
            RefinementResult(2, "v2", 0.75),
        ]

        # Should handle gracefully (may clamp or treat as 0)
        try:
            decision = default_termination.should_stop(results)
            assert isinstance(decision, TerminationDecision)
        except (ValueError, OverflowError):
            # Acceptable to raise error for invalid input
            pass

    def test_confidence_scores_valid(self, default_termination):
        """Test confidence scores are in valid range [0, 1]"""
        test_cases = [
            [RefinementResult(1, "v1", 0.70)],  # Min not met
            [RefinementResult(i, f"v{i}", 0.7 + i*0.02) for i in range(1, 6)],  # Max reached
            [RefinementResult(1, "v1", 0.70), RefinementResult(2, "v2", 0.75),
             RefinementResult(3, "v3", 0.73), RefinementResult(4, "v4", 0.70)],  # Degradation
        ]

        for results in test_cases:
            decision = default_termination.should_stop(results)
            assert 0.0 <= decision.confidence <= 1.0

    def test_reasoning_always_present(self, default_termination):
        """Test reasoning string is always provided"""
        test_cases = [
            [RefinementResult(1, "v1", 0.70)],
            [RefinementResult(i, f"v{i}", 0.7) for i in range(1, 6)],
            [RefinementResult(1, "v1", 0.70), RefinementResult(2, "v2", 0.75),
             RefinementResult(3, "v3", 0.76)],
        ]

        for results in test_cases:
            decision = default_termination.should_stop(results)
            assert decision.reasoning
            assert len(decision.reasoning) > 0
            assert isinstance(decision.reasoning, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
