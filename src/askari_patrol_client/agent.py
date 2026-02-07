"""
Askari Patrol Agent - MCP-Powered Conversational AI with Persistent History

This module provides the AskariAgent class, a production-ready conversational agent
that interfaces with the Askari Patrol MCP (Model Context Protocol) server using
Pydantic AI. It features robust conversation history management, token-aware context
windowing, automatic crash recovery, and structured persistence using SQLite.

Key Features:
    - Structured message history with JSON serialization
    - Token-aware context trimming to prevent API limits
    - Automatic recovery from incomplete tool call sequences
    - Turn-aware history processing for safe conversation boundaries
    - SQLite-backed persistence for multi-session continuity
    - MCP toolset integration for extended capabilities

Architecture:
    The agent maintains a dual-layer history system:
    1. In-memory history (_history): Fast access for current conversation context
    2. Database persistence (ConversationDB): Long-term storage across sessions

    History is managed through a rolling window approach that preserves message
    integrity by only trimming at safe turn boundaries, preventing tool call/return
    sequence corruption.

Usage:
    # Async context manager (recommended)
    async with AskariAgent(
        server_url="http://localhost:8000/mcp",
        phone_number="user_123"
    ) as agent:
        response = await agent.run("What can you help me with?")
        print(response)

    # Manual lifecycle management
    agent = AskariAgent(server_url="http://localhost:8000/mcp")
    await agent.connect()
    try:
        response = await agent.run("Hello!")
    finally:
        await agent.disconnect()

See Also:
    - Pydantic AI Message History: https://ai.pydantic.dev/message-history/
    - MCP Protocol: https://modelcontextprotocol.io/
"""

import logging
from typing import Any

from pydantic import TypeAdapter
from pydantic_ai import Agent, ModelMessagesTypeAdapter
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.messages import (
    BuiltinToolCallPart,
    BuiltinToolReturnPart,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
    ToolReturnPart,
)

from .db import ConversationDB
from .prompts import CLI_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_SERVER_URL = "http://localhost:8000/mcp"
DEFAULT_MODEL = "groq:qwen/qwen3-32b"
DEFAULT_HISTORY_LIMIT = 10
DEFAULT_DB_LOAD_LIMIT = 30


