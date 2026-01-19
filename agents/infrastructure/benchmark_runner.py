"""
Benchmark Runner - Empirical Validation for Darwin Evolution
Infrastructure for measuring agent performance objectively

CRITICAL FOR DARWIN: No formal proof required - just empirical improvement

Benchmarks:
- SWE-Bench: Software engineering tasks (industry standard)
- Genesis Benchmark: Custom business generation tasks
- Unit tests: Agent-specific test suites
- Performance metrics: Speed, accuracy, resource usage

Based on Darwin reference: github.com/jennyzzt/dgm/blob/main/swe_bench/harness.py
"""

import asyncio
import json
import logging
import subprocess
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from infrastructure import get_logger
from infrastructure.sandbox import get_sandbox, SandboxResult

logger = get_logger("benchmark_runner")


class BenchmarkType(Enum):
    """Types of benchmarks available"""
    SWE_BENCH = "swe_bench"  # Software engineering benchmark
    GENESIS_CUSTOM = "genesis_custom"  # Custom business generation tasks
    UNIT_TESTS = "unit_tests"  # Agent-specific unit tests
    PERFORMANCE = "performance"  # Speed/resource metrics


class BenchmarkStatus(Enum):
    """Status of benchmark execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class BenchmarkResult:
    """Result from benchmark execution"""
    benchmark_id: str
    benchmark_type: str  # BenchmarkType
    agent_name: str
    agent_version: str
    status: str  # BenchmarkStatus
    overall_score: float  # 0.0 to 1.0
    metrics: Dict[str, float]  # Detailed metrics
    tasks_total: int
    tasks_passed: int
    tasks_failed: int
    execution_time: float  # seconds
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class Task:
    """Single benchmark task"""
    task_id: str
    description: str
    input_data: Dict[str, Any]
    expected_output: Any
    test_code: str
    timeout: int = 60
    tags: List[str] = field(default_factory=list)


class BenchmarkRunner:
    """
    Benchmark execution engine for validating agent improvements

    Supports multiple benchmark types:
    1. SWE-Bench: Industry-standard software engineering tasks
    2. Genesis Custom: Business generation and management tasks
    3. Unit Tests: Agent-specific test suites
    4. Performance: Speed and resource usage metrics

    Usage:
        runner = BenchmarkRunner()
        result = await runner.run_benchmark(
            agent_code_path="agents/spec_agent.py",
            benchmark_type=BenchmarkType.GENESIS_CUSTOM
        )
    """

    def __init__(self):
        """Initialize benchmark runner with sandbox"""
        self.sandbox = get_sandbox()
        self.benchmarks_dir = Path("benchmarks")
        self.benchmarks_dir.mkdir(exist_ok=True)

        # Load benchmark suites
        self._benchmark_suites: Dict[str, List[Task]] = {}
        self._load_benchmark_suites()

    def _load_benchmark_suites(self):
        """Load all available benchmark suites"""
        logger.info("Loading benchmark suites...")

        # Genesis Custom Benchmark (our main validation suite)
        self._benchmark_suites["genesis_custom"] = self._create_genesis_benchmark()

        # Unit test benchmark
        self._benchmark_suites["unit_tests"] = []  # Populated dynamically per agent

        logger.info(f"Loaded {len(self._benchmark_suites)} benchmark suites")

    def _create_genesis_benchmark(self) -> List[Task]:
        """
        Create Genesis custom benchmark for business generation agents

        Tests agent capabilities on:
        - Specification generation
        - Deployment automation
        - Security analysis
        - Performance optimization
        """
        tasks = [
            Task(
                task_id="spec_generation_saas",
                description="Generate technical specification for a SaaS business",
                input_data={
                    "business_type": "saas",
                    "description": "AI-powered project management tool",
                },
                expected_output={
                    "has_tech_stack": True,
                    "has_features": True,
                    "has_architecture": True,
                },
                test_code="""
def test_spec_generation(result):
    assert "tech_stack" in result or "technology" in result.lower()
    assert "features" in result or "feature" in result.lower()
    assert len(result) > 500, "Specification too short"
    return True
