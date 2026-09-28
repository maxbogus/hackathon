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
PYTHON  ?= $(REPO_ROOT)/.venv/bin/python
DC      ?= docker compose
MACHINE ?= rtx5060    # rtx5060 | rtx4070_12gb
REPO_ROOT := $(shell pwd)

.PHONY: help install hooks-install up up-minimal up-status up-loadtest down \
        build-backend build-harvester build-ml-pipeline build-all \
        export-images import-images \
        lint format typecheck test test-unit test-int test-pipeline test-root check-all \
        seed inventory inspect-real train-baseline train-xgboost train-gru train-hybrid train-all \
        predict calibrate evaluate submission sweep mc-scenario \
        api-gen api-check fe-gen \
        assistant-test assistant-reasoning mcp-run \
        ledger-add ledger-list ledger-check ledger-export \
        note-from-finding promote handoff handoff-update \
        backlog-ready backlog-list ticket docs         pyscn pyscn-compare pyscn-baseline         arch-dbml arch-dbml-check         benchmark-baseline benchmark-all benchmark-compare         run-benchmark         loadtest-smoke loadtest-baseline loadtest-stress loadtest-spike loadtest-soak loadtest-all loadtest-check check-training-time \
        pipeline-up pipeline-down pipeline-logs pipeline-fetch pipeline-train pipeline-predict pipeline-full pipeline-status pipeline-test \
        external-fetch external-gen external-verify external-show external-all \
        predictions-list predictions-activate predictions-restore-etalon predictions-ingest-csv \
        mlflow-probe mlflow-demo mlflow-runs mlflow-test mlflow-ui mlflow-server mlflow-run \
        mlflow-ingest mlflow-ingest-only mlflow-leaderboard \
        mlops-probe mlops-compare mlops-test mlops-test-full \
        lineage-snapshot-real lineage-snapshot lineage-verify lineage-test \
        dvc-probe dvc-init dvc-add-smoke dvc-add-real dvc-add-artifacts \
        dvc-status dvc-cache-size dvc-test \
        optuna-probe optuna-smoke optuna-run optuna-test \
        airflow-probe airflow-dags-list airflow-tasks-list airflow-test-task airflow-test \
        db-upgrade db-downgrade db-revision db-current db-history \
        blog-stats blog-check

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

install: ## Install all deps (uv sync --all-packages + yarn install)
	@printf "\033[36m→ uv sync --all-packages (apps/* + ml + dev extras)\033[0m\n"
	$(UV) sync --all-packages --extra dev
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
# T-198b: offline-capable build через pre-built wheels. Docker НЕ делает
# uv sync (нет интернета) — wheels копируются с хоста и устанавливаются
# через `pip install --no-index --find-links=/tmp/wheels`.
#
# Workflow для разработчика:
#   make build-all  # генерит apps/{backend,harvester,ml-pipeline}/wheels/
#   make up         # docker compose up -d --build (offline!)
#   make up-status  # проверка что всё 200
#
# Workflow для жюри (offline):
#   make import-images TAR=transit-ai-stack-*.tar
#   make up
#   make up-status

# === Pre-build wheels (offline dependency cache) ===

build-backend: ## Pre-build Python wheels для backend (offline cache) [T-198b]
	@mkdir -p apps/backend/wheels
	$(UV) export --no-dev --no-hashes --frozen \
		--package transit-ai-backend -o apps/backend/requirements.txt
	# Отфильтровать editable (-e ./*) — pip download не может их обработать.
	# Эти пакеты собираются из исходников через `uv sync` в runtime stage.
	grep -v '^-e \.' apps/backend/requirements.txt > apps/backend/requirements.deps.txt
	# БЕЗ --platform: скачиваем wheels для текущей платформы (Linux x86_64).
	# Это работает потому что Docker собирается на той же платформе,
	# и жюри проверяет на той же. (--platform manylinux2014_x86_64 ломается
	# на asyncpg — нет wheel под этот marker для текущего Python.)
	$(UV) run --with "pip>=23.0" pip download --dest apps/backend/wheels/ \
		--python-version 3.12 \
		--only-binary=:all: \
		-r apps/backend/requirements.deps.txt
	@rm -f apps/backend/requirements.deps.txt
	@du -sh apps/backend/wheels/ | awk '{printf "✓ Backend wheels: %s\n", $$1}'

build-harvester: ## Pre-build Python wheels для harvester (offline cache) [T-198b]
	@mkdir -p apps/harvester/wheels
	$(UV) export --no-dev --no-hashes --frozen \
		--package transit-ai-harvester -o apps/harvester/requirements.txt
	grep -v '^-e \.' apps/harvester/requirements.txt > apps/harvester/requirements.deps.txt
	$(UV) run --with "pip>=23.0" pip download --dest apps/harvester/wheels/ \
		--python-version 3.12 \
		--only-binary=:all: \
		-r apps/harvester/requirements.deps.txt
	@rm -f apps/harvester/requirements.deps.txt
	@du -sh apps/harvester/wheels/ | awk '{printf "✓ Harvester wheels: %s\n", $$1}'

build-ml-pipeline: ## Pre-build Python wheels для ml-pipeline (offline cache) [T-198b]
	@mkdir -p apps/ml_pipeline/wheels
	$(UV) export --no-dev --no-hashes --frozen \
		--package transit-ai-ml-pipeline -o apps/ml_pipeline/requirements.txt
	grep -v '^-e \.' apps/ml_pipeline/requirements.txt > apps/ml_pipeline/requirements.deps.txt
	$(UV) run --with "pip>=23.0" pip download --dest apps/ml_pipeline/wheels/ \
		--python-version 3.12 \
		--only-binary=:all: \
		-r apps/ml_pipeline/requirements.deps.txt
	@rm -f apps/ml_pipeline/requirements.deps.txt
	@du -sh apps/ml_pipeline/wheels/ | awk '{printf "✓ ML-pipeline wheels: %s\n", $$1}'

