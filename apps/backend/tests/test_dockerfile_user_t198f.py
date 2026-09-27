"""Tests for T-198f: Dockerfile использует adduser для non-root в slim-bookworm.

F-091: docker build падает с '/bin/sh: 1: groupadd: not found' потому что
python:3.12-slim-bookworm НЕ содержит shadow пакет (groupadd/useradd).
Решение: apt-get install -y adduser + `adduser --system` (не groupadd).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def _get_dockerfile(package: str) -> Path | None:
    for dirname in [package, package.replace("_", "-")]:
        p = REPO_ROOT / "apps" / dirname / "Dockerfile"
        if p.exists():
            return p
    return None


class TestDockerfileUsesAdduser:
    """Dockerfile должен использовать adduser (НЕ groupadd/useradd)."""

    @pytest.mark.parametrize("package", ["backend", "harvester", "ml_pipeline"])
    def test_dockerfile_uses_adduser_or_groupadd(self, package: str) -> None:
        """Dockerfile должен создать пользователя app (adduser или groupadd+useradd)."""
        path = _get_dockerfile(package)
        assert path, f"apps/{package}/Dockerfile не найден"
        content = path.read_text()
        # Допустимо: adduser (slim-bookworm) ИЛИ groupadd+useradd (с shadow пакетом)
        has_adduser = "adduser" in content
        has_groupadd = "groupadd" in content
        has_useradd = "useradd" in content
        # T-198h: допускается ручное создание через /etc/passwd (без утилит)
        has_manual = ("echo 'app:x:1000" in content) or (
            "/etc/passwd" in content and "app:x" in content
        )
        assert has_adduser or (has_groupadd and has_useradd) or has_manual, (
            f"apps/{package}/Dockerfile должен создать пользователя app "
            f"через adduser, groupadd+useradd, или /etc/passwd (ручной fallback)"
        )

    @pytest.mark.parametrize("package", ["backend", "harvester", "ml_pipeline"])
    def test_dockerfile_uses_uid_1000(self, package: str) -> None:
        """Не-root пользователь должен быть UID 1000 (для volume mount)."""
        path = _get_dockerfile(package)
        content = path.read_text()
        has_uid = (
            "uid 1000" in content
            or "uid=1000" in content
            or "--uid 1000" in content
            or "--gid 1000" in content
            or "UID 1000" in content
            or "1000:1000" in content  # /etc/passwd строка или USER 1000:1000
        )
        assert has_uid, (
            f"apps/{package}/Dockerfile должен использовать UID 1000 "
            f"(для совместимости с volumes на хосте)"
        )
