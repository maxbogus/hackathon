"""Tests for scripts/ledger.py id-логики (F-128).

Проверяем, что id в ledger уникальны:
  - next_id: max+1, устойчив к битым строкам
  - resolve_id: свободный requested возвращается как есть; занятый — сдвигается
  - существующие дубликаты (F-046, F-096, F-097) не повторяются

Запуск: make test-root
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER_SCRIPT = REPO_ROOT / "scripts" / "ledger.py"


def _load_module() -> ModuleType:
    """Загрузить scripts/ledger.py без side-effects (у него нет __init__)."""
    spec = importlib.util.spec_from_file_location("ledger_script", LEDGER_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_jsonl(path: Path, ids: list[str]) -> None:
    path.write_text(
        "\n".join(json.dumps({"id": i, "title": f"t {i}"}) for i in ids) + "\n",
        encoding="utf-8",
    )


def test_next_id_on_missing_file_is_001(tmp_path: Path) -> None:
    mod = _load_module()
    assert mod.next_id("finding", tmp_path / "absent.jsonl") == "F-001"
    assert mod.next_id("decision", tmp_path / "absent.jsonl") == "D-001"


def test_next_id_is_max_plus_one(tmp_path: Path) -> None:
    mod = _load_module()
    path = tmp_path / "f.jsonl"
    _write_jsonl(path, ["F-001", "F-005", "F-003"])
    assert mod.next_id("finding", path) == "F-006"


def test_next_id_ignores_malformed_lines(tmp_path: Path) -> None:
    """Битая строка (нет id) не должна ломать расчёт следующего id."""
    mod = _load_module()
    path = tmp_path / "f.jsonl"
    path.write_text('{"id": "F-002"}\n{not json}\n\n{"title": "no id"}\n', encoding="utf-8")
    assert mod.next_id("finding", path) == "F-003"


def test_resolve_id_returns_free_requested(tmp_path: Path) -> None:
    mod = _load_module()
    path = tmp_path / "f.jsonl"
    _write_jsonl(path, ["F-001"])
    assert mod.resolve_id("finding", path, "F-010") == "F-010"


def test_resolve_id_bumps_taken_requested(tmp_path: Path) -> None:
    """Занятый requested → следующий свободный (а не дубликат)."""
    mod = _load_module()
    path = tmp_path / "f.jsonl"
    _write_jsonl(path, ["F-001", "F-002"])
    resolved = mod.resolve_id("finding", path, "F-002")
    assert resolved == "F-003"
    assert resolved not in mod.existing_ids(path)


def test_resolve_id_without_requested_skips_existing_duplicates(tmp_path: Path) -> None:
    """Пре-существующие дубликаты не мешают: новый id строго новый."""
    mod = _load_module()
    path = tmp_path / "f.jsonl"
    _write_jsonl(path, ["F-001", "F-002", "F-002", "F-003"])
    resolved = mod.resolve_id("finding", path)
    assert resolved == "F-004"
    assert resolved not in mod.existing_ids(path)


def test_real_ledger_has_no_duplicate_last_id_assignment() -> None:
    """Регресс F-128: resolve_id на реальном ledger не выдаёт занятый id."""
    mod = _load_module()
    findings = REPO_ROOT / "docs" / "ledger" / "findings.jsonl"
    resolved = mod.resolve_id("finding", findings)
    assert resolved not in mod.existing_ids(findings)
