.PHONY: help install lint test ci

UV := uv run --no-project --python 3.12 --with-editable '.[dev]'

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

install: ## Install the frontend dependencies (the backend runs through uv)
	cd frontend && npm ci --legacy-peer-deps

lint: ## ESLint on the frontend
	cd frontend && npm run lint

test: ## Backend tests (SQLite and fakeredis, no services) and frontend tests
	cd backend && $(UV) pytest -q
	cd frontend && npm test

ci: install lint test ## CI entry point
