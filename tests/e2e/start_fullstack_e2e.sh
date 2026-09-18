#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP_DIR="$PROJECT_ROOT/.tmp/e2e_fullstack"
BACKEND_PID_FILE="$TMP_DIR/backend.pid"
FRONTEND_PID_FILE="$TMP_DIR/frontend.pid"
REDIS_PID_FILE="$TMP_DIR/redis.pid"
SMTP_PID_FILE="$TMP_DIR/smtp.pid"
BACKEND_LOG_FILE="$TMP_DIR/backend.log"
FRONTEND_LOG_FILE="$TMP_DIR/frontend.log"
SMTP_LOG_FILE="$TMP_DIR/smtp.log"
SMTP_INBOX_FILE="$TMP_DIR/smtp_inbox.json"

SMTP_PID=""
BACKEND_PID=""
FRONTEND_PID=""
SMTP_TAIL_PID=""
BACKEND_TAIL_PID=""
FRONTEND_TAIL_PID=""
_CLEANED_UP=0

log() {
  echo "[e2e_fullstack] $*"
}

pick_python() {
  if command -v python3.13 >/dev/null 2>&1; then
    echo "python3.13"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return 0
  fi
  return 1
}

kill_pid() {
  local pid="$1"
  local label="$2"
  if [ -z "$pid" ]; then
    return 0
  fi
  if kill -0 "$pid" 2>/dev/null; then
    log "stopping $label pid=$pid"
    kill "$pid" 2>/dev/null || true
    sleep 1
  fi
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null || true
  fi
}

cleanup_pid_file() {
  local file="$1"
  local label="$2"
  if [ -f "$file" ]; then
    local pid
    pid="$(cat "$file" 2>/dev/null || true)"
    if [ -n "$pid" ]; then
      kill_pid "$pid" "$label"
    fi
    # In some runners, path allowlist parsing can mis-handle ':' in absolute paths.
    # Cleanup should stay best-effort and must not abort startup.
    rm -f "$file" 2>/dev/null || log "warn: failed to remove pid file $file"
  fi
}

kill_port_processes() {
  local port="$1"
  local pids
  pids="$(lsof -ti tcp:"$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    log "cleaning occupied port $port"
    for pid in $pids; do
      kill_pid "$pid" "port-$port"
    done
  fi
}

kill_by_pattern() {
  local pattern="$1"
  local label="$2"
  local pids
  pids="$(pgrep -f "$pattern" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    for pid in $pids; do
      if [ "$pid" != "$$" ]; then
        kill_pid "$pid" "$label"
      fi
    done
  fi
}

cleanup_all() {
  if [ "$_CLEANED_UP" -eq 1 ]; then
    return 0
  fi
  _CLEANED_UP=1
  set +e
  kill_pid "$SMTP_PID" "smtp-capture"
  kill_pid "$FRONTEND_PID" "frontend"
  kill_pid "$BACKEND_PID" "backend"
  kill_pid "$SMTP_TAIL_PID" "smtp-tail"
  kill_pid "$FRONTEND_TAIL_PID" "frontend-tail"
  kill_pid "$BACKEND_TAIL_PID" "backend-tail"
  cleanup_pid_file "$SMTP_PID_FILE" "smtp-pidfile"
  cleanup_pid_file "$FRONTEND_PID_FILE" "frontend-pidfile"
  cleanup_pid_file "$BACKEND_PID_FILE" "backend-pidfile"
}

trap cleanup_all EXIT INT TERM

mkdir -p "$TMP_DIR"

log "startup cleanup begin"
cleanup_pid_file "$TMP_DIR/backend.pid" "backend-pidfile"
cleanup_pid_file "$TMP_DIR/frontend.pid" "frontend-pidfile"
cleanup_pid_file "$TMP_DIR/redis.pid" "redis-pidfile"
cleanup_pid_file "$TMP_DIR/smtp.pid" "smtp-pidfile"
cleanup_pid_file "$PROJECT_ROOT/.tmp/dev_up/backend.pid" "legacy-backend-pidfile"
cleanup_pid_file "$PROJECT_ROOT/.tmp/dev_up/frontend.pid" "legacy-frontend-pidfile"
cleanup_pid_file "$PROJECT_ROOT/.tmp/dev_up/redis.pid" "legacy-redis-pidfile"

