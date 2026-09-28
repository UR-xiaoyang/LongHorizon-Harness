"""Advanced task management APIs for MCP Server.

Provides fine-grained control over task execution, configuration,
and debugging capabilities.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import TaskContext


class AdvancedTaskManager:
    """Advanced task management with fine-grained control."""

    def __init__(self, task_manager):
        """Initialize with base TaskManager."""
        self.task_manager = task_manager

    # ========== Configuration Management ==========

    def get_task_config(self, task_id: str) -> dict[str, Any]:
        """Get complete task configuration.

        Args:
            task_id: Task identifier

        Returns:
            Complete configuration including models, timeouts, etc.
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        return {
            "task_id": task_id,
            "goal": task.goal,
            "workspace": task.workspace,
            "max_rounds": task.max_rounds,
            "current_config": task.metadata.get("config", {}),
        }

    def update_task_config(
        self,
        task_id: str,
        config_updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update task configuration dynamically.

        Args:
            task_id: Task identifier
            config_updates: Configuration fields to update

        Returns:
            Updated configuration with changed fields
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        updated_fields = []

        # Update max_rounds
        if "max_rounds" in config_updates:
            task.max_rounds = config_updates["max_rounds"]
            updated_fields.append("max_rounds")

        # Update config metadata
        if "config" not in task.metadata:
            task.metadata["config"] = {}

        for key, value in config_updates.items():
            if key != "max_rounds":
                task.metadata["config"][key] = value
                updated_fields.append(key)

        return {
            "success": True,
            "updated_fields": updated_fields,
            "new_config": self.get_task_config(task_id),
        }

    # ========== Round History Management ==========

    def get_round_detail(
        self,
        task_id: str,
        round_id: str | int,
    ) -> dict[str, Any]:
        """Get detailed information about a specific round.

        Args:
            task_id: Task identifier
            round_id: Round ID or index (0-based)

        Returns:
            Complete round details including all role outputs
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Find the round
        if isinstance(round_id, int):
            round_index = round_id
            if round_index >= len(task.rounds):
                raise ValueError(f"Round index {round_index} out of range")
            round_data = task.rounds[round_index]
        else:
            # Find by round_id string
            round_data = None
            round_index = -1
            for idx, r in enumerate(task.rounds):
                if r.get("round_id") == round_id:
                    round_data = r
                    round_index = idx
                    break
            if not round_data:
                raise ValueError(f"Round {round_id} not found")

        return {
            "round_id": round_data.get("round_id"),
            "round_index": round_index,
            "timestamp": round_data.get("timestamp", ""),
            "status": round_data.get("status", "unknown"),
            "manager": round_data.get("manager", {}),
            "executor": round_data.get("executor", {}),
            "auditor": round_data.get("auditor", {}),
            "checkpoint": round_data.get("checkpoint"),
        }

    def list_rounds(
        self,
        task_id: str,
        status_filter: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List all rounds for a task.

        Args:
            task_id: Task identifier
            status_filter: Optional filter by status
            offset: Pagination offset
            limit: Maximum number of rounds to return

        Returns:
            Paginated list of rounds
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        rounds = task.rounds

        # Apply status filter
        if status_filter:
            rounds = [r for r in rounds if r.get("status") == status_filter]

        # Apply pagination
        total = len(rounds)
        rounds = rounds[offset : offset + limit]

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "rounds": [
                {
                    "round_id": r.get("round_id"),
                    "round_index": r.get("round_index"),
                    "status": r.get("status"),
                    "timestamp": r.get("timestamp", ""),
                    "summary": r.get("summary", ""),
                }
                for r in rounds
            ],
        }

    def edit_round(
        self,
        task_id: str,
        round_id: str | int,
        edits: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        """Edit a specific round's results.

        Args:
            task_id: Task identifier
            round_id: Round ID or index
            edits: Fields to edit
            reason: Reason for editing

        Returns:
            Confirmation with edited fields
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Find the round
        if isinstance(round_id, int):
            round_index = round_id
        else:
            round_index = -1
            for idx, r in enumerate(task.rounds):
                if r.get("round_id") == round_id:
                    round_index = idx
                    break

        if round_index < 0 or round_index >= len(task.rounds):
            raise ValueError(f"Round {round_id} not found")

        round_data = task.rounds[round_index]

        # Apply edits
        edited_fields = []
        for key, value in edits.items():
            round_data[key] = value
            edited_fields.append(key)

        # Record edit history
        if "edit_history" not in round_data:
            round_data["edit_history"] = []

        round_data["edit_history"].append({
            "edited_fields": edited_fields,
            "reason": reason,
            "timestamp": "",  # TODO: Add timestamp
        })

        # Increment revision
        revision = round_data.get("revision", 1) + 1
        round_data["revision"] = revision

        return {
            "success": True,
            "round_id": round_data.get("round_id"),
            "edited_fields": edited_fields,
            "revision": revision,
        }

    def delete_round(
        self,
        task_id: str,
        round_id: str | int,
        delete_mode: str = "this_and_after",
    ) -> dict[str, Any]:
        """Delete a round and optionally subsequent rounds.

        Args:
            task_id: Task identifier
            round_id: Round ID or index to delete
            delete_mode: "this_only" or "this_and_after"

        Returns:
            List of deleted rounds and new state
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Find the round index
        if isinstance(round_id, int):
            round_index = round_id
        else:
            round_index = -1
            for idx, r in enumerate(task.rounds):
                if r.get("round_id") == round_id:
                    round_index = idx
                    break

        if round_index < 0 or round_index >= len(task.rounds):
            raise ValueError(f"Round {round_id} not found")

        # Collect rounds to delete
        if delete_mode == "this_only":
            deleted_rounds = [task.rounds[round_index].get("round_id")]
            task.rounds.pop(round_index)
        else:  # this_and_after
            deleted_rounds = [
                r.get("round_id") for r in task.rounds[round_index:]
            ]
            task.rounds = task.rounds[:round_index]

        # Update current round
        task.current_round = len(task.rounds)

        # Find rollback checkpoint
        rollback_checkpoint = None
        if task.checkpoints and len(task.checkpoints) > round_index:
            rollback_checkpoint = task.checkpoints[round_index - 1] if round_index > 0 else None
            task.checkpoints = task.checkpoints[:round_index]

        return {
            "success": True,
            "deleted_rounds": deleted_rounds,
            "new_current_round": task.current_round,
            "rollback_checkpoint": rollback_checkpoint,
        }

    async def retry_round(
        self,
        task_id: str,
        round_id: str | int,
        modified_input: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Retry a failed or problematic round.

        Args:
            task_id: Task identifier
            round_id: Round to retry
            modified_input: Optional modifications to input

        Returns:
            Result of the retry
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Get the original round
        round_detail = self.get_round_detail(task_id, round_id)

        # Delete this round and after
        self.delete_round(task_id, round_id, "this_and_after")

        # Execute a new round with modified input
        user_input = None
        if modified_input:
            user_input = json.dumps(modified_input, ensure_ascii=False)

        result = await self.task_manager.execute_round(task_id, user_input)

        return {
            "success": True,
            "original_round_id": round_detail["round_id"],
            "new_round_id": result.round_id,
            "result": {
                "plan": result.plan,
                "execution_result": result.execution_result,
                "audit_report": result.audit_report,
                "status": result.status,
            },
        }

    # ========== Checkpoint Management ==========

    def list_checkpoints(self, task_id: str) -> dict[str, Any]:
        """List all checkpoints for a task.

        Args:
            task_id: Task identifier

        Returns:
            List of all checkpoints
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        checkpoints = []
        for idx, cp in enumerate(task.checkpoints):
            checkpoints.append({
                "checkpoint_id": f"{task_id}_cp{idx + 1}",
                "round_index": cp.get("round", idx),
                "timestamp": cp.get("timestamp", ""),
                "verified_state": cp.get("verified_state", ""),
                "can_restore": True,
            })

        return {
            "task_id": task_id,
            "total": len(checkpoints),
            "checkpoints": checkpoints,
        }

    def create_checkpoint(
        self,
        task_id: str,
        label: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        """Manually create a checkpoint at current state.

        Args:
            task_id: Task identifier
            label: Checkpoint label
            note: Optional note

        Returns:
            Created checkpoint info
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        checkpoint = {
            "round": task.current_round,
            "label": label,
            "note": note or "",
            "timestamp": "",  # TODO: Add timestamp
            "verified_state": task.verified_progress,
            "manual": True,
        }

        task.checkpoints.append(checkpoint)

        checkpoint_id = f"{task_id}_cp{len(task.checkpoints)}"

        return {
            "success": True,
            "checkpoint_id": checkpoint_id,
            "checkpoint": checkpoint,
        }

    # ========== Conversation Log Management ==========

    def get_conversation_log(
        self,
        task_id: str,
        include_prompts: bool = True,
        include_responses: bool = True,
        role_filter: str = "all",
    ) -> dict[str, Any]:
        """Get complete conversation log.

        Args:
            task_id: Task identifier
            include_prompts: Include input prompts
            include_responses: Include responses
            role_filter: Filter by role (manager/executor/auditor/all)

        Returns:
            Conversation history
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        conversations = []

        for round_data in task.rounds:
            round_id = round_data.get("round_id")

            # Add conversations for each role
            for role in ["manager", "executor", "auditor"]:
                if role_filter != "all" and role != role_filter:
                    continue

                role_data = round_data.get(role, {})
                if not role_data:
                    continue

                conversation = {
                    "round_id": round_id,
                    "role": role,
                    "timestamp": role_data.get("timestamp", ""),
                }

                if include_prompts:
                    conversation["prompt"] = role_data.get("input_prompt", "")

                if include_responses:
                    conversation["response"] = role_data.get("output", "")

                conversation["metadata"] = {
                    "model": role_data.get("model", ""),
                    "duration_ms": role_data.get("duration_ms", 0),
                    "tokens_used": role_data.get("tokens_used", 0),
                }

                conversations.append(conversation)

        return {
            "task_id": task_id,
            "total": len(conversations),
            "conversations": conversations,
        }

    def search_in_conversation(
        self,
        task_id: str,
        query: str,
        role_filter: str = "all",
        search_in: str = "all",
    ) -> dict[str, Any]:
        """Search for content in conversation history.

        Args:
            task_id: Task identifier
            query: Search query
            role_filter: Role filter
            search_in: Where to search (prompts/responses/all)

        Returns:
            Search matches
        """
        log = self.get_conversation_log(
            task_id,
            include_prompts=(search_in in ["prompts", "all"]),
            include_responses=(search_in in ["responses", "all"]),
            role_filter=role_filter,
        )

        matches = []
        query_lower = query.lower()

        for conv in log["conversations"]:
            # Search in prompt
            if "prompt" in conv and query_lower in conv["prompt"].lower():
                snippet_start = max(0, conv["prompt"].lower().find(query_lower) - 50)
                snippet_end = min(len(conv["prompt"]), snippet_start + 200)
                matches.append({
                    "round_id": conv["round_id"],
                    "role": conv["role"],
                    "match_type": "prompt",
                    "snippet": "..." + conv["prompt"][snippet_start:snippet_end] + "...",
                    "full_text": conv["prompt"],
                })

            # Search in response
            if "response" in conv and query_lower in conv["response"].lower():
                snippet_start = max(0, conv["response"].lower().find(query_lower) - 50)
                snippet_end = min(len(conv["response"]), snippet_start + 200)
                matches.append({
                    "round_id": conv["round_id"],
                    "role": conv["role"],
                    "match_type": "response",
                    "snippet": "..." + conv["response"][snippet_start:snippet_end] + "...",
                    "full_text": conv["response"],
                })

        return {
            "task_id": task_id,
            "query": query,
            "total_matches": len(matches),
            "matches": matches,
        }

    # ========== Diagnostics ==========

    def get_execution_metrics(self, task_id: str) -> dict[str, Any]:
        """Get execution metrics and statistics.

        Args:
            task_id: Task identifier

        Returns:
            Execution metrics
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        total_rounds = len(task.rounds)
        successful_rounds = sum(
            1 for r in task.rounds if r.get("status") == "complete"
        )
        failed_rounds = sum(
            1 for r in task.rounds if r.get("status") in ["incomplete", "blocked"]
        )

        total_duration_ms = 0
        total_tokens = 0

        by_role = {
            "manager": {"rounds": 0, "total_duration_ms": 0, "total_tokens": 0},
            "executor": {"rounds": 0, "total_duration_ms": 0, "total_tokens": 0},
            "auditor": {"rounds": 0, "total_duration_ms": 0, "total_tokens": 0},
        }

        for round_data in task.rounds:
            for role in ["manager", "executor", "auditor"]:
                role_data = round_data.get(role, {})
                if role_data:
                    by_role[role]["rounds"] += 1
                    duration = role_data.get("duration_ms", 0)
                    tokens = role_data.get("tokens_used", 0)
                    by_role[role]["total_duration_ms"] += duration
                    by_role[role]["total_tokens"] += tokens
                    total_duration_ms += duration
                    total_tokens += tokens

        # Calculate averages
        for role_stats in by_role.values():
            if role_stats["rounds"] > 0:
                role_stats["avg_duration_ms"] = (
                    role_stats["total_duration_ms"] / role_stats["rounds"]
                )
            else:
                role_stats["avg_duration_ms"] = 0

        return {
            "task_id": task_id,
            "total_rounds": total_rounds,
            "successful_rounds": successful_rounds,
            "failed_rounds": failed_rounds,
            "total_duration_ms": total_duration_ms,
            "total_tokens": total_tokens,
            "by_role": by_role,
        }

    def validate_task_state(
        self,
        task_id: str,
        fix_issues: bool = False,
    ) -> dict[str, Any]:
        """Validate task state consistency.

        Args:
            task_id: Task identifier
            fix_issues: Attempt to fix detected issues

        Returns:
            Validation results
        """
        task = self.task_manager.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        issues = []
        fixed_issues = []

        # Check round continuity
        for idx, round_data in enumerate(task.rounds):
            expected_index = idx
            actual_index = round_data.get("round_index", -1)
            if actual_index != expected_index:
                issue = {
                    "severity": "warning",
                    "type": "round_index_mismatch",
                    "description": f"Round {idx} has index {actual_index}, expected {expected_index}",
                    "auto_fixable": True,
                }
                issues.append(issue)

                if fix_issues:
                    round_data["round_index"] = expected_index
                    fixed_issues.append(issue)

        # Check checkpoint consistency
        if len(task.checkpoints) > len(task.rounds):
            issues.append({
                "severity": "error",
                "type": "checkpoint_overflow",
                "description": f"More checkpoints ({len(task.checkpoints)}) than rounds ({len(task.rounds)})",
                "auto_fixable": False,
            })

        return {
            "task_id": task_id,
            "valid": len(issues) == 0,
            "issues": issues,
            "fixed_issues": fixed_issues if fix_issues else [],
        }