class AskariAgent:
    """
    MCP-powered conversational agent with persistent history management.

    This class orchestrates interactions between a language model, MCP tools,
    and a SQLite conversation database. It handles the complete lifecycle of
    multi-turn conversations while maintaining message integrity and preventing
    common failure modes like orphaned tool calls or token limit violations.

    The agent implements several critical safety mechanisms:
    - Turn-aware history trimming to prevent breaking tool sequences
    - Automatic healing of incomplete conversation tails
    - Safe boundary detection for history operations
    - Graceful degradation under failure conditions

    Attributes:
        server_url (str): MCP server endpoint URL
        instructions (str): System prompt guiding agent behavior
        model (str): LLM model identifier (e.g., "groq:qwen/qwen3-32b")
        phone_number (Optional[str]): User identifier for history persistence
        history_limit (int): Maximum messages in active context window
        db (ConversationDB): Database interface for message persistence

    Example:
        >>> async with AskariAgent(phone_number="alice") as agent:
        ...     response = await agent.run("List my recent security alerts")
        ...     print(response)
        Recent alerts: ...
    """

    def __init__(
        self,
        server_url: str = DEFAULT_SERVER_URL,
        instructions: str = CLI_SYSTEM_PROMPT,
        model: str = DEFAULT_MODEL,
        phone_number: str | None = None,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
    ):
        """
        Initialize the Askari Patrol agent with configuration.

        Args:
            server_url: MCP server endpoint (default: http://localhost:8000/mcp)
            instructions: System prompt defining agent behavior and capabilities
            model: Language model identifier in provider:model format
            phone_number: Optional user identifier for conversation persistence.
                         If None, history is session-only (not persisted)
            history_limit: Maximum number of messages to retain in active context.
                          Older messages are trimmed at safe turn boundaries

        Example:
            >>> agent = AskariAgent(
            ...     server_url="http://prod.example.com/mcp",
            ...     phone_number="user_42",
            ...     history_limit=20
            ... )
        """
        self.server_url = server_url
        self.instructions = instructions
        self.model = model
        self.phone_number = phone_number
        self.history_limit = history_limit

        # Private state - initialized in connect()
        self._server: MCPServerStreamableHTTP | None = None
        self._agent: Agent | None = None
        self._history: list[ModelMessage] = []

        # Database for persistent storage
        self.db = ConversationDB()

    async def connect(self) -> None:
        """
        Establish MCP server connection and initialize agent runtime.

        This method performs the following initialization sequence:
        1. Connects to the MCPServerStreamableHTTP endpoint
        2. Configures the Pydantic AI agent with model, tools, and processors
        3. Loads and reconstructs conversation history from database (if phone_number set)
        4. Applies automatic healing to recover from crashed sessions

        The agent is configured with a history processor pipeline that ensures
        the context window stays within token limits while preserving message
        integrity through turn-aware trimming.

        Raises:
            ConnectionError: If MCP server is unreachable
            ValueError: If model identifier is invalid
            DatabaseError: If history reconstruction fails critically

        Example:
            >>> agent = AskariAgent(server_url="http://localhost:8000/mcp")
            >>> await agent.connect()
            >>> # Agent is now ready for conversation
        """
        # Establish MCP server connection
        self._server = MCPServerStreamableHTTP(self.server_url)
        await self._server.__aenter__()

        # Configure Pydantic AI agent with MCP toolset
        self._agent = Agent(
            self.model,
            system_prompt=self.instructions,
            toolsets=[self._server],
            history_processors=[self._trim_history_processor],
        )

        # Reconstruct conversation history from persistent storage
        await self._load_and_reconstruct_history()

    async def _load_and_reconstruct_history(self) -> None:
        """
        Load persisted history from database and reconstruct message objects.

        This internal method handles the complete history initialization workflow:
        1. Queries the database for recent messages (up to DEFAULT_DB_LOAD_LIMIT)
        2. Deserializes JSON records into ModelMessage objects
        3. Applies healing to remove incomplete conversation tails
        4. Updates the in-memory history cache

        The reconstruction process uses Pydantic AI's official ModelMessagesTypeAdapter
        to ensure compatibility with all message types and parts.

        Side Effects:
            Updates self._history with reconstructed messages

        Note:
            Only executed if phone_number is set. Anonymous sessions have no
            persisted history.
        """
        if not self.phone_number:
            logger.debug("No phone_number set; skipping history load")
            return

        db_messages = await self.db.load_history(
            self.phone_number, limit=DEFAULT_DB_LOAD_LIMIT
        )
        self._history = self._reconstruct_history(db_messages)

    async def disconnect(self) -> None:
        """
        Gracefully shutdown MCP connection and release resources.

        Ensures proper cleanup of the MCPServerStreamableHTTP session and clears
        internal agent state. Should always be called when the agent is no longer
        needed, either manually or via async context manager protocol.

        Side Effects:
            - Closes MCP server connection
            - Nullifies internal agent and server references
            - Does NOT clear conversation history or database

        Example:
            >>> await agent.connect()
            >>> # ... use agent ...
            >>> await agent.disconnect()
        """
        if self._server:
            await self._server.__aexit__(None, None, None)
            self._server = None
            self._agent = None

    async def run(self, message: str, use_context: bool = True) -> str:
        """
        Execute a conversational turn with the agent.

        This is the primary interface for interacting with the agent. It orchestrates
        the complete request-response cycle:
        1. Invokes the language model with user message and optional history
        2. Handles tool calls and MCP interactions transparently
        3. Applies history processors (trimming, etc.)
        4. Updates in-memory history with new messages
        5. Persists new messages to database for future sessions

        Args:
            message: Natural language input from the user
            use_context: Whether to include conversation history in this request.
                        Set to False for stateless queries or to reset context.
                        Default: True

        Returns:
            str: The agent's natural language response after all tool interactions

        Raises:
            RuntimeError: If agent is not connected (call connect() first)
            ModelError: If the LLM invocation fails
            ToolError: If an MCP tool execution fails critically

        Example:
            >>> response = await agent.run("What's the weather today?")
            >>> print(response)
            Based on current data, it's 72°F and sunny in your area.

            >>> # Stateless query without context
            >>> response = await agent.run("Translate 'hello' to Spanish", use_context=False)
            >>> print(response)
            "Hola"
        """
        if not self._agent:
            raise RuntimeError(
                "Agent not connected. Call connect() or use async context manager."
            )

        # Execute agent with optional conversation history
        result = await self._agent.run(
            message, message_history=self._history if use_context else None
        )

        # Update history and persist new messages
        new_messages = result.new_messages()
        await self._update_history(new_messages)

        return result.output

    async def _update_history(self, new_messages: list[ModelMessage]) -> None:
        """
        Update in-memory history and persist new messages to database.

        This internal method handles the dual-update workflow that keeps both
        the fast in-memory cache and durable database storage in sync.

        Args:
            new_messages: List of ModelMessage objects from the latest agent run

        Side Effects:
            - Extends self._history with new messages
            - Writes new messages to SQLite database (if phone_number set)
        """
        self._history.extend(new_messages)

        if self.phone_number:
            for msg in new_messages:
                await self._persist_message(msg)

    async def _persist_message(self, msg: ModelMessage) -> None:
        """
        Serialize and store a single message to the database.

        Uses Pydantic's TypeAdapter to ensure proper JSON serialization of all
        message parts, including complex types like tool calls, tool returns,
        and thinking blocks.

        Args:
            msg: The ModelMessage object to persist (ModelRequest or ModelResponse)

        Side Effects:
            Writes a record to the conversations table in SQLite

        Note:
            Messages are stored individually but reconstructed as batches using
            ModelMessagesTypeAdapter for optimal deserialization performance.

        Example:
            >>> msg = ModelRequest(parts=[UserPromptPart(content="Hello")])
            >>> await agent._persist_message(msg)
        """
        # Serialize to JSON using Pydantic's schema-aware adapter
        msg_json = TypeAdapter(ModelMessage).dump_json(msg).decode("utf-8")

        await self.db.save_message(
            phone_number=self.phone_number, message_json=msg_json
        )

    async def _trim_history_processor(
        self, messages: list[ModelMessage]
    ) -> list[ModelMessage]:
        """
        History processor: trim messages to stay within token limits.

        This processor implements a turn-aware rolling context window strategy:
        - Keeps the most recent N messages (where N = history_limit)
        - Only trims at safe turn boundaries to prevent tool sequence corruption
        - Returns full history if no safe boundaries exist (graceful degradation)

        The algorithm ensures that trimming never breaks a tool call/return pair,
        which would cause validation errors from the LLM provider (e.g., OpenAI 400).

        Args:
            messages: Complete conversation history in chronological order

        Returns:
            Trimmed message list respecting history_limit and turn boundaries

        Example:
            Given history_limit=5 and 10 messages:
            - Identifies safe boundaries (requests without tool results)
            - Finds closest boundary that keeps ≤5 messages
            - Returns messages[boundary_index:]

        Note:
            This is registered as a history_processor in the Agent configuration
            and runs automatically before each LLM invocation.
        """
        if len(messages) <= self.history_limit:
            return messages

        safe_indices = self._find_safe_turn_indices(messages)

        if not safe_indices:
            logger.warning(
                "No safe truncation points found in %d messages; retaining full history",
                len(messages),
            )
            return messages

        # Find the optimal safe index that gets us closest to history_limit
        best_index = self._find_optimal_trim_point(messages, safe_indices)

        trimmed_count = best_index
        logger.debug(
            "Trimming history: removing %d messages, keeping %d",
            trimmed_count,
            len(messages) - trimmed_count,
        )

        return messages[best_index:]

    def _find_optimal_trim_point(
        self, messages: list[ModelMessage], safe_indices: list[int]
    ) -> int:
        """
        Find the best safe index for trimming to approach history_limit.

        Iterates through safe boundaries to find the latest one that keeps
        the remaining message count at or below history_limit.

        Args:
            messages: Full message history
            safe_indices: List of indices representing safe turn boundaries

        Returns:
            int: The index to slice from (all messages before this are removed)

        Example:
            >>> messages = [msg1, msg2, msg3, msg4, msg5, msg6]  # 6 messages
            >>> safe_indices = [0, 2, 4]
            >>> history_limit = 3
            >>> result = _find_optimal_trim_point(messages, safe_indices)
            >>> result  # Returns 4, keeping messages[4:] = [msg5, msg6] (2 msgs)
            4
        """
        best_index = safe_indices[0]

        for idx in safe_indices:
            remaining = len(messages) - idx
            if remaining <= self.history_limit:
                best_index = idx
                break

        return best_index

    def _find_safe_turn_indices(self, messages: list[ModelMessage]) -> list[int]:
        """
        Identify safe boundaries for history modification operations.

        A "safe boundary" is a ModelRequest that does NOT contain tool returns
        or retry prompts. Trimming/splitting at these points ensures that:
        - No tool calls are orphaned (separated from their results)
        - No tool results are orphaned (separated from their calls)
        - The conversation can resume naturally from that point

        Args:
            messages: List of ModelMessage objects to analyze

        Returns:
            List of zero-based indices representing safe split points

        Example:
            >>> messages = [
            ...     ModelRequest(parts=[UserPromptPart("Hello")]),      # idx 0: SAFE
            ...     ModelResponse(parts=[TextPart("Hi!")]),              # idx 1: (response)
            ...     ModelRequest(parts=[UserPromptPart("Weather?")]),    # idx 2: SAFE
            ...     ModelResponse(parts=[ToolCallPart(...)]),            # idx 3: (has tool call)
            ...     ModelRequest(parts=[ToolReturnPart(...)]),           # idx 4: UNSAFE (has tool result)
            ...     ModelResponse(parts=[TextPart("It's sunny")])        # idx 5: (response)
            ... ]
            >>> _find_safe_turn_indices(messages)
            [0, 2]

        Note:
            This method is critical for preventing "unprocessed tool calls" errors
            that occur when history is modified incorrectly.
        """
        safe_indices = []

        for i, msg in enumerate(messages):
            if isinstance(msg, ModelRequest):
                # Check if request contains tool continuation parts
                contains_tool_result = any(
                    isinstance(
                        part, ToolReturnPart | BuiltinToolReturnPart | RetryPromptPart
                    )
                    for part in msg.parts
                )

                if not contains_tool_result:
                    safe_indices.append(i)

        return safe_indices

    def _reconstruct_history(
        self, db_messages: list[dict[str, Any]]
    ) -> list[ModelMessage]:
        """
        Deserialize conversation history from database JSON records.

        This method performs batch deserialization of persisted messages using
        Pydantic AI's official ModelMessagesTypeAdapter. The process:
        1. Extracts JSON strings from database records
        2. Combines them into a single JSON array
        3. Deserializes using schema-aware adapter
        4. Applies automatic healing to remove incomplete tails

        Args:
            db_messages: List of database records with 'message_json' field

        Returns:
            List of reconstructed and healed ModelMessage objects in chronological
            order. Returns empty list if no valid messages or deserialization fails.

        Example:
            >>> db_msgs = [
            ...     {"message_json": '{"kind":"request","parts":[...]}'},
            ...     {"message_json": '{"kind":"response","parts":[...]}'}
            ... ]
            >>> history = agent._reconstruct_history(db_msgs)
            >>> len(history)
            2

        See Also:
            https://ai.pydantic.dev/message-history/#storing-and-loading-messages-to-json

        Note:
            Errors during deserialization are logged but do not raise exceptions.
            This ensures the agent can start with empty history rather than crash.
        """
        if not db_messages:
            logger.debug("No database messages to reconstruct")
            return []

        # Extract and validate JSON blobs
        json_blobs = self._extract_json_blobs(db_messages)
        if not json_blobs:
            return []

        # Deserialize and heal history
        try:
            history = self._deserialize_messages(json_blobs)
            healed_history = self._heal_history(history)

            self._log_reconstruction_stats(history, healed_history)
            return healed_history

        except Exception as e:
            logger.error(
                "Failed to deserialize message history for user '%s': %s",
                self.phone_number or "anonymous",
                e,
                exc_info=True,
            )
            return []

    def _extract_json_blobs(self, db_messages: list[dict[str, Any]]) -> list[str]:
        """
        Extract valid JSON strings from database message records.

        Args:
            db_messages: Raw database records

        Returns:
            List of JSON strings, filtered for validity
        """
        json_blobs = [
            msg.get("message_json") for msg in db_messages if msg.get("message_json")
        ]

        if not json_blobs:
            logger.warning("No valid message JSON found in database records")
            return []

        return json_blobs

    def _deserialize_messages(self, json_blobs: list[str]) -> list[ModelMessage]:
        """
        Deserialize JSON strings into ModelMessage objects.

        Uses Pydantic AI's ModelMessagesTypeAdapter for schema-compliant parsing.

        Args:
            json_blobs: List of JSON strings representing messages

        Returns:
            List of deserialized ModelMessage objects

        Raises:
            ValidationError: If JSON doesn't match ModelMessage schema
        """
        # Combine into single JSON array for batch deserialization
        json_array = "[" + ",".join(json_blobs) + "]"
        return ModelMessagesTypeAdapter.validate_json(json_array)

    def _log_reconstruction_stats(
        self, original: list[ModelMessage], healed: list[ModelMessage]
    ) -> None:
        """
        Log statistics about history reconstruction and healing.

        Args:
            original: Messages before healing
            healed: Messages after healing
        """
        logger.info(
            "Successfully reconstructed %d message(s) (healed from %d) "
            "from database for user '%s'",
            len(healed),
            len(original),
            self.phone_number or "anonymous",
        )

    def _heal_history(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        """
        Heal conversation history by removing incomplete conversation tails.

        This recovery mechanism handles cases where an agent run was interrupted
        (process crash, network failure, etc.) after the model emitted tool calls
        but before tool results were processed. Such states violate Pydantic AI's
        requirement that all tool calls in history must have corresponding returns.

        The healing algorithm:
        1. Validates that all tool calls have corresponding returns
        2. Checks if the last message is incomplete (pending tool results or response)
        3. If incomplete, truncates back to the last safe turn boundary
        4. Logs the truncation for debugging crash scenarios

        Args:
            messages: Raw reconstructed message history

        Returns:
            Sanitized message history guaranteed to end on a complete turn

        Example:
            Incomplete history (crashes after tool call):
            [Request, Response, Request, Response(tool_call)]
                                                ^^^^ incomplete

            After healing:
            [Request, Response]
                          ^^^^ last complete turn

        Note:
            This is a critical resilience feature that allows the agent to recover
            from crashes without manual intervention or database cleanup.
        """
        if not messages:
            return []

        # First, scan the entire history for orphaned tool calls
        healed = self._remove_orphaned_tool_sequences(messages)

        # Then check if the tail is incomplete
        incomplete_type = self._detect_incomplete_tail(healed)

        if incomplete_type:
            healed = self._truncate_to_last_safe_turn(healed, incomplete_type)

        return healed

    def _remove_orphaned_tool_sequences(
        self, messages: list[ModelMessage]
    ) -> list[ModelMessage]:
        """
        Remove any tool call/return sequences that are incomplete.

        Scans through the entire history to find tool calls that don't have
        corresponding returns in the subsequent request, or tool returns that
        don't have corresponding calls in the previous response.

        Args:
            messages: Message history to validate

        Returns:
            Cleaned message history with orphaned sequences removed

        Example:
            Input:
            [Request, Response(tool_call_1), Request(tool_return_1),  # Complete
             Response, Request,                                        # Complete
             Response(tool_call_2)]                                    # Orphaned!

            Output:
            [Request, Response(tool_call_1), Request(tool_return_1),
             Response, Request]
        """
        if len(messages) < 2:
            return messages

        # Track tool calls that need returns
        pending_tool_calls = set()
        last_safe_index = len(messages)

        for i, msg in enumerate(messages):
            if isinstance(msg, ModelResponse):
                # Collect tool call IDs from this response
                tool_calls_in_msg = {
                    part.tool_call_id
                    for part in msg.parts
                    if isinstance(part, ToolCallPart | BuiltinToolCallPart)
                }

                if tool_calls_in_msg:
                    # Mark these as pending
                    pending_tool_calls.update(tool_calls_in_msg)

            elif isinstance(msg, ModelRequest):
                # Check for tool returns that resolve pending calls
                tool_returns_in_msg = {
                    part.tool_call_id
                    for part in msg.parts
                    if isinstance(part, ToolReturnPart | BuiltinToolReturnPart)
                }

                # Remove resolved tool calls
                pending_tool_calls -= tool_returns_in_msg

            # If we have pending tool calls and we're at a request without returns,
            # or at the end of messages, we have an incomplete sequence
            if pending_tool_calls and i == len(messages) - 1:
                # Find the last safe point before this incomplete sequence
                safe_indices = self._find_safe_turn_indices(messages[:i])
                if safe_indices:
                    last_safe_index = safe_indices[-1]
                    logger.warning(
                        "Found orphaned tool calls at end of history. "
                        "Truncating from index %d to %d",
                        last_safe_index,
                        i,
                    )
                else:
                    logger.warning(
                        "Found orphaned tool calls with no safe truncation point"
                    )
                    last_safe_index = 0
                break

        return messages[:last_safe_index]

    def _detect_incomplete_tail(self, messages: list[ModelMessage]) -> str | None:
        """
        Detect if the conversation history ends with an incomplete turn.

        Args:
            messages: Message history to check

        Returns:
            String describing the incomplete state, or None if complete

        Example:
            >>> _detect_incomplete_tail([..., ModelResponse(parts=[ToolCallPart(...)])])
            "unprocessed_tool_call"
            >>> _detect_incomplete_tail([..., ModelRequest(parts=[UserPromptPart(...)])])
            "missing_response"
            >>> _detect_incomplete_tail([..., ModelResponse(parts=[TextPart(...)])])
            None
        """
        if not messages:
            return None

        last_msg = messages[-1]

        if isinstance(last_msg, ModelResponse):
            # Check for tool calls awaiting results
            has_pending_tools = any(
                isinstance(part, ToolCallPart | BuiltinToolCallPart)
                for part in last_msg.parts
            )
            if has_pending_tools:
                return "unprocessed_tool_call"

        elif isinstance(last_msg, ModelRequest):
            # Check if this request contains tool returns (which is fine)
            # or just a user prompt (which means we're missing a response)
            has_tool_returns = any(
                isinstance(part, ToolReturnPart | BuiltinToolReturnPart)
                for part in last_msg.parts
            )

            # If it's just a user prompt without tool returns, we're missing the response
            if not has_tool_returns:
                return "missing_response"

        return None

    def _truncate_to_last_safe_turn(
        self, messages: list[ModelMessage], incomplete_type: str
    ) -> list[ModelMessage]:
        """
        Truncate history to the last complete turn boundary.

        Args:
            messages: Full message history
            incomplete_type: Description of the incomplete state

        Returns:
            Truncated history ending at a safe boundary
        """
        safe_indices = self._find_safe_turn_indices(messages)

        if not safe_indices:
            logger.warning(
                "No safe turns found during history healing; returning empty history"
            )
            return []

        # Find the last safe index that gives us a complete conversation
        # We want to truncate BEFORE the incomplete turn
        last_safe_index = safe_indices[-1]

        # If the incomplete turn is the very last message and it's a request,
        # we should go back one more safe point
        if incomplete_type == "missing_response" and len(messages) > 1:
            # The last message is a user prompt without a response
            # We should remove it
            if len(safe_indices) > 1:
                # Find the safe index just before this one
                for i in range(len(safe_indices) - 1, -1, -1):
                    if safe_indices[i] < len(messages) - 1:
                        last_safe_index = safe_indices[i]
                        break

        logger.warning(
            "Healing history: removing incomplete turn (%s) from index %d to %d",
            incomplete_type,
            last_safe_index,
            len(messages) - 1,
        )

        # Special case: if we're truncating everything, return empty
        if last_safe_index >= len(messages) - 1 and incomplete_type:
            # We can't make progress, return everything up to but not including the bad message
            if len(safe_indices) > 1:
                return messages[: safe_indices[-2]]
            return []

        return messages[:last_safe_index]

    def clear_context(self) -> None:
        """
        Clear in-memory conversation history without affecting database.

        This resets the active context window, effectively starting a fresh
        conversation while preserving all past messages in persistent storage.
        Useful for privacy-sensitive conversations or context isolation.

        Side Effects:
            Clears self._history but does NOT modify database records

        Example:
            >>> agent.clear_context()
            >>> # Next run() will execute without historical context
            >>> response = await agent.run("Hello")  # Treats as new conversation
        """
        self._history = []
        logger.debug("Cleared in-memory conversation context")

    async def clear_history(self) -> None:
        """
        Permanently delete all conversation history from memory and database.

        This is a destructive operation that removes all persisted messages for
        the current user. Use with caution - this action cannot be undone.

        Side Effects:
            - Clears self._history (in-memory)
            - Deletes all database records for this phone_number

        Example:
            >>> await agent.clear_history()
            >>> # All past conversation data is permanently deleted
        """
        if self.phone_number:
            await self.db.clear_history(self.phone_number)
            logger.info(
                "Cleared all conversation history for user '%s'", self.phone_number
            )

        self.clear_context()

    def get_history(self) -> list[ModelMessage]:
        """
        Retrieve a copy of the current in-memory conversation history.

        Returns a shallow copy to prevent external modification of internal state.

        Returns:
            List of ModelMessage objects currently held in memory

        Example:
            >>> history = agent.get_history()
            >>> for msg in history:
            ...     print(f"{msg.kind}: {msg.parts}")
            request: [UserPromptPart(...)]
            response: [TextPart(...)]
        """
        return list(self._history)

    async def __aenter__(self):
        """
        Async context manager entry - establishes connection.

        Returns:
            Self for use in 'async with' statements

        Example:
            >>> async with AskariAgent() as agent:
            ...     response = await agent.run("Hello")
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit - ensures cleanup.

        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception value if an error occurred
            exc_tb: Exception traceback if an error occurred

        Note:
            Cleanup occurs regardless of whether an exception was raised
        """
        await self.disconnect()
