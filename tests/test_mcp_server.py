"""
MCP Server Integration Test

Tests the LongHorizon-Harness MCP server functionality.
"""

import asyncio
import json

import pytest

from lh_harness.mcp_server import create_mcp_server


@pytest.fixture
def server():
    """Create a test MCP server instance."""
    return create_mcp_server(state_root="/tmp/lh-harness-test")


@pytest.mark.asyncio
async def test_start_task(server):
    """Test starting a new task."""
    result = await server.handle_tool_call(
        "lh_start_task",
        {
            "goal": "Test task: Create a simple Python script",
            "workspace": "/tmp/test-workspace",
            "max_rounds": 10,
        },
    )

    assert result["success"] is True
    assert "task_id" in result
    assert result["status"] == "started"
    assert result["max_rounds"] == 10

    return result["task_id"]


@pytest.mark.asyncio
async def test_get_task_status(server):
    """Test getting task status."""
    # First start a task
    start_result = await server.handle_tool_call(
        "lh_start_task",
        {
            "goal": "Test task",
            "workspace": "/tmp/test-workspace",
        },
    )

    task_id = start_result["task_id"]

    # Now get its status
    result = await server.handle_tool_call(
        "lh_get_task_status",
        {"task_id": task_id},
    )

    assert result["success"] is True
    assert result["task_id"] == task_id
    assert result["status"] == "started"
    assert result["current_round"] == 0


@pytest.mark.asyncio
async def test_execute_round(server):
    """Test executing a round."""
    # Start a task
    start_result = await server.handle_tool_call(
        "lh_start_task",
        {
            "goal": "Test task",
            "workspace": "/tmp/test-workspace",
        },
    )

    task_id = start_result["task_id"]

    # Execute first round
    result = await server.handle_tool_call(
        "lh_execute_round",
        {"task_id": task_id},
    )

    assert result["success"] is True
    assert "round_id" in result
    assert "plan" in result
    assert "execution_result" in result
    assert "audit_report" in result
    assert result["status"] in ["complete", "incomplete", "blocked"]


@pytest.mark.asyncio
async def test_checkpoint_and_recovery(server):
    """Test checkpoint creation and task recovery."""
    # Start a task
    start_result = await server.handle_tool_call(
        "lh_start_task",
        {
            "goal": "Test task",
            "workspace": "/tmp/test-workspace",
        },
    )

    task_id = start_result["task_id"]

    # Execute a round to create a checkpoint
    await server.handle_tool_call(
        "lh_execute_round",
        {"task_id": task_id},
    )

    # Get checkpoint
    checkpoint_result = await server.handle_tool_call(
        "lh_get_checkpoint",
        {"task_id": task_id},
    )

    assert checkpoint_result["success"] is True
    assert "checkpoint_id" in checkpoint_result
    assert "verified_state" in checkpoint_result

    # Recover task
    recover_result = await server.handle_tool_call(
        "lh_recover_task",
        {"task_id": task_id},
    )

    assert recover_result["success"] is True
    assert "recovered_state" in recover_result
    assert "next_plan" in recover_result


@pytest.mark.asyncio
async def test_pause_and_stop_task(server):
    """Test pausing and stopping a task."""
    # Start a task
    start_result = await server.handle_tool_call(
        "lh_start_task",
        {
            "goal": "Test task",
            "workspace": "/tmp/test-workspace",
        },
    )

    task_id = start_result["task_id"]

    # Pause task
    pause_result = await server.handle_tool_call(
        "lh_pause_task",
        {"task_id": task_id},
    )

    assert pause_result["success"] is True

    # Check status is paused
    status = await server.handle_tool_call(
        "lh_get_task_status",
        {"task_id": task_id},
    )
    # Status might be "started" if no rounds were executed
    assert status["status"] in ["started", "paused"]

    # Stop task
    stop_result = await server.handle_tool_call(
        "lh_stop_task",
        {"task_id": task_id, "keep_artifacts": True},
    )

    assert stop_result["success"] is True


@pytest.mark.asyncio
async def test_inject_feedback(server):
    """Test injecting feedback into a task."""
    # Start a task
    start_result = await server.handle_tool_call(
        "lh_start_task",
        {
            "goal": "Test task",
            "workspace": "/tmp/test-workspace",
        },
    )

    task_id = start_result["task_id"]

    # Inject feedback
    feedback_result = await server.handle_tool_call(
        "lh_inject_feedback",
        {
            "task_id": task_id,
            "feedback": "Please use Python 3.11 instead of 3.10",
            "type": "correction",
        },
    )

    assert feedback_result["success"] is True


