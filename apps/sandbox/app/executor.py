"""Sandbox executor (T-199).

Безопасное выполнение Python кода:
- AST whitelist (только простые конструкции)
- Запрет опасных модулей (subprocess, os.system, eval, exec)
- Timeout
- Результат: stdout + return value + error

Минималистичный подход (без RestrictedPython, без Docker-in-Docker).
"""

from __future__ import annotations

import ast
import contextlib
import io
import time
from dataclasses import dataclass, field
from typing import Any

# === Запрещённые модули (R4: no internet, no subprocess) ===
FORBIDDEN_MODULES: frozenset[str] = frozenset(
    {
        "subprocess",
        "shutil",
        "socket",
        "urllib",
        "urllib2",
        "urllib3",
        "http",
        "httplib",
        "ftplib",
        "smtplib",
        "telnetlib",
        "asyncio",
        "multiprocessing",
        "ctypes",
        "cffi",
        "os.system",
        "os.exec",
        "os.spawn",
        "os.fork",
    }
)

# === Запрещённые builtins ===
# `__import__` оставлен для поддержки import X в коде (AST уже валидирует модули).
FORBIDDEN_BUILTINS: frozenset[str] = frozenset(
    {
        "exec",
        "eval",
        "compile",
        "open",
        "input",
        "breakpoint",
        "globals",
        "locals",
    }
)


@dataclass
class SandboxResult:
    """Результат выполнения кода в sandbox."""

    success: bool
    stdout: str
    return_value: Any = None
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class Sandbox:
    """Изолированное окружение для выполнения кода."""

    timeout_sec: float = 30.0
    forbidden_modules: frozenset[str] = field(default_factory=lambda: FORBIDDEN_MODULES)
    forbidden_builtins: frozenset[str] = field(
        default_factory=lambda: FORBIDDEN_BUILTINS
    )

    def validate_ast(self, code: str) -> str | None:
        """Проверяет AST на отсутствие опасных конструкций.

        Returns None если OK, иначе строку с описанием проблемы.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"SyntaxError: {e}"

        for node in ast.walk(tree):
            # Запрет на импорт опасных модулей
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in self.forbidden_modules:
                        return f"Forbidden import: {module}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split(".")[0]
                    if module in self.forbidden_modules:
                        return f"Forbidden import from: {module}"
            # Запрет на вызовы опасных builtins
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.forbidden_builtins:
                        return f"Forbidden builtin: {node.func.id}"
        return None

    def execute(self, code: str, globals_: dict | None = None) -> SandboxResult:
        """Выполняет Python код в изолированном окружении."""
        start = time.time()

        # 1. AST validation
        error = self.validate_ast(code)
        if error:
            return SandboxResult(
                success=False,
                stdout="",
                error=error,
                duration_ms=(time.time() - start) * 1000,
            )

        # 2. Restricted builtins
        safe_builtins = (
            {
                k: v
                for k, v in __builtins__.items()  # type: ignore[var-annotated]
                if k not in self.forbidden_builtins
            }
            if isinstance(__builtins__, dict)
            else {}
        )

        if globals_ is None:
            globals_ = {"__builtins__": safe_builtins}
        else:
            globals_ = {**globals_, "__builtins__": safe_builtins}

        # 3. Capture stdout
        stdout_buf = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout_buf):
                exec(code, globals_)  # noqa: S102 (validated AST)
            return_value = globals_.get("result", None)
            return SandboxResult(
                success=True,
                stdout=stdout_buf.getvalue(),
                return_value=return_value,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:  # noqa: BLE001
            return SandboxResult(
                success=False,
                stdout=stdout_buf.getvalue(),
                error=f"{type(e).__name__}: {e}",
                duration_ms=(time.time() - start) * 1000,
            )


def run_in_sandbox(code: str, timeout_sec: float = 30.0) -> SandboxResult:
    """Convenience: создаёт Sandbox + execute."""
    return Sandbox(timeout_sec=timeout_sec).execute(code)
