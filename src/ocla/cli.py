import argparse
from curses.ascii import isdigit

import humanize
from datetime import datetime

from ollama import Message, Client
from tzlocal import get_localzone

from rich.table import Table

import logging
import logging.config

from ocla.util import format_tool_arguments
from ocla.cli_io import info, console, agent_output, error, interactive_prompt
from ocla.config import (
    CONTEXT_WINDOW,
    MODEL,
    LOG_LEVEL,
    CONFIG_VARS,
    TOOL_PERMISSION_MODE,
    DISPLAY_THINKING,
    TOOL_PERMISSION_MODE_DEFAULT,
    TOOL_PERMISSION_MODE_ALWAYS_ALLOW,
)
from ocla.session import (
    Session,
    list_sessions,
    set_current_session_name,
    get_current_session_name,
    generate_session_name,
    session_exists, ContextWindowExceededError,
)
from ocla.tools import ALL, ToolSecurity
import ollama
import sys

_LOG_LEVEL = LOG_LEVEL.get()

# Skip application if we don't have a valid log level; we'll error out later in the CLI.
if LOG_LEVEL.is_valid():
    logging.basicConfig(level=_LOG_LEVEL)

    # Configure httpx underneath ollama client.
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,  # keep everything already configured
            "formatters": {
                "http": {
                    "format": "%(levelname)s [%(asctime)s] %(name)s - %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            },
            "handlers": {
                "http": {
                    "class": "logging.StreamHandler",
                    "formatter": "http",
                    "level": _LOG_LEVEL,  # this handler sees all httpx debug
                    "stream": "ext://sys.stderr",
                },
            },
            "loggers": {
                "httpx": {
                    "handlers": ["http"],
                    "level": _LOG_LEVEL,
                    "propagate": False,
                },
                "httpcore": {
                    "handlers": ["http"],
                    "level": _LOG_LEVEL,
                    "propagate": False,
                },
            },
        }
    )


def execute_tool(call: ollama.Message.ToolCall) -> str:
    entry = ALL.get(call.function.name)

    result = None

    if entry is None:
        err = f"Unknown tool: {call.function.name}"
    else:
        try:
            result, err = entry.execute(**(call.function.arguments or {}))
            result = str(result)
        except Exception as e:
            err = f"Unknown error"

    info(f"Executed tool '{call.function.name}' with {format_tool_arguments(call)}")

    if result == "" and not err:
        result = "[[ no output from tool ]]"

    logging.debug(f"Tool result: {result}")
    logging.debug(f"Tool error: {err}")

    if err:
        error(err)

    return err or result


def _confirm_tool(call: ollama.Message.ToolCall) -> bool:
    """Ask the user whether to run this tool call respecting config."""
    fn = call.function.name

    tool = ALL.get(call.function.name)
    if not tool:
        error(f"Unknown tool: {fn}")
        return False

    mode = TOOL_PERMISSION_MODE.get()

    if mode == TOOL_PERMISSION_MODE_ALWAYS_ALLOW:
        info(
            f"Automatically allowing use of tool '{fn}' ({TOOL_PERMISSION_MODE_ALWAYS_ALLOW} mode)"
        )
        return True

    if (
        mode == TOOL_PERMISSION_MODE_DEFAULT
        and tool.security == ToolSecurity.PERMISSIBLE
    ):
        info(f"Automatically allowing use of tool '{fn}'")
        return True

    prompt = tool.prompt(call, "[y/N]")

    reply = interactive_prompt(prompt)

    if reply and reply.strip().lower().startswith("y"):
        return True

    if reply is None:
        error("No interactive session to acquire permission from user")

    return False


def _model_context_limit(model: str) -> int | None:
    try:
        response = ollama.show(model)
    except Exception as e:
        logging.debug(f"failed to query model info: {e}")
        return None

    for key in response.modelinfo:
        if "context_length" in key or "num_ctx" in key:
            if isinstance(response.modelinfo[key], str) and response.modelinfo[key].isdigit():
                return int(response.modelinfo[key])

            if type(response.modelinfo[key]) is int:
                return response.modelinfo[key]

    return None


