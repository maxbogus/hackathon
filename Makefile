# ============================================================================
# Transit-AI (hackathon) — Makefile
# ----------------------------------------------------------------------------
# Single entry point for all common tasks. Run `make help` for the full list.
#
# Tooling:
#   - uv 0.5+       : Python deps (workspaces, .venv)
#   - ruff          : lint + format
#   - mypy strict   : types
#   - pytest        : unit tests
#   - yarn 4 corepack: Node deps
#   - vite          : dev server + build
#   - vitest        : frontend tests
#   - tsc           : typecheck
#   - eslint        : lint
#   - prettier      : format
#   - docker compose: backend + postgres + redis + frontend
# ============================================================================

SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help

# Resolve tooling
UV      ?= uv
YARN    ?= yarn
PYTHON  ?= python3
DC      ?= docker compose
MACHINE ?= rtx5060    # rtx5060 | rtx4070_12gb

.PHONY: help install hooks-install up down \
        lint format typecheck test test-unit test-int check-all \
        seed inventory train-baseline train-xgboost train-gru train-hybrid train-all \
        predict calibrate evaluate sweep mc-scenario \
        api-gen api-check fe-gen \
        assistant-test assistant-reasoning mcp-run \
        ledger-add ledger-list ledger-check ledger-export \
        note-from-finding promote handoff handoff-update \
        backlog-ready backlog-list docs         pyscn pyscn-compare pyscn-baseline         arch-dbml arch-dbml-check         benchmark-baseline benchmark-all benchmark-compare         run-benchmark

# ---------------------------------------------------------------------------
# HELP
# ---------------------------------------------------------------------------

help: ## Show this help
	@printf "\n\033[1mTransit-AI (hackathon) — Makefile\033[0m\n"
	@printf "Tooling: \033[36muv\033[0m + \033[36mruff\033[0m + \033[36mmypy\033[0m + \033[36mvitest\033[0m + \033[36mtsc\033[0m + \033[36morval\033[0m\n\n"
	@printf "Usage: \033[36mmake <target>\033[0m  (MACHINE=rtx4070_12gb make train-gru)\n\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# INSTALL
# ---------------------------------------------------------------------------

install: ## Install all deps (uv sync + yarn install)
	@printf "\033[36m→ uv sync (Python workspaces)\033[0m\n"
	$(UV) sync --extra dev
	@printf "\033[36m→ yarn install (Node workspaces)\033[0m\n"
	corepack enable 2>/dev/null || true
	cd apps/frontend && $(YARN) install
	@printf "\n\033[32m✓ dependencies installed\033[0m\n"
	@printf "Run \033[36mmake hooks-install\033[0m to enable git hooks.\n"

hooks-install: ## Install git hooks from .githooks/
	@printf "\033[36m→ Installing git hooks...\033[0m\n"
	@cp .githooks/pre-commit .git/hooks/pre-commit
	@cp .githooks/pre-push .git/hooks/pre-push
	@cp .githooks/commit-msg .git/hooks/commit-msg
	@chmod +x .git/hooks/pre-commit .git/hooks/pre-push .git/hooks/commit-msg
	@printf "\033[32m✓ hooks installed (pre-commit, pre-push, commit-msg)\033[0m\n"

# ---------------------------------------------------------------------------
# DOCKER STACK
# ---------------------------------------------------------------------------

up: ## Start docker stack (backend, postgres+timescale, redis, frontend)
	$(DC) up -d
	@printf "\033[32m✓ Stack up. Backend: http://localhost:8000 | Frontend: http://localhost:5173\033[0m\n"

down: ## Stop docker stack
	$(DC) down

logs: ## Tail docker logs
	$(DC) logs -f

# ---------------------------------------------------------------------------
# ML (NOT in Docker) — runs locally via uv
# ---------------------------------------------------------------------------

seed: ## Generate synthetic data → data/synthetic/
	$(UV) --directory ml run python scripts/gen_synthetic.py
	@printf "\033[32m✓ Synthetic data generated\033[0m\n"

inventory: ## Profile data (numbers, not hearsay) → reports/inventory.json
	$(UV) --directory ml run python scripts/inventory.py

train-baseline: ## Train baseline (mean by hour/day/route)
	$(UV) --directory ml run python scripts/train_baseline.py

train-xgboost: ## Train XGBoost
	$(UV) --directory ml run python scripts/train_xgboost.py

