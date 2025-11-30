#!/usr/bin/env bash
set -euo pipefail


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

VENV_DIR="${VENV_DIR:-${SCRIPT_DIR}/venv}"

ENV_FILE="${ENV_FILE:-/etc/default/syngonium}"
if [[ -f "$ENV_FILE" ]]; then
	source "$ENV_FILE"
fi

SKIP_VENV=${SKIP_VENV:-false}
SKIP_REQUIREMENTS=${SKIP_REQUIREMENTS:-false}
SKIP_AUTO_UPDATE=${SKIP_AUTO_UPDATE:-false}

echo "[run.sh] Starting syngonium: $(date)"

if ! command -v python3 >/dev/null 2>&1; then
	echo "[run.sh] python3 not found in PATH. Aborting." >&2
	exit 1
fi

if [[ "$SKIP_VENV" != "true" && ! -d "$VENV_DIR" ]]; then
	echo "[run.sh] Creating venv at $VENV_DIR"
	python3 -m venv "$VENV_DIR"
fi

ACTIVATE="$VENV_DIR/bin/activate"
if [[ -f "$ACTIVATE" ]]; then
	source "$ACTIVATE"
else
	echo "[run.sh] Warning: venv activate script not found, continuing using system python."
fi

if [[ "$SKIP_REQUIREMENTS" != "true" && -f "$SCRIPT_DIR/requirements.txt" ]]; then
	echo "[run.sh] Upgrading pip and installing requirements"
	python -m pip install --upgrade pip
	python -m pip install -r "$SCRIPT_DIR/requirements.txt"
fi

if [[ "$SKIP_AUTO_UPDATE" != "true" && -d "$SCRIPT_DIR/.git" ]]; then
	echo "[run.sh] Updating local repo via 'git pull'"
	if git config --get remote.origin.url >/dev/null 2>&1; then
		git fetch --all --prune || true
		git pull --ff-only || true
	else
		echo "[run.sh] No 'origin' remote configured; skipping git pull"
	fi
fi

export PYTHONPATH="${SCRIPT_DIR}"

echo "[run.sh] Starting python app"
exec python -u -m app.main