def _chat_stream(**kwargs) -> tuple[str, Message]:
    content_parts: list[str] = []
    tool_calls: list[ollama.Message.ToolCall] = []  # gather all tool calls
    last_role: str | None = None  # keep whatever role we see last

    thinking = False
    show_thinking = DISPLAY_THINKING.get().lower() != "false"

    for chunk in ollama.chat(
        stream=True, options={"num_ctx": int(CONTEXT_WINDOW.get())}, **kwargs
    ):
        msg = chunk.get("message", {})
        last_role = msg.get("role", last_role)

        part = msg.get("content") or ""

        if part:
            content_parts.append(part)
            output = True

            if part == "<think>":
                thinking = True
                output = False

            if thinking and part == "</think>":
                thinking = False
                output = False

            if output and (show_thinking or not thinking):
                agent_output(part, thinking=thinking, end="")

        if "tool_calls" in msg:
            tool_calls.extend(msg["tool_calls"])

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
    model = MODEL.get()

    accumulated_text: list[str] = []

    while True:
        # --- 1️⃣  ask the model ------------------------------------------
        content, msg = _chat_stream(
            model=model,
            messages=session.messages,
            tools=[t for t in ALL.values()],
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
    info("session ")
    return "".join(accumulated_text)


def read_prompt_from_stdin() -> str:
    if sys.stdin.isatty():  # launched interactively with no pipe
        return input("prompt> ")  # one-liner; could also loop for multi-turn
    return sys.stdin.read()  # piped or redirected data


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Interact with a local Ollama model",
    )
    parser.add_argument(
        "-n",
        "--new-session",
        help="Generate a new session and run in it. This will be made the active session for future commands",
        action="store_true",
    )

    subparsers = parser.add_subparsers(dest="command")

    session_parser = subparsers.add_parser("session", help="Manage sessions")
    session_sub = session_parser.add_subparsers(dest="session_cmd")
    session_new = session_sub.add_parser("new", help="Create a new session")
    session_new.add_argument("name", nargs="?")
    session_sub.add_parser("list", help="List available sessions")
    session_set = session_sub.add_parser("set", help="Set current session")
    session_set.add_argument("name")

    subparsers.add_parser("config", help="Show config information")

    args, prompt_parts = parser.parse_known_args(argv)

    for var in CONFIG_VARS.values():
        if validation_err := var.validate():
            parser.error(f"Invalid value for {var.name}: {validation_err}")

    model_ctx = _model_context_limit(MODEL.get())
    if model_ctx is None:
        logging.warning(f"Could not determine model context limit from ollama for model {MODEL.get()}")

    ctx_conf = int(CONTEXT_WINDOW.get())

    if model_ctx and ctx_conf > model_ctx:
        logging.warning(
            "Configured context window %s exceeds model limit %s.",
            ctx_conf,
            model_ctx,
        )

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
            table.add_column("Tokens")
            table.add_column("% of Context")
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
                        str(s.tokens),
                        s.usage_pct(),
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
    elif args.command == "config":
        table = Table(title="Available Configuration Variables")

        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="")
        table.add_column("Env Var", style="magenta")
        table.add_column("Config Key", style="yellow")
        table.add_column("Default", style="dim")
        table.add_column("Current Value", style="green")
        table.add_column("Allowed values", style="")

        for var in CONFIG_VARS.values():
            table.add_row(
                var.name,
                var.description,
                var.env or "",
                var.config_file_property or "",
                var.default or "",
                var.get() or "",
                (
                    "\n".join(
                        [
                            x[0] + ": " + x[1] if x[1] else x[0]
                            for x in list(var.allowed_values.items())
                        ]
                    )
                    if var.allowed_values
                    else ""
                ),
            )

        console.print(table)
        return

    session_name = get_current_session_name() or generate_session_name()
    if args.new_session:
        session_name = generate_session_name()
        set_current_session_name(session_name)
        info(f"Created new session {session_name} and set it as the current session.")

    # Treat remaining arguments as the prompt
    msg = " ".join(prompt_parts).strip() or read_prompt_from_stdin().strip()
    if not msg:
        parser.error("No prompt supplied via arguments or stdin.")

    session = Session(session_name)
    if get_current_session_name() is None:
        set_current_session_name(session_name)

    try:
        do_chat(session, msg)
    except ContextWindowExceededError as e:
        error(e.exceeds_message)
        return


if __name__ == "__main__":
    main()
