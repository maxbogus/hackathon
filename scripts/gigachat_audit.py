#!/usr/bin/env python3
"""GigaChat project audit (T-AUDIT).

Собирает тексты проекта (md, py comments/docstrings, ts interfaces,
jsonl/json reports) по категориям и отправляет в GigaChat-2 для
технического аудита. Результат — markdown-отчёт в docs/audit/.

SECURITY:
    * GIGACHAT_CREDENTIALS — из env, никогда не в коде/git.
    * SSL verify=False (gigachat.devices.sberbank.ru self-signed).
    * .env в .gitignore (clinerule 04).

USAGE:
    # Полный аудит (5 категорий)
    uv run --project . python scripts/gigachat_audit.py

    # Только категория
    uv run --project . python scripts/gigachat_audit.py --category docs_md

    # Dry-run
    uv run --project . python scripts/gigachat_audit.py --dry-run

ВАЖНО:
    - GIGACHAT_API_PERS — лимит ~1000 RPM. Скрипт спит 1.5s между запросами.
    - Чанки <= --max-chars (default 6000). Каждый чанк = 1 запрос.
"""

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable
import datetime as dt
import os
from pathlib import Path
import re
import sys
import time
import uuid

import httpx  # available via apps/backend workspace dep

# ---------- GigaChat endpoints (verified via mlaw-rag/gigachat_client.py) ----
AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
DEFAULT_SCOPE = "GIGACHAT_API_PERS"
DEFAULT_MODEL = "GigaChat-2"  # alternative: GigaChat-2-Max (reasoning)

# ---------- Project paths -----------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "docs" / "audit"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_MAX_CHARS = 6000  # ~ 1.5k-2k токенов на чанк
SLEEP_BETWEEN_REQUESTS = 1.5  # секунд (R6 этикет)

# ---------- Excluded paths (не отправляем в LLM) ------------------------------
EXCLUDE_DIRS = {
    ".venv",
    "node_modules",
    ".git",
    "__pycache__",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".pyscn",
    "htmlcov_audit",
    "artifacts",  # ml/artifacts (модели)
    "src/generated",  # apps/frontend/src/generated (Orval output)
}
EXCLUDE_FILE_PATTERNS = [
    re.compile(r".*\.pyc$"),
    re.compile(r".*\.lock$"),
    re.compile(r".*\.parquet$"),
    re.compile(r".*\.pkl$"),
    re.compile(r".*\.onnx$"),
    re.compile(r".*\.pt$"),
    re.compile(r".*\.bin$"),
    re.compile(r".*coverage\.json$"),
]

# ---------- System prompt -----------------------------------------------------
SYSTEM_PROMPT = """Ты — старший технический аудитор на хакатоне (10 дней, full-stack ML+backend+frontend).
Тебе присылают фрагменты кода/документации проекта. Твоя задача — найти:

1. **Баги**: реальные ошибки, race conditions, утечки, off-by-one, отсутствующие null-проверки.
2. **Anti-patterns**: хардкод, magic numbers, god-объекты, циклические импорты, leaky abstractions.
3. **Security issues**: инъекции, отсутствие auth, leaked secrets, insecure defaults.
4. **Reproducibility/Quality**: missing seeds, не-идемпотентные операции, magic в URL.
5. **Hackathon scoring**: что улучшит оценку жюри (R3 reproducible, R6 SLA, R8 validation, R10 demo).
6. **Docs gaps**: противоречия между README и кодом, отсутствующие ADR.

Формат ответа (строго, на русском):
## Категория: <имя фрагмента>
### Критические проблемы (блокеры)
- [CRITICAL] ...
### Существенные проблемы
- [HIGH] ...
### Замечания / рекомендации
- [MED] ...
- [LOW] ...
### Что хорошо
- ...

Если фрагмент не содержит проблем — напиши "OK" с одной строкой обоснования.
Не выдумывай проблем. Если контекста мало — скажи "Нужно больше контекста".

Контекст проекта (даётся 1 раз, далее только фрагменты):
- Transit-AI: прогноз пассажиропотока трамваев Москвы, 10 маршрутов × 61 день × 24ч = 14640 строк.
- Stack: FastAPI + PostgreSQL+Timescale + Redis; Frontend Vite/React/TS; ML через uv-скрипты (не Docker).
- Hard rules: R1 MIT, R2 LLM<=4B, R3 reproducible, R4 no-internet runtime, R5 real data, R6 <=60 мин train + <=2s inference, R8 validation report, R10 10 slides + 5 мин видео.
- Цель жюри: WAPE-score >= 0.85 (D-016).
"""

