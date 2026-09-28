"""Task lifecycle management for MCP Server."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from .integration import create_harness_integration
from .types import FeedbackType, RoundResult, TaskContext, TaskStatus


class TaskManager:
    """Manages long-horizon task lifecycle and state."""

    def __init__(self, state_root: str = "~/.lh-harness"):
        self.state_root = Path(state_root).expanduser()
        self.tasks: dict[str, TaskContext] = {}
        self._task_locks: dict[str, asyncio.Lock] = {}
        self.harness_integration = create_harness_integration(state_root)

    def start_task(
        self,
        goal: str,
        workspace: str,
        max_rounds: int = 25,
        config: dict[str, Any] | None = None,
    ) -> TaskContext:
        """Start a new long-horizon task.

        Args:
            goal: Task goal description
            workspace: Working directory path
            max_rounds: Maximum execution rounds
            config: Optional configuration overrides

        Returns:
            TaskContext with task_id and initial status
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        task = TaskContext(
            task_id=task_id,
            goal=goal,
            workspace=workspace,
            max_rounds=max_rounds,
            status="started",
            metadata=config or {},
        )

        self.tasks[task_id] = task
        self._task_locks[task_id] = asyncio.Lock()

        # Create task directory
        task_dir = self.state_root / "tasks" / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        return task

    def get_task(self, task_id: str) -> TaskContext | None:
        """Get task context by ID."""
        return self.tasks.get(task_id)

    async def execute_round(
        self,
        task_id: str,
        user_input: str | None = None,
    ) -> RoundResult:
        """Execute one plan-act-verify round.

        Integrates with the existing Manager/Executor/Auditor logic.

        Args:
            task_id: Task identifier
            user_input: Optional user instruction or feedback

        Returns:
            RoundResult with plan, execution, and audit details
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        async with self._task_locks[task_id]:
            task.current_round += 1
            task.status = "running"

            # Execute round using harness integration
            result = await self.harness_integration.execute_round_with_harness(
                task=task,
                user_input=user_input,
            )

            # Store round data with detailed information
            round_data = {
                "round_id": result.round_id,
                "round_index": task.current_round,
                "status": result.status,
                "timestamp": "",  # TODO: Add timestamp
                "summary": result.plan[:200] if result.plan else "",
                "manager": {
                    "input_prompt": f"Task: {task.goal}",
                    "output": result.plan,
                    "model": task.metadata.get("config", {}).get("manager_model", ""),
                    "duration_ms": result.duration_ms // 3,
                    "tokens_used": 0,  # TODO: Track tokens
                },
                "executor": {
                    "type": "cli",  # TODO: Detect from result
                    "input_prompt": result.plan,
                    "output": result.execution_result,
                    "model": task.metadata.get("config", {}).get("executor_model", ""),
                    "duration_ms": result.duration_ms // 3,
                    "tokens_used": 0,  # TODO: Track tokens
                },
                "auditor": {
                    "input_prompt": result.execution_result,
                    "output": result.audit_report,
                    "model": task.metadata.get("config", {}).get("auditor_model", ""),
                    "duration_ms": result.duration_ms // 3,
                    "tokens_used": 0,  # TODO: Track tokens
                },
                "checkpoint": result.checkpoint,
            }

            task.rounds.append(round_data)

            if result.checkpoint:
                task.checkpoints.append(result.checkpoint)
                task.verified_progress = result.checkpoint.get(
                    "verified_state", f"Completed {task.current_round} rounds"
                )

            # Update task state based on result
            if task.current_round >= task.max_rounds:
                task.status = "completed"
            elif result.status == "blocked":
                task.status = "blocked"
            else:
                task.status = "paused"

            return result

    def get_checkpoint(self, task_id: str) -> dict[str, Any] | None:
        """Get latest verified checkpoint for a task."""
        task = self.get_task(task_id)
        if not task or not task.checkpoints:
            return None

        return {
            "checkpoint_id": f"{task_id}_cp{len(task.checkpoints)}",
            "verified_state": task.verified_progress,
            "completed_items": [],  # TODO: Extract from checkpoints
            "artifacts": [],  # TODO: List artifacts
            "timestamp": task.checkpoints[-1].get("timestamp", ""),
            "checkpoint_data": task.checkpoints[-1],
        }

    def recover_task(
        self,
        task_id: str,
        checkpoint_id: str | None = None,
    ) -> dict[str, Any]:
        """Recover task from a checkpoint.

        Args:
            task_id: Task identifier
            checkpoint_id: Optional specific checkpoint to recover from

        Returns:
            Recovery information including recovered state and next plan
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        checkpoint = self.get_checkpoint(task_id)
        if not checkpoint:
            raise ValueError(f"No checkpoint found for task {task_id}")

        task.status = "paused"

        return {
            "recovered_state": checkpoint["verified_state"],
            "next_plan": f"Resume from round {task.current_round + 1}",
            "checkpoint_id": checkpoint["checkpoint_id"],
        }

    def pause_task(self, task_id: str) -> None:
        """Pause a running task."""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.status == "running":
            task.status = "paused"

    def stop_task(self, task_id: str, keep_artifacts: bool = True) -> None:
        """Stop and cleanup a task.

        Args:
            task_id: Task identifier
            keep_artifacts: Whether to preserve output files
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.status = "completed"

        if not keep_artifacts:
            # TODO: Cleanup artifacts
            pass

    def inject_feedback(
        self,
        task_id: str,
        feedback: str,
        feedback_type: FeedbackType,
    ) -> None:
        """Inject human feedback into a running task.

        Args:
            task_id: Task identifier
            feedback: Feedback content
            feedback_type: Type of feedback (correction/guidance/approval)
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Store feedback in metadata
        if "feedbacks" not in task.metadata:
            task.metadata["feedbacks"] = []

        task.metadata["feedbacks"].append({
            "round": task.current_round,
            "type": feedback_type,
            "content": feedback,
        })

    def get_audit_trail(self, task_id: str) -> dict[str, Any]:
        """Get complete audit trail for a task.

        Args:
            task_id: Task identifier

        Returns:
            Complete execution and verification history
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        return {
            "task_id": task_id,
            "goal": task.goal,
            "status": task.status,
            "total_rounds": len(task.rounds),
            "rounds": task.rounds,
            "checkpoints": task.checkpoints,
            "feedbacks": task.metadata.get("feedbacks", []),
        }