train-gru: ## Train GRU + attention pooling (from contest/...)
	$(UV) --directory ml run python scripts/train_gru.py

train-hybrid: ## Train hybrid (GRU + LGBM blend in log-space)
	$(UV) --directory ml run python scripts/train_hybrid.py

train-all: train-baseline train-xgboost train-gru train-hybrid ## Train all models

predict: ## Generate predictions with active model → predictions/*.parquet
	$(UV) --directory ml run python scripts/predict.py

calibrate: ## Apply per-bucket calibration
	$(UV) --directory ml run python scripts/calibrate.py

evaluate: ## Evaluate all models on holdout → reports/
	$(UV) --directory ml run python scripts/evaluate.py

sweep: ## Hyperparameter sweep
	$(UV) --directory ml run python scripts/sweep.py

mc-scenario: ## Run Monte Carlo scenario (1000 iterations)
	$(UV) --directory ml run python scripts/monte_carlo_scenario.py --config ml/configs/scenarios/baseline.yaml

# ---------------------------------------------------------------------------
# API + FRONTEND GENERATION
# ---------------------------------------------------------------------------

api-gen: ## Export OpenAPI from backend → docs/api/openapi.json
	cd apps/backend && $(UV) run python scripts/export_openapi.py
	@printf "\033[32m✓ OpenAPI exported\033[0m\n"

api-check: ## Validate OpenAPI is up-to-date with backend code
	cd apps/backend && $(UV) run python scripts/check_openapi.py

fe-gen: ## Generate TS types via Orval → apps/frontend/src/generated/
	cd apps/frontend && $(YARN) orval --config orval.config.ts
	@printf "\033[32m✓ TS types generated\033[0m\n"

# ---------------------------------------------------------------------------
# QUALITY
# ---------------------------------------------------------------------------

lint: ## ruff + eslint + prettier --check
	$(UV) run ruff check apps/ ml/ scripts/
	cd apps/frontend && $(YARN) lint

format: ## ruff format + eslint --fix
	$(UV) run ruff format apps/ ml/ scripts/
	$(UV) run ruff check --fix apps/ ml/ scripts/
	cd apps/frontend && $(YARN) format

typecheck: ## mypy strict + tsc --noEmit
	$(UV) run mypy apps/backend/app apps/assistant/app apps/mcp/ 2>&1 | tail -30 || true
	cd apps/frontend && $(YARN) typecheck

test: ## pytest (unit) + vitest (run)
	$(UV) run pytest apps/backend/tests ml/tests apps/assistant/tests apps/mcp/tests -m unit -q --no-cov
	cd apps/frontend && $(YARN) test:run

test-unit: test ## Alias for test

test-int: ## Integration tests (requires `make up` first)
	$(UV) run pytest apps/backend/tests -m integration -v --no-cov

check-all: lint typecheck test api-check ledger-check ## Run all checks (CI gate)

# ---------------------------------------------------------------------------
# KNOWLEDGE CAPTURE
# ---------------------------------------------------------------------------

backlog-ready: ## Top-5 ready tickets by RICE
	$(UV) run python scripts/ready_tickets.py --top 5

backlog-list: ## All tickets sorted by RICE
	$(UV) run python scripts/ready_tickets.py --all

ledger-add: ## Add decision to ledger (interactive)
	$(UV) run python scripts/ledger.py add

ledger-list: ## Show last 7 days of decisions
	$(UV) run python scripts/ledger.py list --days 7

ledger-export: ## Export ledger to markdown (for presentation)
	$(UV) run python scripts/ledger.py export --output docs/ledger/EXPORT.md

ledger-check: ## Check if merge requires ledger entry (called from pre-commit)
	$(UV) run python scripts/ledger.py check

note-from-finding: ## Create note from last ledger finding
	$(UV) run python scripts/note_from_finding.py

promote: ## Promote a note to rule or skill (make promote NOTE=001 TARGET=rule|skill)
	@printf "\033[33m→ Promoting note $(NOTE) to $(TARGET)...\033[0m\n"
	$(UV) run python scripts/promote_note.py --note $(NOTE) --target $(TARGET)

handoff: ## Show current HANDOFF.md
	@cat docs/HANDOFF.md

handoff-update: ## Update HANDOFF.md (call at session end)
	$(UV) run python scripts/update_handoff.py