# ---------- Collector helpers ------------------------------------------------


def _should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDE_DIRS:
        return True
    name = str(path)
    for pat in EXCLUDE_FILE_PATTERNS:
        if pat.match(name):
            return True
    return False


def _iter_py_text(repo_root: Path) -> Iterable[tuple[Path, str]]:
    """Извлекает module docstring + docstrings top-level defs из .py."""
    for py in sorted(repo_root.rglob("*.py")):
        if _should_skip(py):
            continue
        try:
            src = py.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            mod_doc = ast.get_docstring(ast.Module(body=[], type_ignores=[])) or ""
            if mod_doc:
                yield py, mod_doc
            continue

        chunks: list[str] = []
        mod_doc = ast.get_docstring(tree)
        if mod_doc:
            chunks.append("# module docstring:" + chr(10) + mod_doc)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                d = ast.get_docstring(node)
                if d:
                    kind = "class" if isinstance(node, ast.ClassDef) else "def"
                    sig = node.name if hasattr(node, "name") else ""
                    chunks.append("# " + kind + " " + sig + ":" + chr(10) + d)

        if chunks:
            yield py, chr(10).join(chunks)


def _iter_md(repo_root: Path, subdir: str = "docs") -> Iterable[tuple[Path, str]]:
    base = repo_root / subdir
    if not base.exists():
        return
    for md in sorted(base.rglob("*.md")):
        if _should_skip(md):
            continue
        try:
            yield md, md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue


def _iter_ts_interfaces(repo_root: Path) -> Iterable[tuple[Path, str]]:
    """Извлекает export interface / type из .ts/.tsx (без generated)."""
    base = repo_root / "apps" / "frontend" / "src"
    if not base.exists():
        return
    iface_re = re.compile(
        r"^export\s+interface\s+\w+[^{]*\{[^}]*\}",
        re.MULTILINE | re.DOTALL,
    )
    type_re = re.compile(
        r"^export\s+type\s+\w+\s*=[^;]+;",
        re.MULTILINE | re.DOTALL,
    )
    for ts in sorted(base.rglob("*.ts*")):
        if _should_skip(ts):
            continue
        try:
            src = ts.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        matches = iface_re.findall(src) + type_re.findall(src)
        if matches:
            yield ts, chr(10).join(matches)


def _iter_reports(repo_root: Path) -> Iterable[tuple[Path, str]]:
    """Собирает json/jsonl из predictions/, docs/ledger/, reports/."""
    candidates: list[Path] = []
    for sub in ("predictions", "reports", "docs/ledger", "docs/reports"):
        base = repo_root / sub
        if not base.exists():
            continue
        for ext in ("*.json", "*.jsonl"):
            candidates.extend(base.rglob(ext))
    for f in sorted(set(candidates)):
        if _should_skip(f):
            continue
        name = f.name.lower()
        if not any(
            k in name
            for k in ("submission", "metrics", "inventory", "decision", "finding", "manifest")
        ):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(text) > 30_000:
            text = (
                text[:30_000]
                + chr(10)
                + chr(10)
                + "... [truncated, "
                + str(len(text))
                + " chars total] ..."
            )
        yield f, text


