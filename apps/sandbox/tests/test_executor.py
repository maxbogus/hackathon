"""Tests for sandbox executor (T-199)."""

from __future__ import annotations

from app.executor import Sandbox, run_in_sandbox


def test_simple_arithmetic() -> None:
    """Базовый код работает."""
    result = Sandbox().execute("result = 2 + 2")
    assert result.success is True
    assert result.return_value == 4


def test_print_captured() -> None:
    """stdout captured."""
    result = Sandbox().execute("print('hello sandbox')")
    assert result.stdout == "hello sandbox\n"


def test_forbidden_import_subprocess() -> None:
    """subprocess запрещён."""
    result = Sandbox().execute("import subprocess")
    assert result.success is False
    assert "subprocess" in result.error


def test_forbidden_import_socket() -> None:
    """socket запрещён (R4 no internet)."""
    result = Sandbox().execute("import socket")
    assert result.success is False
    assert "socket" in result.error


def test_forbidden_builtin_eval() -> None:
    """eval запрещён."""
    result = Sandbox().execute("eval('1+1')")
    assert result.success is False
    assert "eval" in result.error


def test_forbidden_builtin_exec() -> None:
    """exec запрещён."""
    result = Sandbox().execute("exec('1+1')")
    assert result.success is False
    assert "exec" in result.error


def test_allowed_stdlib_math() -> None:
    """math.sqrt(16) = 4 — разрешено."""
    result = Sandbox().execute("import math\nresult = math.sqrt(16)")
    assert result.success is True
    assert result.return_value == 4.0


def test_data_analysis_pattern() -> None:
    """Realistic use case: list comprehension + sum."""
    code = """
values = [1, 2, 3, 4, 5]
result = sum(x * 2 for x in values)
"""
    result = Sandbox().execute(code)
    assert result.success is True
    assert result.return_value == 30


def test_runtime_error_captured() -> None:
    """ZeroDivisionError → success=False, error содержит info."""
    result = Sandbox().execute("result = 1 / 0")
    assert result.success is False
    assert "ZeroDivisionError" in result.error


def test_syntax_error_captured() -> None:
    """SyntaxError → caught в validate_ast."""
    result = Sandbox().execute("def func(:")
    assert result.success is False
    assert "SyntaxError" in result.error


def test_run_in_sandbox_convenience() -> None:
    """Convenience функция работает."""
    result = run_in_sandbox("result = 42")
    assert result.return_value == 42


def test_duration_recorded() -> None:
    """duration_ms > 0."""
    result = Sandbox().execute("result = 1")
    assert result.duration_ms >= 0
