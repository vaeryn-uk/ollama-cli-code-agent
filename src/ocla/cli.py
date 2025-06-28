import argparse
import json
import subprocess

from ocla.state import load_state
from ocla.session import (
    Session,
    list_sessions,
    set_current_session_name,
    get_current_session_name,
    generate_session_name,
)
from ocla.tools import ls
import ollama
import sys
from typing import List, Dict, Callable, Any

TOOLS: Dict[str, Callable[..., Any]] = {
    "ls": ls,
    # "other": other_fn,
}

DEFAULT_MODEL = "qwen2.5"

def execute_tool(call: ollama.Message.ToolCall) -> str:
    fn = TOOLS.get(call.function.name)
    if fn is None:
        raise KeyError(f"Unknown tool: {call.function.name}")
    result = fn(**(call.function.arguments or {}))
    return str(result)

def _confirm_tool(call: ollama.Message.ToolCall) -> bool:
    """
    Ask the user whether to run this tool call.
    Returns True only if the reply begins with 'y' or 'Y'.
    Defaults to False if stdin is not a TTY (e.g. piped input).
    """
    if not sys.stdin.isatty():
        print(f"not a tty so skipping tool call {call.function.name} as no permission can be attained")
        return False                                 # non-interactive → skip

    fn       = call.function.name
    raw_args = call.function.arguments
    try:
        if isinstance(raw_args, (dict, list)):
            args = json.dumps(raw_args, separators=(",", ":"))
        else:
            args = str(raw_args)
    except TypeError:
        args = str(raw_args)

    reply = input(f"Run tool '{fn}'? Arguments: {args} [y/N] ").strip().lower()
    return reply.startswith("y")

def chat_with_tools(model: str, session: Session, prompt: str) -> str:
    session.add({"role": "user", "content": prompt})
    response = ollama.chat(model=load_state().default_model or default_model, messages=session.messages, tools=list(TOOLS.values()))
    message = response.get("message", {})
    session.add(message)

    if "tool_calls" in message:
        for call in message["tool_calls"]:
            if _confirm_tool(call):  # ← check with user
                output = execute_tool(call)
                session.add(
                    {
                        "role": "tool",
                        "content": output,
                        "name": call.function.name,
                    }
                )
            else:
                session.add(
                    {
                        "role": "tool",
                        "content": "skipped tool execution because the user did not allow it",
                        "name": call.function.name,
                    }
                )
        response = ollama.chat(model=model, messages=session.messages)
        message = response.get("message", {})
        session.add(message)

    session.save()
    return message.get("content", "")

def read_prompt_from_stdin() -> str:
    if sys.stdin.isatty():          # launched interactively with no pipe
        return input("prompt> ")    # one-liner; could also loop for multi-turn
    return sys.stdin.read()         # piped or redirected data


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Interact with a local Ollama model",
    )
    parser.add_argument("-m", "--model", default="codellama", help="Model name")
    parser.add_argument("--session", help="Override session name")
    parser.add_argument("--reset", action="store_true", help="Reset the session history")

    subparsers = parser.add_subparsers(dest="command")

    session_parser = subparsers.add_parser("session", help="Manage sessions")
    session_sub = session_parser.add_subparsers(dest="session_cmd")
    session_new = session_sub.add_parser("new", help="Create a new session")
    session_new.add_argument("name", nargs="?")
    session_sub.add_parser("list", help="List available sessions")
    session_set = session_sub.add_parser("set", help="Set current session")
    session_set.add_argument("name")

    # parse args but allow extra positional arguments as the prompt
    args, prompt_parts = parser.parse_known_args(argv)

    if args.command == "session":
        if args.session_cmd == "new":
            name = args.name or generate_session_name()
            Session(name).save()
            set_current_session_name(name)
            print(name)
        elif args.session_cmd == "list":
            for s in list_sessions():
                if get_current_session_name() == s:
                    print(f"> {s}")
                else:
                    print(f"  {s}")
        elif args.session_cmd == "set":
            if args.name not in list_sessions():
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
    session = Session(session_name)
    if get_current_session_name() is None:
        set_current_session_name(session_name)
    if args.reset:
        session.messages = []

    output = chat_with_tools(args.model, session, msg)
    print(output)


if __name__ == "__main__":
    main()