_USER_FOUND_PARTS = [
    "# Аудит HACKATHON_CHECKLIST.md — найдено Cline",
    "",
    "## Контекст проверки",
    "Проверено ~75 пунктов чек-листа (16 секций). Командами сверены статусы",
    "с реальным состоянием файлов.",
    "",
    "## Блокеры (НЕ ВЫПОЛНЕНО, 5 шт.)",
    "1. Презентация (R10): 1/10 слайдов (только slide_01_pain_points.md).",
    "2. demo_video.mp4: отсутствует.",
    "3. LICENSE (MIT): файл не в корне.",
    "4. inventory.json: папка data/validation_reports/ отсутствует.",
    "5. reports/*.json: папка reports/ отсутствует (нет model metrics).",
    "",
    "## Частично (4 шт.)",
    "- README на русском (T-115 in-progress).",
    "- HTML-отчёты load testing (docs/load-profiles/reports/ пустая).",
    "- .gitignore — найдено только .env.",
    "- Submission pipeline — кейс с route 5 (F-051, 14640 строк валидно).",
    "",
    "## Выполнено (52+ шт.)",
    "- meta.json (git_commit, train_data_hash, seed=42, timestamps).",
    "- LICENSE deps, uv.lock+yarn.lock, seed=42 в 9 местах.",
    "- No HTTP outside (backend + ML чистые).",
    "- Real data: submission.csv = 14640 строк, real.py на хакатоне.",
    "- Container resources: postgres 1CPU/1G, redis 0.25/256M, backend 1/512M, k6 cpuset 0,1.",
    "- 17 OpenAPI pathов, Orval сгенерирован, JSON Schema артефактов.",
    "- Jury criteria 19/19.",
    "",
    "## Гипотезы для расследования GigaChat",
    "- Возможно ли авто-генерация недостающих слайдов из docs/?",
    "- Стоит ли генерить LICENSE автоматически из README?",
    "- Какой holdout WAPE-score у текущего submission.csv?",
    "- Не появились ли недавние тикеты, отменяющие T-115/README?",
]
USER_FOUND_REPORT = chr(10).join(_USER_FOUND_PARTS)


def collect(category: str, repo_root: Path = ROOT) -> list[tuple[str, str]]:
    """Возвращает список (label, content) по категории."""
    if category == "comments":
        return [(str(p.relative_to(repo_root)), t) for p, t in _iter_py_text(repo_root)]
    if category == "docs_md":
        return [(str(p.relative_to(repo_root)), t) for p, t in _iter_md(repo_root, "docs")]
    if category == "interfaces":
        return [(str(p.relative_to(repo_root)), t) for p, t in _iter_ts_interfaces(repo_root)]
    if category == "reports_jsonl":
        return [(str(p.relative_to(repo_root)), t) for p, t in _iter_reports(repo_root)]
    if category == "user_found":
        return [("audit_findings.md", USER_FOUND_REPORT)]
    raise ValueError("Unknown category: " + repr(category))


# ---------- GigaChat client --------------------------------------------------


def _get_credentials() -> str:
    creds = os.environ.get("GIGACHAT_CREDENTIALS")
    if not creds:
        raise RuntimeError(
            "GIGACHAT_CREDENTIALS не установлен. Экспортируйте ключ:"
            + chr(10)
            + "  export GIGACHAT_CREDENTIALS=<base64_client_id_colon_secret>"
            + chr(10)
            + "(см. lawcopilot/.env.example)"
        )
    return creds.strip()


def _get_token(creds: str, scope: str) -> str:
    """OAuth client_credentials -> Bearer token (self-signed TLS)."""
    with httpx.Client(verify=False, timeout=30.0) as client:
        r = client.post(
            AUTH_URL,
            headers={
                "Authorization": "Basic " + creds,
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"grant_type": "client_credentials", "scope": scope},
        )
        r.raise_for_status()
        return r.json()["access_token"]