kill_port_processes 3025
kill_port_processes 8025
kill_port_processes 8000
kill_port_processes 5173
kill_port_processes 5174
kill_by_pattern "uvicorn backend.main:app" "legacy-uvicorn"
kill_by_pattern "$PROJECT_ROOT/frontend.*vite" "legacy-vite"
kill_by_pattern "$PROJECT_ROOT/frontend.*npm run dev" "legacy-npm-dev"
log "startup cleanup done"

if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  # Always prefer project venv python to avoid interpreter mismatch.
  PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
  if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.venv/bin/activate"
  fi
else
  PYTHON_BIN="$(pick_python)"
  if [ -z "$PYTHON_BIN" ]; then
    echo "[e2e_fullstack] python not found"
    exit 1
  fi
fi

"$PYTHON_BIN" - <<'PY'
import sys
assert sys.version_info >= (3, 10), "Python version must be >= 3.10"
print("Python version OK")
PY

if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import importlib
import sys

required_modules = ("langgraph", "multipart", "pypdf", "docx", "boto3")
missing = []
for module_name in required_modules:
    try:
        importlib.import_module(module_name)
    except Exception:
        missing.append(module_name)

if missing:
    print("missing modules:", ", ".join(missing))
    sys.exit(1)
PY
then
  log "backend python deps missing in selected python, installing backend requirements"
  "$PYTHON_BIN" -m pip install -r "$PROJECT_ROOT/backend/requirements.txt"
fi

if ! command -v redis-cli >/dev/null 2>&1; then
  echo "[e2e_fullstack] redis-cli not found"
  exit 1
fi
if ! command -v redis-server >/dev/null 2>&1; then
  echo "[e2e_fullstack] redis-server not found"
  exit 1
fi

if redis-cli ping >/dev/null 2>&1; then
  log "redis already running"
else
  log "starting redis-server"
  redis-server --daemonize yes
  sleep 1
fi

if ! redis-cli ping >/dev/null 2>&1; then
  echo "[e2e_fullstack] redis start failed"
  exit 1
fi

if pgrep -f "redis-server.*6379" >/dev/null 2>&1; then
  pgrep -f "redis-server.*6379" | head -n 1 > "$REDIS_PID_FILE"
fi

rm -f "$BACKEND_LOG_FILE" "$FRONTEND_LOG_FILE" "$SMTP_LOG_FILE" "$SMTP_INBOX_FILE" 2>/dev/null || true
touch "$BACKEND_LOG_FILE" "$FRONTEND_LOG_FILE" "$SMTP_LOG_FILE"

tail -n 0 -F "$SMTP_LOG_FILE" | sed -u 's/^/[smtp] /' &
SMTP_TAIL_PID="$!"
tail -n 0 -F "$BACKEND_LOG_FILE" | sed -u 's/^/[backend] /' &
BACKEND_TAIL_PID="$!"
tail -n 0 -F "$FRONTEND_LOG_FILE" | sed -u 's/^/[frontend] /' &
FRONTEND_TAIL_PID="$!"

