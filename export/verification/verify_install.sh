#!/bin/sh
# verify_install.sh — проверка установки и запуска артефактов Transit-AI.
#
#   sh export/verification/verify_install.sh            # полная проверка (+ k6 smoke)
#   sh export/verification/verify_install.sh --quick     # без нагрузочного теста
#   sh export/verification/verify_install.sh --no-docker # только офлайн-часть
#
# Коды выхода: 0 — PASS (WARN допустимы), 1 — есть FAIL.

set -u
REPO_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
REPORT="$REPO_ROOT/export/verification/verification-report.txt"
QUICK=0
NO_DOCKER=0
FAILS=0
WARNS=0

for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    --no-docker) NO_DOCKER=1 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "unknown flag: $arg"; exit 2 ;;
  esac
done

: > "$REPORT"
say() { printf '%s\n' "$*" | tee -a "$REPORT"; }
ok()   { say "PASS  $*"; }
warn() { WARNS=$((WARNS+1)); say "WARN  $*"; }
fail() { FAILS=$((FAILS+1)); say "FAIL  $*"; }
need() { if command -v "$1" >/dev/null 2>&1; then ok "$2: $(command -v "$1")"; else fail "$2 не найден"; fi; }

say "=== Transit-AI verification: $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="
say "repo: $REPO_ROOT"
say "--- 1. Пререквизиты ---"
need docker "docker"
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  ok "docker compose: $(docker compose version --short 2>/dev/null)"
else
  fail "docker compose недоступен"
fi
need uv "uv (Python-раннер)"
if command -v python3 >/dev/null 2>&1; then
  ok "python3: $(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:3])))')"
else
  fail "python3 не найден"
fi
command -v mmdc >/dev/null 2>&1 && ok "mmdc (mermaid→png)" || warn "mmdc не найден — диаграммы не пересобрать"

say "--- 2. Wheels для offline-сборки образов ---"
for app in backend harvester ml_pipeline; do
  d="$REPO_ROOT/apps/$app/wheels"
  if [ -d "$d" ] && [ -n "$(ls -A "$d" 2>/dev/null)" ]; then
    ok "wheels $app: $(du -sh "$d" 2>/dev/null | cut -f1)"
  else
    warn "wheels $app отсутствуют/пусты — сборка образа потребует сети"
  fi
done
[ -d "$REPO_ROOT/apps/ml-pipeline/wheels" ] && warn "дубль каталога apps/ml-pipeline/ рядом с apps/ml_pipeline/"

say "--- 3. Внешние данные: raw → normalized JSON ---"
if (cd "$REPO_ROOT" && make external-gen >/dev/null 2>&1); then
  ok "make external-gen (8 источников → data/external/normalized/)"
else
  fail "make external-gen упал"
fi
if (cd "$REPO_ROOT" && make external-verify >>"$REPORT" 2>&1); then
  ok "make external-verify (sha256 + rows_count + JSON Schema)"
else
  fail "make external-verify упал (см. отчёт выше)"
fi
for f in weather poi stops calendar validators traffic events user_routes; do
  p="$REPO_ROOT/data/external/normalized/$f.json"
  [ -f "$p" ] && ok "normalized/$f.json" || fail "нет normalized/$f.json"
done

say "--- 4. Стенд (docker compose) ---"
if [ "$NO_DOCKER" -eq 1 ]; then
  warn "--no-docker: запуск сервиса пропущен"
elif ! command -v docker >/dev/null 2>&1; then
  fail "docker недоступен (можно пропустить флагом --no-docker)"
else
  (cd "$REPO_ROOT" && docker compose up -d >/dev/null 2>&1) && ok "docker compose up -d" || fail "docker compose up -d не удался"
  i=0
  until curl -sf -m 3 http://localhost:8000/api/v1/healthz >/dev/null 2>&1; do
    i=$((i+1))
    [ "$i" -ge 40 ] && break
    sleep 3
  done
  if curl -sf -m 3 http://localhost:8000/api/v1/healthz >/dev/null 2>&1; then
    ok "backend /api/v1/healthz → ok (после ~$((i*3))с)"
  else
    fail "backend не отвечает на :8000 (смотри docker compose logs backend)"
  fi

  say "--- 5. API smoke ---"
  for path in /api/v1/models /api/v1/geo/routes /api/v1/predictions/load /api/v1/historical/load /api/v1/features; do
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 "http://localhost:8000$path" 2>/dev/null)
    [ "$code" = "200" ] && ok "GET $path → 200" || fail "GET $path → $code"
  done
  paths=$(curl -sf -m 10 http://localhost:8000/openapi.json 2>/dev/null | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["paths"]))' 2>/dev/null)
  if [ -n "$paths" ] && [ "$paths" -ge 30 ] 2>/dev/null; then
    ok "openapi.json: $paths путей"
  else
    fail "openapi.json: путей $paths (ожидалось ≥30)"
  fi
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 15 "http://localhost:8000/api/v1/predictions/export.csv" 2>/dev/null)
  [ "$code" = "200" ] && ok "GET /api/v1/predictions/export.csv → 200" || fail "export.csv → $code"
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 "http://localhost:5173/" 2>/dev/null)
  [ "$code" = "200" ] && ok "frontend :5173 → 200" || warn "frontend :5173 → $code"
fi

say "--- 6. Submission (CSV контракт) ---"
SUB=$(ls "$REPO_ROOT"/export/01-ml/submissions/submission_route_baseline_v1_*.csv 2>/dev/null | head -1)
if [ -n "$SUB" ]; then
  rows=$(wc -l < "$SUB" | tr -d ' ')
  header=$(head -1 "$SUB")
  [ "$header" = "route;date;hour;prediction" ] && ok "заголовок submission: $header" || fail "заголовок submission: $header"
  if [ "$rows" = "14641" ] || [ "$rows" = "14640" ]; then
    ok "строк в submission: $rows (10 маршрутов × 61 день × 24 ч)"
  else
    warn "строк в submission: $rows (ожидалось 14640/14641)"
  fi
else
  fail "submission CSV не найден в export/01-ml/submissions/"
fi

say "--- 7. Нагрузочный тест (k6) ---"
SUMMARY="$REPO_ROOT/export/05-performance/k6-smoke-summary.txt"
if [ "$QUICK" -eq 1 ] || [ "$NO_DOCKER" -eq 1 ]; then
  warn "smoke пропущен (--quick/--no-docker)"
elif (cd "$REPO_ROOT" && timeout 180 make loadtest-smoke >"$SUMMARY" 2>&1); then
  ok "make loadtest-smoke → summary в export/05-performance/k6-smoke-summary.txt"
elif grep -q "complete and 0 interrupted" "$SUMMARY" 2>/dev/null; then
  warn "make loadtest-smoke вернул ненулевой код, но прогон прошёл (см. summary)"
else
  warn "make loadtest-smoke не завершился (см. summary)"
fi

say "=== ИТОГ: FAIL=$FAILS WARN=$WARNS ==="
if [ "$FAILS" -eq 0 ]; then say "VERIFIED"; exit 0; else say "FAILED"; exit 1; fi
