import argparse
import json
import subprocess
from ocla.session import Session
import ollama


def execute_tool(call: dict) -> str:
    function = call.get("function", {})
    name = function.get("name")
    raw_args = function.get("arguments", "{}")
    try:
        args = json.loads(raw_args)
    except json.JSONDecodeError:
        args = {}
    if name == "shell":
        cmd = args.get("cmd") or args.get("command")
        if not cmd:
            return "No command provided"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout + result.stderr
    return f"Unknown tool {name}"


def chat_with_tools(model: str, session: Session, prompt: str) -> str:
    session.add({"role": "user", "content": prompt})
    response = ollama.chat(model=model, messages=session.messages)
    message = response.get("message", {})
    session.add(message)

    if "tool_calls" in message:
        for call in message["tool_calls"]:
            output = execute_tool(call)
            session.add({"role": "tool", "content": output, "name": call.get("function", {}).get("name")})
        response = ollama.chat(model=model, messages=session.messages)
        message = response.get("message", {})
        session.add(message)

    session.save()
    return message.get("content", "")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Interact with a local ollama model")
    parser.add_argument("prompt", nargs="*", help="Message to send to the model")
    parser.add_argument("-m", "--model", default="codellama", help="Model name")
    parser.add_argument("-s", "--session", default="default", help="Session name")
    parser.add_argument("--reset", action="store_true", help="Reset the session history")
    args = parser.parse_args(argv)

    msg = " ".join(args.prompt)
    session = Session(args.session)
    if args.reset:
        session.messages = []
    output = chat_with_tools(args.model, session, msg)
    print(output)


if __name__ == "__main__":
    main()