""",
                tags=["spec", "saas"],
            ),
            Task(
                task_id="spec_generation_ecommerce",
                description="Generate specification for ecommerce business",
                input_data={
                    "business_type": "ecommerce",
                    "description": "Sustainable fashion marketplace",
                },
                expected_output={
                    "has_payment_integration": True,
                    "has_product_catalog": True,
                },
                test_code="""
def test_ecommerce_spec(result):
    assert "payment" in result.lower() or "checkout" in result.lower()
                    assert "product" in result.lower() or "catalog" in result.lower()
    return True
""",
                tags=["spec", "ecommerce"],
            ),
            Task(
                task_id="deployment_validation",
                description="Validate deployment configuration",
                input_data={
                    "platform": "vercel",
                    "framework": "nextjs",
                },
                expected_output={
                    "has_build_command": True,
                    "has_env_vars": True,
                },
                test_code="""
def test_deployment_config(result):
    assert "build" in result.lower() or "deploy" in result.lower()
    assert isinstance(result, (dict, str))
    return True
""",
                tags=["deploy"],
            ),
            Task(
                task_id="security_scan",
                description="Identify security vulnerabilities",
                input_data={
                    "code_snippet": "def process_data(user_input): return eval(user_input)",
                },
                expected_output={
                    "vulnerabilities_found": True,
                    "severity_high": True,
                },
                test_code="""
def test_security_scan(result):
    # Should detect eval() as vulnerability
    result_lower = str(result).lower()
    assert "vulnerability" in result_lower or "security" in result_lower or "risk" in result_lower
    return True
""",
                tags=["security"],
            ),
            Task(
                task_id="performance_optimization",
                description="Suggest performance improvements",
                input_data={
                    "code": "for i in range(1000000): list.append(i)",
                    "metric": "execution_time",
                },
                expected_output={
                    "has_suggestions": True,
                },
                test_code="""
def test_performance_optimization(result):
    result_lower = str(result).lower()
    # Should suggest list comprehension or generator
    assert "optimize" in result_lower or "improve" in result_lower or "faster" in result_lower
    return True
""",
                tags=["performance"],
            ),
        ]

        return tasks

    async def run_benchmark(
        self,
        agent_code_path: Path,
        agent_name: str,
        agent_version: str,
        benchmark_type: BenchmarkType = BenchmarkType.GENESIS_CUSTOM,
        task_filter: Optional[List[str]] = None,
    ) -> BenchmarkResult:
        """
        Run benchmark suite against an agent

        Args:
            agent_code_path: Path to agent code file
            agent_name: Name of agent being tested
            agent_version: Version identifier
            benchmark_type: Which benchmark suite to run
            task_filter: Optional list of task IDs to run (None = all)

        Returns:
            BenchmarkResult with scores and details
        """
        benchmark_id = f"bench_{uuid.uuid4().hex[:8]}"

        logger.info(f"🎯 Starting benchmark: {benchmark_id}")
        logger.info(f"Agent: {agent_name} v{agent_version}")
        logger.info(f"Type: {benchmark_type.value}")

        start_time = time.time()

        # Get tasks for this benchmark
        tasks = self._benchmark_suites.get(benchmark_type.value, [])

        if not tasks:
            logger.warning(f"No tasks found for benchmark type: {benchmark_type.value}")
            return BenchmarkResult(
                benchmark_id=benchmark_id,
                benchmark_type=benchmark_type.value,
                agent_name=agent_name,
                agent_version=agent_version,
                status=BenchmarkStatus.FAILED.value,
                overall_score=0.0,
                metrics={},
                tasks_total=0,
                tasks_passed=0,
                tasks_failed=0,
                execution_time=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_message="No tasks available for this benchmark type",
            )

        # Filter tasks if requested
        if task_filter:
            tasks = [t for t in tasks if t.task_id in task_filter]

        logger.info(f"Running {len(tasks)} tasks...")

        # Execute tasks
        task_results = []
        for i, task in enumerate(tasks):
            logger.info(f"Task {i+1}/{len(tasks)}: {task.task_id}")

            try:
                result = await self._execute_task(agent_code_path, task)
                task_results.append(result)
            except Exception as e:
                logger.error(f"Task {task.task_id} failed: {e}")
                task_results.append({
                    "task_id": task.task_id,
                    "passed": False,
                    "error": str(e),
                })

        # Compute metrics
        tasks_passed = sum(1 for r in task_results if r.get("passed", False))
        tasks_failed = len(task_results) - tasks_passed

        overall_score = tasks_passed / len(task_results) if task_results else 0.0

        # Detailed metrics
        metrics = {
            "accuracy": overall_score,
            "precision": tasks_passed / max(tasks_passed + tasks_failed, 1),
            "task_success_rate": overall_score,
        }

        # Aggregate by tags
        tag_metrics = defaultdict(lambda: {"passed": 0, "total": 0})
        for result, task in zip(task_results, tasks):
            for tag in task.tags:
                tag_metrics[tag]["total"] += 1
                if result.get("passed", False):
                    tag_metrics[tag]["passed"] += 1

        metrics.update({
            f"{tag}_success_rate": stats["passed"] / max(stats["total"], 1)
            for tag, stats in tag_metrics.items()
        })

        execution_time = time.time() - start_time

        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            benchmark_type=benchmark_type.value,
            agent_name=agent_name,
            agent_version=agent_version,
            status=BenchmarkStatus.COMPLETED.value,
            overall_score=overall_score,
            metrics=metrics,
            tasks_total=len(tasks),
            tasks_passed=tasks_passed,
            tasks_failed=tasks_failed,
            execution_time=execution_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details={"task_results": task_results},
        )

        logger.info(f"✅ Benchmark complete: {overall_score:.1%} ({tasks_passed}/{len(tasks)})")

        # Save results
        await self._save_results(result)

        return result

    async def _execute_task(self, agent_code_path: Path, task: Task) -> Dict[str, Any]:
        """
        Execute single benchmark task

        Returns:
            Dictionary with task results
        """
        try:
            # Create test harness code
            test_harness = f"""
