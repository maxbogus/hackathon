# 14-decisions-ledger.md — Фиксация решений в ledger

## Зачем

Каждое значимое решение (RICE > 5 или меняет архитектуру) фиксируется
в `docs/ledger/decisions.jsonl` (append-only JSON Lines).

**Цели:**
1. Не переучивать агента в каждой сессии — решения накапливаются
2. Использовать для презентации (`make ledger-export`)
3. Обоснование архитектурных выборов (почему ML вне Docker, почему LiteLLM и т.д.)
4. История для потомков (включая самих себя через месяц)

## Формат записи

**Файл:** `docs/ledger/decisions.jsonl`
**Одна строка = один JSON**, формат:

```json
{"id": "D-001", "ts": "2026-09-20T15:30:00Z", "title": "ML обучается скриптами, не в Docker", "context": "На хакатоне три машины с разными GPU (RTX 5060, 4070 12GB). Docker ломает GPU-доступ. Артефакты моделей нужны как файлы для переключения.", "decision": "ML в ml/ как скрипты через uv run. Артефакты на диск в ml/artifacts/<id>/{meta.json, model.pkl, calibration.json}. Backend читает через forecast/loader.py с валидацией по JSON Schema.", "alternatives": ["ML в Docker с nvidia-container-runtime (отказано: сложно, ломается на Mac)", "ML в виде HTTP-сервиса (отказано: оверкилл, latency)"], "consequences": ["+ Быстрый цикл разработки", "+ Версионирование через meta.json", "+ Переключение модели = atomic rename", "- Нет изоляции (нужно следить за env)"], "tickets": ["T-023", "T-038"], "tags": ["architecture", "ml", "deployment"], "links": [".clinerules/10-ml-as-scripts.md"]}
```

## Когда писать

| Решение | RICE > 5? | Записать? |
|---|---|---|
| ML вне Docker | да (RICE 12) | ✅ D-001 |
| Использовать lawcopilot-паттерн | да (RICE 8) | ✅ D-002 |
| MapProvider strategy OSM ↔ Yandex | да (RICE 7) | ✅ D-003 |
| Добавить ruff правило X | нет (RICE 2) | ❌ |
| Поменять цвет кнопки | нет (RICE 1) | ❌ |

**Правило:** если решение **меняет архитектуру**, **отменяет другой тикет**,
или **RICE > 5** — записывать обязательно.

## Команды

```bash
# Интерактивное добавление (с подсказками)
make ledger-add

# Список последних 7 дней
make ledger-list

# Экспорт в markdown (для презентации)
make ledger-export

# Проверка при merge (вызывается из pre-commit)
make ledger-check
```

## Скрипт `scripts/ledger.py`

Уже будет создан в Phase 0 (T-013). Базовая структура:

