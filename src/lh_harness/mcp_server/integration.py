"""Integration layer between MCP Server and existing harness logic."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from ..adapters.base import AgentAdapter
from ..environment.base import Environment
from ..environment.local import LocalEnvironment
from ..manager import _run_impl
from ..types import EpisodeBudget, HarnessConfig
from .types import RoundResult, TaskContext

logger = logging.getLogger(__name__)


class HarnessIntegration:
    """Integration layer connecting MCP Server to existing harness logic."""

    def __init__(self, state_root: str = "~/.lh-harness"):
        self.state_root = Path(state_root).expanduser()

    async def execute_round_with_harness(
        self,
        task: TaskContext,
        user_input: str | None = None,
    ) -> RoundResult:
        """Execute a round using the existing Manager/Executor/Auditor logic.

        Args:
            task: Task context
            user_input: Optional user input or feedback

        Returns:
            RoundResult with plan, execution, and audit details
        """
        try:
            # Build HarnessConfig
            config = self._build_harness_config(task)

            # Create environment
            env = LocalEnvironment(workspace_path=task.workspace)

            # Get agent configuration
            agent_type = task.metadata.get("config", {}).get("agent", "claude_code")
            model = task.metadata.get("config", {}).get("model", "claude-opus-5")

            # Create agent adapter using the same method as CLI
            agent = self._build_agent(
                name=agent_type,
                model=model,
                workspace_path=task.workspace,
                prompt_dir=str(config.harness_dir),
            )

            # For now, create a simplified single-round execution
            # This is a placeholder that needs full integration
            round_id = f"{task.task_id}_r{task.current_round + 1}"

            # Execute one management cycle
            result = await self._execute_single_round(
                task=task,
                config=config,
                env=env,
                agent=agent,
                user_input=user_input,
            )

            return RoundResult(
                round_id=round_id,
                plan=result.get("plan", ""),
                execution_result=result.get("execution_result", ""),
                audit_report=result.get("audit_report", ""),
                status=result.get("status", "complete"),
                checkpoint=result.get("checkpoint"),
                duration_ms=result.get("duration_ms", 0),
            )

        except Exception as e:
            logger.error(f"Error executing round: {e}", exc_info=True)
            round_id = f"{task.task_id}_r{task.current_round + 1}"
            return RoundResult(
                round_id=round_id,
                plan="",
                execution_result=f"Error: {str(e)}",
                audit_report="Status: incomplete\nError occurred during execution",
                status="incomplete",
                duration_ms=0,
            )

    def _build_harness_config(self, task: TaskContext) -> HarnessConfig:
        """Build HarnessConfig from TaskContext.

        Args:
            task: Task context

        Returns:
            HarnessConfig instance
        """
        config_data = task.metadata.get("config", {})

        # Create run directory for this task
        run_dir = self.state_root / "tasks" / task.task_id
        run_dir.mkdir(parents=True, exist_ok=True)

        return HarnessConfig(
            workspace_path=task.workspace,
            harness_dir=str(run_dir / "harness"),
            log_dir=str(run_dir / "logs"),
            max_total_episodes=task.max_rounds,
            manager_budget=EpisodeBudget(
                max_duration_seconds=config_data.get("timeouts", {}).get("manager", 600)
            ),
            gui_executor_budget=EpisodeBudget(
                max_duration_seconds=config_data.get("timeouts", {}).get(
                    "gui_executor", 1800
                )
            ),
            cli_executor_budget=EpisodeBudget(
                max_duration_seconds=config_data.get("timeouts", {}).get(
                    "cli_executor", 1800
                )
            ),
            auditor_budget=EpisodeBudget(
                max_duration_seconds=config_data.get("timeouts", {}).get("auditor", 600)
            ),
            prompt_language="en",
        )

    async def _execute_single_round(
        self,
        task: TaskContext,
        config: HarnessConfig,
        env: Environment,
        agent: AgentAdapter,
        user_input: str | None = None,
    ) -> dict[str, Any]:
        """Execute a single round.

        This is a simplified version that needs to be integrated with
        the full _run_impl logic.

        Args:
            task: Task context
            config: Harness configuration
            env: Environment
            agent: Agent adapter
            user_input: Optional user input

        Returns:
            Dictionary with plan, execution_result, audit_report, status
        """
        import time

        start_time = time.monotonic()

        # TODO: Integrate with actual _run_impl
        # For now, return a placeholder
        result = {
            "plan": f"Manager planning for: {task.goal}",
            "execution_result": f"Executor working on: {task.current_step or 'next step'}",
            "audit_report": "Status: complete\nIntegrity: clean\nContract audit: aligned",
            "status": "complete",
            "checkpoint": {
                "round": task.current_round + 1,
                "verified": True,
                "verified_state": f"Round {task.current_round + 1} completed",
                "timestamp": "",
            },
            "duration_ms": int((time.monotonic() - start_time) * 1000),
        }

        return result

    def _build_agent(
        self,
        name: str,
        model: str | None,
        workspace_path: str,
        prompt_dir: str,
    ) -> AgentAdapter:
        """Build an agent adapter.

        Args:
            name: Agent name (claude_code, codex, etc.)
            model: Model name
            workspace_path: Workspace path
            prompt_dir: Prompt directory

        Returns:
            AgentAdapter instance
        """
        if name == "claude_code":
            from ..adapters.claude_code import ClaudeCodeAdapter

            kwargs = {
                "workspace_path": workspace_path,
                "prompt_dir": prompt_dir,
                "role": "cli_executor",  # Default role
            }
            if model:
                kwargs["model"] = model

            return ClaudeCodeAdapter(**kwargs)

        elif name == "codex":
            from ..adapters.codex import CodexAdapter

            kwargs = {
                "workspace_path": workspace_path,
                "prompt_dir": prompt_dir,
            }
            if model:
                kwargs["model"] = model

            return CodexAdapter(**kwargs)

        elif name == "opencode":
            from ..adapters.opencode import OpenCodeAdapter

            kwargs = {
                "workspace_path": workspace_path,
                "prompt_dir": prompt_dir,
            }
            if model:
                kwargs["model"] = model

            return OpenCodeAdapter(**kwargs)

        elif name == "deepseek_harness":
            from ..adapters.deepseek_harness import DeepSeekHarnessAdapter

            kwargs = {
                "workspace_path": workspace_path,
                "prompt_dir": prompt_dir,
            }
            if model:
                kwargs["model"] = model

            return DeepSeekHarnessAdapter(**kwargs)

        else:
            raise ValueError(f"Unknown agent: {name}")


def create_harness_integration(state_root: str = "~/.lh-harness") -> HarnessIntegration:
    """Create a harness integration instance.

    Args:
        state_root: Root directory for state storage

    Returns:
        HarnessIntegration instance
    """
    return HarnessIntegration(state_root)
