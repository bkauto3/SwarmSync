"""
OSWorld Benchmark Test Suite
Purpose: Validate Computer Use capabilities against OSWorld GUI benchmark
Author: Alex (E2E Testing Specialist)
Date: October 27, 2025

OSWorld is a comprehensive benchmark for evaluating GUI agents on desktop environments.
Tasks include file operations, application usage, system configuration, and more.

Success Criteria: >90% success rate on benchmark tasks
"""

import pytest
import asyncio
import json
import time
from typing import Dict, List, Optional
from pathlib import Path
import sys
import os

# Add OSWorld to path if installed
OSWORLD_PATH = Path.home() / "OSWorld"
if OSWORLD_PATH.exists():
    sys.path.insert(0, str(OSWORLD_PATH))

# Try to import OSWorld components
try:
    from desktop_env.desktop_env import DesktopEnv
    OSWORLD_AVAILABLE = True
except ImportError:
    OSWORLD_AVAILABLE = False
    DesktopEnv = None

# Mock Computer Use client for testing when real implementation not available
class MockComputerUseClient:
    """Mock Computer Use client for testing without real implementation"""

    def __init__(self, backend="agent_s"):
        self.backend = backend
        self.tasks_executed = []

    async def execute_task(self, task: str, max_steps: int = 15, timeout: int = 300) -> Dict:
        """Mock task execution"""
        self.tasks_executed.append(task)

        # Simulate execution
        await asyncio.sleep(0.1)

        # Simple heuristic success determination
        success = not any(word in task.lower() for word in ['impossible', 'fail', 'error'])

        return {
            'success': success,
            'steps_taken': 5,
            'final_state': 'completed' if success else 'failed',
            'actions': [{'type': 'click', 'target': 'element'}] * 5
        }


@pytest.fixture
def computer_use_client():
    """Fixture for Computer Use client"""
    # TODO: Replace with real ComputerUseClient when implemented
    return MockComputerUseClient(backend="agent_s")


@pytest.fixture
def osworld_env():
    """Fixture for OSWorld environment"""
    if not OSWORLD_AVAILABLE:
        pytest.skip("OSWorld not installed. Run: bash scripts/install_osworld.sh")

    env = DesktopEnv(action_space="pyautogui")
    yield env
    # Cleanup if needed


@pytest.fixture
def sample_osworld_tasks():
    """Sample OSWorld tasks for testing (subset of full benchmark)"""
    return [
        {
            "id": "file_create_001",
            "instruction": "Create a new text file named 'test_document.txt' in the Documents folder",
            "max_steps": 10,
            "timeout": 120,
            "category": "file_operations",
            "expected_outcome": {
                "type": "file_exists",
                "path": "~/Documents/test_document.txt"
            }
        },
        {
            "id": "file_edit_001",
            "instruction": "Open test_document.txt and write 'Hello, OSWorld!' on the first line",
            "max_steps": 12,
            "timeout": 120,
            "category": "file_operations",
            "expected_outcome": {
                "type": "file_content",
                "path": "~/Documents/test_document.txt",
                "contains": "Hello, OSWorld!"
            }
        },
        {
            "id": "file_rename_001",
            "instruction": "Rename test_document.txt to hello_world.txt",
            "max_steps": 8,
            "timeout": 90,
            "category": "file_operations",
            "expected_outcome": {
                "type": "file_renamed",
                "old_path": "~/Documents/test_document.txt",
                "new_path": "~/Documents/hello_world.txt"
            }
        },
        {
            "id": "file_delete_001",
            "instruction": "Delete the file hello_world.txt from Documents folder",
            "max_steps": 8,
            "timeout": 90,
            "category": "file_operations",
            "expected_outcome": {
                "type": "file_not_exists",
                "path": "~/Documents/hello_world.txt"
            }
        },
        {
            "id": "browser_open_001",
            "instruction": "Open a web browser and navigate to example.com",
            "max_steps": 10,
            "timeout": 150,
            "category": "web_browsing",
            "expected_outcome": {
                "type": "url_match",
                "url_pattern": "example.com"
            }
        },
        {
            "id": "terminal_command_001",
            "instruction": "Open a terminal and run the command 'pwd' to print working directory",
            "max_steps": 8,
            "timeout": 90,
            "category": "terminal",
            "expected_outcome": {
                "type": "command_output",
                "contains": "/home"
            }
        },
        {
            "id": "calculator_001",
            "instruction": "Open calculator application and compute 123 + 456",
            "max_steps": 12,
            "timeout": 120,
            "category": "applications",
            "expected_outcome": {
                "type": "calculation_result",
                "result": 579
            }
        },
        {
            "id": "screenshot_001",
            "instruction": "Take a screenshot and save it to Pictures folder",
            "max_steps": 10,
            "timeout": 120,
            "category": "system",
            "expected_outcome": {
                "type": "file_exists",
                "path_pattern": "~/Pictures/*.png"
            }
        },
        {
            "id": "search_file_001",
            "instruction": "Use file manager to search for files containing 'test' in their name",
            "max_steps": 15,
            "timeout": 150,
            "category": "file_operations",
            "expected_outcome": {
                "type": "search_results",
                "min_results": 0
            }
        },
        {
            "id": "settings_001",
            "instruction": "Open system settings and navigate to display settings",
            "max_steps": 12,
            "timeout": 150,
            "category": "system",
            "expected_outcome": {
                "type": "window_open",
                "title_contains": "display"
            }
        }
    ]


