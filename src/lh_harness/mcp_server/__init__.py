"""MCP Server implementation for LongHorizon-Harness.

This module exposes LongHorizon-Harness capabilities as an MCP server
that can be called by Claude Code, Codex, or other MCP-compatible tools.
"""

from .server import create_mcp_server, run_mcp_server

__all__ = ["create_mcp_server", "run_mcp_server"]
