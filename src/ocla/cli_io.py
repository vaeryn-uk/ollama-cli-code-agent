from __future__ import annotations

from rich.console import Console
from rich.text import Text

console = Console()

def agent_output(text: str, thinking: bool, con=None, **kwargs) -> None:
    (con or console).print(Text(text, style="italic yellow" if thinking else "magenta"), **kwargs)


def user_prompt(text: str, con=None, **kwargs) -> None:
    (con or console).print(Text(text, style="bold"), **kwargs)


def info(text: str, con=None, **kwargs) -> None:
    (con or console).print(Text(text, style="cyan"), **kwargs)


def error(text: str, con=None, **kwargs) -> None:
    (con or console).print(Text(text, style="red"), **kwargs)
