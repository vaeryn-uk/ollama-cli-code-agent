VENV ?= .venv

.PHONY: init test

# extras declared under [project.optional-dependencies] in pyproject.toml
EXTRAS := test,dev

init:
	uv venv $(VENV)
	uv pip install -e .[$(EXTRAS)] -p $(VENV)

test.docker:
	docker compose -f tests/docker-compose.yml up -d

test:
	uv run pytest -q

lint:
	uv run black --check --diff .

fmt:
	uv run black .