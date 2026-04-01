#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_RUNNER="${SCRIPT_DIR}/run_task.py"
TARGET_RUNNER="${OPENCLAW_RUNTIME_RUNNER:-$HOME/.openclaw/bin/run_task.py}"

if [[ ! -f "${SOURCE_RUNNER}" ]]; then
  echo "Source runner not found: ${SOURCE_RUNNER}" >&2
  exit 1
fi

mkdir -p "$(dirname "${TARGET_RUNNER}")"
ln -sfn "${SOURCE_RUNNER}" "${TARGET_RUNNER}"
chmod +x "${SOURCE_RUNNER}"

echo "Linked ${TARGET_RUNNER} -> ${SOURCE_RUNNER}"
