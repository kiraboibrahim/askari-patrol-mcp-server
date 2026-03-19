"""
Unit tests for the AskariAgent authentication and session restoration logic.

These tests verify that the agent correctly handles session expiry on the MCP server
by proactively attempting to restore the session from the conversation history
before proceeding with user requests.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.messages import ModelResponse, ToolReturnPart

from askari_patrol_client.agent import AskariAgent


@pytest.mark.asyncio
async def test_run_restores_session_when_expired_if_history_exists():
    """
    Test that agent.run correctly restores the session if it's expired
    but a valid token exists in history.

    This scenario simulates:
    1. Agent is connected and has history from a previous session.
    2. Server session times out or server restarts (is_authenticated returns False).
    3. User sends a message.
    4. Agent detects unauthenticated state, finds the token in history, calls restore_session.
    5. Agent verifies authentication again and successfully proceeds to LLM.
    """

    # --- 1. Setup mocks ---
    mock_server = AsyncMock()

    # Define authentication response objects
    mock_auth_res_false = MagicMock()
    mock_auth_res_false.content = [MagicMock(text=json.dumps({"authenticated": False}))]

    mock_auth_res_true = MagicMock()
    mock_auth_res_true.content = [MagicMock(text=json.dumps({"authenticated": True}))]

    # Setup LLM Agent and its run result
    mock_ai_agent = MagicMock()
    mock_run_result = MagicMock()
    mock_run_result.output = "Success"
    mock_run_result.new_messages.return_value = []
    mock_ai_agent.run = AsyncMock(return_value=mock_run_result)

    # Mock ConversationDB (avoiding actual file I/O)
    mock_db = MagicMock()
    mock_db.load_history = AsyncMock(return_value=[])
    mock_db.save_message = AsyncMock()

    # Patch dependencies
    with patch(
        "askari_patrol_client.agent.MCPServerStreamableHTTP", return_value=mock_server
    ), patch("askari_patrol_client.agent.Agent", return_value=mock_ai_agent), patch(
        "askari_patrol_client.agent.ConversationDB", return_value=mock_db
    ), patch.dict("os.environ", {"GOOGLE_API_KEY": "dummy"}), patch(
        "askari_patrol_client.agent.is_token_valid", return_value=True
    ):
        # Initialize and connect the agent
        agent = AskariAgent(phone_number="test_user")
        await agent.connect()

        # --- 2. Action: Simulate disconnected state with valid history ---

        # Manually inject history with a successful login tool return.
        # This matches the structure found in the production database (no 'success' field).
        login_part = ToolReturnPart(
            tool_name="login",
            content=json.dumps({"access_token": "valid_dummy_token"}),
            tool_call_id="call_1",
        )
        agent._history = [ModelResponse(parts=[login_part])]

        # Setup the mock for the sequence of calls during agent.run():
        # 1. First is_authenticated() check (returns False)
        # 2. restore_session() call (returns None/ignored)
        # 3. Second is_authenticated() check (returns True)
        mock_server.direct_call_tool.reset_mock()
        mock_server.direct_call_tool.side_effect = [
            mock_auth_res_false,  # Pre-flight check fails
            None,  # restore_session called behind the scenes
            mock_auth_res_true,  # Post-restore check succeeds
        ]

        # Execute the agent call
        result = await agent.run("get guards of Test site")

        # --- 3. Verification ---
        assert result == "Success", "Agent should have successfully returned LLM output"

        # Verify the sequence and substance of MCP tool calls
        calls = mock_server.direct_call_tool.call_args_list
        assert len(calls) == 3, "Expected 3 tool calls: check -> restore -> check"

        # Check 1: Initial auth check
        assert calls[0][0][0] == "is_authenticated"

        # Check 2: Silent restoration using the token from history
        assert calls[1][0][0] == "restore_session"
        assert calls[1][0][1] == {"token": "valid_dummy_token"}

        # Check 3: Final auth check before proceeding
        assert calls[2][0][0] == "is_authenticated"

        # Verify that the LLM was indeed invoked after successful restoration
        mock_ai_agent.run.assert_called_once()
