VENV ?= .venv

.PHONY: init

init:
	uv venv $(VENV)
	uv pip install -e . -p $(VENV)
