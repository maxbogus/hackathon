"""Transit-AI Sandbox (T-199) — restricted shell executor.

Используется MCP tools (T-200) для безопасного выполнения кода,
сгенерированного LLM. Ограничения:
- import whitelist: только stdlib + numpy/pandas (для анализа данных)
- Запрет subprocess, network, file I/O вне /tmp/sandbox
- Timeout 30 сек
- Memory limit 256MB (через Docker)

Не копирует код из lawcopilot — реализует свой минимальный sandbox.
Использует RestrictedPython (или ручную проверку AST если не установлен).
"""

from app.executor import Sandbox, SandboxResult, run_in_sandbox

__all__ = ["Sandbox", "SandboxResult", "run_in_sandbox"]
