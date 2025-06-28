import argparse
import json
import subprocess
from ocla.session import Session
from ocla.tools import ls
import ollama
import sys
from typing import List, Dict, Callable, Any

TOOLS: Dict[str, Callable[..., Any]] = {
    "ls": ls,
    # "other": other_fn,
}

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
    response = ollama.chat(model=model, messages=session.messages, tools=list(TOOLS.values()))
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
    parser.add_argument("prompt", nargs="*", help="Message to send to the model")
    parser.add_argument("-m", "--model", default="codellama", help="Model name")
    parser.add_argument("-s", "--session", default="default", help="Session name")
    parser.add_argument("--reset", action="store_true", help="Reset the session history")
    args = parser.parse_args(argv)

    # Prefer positional argument; otherwise use stdin
    msg = " ".join(args.prompt).strip() or read_prompt_from_stdin().strip()
    if not msg:
        parser.error("No prompt supplied via arguments or stdin.")

    session = Session(args.session)
    if args.reset:
        session.messages = []

    output = chat_with_tools(args.model, session, msg)
    print(output)


if __name__ == "__main__":
    main()