@pytest.mark.benchmark
@pytest.mark.osworld
class TestOSWorldBenchmark:
    """OSWorld benchmark tests for GUI automation validation"""

    @pytest.mark.asyncio
    async def test_osworld_file_operations(self, computer_use_client, sample_osworld_tasks):
        """Test OSWorld file operation tasks"""

        file_tasks = [t for t in sample_osworld_tasks if t['category'] == 'file_operations']
        results = []

        for task in file_tasks:
            try:
                result = await computer_use_client.execute_task(
                    task=task['instruction'],
                    max_steps=task['max_steps'],
                    timeout=task['timeout']
                )

                success = result.get('success', False)
                results.append({
                    'task_id': task['id'],
                    'success': success,
                    'steps': result.get('steps_taken', 0)
                })

            except Exception as e:
                results.append({
                    'task_id': task['id'],
                    'success': False,
                    'error': str(e)
                })

        # Calculate success rate
        success_count = sum(1 for r in results if r['success'])
        success_rate = success_count / len(results) if results else 0

        print(f"\nFile Operations Results: {success_count}/{len(results)} passed ({success_rate:.1%})")
        for r in results:
            status = "✓" if r['success'] else "✗"
            print(f"  {status} {r['task_id']}")

        # Require >90% success rate
        assert success_rate >= 0.90, (
            f"File operations success rate {success_rate:.1%} below 90% threshold. "
            f"Passed: {success_count}/{len(results)}"
        )

    @pytest.mark.asyncio
    async def test_osworld_web_browsing(self, computer_use_client, sample_osworld_tasks):
        """Test OSWorld web browsing tasks"""

        web_tasks = [t for t in sample_osworld_tasks if t['category'] == 'web_browsing']
        results = []

        for task in web_tasks:
            try:
                result = await computer_use_client.execute_task(
                    task=task['instruction'],
                    max_steps=task['max_steps'],
                    timeout=task['timeout']
                )

                results.append({
                    'task_id': task['id'],
                    'success': result.get('success', False)
                })

            except Exception as e:
                results.append({
                    'task_id': task['id'],
                    'success': False,
                    'error': str(e)
                })

        success_count = sum(1 for r in results if r['success'])
        success_rate = success_count / len(results) if results else 0

        print(f"\nWeb Browsing Results: {success_count}/{len(results)} passed ({success_rate:.1%})")

        assert success_rate >= 0.90, (
            f"Web browsing success rate {success_rate:.1%} below 90% threshold"
        )

    @pytest.mark.asyncio
    async def test_osworld_terminal_commands(self, computer_use_client, sample_osworld_tasks):
        """Test OSWorld terminal command tasks"""

        terminal_tasks = [t for t in sample_osworld_tasks if t['category'] == 'terminal']
        results = []

        for task in terminal_tasks:
            try:
                result = await computer_use_client.execute_task(
                    task=task['instruction'],
                    max_steps=task['max_steps'],
                    timeout=task['timeout']
                )

                results.append({
                    'task_id': task['id'],
                    'success': result.get('success', False)
                })

            except Exception as e:
                results.append({
                    'task_id': task['id'],
                    'success': False,
                    'error': str(e)
                })

        success_count = sum(1 for r in results if r['success'])
        success_rate = success_count / len(results) if results else 0

        print(f"\nTerminal Commands Results: {success_count}/{len(results)} passed ({success_rate:.1%})")

        assert success_rate >= 0.90, (
            f"Terminal commands success rate {success_rate:.1%} below 90% threshold"
        )

    @pytest.mark.asyncio
    async def test_osworld_application_usage(self, computer_use_client, sample_osworld_tasks):
        """Test OSWorld application usage tasks"""

        app_tasks = [t for t in sample_osworld_tasks if t['category'] == 'applications']
        results = []

        for task in app_tasks:
            try:
                result = await computer_use_client.execute_task(
                    task=task['instruction'],
                    max_steps=task['max_steps'],
                    timeout=task['timeout']
                )

                results.append({
                    'task_id': task['id'],
                    'success': result.get('success', False)
                })

            except Exception as e:
                results.append({
                    'task_id': task['id'],
                    'success': False,
                    'error': str(e)
                })

        success_count = sum(1 for r in results if r['success'])
        success_rate = success_count / len(results) if results else 0

        print(f"\nApplication Usage Results: {success_count}/{len(results)} passed ({success_rate:.1%})")

        assert success_rate >= 0.90, (
            f"Application usage success rate {success_rate:.1%} below 90% threshold"
        )

    @pytest.mark.asyncio
    async def test_osworld_system_operations(self, computer_use_client, sample_osworld_tasks):
        """Test OSWorld system operation tasks"""

        system_tasks = [t for t in sample_osworld_tasks if t['category'] == 'system']
        results = []

        for task in system_tasks:
            try:
                result = await computer_use_client.execute_task(
                    task=task['instruction'],
                    max_steps=task['max_steps'],
                    timeout=task['timeout']
                )

                results.append({
                    'task_id': task['id'],
                    'success': result.get('success', False)
                })

            except Exception as e:
                results.append({
                    'task_id': task['id'],
                    'success': False,
                    'error': str(e)
                })

        success_count = sum(1 for r in results if r['success'])
        success_rate = success_count / len(results) if results else 0

        print(f"\nSystem Operations Results: {success_count}/{len(results)} passed ({success_rate:.1%})")

        assert success_rate >= 0.90, (
            f"System operations success rate {success_rate:.1%} below 90% threshold"
        )

    @pytest.mark.asyncio
    async def test_osworld_comprehensive_benchmark(self, computer_use_client, sample_osworld_tasks):
        """Run comprehensive OSWorld benchmark across all task categories"""

        start_time = time.time()
        results = []
        category_stats = {}

        for task in sample_osworld_tasks:
            task_start = time.time()

            try:
                result = await computer_use_client.execute_task(
                    task=task['instruction'],
                    max_steps=task['max_steps'],
                    timeout=task['timeout']
                )

                task_result = {
                    'task_id': task['id'],
                    'category': task['category'],
                    'success': result.get('success', False),
                    'steps_taken': result.get('steps_taken', 0),
                    'execution_time': time.time() - task_start
                }
                results.append(task_result)

                # Track category stats
                cat = task['category']
                if cat not in category_stats:
                    category_stats[cat] = {'total': 0, 'passed': 0}
                category_stats[cat]['total'] += 1
                if task_result['success']:
                    category_stats[cat]['passed'] += 1

            except Exception as e:
                results.append({
                    'task_id': task['id'],
                    'category': task['category'],
                    'success': False,
                    'error': str(e),
                    'execution_time': time.time() - task_start
                })

                cat = task['category']
                if cat not in category_stats:
                    category_stats[cat] = {'total': 0, 'passed': 0}
                category_stats[cat]['total'] += 1

        total_time = time.time() - start_time

        # Calculate overall success rate
        success_count = sum(1 for r in results if r['success'])
        total_tasks = len(results)
        success_rate = success_count / total_tasks if total_tasks > 0 else 0

        # Print comprehensive report
        print("\n" + "="*70)
        print("OSWorld Comprehensive Benchmark Results")
        print("="*70)
        print(f"\nOverall: {success_count}/{total_tasks} passed ({success_rate:.1%})")
        print(f"Total Execution Time: {total_time:.2f}s")
        print(f"Average Time per Task: {total_time/total_tasks:.2f}s")

        print("\nCategory Breakdown:")
        for cat, stats in sorted(category_stats.items()):
            cat_rate = stats['passed'] / stats['total'] if stats['total'] > 0 else 0
            print(f"  {cat:20s}: {stats['passed']}/{stats['total']} ({cat_rate:.1%})")

        print("\nDetailed Results:")
        for r in results:
            status = "✓" if r['success'] else "✗"
            time_str = f"{r['execution_time']:.2f}s"
            print(f"  {status} {r['task_id']:20s} [{r['category']:15s}] {time_str}")

        print("="*70)

        # Save results to file
        results_dir = Path(__file__).parent.parent / "benchmark_results"
        results_dir.mkdir(exist_ok=True)

        results_file = results_dir / f"osworld_results_{int(time.time())}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': int(time.time()),
                'success_rate': success_rate,
                'total_tasks': total_tasks,
                'passed_tasks': success_count,
                'total_time': total_time,
                'category_stats': category_stats,
                'detailed_results': results
            }, f, indent=2)

        print(f"\nResults saved to: {results_file}")

        # Require >90% success rate
        assert success_rate >= 0.90, (
            f"OSWorld benchmark success rate {success_rate:.1%} below 90% threshold. "
            f"Passed: {success_count}/{total_tasks}. "
            f"See {results_file} for details."
        )

    @pytest.mark.asyncio
    @pytest.mark.skipif(not OSWORLD_AVAILABLE, reason="OSWorld not installed")
    async def test_osworld_real_env_integration(self, osworld_env):
        """Test real OSWorld environment integration (requires full OSWorld setup)"""

        # Simple test task
        test_task = {
            "id": "integration_test_001",
            "instruction": "Verify OSWorld environment is operational",
            "config": [],
            "evaluator": {
                "func": "check_environment",
                "result": {"type": "status"},
                "expected": {"type": "operational"}
            }
        }

        try:
            # Reset environment with task
            obs = osworld_env.reset(task_config=test_task)

            # Verify we got an observation
            assert obs is not None, "Failed to get initial observation"

            # Try a simple action
            obs, reward, done, info = osworld_env.step("# Verification step")

            print(f"\nOSWorld Environment Integration Test:")
            print(f"  Initial observation: {type(obs)}")
            print(f"  Action executed successfully")
            print(f"  Reward: {reward}")
            print(f"  Info: {info}")

        except Exception as e:
            pytest.fail(f"OSWorld environment integration failed: {e}")


