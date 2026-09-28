"""Redesigned MCP Server implementation.

New architecture:
- Claude is the main controller
- LongHorizon-Harness provides execution, verification, and state management
- 12 focused tools instead of 23
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from .workspace_manager import WorkspaceManager

logger = logging.getLogger(__name__)


class RedesignedMCPServer:
    """MCP Server with redesigned architecture."""

    def __init__(self, state_root: str = "~/.lh-harness"):
        self.workspace_manager = WorkspaceManager(state_root)
        self.tools = self._register_tools()

    def _register_tools(self) -> dict[str, dict[str, Any]]:
        """Register MCP tools."""
        return {
            # Core Execution Tools (4)
            "lh_execute": {
                "description": "执行一个具体的操作（创建文件、运行命令等）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "create_file",
                                "modify_file",
                                "delete_file",
                                "run_command",
                                "read_file",
                            ],
                            "description": "操作类型",
                        },
                        "params": {
                            "type": "object",
                            "description": "操作参数（根据action类型不同）",
                        },
                        "workspace": {
                            "type": "string",
                            "description": "工作空间路径（可选，使用当前工作空间）",
                        },
                    },
                    "required": ["action", "params"],
                },
            },
            "lh_verify": {
                "description": "验证上一步操作的结果",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "执行ID（从lh_execute返回）",
                        },
                        "verification_goals": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "验证目标列表",
                        },
                    },
                    "required": ["execution_id", "verification_goals"],
                },
            },
            "lh_inspect": {
                "description": "检查当前状态（不执行任何操作）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "enum": ["workspace", "file", "structure"],
                            "description": "检查目标",
                        },
                        "workspace": {
                            "type": "string",
                            "description": "工作空间路径（可选）",
                        },
                        "path": {
                            "type": "string",
                            "description": "文件路径（target=file时必需）",
                        },
                    },
                    "required": ["target"],
                },
            },
            "lh_rollback": {
                "description": "回滚到之前的检查点",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "checkpoint_id": {
                            "type": "string",
                            "description": "检查点ID",
                        },
                    },
                    "required": ["checkpoint_id"],
                },
            },
            # State Management Tools (5)
            "lh_save_checkpoint": {
                "description": "手动保存当前状态为检查点",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": "检查点标签",
                        },
                        "note": {
                            "type": "string",
                            "description": "可选说明",
                        },
                        "workspace": {
                            "type": "string",
                            "description": "工作空间路径（可选）",
                        },
                    },
                    "required": ["label"],
                },
            },
            "lh_list_checkpoints": {
                "description": "列出所有检查点",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            "lh_get_history": {
                "description": "获取执行历史",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "description": "返回记录数量",
                        },
                        "filter": {
                            "type": "string",
                            "enum": ["all", "success", "failed"],
                            "default": "all",
                            "description": "状态过滤",
                        },
                    },
                },
            },
            "lh_search_history": {
                "description": "在执行历史中搜索",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词",
                        },
                        "search_in": {
                            "type": "string",
                            "enum": ["all", "commands", "results", "errors"],
                            "default": "all",
                            "description": "搜索范围",
                        },
                    },
                    "required": ["query"],
                },
            },
            "lh_get_metrics": {
                "description": "获取统计信息",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            # Workspace Management Tools (3)
            "lh_init_workspace": {
                "description": "初始化工作空间",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "工作空间路径",
                        },
                        "git_init": {
                            "type": "boolean",
                            "default": False,
                            "description": "是否初始化Git仓库",
                        },
                    },
                    "required": ["path"],
                },
            },
            "lh_get_workspace_state": {
                "description": "获取工作空间完整状态",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "工作空间路径（可选）",
                        },
                    },
                },
            },
            "lh_cleanup_workspace": {
                "description": "清理临时文件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workspace": {
                            "type": "string",
                            "description": "工作空间路径（可选）",
                        },
                        "pattern": {
                            "type": "string",
                            "default": "*.tmp,*.pyc,__pycache__",
                            "description": "要清理的文件模式",
                        },
                    },
                },
            },
        }

    async def handle_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle MCP tool call.

        Args:
            tool_name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        try:
            # Core execution tools
            if tool_name == "lh_execute":
                return self._handle_execute(arguments)
            elif tool_name == "lh_verify":
                return self._handle_verify(arguments)
            elif tool_name == "lh_inspect":
                return self._handle_inspect(arguments)
            elif tool_name == "lh_rollback":
                return self._handle_rollback(arguments)

            # State management tools
            elif tool_name == "lh_save_checkpoint":
                return self._handle_save_checkpoint(arguments)
            elif tool_name == "lh_list_checkpoints":
                return self._handle_list_checkpoints(arguments)
            elif tool_name == "lh_get_history":
                return self._handle_get_history(arguments)
            elif tool_name == "lh_search_history":
                return self._handle_search_history(arguments)
            elif tool_name == "lh_get_metrics":
                return self._handle_get_metrics(arguments)

            # Workspace management tools
            elif tool_name == "lh_init_workspace":
                return self._handle_init_workspace(arguments)
            elif tool_name == "lh_get_workspace_state":
                return self._handle_get_workspace_state(arguments)
            elif tool_name == "lh_cleanup_workspace":
                return self._handle_cleanup_workspace(arguments)

            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}",
                }

        except Exception as e:
            logger.error(f"Tool call error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    def _handle_execute(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_execute."""
        return self.workspace_manager.execute_action(
            action=args["action"],
            params=args["params"],
            workspace=args.get("workspace"),
        )

    def _handle_verify(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_verify."""
        return self.workspace_manager.verify_execution(
            execution_id=args["execution_id"],
            verification_goals=args["verification_goals"],
        )

    def _handle_inspect(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_inspect."""
        return self.workspace_manager.inspect_workspace(
            target=args["target"],
            workspace=args.get("workspace"),
            path=args.get("path"),
        )

    def _handle_rollback(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_rollback."""
        return self.workspace_manager.rollback_to_checkpoint(
            checkpoint_id=args["checkpoint_id"],
        )

    def _handle_save_checkpoint(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_save_checkpoint."""
        return self.workspace_manager.save_checkpoint(
            label=args["label"],
            note=args.get("note", ""),
            workspace=args.get("workspace"),
        )

    def _handle_list_checkpoints(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_list_checkpoints."""
        return self.workspace_manager.list_checkpoints()

    def _handle_get_history(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_get_history."""
        return self.workspace_manager.get_history(
            limit=args.get("limit", 10),
            filter_status=args.get("filter", "all"),
        )

    def _handle_search_history(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_search_history."""
        return self.workspace_manager.search_history(
            query=args["query"],
            search_in=args.get("search_in", "all"),
        )

    def _handle_get_metrics(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_get_metrics."""
        return self.workspace_manager.get_metrics()

    def _handle_init_workspace(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_init_workspace."""
        return self.workspace_manager.init_workspace(
            path=args["path"],
            git_init=args.get("git_init", False),
        )

    def _handle_get_workspace_state(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_get_workspace_state."""
        workspace = args.get("workspace")

        # Get files
        files_result = self.workspace_manager.inspect_workspace(
            target="workspace",
            workspace=workspace,
        )

        # Get structure
        structure_result = self.workspace_manager.inspect_workspace(
            target="structure",
            workspace=workspace,
        )

        # Get history
        history_result = self.workspace_manager.get_history(limit=5)

        # Get checkpoints
        checkpoints_result = self.workspace_manager.list_checkpoints()

        return {
            "success": True,
            "workspace": workspace or self.workspace_manager.current_workspace,
            "files": files_result.get("files", []),
            "file_count": files_result.get("file_count", 0),
            "structure": structure_result.get("structure", ""),
            "recent_executions": len(history_result.get("executions", [])),
            "checkpoints": len(checkpoints_result.get("checkpoints", [])),
        }

    def _handle_cleanup_workspace(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_cleanup_workspace."""
        from pathlib import Path

        workspace = args.get("workspace") or self.workspace_manager.current_workspace
        if not workspace:
            return {
                "success": False,
                "error": "No workspace specified",
            }

        pattern = args.get("pattern", "*.tmp,*.pyc,__pycache__")
        patterns = [p.strip() for p in pattern.split(",")]

        workspace_path = Path(workspace)
        cleaned_files = []

        for pattern in patterns:
            for file_path in workspace_path.rglob(pattern):
                if file_path.is_file():
                    file_path.unlink()
                    cleaned_files.append(str(file_path.relative_to(workspace_path)))
                elif file_path.is_dir():
                    import shutil
                    shutil.rmtree(file_path)
                    cleaned_files.append(str(file_path.relative_to(workspace_path)) + "/")

        return {
            "success": True,
            "cleaned_files": cleaned_files,
            "count": len(cleaned_files),
        }


def create_redesigned_mcp_server(state_root: str = "~/.lh-harness") -> RedesignedMCPServer:
    """Create a redesigned MCP server instance.

    Args:
        state_root: Root directory for state storage

    Returns:
        RedesignedMCPServer instance
    """
    return RedesignedMCPServer(state_root)


async def run_redesigned_mcp_server(
    state_root: str = "~/.lh-harness",
    transport: str = "stdio",
) -> None:
    """Run the redesigned MCP server.

    Args:
        state_root: Root directory for state storage
        transport: Transport method (stdio or http)
    """
    server = create_redesigned_mcp_server(state_root)
    logger.info(f"Starting redesigned MCP server on {transport}")

    if transport == "stdio":
        await _run_stdio_server(server)
    elif transport == "http":
        await _run_http_server(server)
    else:
        raise ValueError(f"Unknown transport: {transport}")


async def _run_stdio_server(server: RedesignedMCPServer) -> None:
    """Run server with stdio transport."""
    import sys

    while True:
        try:
            # Read JSON-RPC request from stdin
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )

            if not line:
                break

            request = json.loads(line)

            # Handle request
            method = request.get("method")
            params = request.get("params", {})

            if method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "tools": [
                            {
                                "name": name,
                                "description": tool["description"],
                                "inputSchema": tool["parameters"],
                            }
                            for name, tool in server.tools.items()
                        ]
                    },
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                result = await server.handle_tool_call(tool_name, arguments)

                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": result,
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }

            # Write response to stdout
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)


async def _run_http_server(server: RedesignedMCPServer) -> None:
    """Run server with HTTP transport."""
    # TODO: Implement HTTP server
    raise NotImplementedError("HTTP transport not yet implemented")
