---
id: T-163
phase: 8
title: docker-compose deploy.resources для всех сервисов + loadtest profile с CPU pinning
priority: P0
effort: 1.5
unit: hours
rice:
  R: 4
  I: 3.0
  C: 1.0
  score: 7.00
depends_on: []
blocks: []
tags: [devops, docker, resources, r3, reproducible, loadtest]
status: ready
created: 2026-09-25
updated: 2026-09-25
assignee: "maxim"
---

# T-163: docker-compose deploy.resources для всех сервисов + loadtest profile

## Context

R3 hackathon-rules: "Reproducible: ... Docker образ ≤ 15 GB"

Сейчас в docker-compose.yml нет deploy.resources ни для одного сервиса.
Это означает: контейнеры могут сожрать всю RAM/CPU, воспроизводимость под вопросом,
k6 нагрузка может повлиять на измеряемый backend.

Решение: добавить deploy.resources для всех сервисов + профиль loadtest
с изолированным k6 контейнером (CPU pinning на ядра 0-1).

## Acceptance Criteria

- [ ] docker-compose.yml — для каждого сервиса указан deploy.resources:
  - [ ] postgres: cpus 1.0, mem_limit 1g, mem_reservation 512m
  - [ ] redis: cpus 0.25, mem_limit 256m, mem_reservation 128m
  - [ ] backend: cpus 1.0, mem_limit 512m, mem_reservation 256m, pids_limit 200
  - [ ] frontend: cpus 0.25, mem_limit 128m, mem_reservation 64m
- [ ] Профиль loadtest с k6:
  - [ ] image: grafana/k6:0.54.0
  - [ ] profiles: ["loadtest"]
  - [ ] network_mode: host
  - [ ] cpus 2.0, mem_limit 1g
  - [ ] cpuset: "0,1" — CPU pinning
  - [ ] volumes: ./tests/load:/scripts:ro, ./docs/load-profiles/reports:/reports:rw
  - [ ] env: K6_WEB_DASHBOARD=true, K6_WEB_DASHBOARD_PORT=5665
- [ ] YAML-комментарии с обоснованием (R6 ≤ 15 GB, R3 reproducible)
- [ ] tests/test_compose_resources.py — RED тесты:
  - [ ] Все сервисы имеют deploy.resources.limits.memory
  - [ ] Все сервисы имеют deploy.resources.limits.cpus
  - [ ] k6 в профиле loadtest
  - [ ] k6 имеет cpuset
- [ ] make up запускается без изменений
- [ ] make up-loadtest запускает k6

## Technical Notes

**docker-compose.yml fragment (k6):**

```yaml
  k6:
    image: grafana/k6:0.54.0
    container_name: transit-ai-k6
    profiles: ["loadtest"]
    network_mode: host  # Прямой доступ к localhost:8000
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 1G
        reservations:
          cpus: "1.0"
          memory: 512M
    volumes:
      - ./tests/load:/scripts:ro
      - ./docs/load-profiles/reports:/reports:rw
    environment:
      K6_WEB_DASHBOARD: "true"
      K6_WEB_DASHBOARD_PORT: "5665"
      K6_WEB_DASHBOARD_OPEN: "false"
```

**backend resources:**
```yaml
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M     # 256MB/worker × 2 workers
          pids_limit: 200
        reservations:
          cpus: "0.5"
          memory: 256M
```

**tests/test_compose_resources.py:**

```python
from pathlib import Path
import yaml

COMPOSE = Path(__file__).resolve().parents[1] / "docker-compose.yml"

def load_compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text())

def test_all_services_have_memory_limit():
    compose = load_compose()
    for name, cfg in compose["services"].items():
        if name == "k6":
            continue
        mem = cfg.get("deploy", {}).get("resources", {}).get("limits", {}).get("memory")
        assert mem is not None, f"Service {name!r} missing memory limit"

def test_k6_profile_exists():
    compose = load_compose()
    k6 = compose["services"].get("k6")
    assert k6 is not None, "k6 service missing"
    assert "loadtest" in k6.get("profiles", [])

def test_k6_has_cpu_pinning():
    compose = load_compose()
    k6 = compose["services"]["k6"]
    cpuset = k6.get("cpuset", None) or \
             k6.get("deploy", {}).get("resources", {}).get("limits", {}).get("cpuset")
    assert cpuset is not None, "k6 missing cpuset (CPU pinning)"
```

## Verification

```bash
uv run pytest tests/test_compose_resources.py -v
docker compose config | head -20
docker compose --profile loadtest up -d k6
docker stats --no-stream backend  # MEM LIMIT 512MiB
```

## Beneficiary Impact

Жюри (5/5) — R3 compliance.
Команда (4/5) — предсказуемое потребление.
Измерения (5/5) — CPU pinning гарантирует изоляцию.

RICE: 7.00 — обязательный компонент.