export PYTHONPATH="$PROJECT_ROOT"
export ENV="${ENV:-dev}"
export AUTH_DEV_BYPASS_ENABLED="${AUTH_DEV_BYPASS_ENABLED:-false}"
export AUTH_DEV_USER_ID="${AUTH_DEV_USER_ID:-dev-user}"
export AUTH_DEV_TEAM_ID="${AUTH_DEV_TEAM_ID:-00000000-0000-0000-0000-000000000001}"
export DB_URL="sqlite+aiosqlite:///$PROJECT_ROOT/agentforge_preview.db"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/1}"
export MODEL_API_KEY="${MODEL_API_KEY:-test_key}"
export EMAIL_DELIVERY_MODE="smtp"
export SMTP_HOST="${SMTP_HOST:-smtp.qq.com}"
export SMTP_PORT="${SMTP_PORT:-587}"
export SMTP_USERNAME="${SMTP_USERNAME:-}"
export SMTP_PASSWORD="${SMTP_PASSWORD:-}"
export SMTP_FROM_EMAIL="${SMTP_FROM_EMAIL:-$SMTP_USERNAME}"
export SMTP_FROM_NAME="${SMTP_FROM_NAME:-AgentForge}"
export SMTP_USE_TLS="${SMTP_USE_TLS:-true}"
export SMTP_USE_SSL="${SMTP_USE_SSL:-false}"

if [ -z "$SMTP_USERNAME" ] || [ -z "$SMTP_PASSWORD" ] || [ -z "$SMTP_FROM_EMAIL" ]; then
  echo "[e2e_fullstack] SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM_EMAIL must be set for real SMTP tests" >&2
  exit 1
fi

: > "$SMTP_LOG_FILE"
{
  echo "[e2e_fullstack] using configured external smtp provider"
  echo "[e2e_fullstack] smtp host=$SMTP_HOST port=$SMTP_PORT tls=$SMTP_USE_TLS ssl=$SMTP_USE_SSL from=$SMTP_FROM_EMAIL name=$SMTP_FROM_NAME"
} >> "$SMTP_LOG_FILE"
log "using configured external smtp provider host=$SMTP_HOST port=$SMTP_PORT from=$SMTP_FROM_EMAIL"

log "starting backend on 127.0.0.1:8000"
"$PYTHON_BIN" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 > "$BACKEND_LOG_FILE" 2>&1 &
BACKEND_PID="$!"
echo "$BACKEND_PID" > "$BACKEND_PID_FILE"

backend_ready=0
i=0
while [ "$i" -lt 30 ]; do
  if lsof -ti tcp:8000 -sTCP:LISTEN >/dev/null 2>&1; then
    backend_ready=1
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    break
  fi
  sleep 1
  i=$((i + 1))
done

if [ "$backend_ready" -ne 1 ]; then
  echo "[e2e_fullstack] backend failed health check"
  exit 1
fi

log "starting frontend after backend is ready"
(
  cd "$PROJECT_ROOT/frontend" || exit 1
  if [ ! -d "node_modules" ] || [ ! -x "node_modules/.bin/vite" ]; then
    npm install || exit 1
  fi
  # Use the package script instead of invoking the vite binary directly so the
  # same startup path works in restricted environments that explicitly allow
  # `npm run dev` but not arbitrary child binaries.
  npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
) > "$FRONTEND_LOG_FILE" 2>&1 &
FRONTEND_PID="$!"
echo "$FRONTEND_PID" > "$FRONTEND_PID_FILE"

frontend_ready=0
j=0
while [ "$j" -lt 30 ]; do
  if lsof -ti tcp:5173 -sTCP:LISTEN >/dev/null 2>&1; then
    frontend_ready=1
    break
  fi
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    break
  fi
  sleep 1
  j=$((j + 1))
done

if [ "$frontend_ready" -ne 1 ]; then
  echo "[e2e_fullstack] frontend failed to start on 127.0.0.1:5173"
  echo "[e2e_fullstack] check log: $FRONTEND_LOG_FILE"
  exit 1
fi

log "services ready: backend=http://127.0.0.1:8000, frontend=http://127.0.0.1:5173"
log "smtp delivery: external provider $SMTP_HOST:$SMTP_PORT as $SMTP_FROM_EMAIL"
log "sqlite db: $PROJECT_ROOT/agentforge_preview.db"
log "press Ctrl+C to stop all"

while true; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "[e2e_fullstack] backend process exited"
    exit 1
  fi
  if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "[e2e_fullstack] frontend process exited"
    exit 1
  fi
  sleep 1
done