build-all: build-backend build-harvester build-ml-pipeline ## Pre-build все wheels (offline cache) [T-198b]
	@printf "\n\033[32m✓ All wheels готовы для offline build (~430 MB).\033[0m\n"
	@printf "\033[33m→ Следующий шаг: make up (Docker build будет offline)\033[0m\n"

# === Main up target (зависит от build-all) ===

up: build-all ## [T-198b] Pre-build wheels → docker compose up -d --build (offline)
	$(DC) up -d --build
	@$(MAKE) up-status

up-minimal: build-backend ## [T-198] Pre-build backend wheels → docker compose up -d (no Celery) [T-198b]
	$(DC) up -d postgres redis backend frontend
	@printf "\n\033[32m✓ Minimal stack up (без harvester/ml-pipeline workers).\033[0m\n"
	@printf "Frontend: \033[36mhttp://localhost:5173\033[0m\n"
	@printf "\033[33m→ Запустить Celery: make up (или docker compose --profile pipeline up -d)\033[0m\n"

up-status: ## Healthcheck всех сервисов стека (T-198)
	@printf "\n\033[36m=== Stack health ===\033[0m\n"
	@printf "Backend healthz:  "
	@curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/healthz || echo "DOWN"
	@printf "Backend readyz:   "
	@curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/readyz || echo "DOWN"
	@printf "Frontend:         "
	@curl -sf -o /dev/null -w "%{http_code}\n" http://localhost:5173/ || echo "DOWN"
	@printf "Backend /api/v1/predictions/status:\n"
	@curl -sf http://localhost:8000/api/v1/predictions/status | (which jq > /dev/null && jq . || cat) 2>/dev/null || echo "DOWN"
	@printf "\n\033[36m=== Container status ===\033[0m\n"
	@$(DC) ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true

# === Distribution через .tar (Яндекс.Диск) ===

export-images: ## [T-198b] Export всех images в .tar для раздачи через Яндекс.Диск
	@mkdir -p dist/
	@TIMESTAMP=$$(date +%Y%m%d-%H%M); \
		docker save -o dist/transit-ai-stack-$$TIMESTAMP.tar \
			transit-ai-backend:latest \
			transit-ai-frontend:latest \
			transit-ai-harvester:latest \
			transit-ai-ml-pipeline:latest; \
		echo ""; \
		echo "✓ Exported:"; \
		ls -lah dist/transit-ai-stack-$$TIMESTAMP.tar; \
		echo ""; \
		printf "\033[33m→ Залить на Яндекс.Диск: https://disk.yandex.ru/\033[0m\n"; \
		printf "\033[33m→ Расшарить ссылку жюри\033[0m\n"; \
		printf "\033[33m→ Жюри: make import-images TAR=dist/transit-ai-stack-*.tar && make up\033[0m\n"

import-images: ## [T-198b] Import .tar для жюри: make import-images TAR=dist/transit-ai-stack-*.tar
	@if [ -z "$(TAR)" ]; then \
		echo "ERROR: укажите TAR=<path>"; \
		echo "  make import-images TAR=dist/transit-ai-stack-YYYYMMDD-HHMM.tar"; \
		exit 1; \
	fi
	@if [ ! -f "$(TAR)" ]; then \
		echo "ERROR: файл $(TAR) не найден"; \
		exit 1; \
	fi
	docker load -i $(TAR)
	@printf "\n\033[32m✓ Images загружены.\033[0m\n"
	@printf "\033[33m→ Следующий шаг: make up\033[0m\n"

down: ## Stop docker stack
	$(DC) down

logs: ## Tail docker logs
	$(DC) logs -f

# ---------------------------------------------------------------------------
# ML (NOT in Docker) — runs locally via uv
# ---------------------------------------------------------------------------

# WIP (T-019): synthetic gen script not yet implemented
seed: ## Generate synthetic data → data/synthetic/  [WIP: T-019]
	@echo "WIP: pending T-019 (synthetic generator). Skipped."

# WIP: data profiling script not yet implemented
inventory: ## Profile data (numbers, not hearsay) → data/validation_reports/inventory.json (R8)
	$(UV) --directory ml run python scripts/inventory.py

train-baseline: ## Train baseline (mean by hour/day/route)
	$(UV) --directory ml run python scripts/train_baseline.py

# WIP (T-027): XGBoost trainer not yet implemented
train-xgboost: ## Train XGBoost  [WIP: T-027]
	@echo "WIP: pending T-027 (XGBoost trainer). Skipped."

# WIP (T-029): GRU trainer not yet implemented
train-gru: ## Train GRU + attention pooling (from contest/...)  [WIP: T-029]
	@echo "WIP: pending T-029 (GRU trainer). Skipped."

# WIP (T-031): Hybrid trainer not yet implemented
train-hybrid: ## Train hybrid (GRU + LGBM blend in log-space)  [WIP: T-031]
	@echo "WIP: pending T-031 (Hybrid trainer). Skipped."

# WIP (T-027, T-029, T-031): trainers not yet implemented
# train-all: train-baseline train-xgboost train-gru train-hybrid ## Train all models
train-all: ## Train all models  [WIP: only baseline works, others pending]
	@echo "WIP: train-all currently only runs baseline. XGBoost/GRU/Hybrid pending (T-027, T-029, T-031)."
	$(MAKE) train-baseline

predict: ## Generate predictions with active model → predictions/*.parquet
	$(UV) --directory ml run python scripts/predict.py

inspect-real: ## Print hackathon real dataset summary (T-143)
	$(UV) --directory ml run python scripts/inspect_real.py

# T-145: submission pipeline (WAPE-score = 0.8681 baseline на holdout)
submission: ## Generate submission.csv for hackathon platform (10 routes × 61 days × 24h) (T-145)
	$(UV) --directory ml run python scripts/make_submission.py --output $(REPO_ROOT)/predictions/submission.csv

