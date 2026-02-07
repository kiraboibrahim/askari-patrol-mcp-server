"""
Askari Patrol Agent - Interactive Command-Line Chat Interface

This script provides a rich, interactive terminal-based chat interface for communicating
with the Askari Patrol Agent via MCP (Model Context Protocol).

Features:
    - Rich formatted output with syntax highlighting
    - Command history and auto-suggestions
    - Interactive REPL with helpful commands
    - Markdown rendering for agent responses
    - Test query mode for quick validation

Usage:
    # Using make
    make chat

    # Direct execution
    PYTHONPATH=src python scripts/chat.py

    # Custom server URL
    MCP_SERVER_URL=http://custom-host:8000/mcp python scripts/chat.py

Environment Variables:
    MCP_SERVER_URL : URL of the MCP server (default: http://localhost:8000/mcp)

Interactive Commands:
    exit/quit/q : Exit the chat
    clear       : Clear the screen
    help        : Show help message

Requirements:
    - prompt_toolkit: For interactive prompts and history
    - rich: For beautiful terminal output
    - askari_patrol_client: The agent client library

Author: Askari Development Team
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging before any other imports
from common.logging_config import setup_logging  # noqa: E402

setup_logging()

from askari_patrol_client.agent import AskariAgent  # noqa: E402
from prompt_toolkit import PromptSession  # noqa: E402
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory  # noqa: E402
from prompt_toolkit.history import FileHistory  # noqa: E402
from prompt_toolkit.styles import Style  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.markdown import Markdown  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402

# Initialize Rich console for beautiful terminal output
console = Console()

# Prompt toolkit style configuration
prompt_style = Style.from_dict(
    {
        "prompt": "#00aa00 bold",
    }
)

# Configuration constants
HISTORY_FILE = Path.home() / ".askari_chat_history"
DEFAULT_SERVER_URL = "http://localhost:8000/mcp"
MARKDOWN_MARKERS = ["#", "*", "-", "`", "|"]


def create_header() -> Panel:
    """
    Create a stylish ASCII header for the application.

    Returns:
        Panel: A Rich Panel containing the formatted header with title and subtitle

    Example:
        >>> header = create_header()
        >>> console.print(header)
        ╭────────────────────────────────╮
        │  🛡️  ASKARI PATROL AGENT       │
        │  MCP Chat Interface            │
        ╰────────────────────────────────╯
    """
    table = Table.grid(padding=1)
    table.add_column(justify="center")

    title = Text("🛡️  ASKARI PATROL AGENT", style="bold cyan")
    subtitle = Text("MCP Chat Interface", style="dim")

    table.add_row(title)
    table.add_row(subtitle)

    return Panel(table, border_style="cyan", padding=(1, 2))


def format_user_message(message: str) -> Panel:
    """
    Format a user message in a styled panel.

    Args:
        message (str): The user's input message

    Returns:
        Panel: A Rich Panel with blue border and user icon

    Example:
        >>> panel = format_user_message("Hello, agent!")
        >>> console.print(panel)
    """
    return Panel(
        message,
        title="[bold blue]👤 You[/bold blue]",
        title_align="left",
        border_style="blue",
        padding=(0, 2),
    )


def format_agent_message(message: str) -> Panel:
    """
    Format an agent response with markdown rendering if applicable.

    Automatically detects markdown formatting in the message and renders it
    appropriately. Falls back to plain text for simple messages.

    Args:
        message (str): The agent's response message

    Returns:
        Panel: A Rich Panel with green border and agent icon, containing
               either rendered Markdown or plain Text

    Example:
        >>> response = "# Summary\n- Item 1\n- Item 2"
        >>> panel = format_agent_message(response)
        >>> console.print(panel)
    """
    # Try to render as markdown if it looks like formatted text
    if any(marker in message for marker in MARKDOWN_MARKERS):
        content = Markdown(message)
    else:
        content = Text(message)

    return Panel(
        content,
        title="[bold green]🤖 Agent[/bold green]",
        title_align="left",
        border_style="green",
        padding=(0, 2),
    )


def format_error(error: str) -> Panel:
    """
    Format an error message in a red-bordered panel.

    Args:
        error (str): The error message to display

    Returns:
        Panel: A Rich Panel with red styling and error icon

    Example:
        >>> panel = format_error("Connection failed")
        >>> console.print(panel)
    """
    return Panel(
        f"[red]{error}[/red]",
        title="[bold red]❌ Error[/bold red]",
        title_align="left",
        border_style="red",
        padding=(0, 2),
    )


def create_info_panel() -> Panel:
    """
    Create an informational panel with available commands.

    Returns:
        Panel: A Rich Panel containing command documentation

    Example:
        >>> panel = create_info_panel()
        >>> console.print(panel)
    """
    return Panel(
        "[yellow]Interactive mode enabled[/yellow]\n"
        "Commands:\n"
        "  • [cyan]exit/quit/q[/cyan] - Exit the chat\n"
        "  • [cyan]clear[/cyan] - Clear the screen\n"
        "  • [cyan]help[/cyan] - Show this help message",
        title="[bold]ℹ️  Info[/bold]",
        border_style="yellow",
    )


def create_help_panel() -> Panel:
    """
    Create a detailed help panel with all available commands.

    Returns:
        Panel: A Rich Panel containing comprehensive help text

    Example:
        >>> panel = create_help_panel()
        >>> console.print(panel)
    """
    return Panel(
        "Available commands:\n"
        "  • [cyan]exit/quit/q[/cyan] - Exit the chat\n"
        "  • [cyan]clear[/cyan] - Clear the screen\n"
        "  • [cyan]help[/cyan] - Show this help message\n\n"
        "Just type your question to chat with the agent!",
        title="[bold]ℹ️  Help[/bold]",
        border_style="yellow",
    )


async def execute_query(agent: AskariAgent, query: str) -> None:
    """
    Execute a single query against the agent and display the response.

    Handles the complete query lifecycle including status display, error
    handling, and formatted output.

    Args:
        agent (AskariAgent): The agent instance to query
        query (str): The user's query text

    Side Effects:
        Prints formatted output to console

    Example:
        >>> await execute_query(agent, "What can you help with?")
        🤔 Agent thinking...
        🤖 Agent: I can help you with...
    """
    try:
        with console.status("[bold green]🤔 Agent thinking...", spinner="dots"):
            response = await agent.run(query)
        console.print(format_agent_message(response))
    except Exception as e:
        console.print(format_error(str(e)))


async def run_test_queries(agent: AskariAgent) -> None:
    """
    Run a predefined set of test queries to validate agent functionality.

    Useful for quick smoke testing and demonstrating agent capabilities.

    Args:
        agent (AskariAgent): The agent instance to test

    Side Effects:
        Prints test results to console

    Example:
        >>> await run_test_queries(agent)
        Running Test Queries...
        👤 You: What can you help me with?
        🤖 Agent: I can assist with...
    """
    test_queries: list[str] = [
        "What can you help me with?",
    ]

    console.print("\n[bold cyan]Running Test Queries...[/bold cyan]\n")

    for query in test_queries:
        console.print(format_user_message(query))
        await execute_query(agent, query)
        console.print()  # Add spacing


async def handle_command(command: str) -> bool:
    """
    Process special commands in interactive mode.

    Args:
        command (str): The command to process (should be lowercase)

    Returns:
        bool: True if the session should continue, False if it should exit

    Side Effects:
        May clear screen or print help information

    Example:
        >>> should_continue = await handle_command("clear")
        >>> # Screen is cleared
        >>> should_continue = await handle_command("exit")
        >>> # Returns False to exit loop
    """
    if command in ["exit", "quit", "q"]:
        console.print("\n[yellow]👋 Goodbye![/yellow]\n")
        return False

    if command == "clear":
        console.clear()
        console.print(create_header())
        return True

    if command == "help":
        console.print(create_help_panel())
        return True

    return True


async def get_user_input(session: PromptSession) -> str:
    """
    Get user input asynchronously with history and auto-suggest.

    Args:
        session (PromptSession): The prompt_toolkit session with history

    Returns:
        str: The user's input, stripped of whitespace

    Example:
        >>> session = PromptSession()
        >>> user_input = await get_user_input(session)
        👤 You: _
    """
    return await asyncio.to_thread(
        session.prompt,
        [("class:prompt", "👤 You: ")],
    )


async def interactive_mode(agent: AskariAgent) -> None:
    """
    Run the main interactive chat REPL (Read-Eval-Print Loop).

    Provides a persistent chat session with command history, auto-suggestions,
    and special command support. Continues until the user exits or interrupts.

    Args:
        agent (AskariAgent): The agent instance to chat with

    Side Effects:
        - Creates/updates chat history file at ~/.askari_chat_history
        - Prints all interaction output to console

    Example:
        >>> agent = AskariAgent(server_url="http://localhost:8000/mcp")
        >>> await interactive_mode(agent)
        👤 You: hello
        🤖 Agent: Hello! How can I help you?
        👤 You: exit
        👋 Goodbye!
    """
    # Setup prompt session with history and auto-suggestions
    session = PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        auto_suggest=AutoSuggestFromHistory(),
        style=prompt_style,
    )

    console.print("\n")
    console.print(create_info_panel())
    console.print()

    while True:
        try:
            # Get user input
            user_input = await get_user_input(session)
            user_input = user_input.strip()

            # Skip empty input
            if not user_input:
                continue

            # Handle special commands
            command = user_input.lower()
            if command in ["exit", "quit", "q", "clear", "help"]:
                should_continue = await handle_command(command)
                if not should_continue:
                    break
                continue

            # Execute user query
            await execute_query(agent, user_input)
            console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Goodbye![/yellow]\n")
            break
        except EOFError:
            console.print("\n[yellow]👋 Goodbye![/yellow]\n")
            break
        except Exception as e:
            console.print(format_error(str(e)))
            console.print()


async def initialize_agent(server_url: str) -> AskariAgent:
    """
    Initialize and connect to the Askari Agent.

    Args:
        server_url (str): The MCP server URL to connect to

    Returns:
        AskariAgent: A connected agent instance

    Raises:
        Exception: If connection to the server fails

    Example:
        >>> agent = await initialize_agent("http://localhost:8000/mcp")
        ✅ Agent connected successfully!
    """
    console.print("[cyan]⏳ Connecting to MCP server...[/cyan]")

    agent = AskariAgent(server_url=server_url, phone_number="CLI_USER")
    await agent.__aenter__()

    console.print("[green]✅ Agent connected successfully![/green]")
    console.print(f"[dim]Server: {server_url}[/dim]\n")

    return agent


async def chat(server_url: str = DEFAULT_SERVER_URL) -> None:
    """
    Main entry point for the chat interface.

    Sets up the UI, connects to the agent, runs test queries, and starts
    the interactive chat session.

    Args:
        server_url (str): The MCP server URL to connect to.
                         Defaults to http://localhost:8000/mcp

    Side Effects:
        - Clears the terminal screen
        - Establishes connection to MCP server
        - Runs interactive chat session

    Example:
        >>> await chat("http://localhost:8000/mcp")
        # Interactive chat session starts
    """
    # Clear screen and show header
    console.clear()
    console.print(create_header())
    console.print()

    try:
        # Initialize and connect agent
        agent = await initialize_agent(server_url)

        try:
            # Run test queries
            await run_test_queries(agent)

            # Start interactive mode
            await interactive_mode(agent)
        finally:
            # Ensure cleanup even if interrupted
            await agent.__aexit__(None, None, None)

    except Exception as e:
        console.print(format_error(f"Failed to connect: {e}"))
        return


if __name__ == "__main__":
    # Get server URL from environment or use default
    server_url = os.environ.get("MCP_SERVER_URL", DEFAULT_SERVER_URL)

    try:
        asyncio.run(chat(server_url=server_url))
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Interrupted. Goodbye![/yellow]\n")
