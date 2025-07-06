import argparse
import os

import humanize
from datetime import datetime

from typing import Any, Dict

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
    add_cli_args,
    TOOL_PERMISSION_MODE,
    THINKING,
    THINKING_DISABLED,
    THINKING_ENABLED,
    TOOL_PERMISSION_MODE_DEFAULT,
    TOOL_PERMISSION_MODE_ALWAYS_ALLOW,
    PROMPT_MODE,
)
from ocla.providers import get_provider, ModelInfo
from ocla.session import (
    Session,
    list_sessions,
    set_current_session_name,
    get_current_session_name,
    generate_session_name,
    session_exists,
    ContextWindowExceededError,
    load_session_meta, ProviderMismatchError,
)
from ocla.tools import ALL as ALL_TOOLS, ToolSecurity, Tool

_LOG_LEVEL = LOG_LEVEL.get()

import signal
import sys


# No python stacktrace.
def _quit_gracefully(signum, frame):
    print()
    sys.exit(130)


signal.signal(signal.SIGINT, _quit_gracefully)

# Skip application if we don't have a valid log level; we'll error out later in the CLI.
if LOG_LEVEL.is_valid():
    logging.basicConfig(level=_LOG_LEVEL)

    # Configure httpx underneath HTTP clients.
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


provider = get_provider()


def execute_tool(call: Dict[str, Any]) -> str:
    fn = call.get("function", {}).get("name")
    entry = ALL_TOOLS.get(fn)

    result = None

    if entry is None:
        err = f"Unknown tool: {fn}"
    else:
        try:
            result, err = entry.execute(
                **(call.get("function", {}).get("arguments", {}) or {})
            )
            result = str(result)
        except Exception as e:
            err = f"Unknown error"

    info(f"Executed tool '{fn}' with {format_tool_arguments(call)}")

    if result == "" and not err:
        result = "[[ no output from tool ]]"

    logging.debug(f"Tool result: {result}")
    logging.debug(f"Tool error: {err}")

    if err:
        error(err)

    return err or result


def _confirm_tool(call: Dict[str, Any]) -> bool:
    """Ask the user whether to run this tool call respecting config."""
    fn = call.get("function", {}).get("name")

    tool = ALL_TOOLS.get(fn)
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


def _current_model_info() -> ModelInfo:
    return provider.model_info(MODEL.get())


def _chat_stream(messages, tools: list[Tool]) -> tuple[str, Dict[str, Any]]:
    full_content: str = ""
    full_thinking: str = ""
    tool_calls: list[Dict[str, Any]] = []  # gather all tool calls
    last_role: str | None = None  # keep whatever role we see last

    thinking_mode = THINKING.get()
    enable_think = thinking_mode != THINKING_DISABLED and _current_model_info().supports_thinking
    show_thinking = thinking_mode == THINKING_ENABLED
    num_ctx = int(CONTEXT_WINDOW.get()) if CONTEXT_WINDOW.get() else None

    for chunk in provider.chat(messages=messages, tools=tools, thinking=enable_think, model=MODEL.get(), context_window=num_ctx):
        msg = chunk.get("message", {})
        if hasattr(msg, "model_dump"):
            msg = msg.model_dump(mode="python", by_alias=True)
        last_role = msg.get("role", last_role)

        if part := msg.get("content"):
            full_content += part
            agent_output(part, thinking=False, end="")

        if part := msg.get("thinking"):
            full_thinking += part
            if show_thinking:
                agent_output(part, thinking=True, end="")

        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                if hasattr(tc, "model_dump"):
                    tool_calls.append(tc.model_dump(mode="python", by_alias=True))
                else:
                    tool_calls.append(tc)

    assistant_msg: Dict[str, Any] = {
        "role": last_role or "assistant",
        "content": full_content,
    }
    if full_thinking:
        assistant_msg["thinking"] = full_thinking
    if tool_calls:
        assistant_msg["tool_calls"] = tool_calls

    return full_content, assistant_msg


def do_chat(session: Session, prompt: str) -> str:
    session.add({"role": "user", "content": prompt})
    model = MODEL.get()

    accumulated_text: list[str] = []

    while True:
        # --- 1️⃣  ask the model ------------------------------------------
        content, msg = _chat_stream(
            session.messages,
            tools=ALL_TOOLS.values(),
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
                    "name": call.get("function", {}).get("name"),
                    "content": tool_output,
                    "tool_call_id": call.get("id", None), # OpenAI needs this.
                }
            )

    session.save()
    info("")

    info("")
    info(f"[ session context usage {load_session_meta(session.name).usage_pct()} ]")

    return "".join(accumulated_text)


