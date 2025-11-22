from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp

from .prompts import SYSTEM_INSTRUCTIONS as DEFAULT_INSTRUCTIONS


class AskariAgent:
    """
    Reusable agent for Askari Patrol.

    Connects to the MCP server and processes natural language queries.
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8000/mcp",
        instructions: str = DEFAULT_INSTRUCTIONS,
        model: str = "gpt-4o",
    ):
        self.server_url = server_url
        self.instructions = instructions
        self.model = model

        self._server: MCPServerStreamableHttp | None = None
        self._agent: Agent | None = None

    async def connect(self):
        """Connect to the MCP server."""
        self._server = MCPServerStreamableHttp(
            name="Askari Patrol",
            params={"url": self.server_url, "timeout": 30},
            cache_tools_list=True,
        )
        await self._server.__aenter__()

        self._agent = Agent(
            name="Askari Assistant",
            instructions=self.instructions,
            mcp_servers=[self._server],
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

        result = await Runner.run(self._agent, message)
        return result.final_output

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
