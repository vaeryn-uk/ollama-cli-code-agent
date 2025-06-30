## Project Layout

- **.gitignore**: Specifies files to ignore in Git
- **AGENTS.md**: Documentation for agents
- **Makefile**: Build automation scripts
- **pyproject.toml**: Python project configuration
- **uv.lock**: Poetry lock file for dependencies
- **README.md**: Project overview and setup instructions

### Configuration

Configuration values can be set in `.ocla/config.json` or through environment
variables. Newly added options include:

- `toolPermissionMode` – one of `DEFAULT`, `ASK_ALL`, or `ALLOW_ALLOW`.
- `displayThinking` – `True` to show LLM thinking output or `False` to hide it.
