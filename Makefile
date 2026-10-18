# Makefile: the entry point for agents, hooks and CI (see AGENTS.md > Commands).
# Every target runs from the repository root.

SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

UV := uv run --directory backend
API_IMAGE ?= devorchestrator-api:local
# The commit the API reports in its version (compose and smoke targets only).
GIT_SHA ?= $(shell git rev-parse HEAD 2>/dev/null)

.PHONY: help install lint typecheck test build build-web build-image openapi up down smoke

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Install backend (uv, from the lockfile) and npm dependencies
	uv sync --directory backend --locked
	npm ci

lint: ## ruff check, ruff format --check, ESLint and Prettier
	$(UV) ruff check .
	$(UV) ruff format --check .
	npm run lint

typecheck: ## mypy and tsc --noEmit in every workspace
	$(UV) mypy
	npm run typecheck

test: ## pytest, Vitest and Jest
	$(UV) pytest
	npm test

build: build-web build-image ## Web bundle and API image

build-web: ## Web bundle (apps/web/dist)
	npm run build

build-image: ## API image, local only (never pushed)
	docker build -f backend/Dockerfile -t $(API_IMAGE) .

openapi: ## Export the API contract to docs/api/openapi.yaml
	$(UV) python scripts/export_openapi.py

up: ## Start api and db with compose, waiting for the healthchecks
	GIT_SHA=$(GIT_SHA) docker compose up -d --build --wait

down: ## Stop the compose stack (the database volume is kept)
	docker compose down

smoke: ## Compose smoke test: build, start, check readiness, tear down
	GIT_SHA=$(GIT_SHA) ci/smoke.sh