# === T-230: наборы прогнозов (активный набор + эталон) ===

predictions-list: ## Список запусков генерации + активный набор (T-230)
	cd apps/backend && PYTHONPATH=. $(UV) run python -m app.scripts.predictions_admin list

predictions-activate: ## Сделать набор активным: make predictions-activate SUBMISSION_ID=ui-... (T-230)
	@if [ -z "$(SUBMISSION_ID)" ]; then echo "ERROR: укажите SUBMISSION_ID=<id>"; exit 1; fi
	cd apps/backend && PYTHONPATH=. $(UV) run python -m app.scripts.predictions_admin activate --submission-id "$(SUBMISSION_ID)"

predictions-restore-etalon: ## Вернуть эталонный набор активным (T-230)
	cd apps/backend && PYTHONPATH=. $(UV) run python -m app.scripts.predictions_admin restore-etalon

predictions-ingest-csv: ## Загрузить CSV+manifest с диска: make predictions-ingest-csv CSV=predictions/x.csv (T-230)
	@if [ -z "$(CSV)" ]; then echo "ERROR: укажите CSV=predictions/submission_....csv"; exit 1; fi
	cd apps/backend && PYTHONPATH=. $(UV) run python -m app.scripts.predictions_admin ingest-path --csv "$(REPO_ROOT)/$(CSV)"

# T-146: per-route WAPE diagnose
diagnose: ## Per-route / per-hour / per-weekday WAPE diagnose (T-146)
	$(UV) --directory ml run python scripts/diagnose_per_route.py

calibrate: ## Apply per-bucket calibration
	$(UV) --directory ml run python scripts/calibrate.py

evaluate: ## Evaluate all models on holdout → reports/
	$(UV) --directory ml run python scripts/evaluate.py

# WIP: hyperparameter sweep script not yet implemented
sweep: ## Hyperparameter sweep  [WIP]
	@echo "WIP: pending sweep script. Skipped."

# WIP: Monte Carlo scenario script not yet implemented
mc-scenario: ## Run Monte Carlo scenario (1000 iterations)  [WIP]
	@echo "WIP: pending Monte Carlo script. Skipped."

# ---------------------------------------------------------------------------
# API + FRONTEND GENERATION
# ---------------------------------------------------------------------------

api-gen: ## Export OpenAPI from backend → docs/api/openapi.json
	cd apps/backend && PYTHONPATH=. $(UV) run python scripts/export_openapi.py
	@printf "\033[32m✓ OpenAPI exported\033[0m\n"

api-check: ## Validate OpenAPI is up-to-date with backend code
	cd apps/backend && PYTHONPATH=. $(UV) run python scripts/check_openapi.py

fe-gen: ## Generate TS types via Orval → apps/frontend/src/generated/
	cd apps/frontend && $(YARN) orval --config orval.config.ts
	@printf "\033[32m✓ TS types generated\033[0m\n"
lint-frontend-text: ## Grep guard: forbid hardcoded Cyrillic UI strings outside lib/i18n
	@printf "\033[36m→ Checking for hardcoded Cyrillic in apps/frontend/src...\033[0m\n"
	@if grep -rEn '"[А-ЯЁа-яё][А-ЯЁа-яё]+[ А-ЯЁа-яё]*"' \
		apps/frontend/src/components/ apps/frontend/src/pages/ apps/frontend/src/App.tsx 2>/dev/null \
		| grep -v 'lib/i18n/' \
		| grep -v '\.test\.' \
		| grep -vE ':[0-9]+:[[:space:]]*\*' \
		| grep -vE ':[0-9]+:[[:space:]]*//' ; then \
		echo "\033[31m✗ Hardcoded Cyrillic UI strings found -- use t() from lib/i18n (T-141, D-014)\033[0m" ; \
		exit 1 ; \
	else \
		echo "\033[32m✓ No hardcoded UI strings\033[0m" ; \
	fi

frontend-text-check: lint-frontend-text ## Alias

# ---------------------------------------------------------------------------
# QUALITY
# ---------------------------------------------------------------------------

lint: ## ruff + eslint + prettier --check
	$(UV) run ruff check apps/ ml/ mlops/ scripts/
	cd apps/frontend && $(YARN) lint

format: ## ruff format + eslint --fix
	$(UV) run ruff format apps/ ml/ mlops/ scripts/
	$(UV) run ruff check --fix apps/ ml/ mlops/ scripts/
	cd apps/frontend && $(YARN) format

typecheck: ## mypy strict + tsc --noEmit
	$(UV) run mypy apps/backend/app apps/assistant/app apps/mcp/ 2>&1 | tail -30 || true
	cd apps/frontend && $(YARN) typecheck
test: ## pytest (per-app + ml) + vitest (run)
	@printf "\033[36m→ backend pytest\033[0m\n"
	cd $(REPO_ROOT)/apps/backend && $(PYTHON) -m pytest tests/ -q --no-cov
	@printf "\033[36m→ ml pytest\033[0m\n"
	cd $(REPO_ROOT) && $(UV) run pytest ml/tests -q --no-cov
	@printf "\033[36m→ assistant pytest\033[0m\n"
	cd $(REPO_ROOT)/apps/assistant && $(PYTHON) -m pytest tests/ -q --no-cov
	@printf "\033[36m→ mcp pytest\033[0m\n"
	cd $(REPO_ROOT)/apps/mcp && $(PYTHON) -m pytest tests/ -q --no-cov
	@printf "\033[36m→ vitest (frontend)\033[0m\n"
	cd $(REPO_ROOT)/apps/frontend && $(YARN) test:run


# Root tests/ (clinerules, loadtest SLA, dockerfile hardening) — отдельно,
# иначе shadow-конфликт `tests` пакета между apps/*/tests/ и корневой tests/.
test-root: ## pytest for root tests/ (clinerules, loadtest, dockerfile)
	cd $(REPO_ROOT) && $(UV) run pytest tests/ -q --no-cov

