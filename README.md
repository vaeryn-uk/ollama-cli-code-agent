# Ollama CLI Code Agent

This project provides a command-line interface that wraps an AI agent powered by Ollama.
Use it to generate code, analyze repositories and manage development tasks directly from
your terminal.

## Configuration

<!-- CONFIG_TABLE_START -->
### `config_file`
- **CLI:** `N/A`
- **Env:** `OCLA_CONFIG_FILE`
- **Config file:** `N/A`
- **Default:** `./.ocla/config.json`
- **Description:** Path to the config file

### `context_window`
- **CLI:** `N/A`
- **Env:** `OCLA_CONTEXT_WINDOW`
- **Config file:** `contextWindow`
- **Default:** `16384`
- **Description:** Context window size in tokens

### `log_level`
- **CLI:** `N/A`
- **Env:** `OCLA_LOG_LEVEL`
- **Config file:** `logLevel`
- **Default:** `WARNING`
- **Description:** Log level (`CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`)

### `model`
- **CLI:** `-m --model`
- **Env:** `OCLA_MODEL`
- **Config file:** `model`
- **Default:** `qwen3`
- **Description:** Model name

### `ollama_host`
- **CLI:** `N/A`
- **Env:** `OCLA_OLLAMA_HOST`
- **Config file:** `ollamaHost`
- **Default:** `N/A`
- **Description:** Override the OLLAMA_HOST for the Ollama API

### `project_context_file`
- **CLI:** `N/A`
- **Env:** `OCLA_PROJECT_CONTEXT_FILE`
- **Config file:** `projectContextFiles`
- **Default:** `AGENTS.md`
- **Description:** the relative path to a file that gives ocla more context about your project (case-insensitive)

### `prompt_mode`
- **CLI:** `-p --prompt-mode`
- **Env:** `OCLA_PROMPT_MODE`
- **Config file:** `promptMode`
- **Default:** `INTERACTIVE`
- **Description:** How you want to interact with the assistant (`ONESHOT`: The program quits after a single prompt, `INTERACTIVE`: You issue prompts until quit)

### `session_dir`
- **CLI:** `N/A`
- **Env:** `OCLA_SESSION_DIR`
- **Config file:** `sessionDir`
- **Default:** `./.ocla/sessions`
- **Description:** Path to the session directory

### `session_storage_mode`
- **CLI:** `N/A`
- **Env:** `OCLA_SESSION_STORAGE_MODE`
- **Config file:** `sessionStorageMode`
- **Default:** `COMPRESS`
- **Description:** how we store session data on disk (`PLAIN`: Plain text (JSON). Can get large., `COMPRESS`: Compressed via gzip)

### `state_file`
- **CLI:** `N/A`
- **Env:** `OCLA_STATE_FILE`
- **Config file:** `stateFile`
- **Default:** `./.ocla/state.json`
- **Description:** Path to the state file

### `thinking`
- **CLI:** `-t --thinking`
- **Env:** `OCLA_THINKING`
- **Config file:** `thinking`
- **Default:** `ENABLED`
- **Description:** Enable & show model thinking, if supported. (`DISABLED`: The model will not think and nothing is shown, `HIDDEN`: The model will think, but thinking output is not displayed, `ENABLED`: The model will think and ocla prints this output)

### `tool_permission_mode`
- **CLI:** `N/A`
- **Env:** `OCLA_TOOL_PERMISSION_MODE`
- **Config file:** `toolPermissionMode`
- **Default:** `DEFAULT`
- **Description:** How tools request permission to run (`DEFAULT`: Ask for permission for non-trivial tools, `ALWAYS_ASK`: Always ask for permission for all tools, `ALWAYS_ALLOW`: Always run any tool; use with caution)

<!-- CONFIG_TABLE_END -->

