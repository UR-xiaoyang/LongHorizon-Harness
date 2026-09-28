"""MCP server CLI command."""

import argparse
import asyncio
import logging
import sys

from .mcp_server import run_mcp_server


def add_mcp_server_command(subparsers):
    """Add mcp-server command to CLI."""
    parser = subparsers.add_parser(
        "mcp-server",
        help="Start LongHorizon-Harness as an MCP server",
        description=(
            "Start the MCP server to expose LongHorizon-Harness capabilities "
            "to Claude Code, Codex, or other MCP-compatible tools."
        ),
    )

    parser.add_argument(
        "--state-root",
        type=str,
        default="~/.lh-harness",
        help="Root directory for task state storage (default: ~/.lh-harness)",
    )

    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "http"],
        default="stdio",
        help="Transport method (default: stdio)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--log-file",
        type=str,
        help="Optional log file path (default: stderr only)",
    )

    parser.set_defaults(func=run_mcp_server_command)


def run_mcp_server_command(args):
    """Run the MCP server command."""
    # Configure logging
    log_handlers = []

    if args.log_file:
        log_handlers.append(logging.FileHandler(args.log_file))
    else:
        # Log to stderr to avoid interfering with stdio communication
        log_handlers.append(logging.StreamHandler(sys.stderr))

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=log_handlers,
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Starting LongHorizon-Harness MCP server")
    logger.info(f"Transport: {args.transport}")
    logger.info(f"State root: {args.state_root}")

    # Run the server
    try:
        asyncio.run(
            run_mcp_server(
                state_root=args.state_root,
                transport=args.transport,
            )
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