@pytest.mark.asyncio
async def test_get_audit_trail(server):
    """Test getting the complete audit trail."""
    # Start a task
    start_result = await server.handle_tool_call(
        "lh_start_task",
        {
            "goal": "Test task",
            "workspace": "/tmp/test-workspace",
        },
    )

    task_id = start_result["task_id"]

    # Execute a few rounds
    await server.handle_tool_call("lh_execute_round", {"task_id": task_id})
    await server.handle_tool_call("lh_execute_round", {"task_id": task_id})

    # Get audit trail
    trail_result = await server.handle_tool_call(
        "lh_get_audit_trail",
        {"task_id": task_id},
    )

    assert trail_result["success"] is True
    assert trail_result["task_id"] == task_id
    assert "total_rounds" in trail_result
    assert "rounds" in trail_result
    assert "checkpoints" in trail_result
    assert trail_result["total_rounds"] == 2


@pytest.mark.asyncio
async def test_invalid_task_id(server):
    """Test handling of invalid task IDs."""
    result = await server.handle_tool_call(
        "lh_get_task_status",
        {"task_id": "invalid_task_id"},
    )

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_tools_list(server):
    """Test that all expected tools are registered."""
    expected_tools = [
        "lh_start_task",
        "lh_get_task_status",
        "lh_execute_round",
        "lh_get_checkpoint",
        "lh_recover_task",
        "lh_pause_task",
        "lh_stop_task",
        "lh_inject_feedback",
        "lh_get_audit_trail",
    ]

    for tool_name in expected_tools:
        assert tool_name in server.tools
        assert "description" in server.tools[tool_name]
        assert "parameters" in server.tools[tool_name]


if __name__ == "__main__":
    # Run a simple interactive test
    async def interactive_test():
        print("Starting LongHorizon-Harness MCP Server Interactive Test")
        print("=" * 60)

        server = create_mcp_server()

        # Start a task
        print("\n1. Starting a new task...")
        start_result = await server.handle_tool_call(
            "lh_start_task",
            {
                "goal": "Create a Python web scraper for news articles",
                "workspace": "./test-workspace",
                "max_rounds": 15,
            },
        )
        print(json.dumps(start_result, indent=2, ensure_ascii=False))

        task_id = start_result["task_id"]

        # Execute first round
        print("\n2. Executing first round...")
        round1 = await server.handle_tool_call(
            "lh_execute_round",
            {"task_id": task_id},
        )
        print(json.dumps(round1, indent=2, ensure_ascii=False))

        # Get status
        print("\n3. Getting task status...")
        status = await server.handle_tool_call(
            "lh_get_task_status",
            {"task_id": task_id},
        )
        print(json.dumps(status, indent=2, ensure_ascii=False))

        # Get checkpoint
        print("\n4. Getting checkpoint...")
        checkpoint = await server.handle_tool_call(
            "lh_get_checkpoint",
            {"task_id": task_id},
        )
        print(json.dumps(checkpoint, indent=2, ensure_ascii=False))

        # Inject feedback
        print("\n5. Injecting feedback...")
        feedback = await server.handle_tool_call(
            "lh_inject_feedback",
            {
                "task_id": task_id,
                "feedback": "Please add rate limiting to avoid being blocked",
                "type": "guidance",
            },
        )
        print(json.dumps(feedback, indent=2, ensure_ascii=False))

        # Execute another round
        print("\n6. Executing second round with feedback...")
        round2 = await server.handle_tool_call(
            "lh_execute_round",
            {"task_id": task_id},
        )
        print(json.dumps(round2, indent=2, ensure_ascii=False))

        # Get audit trail
        print("\n7. Getting complete audit trail...")
        trail = await server.handle_tool_call(
            "lh_get_audit_trail",
            {"task_id": task_id},
        )
        print(json.dumps(trail, indent=2, ensure_ascii=False))

        # Pause task
        print("\n8. Pausing task...")
        pause = await server.handle_tool_call(
            "lh_pause_task",
            {"task_id": task_id},
        )
        print(json.dumps(pause, indent=2, ensure_ascii=False))

        print("\n" + "=" * 60)
        print("Interactive test completed successfully!")

    asyncio.run(interactive_test())
