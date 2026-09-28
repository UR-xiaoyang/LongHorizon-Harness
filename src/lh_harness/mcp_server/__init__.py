"""MCP Server implementation for LongHorizon-Harness.

This module exposes LongHorizon-Harness capabilities as an MCP server
that can be called by Claude Code, Codex, or other MCP-compatible tools.

Provides two architectures:
- V1 (Original): 23 tools with full task management
- V2 (Redesigned): 12 focused tools where Claude is the main controller (recommended)
"""

from .redesigned_server import (
    RedesignedMCPServer,
    create_redesigned_mcp_server,
    run_redesigned_mcp_server,
)
from .server import create_mcp_server, run_mcp_server
from .workspace_manager import WorkspaceManager

__all__ = [
    # V2 (Redesigned) - Recommended
    "RedesignedMCPServer",
    "create_redesigned_mcp_server",
    "run_redesigned_mcp_server",
    "WorkspaceManager",
    # V1 (Original)
    "create_mcp_server",
    "run_mcp_server",
]
