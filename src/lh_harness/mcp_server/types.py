"""Type definitions for MCP Server."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

TaskStatus = Literal["started", "running", "paused", "completed", "failed", "blocked"]
FeedbackType = Literal["correction", "guidance", "approval"]


@dataclass
class TaskContext:
    """Context for a managed long-horizon task."""

    task_id: str
    goal: str
    workspace: str
    max_rounds: int
    status: TaskStatus
    current_round: int = 0
    verified_progress: str = ""
    current_step: str = ""
    next_action: str = ""
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    rounds: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoundResult:
    """Result of a single plan-act-verify round."""

    round_id: str
    plan: str
    execution_result: str
    audit_report: str
    status: Literal["complete", "incomplete", "blocked"]
    checkpoint: dict[str, Any] | None = None
    duration_ms: int = 0