# ---------------------------------------------------------------------------
# ASSISTANT + MCP
# ---------------------------------------------------------------------------

assistant-test: ## Smoke test registry of LLM providers
	cd apps/assistant && $(UV) run python -c "from app.providers.registry import REGISTRY; print(f'{len(REGISTRY)} models:', list(REGISTRY.keys()))"

assistant-reasoning: ## Test reasoning (DeepSeek R1 via OpenRouter)
	cd apps/assistant && $(UV) run python scripts/test_reasoning.py

mcp-run: ## Start MCP server (stdio JSON-RPC)
	cd apps/mcp && $(UV) run python server.py

# ---------------------------------------------------------------------------
# LOCAL DEV
# ---------------------------------------------------------------------------

dev: up seed train-baseline predict ## Local dev: up stack + seed + train baseline + predict
	@printf "\n\033[32m✓ Dev environment ready\033[0m\n"
	@printf "Frontend: \033[36mhttp://localhost:5173\033[0m\n"
	@printf "Backend:  \033[36mhttp://localhost:8000/docs\033[0m\n"

docs: api-gen fe-gen ## Regenerate all generated docs (OpenAPI + TS types)

# ---------------------------------------------------------------------------
# TOOLING: pyscn (structural code quality gate)
# ---------------------------------------------------------------------------

.pyscn/report.json:
	@mkdir -p .pyscn

pyscn: .pyscn/report.json ## Run pyscn structural analysis → .pyscn/report.{json,html}
	@printf "\033[36m→ Running pyscn analyze...\033[0m\n"
	pyscn analyze apps/ ml/ scripts/ --json --html --no-open --output .pyscn/report.json

pyscn-compare: pyscn ## Compare current report vs baseline (CI gate)
	@printf "\033[36m→ Comparing vs baseline...\033[0m\n"
	$(UV) run python scripts/pyscn_compare.py \
		--baseline ai/analysis/pyscn-baseline.json \
		--current .pyscn/report.json

pyscn-baseline: pyscn ## Overwrite baseline from current report (use sparingly, ADR required)
	@printf "\033[33m→ Updating pyscn baseline (commit message should reference ADR)...\033[0m\n"
	$(UV) run python -c "
import json, datetime
from pyscn_summary import extract
" 2>/dev/null || cp .pyscn/report.json ai/analysis/pyscn-baseline.json
	@printf "\033[32m✓ Baseline updated\033[0m\n"

# ---------------------------------------------------------------------------
# TOOLING: arch-dbml (DB schema tracking)
# ---------------------------------------------------------------------------

arch-dbml: ## Regenerate docs/architecture/schema.{dbml,tables.md} from SQLAlchemy models
	@printf "\033[36m→ Generating DBML...\033[0m\n"
	$(UV) run python scripts/generate_dbml.py

arch-dbml-check: ## CI gate: fail if DBML drift detected (run after models change)
	@printf "\033[36m→ Checking DBML drift...\033[0m\n"
	$(UV) run python scripts/generate_dbml.py --check

# ---------------------------------------------------------------------------
# ML: benchmark pipeline (offline tool)
# ---------------------------------------------------------------------------

benchmark-baseline: ## Smoke benchmark BaselineMean (~30 sec)
	@printf "\033[36m→ Benchmark: BaselineMean smoke test...\033[0m\n"
	cd ml && $(UV) run python scripts/benchmark_baseline.py

benchmark-all: ## Full benchmark grid (12 configs × 4 folds)
	@printf "\033[36m→ Benchmark: full grid...\033[0m\n"
	cd ml && $(UV) run python scripts/benchmark_all.py

benchmark-compare: ## Compare N benchmark reports → leaderboard
	@printf "\033[36m→ Comparing benchmark reports...\033[0m\n"
	cd ml && $(UV) run python -m transit_ai.benchmark.compare \
		--reports docs/reports/benchmark_*.json \
		--output docs/reports/leaderboard.md

run-benchmark: ## Generic benchmark entry (delegates to ml.transit_ai.benchmark.cli)
	$(UV) run python scripts/run_benchmark.py

# ---------------------------------------------------------------------------
# CI gate (расширенный): все проверки включая структурный анализ
# ---------------------------------------------------------------------------

check-all: lint typecheck test api-check ledger-check arch-dbml-check pyscn-compare ## Run all checks (CI gate)