# ---------------------------------------------------------------------------
# PIPELINE/CELERY tests — отдельный target, иначе collection error (apps/X/tests
# shadow'ит pytest internal `tests` package; эти тесты требуют запуск из apps/X/).
# ---------------------------------------------------------------------------

test-pipeline: ## pytest for pipeline (harvester/sandbox/ml_pipeline) [WIP: T-193/T-194]
	@printf "\033[36m→ harvester pytest (celery)[0m\n"
	cd $(REPO_ROOT)/apps/harvester && $(UV) run --package transit-ai-harvester python -m pytest tests/ -q --no-cov
	@printf "\033[36m→ sandbox pytest[0m\n"
	cd $(REPO_ROOT)/apps/sandbox && $(PYTHON) -m pytest tests/ -q --no-cov
	@printf "\033[36m→ ml_pipeline pytest (celery)[0m\n"
	cd $(REPO_ROOT)/apps/ml_pipeline && $(UV) run --package transit-ai-ml-pipeline python -m pytest tests/ -q --no-cov

test-unit: test ## Alias for test

test-int: ## Integration tests (requires `make up` first)
	$(UV) run pytest apps/backend/tests -m integration -v --no-cov

check-all: lint typecheck test api-check ledger-check frontend-text-check ## Run all checks (CI gate)

# ---------------------------------------------------------------------------
# KNOWLEDGE CAPTURE
# ---------------------------------------------------------------------------

backlog-ready: ## Top-5 ready tickets by RICE
	$(UV) run python scripts/ready_tickets.py --top 5

backlog-list: ## All tickets sorted by RICE
	$(UV) run python scripts/ready_tickets.py --all

ticket: ## Create new ticket (make ticket ID=T-NNN TITLE="..." PHASE=1 PRIORITY=P1)
	@if [ -z "$(ID)" ] || [ -z "$(TITLE)" ]; then \
		echo "Usage: make ticket ID=T-NNN TITLE=\"your title\" [PHASE=1] [PRIORITY=P1] [EFFORT=4] [TAGS=backend,api]" ; \
		exit 1 ; \
	fi
	$(UV) run python scripts/new_ticket.py \
		--id "$(ID)" \
		--title "$(TITLE)" \
		--phase $(or $(PHASE),1) \
		--priority $(or $(PRIORITY),P1) \
		--effort $(or $(EFFORT),4) \
		--tags "$(or $(TAGS),)"

ledger-add: ## Add decision to ledger (interactive)
	$(UV) run python scripts/ledger.py add

ledger-list: ## Show last 7 days of decisions
	$(UV) run python scripts/ledger.py list --days 7

ledger-export: ## Export ledger to markdown (for presentation)
	$(UV) run python scripts/ledger.py export --output docs/ledger/EXPORT.md

blog-stats: ## Regenerate blog stats → docs/blog/stats.json (docs/blog/)
	$(UV) run python scripts/blog_stats.py

blog-check: ## Blog gate: refresh stats + anonymization grep (docs/blog/)
	$(UV) run python scripts/blog_stats.py --quiet
	@if grep -rniE --exclude='00-*.md' --exclude-dir=sources \
		'МТТЕХ|Богуславск|Баев|Павел|Света|Московск(ий|ого) транспорт|data/real/' docs/blog/ ; then \
		echo "FAIL: в постах найдены запрещённые строки (см. 00-FACTS.md §9-10)"; \
		exit 1; \
	fi
	@echo "blog-check: OK (stats обновлены, посты обезличены)"

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

# WIP: assistant reasoning test script not yet implemented
assistant-reasoning: ## Test reasoning (DeepSeek R1 via OpenRouter)  [WIP]
	@echo "WIP: pending test_reasoning.py. Skipped."

mcp-run: ## Start MCP server (stdio JSON-RPC)
	cd apps/mcp && $(UV) run python -m app.server

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
	@cp .pyscn/report.json ai/analysis/pyscn-baseline.json
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
# MLOPS LAB: MLflow tracking (observability, НЕ источник истины)
# ---------------------------------------------------------------------------
# MLflow НЕ в uv.lock и НЕ в Docker: ставится эфемерно через `uv run --with`.
# Store по умолчанию: sqlite:///<repo>/mlruns.db (file-store в MLflow 3 переведён
# в maintenance mode и падает без MLFLOW_ALLOW_FILE_STORE=true — см. F-112).
# Артефакты: file:<repo>/mlartifacts. Контракты (JSON Schema, ml/artifacts/*/meta.json,
# predictions/*.json) остаются источником истины. См. docs/MLFLOW.md.

MLFLOW_PKG      ?= mlflow>=2.16
MLFLOW_PORT     ?= 5000
MLFLOW_HINT_ENV  = MLFLOW_DISABLE_AGENT_HINT=1

mlflow-probe: ## Версия MLflow (эфемерная установка, uv.lock не трогаем)
	@$(MLFLOW_HINT_ENV) $(UV) run --with "$(MLFLOW_PKG)" python -c "import importlib.metadata as m; print('mlflow', m.version('mlflow'))"

mlflow-demo: ## Демо tracking: 3 конфига x 4 fold -> раны в mlruns.db
	@$(MLFLOW_HINT_ENV) $(UV) run --with "$(MLFLOW_PKG)" python ml/scripts/mlflow_demo.py

mlflow-runs: ## Список ранов из локального store (LIMIT=N)
	@$(MLFLOW_HINT_ENV) $(UV) run --with "$(MLFLOW_PKG)" python ml/scripts/mlflow_runs.py

mlflow-test: ## Тесты трекера в MLflow-режиме (pytest + mlflow эфемерно)
	@$(MLFLOW_HINT_ENV) $(UV) run --with pytest --with pytest-asyncio --with "$(MLFLOW_PKG)" python -m pytest ml/tests/test_mlflow_tracker.py -q

