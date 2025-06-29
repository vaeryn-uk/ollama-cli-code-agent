from __future__ import annotations

from rich.console import Console
from rich.text import Text

_console = Console()


def agent_thinking(text: str) -> None:
    """Show that the agent is thinking or working."""
    _console.print(Text(text, style="italic yellow"))


def agent_output(text: str) -> None:
    """Display output from the agent."""
    _console.print(Text(text, style="green"))


def user_prompt(text: str) -> None:
    """Display the user's input."""
    _console.print(Text(text, style="bold"))


def info(text: str) -> None:
    """Display generic tool output."""
    _console.print(Text(text, style="cyan"))
