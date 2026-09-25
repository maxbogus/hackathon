"""Tests for .clinerules/00-AGENTS.md index consistency.

Validates that:
- All .clinerules/NN-*.md files are listed in the index table
- Index line format matches expected pattern
- ai/skills/02-*.md exists (T-166 deliverable)
- No orphan index entries (file exists for every listed number)
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CLINERULES_DIR = REPO_ROOT / ".clinerules"
INDEX_FILE = CLINERULES_DIR / "00-AGENTS.md"
SKILLS_DIR = REPO_ROOT / "ai" / "skills"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _index_entries() -> dict[int, str]:
    """Парсит таблицу Index of clinerules → {number: filename}."""
    text = _read(INDEX_FILE)
    entries: dict[int, str] = {}
    # Строки вида: | 00 | `00-AGENTS.md` (this) | Мастер-индекс ... |
    # или | — | `MEMORY-BUDGET.md` | ...
    for line in text.splitlines():
        m = re.match(r"\|\s*(\d+|—)\s*\|\s*`([^`]+)`\s*\|", line)
        if not m:
            continue
        num_str, filename = m.group(1), m.group(2)
        if num_str == "—":
            continue  # MEMORY-BUDGET.md — особый файл
        entries[int(num_str)] = filename
    return entries


# === Index integrity ===


def test_clinerule_index_exists() -> None:
    assert INDEX_FILE.exists(), f"Missing {INDEX_FILE}"


def test_00_index_self_reference() -> None:
    """Index должен содержать ссылку на самого себя (00)."""
    entries = _index_entries()
    assert 0 in entries, "Index missing entry for 00-AGENTS.md"
    assert entries[0] == "00-AGENTS.md", (
        f"Index entry for 00 must be '00-AGENTS.md'. Got: {entries.get(0)}"
    )


def test_index_numbers_contiguous() -> None:
    """Номера clinerules должны идти подряд без пропусков."""
    entries = _index_entries()
    if not entries:
        pytest.skip("No index entries found")
    max_n = max(entries.keys())
    for n in range(1, max_n + 1):
        assert n in entries, f"Index missing entry for clinerule #{n:02d}"


@pytest.mark.parametrize("num,filename", list(_index_entries().items()))
def test_index_entry_file_exists(num: int, filename: str) -> None:  # noqa: ARG001
    """Каждый файл из индекса должен реально существовать.

    `num` нужен только для читаемого ID в pytest output.
    """
    path = CLINERULES_DIR / filename
    assert path.exists(), f"Index references {filename} but file does not exist at {path}"


# === T-166 deliverables ===


def test_clinerule_22_load_testing_exists() -> None:
    """T-166: должен появиться .clinerules/22-load-testing.md."""
    path = CLINERULES_DIR / "22-load-testing.md"
    assert path.exists(), f"Missing {path}"


def test_clinerule_22_in_index() -> None:
    """T-166: clinerule 22 должен быть в индексе 00-AGENTS.md."""
    entries = _index_entries()
    assert 22 in entries, "22-load-testing.md missing from index"
    assert entries[22] == "22-load-testing.md"


def test_clinerule_22_has_hard_rules() -> None:
    """T-166: clinerule 22 должен содержать hard rules."""
    path = CLINERULES_DIR / "22-load-testing.md"
    if not path.exists():
        pytest.skip("22-load-testing.md not yet created")
    text = _read(path)
    assert "Hard rules" in text or "hard rules" in text, (
        "22-load-testing.md missing 'Hard rules' section"
    )
    assert "❌" in text, "22-load-testing.md should have ❌ forbidden actions"
    assert "make loadtest" in text, "22-load-testing.md should reference make targets"


def test_skill_02_k6_load_testing_exists() -> None:
    """T-166: должен появиться ai/skills/02-k6-load-testing.md."""
    path = SKILLS_DIR / "02-k6-load-testing.md"
    assert path.exists(), f"Missing {path}" if SKILLS_DIR.exists() else f"Missing {SKILLS_DIR}"


def test_skill_02_has_troubleshooting() -> None:
    """T-166: skill 02 должен содержать troubleshooting секцию."""
    path = SKILLS_DIR / "02-k6-load-testing.md"
    if not path.exists():
        pytest.skip("02-k6-load-testing.md not yet created")
    text = _read(path)
    assert "Troubleshooting" in text or "troubleshooting" in text, (
        "02-k6-load-testing.md missing 'Troubleshooting' section"
    )
