"""
Askari Patrol Agent

A reusable agent layer for the Askari Patrol MCP server using Pydantic AI with Groq.

Usage:
    async with AskariAgent() as agent:
        response = await agent.run("Show me all sites")
        print(response)
"""

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

from .prompts import SYSTEM_INSTRUCTIONS


class AskariAgent:
    """
    Reusable agent for Askari Patrol using Pydantic AI with Groq.

    Connects to the MCP server and processes natural language queries.
    """

    DEFAULT_INSTRUCTIONS = SYSTEM_INSTRUCTIONS

    def __init__(
        self,
        server_url: str = "http://localhost:8000/mcp",
        instructions: str = SYSTEM_INSTRUCTIONS,
        model: str = "groq:openai/gpt-oss-120b",
    ):
        self.server_url = server_url
        self.instructions = instructions
        self.model = model

        self._server: MCPServerStreamableHTTP | None = None
        self._agent: Agent | None = None

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

    async def run(self, message: str) -> str:
        """
        Process a natural language message.

        Args:
            message: User's message

        Returns:
            Agent's response
        """
        if not self._agent:
            raise RuntimeError("Agent not connected. Call connect() first.")

        result = await self._agent.run(message)
        return result.output

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