import sys
import json

# Import agent code
sys.path.insert(0, '/workspace')

{agent_code_path.read_text()}

# Task input
input_data = {json.dumps(task.input_data)}

# Execute agent (this depends on agent's API - we'll use a generic pattern)
try:
    # Try common agent patterns
    if 'generate' in dir():
        result = generate(**input_data)
    elif 'run' in dir():
        result = run(**input_data)
    elif 'execute' in dir():
        result = execute(**input_data)
    else:
        # Fallback: just import and check it's valid Python
        result = {{"status": "imported", "input": input_data}}

    # Run test validation
    {task.test_code}

    test_passed = test_{task.task_id.split('_')[0]}(str(result))

    print(json.dumps({{
        "passed": test_passed,
        "result": str(result)[:500],  # Truncate for safety
    }}))

except Exception as e:
    print(json.dumps({{
        "passed": False,
        "error": str(e),
    }}))
"""

            # Execute in sandbox
            sandbox_result = await self.sandbox.execute_code(
                code=test_harness,
                timeout=task.timeout,
                memory_limit="512m",
            )

            # Parse result
            if sandbox_result.exit_code == 0 and sandbox_result.stdout:
                try:
                    task_result = json.loads(sandbox_result.stdout.strip().split('\n')[-1])
                    return {
                        "task_id": task.task_id,
                        **task_result,
                    }
                except json.JSONDecodeError:
                    return {
                        "task_id": task.task_id,
                        "passed": False,
                        "error": "Invalid JSON output",
                        "stdout": sandbox_result.stdout,
                    }
            else:
                return {
                    "task_id": task.task_id,
                    "passed": False,
                    "error": sandbox_result.stderr or "Execution failed",
                }

        except Exception as e:
            return {
                "task_id": task.task_id,
                "passed": False,
                "error": str(e),
            }

    async def _save_results(self, result: BenchmarkResult):
        """Save benchmark results to disk"""
        results_dir = self.benchmarks_dir / "results" / result.agent_name
        results_dir.mkdir(parents=True, exist_ok=True)

        result_file = results_dir / f"{result.benchmark_id}.json"
        result_file.write_text(json.dumps(asdict(result), indent=2))

        logger.info(f"Results saved: {result_file}")

    async def run_unit_tests(
        self,
        agent_code_path: Path,
        test_path: Path,
        agent_name: str,
        agent_version: str,
    ) -> BenchmarkResult:
        """
        Run pytest unit tests for an agent

        Args:
            agent_code_path: Path to agent code
            test_path: Path to test file
            agent_name: Agent name
            agent_version: Version identifier

        Returns:
            BenchmarkResult with test results
        """
        benchmark_id = f"unittest_{uuid.uuid4().hex[:8]}"

        logger.info(f"Running unit tests: {test_path}")

        start_time = time.time()

        try:
            # Combine code and tests
            combined_code = f"""
