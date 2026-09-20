# 04-secret-handling.md — Секреты НИКОГДА в git

## Hard Rules

1. **Реальные ключи — ТОЛЬКО в `.env`** (gitignored). Никогда в `.env.example`.
2. **`.env.example`** содержит только плейсхолдеры: `your_key_here`, `your_2gis_key_here`.
3. **`.env`** для локальной разработки. В проде — Vault / AWS Secrets Manager.
4. **Никаких ключей в коде**, включая `print(api_key)`, логи, комментарии.
5. **gitleaks** запускается в pre-commit hook — сканирует staged файлы.

## Где какие ключи

| Ключ | Где | Когда заполнять |
|---|---|---|
| `VITE_YANDEX_MAPS_API_KEY` | `.env` | уже есть (получен для хакатона) |
| `VITE_YANDEX_GEOCODER_API_KEY` | `.env` | уже есть |
| `OPENROUTER_API_KEY` | `.env` | каждый ставит свой (lawcopilot-паттерн) |
| `DEEPSEEK_API_KEY` | `.env` | опционально |
| `GIGACHAT_CREDENTIALS` | `.env` | опционально |
| `ANTHROPIC_API_KEY` | `.env` | опционально |
| `POSTGRES_PASSWORD` | `.env` | дефолт `transit_dev_only` для dev |

## Когда всё-таки ключ попал в git

1. **Немедленно rotate** ключ у провайдера (Yandex, OpenRouter и т.д.).
2. Удалить из истории: `git filter-repo --invert-paths --path <file>` или BFG.
3. Force push (с предупреждением команды).
4. Записать инцидент в `docs/ledger/findings.jsonl` (тег `security`).

## Pre-commit защита

`gitleaks` в `.pre-commit-config.yaml` блокирует коммит если в staged файлах
есть паттерны ключей (например `sk-...`, `AIza...`, `gigachat_...`).

Если gitleaks даёт false positive — добавь исключение в `.gitleaks.toml`,
а не игнорируй `--no-verify`.

## CI (когда добавим)

GitHub Actions / GitLab CI должен запускать gitleaks на каждый push.