```python
"""CLI для работы с docs/ledger/{decisions,findings}.jsonl."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

LEDGER_DIR = Path("docs/ledger")
DECISIONS = LEDGER_DIR / "decisions.jsonl"
FINDINGS = LEDGER_DIR / "findings.jsonl"


def cmd_add(args: argparse.Namespace) -> int:
    """Интерактивно добавляет запись через stdin (json) или prompts."""
    if args.from_file:
        record = json.loads(Path(args.from_file).read_text())
    else:
        record = {
            "id": args.id or f"D-{next_id():03d}",
            "ts": datetime.now(timezone.utc).isoformat(),
            "title": input("Title: "),
            "context": input("Context (\\n for multi-line, '.' to finish):\n"),
            "decision": input("Decision: "),
            "alternatives": input("Alternatives (comma-separated): ").split(","),
            "consequences": input("Consequences (comma-separated): ").split(","),
            "tickets": input("Tickets (T-NNN,T-NNN): ").split(","),
            "tags": input("Tags (comma-separated): ").split(","),
        }
    record["ts"] = record.get("ts", datetime.now(timezone.utc).isoformat())
    record["id"] = record.get("id") or f"D-{next_id():03d}"

    with DECISIONS.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"✅ Added {record['id']}: {record['title']}")
    return 0


def next_id() -> int:
    """Следующий свободный id D-NNN или F-NNN."""
    if not DECISIONS.exists():
        return 1
    ids = []
    for line in DECISIONS.read_text().splitlines():
        if line.strip():
            ids.append(int(json.loads(line)["id"].split("-")[1]))
    return max(ids, default=0) + 1


def cmd_list(args: argparse.Namespace) -> int:
    """Показать последние N дней."""
    if not DECISIONS.exists():
        print("Ledger пуст")
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    for line in DECISIONS.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        ts = datetime.fromisoformat(rec["ts"])
        if ts < cutoff:
            continue
        print(f"\n{rec['id']} [{rec['ts']}] {rec['title']}")
        print(f"  Context: {rec['context'][:100]}...")
        print(f"  Decision: {rec['decision'][:100]}...")
        print(f"  Tickets: {', '.join(rec.get('tickets', []))}")
        print(f"  Tags: {', '.join(rec.get('tags', []))}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Экспорт в markdown."""
    output = Path(args.output)
    lines = ["# Decision Ledger Export", "", f"_Generated: {datetime.now(timezone.utc).isoformat()}_", ""]
    for line in DECISIONS.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        lines.append(f"## {rec['id']}: {rec['title']}")
        lines.append(f"_{rec['ts']}_")
        lines.append("")
        lines.append(f"**Context:** {rec['context']}")
        lines.append("")
        lines.append(f"**Decision:** {rec['decision']}")
        lines.append("")
        lines.append(f"**Alternatives:** {', '.join(rec.get('alternatives', []))}")
        lines.append("")
        lines.append(f"**Consequences:**")
        for c in rec.get("consequences", []):
            lines.append(f"- {c}")
        lines.append("")
        if rec.get("tickets"):
            lines.append(f"**Tickets:** {', '.join(rec['tickets'])}")
            lines.append("")
        if rec.get("links"):
            lines.append(f"**Links:** {', '.join(rec['links'])}")
            lines.append("")
        lines.append("---")
        lines.append("")
    output.write_text("\n".join(lines))
    print(f"✅ Exported to {output}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Pre-commit: проверить что для merge в main есть запись в ledger.
    Вызывается из .githooks/pre-commit.
    """
    # Простая версия: проверить что за последние 7 дней есть хотя бы 1 запись
    if not DECISIONS.exists() or DECISIONS.stat().st_size == 0:
        print("⚠ Ledger пуст. Добавьте решение: make ledger-add")
        return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Добавить решение")
    p_add.add_argument("--id", help="ID (например D-001)")
    p_add.add_argument("--from-file", help="JSON файл с записью")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="Список за период")
    p_list.add_argument("--days", type=int, default=7)
    p_list.set_defaults(func=cmd_list)

    p_export = sub.add_parser("export", help="Экспорт в markdown")
    p_export.add_argument("--output", required=True)
    p_export.set_defaults(func=cmd_export)

    p_check = sub.add_parser("check", help="Pre-commit проверка")
    p_check.set_defaults(func=cmd_check)

    args = parser.parse_args()
    sys.exit(args.func(args))
```

## Findings (отдельный файл)

`docs/ledger/findings.jsonl` — находки (отличаются от решений):

```json
{"id": "F-001", "ts": "2026-09-20T16:00:00Z", "title": "Yandex Geocoder API возвращает 403 при превышении лимита 1000/день", "context": "При попытке геокодировать 1500 остановок за раз получили 403 на 1001-м запросе.", "evidence": "Лог в scripts/logs/geocode.log: 1000 OK, 1001 → 403. Тест в ml/tests/test_geocoder.py::test_rate_limit.", "impact": "Нужно батчить по 800 запросов с задержкой 1 сек. Или переключиться на Overpass для bulk-операций.", "tickets": ["T-NNN"], "tags": ["data", "yandex", "bug"]}
```

## Promotion в Note / Rule / Skill

См. `.clinerules/15-promote-finding.md`.

## Не делать

- ❌ Редактировать старые записи (append-only!)
- ❌ Использовать yaml (только jsonl для простоты парсинга)
- ❌ Записывать каждое мелкое решение (только значимые)
- ❌ Забывать указывать `tickets` (связь с backlog)
