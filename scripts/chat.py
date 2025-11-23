"""
Commandline Client for Askari Agent.

Usage:
    make chat
    # or
    PYTHONPATH=src python scripts/chat.py
"""

import asyncio
from pathlib import Path

from askari_patrol_client.agent import AskariAgent
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Initialize Rich console
console = Console()

# Prompt toolkit style
prompt_style = Style.from_dict(
    {
        "prompt": "#00aa00 bold",
    }
)


def create_header():
    """Create a stylish header."""
    table = Table.grid(padding=1)
    table.add_column(justify="center")

    title = Text("🛡️  ASKARI PATROL AGENT", style="bold cyan")
    subtitle = Text("MCP Chat Interface", style="dim")

    table.add_row(title)
    table.add_row(subtitle)

    return Panel(table, border_style="cyan", padding=(1, 2))


def format_user_message(message: str) -> Panel:
    """Format user message."""
    return Panel(
        message,
        title="[bold blue]👤 You[/bold blue]",
        title_align="left",
        border_style="blue",
        padding=(0, 2),
    )


def format_agent_message(message: str) -> Panel:
    """Format agent response."""
    # Try to render as markdown if it looks like formatted text
    if any(marker in message for marker in ["#", "*", "-", "`", "|"]):
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
    """Format error message."""
    return Panel(
        f"[red]{error}[/red]",
        title="[bold red]❌ Error[/bold red]",
        title_align="left",
        border_style="red",
        padding=(0, 2),
    )


async def run_test_queries(agent: AskariAgent):
    """Run predefined test queries."""
    test_queries = [
        "What can you help me with?",
    ]

    console.print("\n[bold cyan]Running Test Queries...[/bold cyan]\n")

    for query in test_queries:
        console.print(format_user_message(query))

        try:
            with console.status("[bold green]🤔 Agent thinking...", spinner="dots"):
                response = await agent.run(query)
            console.print(format_agent_message(response))
        except Exception as e:
            console.print(format_error(str(e)))

        console.print()  # Add spacing


async def interactive_mode(agent: AskariAgent):
    """Run interactive chat mode."""
    # Setup prompt session with history
    history_file = Path.home() / ".askari_chat_history"
    session = PromptSession(
        history=FileHistory(str(history_file)),
        auto_suggest=AutoSuggestFromHistory(),
        style=prompt_style,
    )

    console.print("\n")
    console.print(
        Panel(
            "[yellow]Interactive mode enabled[/yellow]\n"
            "Commands:\n"
            "  • [cyan]exit/quit/q[/cyan] - Exit the chat\n"
            "  • [cyan]clear[/cyan] - Clear the screen\n"
            "  • [cyan]help[/cyan] - Show this help message",
            title="[bold]ℹ️  Info[/bold]",
            border_style="yellow",
        )
    )
    console.print()

    while True:
        try:
            # Get user input with nice prompt (run in thread to avoid blocking)
            user_input = await asyncio.to_thread(
                session.prompt,
                [("class:prompt", "👤 You: ")],
            )
            user_input = user_input.strip()

            # Handle commands
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("\n[yellow]👋 Goodbye![/yellow]\n")
                break

            if user_input.lower() == "clear":
                console.clear()
                console.print(create_header())
                continue

            if user_input.lower() == "help":
                console.print(
                    Panel(
                        "Available commands:\n"
                        "  • [cyan]exit/quit/q[/cyan] - Exit the chat\n"
                        "  • [cyan]clear[/cyan] - Clear the screen\n"
                        "  • [cyan]help[/cyan] - Show this help message\n\n"
                        "Just type your question to chat with the agent!",
                        title="[bold]ℹ️  Help[/bold]",
                        border_style="yellow",
                    )
                )
                continue

            if not user_input:
                continue

            # Show spinner while waiting for response
            try:
                with console.status("[bold green]🤔 Agent thinking...", spinner="dots"):
                    response = await agent.run(user_input)
                console.print(format_agent_message(response))
            except Exception as e:
                console.print(format_error(str(e)))

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


async def chat(server_url: str = "http://localhost:8000/mcp"):
    """Chat with Agent."""

    # Clear screen and show header
    console.clear()
    console.print(create_header())
    console.print()

    try:
        # Show connection message
        console.print("[cyan]⏳ Connecting to MCP server...[/cyan]")

        agent = AskariAgent(server_url=server_url)
        await agent.__aenter__()

        # Clear the connecting message and show success
        console.print("[green]✅ Agent connected successfully![/green]")
        console.print(f"[dim]Server: {server_url}[/dim]\n")

        try:
            # Run test queries
            await run_test_queries(agent)

            # Start interactive mode
            await interactive_mode(agent)
        finally:
            await agent.__aexit__(None, None, None)

    except Exception as e:
        console.print(format_error(f"Failed to connect: {e}"))
        return


if __name__ == "__main__":
    import os

    server_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp")

    try:
        asyncio.run(chat(server_url=server_url))
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Interrupted. Goodbye![/yellow]\n")
