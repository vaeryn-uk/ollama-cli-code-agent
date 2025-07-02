# Ollama CLI Code Agent

This project provides a command-line interface that wraps an AI agent powered by Ollama.
Use it to generate code, analyze repositories and manage development tasks directly from
your terminal.

## Configuration

<!-- CONFIG_TABLE_START -->
| Name | CLI | Env | Config file | Default | Description |
| --- | --- | --- | --- | --- | --- |
| `config_file` | `N/A` | `OCLA_CONFIG_FILE` | `N/A` | `./.ocla/config.json` | Path to the config file |
| `context_window` | `N/A` | `OCLA_CONTEXT_WINDOW` | `contextWindow` | `16384` | Context window size in tokens |
| `log_level` | `N/A` | `OCLA_LOG_LEVEL` | `logLevel` | `WARNING` | Log level (`CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`) |
| `model` | `-m --model` | `OCLA_MODEL` | `model` | `qwen3` | Model name |
| `ollama_host` | `N/A` | `OCLA_OLLAMA_HOST` | `ollamaHost` | `N/A` | Override the OLLAMA_HOST for the Ollama API |
| `project_context_file` | `N/A` | `OCLA_PROJECT_CONTEXT_FILE` | `projectContextFiles` | `AGENTS.md` | the relative path to a file that gives ocla more context about your project (case-insensitive) |
| `prompt_mode` | `-p --prompt-mode` | `OCLA_SESSION_STORAGE_MODE` | `promptMode` | `INTERACTIVE` | How you want to interact with the assistant (`ONESHOT`: The program quits after a single prompt, `INTERACTIVE`: You issue prompts until quit) |
| `session_dir` | `N/A` | `OCLA_SESSION_DIR` | `sessionDir` | `./.ocla/sessions` | Path to the session directory |
| `session_storage_mode` | `N/A` | `OCLA_SESSION_STORAGE_MODE` | `sessionStorageMode` | `COMPRESS` | how we store session data on disk (`PLAIN`: Plain text (JSON). Can get large., `COMPRESS`: Compressed via gzip) |
| `state_file` | `N/A` | `OCLA_STATE_FILE` | `stateFile` | `./.ocla/state.json` | Path to the state file |
| `thinking` | `-t --thinking` | `OCLA_THINKING` | `displayThinking` | `ENABLED` | How to display assistant thinking output (`DISABLED`: The model will not think and nothing is shown, `HIDDEN`: The model will think, but thinking output is not displayed, `ENABLED`: The model will think and ocla prints this output) |
| `tool_permission_mode` | `N/A` | `OCLA_TOOL_PERMISSION_MODE` | `toolPermissionMode` | `DEFAULT` | How tools request permission to run (`DEFAULT`: Ask for permission for non-trivial tools, `ALWAYS_ASK`: Always ask for permission for all tools, `ALWAYS_ALLOW`: Always run any tool; use with caution) |
<!-- CONFIG_TABLE_END -->

