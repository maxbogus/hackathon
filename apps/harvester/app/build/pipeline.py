"""Пайплайн external ETL (шаг 0, T-231): сборка + манифест + верификация.

`build_all()` собирает все источники и пишет `manifest.json` с sha256 каждого
артефакта. `verify()` сверяет артефакты с манифестом (хэши, row counts,
наличие входов, JSON Schema) и возвращает exit code.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Sequence

from app.build import builders
from app.build.schema import validate_payload
from app.config import REPO_ROOT

MANIFEST_NAME = "manifest.json"

# Кто в системе читает нормализованный артефакт (для `make external-show`).
CONSUMERS: dict[str, str] = {
    "weather": "ml/transit_ai/data/weather_openmeteo.py",
    "traffic": "ml/transit_ai/data/traffic_osm.py",
    "poi": "ml/transit_ai/data/poi_features.py",
    "events": "ml/transit_ai/data/events_calendar.py",
    "stops": "ml/transit_ai/data/poi_features.py + apps/backend/app/data/geo.py",
    "validators": "ml/transit_ai/data/validators_lookup.py",
    "calendar": "ml/transit_ai/data/{calendar_rf,seasonal_calendar}.py",
    "user_routes": "ml/transit_ai/data/spravochnik_geo.py",
}


def git_commit(repo_root: Path) -> str:
    """Короткий hash коммита (или 'unknown', если git недоступен)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def build_all(
    repo_root: Path | str | None = None,
    out_dir: Path | str | None = None,
    mode: str = "offline",
    sources: Sequence[str] | None = None,
    source_epoch: str | None = None,
) -> dict[str, Any]:
    """Собрать все (или указанные) источники → normalized/*.json + manifest.json.

    `mode="offline"` — контракт R4: никаких сетевых вызовов (builders читают
    только локальные raw-файлы). `mode="online"` зарезервирован под `external-fetch`.
    """
    root, out = builders.resolve_paths(repo_root, out_dir)
    names = list(sources) if sources else list(builders.SOURCES)
    entries: dict[str, dict[str, Any]] = {}
    for name in names:
        result = builders.BUILDERS[name](repo_root=root, out_dir=out, source_epoch=source_epoch)
        entries[name] = {
            "output_path": str(result.output_path),
            "output_sha256": result.output_sha256,
            "rows_count": result.rows_count,
            "generated_at": result.generated_at,
            "inputs": list(result.inputs),
            "warning": result.warning,
        }

    manifest = {
        "mode": mode,
        "generated_at": builders.generated_at([Path(e["output_path"]) for e in entries.values()])
        if entries
        else builders.now_iso(),
        "git_commit": git_commit(root),
        "out_dir": str(out),
        "sources": entries,
    }
    manifest_path = out / MANIFEST_NAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def _default_out_dir(out_dir: Path | str | None) -> Path:
    if out_dir:
        return Path(out_dir)
    return REPO_ROOT / builders.DEFAULT_OUT_SUBDIR


def load_manifest(out_dir: Path | str | None = None) -> dict[str, Any] | None:
    """Прочитать manifest.json (None, если его нет/битый)."""
    path = _default_out_dir(out_dir) / MANIFEST_NAME
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def verify(out_dir: Path | str | None = None) -> int:
    """Проверить артефакты против манифеста. 0 — всё сошлось, 1 — нет."""
    out = _default_out_dir(out_dir)
    manifest = load_manifest(out)
    if manifest is None:
        print(f"FAIL: manifest.json не найден в {out}. Запусти: make external-gen")
        return 1

    problems: list[str] = []
    sources = manifest.get("sources", {})
    if not sources:
        problems.append("manifest: пустой список sources")

    for name, meta in sources.items():
        path = Path(str(meta.get("output_path", "")))
        if not path.exists():
            problems.append(f"{name}: артефакт не найден ({path})")
            continue
        data = path.read_bytes()
        if builders.sha256_bytes(data) != meta.get("output_sha256"):
            problems.append(f"{name}: sha256 не совпадает с манифестом (артефакт изменён?)")
            continue
        payload = json.loads(data.decode("utf-8"))
        if payload.get("source") != name:
            problems.append(f"{name}: поле source={payload.get('source')!r}")
        rows = payload.get("rows")
        if isinstance(rows, list) and int(payload.get("rows_count", -1)) != len(rows):
            problems.append(
                f"{name}: rows_count={payload.get('rows_count')} != {len(rows)}"
            )
        if not payload.get("inputs"):
            problems.append(f"{name}: пустой список inputs")
        for issue in validate_payload(payload, name):
            problems.append(f"{name}: schema: {issue}")

    if problems:
        print(f"FAIL: {len(problems)} проблем(ы) в {out}")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"OK: {len(sources)} источников проверено (sha256 + rows_count + schema) в {out}")
    return 0


def show(out_dir: Path | str | None = None) -> str:
    """ASCII-таблица: источник / строк / sha256(8) / потребитель."""
    out = _default_out_dir(out_dir)
    manifest = load_manifest(out)
    lines = [f"external ETL: {out}"]
    if manifest is None:
        lines.append("  manifest.json не найден — запусти: make external-gen")
        return "\n".join(lines)
    lines.append(
        f"  git_commit={manifest.get('git_commit')} generated_at={manifest.get('generated_at')}"
    )
    lines.append(f"  {'source':<12} {'rows':>7}  {'sha256':<8}  consumer")
    for name, meta in manifest.get("sources", {}).items():
        sha8 = str(meta.get("output_sha256", ""))[:8]
        lines.append(
            f"  {name:<12} {meta.get('rows_count', 0):>7}  {sha8:<8}  {CONSUMERS.get(name, '-')}"
        )
    return "\n".join(lines)
