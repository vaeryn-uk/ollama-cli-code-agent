# Ollama CLI Code Agent

A hobby project implementing an experimental command-line coding agent.
Use it to generate code, analyze repositories, and manage development tasks directly from your terminal.

**Warning: This is experimental software and may be unstable or incomplete. Use at your own risk. 
Functionality, performance, and APIs are subject to change without notice.**

## Features

- Ollama-first; local LLM support.
- OpenAI support for more powerful models.
- Session management and context usage tracking.
- Project-centric storage and configuration.
- Support for Linux & Windows.

## Dependencies & Installation

TODO.

## Configuration

`ocla` supports configuration through three sources, in the following order of precedence (highest to lowest):

- Command-line arguments
- Environment variables
- Configuration file – `.ocla/config.json` in the current working directory

Each configuration setting specifies which of these sources it supports.

<!-- CONFIG_TABLE_START -->
### config_file

Path to the config file

- **CLI:** `N/A`
- **Environment variable:** `OCLA_CONFIG_FILE`
- **Config file:** `N/A`
- **Default value:** `./.ocla/config.json`


### context_window

Context window size in tokens

- **CLI:** `N/A`
- **Environment variable:** `OCLA_CONTEXT_WINDOW`
- **Config file:** `contextWindow`
- **Default value:** `16384`


### log_level

Log level

- **CLI:** `N/A`
- **Environment variable:** `OCLA_LOG_LEVEL`
- **Config file:** `logLevel`
- **Default value:** `WARNING`
- **Allowed values:**
  - `CRITICAL`
  - `ERROR`
  - `WARNING`
  - `INFO`
  - `DEBUG`

### model

The model to use for agent inference. Must be available in the Ollama API

- **CLI:** `-m --model`
- **Environment variable:** `OCLA_MODEL`
- **Config file:** `model`
- **Default value:** `qwen3`


### ollama_host

Override the OLLAMA_HOST for the Ollama API

- **CLI:** `N/A`
- **Environment variable:** `OCLA_OLLAMA_HOST`
- **Config file:** `ollamaHost`
- **Default value:** `N/A`


### project_context_file

the relative path to a file that gives ocla more context about your project (case-insensitive)

- **CLI:** `N/A`
- **Environment variable:** `OCLA_PROJECT_CONTEXT_FILE`
- **Config file:** `projectContextFiles`
- **Default value:** `AGENTS.md`


### prompt_mode

How you want to interact with the assistant

- **CLI:** `-p --prompt-mode`
- **Environment variable:** `OCLA_PROMPT_MODE`
- **Config file:** `promptMode`
- **Default value:** `INTERACTIVE`
- **Allowed values:**
  - `ONESHOT`: The program quits after a single prompt
  - `INTERACTIVE`: You issue prompts until quit

### provider

Model provider to use

- **CLI:** `N/A`
- **Environment variable:** `OCLA_PROVIDER`
- **Config file:** `provider`
- **Default value:** `ollama`
- **Allowed values:**
  - `ollama`: Use local Ollama models
  - `openai`: Use the OpenAI API

### session_dir

Path to the session directory

- **CLI:** `N/A`
- **Environment variable:** `OCLA_SESSION_DIR`
- **Config file:** `sessionDir`
- **Default value:** `./.ocla/sessions`


### session_storage_mode

how we store session data on disk

- **CLI:** `N/A`
- **Environment variable:** `OCLA_SESSION_STORAGE_MODE`
- **Config file:** `sessionStorageMode`
- **Default value:** `COMPRESS`
- **Allowed values:**
  - `PLAIN`: Plain text (JSON). Can get large.
  - `COMPRESS`: Compressed via gzip

### state_file

Path to the state file

- **CLI:** `N/A`
- **Environment variable:** `OCLA_STATE_FILE`
- **Config file:** `stateFile`
- **Default value:** `./.ocla/state.json`


### thinking

Enable & show model thinking. If the model does not support thinking, this has no effect and thinking is disabled.

- **CLI:** `-t --thinking`
- **Environment variable:** `OCLA_THINKING`
- **Config file:** `thinking`
- **Default value:** `ENABLED`
- **Allowed values:**
  - `DISABLED`: The model will not think and nothing is shown
  - `HIDDEN`: The model will think, but thinking output is not displayed
  - `ENABLED`: The model will think and ocla prints this output

### tool_permission_mode

How tools request permission to run

- **CLI:** `N/A`
- **Environment variable:** `OCLA_TOOL_PERMISSION_MODE`
- **Config file:** `toolPermissionMode`
- **Default value:** `DEFAULT`
- **Allowed values:**
  - `DEFAULT`: Ask for permission for non-trivial tools
  - `ALWAYS_ASK`: Always ask for permission for all tools
  - `ALWAYS_ALLOW`: Always run any tool; use with caution

<!-- CONFIG_TABLE_END -->

