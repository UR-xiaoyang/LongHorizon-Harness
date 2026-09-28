"""MCP Server implementation for LongHorizon-Harness."""

import asyncio
import json
import logging
from typing import Any

from .advanced_manager import AdvancedTaskManager
from .task_manager import TaskManager
from .types import FeedbackType

logger = logging.getLogger(__name__)


class LongHorizonMCPServer:
    """MCP Server exposing LongHorizon-Harness capabilities."""

    def __init__(self, state_root: str = "~/.lh-harness"):
        self.task_manager = TaskManager(state_root)
        self.advanced_manager = AdvancedTaskManager(self.task_manager)
        self.tools = self._register_tools()

    def _register_tools(self) -> dict[str, dict[str, Any]]:
        """Register available MCP tools."""
        return {
            "lh_start_task": {
                "description": "启动一个需要多轮plan-act-verify循环的长期任务",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "goal": {
                            "type": "string",
                            "description": "任务目标描述",
                        },
                        "workspace": {
                            "type": "string",
                            "description": "工作目录路径",
                        },
                        "max_rounds": {
                            "type": "integer",
                            "description": "最大执行轮数",
                            "default": 25,
                        },
                        "config": {
                            "type": "object",
                            "description": "可选的配置覆盖",
                        },
                    },
                    "required": ["goal", "workspace"],
                },
            },
            "lh_get_task_status": {
                "description": "获取长期任务的当前状态和进度",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "任务ID",
                        },
                    },
                    "required": ["task_id"],
                },
            },
            "lh_execute_round": {
                "description": "执行一轮Manager规划→Executor执行→Auditor验证的循环",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "任务ID",
                        },
                        "user_input": {
                            "type": "string",
                            "description": "可选的用户指令或反馈",
                        },
                    },
                    "required": ["task_id"],
                },
            },
            "lh_get_checkpoint": {
                "description": "获取任务最新的已验证状态快照",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "任务ID",
                        },
                    },
                    "required": ["task_id"],
                },
            },
            "lh_recover_task": {
                "description": "从最近的checkpoint恢复任务执行",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "任务ID",
                        },
                        "checkpoint_id": {
                            "type": "string",
                            "description": "可选的特定checkpoint",
                        },
                    },
                    "required": ["task_id"],
                },
            },
            "lh_pause_task": {
                "description": "暂停长期任务，保存当前状态以便后续恢复",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "任务ID",
                        },
                    },
                    "required": ["task_id"],
                },
            },
            "lh_stop_task": {
                "description": "停止任务执行并清理资源",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "任务ID",
                        },
                        "keep_artifacts": {
                            "type": "boolean",
                            "description": "是否保留产出文件",
                            "default": True,
                        },
                    },
                    "required": ["task_id"],
                },
            },
            "lh_inject_feedback": {
                "description": "向正在运行的任务注入人工反馈或修正",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "任务ID",
                        },
                        "feedback": {
                            "type": "string",
                            "description": "反馈内容",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["correction", "guidance", "approval"],
                            "description": "反馈类型",
                        },
                    },
                    "required": ["task_id", "feedback", "type"],
                },
            },
            "lh_get_audit_trail": {
                "description": "获取任务的完整执行和验证历史",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "任务ID",
                        },
                    },
                    "required": ["task_id"],
                },
            },
            # ========== Advanced APIs ==========
            "lh_get_task_config": {
                "description": "获取任务的完整配置信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                    },
                    "required": ["task_id"],
                },
            },
            "lh_update_task_config": {
                "description": "动态修改任务配置",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                        "config_updates": {
                            "type": "object",
                            "description": "要更新的配置项",
                        },
                    },
                    "required": ["task_id", "config_updates"],
                },
            },
            "lh_get_round_detail": {
                "description": "获取特定轮次的详细信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                        "round_id": {
                            "description": "轮次ID或索引（整数）",
                        },
                    },
                    "required": ["task_id", "round_id"],
                },
            },
            "lh_list_rounds": {
                "description": "列出任务的所有轮次",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                        "status_filter": {
                            "type": "string",
                            "enum": ["complete", "incomplete", "blocked"],
                            "description": "按状态过滤",
                        },
                        "offset": {"type": "integer", "default": 0},
                        "limit": {"type": "integer", "default": 20},
                    },
                    "required": ["task_id"],
                },
            },
            "lh_edit_round": {
                "description": "编辑已执行轮次的结果",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                        "round_id": {"description": "轮次ID或索引"},
                        "edits": {"type": "object", "description": "要编辑的字段"},
                        "reason": {"type": "string", "description": "修改原因"},
                    },
                    "required": ["task_id", "round_id", "edits", "reason"],
                },
            },
            "lh_delete_round": {
                "description": "删除特定轮次及其后续轮次",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                        "round_id": {"description": "要删除的轮次ID或索引"},
                        "delete_mode": {
                            "type": "string",
                            "enum": ["this_only", "this_and_after"],
                            "default": "this_and_after",
                        },
                    },
                    "required": ["task_id", "round_id"],
                },
            },
            "lh_retry_round": {
                "description": "重新执行特定轮次",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                        "round_id": {"description": "要重试的轮次ID或索引"},
                        "modified_input": {
                            "type": "object",
                            "description": "修改的输入参数",
                        },
                    },
                    "required": ["task_id", "round_id"],
                },
            },
            "lh_list_checkpoints": {
                "description": "列出所有 checkpoint",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                    },
                    "required": ["task_id"],
                },
            },
            "lh_create_checkpoint": {
                "description": "手动创建 checkpoint",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                        "label": {"type": "string", "description": "Checkpoint 标签"},
                        "note": {"type": "string", "description": "说明信息"},
                    },
                    "required": ["task_id", "label"],
                },
            },
            "lh_get_conversation_log": {
                "description": "获取完整的对话日志",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                        "include_prompts": {"type": "boolean", "default": True},
                        "include_responses": {"type": "boolean", "default": True},
                        "role_filter": {
                            "type": "string",
                            "enum": ["manager", "executor", "auditor", "all"],
                            "default": "all",
                        },
                    },
                    "required": ["task_id"],
                },
            },
            "lh_search_in_conversation": {
                "description": "在对话历史中搜索内容",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                        "query": {"type": "string", "description": "搜索关键词"},
                        "role_filter": {
                            "type": "string",
                            "enum": ["manager", "executor", "auditor", "all"],
                            "default": "all",
                        },
                        "search_in": {
                            "type": "string",
                            "enum": ["prompts", "responses", "all"],
                            "default": "all",
                        },
                    },
                    "required": ["task_id", "query"],
                },
            },
            "lh_get_execution_metrics": {
                "description": "获取任务的执行指标和统计信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                    },
                    "required": ["task_id"],
                },
            },
            "lh_validate_task_state": {
                "description": "验证任务状态一致性",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "任务ID"},
                        "fix_issues": {"type": "boolean", "default": False},
                    },
                    "required": ["task_id"],
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
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        try:
            if tool_name == "lh_start_task":
                return await self._handle_start_task(arguments)
            elif tool_name == "lh_get_task_status":
                return await self._handle_get_task_status(arguments)
            elif tool_name == "lh_execute_round":
                return await self._handle_execute_round(arguments)
            elif tool_name == "lh_get_checkpoint":
                return await self._handle_get_checkpoint(arguments)
            elif tool_name == "lh_recover_task":
                return await self._handle_recover_task(arguments)
            elif tool_name == "lh_pause_task":
                return await self._handle_pause_task(arguments)
            elif tool_name == "lh_stop_task":
                return await self._handle_stop_task(arguments)
            elif tool_name == "lh_inject_feedback":
                return await self._handle_inject_feedback(arguments)
            elif tool_name == "lh_get_audit_trail":
                return await self._handle_get_audit_trail(arguments)
            # Advanced APIs
            elif tool_name == "lh_get_task_config":
                return await self._handle_get_task_config(arguments)
            elif tool_name == "lh_update_task_config":
                return await self._handle_update_task_config(arguments)
            elif tool_name == "lh_get_round_detail":
                return await self._handle_get_round_detail(arguments)
            elif tool_name == "lh_list_rounds":
                return await self._handle_list_rounds(arguments)
            elif tool_name == "lh_edit_round":
                return await self._handle_edit_round(arguments)
            elif tool_name == "lh_delete_round":
                return await self._handle_delete_round(arguments)
            elif tool_name == "lh_retry_round":
                return await self._handle_retry_round(arguments)
            elif tool_name == "lh_list_checkpoints":
                return await self._handle_list_checkpoints(arguments)
            elif tool_name == "lh_create_checkpoint":
                return await self._handle_create_checkpoint(arguments)
            elif tool_name == "lh_get_conversation_log":
                return await self._handle_get_conversation_log(arguments)
            elif tool_name == "lh_search_in_conversation":
                return await self._handle_search_in_conversation(arguments)
            elif tool_name == "lh_get_execution_metrics":
                return await self._handle_get_execution_metrics(arguments)
            elif tool_name == "lh_validate_task_state":
                return await self._handle_validate_task_state(arguments)
            else:
                return {
                    "error": f"Unknown tool: {tool_name}",
                    "success": False,
                }
        except Exception as e:
            logger.error(f"Error handling tool {tool_name}: {e}", exc_info=True)
            return {
                "error": str(e),
                "success": False,
            }

    async def _handle_start_task(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_start_task tool call."""
        task = self.task_manager.start_task(
            goal=args["goal"],
            workspace=args["workspace"],
            max_rounds=args.get("max_rounds", 25),
            config=args.get("config"),
        )

        return {
            "success": True,
            "task_id": task.task_id,
            "status": task.status,
            "initial_plan": f"Task started: {task.goal}",
            "workspace": task.workspace,
            "max_rounds": task.max_rounds,
        }

    async def _handle_get_task_status(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_get_task_status tool call."""
        task = self.task_manager.get_task(args["task_id"])
        if not task:
            return {
                "success": False,
                "error": f"Task {args['task_id']} not found",
            }

        return {
            "success": True,
            "task_id": task.task_id,
            "status": task.status,
            "current_round": task.current_round,
            "total_rounds": task.max_rounds,
            "verified_progress": task.verified_progress,
            "current_step": task.current_step,
            "next_action": task.next_action,
        }

    async def _handle_execute_round(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_execute_round tool call."""
        result = await self.task_manager.execute_round(
            task_id=args["task_id"],
            user_input=args.get("user_input"),
        )

        return {
            "success": True,
            "round_id": result.round_id,
            "plan": result.plan,
            "execution_result": result.execution_result,
            "audit_report": result.audit_report,
            "status": result.status,
            "checkpoint": result.checkpoint,
            "duration_ms": result.duration_ms,
        }

    async def _handle_get_checkpoint(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_get_checkpoint tool call."""
        checkpoint = self.task_manager.get_checkpoint(args["task_id"])
        if not checkpoint:
            return {
                "success": False,
                "error": f"No checkpoint found for task {args['task_id']}",
            }

        return {
            "success": True,
            **checkpoint,
        }

    async def _handle_recover_task(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_recover_task tool call."""
        result = self.task_manager.recover_task(
            task_id=args["task_id"],
            checkpoint_id=args.get("checkpoint_id"),
        )

        return {
            "success": True,
            **result,
        }

    async def _handle_pause_task(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_pause_task tool call."""
        self.task_manager.pause_task(args["task_id"])

        return {
            "success": True,
            "task_id": args["task_id"],
            "message": "Task paused successfully",
        }

    async def _handle_stop_task(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_stop_task tool call."""
        self.task_manager.stop_task(
            task_id=args["task_id"],
            keep_artifacts=args.get("keep_artifacts", True),
        )

        return {
            "success": True,
            "task_id": args["task_id"],
            "message": "Task stopped successfully",
        }

    async def _handle_inject_feedback(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_inject_feedback tool call."""
        self.task_manager.inject_feedback(
            task_id=args["task_id"],
            feedback=args["feedback"],
            feedback_type=args["type"],
        )

        return {
            "success": True,
            "task_id": args["task_id"],
            "message": "Feedback injected successfully",
        }

    async def _handle_get_audit_trail(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_get_audit_trail tool call."""
        trail = self.task_manager.get_audit_trail(args["task_id"])

        return {
            "success": True,
            **trail,
        }

    # ========== Advanced API Handlers ==========

    async def _handle_get_task_config(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_get_task_config tool call."""
        config = self.advanced_manager.get_task_config(args["task_id"])
        return {"success": True, **config}

    async def _handle_update_task_config(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_update_task_config tool call."""
        result = self.advanced_manager.update_task_config(
            task_id=args["task_id"],
            config_updates=args["config_updates"],
        )
        return result

    async def _handle_get_round_detail(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_get_round_detail tool call."""
        detail = self.advanced_manager.get_round_detail(
            task_id=args["task_id"],
            round_id=args["round_id"],
        )
        return {"success": True, **detail}

    async def _handle_list_rounds(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_list_rounds tool call."""
        result = self.advanced_manager.list_rounds(
            task_id=args["task_id"],
            status_filter=args.get("status_filter"),
            offset=args.get("offset", 0),
            limit=args.get("limit", 20),
        )
        return {"success": True, **result}

    async def _handle_edit_round(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_edit_round tool call."""
        result = self.advanced_manager.edit_round(
            task_id=args["task_id"],
            round_id=args["round_id"],
            edits=args["edits"],
            reason=args["reason"],
        )
        return result

    async def _handle_delete_round(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_delete_round tool call."""
        result = self.advanced_manager.delete_round(
            task_id=args["task_id"],
            round_id=args["round_id"],
            delete_mode=args.get("delete_mode", "this_and_after"),
        )
        return result

    async def _handle_retry_round(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_retry_round tool call."""
        result = await self.advanced_manager.retry_round(
            task_id=args["task_id"],
            round_id=args["round_id"],
            modified_input=args.get("modified_input"),
        )
        return result

    async def _handle_list_checkpoints(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_list_checkpoints tool call."""
        result = self.advanced_manager.list_checkpoints(args["task_id"])
        return {"success": True, **result}

    async def _handle_create_checkpoint(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_create_checkpoint tool call."""
        result = self.advanced_manager.create_checkpoint(
            task_id=args["task_id"],
            label=args["label"],
            note=args.get("note"),
        )
        return result

    async def _handle_get_conversation_log(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_get_conversation_log tool call."""
        result = self.advanced_manager.get_conversation_log(
            task_id=args["task_id"],
            include_prompts=args.get("include_prompts", True),
            include_responses=args.get("include_responses", True),
            role_filter=args.get("role_filter", "all"),
        )
        return {"success": True, **result}

    async def _handle_search_in_conversation(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_search_in_conversation tool call."""
        result = self.advanced_manager.search_in_conversation(
            task_id=args["task_id"],
            query=args["query"],
            role_filter=args.get("role_filter", "all"),
            search_in=args.get("search_in", "all"),
        )
        return {"success": True, **result}

    async def _handle_get_execution_metrics(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_get_execution_metrics tool call."""
        result = self.advanced_manager.get_execution_metrics(args["task_id"])
        return {"success": True, **result}

    async def _handle_validate_task_state(self, args: dict[str, Any]) -> dict[str, Any]:
        """Handle lh_validate_task_state tool call."""
        result = self.advanced_manager.validate_task_state(
            task_id=args["task_id"],
            fix_issues=args.get("fix_issues", False),
        )
        return result


def create_mcp_server(state_root: str = "~/.lh-harness") -> LongHorizonMCPServer:
    """Create an MCP server instance.

    Args:
        state_root: Root directory for task state storage

    Returns:
        Configured LongHorizonMCPServer instance
    """
    return LongHorizonMCPServer(state_root)


async def run_mcp_server(
    state_root: str = "~/.lh-harness",
    transport: str = "stdio",
) -> None:
    """Run the MCP server.

    Args:
        state_root: Root directory for task state storage
        transport: Transport method ('stdio' or 'http')
    """
    server = create_mcp_server(state_root)

    if transport == "stdio":
        await _run_stdio_server(server)
    elif transport == "http":
        await _run_http_server(server)
    else:
        raise ValueError(f"Unsupported transport: {transport}")


async def _run_stdio_server(server: LongHorizonMCPServer) -> None:
    """Run MCP server over stdio.

    Reads JSON-RPC requests from stdin and writes responses to stdout.
    """
    import sys

    logger.info("Starting MCP server on stdio")

    while True:
        try:
            # Read one line from stdin
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )

            if not line:
                break

            # Parse JSON-RPC request
            request = json.loads(line.strip())

            # Handle request
            if request.get("method") == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "tools": [
                            {"name": name, **schema}
                            for name, schema in server.tools.items()
                        ]
                    },
                }
            elif request.get("method") == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                result = await server.handle_tool_call(tool_name, arguments)

                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]},
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {request.get('method')}",
                    },
                }

            # Write response to stdout
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)


async def _run_http_server(server: LongHorizonMCPServer) -> None:
    """Run MCP server over HTTP with SSE.

    TODO: Implement HTTP transport
    """
    raise NotImplementedError("HTTP transport not yet implemented")