def _build_arg_parser() -> argparse.ArgumentParser | None:
    parser = argparse.ArgumentParser(
        description="Interact with a language model",
    )
    parser.add_argument(
        "-n",
        "--new-session",
        help="Generate a new session and run in it. This will be made the active session for future commands",
        action="store_true",
    )

    add_cli_args(parser)

    subparsers = parser.add_subparsers(dest="command")

    session_parser = subparsers.add_parser("session", help="Manage sessions")
    session_sub = session_parser.add_subparsers(dest="session_cmd")
    session_new = session_sub.add_parser("new", help="Create a new session")
    session_new.add_argument("name", nargs="?")
    session_sub.add_parser("list", help="List available sessions")
    session_set = session_sub.add_parser("set", help="Set current session")
    session_set.add_argument("name")

    subparsers.add_parser("config", help="Show config information")
    model = subparsers.add_parser("model", help="Show model information")
    subparsers.add_parser("tools", help="Display tools made available to the agent")

    model_cmd = model.add_subparsers(dest="model_cmd")
    model_cmd.add_parser("list", help="Show available models")
    model_cmd.add_parser("info", help="Show information for the current model")

    return parser


def _initialization_check():
    if os.getenv("OCLA_DISABLE_INIT_CHECK"):
        return

    try:
        provider.initialization_check(MODEL.get())
    except RuntimeError as e:
        error(str(e))
        raise SystemExit(1)

    model_ctx = _current_model_info().context_length
    if model_ctx is None:
        logging.warning(
            f"Could not determine model context limit from {provider.name} for model {MODEL.get()}"
        )

    ctx_conf = int(CONTEXT_WINDOW.get())

    if model_ctx and ctx_conf > model_ctx:
        logging.warning(
            "Configured context window %s exceeds model limit %s.",
            ctx_conf,
            model_ctx,
        )


def main(argv=None):
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    for var in CONFIG_VARS.values():
        if validation_err := var.validate():
            parser.error(
                f"Invalid value for {var.name} ({var.get()}): {validation_err}"
            )

    _initialization_check()

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
            table.add_column("Provider")
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
                        s.provider,
                    )
                )

            console.print(table)
        elif args.session_cmd == "set":
            if not session_exists(args.name):
                parser.error(f"Unknown session: {args.name}")
            set_current_session_name(args.name)

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
            current_value = var.get() or ""
            if var.sensitive and current_value:
                current_value = "************"

            table.add_row(
                var.name,
                var.description,
                var.env or "",
                var.config_file_property or "",
                var.default or "",
                current_value,
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
    elif args.command == "model":
        if args.model_cmd == "info":
            table = Table(title="Model info", show_header=False)

            table.add_column("key")
            table.add_column("value")

            table.add_row("Name", MODEL.get())

            table.add_section()
            table.add_row(
                "Model maximum context window",
                str(_current_model_info().context_length) or "N/A",
            )
            table.add_row("Current configured context window", f"{CONTEXT_WINDOW.get()}")

            table.add_section()
            supported = _current_model_info().supports_thinking
            table.add_row(
                "Model supports thinking?",
                "N/A" if supported is None else str(supported),
            )
            table.add_row("Current thinking setting", THINKING.get())

            console.print(table)
            return
        elif args.model_cmd == "list":
            if len(provider.available_models()) == 0:
                console.print("No models available")
                return

            table = Table(title="Available models")

            table.add_column("Model")
            table.add_column("Supports thinking?")
            table.add_column("Context window")

            for provider_model in provider.available_models():
                table.add_row(
                    provider_model.name,
                    str(provider_model.supports_thinking) if provider_model.supports_thinking is not None else "Unknown",
                    str(provider_model.context_length) if provider_model.context_length is not None else "Unknown",
                )

            console.print(table)
            return
        else:
            parser.error("Invalid model command")
    elif args.command == "tools":
        for t in ALL_TOOLS.values():
            console.print(t.describe().model_dump(exclude_none=True))
        return

    session_name = get_current_session_name() or generate_session_name()
    if args.new_session:
        session_name = generate_session_name()
        set_current_session_name(session_name)
        info(f"Created new session {session_name} and set it as the current session.")

    try:
        session = Session(session_name)
    except ProviderMismatchError as e:
        error(str(e))
        return
    if get_current_session_name() is None:
        set_current_session_name(session_name)

    # Take prompt from stdin if provided.
    msg = None if sys.stdin.isatty() else sys.stdin.read().strip()

    while True:
        if not msg or len(msg) == 0:
            detect_quit = False
            if PROMPT_MODE.get() == "INTERACTIVE":
                prompt_msg = "[bold cyan]prompt (q to quit) ❯[/bold cyan] "
                detect_quit = True
            else:
                prompt_msg = "[bold cyan]prompt ❯[/bold cyan] "

            msg = interactive_prompt(prompt_msg).strip()
            if detect_quit and msg.lower() == "q":
                break

        if msg is not None and len(msg) > 0:
            try:
                do_chat(session, msg)
            except ContextWindowExceededError as e:
                error(e.exceeds_message)
                return

        if PROMPT_MODE.get() == "ONESHOT":
            break

        msg = None


if __name__ == "__main__":
    main()
