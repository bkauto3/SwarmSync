"""
TaskDAG: Directed Acyclic Graph for hierarchical task decomposition
Based on Deep Agent (arXiv:2502.07056)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import networkx as nx


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Single task node in the DAG"""
    task_id: Optional[str] = None
    task_type: Optional[str] = None  # e.g., "design", "implement", "test", "deploy"
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)  # Parent task IDs
    metadata: Dict[str, Any] = field(default_factory=dict)
    agent_assigned: Optional[str] = None
    estimated_duration: Optional[float] = None
    # Backwards compatibility: support 'id' parameter as alias for 'task_id'
    id: Optional[str] = None

    def __post_init__(self):
        """Handle id/task_id aliasing for backwards compatibility"""
        # If 'id' provided but not 'task_id', use 'id' for 'task_id'
        if self.id is not None and self.task_id is None:
            self.task_id = self.id
        # If 'task_id' provided but not 'id', set 'id' to match
        elif self.task_id is not None and self.id is None:
            self.id = self.task_id
        # If neither provided, raise error
        elif self.task_id is None and self.id is None:
            raise ValueError("Either task_id or id must be provided")

        # Validate / infer required fields
        if self.task_type is None:
            inferred_type = None
            if isinstance(self.metadata, dict):
                inferred_type = (
                    self.metadata.get("business_type")
                    or self.metadata.get("task_type")
                    or self.metadata.get("agent_type")
                )
            self.task_type = inferred_type or "generic"
        if self.description is None:
            raise ValueError("description is required")


class TaskDAG:
    """Directed Acyclic Graph for task decomposition"""

    def __init__(self):
        self.graph = nx.DiGraph()
        self.tasks: Dict[str, Task] = {}

    def add_task(self, task: Task) -> None:
        """Add task node to DAG"""
        self.tasks[task.task_id] = task
        self.graph.add_node(task.task_id)

    def add_dependency(self, parent_id: str, child_id: str) -> None:
        """Add edge: parent must complete before child"""
        if parent_id not in self.tasks or child_id not in self.tasks:
            raise ValueError(f"Task not found: {parent_id} or {child_id}")
        self.graph.add_edge(parent_id, child_id)
        self.tasks[child_id].dependencies.append(parent_id)

    def get_children(self, task_id: str) -> List[str]:
        """Get child tasks (tasks that depend on this one)"""
        return list(self.graph.successors(task_id))

    def get_parents(self, task_id: str) -> List[str]:
        """Get parent tasks (dependencies)"""
        return list(self.graph.predecessors(task_id))

    def get_root_tasks(self) -> List[str]:
        """Get tasks with no dependencies"""
        return [tid for tid, task in self.tasks.items() if not task.dependencies]

    def get_leaf_tasks(self) -> List[str]:
        """Get tasks with no children"""
        return [tid for tid in self.tasks if self.graph.out_degree(tid) == 0]

    def topological_sort(self) -> List[str]:
        """Get execution order (respects dependencies)"""
        try:
            return list(nx.topological_sort(self.graph))
        except (nx.NetworkXError, nx.NetworkXUnfeasible) as e:
            raise ValueError(f"DAG has cycles: {e}")

    def has_cycle(self) -> bool:
        """Check if graph contains cycles"""
        return not nx.is_directed_acyclic_graph(self.graph)

    def get_all_task_ids(self) -> List[str]:
        """Get all task IDs in DAG"""
        return list(self.tasks.keys())

    def get_all_tasks(self) -> List[Task]:
        """Get all Task objects in DAG (for test compatibility)"""
        return list(self.tasks.values())

    def mark_complete(self, task_id: str) -> None:
        """Mark task as completed"""
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED

    def copy(self) -> 'TaskDAG':
        """Create deep copy of DAG"""
        new_dag = TaskDAG()
        new_dag.graph = self.graph.copy()
        new_dag.tasks = {tid: task for tid, task in self.tasks.items()}
        return new_dag

    def max_depth(self) -> int:
        """Calculate maximum depth of DAG"""
        if not self.tasks:
            return 0
        return nx.dag_longest_path_length(self.graph)

    def __len__(self) -> int:
        return len(self.tasks)

    def __repr__(self) -> str:
        return f"TaskDAG(tasks={len(self.tasks)}, edges={self.graph.number_of_edges()})"