# Agent code
{agent_code_path.read_text()}

# Tests
{test_path.read_text()}

# Run pytest
if __name__ == "__main__":
    import pytest
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
"""

            # Execute in sandbox
            sandbox_result = await self.sandbox.execute_code(
                code=combined_code,
                timeout=300,  # 5 minutes for tests
                requirements=["pytest"],
            )

            # Parse pytest output to count passed/failed
            output = sandbox_result.stdout + sandbox_result.stderr

            # Simple parsing (in production, use pytest JSON output)
            tasks_passed = output.count(" PASSED")
            tasks_failed = output.count(" FAILED")
            tasks_total = tasks_passed + tasks_failed

            overall_score = tasks_passed / max(tasks_total, 1)

            execution_time = time.time() - start_time

            return BenchmarkResult(
                benchmark_id=benchmark_id,
                benchmark_type=BenchmarkType.UNIT_TESTS.value,
                agent_name=agent_name,
                agent_version=agent_version,
                status=BenchmarkStatus.COMPLETED.value,
                overall_score=overall_score,
                metrics={"test_pass_rate": overall_score},
                tasks_total=tasks_total,
                tasks_passed=tasks_passed,
                tasks_failed=tasks_failed,
                execution_time=execution_time,
                timestamp=datetime.now(timezone.utc).isoformat(),
                details={"output": output},
            )

        except Exception as e:
            logger.error(f"Unit test execution failed: {e}")
            return BenchmarkResult(
                benchmark_id=benchmark_id,
                benchmark_type=BenchmarkType.UNIT_TESTS.value,
                agent_name=agent_name,
                agent_version=agent_version,
                status=BenchmarkStatus.FAILED.value,
                overall_score=0.0,
                metrics={},
                tasks_total=0,
                tasks_passed=0,
                tasks_failed=0,
                execution_time=time.time() - start_time,
                timestamp=datetime.now(timezone.utc).isoformat(),
                error_message=str(e),
            )


# Convenience functions
_runner_instance = None


def get_benchmark_runner() -> BenchmarkRunner:
    """Get singleton benchmark runner"""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = BenchmarkRunner()
    return _runner_instance


async def run_benchmark(agent_code_path: Path, agent_name: str, **kwargs) -> BenchmarkResult:
    """
    Convenience function to run benchmark

    Example:
        result = await run_benchmark(
            agent_code_path=Path("agents/spec_agent.py"),
            agent_name="spec_agent",
            agent_version="v1.0"
        )
    """
    runner = get_benchmark_runner()
    return await runner.run_benchmark(agent_code_path, agent_name, **kwargs)


if __name__ == "__main__":
    # Test benchmark runner
    async def test_runner():
        runner = BenchmarkRunner()

        # Create dummy agent for testing
        dummy_agent = Path("/tmp/dummy_agent.py")
        dummy_agent.write_text("""
def generate(business_type, description):
    return f"Specification for {business_type}: {description}. Tech stack: Python, React. Features: User auth, Dashboard."

def run(**kwargs):
    return generate(**kwargs)
""")

        # Run benchmark
        result = await runner.run_benchmark(
            agent_code_path=dummy_agent,
            agent_name="dummy_agent",
            agent_version="test",
            benchmark_type=BenchmarkType.GENESIS_CUSTOM,
        )

        print(f"\n✅ Benchmark Results:")
        print(f"Overall Score: {result.overall_score:.1%}")
        print(f"Tasks: {result.tasks_passed}/{result.tasks_total} passed")
        print(f"Metrics: {json.dumps(result.metrics, indent=2)}")

        # Cleanup
        dummy_agent.unlink()

    asyncio.run(test_runner())
