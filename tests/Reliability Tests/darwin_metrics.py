"""
Darwin Performance Monitoring and Metrics Collection
Version: 1.0
Date: October 19, 2025

Monitors and tracks performance metrics for Darwin evolution cycles.
Validates evolution cycle time meets <10 minute target.
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import statistics

logger = logging.getLogger(__name__)


@dataclass
class EvolutionCycleMetrics:
    """Metrics for a single evolution cycle"""
    request_id: str
    agent_name: str
    evolution_type: str
    start_time: float
    end_time: float
    duration_seconds: float
    duration_minutes: float
    success: bool
    improvement_delta: float
    error_message: Optional[str] = None

    # Detailed timing breakdown
    htdag_decomposition_time: Optional[float] = None
    halo_routing_time: Optional[float] = None
    aop_validation_time: Optional[float] = None
    darwin_analysis_time: Optional[float] = None
    darwin_generation_time: Optional[float] = None
    sandbox_validation_time: Optional[float] = None
    benchmark_execution_time: Optional[float] = None

    # Resource usage
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

    # Benchmark results
    baseline_score: Optional[float] = None
    final_score: Optional[float] = None
    test_cases_passed: Optional[int] = None
    test_cases_total: Optional[int] = None

    def meets_slo(self, target_minutes: float = 10.0) -> bool:
        """Check if evolution cycle meets SLO target"""
        return self.duration_minutes < target_minutes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class DarwinPerformanceMonitor:
    """
    Monitor Darwin evolution cycle performance

    Tracks:
    - Evolution cycle times
    - Component-level timing
    - Success/failure rates
    - Resource usage
    - Benchmark scores
    """

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("metrics/darwin")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.metrics: List[EvolutionCycleMetrics] = []
        self.current_cycle: Optional[Dict[str, Any]] = None

        logger.info(f"Darwin Performance Monitor initialized, output: {self.output_dir}")

    def start_cycle(self, request_id: str, agent_name: str, evolution_type: str):
        """Start monitoring a new evolution cycle"""
        self.current_cycle = {
            "request_id": request_id,
            "agent_name": agent_name,
            "evolution_type": evolution_type,
            "start_time": time.time(),
            "component_times": {}
        }
        logger.info(f"Started monitoring cycle: {request_id}")

    def record_component_time(self, component: str, duration: float):
        """Record timing for a specific component"""
        if self.current_cycle:
            self.current_cycle["component_times"][component] = duration
            logger.debug(f"Component {component} took {duration:.3f}s")

    def end_cycle(
        self,
        success: bool,
        improvement_delta: float = 0.0,
        error_message: str = None,
        baseline_score: float = None,
        final_score: float = None,
        test_cases_passed: int = None,
        test_cases_total: int = None
    ):
        """End monitoring and save metrics"""
        if not self.current_cycle:
            logger.warning("No active cycle to end")
            return

        end_time = time.time()
        duration = end_time - self.current_cycle["start_time"]

        # Create metrics object
        component_times = self.current_cycle["component_times"]

        metrics = EvolutionCycleMetrics(
            request_id=self.current_cycle["request_id"],
            agent_name=self.current_cycle["agent_name"],
            evolution_type=self.current_cycle["evolution_type"],
            start_time=self.current_cycle["start_time"],
            end_time=end_time,
            duration_seconds=duration,
            duration_minutes=duration / 60,
            success=success,
            improvement_delta=improvement_delta,
            error_message=error_message,
            htdag_decomposition_time=component_times.get("htdag_decomposition"),
            halo_routing_time=component_times.get("halo_routing"),
            aop_validation_time=component_times.get("aop_validation"),
            darwin_analysis_time=component_times.get("darwin_analysis"),
            darwin_generation_time=component_times.get("darwin_generation"),
            sandbox_validation_time=component_times.get("sandbox_validation"),
            benchmark_execution_time=component_times.get("benchmark_execution"),
            baseline_score=baseline_score,
            final_score=final_score,
            test_cases_passed=test_cases_passed,
            test_cases_total=test_cases_total
        )

        # Add to metrics list
        self.metrics.append(metrics)

        # Log results
        slo_met = "✅" if metrics.meets_slo() else "❌"
        logger.info(
            f"{slo_met} Cycle {metrics.request_id} completed: "
            f"{metrics.duration_minutes:.2f} min, "
            f"success={success}, "
            f"improvement={improvement_delta:+.3f}"
        )

        # Save to file
        self._save_metrics(metrics)

        # Reset current cycle
        self.current_cycle = None

        return metrics

    def _save_metrics(self, metrics: EvolutionCycleMetrics):
        """Save metrics to JSON file"""
        try:
            # Save individual cycle
            cycle_file = self.output_dir / f"cycle_{metrics.request_id}.json"
            with open(cycle_file, 'w') as f:
                json.dump(metrics.to_dict(), f, indent=2)

            # Append to aggregate file
            aggregate_file = self.output_dir / "all_cycles.jsonl"
            with open(aggregate_file, 'a') as f:
                f.write(json.dumps(metrics.to_dict()) + "\n")

            logger.debug(f"Saved metrics to {cycle_file}")

        except Exception as e:
            logger.error(f"Error saving metrics: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get aggregate statistics across all cycles"""
        if not self.metrics:
            return {
                "total_cycles": 0,
                "message": "No metrics collected yet"
            }

        durations = [m.duration_minutes for m in self.metrics]
        successful = [m for m in self.metrics if m.success]
        improvements = [m.improvement_delta for m in successful if m.improvement_delta > 0]

        stats = {
            "total_cycles": len(self.metrics),
            "successful_cycles": len(successful),
            "failed_cycles": len(self.metrics) - len(successful),
            "success_rate": len(successful) / len(self.metrics) if self.metrics else 0.0,

            # Timing statistics
            "avg_duration_minutes": statistics.mean(durations),
            "median_duration_minutes": statistics.median(durations),
            "min_duration_minutes": min(durations),
            "max_duration_minutes": max(durations),
            "std_duration_minutes": statistics.stdev(durations) if len(durations) > 1 else 0.0,

            # SLO compliance
            "cycles_meeting_slo": sum(1 for m in self.metrics if m.meets_slo()),
            "slo_compliance_rate": sum(1 for m in self.metrics if m.meets_slo()) / len(self.metrics),

            # Improvement statistics
            "avg_improvement": statistics.mean(improvements) if improvements else 0.0,
            "median_improvement": statistics.median(improvements) if improvements else 0.0,
            "cycles_with_improvement": len(improvements),

            # Agent breakdown
            "agents_evolved": list(set(m.agent_name for m in self.metrics)),
            "evolution_types": list(set(m.evolution_type for m in self.metrics))
        }

        return stats

    def print_report(self):
        """Print performance report to console"""
        stats = self.get_statistics()

        print("\n" + "="*60)
        print("DARWIN EVOLUTION PERFORMANCE REPORT")
        print("="*60)

        print(f"\nTotal Cycles: {stats['total_cycles']}")
        print(f"Successful: {stats['successful_cycles']} ({stats['success_rate']:.1%})")
        print(f"Failed: {stats['failed_cycles']}")

        print(f"\nTiming (minutes):")
        print(f"  Average: {stats['avg_duration_minutes']:.2f}")
        print(f"  Median: {stats['median_duration_minutes']:.2f}")
        print(f"  Range: {stats['min_duration_minutes']:.2f} - {stats['max_duration_minutes']:.2f}")
        print(f"  Std Dev: {stats['std_duration_minutes']:.2f}")

        print(f"\nSLO Compliance (<10 min target):")
        print(f"  Cycles meeting SLO: {stats['cycles_meeting_slo']}/{stats['total_cycles']}")
        print(f"  Compliance rate: {stats['slo_compliance_rate']:.1%}")

        if stats.get('cycles_with_improvement', 0) > 0:
            print(f"\nImprovement:")
            print(f"  Cycles with improvement: {stats['cycles_with_improvement']}")
            print(f"  Average improvement: {stats['avg_improvement']:+.3f}")
            print(f"  Median improvement: {stats['median_improvement']:+.3f}")

        print(f"\nAgents Evolved: {', '.join(stats['agents_evolved'])}")
        print(f"Evolution Types: {', '.join(stats['evolution_types'])}")

        print("\n" + "="*60)

    def export_to_csv(self, filename: str = "darwin_metrics.csv"):
        """Export metrics to CSV file"""
        import csv

        output_file = self.output_dir / filename

        if not self.metrics:
            logger.warning("No metrics to export")
            return

        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.metrics[0].to_dict().keys())
            writer.writeheader()

            for metric in self.metrics:
                writer.writerow(metric.to_dict())

        logger.info(f"Exported {len(self.metrics)} metrics to {output_file}")

    def load_metrics_from_disk(self):
        """Load previously saved metrics from disk"""
        aggregate_file = self.output_dir / "all_cycles.jsonl"

        if not aggregate_file.exists():
            logger.warning(f"No metrics file found at {aggregate_file}")
            return

        loaded = 0
        with open(aggregate_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    metric = EvolutionCycleMetrics(**data)
                    self.metrics.append(metric)
                    loaded += 1
                except Exception as e:
                    logger.error(f"Error loading metric: {e}")

        logger.info(f"Loaded {loaded} metrics from disk")


# Global monitor instance
_monitor: Optional[DarwinPerformanceMonitor] = None


def get_performance_monitor(output_dir: Path = None) -> DarwinPerformanceMonitor:
    """Get or create global performance monitor"""
    global _monitor

    if _monitor is None:
        _monitor = DarwinPerformanceMonitor(output_dir)

    return _monitor


def measure_evolution_cycle(request_id: str, agent_name: str, evolution_type: str):
    """
    Decorator to measure evolution cycle performance

    Usage:
        @measure_evolution_cycle("req-123", "marketing_agent", "improve_agent")
        async def evolve_agent():
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            monitor.start_cycle(request_id, agent_name, evolution_type)

            try:
                result = await func(*args, **kwargs)

                # Extract metrics from result if available
                if hasattr(result, 'success'):
                    monitor.end_cycle(
                        success=result.success,
                        improvement_delta=result.improvement_delta.get("overall_score", 0.0),
                        error_message=result.error_message
                    )
                else:
                    monitor.end_cycle(success=True)

                return result

            except Exception as e:
                monitor.end_cycle(success=False, error_message=str(e))
                raise

        return wrapper
    return decorator
