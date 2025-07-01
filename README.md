# Ollama CLI Code Agent

This project provides a command-line interface that wraps an AI agent powered by Ollama.
Use it to generate code, analyze repositories and manage development tasks directly from
your terminal.

## Configuration

<!-- CONFIG_TABLE_START -->
| Name | Env | Config file | Default | Description |
| --- | --- | --- | --- | --- |
| `config_file` | `OCLA_CONFIG_FILE` | `N/A` | `./.ocla/config.json` | Path to the config file |
| `context_window` | `OCLA_CONTEXT_WINDOW` | `contextWindow` | `16384` | Context window size in tokens |
| `display_thinking` | `OCLA_DISPLAY_THINKING` | `displayThinking` | `True` | Display assistant thinking output (True: Display thinking output, False: Do not display thinking output) |
| `log_level` | `OCLA_LOG_LEVEL` | `logLevel` | `WARNING` | Log level (CRITICAL: Critical, ERROR: Error, WARNING: Warning, INFO: Info, DEBUG: Debug) |
| `model` | `OCLA_MODEL` | `model` | `qwen3` | Model name |
| `project_context_file` | `OCLA_PROJECT_CONTEXT_FILE` | `projectContextFiles` | `AGENTS.md` | the relative path to a file that gives ocla more context about your project (case-insensitive) |
| `session_dir` | `OCLA_SESSION_DIR` | `sessionDir` | `./.ocla/sessions` | Path to the session directory |
| `session_storage_mode` | `OCLA_SESSION_STORAGE_MODE` | `sessionStorageMode` | `ENCRYPT` | how we store session data on disk (PLAIN: Plain text (JSON). Can get large., COMPRESS: Compressed via TODO, ENCRYPT: Compressed and encrypted via OS-provided encryption methods (if supported)) |
| `state_file` | `OCLA_STATE_FILE` | `stateFile` | `./.ocla/state.json` | Path to the state file |
| `tool_permission_mode` | `OCLA_TOOL_PERMISSION_MODE` | `toolPermissionMode` | `DEFAULT` | How tools request permission to run (DEFAULT: Default: ask for permission for non-trivial tools, ALWAYS_ASK: Always ask for permission for all tools, ALWAYS_ALLOW: Always run any tool; use with caution) |
<!-- CONFIG_TABLE_END -->