mlflow-ui: ## MLflow UI -> http://127.0.0.1:$(MLFLOW_PORT) (sqlite store)
	@$(MLFLOW_HINT_ENV) $(UV) run --with "$(MLFLOW_PKG)" mlflow ui --backend-store-uri "sqlite:///$(REPO_ROOT)/mlruns.db" --port $(MLFLOW_PORT)

mlflow-server: ## Local tracking server (sqlite) -> MLFLOW_TRACKING_URI=http://127.0.0.1:$(MLFLOW_PORT)
	@$(MLFLOW_HINT_ENV) $(UV) run --with "$(MLFLOW_PKG)" mlflow server --host 127.0.0.1 --port $(MLFLOW_PORT) --backend-store-uri "sqlite:///$(REPO_ROOT)/mlruns.db" --default-artifact-root "file:$(REPO_ROOT)/mlartifacts"

mlflow-run: ## Любой ml/-скрипт под tracking: make mlflow-run SCRIPT=scripts/train_xgboost.py ARGS="--model-id x"
	@$(MLFLOW_HINT_ENV) $(UV) --directory ml run --with "$(MLFLOW_PKG)" python $(SCRIPT) $(ARGS)

mlops-probe: ## Probe all 4 MLOps tools ephemerally (versions + filesystem support)
	@bash $(REPO_ROOT)/mlops/probes/dvc_probe.sh

mlops-compare: ## Show MLOPS_LAB.md (the comparison report)
	@cat $(REPO_ROOT)/mlops/MLOPS_LAB.md

# ---------------------------------------------------------------------------
# MLOPS LAB: тесты лаборатории (изолированы от `make test`)
# ---------------------------------------------------------------------------
# mlops/tests/ НЕ входит в testpaths (pyproject.toml): тесты лаборатории требуют
# эфемерных пакетов (optuna/dvc/apache-airflow) и сети, поэтому `make test`
# остаётся герметичным и быстрым (F-125). Контур A — mlops-test (герметичный),
# полный контур (эфемерные зависимости + сеть) — mlops-test-full.

mlops-test: ## MLOps lab tests: герметичный контур (AST-структура DAG, skip эфемерных)
	$(UV) run --with pytest --with pytest-asyncio python -m pytest mlops/tests/ -q --no-cov

mlops-test-full: ## MLOps lab tests: + эфемерные optuna/dvc/apache-airflow (нужна сеть)
	$(UV) run --with pytest --with pytest-asyncio --with optuna --with dvc --with apache-airflow python -m pytest mlops/tests/ -q --no-cov


mlflow-ingest: ## Idempotent ingest 81 sources (23 artifacts + 53 manifests + 5 benchmarks)
	@$(MLFLOW_HINT_ENV) $(UV) --directory ml run --with "$(MLFLOW_PKG)" python scripts/mlflow_ingest.py

mlflow-ingest-only: ## Ingest only one kind: make mlflow-ingest-only KIND=artifacts|manifests|benchmarks
	@$(MLFLOW_HINT_ENV) $(UV) --directory ml run --with "$(MLFLOW_PKG)" python scripts/mlflow_ingest.py --only $(KIND)

mlflow-leaderboard: ## Drift-table: local holdout vs platform score, top-30 submissions
	@$(MLFLOW_HINT_ENV) $(UV) --directory ml run --with "$(MLFLOW_PKG)" python scripts/mlflow_leaderboard.py --top 30
# ---------------------------------------------------------------------------
# MLOPS LAB: Lineage-lite (sha256 + manifest для 8 GB датасетов)
# ---------------------------------------------------------------------------
# Streaming sha256 (1 MB chunks) — заменяет hash_dataframe() из training.registry.py,
# который pickle'ит DataFrame в RAM и OOM-ит на 8 GB train.csv.
# Snapshot пишется в docs/lineage/datasets/*.json (маленький, коммитится в git).
# train_xgboost/gru/catboost.py подтягивают sha256 из snapshot в meta.json.

LINEAGE_DATASET ?= $(REPO_ROOT)/data/real/train.csv
LINEAGE_OUTPUT ?= $(REPO_ROOT)/docs/lineage/datasets/real_ridership.json

lineage-snapshot-real: ## sha256+size+mtime+rows для data/real/train.csv (8 GB, ~23 сек)
	$(UV) run --directory ml python scripts/lineage_snapshot.py \
		--input $(LINEAGE_DATASET) --output $(LINEAGE_OUTPUT)

lineage-snapshot: ## Снять snapshot для произвольного файла: make lineage-snapshot INPUT=... OUTPUT=...
	$(UV) run --directory ml python scripts/lineage_snapshot.py --input $(INPUT) --output $(OUTPUT)

