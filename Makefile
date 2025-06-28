VENV ?= .venv

.PHONY: init test

init:
	uv venv $(VENV)
	uv pip install -e . -p $(VENV)

test:
	docker compose -f tests/docker-compose.yml up -d
	pytest -q
	docker compose -f tests/docker-compose.yml down -v
