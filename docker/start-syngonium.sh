#!/usr/bin/env bash
set -euo pipefail

REPO_URL=${GIT_REPO:-}
if [[ -z "$REPO_URL" ]]; then
  echo "[start] GIT_REPO is required (e.g. https://github.com/<owner>/<repo>.git)" >&2
  exit 2
fi
BRANCH=${GIT_BRANCH:-main}
APP_DIR=${APP_DIR:-/srv/app}

if ! command -v git >/dev/null 2>&1; then
  echo "[start] Installing git"
  apt-get update -y
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends git ca-certificates
  rm -rf /var/lib/apt/lists/*
fi

mkdir -p "${APP_DIR%/}"
cd "${APP_DIR%/}"/..
BASE_DIR=$(pwd)

if [[ -d "$APP_DIR/.git" ]]; then
  echo "[start] Existing repo found at $APP_DIR — pulling latest"
  cd "$APP_DIR"
  git fetch --all --prune
  git checkout "$BRANCH" || true
  git pull --ff-only --tags origin "$BRANCH" || true
else
  echo "[start] Cloning $REPO_URL (branch: $BRANCH)"
  git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

if [[ -f requirements.txt ]]; then
  echo "[start] Installing Python requirements"
  python -m pip install --no-cache-dir --upgrade pip
  python -m pip install --no-cache-dir -r requirements.txt
fi

export PYTHONUNBUFFERED=1
export PYTHONPATH="$APP_DIR"

COMMIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
export GIT_COMMIT_HASH="$COMMIT_HASH"
echo "[start] Current commit: $COMMIT_HASH"

CHECK_INTERVAL=${UPDATE_CHECK_INTERVAL:-300}

APP_PID=""

start_app() {
  echo "[start] Launching app: python -m app.main"
  python -u -m app.main &
  APP_PID=$!
  echo "[start] App started with PID $APP_PID"
}

stop_app() {
  if [[ -n "$APP_PID" ]] && kill -0 "$APP_PID" 2>/dev/null; then
    echo "[start] Stopping app (PID $APP_PID)"
    kill -TERM "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
  fi
}

check_for_updates() {
  git fetch --all --prune >/dev/null 2>&1
  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse origin/"$BRANCH" 2>/dev/null || echo "$LOCAL")
  if [[ "$LOCAL" != "$REMOTE" ]]; then
    echo "[start] New commit detected: $REMOTE — restarting"
    stop_app
    git reset --hard origin/"$BRANCH"
    if [[ -f requirements.txt ]]; then
      python -m pip install --no-cache-dir -r requirements.txt
    fi
    COMMIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    export GIT_COMMIT_HASH="$COMMIT_HASH"
    echo "[start] Updated to commit: $COMMIT_HASH"
    start_app
  fi
}

trap 'stop_app; exit 0' SIGTERM SIGINT

start_app

while true; do
  sleep "$CHECK_INTERVAL"
  if ! kill -0 "$APP_PID" 2>/dev/null; then
    echo "[start] App crashed, restarting"
    start_app
  else
    check_for_updates
  fi
done
