#!/usr/bin/env bash
# Starts the local backend and Vite UI when needed, then opens the workspace.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/.run"
BACKEND_URL="http://127.0.0.1:8000/api/v1/health"
FRONTEND_URL="http://127.0.0.1:5173"

mkdir -p "$RUNTIME_DIR"

is_ready() {
  curl --fail --silent --max-time 1 "$1" >/dev/null 2>&1
}

start_backend() {
  if is_ready "$BACKEND_URL"; then
    return
  fi
  nohup bash -c '
    cd "$1"
    uv run --directory backend alembic upgrade head
    exec uv run --directory backend uvicorn agentgraph.app:app --host 127.0.0.1 --port 8000
  ' _ "$ROOT_DIR" >>"$RUNTIME_DIR/backend.log" 2>&1 &
  echo $! >"$RUNTIME_DIR/backend.pid"
}

start_frontend() {
  if is_ready "$FRONTEND_URL"; then
    return
  fi
  nohup bash -c '
    cd "$1"
    exec pnpm --dir frontend dev -- --host 127.0.0.1 --port 5173 --strictPort
  ' _ "$ROOT_DIR" >>"$RUNTIME_DIR/frontend.log" 2>&1 &
  echo $! >"$RUNTIME_DIR/frontend.pid"
}

wait_for() {
  local url="$1"
  local name="$2"
  for _ in {1..30}; do
    if is_ready "$url"; then
      return
    fi
    sleep 1
  done
  printf '%s did not become ready. See %s.\n' "$name" "$RUNTIME_DIR" >&2
  exit 1
}

start_backend
wait_for "$BACKEND_URL" "Backend"
start_frontend
wait_for "$FRONTEND_URL" "Frontend"

xdg-open "$FRONTEND_URL" >/dev/null 2>&1 &
printf 'AgentGraph OS is ready at %s\n' "$FRONTEND_URL"
