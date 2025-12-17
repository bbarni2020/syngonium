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

echo "[start] Launching app: python -m app.main"
exec python -u -m app.main
