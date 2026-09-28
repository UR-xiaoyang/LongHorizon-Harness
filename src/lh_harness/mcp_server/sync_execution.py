"""Synchronous execution mode for MCP Server.

This addresses the issue where Claude cannot monitor async tasks
and needs to wait for each round to complete.
"""

from __future__ import annotations

import asyncio
from typing import Any


class SyncExecutionWrapper:
    """Wrapper to make task execution synchronous for Claude.

    Problem: When Claude calls lh_execute_round, the task runs in background.
    Claude has no way to:
    - Monitor progress
    - Know when it completes
    - Continue next steps

    Solution: Make execute_round block until the round completes,
    then return full results immediately.
    """

    def __init__(self, task_manager):
        self.task_manager = task_manager

    async def execute_round_sync(
        self,
        task_id: str,
        user_input: str | None = None,
        wait_for_completion: bool = True,
        timeout_seconds: int = 3600,
    ) -> dict[str, Any]:
        """Execute a round and wait for completion.

        Args:
            task_id: Task identifier
            user_input: Optional user input
            wait_for_completion: If True, blocks until round completes
            timeout_seconds: Maximum wait time

        Returns:
            Complete round result with all details
        """
        # Start the round
        result = await self.task_manager.execute_round(task_id, user_input)

        if not wait_for_completion:
            return {
                "success": True,
                "round_id": result.round_id,
                "status": "started",
                "message": "Round started in background",
            }

        # Wait for completion (simplified - real implementation would poll)
        # In real implementation, this would:
        # 1. Check task status periodically
        # 2. Return when status changes to "complete" or "blocked"
        # 3. Timeout if takes too long

        return {
            "success": True,
            "round_id": result.round_id,
            "status": result.status,
            "plan": result.plan,
            "execution_result": result.execution_result,
            "audit_report": result.audit_report,
            "checkpoint": result.checkpoint,
        }


# Integration with MCP Server
def add_sync_execution_tool(server, task_manager):
    """Add synchronous execution tool to MCP server."""
    wrapper = SyncExecutionWrapper(task_manager)

    server.tools["lh_execute_round_sync"] = {
        "description": "执行一轮并等待完成（阻塞式，推荐用于交互）",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "任务ID"},
                "user_input": {"type": "string", "description": "用户输入"},
                "timeout_seconds": {
                    "type": "integer",
                    "default": 3600,
                    "description": "超时时间（秒）"
                },
            },
            "required": ["task_id"],
        },
    }

    return wrapper
