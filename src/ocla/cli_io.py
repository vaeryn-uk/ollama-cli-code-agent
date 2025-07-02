from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.text import Text
import sys
import os

console = Console()

_TTY_WIN = "CONIN$"  # Windows console device
_TTY_NIX = "/dev/tty"  # POSIX console device


def agent_output(text: str, thinking: bool, con=None, **kwargs) -> None:
    (con or console).print(
        Text(text, style="italic yellow" if thinking else "magenta"), **kwargs
    )


def user_prompt(text: str, con=None, **kwargs) -> None:
    (con or console).print(Text(text, style="bold"), **kwargs)


def info(text: str, con=None, **kwargs) -> None:
    (con or console).print(Text(text, style="cyan"), **kwargs)


def error(text: str, con=None, **kwargs) -> None:
    (con or console).print(Text("ERROR: " + text, style="red"), **kwargs)


def interactive_prompt(prompt: str) -> Optional[str]:
    # 1. Fast path – stdin is already a TTY
    if sys.stdin.isatty():
        return console.input(prompt)

    # 2. Try to open the controlling terminal directly
    tty_name = _TTY_WIN if os.name == "nt" else _TTY_NIX
    try:
        with open(tty_name, "r") as tty_in, open(tty_name, "w") as tty_out:
            fd_console = Console(file=tty_out, force_terminal=True)

            fd_console.print(prompt, end="")  # emits ANSI codes, not markup
            fd_console.file.flush()  # make sure it appears immediately

            reply = tty_in.readline().rstrip("\n")
        return reply
    except OSError:
        # No terminal (cron, CI, docker without TTY, etc.)
        return None