lineage-verify: ## Проверить целостность: sha256 в meta.json всех артефактов == snapshot (если есть)
	@echo "lineage-verify: проверка, что train_data_hash в ml/artifacts/*/meta.json == sha256 в snapshot"
	@if [ ! -f $(LINEAGE_OUTPUT) ]; then echo "ERROR: snapshot $(LINEAGE_OUTPUT) missing"; exit 1; fi
	@EXPECTED=$$($(UV) run --directory ml python -c "import json; print(json.load(open('$(LINEAGE_OUTPUT)'))['sha256'])") \
	&& echo "expected=$$EXPECTED" \
	&& HIT=0; TOTAL=0; \
	for meta in $(REPO_ROOT)/ml/artifacts/*/meta.json; do \
		  [ -f $$meta ] || continue; \
		  TOTAL=$$((TOTAL+1)); \
		  ACTUAL=$$($(UV) run --directory ml python -c "import json,sys; print(json.load(open('$$meta')).get('train_data_hash',''))"); \
		  if [ "$$ACTUAL" = "$$EXPECTED" ]; then HIT=$$((HIT+1)); \
		  else echo "  $$meta: $$ACTUAL (≠ expected)"; fi; \
	done; \
	echo "matched=$$HIT/$$TOTAL (остальные имеют train_data_hash='pending' — не обучены на этой версии train.csv)"

lineage-test: ## Тесты lineage пакета (hashing + snapshot, +pytest эфемерно)
	$(UV) run --directory ml --with pytest --with pytest-asyncio python -m pytest tests/test_lineage_hashing.py tests/test_lineage_snapshot.py -q


# ---------------------------------------------------------------------------
# MLOPS LAB: DVC (dataset tracking, hardlink cache)
# ---------------------------------------------------------------------------
# DVC is NOT in uv.lock: installed ephemerally via uv run --with dvc.
# cache.type=hardlink + cache.dir=mlops/dvc-cache on ext4 = 0 GB overhead.
# Verified: train.csv inode in repo == inode in cache, link count = 2.
# .dvc/ and *.dvc are committed; .dvc/cache/ is in .gitignore.

dvc-probe: ## DVC version + filesystem support (hardlink/reflink)
	@bash $(REPO_ROOT)/mlops/probes/dvc_probe.sh

dvc-init: ## dvc init --no-scm + cache.type=hardlink + cache.dir=mlops/dvc-cache
	@if [ -d $(REPO_ROOT)/.dvc ]; then echo "already initialized"; exit 0; fi
	$(UV) run --with dvc dvc init --no-scm
	$(UV) run --with dvc dvc cache dir mlops/dvc-cache
	$(UV) run --with dvc dvc config cache.type hardlink

dvc-add-smoke: ## dvc add data/external/normalized/manifest.json (smoke 5 KB, ~2s)
	$(UV) run --with dvc dvc add data/external/normalized/manifest.json

dvc-add-real: ## dvc add data/real/*.csv (~18s for 8 GB train.csv + ~6s for 2 GB test.csv)
	$(UV) run --with dvc dvc add data/real/train.csv data/real/test.csv

dvc-add-artifacts: ## dvc add ml/artifacts/*/model.pkl (~25s, 23 files)
	@for pkl in ml/artifacts/*/model.pkl; do $(UV) run --with dvc dvc add "$$pkl"; done

dvc-status: ## dvc status (data up-to-date?)
	$(UV) run --with dvc dvc status

dvc-cache-size: ## DVC cache size (close to 0 if hardlink works)
	@du -sh $(REPO_ROOT)/mlops/dvc-cache 2>/dev/null || echo "no cache yet"

dvc-test: ## DVC probe tests (script exists + version >= 3.0)
	$(UV) run --with pytest --with pytest-asyncio python -m pytest mlops/tests/test_dvc_probe.py -q --no-cov


# ---------------------------------------------------------------------------
# MLOPS LAB: Optuna (TPE hyperparameter search, sqlite storage)
# ---------------------------------------------------------------------------
# Optuna is NOT in uv.lock: installed ephemerally via uv run --with optuna.
# Study storage: sqlite at mlops/optuna/studies/xgboost_route.db (gitignored).
# R6 budget: n_trials=15, timeout=1800s. Smoke: 2 trials, <5 sec.
# Surrogate objective for smoke; real objective via build_real_objective(df).

optuna-probe: ## Optuna version ephemerally
	@$(UV) run --with optuna python -c "import optuna; print('optuna', optuna.__version__)"

optuna-smoke: ## 2-trial smoke (CI, <5s, deterministic seed=42)
	@cd $(REPO_ROOT) && $(UV) run --with optuna python -c \
		"from mlops.optuna.study_xgboost import create_study; s = create_study(n_trials=2); print(f\"smoke OK: best={s.best_value:.4f}, n_trials={len(s.trials)}\")"

optuna-run: ## 15-trial TPE run (~30 sec on real XGBoost, R6 budget)
	@cd $(REPO_ROOT) && $(UV) run --with optuna --with xgboost --with polars python -c \
		"from mlops.optuna.study_xgboost import create_study; s = create_study(n_trials=15, timeout=1800); print(f\"best={s.best_value:.4f}, params={s.best_params}\")"

optuna-test: ## Optuna tests (storage, determinism, smoke)
	$(UV) run --with pytest --with pytest-asyncio --with optuna python -m pytest mlops/tests/test_optuna_objective.py -q --no-cov


# ---------------------------------------------------------------------------
# MLOPS LAB: Airflow (DAG orchestration, ephemeral via uv run --with)
# ---------------------------------------------------------------------------
# Airflow is NOT in uv.lock: installed ephemerally via uv run --with apache-airflow.
# AIRFLOW_HOME=mlops/airflow_home (gitignored), DAG bundle = mlops/dags/.
# Manual trigger only (schedule=None); `airflow tasks test <dag> <task> <date>`
# for single-task smoke (no scheduler).

AIRFLOW_HOME ?= $(REPO_ROOT)/mlops/airflow_home

airflow-probe: ## Airflow version ephemerally + db migrate
	@AIRFLOW_HOME=$(AIRFLOW_HOME) $(UV) run --with apache-airflow airflow version
	@AIRFLOW_HOME=$(AIRFLOW_HOME) $(UV) run --with apache-airflow airflow db migrate 2>&1 | tail -2

airflow-dags-list: ## List DAGs in mlops/dags
	@AIRFLOW_HOME=$(AIRFLOW_HOME) $(UV) run --with apache-airflow airflow dags list 2>&1 | grep -E "dag_id|transit" | head -10

airflow-tasks-list: ## List tasks in transit_side_car DAG
	@AIRFLOW_HOME=$(AIRFLOW_HOME) $(UV) run --with apache-airflow airflow tasks list transit_side_car 2>&1 | tail -10

airflow-test-task: ## Test single task: make airflow-test-task TASK=lineage_snapshot
	@AIRFLOW_HOME=$(AIRFLOW_HOME) $(UV) run --with apache-airflow airflow tasks test transit_side_car $(TASK) 2026-01-01 2>&1 | tail -3

airflow-test: ## Airflow DAG structure tests (AST-контур + DAG-импорт в apache-airflow)
	$(UV) run --with pytest --with pytest-asyncio --with apache-airflow python -m pytest mlops/tests/test_airflow_dag_structure.py -q --no-cov

# CI gate (расширенный): все проверки включая структурный анализ
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# LOAD TESTING (k6) — T-160..T-165
# ---------------------------------------------------------------------------
# R6 hackathon-rules: p95 ≤ 2000ms, error_rate ≤ 1%.
# k6 запускается в Docker (профиль loadtest, см. docker-compose.yml).
# SLA gate: scripts/check_load_sla.py парсит JSON и валидирует thresholds.

# === Smoke (CI gate, 10 VU × 30s) ===
loadtest-smoke: ## 10 VU × 30s smoke (R6 SLA p95 ≤ 2s) — CI gate
	@mkdir -p docs/load-profiles/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	docker compose --profile loadtest run --rm \
		-e K6_WEB_DASHBOARD_EXPORT=/reports/smoke_$$TIMESTAMP.html \
		-e K6_WEB_DASHBOARD_OPEN=false \
		k6 run /scripts/smoke_dispatcher.js
	@printf "\n\033[32m✓ Smoke test complete. Reports in docs/load-profiles/reports/\033[0m\n"

# === Baseline (50 VU × 5 min, нормальная нагрузка ЕДЦ) ===
loadtest-baseline: ## 50 VU × 5 min baseline load test (R6 SLA p95 ≤ 2s)
	@mkdir -p docs/load-profiles/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	docker compose --profile loadtest run --rm \
		-e K6_WEB_DASHBOARD_EXPORT=/reports/baseline_$$TIMESTAMP.html \
		-e K6_WEB_DASHBOARD_OPEN=false \
		k6 run /scripts/baseline_dispatcher.js
	@printf "\n\033[32m✓ Baseline test complete\033[0m\n"

# === Stress (100 VU × 3 min, по запросу пользователя) ===
loadtest-stress: ## 100 VU × 3 min stress test (R6 допуск p95 ≤ 3s)
	@mkdir -p docs/load-profiles/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	docker compose --profile loadtest run --rm \
		-e K6_WEB_DASHBOARD_EXPORT=/reports/stress_$$TIMESTAMP.html \
		-e K6_WEB_DASHBOARD_OPEN=false \
		k6 run /scripts/stress_dispatcher.js
	@printf "\n\033[32m✓ Stress test complete\033[0m\n"

# === Spike (резкий скачок 10→200 VU) ===
loadtest-spike: ## Spike test: 10 VU → 200 VU за 10 сек (resilience check)
	@mkdir -p docs/load-profiles/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	docker compose --profile loadtest run --rm \
		-e K6_WEB_DASHBOARD_EXPORT=/reports/spike_$$TIMESTAMP.html \
		-e K6_WEB_DASHBOARD_OPEN=false \
		k6 run /scripts/spike_dispatcher.js
	@printf "\n\033[32m✓ Spike test complete\033[0m\n"

# === Soak (30 VU × 30 min, memory/connection leak detection) ===
loadtest-soak: ## 30 VU × 30 min soak test (memory leak detection)
	@mkdir -p docs/load-profiles/reports
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	docker compose --profile loadtest run --rm \
		-e K6_WEB_DASHBOARD_EXPORT=/reports/soak_$$TIMESTAMP.html \
		-e K6_WEB_DASHBOARD_OPEN=false \
		k6 run /scripts/soak_dispatcher.js
	@printf "\n\033[32m✓ Soak test complete\033[0m\n"

# === Run all profiles sequentially ===
loadtest-all: loadtest-smoke loadtest-baseline loadtest-stress loadtest-spike ## Run smoke + baseline + stress + spike
	@printf "\n\033[32m✓ All load tests complete (soak excluded — run manually)\033[0m\n"

# === SLA gate: parse latest JSON, verify thresholds ===
loadtest-check: ## Parse latest k6 JSON, verify R6 SLA (p95 ≤ 2s, err ≤ 1%)
	$(UV) run python scripts/check_load_sla.py --latest

# === up-loadtest: поднять backend + k6 контейнер ===
up-loadtest: ## Run backend + k6 load tester (profile: loadtest)
	$(DC) --profile loadtest up -d
	@printf "\n\033[32m✓ Stack + k6 up. Backend: http://localhost:8000 | k6 dashboard: http://localhost:5665\033[0m\n"

# === Training time gate (R6 ≤ 60 мин) ===
check-training-time: ## R6 gate: суммарное время обучения ML ≤ 60 мин
	$(UV) run python scripts/check_training_time.py

check-all: lint typecheck test api-check ledger-check frontend-text-check arch-dbml-check pyscn-compare ## Run all checks (CI gate)

# ────────────────────────────────────────────────────────────────────────────
# CELERY PIPELINE (T-193)
# ────────────────────────────────────────────────────────────────────────────
# Три сервиса: harvester (качает JSON), ml-pipeline (train+predict).
# Поднимаются через профиль `pipeline`, чтобы не запускать в dev по умолчанию.

pipeline-up: ## Start Celery workers (harvester + ml-pipeline, profile: pipeline)
	$(DC) --profile pipeline up -d
	@printf "\n\033[32m✓ Pipeline workers up.\n  - harvester: harvester.fetch_* tasks\n  - ml-pipeline: ml_pipeline.train_xgboost / predict_window / full_pipeline\n  Broker: redis://localhost:6379/1\033[0m\n"

pipeline-down: ## Stop pipeline workers
	$(DC) --profile pipeline down

pipeline-logs: ## Tail pipeline logs (both workers)
	$(DC) --profile pipeline logs -f harvester ml-pipeline

# === Trigger tasks (Eager mode: запускает через .apply() вместо брокера) ===

pipeline-fetch: ## Собрать все внешние источники → normalized/*.json + manifest (T-231)
	$(UV) --directory apps/harvester run python -m app.build --source all

# === T-231: external ETL (шаг 0) — raw → training-ready JSON ===
# Пайплайн: external-fetch (online, dev) → external-gen (offline) → external-verify.
# Артефакты: data/external/normalized/*.json + manifest.json (sha256 каждого).

external-fetch: ## Обновить raw из Open-Meteo/Overpass (dev only, R4: не в runtime)  [T-231]
	HARVESTER_MODE=online $(UV) --directory apps/harvester run python -c "from app.tasks import fetch_all; import json; print(json.dumps(fetch_all.apply().get(), indent=2, ensure_ascii=False))"

external-gen: ## Сгенерировать normalized/*.json + manifest.json из raw (шаг 0, offline)  [T-231]
	$(UV) --directory apps/harvester run python -m app.build --source all

external-verify: ## Проверить артефакты против манифеста (sha256 + rows_count + schema)  [T-231]
	$(UV) --directory apps/harvester run python -m app.build --verify

external-show: ## Таблица источников: строки / sha256 / потребитель  [T-231]
	$(UV) --directory apps/harvester run python -m app.build --show

external-all: external-gen external-verify ## gen + verify (offline)  [T-231]

pipeline-train: ## Trigger ml_pipeline.train_xgboost via broker
	$(UV) --directory apps/ml_pipeline run python -c "from app.celery_app import celery_app; r = celery_app.send_task('ml_pipeline.train_xgboost'); print('Task:', r.id); print('Result:', r.get(timeout=600))"

pipeline-predict: ## Trigger ml_pipeline.predict_window with default params
	$(UV) --directory apps/ml_pipeline run python -c "from app.celery_app import celery_app; r = celery_app.send_task('ml_pipeline.predict_window', kwargs={'model_id':'xgboost_v_default'}); print('Task:', r.id); print('Result:', r.get(timeout=600))"

pipeline-full: ## Trigger full_pipeline (train → predict) via Celery broker  [T-198]
	$(UV) --directory apps/ml_pipeline run python -c "from app.celery_app import celery_app; r = celery_app.send_task('ml_pipeline.full_pipeline'); print('Task ID:', r.id); print('Waiting for result (timeout=1800s)...'); print('Result:', r.get(timeout=1800))"

pipeline-status: ## Show active Celery tasks (ml-pipeline worker status)  [T-198]
	@$(DC) exec ml-pipeline celery -A app.celery_app:celery_app inspect active 2>/dev/null || echo "ml-pipeline worker not running"

pipeline-test: ## Run unit tests for harvester + ml_pipeline
	$(UV) --directory apps/harvester run pytest tests/ -v --no-cov
	$(UV) --directory apps/ml_pipeline run pytest tests/ -v --no-cov

# ────────────────────────────────────────────────────────────────────────────
# DATABASE MIGRATIONS (T-194)
# ────────────────────────────────────────────────────────────────────────────
# alembic для PostgreSQL (TimescaleDB). Используется в docker stack и локально.

db-upgrade: ## Apply all alembic migrations (need postgres running)
	cd apps/backend && TRANSIT_AI_DATABASE_URL=$${TRANSIT_AI_DATABASE_URL:-postgresql+asyncpg://transit:transit_dev_only@localhost:5432/transit_dev} \
		$(UV) run alembic upgrade head

db-downgrade: ## Rollback last alembic migration
	cd apps/backend && TRANSIT_AI_DATABASE_URL=$${TRANSIT_AI_DATABASE_URL:-postgresql+asyncpg://transit:transit_dev_only@localhost:5432/transit_dev} \
		$(UV) run alembic downgrade -1

db-revision: ## Generate new alembic migration (use MSG="...")
	cd apps/backend && $(UV) run alembic revision --autogenerate -m "$(MSG)"

db-current: ## Show current alembic revision
	cd apps/backend && $(UV) run alembic current

db-history: ## Show alembic migration history
	cd apps/backend && $(UV) run alembic history --verbose


# ────────────────────────────────────────────────────────────────────────────
# GigaChat PROJECT AUDIT (T-AUDIT) — собирает тексты проекта и шлёт в GigaChat-2
# ────────────────────────────────────────────────────────────────────────────
# Требует GIGACHAT_CREDENTIALS в env (base64 client_id:client_secret).
# Без ключа работает только --dry-run (сборка без API-вызовов).
# Output: docs/audit/gigachat_audit_<ts>.md

audit-gigachat: ## Собрать тексты проекта + аудит через GigaChat-2 → docs/audit/  [WIP: T-AUDIT]
	@if [ -z "$$GIGACHAT_CREDENTIALS" ]; then \
		echo "WARN: GIGACHAT_CREDENTIALS не установлен. Запускаю --dry-run."; \
		$(PYTHON) scripts/gigachat_audit.py --dry-run; \
	else \
		$(PYTHON) scripts/gigachat_audit.py --max-chars 4000 --limit 80; \
	fi

audit-gigachat-smoke: ## Smoke test (1 чанк по user_found) — проверить OAuth+chat pipeline
	@if [ -z "$$GIGACHAT_CREDENTIALS" ]; then \
		echo "ERROR: GIGACHAT_CREDENTIALS не установлен. Экспортируйте ключ:"; \
		echo "  export GIGACHAT_CREDENTIALS=\$$(grep GIGACHAT_CREDENTIALS ~/Repositories/lawcopilot/.env | cut -d= -f2)"; \
		exit 1; \
	fi
	$(PYTHON) scripts/gigachat_audit.py --limit 1 --category user_found --output /tmp/gigachat_smoke.md
	@echo "OK: /tmp/gigachat_smoke.md"

audit-gigachat-full: ## Полный аудит без лимита (418 чанков, ~14 мин) — для глубокого pre-submission review
	@if [ -z "$$GIGACHAT_CREDENTIALS" ]; then \
		echo "ERROR: GIGACHAT_CREDENTIALS не установлен"; exit 1; \
	fi
	$(PYTHON) scripts/gigachat_audit.py --max-chars 4000
