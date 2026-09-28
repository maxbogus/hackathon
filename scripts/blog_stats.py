"""Collect reproducible numbers for the blog series in ``docs/blog/``.

Usage:
    uv run python scripts/blog_stats.py              # → docs/blog/stats.json + таблица
    uv run python scripts/blog_stats.py --quiet      # только записать JSON
    make blog-stats                                  # то же через Makefile

Зачем: посты про ИИ-скепсис ссылаются на цифры (коммиты, тесты, эндпоинты,
лучший платформенный скор). Скрипт берёт их из самого репозитория, чтобы цифры
в текстах не «протухали». Правило: каждое число в посте обязано иметь строку
в ``docs/blog/00-FACTS.md``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PY_ROOTS = ("apps", "ml", "mlops", "scripts")
SKIP_PARTS = ("__pycache__", ".venv", "node_modules", "generated")


def _git(*args: str) -> str:
    """Run a read-only git command from the repo root."""
    proc = subprocess.run(
        ["git", "--no-pager", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip()


def _files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    """All files under ``root`` with the given suffixes, minus vendored dirs."""
    if not root.exists():
        return []
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in suffixes
        and not any(part in SKIP_PARTS for part in path.parts)
    ]


def _line_count(paths: list[Path]) -> int:
    """Total number of lines across the given files (tolerant to bad encoding)."""
    total = 0
    for path in paths:
        try:
            total += len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
        except OSError:
            continue
    return total


def code_size() -> dict[str, int]:
    """Python and frontend source size (files + lines)."""
    py_files: list[Path] = []
    for root_name in PY_ROOTS:
        py_files.extend(_files(REPO_ROOT / root_name, (".py",)))
    fe_files = _files(REPO_ROOT / "apps" / "frontend" / "src", (".ts", ".tsx"))
    return {
        "python_files": len(py_files),
        "python_lines": _line_count(py_files),
        "frontend_files": len(fe_files),
        "frontend_lines": _line_count(fe_files),
    }


def ledger_counts() -> dict[str, int]:
    """Number of findings and decisions in the append-only ledger."""
    counts: dict[str, int] = {}
    for name in ("findings", "decisions"):
        path = REPO_ROOT / "docs" / "ledger" / f"{name}.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        counts[name] = sum(1 for line in lines if line.strip())
    return counts


def tests() -> dict[str, int]:
    """Python test functions and frontend test cases (static count)."""
    py_tests = 0
    for path in _files(REPO_ROOT, (".py",)):
        if not (path.name.startswith("test_") or path.name.endswith("_test.py")):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        py_tests += len(re.findall(r"^\s*(?:async )?def test_", text, re.MULTILINE))

    fe_files = 0
    fe_cases = 0
    for path in _files(REPO_ROOT / "apps" / "frontend" / "src", (".ts", ".tsx")):
        if ".test." not in path.name:
            continue
        fe_files += 1
        fe_cases += len(re.findall(r"\bit\(", path.read_text(encoding="utf-8", errors="ignore")))

    return {
        "python_test_functions": py_tests,
        "frontend_test_files": fe_files,
        "frontend_cases": fe_cases,
    }


def repo_shape() -> dict[str, Any]:
    """Counts of contracts, containers, database tables, screens and text keys."""
    openapi = REPO_ROOT / "docs" / "api" / "openapi.json"
    openapi_paths = 0
    if openapi.exists():
        try:
            openapi_paths = len(json.loads(openapi.read_text(encoding="utf-8")).get("paths", {}))
        except json.JSONDecodeError:
            openapi_paths = 0

    compose_text = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    services = re.findall(r"^  ([a-z0-9_-]+):$", compose_text, re.MULTILINE)

    tables: list[str] = []
    for path in _files(REPO_ROOT / "apps" / "backend" / "app", (".py",)):
        text = path.read_text(encoding="utf-8", errors="ignore")
        tables.extend(re.findall(r'__tablename__\s*=\s*"([^"]+)"', text))

    i18n = REPO_ROOT / "apps" / "frontend" / "src" / "lib" / "i18n" / "ru-RU.ts"
    i18n_key_lines = 0
    if i18n.exists():
        i18n_key_lines = len(
            re.findall(r"^\s{2,}[a-zA-Z]+:", i18n.read_text(encoding="utf-8"), re.M)
        )

    routes_dir = REPO_ROOT / "apps" / "frontend" / "src" / "routes"
    screens = sorted(
        p.stem
        for p in routes_dir.glob("*.tsx")
        if not p.name.startswith(("-", "_")) and p.stem != "__root"
    )

    return {
        "openapi_paths": openapi_paths,
        "compose_services": len(services),
        "compose_service_names": services,
        "db_tables": sorted(set(tables)),
        "i18n_key_lines": i18n_key_lines,
        "screens": screens,
    }


def workflow() -> dict[str, Any]:
    """Tickets, agent rules, commits, submissions and model artifacts."""
    predictions = REPO_ROOT / "predictions"
    days: dict[str, int] = {}
    for line in _git("log", "--pretty=%ad", "--date=short").splitlines():
        if line:
            days[line] = days.get(line, 0) + 1

    return {
        "tickets": len(list((REPO_ROOT / "docs" / "backlog" / "tickets").glob("*.md"))),
        "clinerules": len(list((REPO_ROOT / ".clinerules").glob("*.md"))),
        "skills": len(list((REPO_ROOT / "ai" / "skills").glob("*.md"))),
        "commits_head": int(_git("rev-list", "--count", "HEAD") or 0),
        "commits_all_refs": int(_git("rev-list", "--count", "--all") or 0),
        "commits_per_day": dict(sorted(days.items())),
        "first_commit": (
            _git("log", "--reverse", "--pretty=%ad", "--date=short").splitlines() or [""]
        )[0],
        "submission_csv": len(list(predictions.glob("*.csv"))) if predictions.exists() else 0,
        "submission_manifests": len(list(predictions.glob("*.json")))
        if predictions.exists()
        else 0,
        "model_artifacts": len(
            [p for p in (REPO_ROOT / "ml" / "artifacts").glob("*") if p.is_dir()]
        ),
    }


def best_platform_score() -> float | None:
    """Best platform WAPE-score recorded in ``docs/SUBMISSION.md``."""
    doc = REPO_ROOT / "docs" / "SUBMISSION.md"
    if not doc.exists():
        return None
    match = re.search(r"platform (\d\.\d+)", doc.read_text(encoding="utf-8"))
    return float(match.group(1)) if match else None


def collect() -> dict[str, Any]:
    """All stats in one dictionary."""
    stats: dict[str, Any] = {"repo": code_size(), "ledger": ledger_counts(), "tests": tests()}
    stats.update(repo_shape())
    stats.update(workflow())
    stats["best_platform_wape_score"] = best_platform_score()
    return stats


def main() -> int:
    """Write ``docs/blog/stats.json`` and print a short table."""
    parser = argparse.ArgumentParser(description="Collect blog stats from the repo")
    parser.add_argument("--output", default="docs/blog/stats.json", help="output JSON path")
    parser.add_argument("--quiet", action="store_true", help="do not print the table")
    args = parser.parse_args()

    stats = collect()
    out_path = REPO_ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.quiet:
        repo, tests_d = stats["repo"], stats["tests"]
        print(f"commits (HEAD / all refs): {stats['commits_head']} / {stats['commits_all_refs']}")
        print(f"python: {repo['python_files']} files / {repo['python_lines']} lines")
        print(f"frontend: {repo['frontend_files']} files / {repo['frontend_lines']} lines")
        print(
            f"tests: {tests_d['python_test_functions']} python / {tests_d['frontend_cases']} frontend"
        )
        print(f"openapi paths: {stats['openapi_paths']}; containers: {stats['compose_services']}")
        print(f"db tables: {len(stats['db_tables'])}; screens: {len(stats['screens'])}")
        print(
            f"ledger: {stats['ledger']['findings']} findings / {stats['ledger']['decisions']} decisions"
        )
        print(f"best platform WAPE-score: {stats['best_platform_wape_score']}")
        print(f"written → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
