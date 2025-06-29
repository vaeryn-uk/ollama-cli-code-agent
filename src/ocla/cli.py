import argparse
import json
import os
import subprocess
import humanize
from datetime import datetime

from ollama import Message
from tzlocal import get_localzone

from rich.console import Console
from rich.table import Table
from ocla.state import load_state
from ocla.session import (
    Session,
    list_sessions,
    set_current_session_name,
    get_current_session_name,
    generate_session_name,
    session_exists,
)
from ocla.tools import ALL
import ollama
import sys

DEFAULT_MODEL = "qwen3"

_TTY_WIN = "CONIN$"   # Windows console device
_TTY_NIX = "/dev/tty" # POSIX console device

console = Console()

def execute_tool(call: ollama.Message.ToolCall) -> str:
    entry = ALL.get(call.function.name)
    if entry is None:
        raise KeyError(f"Unknown tool: {call.function.name}")
    result = entry.fn(**(call.function.arguments or {}))
    return str(result)


def _confirm_tool(call: ollama.Message.ToolCall) -> bool:
    """
    Ask the user whether to run this tool call.
    """
    fn = call.function.name
    raw_args = call.function.arguments
    try:
        if isinstance(raw_args, (dict, list)):
            args = json.dumps(raw_args, separators=(",", ":"))
        else:
            args = str(raw_args)
    except TypeError:
        args = str(raw_args)

    prompt = f"Run tool '{fn}'? Arguments: {args} [y/N] "

    # 1. Fast path – stdin is already a TTY
    if sys.stdin.isatty():
        reply = input(prompt)
        return reply.strip().lower().startswith("y")

    # 2. Try to open the controlling terminal directly
    tty_name = _TTY_WIN if os.name == "nt" else _TTY_NIX
    try:
        with open(tty_name, "r") as tty_in, open(tty_name, "w") as tty_out:
            tty_out.write(prompt)
            tty_out.flush()
            reply = tty_in.readline()
        return reply.strip().lower().startswith("y")
    except OSError:
        # No terminal (cron, CI, docker without TTY, etc.)
        return False


def _chat_stream(**kwargs) -> tuple[str, Message]:
    content_parts: list[str] = []
    tool_calls: list[ollama.Message.ToolCall] = []          # gather all tool calls
    last_role: str | None = None         # keep whatever role we see last

    for chunk in ollama.chat(stream=True, **kwargs):
        msg = chunk.get("message", {})
        last_role = msg.get("role", last_role)

        part = msg.get("content") or ""
        if part:
            print(part, end="", flush=True)
            content_parts.append(part)

        if "tool_calls" in msg:
            tool_calls.extend(msg["tool_calls"])

    print()  # newline after streaming output

    full_content = "".join(content_parts)

    # Build a consolidated assistant message
    assistant_msg = Message(
        role=last_role or "assistant",
        content=full_content,
        tool_calls=tool_calls,
    )

    return full_content, assistant_msg


def do_chat(session: Session, prompt: str) -> str:
    session.add({"role": "user", "content": prompt})
    model = load_state().default_model or DEFAULT_MODEL

    accumulated_text: list[str] = []

    while True:
        # --- 1️⃣  ask the model ------------------------------------------
        content, msg = _chat_stream(
            model=model,
            messages=session.messages,
            tools=[t.fn for t in ALL.values()],
        )
        session.add(msg)
        if content:
            accumulated_text.append(content)

        # --- 2️⃣  check for tool-calls ----------------------------------
        calls = msg.get("tool_calls", [])
        if not calls:
            break  # assistant is done, exit loop

        # execute each call, append tool results, then loop again
        for call in calls:
            if _confirm_tool(call):
                tool_output = execute_tool(call)
            else:
                tool_output = "skipped tool execution because the user did not allow it"

            session.add(
                {
                    "role": "tool",
                    "name": call.function.name,
                    "content": tool_output,
                }
            )

    session.save()
    return "".join(accumulated_text)


def read_prompt_from_stdin() -> str:
    if sys.stdin.isatty():  # launched interactively with no pipe
        return input("prompt> ")  # one-liner; could also loop for multi-turn
    return sys.stdin.read()  # piped or redirected data


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Interact with a local Ollama model",
    )
    parser.add_argument("--session", help="Run in a session for this command only")
    parser.add_argument(
        "--new-session",
        help="Generate a new session and run in it. This will be made the active session for future commands",
        action="store_true"
    )

    subparsers = parser.add_subparsers(dest="command")

    session_parser = subparsers.add_parser("session", help="Manage sessions")
    session_sub = session_parser.add_subparsers(dest="session_cmd")
    session_new = session_sub.add_parser("new", help="Create a new session")
    session_new.add_argument("name", nargs="?")
    session_sub.add_parser("list", help="List available sessions")
    session_set = session_sub.add_parser("set", help="Set current session")
    session_set.add_argument("name")

    args, prompt_parts = parser.parse_known_args(argv)

    if args.new_session and args.session:
        parser.error("Cannot specify both --new-session and --session.")

    if args.command == "session":
        if args.session_cmd == "new":
            name = args.name or generate_session_name()
            Session(name).save()
            set_current_session_name(name)
            print(name)
        elif args.session_cmd == "list":

            table = Table(show_header=True, header_style="bold")

            table.add_column("Session")
            table.add_column("Created")
            table.add_column("Last Used")
            for s in list_sessions():
                table.add_row(
                    *(
                        (
                            f"> {s.name}"
                            if get_current_session_name() == s.name
                            else f"  {s.name}"
                        ),
                        humanize.naturaltime(datetime.now(get_localzone()) - s.created),
                        humanize.naturaltime(datetime.now(get_localzone()) - s.used),
                    )
                )

            console.print(table)
        elif args.session_cmd == "set":
            if not session_exists(args.name):
                parser.error(f"Unknown session: {args.name}")
            set_current_session_name(args.name)
        else:
            session_parser.print_help()
        return

    # Treat remaining arguments as the prompt
    msg = " ".join(prompt_parts).strip() or read_prompt_from_stdin().strip()
    if not msg:
        parser.error("No prompt supplied via arguments or stdin.")

    session_name = args.session or get_current_session_name() or generate_session_name()
    if args.new_session:
        session_name = generate_session_name()

    session = Session(session_name)
    if get_current_session_name() is None:
        set_current_session_name(session_name)

    do_chat(session, msg)


if __name__ == "__main__":
    main()