def _chat(token: str, model: str, user_msg: str, max_tokens: int = 1500) -> str:
    """Single chat completion with retry on 429/5xx."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    last_exc = None
    for attempt in range(4):
        try:
            with httpx.Client(verify=False, timeout=90.0) as client:
                r = client.post(
                    CHAT_URL,
                    headers={
                        "Authorization": "Bearer " + token,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2**attempt + 1)
                    continue
                r.raise_for_status()
                data = r.json()
                return str(data["choices"][0]["message"]["content"])
        except httpx.HTTPError as exc:
            last_exc = exc
            time.sleep(2**attempt + 1)
    raise RuntimeError("GigaChat failed after retries: " + repr(last_exc))


# ---------- Chunking ---------------------------------------------------------


def chunk_text(label: str, text: str, max_chars: int) -> list[str]:
    """Делит текст на чанки <= max_chars. Сохраняет контекст label в каждом."""
    header = "### Фрагмент: " + label + chr(10)
    overhead = len(header) + 4
    if len(text) + overhead <= max_chars:
        return [header + text]
    chunks = []
    step = max_chars - overhead
    for i in range(0, len(text), step):
        chunk = text[i : i + step]
        chunks.append(header + chunk)
    return chunks


# ---------- Main -------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split(chr(10), 1)[0])
    parser.add_argument(
        "--category",
        "-c",
        action="append",
        choices=["comments", "docs_md", "interfaces", "reports_jsonl", "user_found"],
        help="Категория текстов (можно несколько раз). Default: все.",
    )
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help="GigaChat model: GigaChat-2 или GigaChat-2-Max"
    )
    parser.add_argument("--scope", default=os.environ.get("GIGACHAT_SCOPE", DEFAULT_SCOPE))
    parser.add_argument(
        "--dry-run", action="store_true", help="Только собрать и показать план, без запросов к API."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Путь к отчёту (default: docs/audit/gigachat_audit_<ts>.md",
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Лимит чанков (0 = без лимита). Для отладки."
    )
    args = parser.parse_args(argv)

    categories = args.category or [
        "comments",
        "docs_md",
        "interfaces",
        "reports_jsonl",
        "user_found",
    ]

    # 1. Collect
    print("[collect] categories=" + str(categories), file=sys.stderr)
    collected = []  # (category, label, text)
    for cat in categories:
        items = collect(cat)
        for label, text in items:
            collected.append((cat, label, text))
        print("  " + cat + ": " + str(len(items)) + " файлов", file=sys.stderr)

    # 2. Chunk
    all_chunks = []  # (category, label, chunk)
    for cat, label, text in collected:
        for ch in chunk_text(label, text, args.max_chars):
            all_chunks.append((cat, label, ch))
    if args.limit:
        all_chunks = all_chunks[: args.limit]
    print(
        "[chunk] total "
        + str(len(all_chunks))
        + " чанков (max "
        + str(args.max_chars)
        + " chars each)",
        file=sys.stderr,
    )

    if args.dry_run:
        print("[dry-run] STOP. Collected sizes:", file=sys.stderr)
        for cat, label, text in collected:
            print("  " + cat + "/" + label + ": " + str(len(text)) + " chars", file=sys.stderr)
        return 0

    # 3. Auth
    creds = _get_credentials()
    print("[auth] getting token (scope=" + args.scope + ")...", file=sys.stderr)
    token = _get_token(creds, args.scope)
    print("[auth] OK, token len=" + str(len(token)), file=sys.stderr)

    # 4. Output file
    ts = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    out_path = args.output or AUDIT_DIR / ("gigachat_audit_" + ts + ".md")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 5. Process chunks
    lines = []
    lines.append("# GigaChat Audit — Transit-AI (" + ts + ")")
    lines.append("")
    lines.append("- Модель: `" + args.model + "`")
    lines.append("- Категории: " + str(categories))
    lines.append("- Чанков: " + str(len(all_chunks)))
    lines.append("- Max chars/чанк: " + str(args.max_chars))
    lines.append("")
    lines.append("## System prompt")
    lines.append("```")
    lines.append(SYSTEM_PROMPT.strip())
    lines.append("```")
    lines.append("")

    for i, (cat, label, chunk) in enumerate(all_chunks, 1):
        print(
            "["
            + str(i)
            + "/"
            + str(len(all_chunks))
            + "] "
            + cat
            + "/"
            + label
            + " ("
            + str(len(chunk))
            + " chars)...",
            file=sys.stderr,
        )
        try:
            response = _chat(token, args.model, chunk)
        except Exception as exc:
            response = "## ОШИБКА" + chr(10) + "```" + chr(10) + repr(exc) + chr(10) + "```"
        lines.append("---")
        lines.append("## [" + str(i) + "/" + str(len(all_chunks)) + "] " + cat + "/" + label)
        lines.append("")
        lines.append("### Отправлено (фрагмент):")
        lines.append("<details><summary>click to expand</summary>")
        lines.append("```")
        snippet = chunk[:3000] + (
            chr(10) + "... [truncated in report]" if len(chunk) > 3000 else ""
        )
        lines.append(snippet)
        lines.append("```")
        lines.append("</details>")
        lines.append("")
        lines.append("### Ответ GigaChat:")
        lines.append("")
        lines.append(response)
        lines.append("")
        if i < len(all_chunks):
            time.sleep(SLEEP_BETWEEN_REQUESTS)

    out_path.write_text(chr(10).join(lines), encoding="utf-8")
    print("[done] report saved: " + str(out_path), file=sys.stderr)
    print("[done] chunks processed: " + str(len(all_chunks)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
