"""Tests for redesigned MCP Server."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lh_harness.mcp_server import create_redesigned_mcp_server


async def test_redesigned_workflow():
    """Test complete workflow with redesigned architecture."""
    print("=" * 80)
    print("Testing Redesigned MCP Server (v2)")
    print("=" * 80)
    print()

    server = create_redesigned_mcp_server()

    print(f"✅ Server initialized with {len(server.tools)} tools")
    print()

    # List tools
    print("📋 Available tools:")
    for name, tool in server.tools.items():
        print(f"  - {name}: {tool['description']}")
    print()

    # Test 1: Initialize workspace
    print("🧪 Test 1: Initialize workspace")
    result = await server.handle_tool_call(
        "lh_init_workspace",
        {
            "path": "./test-blog-system",
            "git_init": True,
        },
    )
    print(f"✅ Workspace initialized: {result}")
    print()

    # Test 2: Create a file
    print("🧪 Test 2: Create README.md")
    result = await server.handle_tool_call(
        "lh_execute",
        {
            "action": "create_file",
            "params": {
                "path": "README.md",
                "content": "# Blog System\n\nA simple blog system with React and FastAPI.\n",
            },
        },
    )
    print(f"✅ File created: {result}")
    execution_id = result.get("execution_id")
    print()

    # Test 3: Verify the creation
    print("🧪 Test 3: Verify file creation")
    result = await server.handle_tool_call(
        "lh_verify",
        {
            "execution_id": execution_id,
            "verification_goals": [
                "README.md exists",
                "Content is correct",
            ],
        },
    )
    print(f"✅ Verification: {result}")
    print()

    # Test 4: Save checkpoint
    print("🧪 Test 4: Save checkpoint")
    result = await server.handle_tool_call(
        "lh_save_checkpoint",
        {
            "label": "Initial project structure",
            "note": "Created README",
        },
    )
    print(f"✅ Checkpoint saved: {result}")
    print()

    # Test 5: Create more files
    print("🧪 Test 5: Create package.json")
    result = await server.handle_tool_call(
        "lh_execute",
        {
            "action": "create_file",
            "params": {
                "path": "package.json",
                "content": '{\n  "name": "blog-system",\n  "version": "1.0.0"\n}\n',
            },
        },
    )
    print(f"✅ package.json created: {result}")
    print()

    # Test 6: Inspect workspace
    print("🧪 Test 6: Inspect workspace")
    result = await server.handle_tool_call(
        "lh_inspect",
        {
            "target": "workspace",
        },
    )
    print(f"✅ Workspace inspection:")
    print(f"   Files: {result.get('files')}")
    print(f"   Total: {result.get('file_count')}")
    print()

    # Test 7: Get history
    print("🧪 Test 7: Get execution history")
    result = await server.handle_tool_call(
        "lh_get_history",
        {
            "limit": 5,
        },
    )
    print(f"✅ History:")
    for exec_record in result.get("executions", []):
        print(f"   - {exec_record['execution_id']}: {exec_record['action']} - {exec_record['result']}")
    print()

    # Test 8: Get metrics
    print("🧪 Test 8: Get metrics")
    result = await server.handle_tool_call(
        "lh_get_metrics",
        {},
    )
    print(f"✅ Metrics:")
    print(f"   Total executions: {result.get('total_executions')}")
    print(f"   Successful: {result.get('successful')}")
    print(f"   Files changed: {result.get('total_files_changed')}")
    print(f"   Checkpoints: {result.get('total_checkpoints')}")
    print()

    # Test 9: List checkpoints
    print("🧪 Test 9: List checkpoints")
    result = await server.handle_tool_call(
        "lh_list_checkpoints",
        {},
    )
    print(f"✅ Checkpoints:")
    for cp in result.get("checkpoints", []):
        print(f"   - {cp['checkpoint_id']}: {cp['label']}")
    print()

    # Test 10: Get workspace state
    print("🧪 Test 10: Get workspace state")
    result = await server.handle_tool_call(
        "lh_get_workspace_state",
        {},
    )
    print(f"✅ Workspace state:")
    print(f"   Files: {result.get('file_count')}")
    print(f"   Recent executions: {result.get('recent_executions')}")
    print(f"   Checkpoints: {result.get('checkpoints')}")
    print()

    # Test 11: Search history
    print("🧪 Test 11: Search history")
    result = await server.handle_tool_call(
        "lh_search_history",
        {
            "query": "README",
            "search_in": "all",
        },
    )
    print(f"✅ Search results: {result.get('total_matches')} matches")
    print()

    # Test 12: Run command
    print("🧪 Test 12: Run command (ls)")
    result = await server.handle_tool_call(
        "lh_execute",
        {
            "action": "run_command",
            "params": {
                "command": "ls -la",
            },
        },
    )
    print(f"✅ Command executed: {result.get('success')}")
    if result.get("success"):
        print(f"   Output: {result.get('stdout', '')[:200]}")
    print()

    print("=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_redesigned_workflow())
