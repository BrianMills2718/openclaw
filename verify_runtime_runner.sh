#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_RUNNER="$(readlink -f "${SCRIPT_DIR}/run_task.py")"
TARGET_RUNNER="${OPENCLAW_RUNTIME_RUNNER:-$HOME/.openclaw/bin/run_task.py}"

if [[ ! -e "${TARGET_RUNNER}" ]]; then
  echo "Runtime runner missing: ${TARGET_RUNNER}" >&2
  exit 1
fi

if [[ ! -L "${TARGET_RUNNER}" ]]; then
  echo "Runtime runner is not a symlink: ${TARGET_RUNNER}" >&2
  echo "Run: bash project-meta/ops/openclaw/install_runtime_runner.sh" >&2
  exit 1
fi

TARGET_REALPATH="$(readlink -f "${TARGET_RUNNER}")"
if [[ "${TARGET_REALPATH}" != "${SOURCE_RUNNER}" ]]; then
  echo "Runtime runner drift detected." >&2
  echo "  expected: ${SOURCE_RUNNER}" >&2
  echo "  actual:   ${TARGET_REALPATH}" >&2
  echo "Run: bash project-meta/ops/openclaw/install_runtime_runner.sh" >&2
  exit 1
fi

echo "Runtime runner synced: ${TARGET_RUNNER} -> ${SOURCE_RUNNER}"
