"""
Tests for Socratic-Zero Benchmarking

Tests the benchmarking system for Analyst agent.
"""

import json
import pytest
import sys
from pathlib import Path

# Add scripts to path
SCRIPTS_PATH = Path(__file__).parent.parent / "scripts" / "socratic_zero"
sys.path.insert(0, str(SCRIPTS_PATH))

from benchmark_analyst import AnalystBenchmark


@pytest.fixture
def temp_test_data_file(tmp_path):
    """Create temporary test data file."""
    test_file = tmp_path / "test_set.jsonl"
    
    questions = [
        {
            "id": "test_001",
            "category": "Revenue Analysis",
            "question": "Analyze revenue trends",
            "expected_answer": "Revenue increased 15%",
            "difficulty": "easy"
        },
        {
            "id": "test_002",
            "category": "Market Analysis",
            "question": "Estimate market size",
            "expected_answer": "$5B TAM",
            "difficulty": "medium"
        },
        {
            "id": "test_003",
            "category": "Strategic Planning",
            "question": "Develop growth strategy",
            "expected_answer": "Focus on product expansion",
            "difficulty": "hard"
        }
    ]
    
    with open(test_file, 'w') as f:
        for q in questions:
            f.write(json.dumps(q) + "\n")
    
    return test_file


@pytest.fixture
def temp_results_dir(tmp_path):
    """Create temporary results directory."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    return results_dir


class TestAnalystBenchmark:
    """Test suite for AnalystBenchmark class."""
    
    def test_benchmark_initialization(self, temp_test_data_file, temp_results_dir):
        """Test benchmark initialization."""
        benchmark = AnalystBenchmark(
            test_data_file=temp_test_data_file,
            results_dir=temp_results_dir
        )
        
        assert benchmark.test_data_file == temp_test_data_file
        assert benchmark.results_dir == temp_results_dir
        assert benchmark.results_dir.exists()
    
    def test_load_test_set(self, temp_test_data_file, temp_results_dir):
        """Test loading test dataset."""
        benchmark = AnalystBenchmark(
            test_data_file=temp_test_data_file,
            results_dir=temp_results_dir
        )
        
        questions = benchmark.load_test_set()
        
        assert len(questions) == 3
        assert all("id" in q for q in questions)
        assert all("question" in q for q in questions)
        assert all("category" in q for q in questions)
    
    def test_benchmark_model_creates_results(self, temp_test_data_file, temp_results_dir, tmp_path):
        """Test that benchmarking creates results file."""
        benchmark = AnalystBenchmark(
            test_data_file=temp_test_data_file,
            results_dir=temp_results_dir
        )
        
        questions = benchmark.load_test_set()
        model_path = tmp_path / "test_model"
        model_path.mkdir()
        
        metrics = benchmark.benchmark_model(
            model_path=model_path,
            model_name="test_model",
            test_questions=questions
        )
        
        assert "overall_score" in metrics
        assert "total_questions" in metrics
        assert "avg_inference_time" in metrics
        assert "category_scores" in metrics
        
        assert metrics["total_questions"] == 3
    
    def test_evaluate_response_scoring(self, temp_test_data_file, temp_results_dir):
        """Test response evaluation scoring."""
        benchmark = AnalystBenchmark(
            test_data_file=temp_test_data_file,
            results_dir=temp_results_dir
        )
        
        # Test different response types
        short_response = "Short answer"
        score1 = benchmark._evaluate_response(short_response, "Expected", "Revenue Analysis")
        
        detailed_response = "Detailed analysis with reasoning and comprehensive evaluation of the scenario"
        score2 = benchmark._evaluate_response(detailed_response, "Expected", "Revenue Analysis")
        
        # Detailed response should score higher
        assert score2 > score1
        
        # Scores should be between 0 and 1
        assert 0 <= score1 <= 1
        assert 0 <= score2 <= 1
    
    def test_calculate_metrics(self, temp_test_data_file, temp_results_dir):
        """Test metrics calculation."""
        benchmark = AnalystBenchmark(
            test_data_file=temp_test_data_file,
            results_dir=temp_results_dir
        )
        
        results = [
            {
                "question_id": "q1",
                "category": "Revenue Analysis",
                "score": 0.8,
                "inference_time": 0.5
            },
            {
                "question_id": "q2",
                "category": "Revenue Analysis",
                "score": 0.9,
                "inference_time": 0.6
            },
            {
                "question_id": "q3",
                "category": "Market Analysis",
                "score": 0.7,
                "inference_time": 0.4
            }
        ]
        
        metrics = benchmark._calculate_metrics(results, total_time=1.5)
        
        assert metrics["overall_score"] == pytest.approx(0.8, abs=0.01)
        assert metrics["total_questions"] == 3
        assert metrics["avg_inference_time"] == pytest.approx(0.5, abs=0.01)
        assert metrics["total_time"] == 1.5
        
        # Check category scores
        assert "Revenue Analysis" in metrics["category_scores"]
        assert "Market Analysis" in metrics["category_scores"]
        assert metrics["category_scores"]["Revenue Analysis"] == pytest.approx(0.85, abs=0.01)
    
    def test_compare_models(self, temp_test_data_file, temp_results_dir):
        """Test model comparison."""
        benchmark = AnalystBenchmark(
            test_data_file=temp_test_data_file,
            results_dir=temp_results_dir
        )
        
        baseline_metrics = {
            "overall_score": 0.70,
            "category_scores": {
                "Revenue Analysis": 0.65,
                "Market Analysis": 0.75
            }
        }
        
        socratic_metrics = {
            "overall_score": 0.80,
            "category_scores": {
                "Revenue Analysis": 0.75,
                "Market Analysis": 0.85
            }
        }
        
        comparison = benchmark.compare_models(baseline_metrics, socratic_metrics)
        
        assert comparison["baseline_score"] == 0.70
        assert comparison["socratic_zero_score"] == 0.80
        assert comparison["improvement_percentage"] == pytest.approx(14.29, abs=0.1)
        assert comparison["meets_target"] is True  # >10% improvement
        
        # Check category improvements
        assert "Revenue Analysis" in comparison["category_improvements"]
        assert "Market Analysis" in comparison["category_improvements"]
    
    def test_compare_models_below_target(self, temp_test_data_file, temp_results_dir):
        """Test model comparison when improvement is below target."""
        benchmark = AnalystBenchmark(
            test_data_file=temp_test_data_file,
            results_dir=temp_results_dir
        )
        
        baseline_metrics = {
            "overall_score": 0.70,
            "category_scores": {"Revenue Analysis": 0.70}
        }
        
        socratic_metrics = {
            "overall_score": 0.75,  # Only 7.14% improvement
            "category_scores": {"Revenue Analysis": 0.75}
        }
        
        comparison = benchmark.compare_models(baseline_metrics, socratic_metrics)
        
        assert comparison["improvement_percentage"] == pytest.approx(7.14, abs=0.1)
        assert comparison["meets_target"] is False  # <10% improvement
    
    def test_run_inference_placeholder(self, temp_test_data_file, temp_results_dir, tmp_path):
        """Test inference placeholder."""
        benchmark = AnalystBenchmark(
            test_data_file=temp_test_data_file,
            results_dir=temp_results_dir
        )
        
        model_path = tmp_path / "test_model"
        model_path.mkdir()
        
        response = benchmark._run_inference(model_path, "Test question")
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_create_default_test_set(self, tmp_path):
        """Test default test set creation."""
        test_file = tmp_path / "default_test.jsonl"
        results_dir = tmp_path / "results"
        results_dir.mkdir()
        
        benchmark = AnalystBenchmark(
            test_data_file=test_file,
            results_dir=results_dir
        )
        
        # Should create default test set
        assert test_file.exists()
        
        # Load and verify
        questions = benchmark.load_test_set()
        assert len(questions) > 0
        assert all("id" in q for q in questions)
        assert all("category" in q for q in questions)
    
    def test_results_saved_to_file(self, temp_test_data_file, temp_results_dir, tmp_path):
        """Test that results are saved to file."""
        benchmark = AnalystBenchmark(
            test_data_file=temp_test_data_file,
            results_dir=temp_results_dir
        )
        
        questions = benchmark.load_test_set()
        model_path = tmp_path / "test_model"
        model_path.mkdir()
        
        benchmark.benchmark_model(
            model_path=model_path,
            model_name="test_model",
            test_questions=questions
        )
        
        # Check that results file was created
        result_files = list(temp_results_dir.glob("test_model_results_*.json"))
        assert len(result_files) > 0
        
        # Verify results file content
        with open(result_files[0], 'r') as f:
            results = json.load(f)
        
        assert "model_name" in results
        assert "metrics" in results
        assert "detailed_results" in results
    
    def test_category_breakdown_in_metrics(self, temp_test_data_file, temp_results_dir):
        """Test that metrics include category breakdown."""
        benchmark = AnalystBenchmark(
            test_data_file=temp_test_data_file,
            results_dir=temp_results_dir
        )
        
        results = [
            {"category": "Revenue Analysis", "score": 0.8, "inference_time": 0.5},
            {"category": "Revenue Analysis", "score": 0.9, "inference_time": 0.6},
            {"category": "Market Analysis", "score": 0.7, "inference_time": 0.4}
        ]
        
        metrics = benchmark._calculate_metrics(results, total_time=1.5)
        
        assert "category_scores" in metrics
        assert len(metrics["category_scores"]) == 2
        assert "Revenue Analysis" in metrics["category_scores"]
        assert "Market Analysis" in metrics["category_scores"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

