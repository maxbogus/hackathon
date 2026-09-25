# 29-zsh-shell-quirks.md — Особенности shell zsh на Ubuntu (и почему команды ломаются)

## Контекст

Хост агента — **zsh на Ubuntu Linux**. Это НЕ bash, и НЕ POSIX sh.
Многие команды, которые «должны работать», ломаются молча или с непредсказуемым
поведением. Этот clinerule фиксирует **конкретные gotchas** с которыми агент
сталкивается в этой среде.

## Hard rules

### ❌ НЕ использовать `echo` с подстановкой `{...}` без кавычек

zsh интерпретирует `{}` как **brace expansion**, не как строку:

```bash
# ❌ НЕПРАВИЛЬНО — zsh попытается раскрыть {i}:
echo "predictions[{i}] length"
# → SyntaxError или странный вывод

# ✅ ПРАВИЛЬНО — используем chr() или string concatenation:
python3 -c "print('predictions[' + str(i) + '] length')"
# ИЛИ escape: echo "predictions[\${i}] length"
```

### ❌ НЕ использовать `python3 -c "..."` с f-string-подобным синтаксисом внутри

zsh пытается раскрыть `f"..."`, `{var}`, `[]` ДО передачи в python:

```bash
# ❌ НЕПРАВИЛЬНО:
python3 -c "x = f'val={i}'"  # zsh увидит {i} как brace expansion
python3 -c "print(f'{data[idx]:rm -rf ...}')"  # подставит из истории!

# ✅ ПРАВИЛЬНО — используем heredoc:
python3 << 'PYEOF'
x = f"val={i}"
PYEOF
# ИЛИ: python3 -c 'x = f"val={i}"'  # одинарные снаружи
```

### ❌ НЕ использовать `python3 -c "..."` со сложными heredoc-вложениями

zsh + bash heredoc конфликтуют при вложенных кавычках и f-string:

```bash
# ❌ НЕПРАВИЛЬНО — zsh heredoc съедает f-string:
python3 << 'PYEOF'
print(f"@{idx}: {data[idx:idx+50]rm -rf <история>}")  # ← подставит из истории!
PYEOF

# ✅ ПРАВИЛЬНО — пишем через script file:
# Сохранить python в отдельный .py файл, вызвать
```

### ✅ Безопасные паттерны

```bash
# 1. Heredoc с одинарными кавычками и ПРОСТЫМ кодом (без f-string с []):
python3 << 'PYEOF'
content = "predictions[" + str(i) + "]"
PYEOF

# 2. Editor tool для изменений файлов (предпочтительно!)

# 3. sed с простыми substitution:
sed -i 's|OLD|NEW|' file.py

# 4. uv run python -m pytest ... (запускает pytest через venv)
```

### ✅ Диагностика перед заменой

Прежде чем использовать `replace()` / `sed`, проверять что строка существует:

```python
with open(path, 'rb') as f:
    data = f.read()
print(f'Found: {data.count(target_bytes)}')  # должно быть > 0
data = data.replace(target_bytes, new_bytes)
```

Если `count == 0` после `replace()` — **строка не существует**, проблема в чём-то
другом (кеш, BOM, разные кавычки, невидимые символы).

## Диагностика SyntaxError в Python из-за shell

Если `uv run --directory ml python -c "..."` падает с SyntaxError, **виноват shell**,
а не Python. Чеклист:

1. Есть ли в коде `f"...[{var}]..."` ? → заменить на конкатенацию или chr().
2. Есть ли `f"..."` внутри `python3 -c "..."` ? → использовать heredoc.
3. Есть ли `${var}` ? → escape как `\${var}`.

## Когда НЕ применять

- Bash скрипты в `docker-compose.yml` — там bash, не zsh.
- `make` цели — там shell определяется Makefile'ом (`/bin/sh`).
- CI скрипты — там bash.

## Cross-references

- `00-AGENTS.md` — Quick rules (обновить индекс при добавлении правила)
- `MEMORY-BUDGET.md` — экономия контекста (писать диагнозы в файлы, не в чат)
- Сессия T-172/T-173 — конкретный случай с f-string `predictions[{i}]` который
  zsh пытался интерпретировать как brace expansion.
