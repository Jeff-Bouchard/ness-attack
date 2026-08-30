#!/usr/bin/env bash

# Ness Attack Console launcher
# Builds (if needed) and runs the ness-attack container, starting the
# web UI on a dynamically chosen port.
#
# Usage (from repo root or this directory):
#   bash ./ness-attack/run-console.sh
# Then open the URL printed to your terminal.
#
# Scope: your own host and LAN, authorised lab / production defense only.
# Ethic: EULA applies. Do no harm.

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_USER="${DOCKER_USER:-nessnetwork}"
IMAGE_NAME="${DOCKER_USER}/ness-attack:latest"
CONTAINER_PORT=18080   # Flask port inside the container

# ── Port helpers (Git Bash on Windows; netstat is native) ──────────

function port_in_use() {
  local port=$1
  # Windows netstat is on PATH inside Git Bash
  netstat -ano 2>/dev/null | grep -q ":${port} .*LISTENING"
}

function find_free_port() {
  # Per convention: random port in 50000–59999 range
  local port
  local attempts=0
  while (( attempts < 100 )); do
    port=$(( RANDOM % 10000 + 50000 ))
    if ! port_in_use "$port"; then
      echo "$port"
      return 0
    fi
    attempts=$(( attempts + 1 ))
  done
  echo "[attack-console] FATAL: could not find a free port in 50000-59999 after 100 attempts." >&2
  exit 1
}

function kill_port() {
  local port=$1
  local pid
  pid=$(netstat -ano 2>/dev/null | grep ":${port} .*LISTENING" | awk '{print $NF}' | head -1)
  if [[ -n "$pid" && "$pid" =~ ^[0-9]+$ ]]; then
    taskkill //PID "$pid" //F 2>/dev/null && \
      echo "[attack-console] Killed PID $pid on port $port." || \
      echo "[attack-console] taskkill failed for PID $pid." >&2
  else
    echo "[attack-console] Could not identify PID on port $port." >&2
    return 1
  fi
}

# ── Pre-flight checks ──────────────────────────────────────────────

if ! command -v docker >/dev/null 2>&1; then
  echo "[attack-console] docker is required but not installed or not in PATH." >&2
  exit 1
fi

# Pick a host port: try the container port first, fall back to random >50000
HOST_PORT="$CONTAINER_PORT"
if port_in_use "$HOST_PORT"; then
  echo "[attack-console] Port $HOST_PORT is in use."
  read -rp "Kill the process on port $HOST_PORT? [y/N]: " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    if kill_port "$HOST_PORT"; then
      sleep 1
    else
      HOST_PORT=$(find_free_port)
    fi
  else
    HOST_PORT=$(find_free_port)
  fi
fi

echo "[attack-console] Host port: $HOST_PORT  →  container port: $CONTAINER_PORT"

# ── Build image if missing ─────────────────────────────────────────

if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "[attack-console] Building $IMAGE_NAME from ${SCRIPT_DIR##*/}..."
  ( cd "$REPO_ROOT" && docker build -t "$IMAGE_NAME" ./ness-attack )
fi

# ── Launch ─────────────────────────────────────────────────────────

echo "[attack-console] Starting Ness Attack web console on http://127.0.0.1:${HOST_PORT}"
echo "[attack-console] Press Ctrl-C to stop."

docker run --rm \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  "$IMAGE_NAME" \
  bash -lc 'command -v python3 >/dev/null 2>&1 && python3 /opt/ness-attack-webui/app.py || python /opt/ness-attack-webui/app.py'