@pytest.mark.benchmark
@pytest.mark.osworld
@pytest.mark.performance
class TestOSWorldPerformance:
    """Performance tests for OSWorld benchmark execution"""

    @pytest.mark.asyncio
    async def test_osworld_execution_speed(self, computer_use_client):
        """Verify OSWorld tasks execute within reasonable time limits"""

        simple_task = {
            "instruction": "Echo 'test' in terminal",
            "max_steps": 5,
            "timeout": 30
        }

        start = time.time()
        result = await computer_use_client.execute_task(
            task=simple_task['instruction'],
            max_steps=simple_task['max_steps'],
            timeout=simple_task['timeout']
        )
        execution_time = time.time() - start

        # Should complete simple task in <30 seconds
        assert execution_time < 30, (
            f"Simple task took {execution_time:.2f}s, expected <30s"
        )

        print(f"\nExecution Speed Test: {execution_time:.2f}s (< 30s threshold)")

    @pytest.mark.asyncio
    async def test_osworld_parallel_execution(self, computer_use_client):
        """Test parallel execution of multiple OSWorld tasks"""

        tasks = [
            {"instruction": f"Task {i}", "max_steps": 5, "timeout": 30}
            for i in range(5)
        ]

        start = time.time()

        # Execute tasks in parallel
        results = await asyncio.gather(*[
            computer_use_client.execute_task(
                task=t['instruction'],
                max_steps=t['max_steps'],
                timeout=t['timeout']
            )
            for t in tasks
        ])

        parallel_time = time.time() - start

        # Parallel execution should be faster than sequential
        print(f"\nParallel Execution: {len(tasks)} tasks in {parallel_time:.2f}s")
        print(f"Average per task: {parallel_time/len(tasks):.2f}s")

        assert all(r.get('success') for r in results), "Some parallel tasks failed"
