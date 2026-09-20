# 17-pyscn-quality-gate.md — pyscn: structural quality gate

## Что это

[pyscn](https://github.com/ludo-technologies/pyscn) — structural code analyzer
(CFG + APTED): complexity, dead code, clones, coupling, architecture compliance.

**Цель:** ловить регресс качества кода ДО того, как ruff начнёт ругаться на стили,
а mypy — на типы. pyscn ловит **архитектурный долг**: high coupling, code clones,
недостижимый код, циклические импорты, нарушения layering rules.

**Версия:** pyscn 1.32.0 (CLI + MCP server).
**Источник шаблона:** lawcopilot-api/ai/skills/pyscn-quality-gate.md.

## Установка

```bash
uv tool install pyscn     # ставит бинарь в ~/.local/bin/pyscn
pyscn --version           # проверить
```

CI/PySCN-MCP доступны через `uv run pyscn-mcp` (stdio JSON-RPC сервер для Cline).

## Где живёт конфиг

`./.pyscn.toml` в корне репо:

```toml
[tool.pyscn]
clone_threshold = 0.65
cognitive_complexity_threshold = 25
function_sloc_critical_threshold = 100
function_sloc_warn_threshold = 50
min_cbo = 0
nesting_depth_threshold = 7
low_threshold = 9
medium_threshold = 19
min_severity = "info"

[tool.pyscn.dead_code]
enabled = true
min_severity = "warning"

[tool.pyscn.clone]
enabled = true

[tool.pyscn.coupling]
enabled = true

[tool.pyscn.deps]
enabled = true

[tool.pyscn.architecture]
enabled = true
rules = ["apps/backend->apps/backend.forecast", "ml->apps/backend"]
```

## Thresholds (baseline 2026-09-20)

| Metric | Baseline | Target | Hard limit (CI) |
|---|---|---|---|
| Health score | 68 | 80 | 55 |
| Complexity avg | 4.25 | ≤ 3.0 | 6.0 |
| Cognitive complexity avg | 6.5 | ≤ 5.0 | 10.0 |
| Duplication % | 56.5* | ≤ 25 | 40 |
| High coupling | 0 | 0 | 5 |
| Dead code | 0 | 0 | 0 |
| High complexity count | 2 | ≤ 3 | 10 |

*Baseline duplication завышен из-за повторяющихся docstring в `__init__.py`. Снизится по мере наполнения кодом.

## Команды Makefile

```bash
make pyscn            # pyscn analyze apps/ ml/ scripts/ → .pyscn/report.{json,html}
make pyscn-compare    # delta vs baseline → exit 1 если регресс
make pyscn-baseline   # перезаписать baseline (использовать редко, RICE>5)
```

## CI gate

`make pyscn-compare` вызывается из `.githooks/pre-push` ПОСЛЕ mypy.
Если delta complexity > 0.5 или delta duplication > 3% или health score упал > 5 —
push блокируется.

## MCP интеграция

`pyscn-mcp` (stdio JSON-RPC) — подключается к Cline через `.clinerules/12-mcp-draft.md`
и `apps/mcp/mcp.json`. Инструменты: `analyze_code`, `check_complexity`, `detect_clones`.

Подключение (для локального Cline):

```json
{
  "mcpServers": {
    "pyscn": {
      "command": "uv",
      "args": ["tool", "run", "--from", "pyscn", "pyscn-mcp"]
    }
  }
}
```

## Когда запускать

| Событие | Триггер |
|---|---|
| Локально перед push | `make pyscn-compare` |
| В pre-push hook | автоматически (через `.githooks/pre-push`) |
| В CI | на каждый push (GitHub Actions — будущее T-088) |
| Ручной аудит | `pyscn analyze apps/ --html` → открыть `.pyscn/reports/analyze_<date>.html` |

## Что делать с регрессом

1. **`duplication %` растёт** → extract common code в shared module, например `ml/transit_ai/_common.py`
2. **`high_coupling` появились классы** → применить DI (Depends в FastAPI, factory в ML)
3. **`complexity_avg > 5`** → разбить большие функции (Cyclomatic complexity > 10 = red flag)
4. **`dead_code_count > 0`** → удалить неиспользуемые функции/модули
5. **`arch_compliance < 100`** → нарушен layering rule, исправить импорты

## Не делать

- ❌ Запускать `pyscn` на сгенерированных файлах (`apps/frontend/src/generated/`)
- ❌ Коммитить `.pyscn/reports/` (в `.gitignore`)
- ❌ Менять baseline без ADR (это сигнал «качество упало, и мы согласны»)
- ❌ Игнорировать `critical_dead_code` — это 100% баг или удалённый feature
