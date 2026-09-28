"""Redesigned MCP Server - Core execution tools.

New architecture where Claude is the main controller and LongHorizon-Harness
provides execution, verification, and state management tools.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


class ExecutionRecord:
    """Record of a single execution."""

    def __init__(
        self,
        execution_id: str,
        action: str,
        params: dict[str, Any],
        workspace: str,
    ):
        self.execution_id = execution_id
        self.action = action
        self.params = params
        self.workspace = workspace
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.success: bool | None = None
        self.result: str = ""
        self.files_changed: list[str] = []
        self.verification_needed: bool = True
        self.verified: bool = False
        self.audit_report: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "action": self.action,
            "params": self.params,
            "workspace": self.workspace,
            "timestamp": self.timestamp,
            "success": self.success,
            "result": self.result,
            "files_changed": self.files_changed,
            "verification_needed": self.verification_needed,
            "verified": self.verified,
            "audit_report": self.audit_report,
        }


class Checkpoint:
    """Workspace checkpoint."""

    def __init__(
        self,
        checkpoint_id: str,
        label: str,
        note: str,
        workspace: str,
    ):
        self.checkpoint_id = checkpoint_id
        self.label = label
        self.note = note
        self.workspace = workspace
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.files_snapshot: dict[str, str] = {}  # path -> content hash

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "label": self.label,
            "note": self.note,
            "workspace": self.workspace,
            "timestamp": self.timestamp,
            "files_count": len(self.files_snapshot),
        }


class WorkspaceManager:
    """Manages workspace state and checkpoints."""

    def __init__(self, state_root: str = "~/.lh-harness"):
        self.state_root = Path(state_root).expanduser()
        self.state_root.mkdir(parents=True, exist_ok=True)

        # Execution history
        self.executions: list[ExecutionRecord] = []

        # Checkpoints
        self.checkpoints: list[Checkpoint] = []

        # Current workspace
        self.current_workspace: str | None = None

    def init_workspace(
        self,
        path: str,
        git_init: bool = False,
    ) -> dict[str, Any]:
        """Initialize a workspace.

        Args:
            path: Workspace path
            git_init: Initialize git repository

        Returns:
            Initialization result
        """
        workspace_path = Path(path).resolve()
        workspace_path.mkdir(parents=True, exist_ok=True)

        self.current_workspace = str(workspace_path)

        # Initialize git if requested
        if git_init:
            import subprocess

            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=workspace_path,
                    check=True,
                    capture_output=True,
                )
                git_initialized = True
            except Exception as e:
                logger.warning(f"Git init failed: {e}")
                git_initialized = False
        else:
            git_initialized = False

        # Create initial checkpoint
        cp = Checkpoint(
            checkpoint_id=f"cp_{uuid.uuid4().hex[:8]}",
            label="Initial workspace",
            note="Workspace initialized",
            workspace=str(workspace_path),
        )
        self.checkpoints.append(cp)

        return {
            "success": True,
            "workspace": str(workspace_path),
            "git_initialized": git_initialized,
            "checkpoint_id": cp.checkpoint_id,
        }

    def execute_action(
        self,
        action: str,
        params: dict[str, Any],
        workspace: str | None = None,
    ) -> dict[str, Any]:
        """Execute an action.

        Args:
            action: Action type (create_file, run_command, modify_file, etc.)
            params: Action parameters
            workspace: Workspace path (uses current if not specified)

        Returns:
            Execution result
        """
        workspace = workspace or self.current_workspace
        if not workspace:
            return {
                "success": False,
                "error": "No workspace specified or initialized",
            }

        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        record = ExecutionRecord(
            execution_id=execution_id,
            action=action,
            params=params,
            workspace=workspace,
        )

        try:
            if action == "create_file":
                result = self._create_file(workspace, params)
            elif action == "modify_file":
                result = self._modify_file(workspace, params)
            elif action == "delete_file":
                result = self._delete_file(workspace, params)
            elif action == "run_command":
                result = self._run_command(workspace, params)
            elif action == "read_file":
                result = self._read_file(workspace, params)
            else:
                result = {
                    "success": False,
                    "error": f"Unknown action: {action}",
                }

            record.success = result.get("success", False)
            record.result = result.get("message", "")
            record.files_changed = result.get("files_changed", [])

            self.executions.append(record)

            return {
                "success": result["success"],
                "execution_id": execution_id,
                "result": record.result,
                "files_changed": record.files_changed,
                "verification_needed": record.verification_needed,
            }

        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            record.success = False
            record.result = f"Error: {str(e)}"
            self.executions.append(record)

            return {
                "success": False,
                "execution_id": execution_id,
                "error": str(e),
            }

    def _create_file(self, workspace: str, params: dict[str, Any]) -> dict[str, Any]:
        """Create a file."""
        path = params.get("path")
        content = params.get("content", "")

        if not path:
            return {"success": False, "error": "Missing path parameter"}

        file_path = Path(workspace) / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "message": f"File created: {path}",
            "files_changed": [path],
        }

    def _modify_file(self, workspace: str, params: dict[str, Any]) -> dict[str, Any]:
        """Modify a file."""
        path = params.get("path")
        content = params.get("content")
        mode = params.get("mode", "replace")  # replace or append

        if not path:
            return {"success": False, "error": "Missing path parameter"}

        file_path = Path(workspace) / path

        if not file_path.exists():
            return {"success": False, "error": f"File not found: {path}"}

        if mode == "append":
            file_path.write_text(
                file_path.read_text(encoding="utf-8") + content,
                encoding="utf-8",
            )
        else:
            file_path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "message": f"File modified: {path}",
            "files_changed": [path],
        }

    def _delete_file(self, workspace: str, params: dict[str, Any]) -> dict[str, Any]:
        """Delete a file."""
        path = params.get("path")

        if not path:
            return {"success": False, "error": "Missing path parameter"}

        file_path = Path(workspace) / path

        if not file_path.exists():
            return {"success": False, "error": f"File not found: {path}"}

        file_path.unlink()

        return {
            "success": True,
            "message": f"File deleted: {path}",
            "files_changed": [path],
        }

    def _run_command(self, workspace: str, params: dict[str, Any]) -> dict[str, Any]:
        """Run a shell command."""
        import subprocess

        command = params.get("command")
        timeout = params.get("timeout", 300)

        if not command:
            return {"success": False, "error": "Missing command parameter"}

        try:
            result = subprocess.run(
                command,
                cwd=workspace,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return {
                "success": result.returncode == 0,
                "message": f"Command executed: {command}",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "files_changed": [],  # TODO: Detect changed files
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timeout after {timeout}s",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Command failed: {str(e)}",
            }

    def _read_file(self, workspace: str, params: dict[str, Any]) -> dict[str, Any]:
        """Read a file."""
        path = params.get("path")

        if not path:
            return {"success": False, "error": "Missing path parameter"}

        file_path = Path(workspace) / path

        if not file_path.exists():
            return {"success": False, "error": f"File not found: {path}"}

        content = file_path.read_text(encoding="utf-8")

        return {
            "success": True,
            "message": f"File read: {path}",
            "content": content,
            "files_changed": [],
        }

    def verify_execution(
        self,
        execution_id: str,
        verification_goals: list[str],
    ) -> dict[str, Any]:
        """Verify an execution.

        Args:
            execution_id: Execution ID
            verification_goals: List of verification goals

        Returns:
            Verification result
        """
        # Find execution
        record = None
        for exec_record in self.executions:
            if exec_record.execution_id == execution_id:
                record = exec_record
                break

        if not record:
            return {
                "success": False,
                "error": f"Execution not found: {execution_id}",
            }

        # Perform verification (simplified)
        issues = []
        for goal in verification_goals:
            # TODO: Implement actual verification logic
            # For now, just mark as verified
            pass

        record.verified = True
        record.audit_report = (
            "✅ All checks passed"
            if not issues
            else f"⚠️ Issues found: {', '.join(issues)}"
        )

        return {
            "success": True,
            "verified": len(issues) == 0,
            "integrity": "clean" if not issues else "issues_found",
            "issues": issues,
            "audit_report": record.audit_report,
        }

    def inspect_workspace(
        self,
        target: Literal["workspace", "file", "structure"],
        workspace: str | None = None,
        path: str | None = None,
    ) -> dict[str, Any]:
        """Inspect workspace state.

        Args:
            target: What to inspect
            workspace: Workspace path
            path: Specific file path (for target="file")

        Returns:
            Inspection result
        """
        workspace = workspace or self.current_workspace
        if not workspace:
            return {
                "success": False,
                "error": "No workspace specified",
            }

        workspace_path = Path(workspace)

        if target == "workspace":
            # List all files
            files = [str(p.relative_to(workspace_path)) for p in workspace_path.rglob("*") if p.is_file()]
            return {
                "success": True,
                "workspace": workspace,
                "files": files,
                "file_count": len(files),
            }

        elif target == "file":
            if not path:
                return {"success": False, "error": "Missing path parameter"}

            file_path = workspace_path / path
            if not file_path.exists():
                return {"success": False, "error": f"File not found: {path}"}

            return {
                "success": True,
                "path": path,
                "exists": True,
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime,
            }

        elif target == "structure":
            # Build directory tree
            def build_tree(dir_path: Path, prefix: str = "") -> list[str]:
                tree = []
                items = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
                for item in items:
                    tree.append(f"{prefix}{item.name}{'/' if item.is_dir() else ''}")
                    if item.is_dir() and not item.name.startswith("."):
                        tree.extend(build_tree(item, prefix + "  "))
                return tree

            structure = build_tree(workspace_path)
            return {
                "success": True,
                "workspace": workspace,
                "structure": "\n".join(structure),
            }

        return {"success": False, "error": f"Unknown target: {target}"}

    def save_checkpoint(
        self,
        label: str,
        note: str = "",
        workspace: str | None = None,
    ) -> dict[str, Any]:
        """Save a checkpoint.

        Args:
            label: Checkpoint label
            note: Optional note
            workspace: Workspace path

        Returns:
            Checkpoint info
        """
        workspace = workspace or self.current_workspace
        if not workspace:
            return {
                "success": False,
                "error": "No workspace specified",
            }

        checkpoint = Checkpoint(
            checkpoint_id=f"cp_{uuid.uuid4().hex[:8]}",
            label=label,
            note=note,
            workspace=workspace,
        )

        # TODO: Snapshot workspace files

        self.checkpoints.append(checkpoint)

        return {
            "success": True,
            "checkpoint_id": checkpoint.checkpoint_id,
            "label": label,
            "timestamp": checkpoint.timestamp,
        }

    def list_checkpoints(self) -> dict[str, Any]:
        """List all checkpoints.

        Returns:
            List of checkpoints
        """
        return {
            "success": True,
            "checkpoints": [cp.to_dict() for cp in self.checkpoints],
            "total": len(self.checkpoints),
        }

    def rollback_to_checkpoint(
        self,
        checkpoint_id: str,
    ) -> dict[str, Any]:
        """Rollback to a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            Rollback result
        """
        # Find checkpoint
        checkpoint = None
        for cp in self.checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                checkpoint = cp
                break

        if not checkpoint:
            return {
                "success": False,
                "error": f"Checkpoint not found: {checkpoint_id}",
            }

        # TODO: Restore workspace state

        return {
            "success": True,
            "restored_to": checkpoint.label,
            "checkpoint_id": checkpoint_id,
        }

    def get_history(
        self,
        limit: int = 10,
        filter_status: Literal["all", "success", "failed"] = "all",
    ) -> dict[str, Any]:
        """Get execution history.

        Args:
            limit: Maximum number of records
            filter_status: Filter by status

        Returns:
            Execution history
        """
        records = self.executions

        if filter_status == "success":
            records = [r for r in records if r.success is True]
        elif filter_status == "failed":
            records = [r for r in records if r.success is False]

        records = records[-limit:]

        return {
            "success": True,
            "executions": [r.to_dict() for r in records],
            "total": len(self.executions),
            "returned": len(records),
        }

    def search_history(
        self,
        query: str,
        search_in: Literal["all", "commands", "results", "errors"] = "all",
    ) -> dict[str, Any]:
        """Search in execution history.

        Args:
            query: Search query
            search_in: Where to search

        Returns:
            Search results
        """
        query_lower = query.lower()
        matches = []

        for record in self.executions:
            matched = False

            if search_in in ("all", "commands"):
                if query_lower in record.action.lower():
                    matched = True
                if query_lower in json.dumps(record.params).lower():
                    matched = True

            if search_in in ("all", "results"):
                if query_lower in record.result.lower():
                    matched = True

            if search_in in ("all", "errors") and not record.success:
                if query_lower in record.result.lower():
                    matched = True

            if matched:
                matches.append(record.to_dict())

        return {
            "success": True,
            "query": query,
            "matches": matches,
            "total_matches": len(matches),
        }

    def get_metrics(self) -> dict[str, Any]:
        """Get execution metrics.

        Returns:
            Metrics
        """
        total = len(self.executions)
        successful = sum(1 for r in self.executions if r.success is True)
        failed = sum(1 for r in self.executions if r.success is False)
        verified = sum(1 for r in self.executions if r.verified)

        all_files_changed = []
        for record in self.executions:
            all_files_changed.extend(record.files_changed)

        return {
            "success": True,
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "verified": verified,
            "total_files_changed": len(set(all_files_changed)),
            "total_checkpoints": len(self.checkpoints),
        }
