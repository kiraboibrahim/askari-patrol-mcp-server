"""
Askari Patrol Agent with simple history management
"""

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

from .prompts import CLI_SYSTEM_PROMPT


class AskariAgent:
    """
    Reusable agent for Askari Patrol using Pydantic AI with Groq.
    """

    DEFAULT_INSTRUCTIONS = CLI_SYSTEM_PROMPT

    def __init__(
        self,
        server_url: str = "http://localhost:8000/mcp",
        instructions: str = CLI_SYSTEM_PROMPT,
        model: str = "groq:openai/gpt-oss-20b",
    ):
        self.server_url = server_url
        self.instructions = instructions
        self.model = model

        self._server: MCPServerStreamableHTTP | None = None
        self._agent: Agent | None = None
        self._conversation_context: list[dict] = []  # Simple text-only context

    async def connect(self):
        """Connect to the MCP server."""
        self._server = MCPServerStreamableHTTP(self.server_url)

        await self._server.__aenter__()

        self._agent = Agent(
            self.model,
            system_prompt=self.instructions,
            toolsets=[self._server],
        )

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self._server:
            await self._server.__aexit__(None, None, None)
            self._server = None
            self._agent = None

    def _build_context_prompt(self, message: str) -> str:
        """
        Build a message that includes conversation context.

        Args:
            message: Current user message

        Returns:
            Message with context prepended
        """
        if not self._conversation_context:
            return message

        # Build context from last few exchanges
        context_parts = []
        for exchange in self._conversation_context[-3:]:  # Last 3 exchanges
            context_parts.append(f"User: {exchange['user']}")
            context_parts.append(f"Assistant: {exchange['assistant']}")

        context_str = "\n".join(context_parts)

        return f"""Previous conversation:
{context_str}

Current question: {message}"""

    async def run(self, message: str, use_context: bool = True) -> str:
        """
        Process a natural language message.

        Args:
            message: User's message
            use_context: Whether to include previous conversation context

        Returns:
            Agent's response
        """
        if not self._agent:
            raise RuntimeError("Agent not connected. Call connect() first.")

        # Build message with context if requested
        if use_context and self._conversation_context:
            enhanced_message = self._build_context_prompt(message)
        else:
            enhanced_message = message

        # Run WITHOUT message_history to avoid tool serialization issues
        result = await self._agent.run(enhanced_message)

        # Store simple text context
        self._conversation_context.append({"user": message, "assistant": result.output})

        # Keep only last 5 exchanges
        if len(self._conversation_context) > 5:
            self._conversation_context = self._conversation_context[-5:]

        return result.output

    def clear_context(self):
        """Clear the conversation context."""
        self._conversation_context = []

    def get_context(self) -> list[dict]:
        """Get the current conversation context."""
        return self._conversation_context.copy()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
