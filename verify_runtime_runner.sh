#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_RUNNER="$(readlink -f "${SCRIPT_DIR}/run_task.py")"
TARGET_RUNNER="${OPENCLAW_RUNTIME_RUNNER:-$HOME/.openclaw/bin/run_task.py}"
PYTHON_BIN="${OPENCLAW_RUNTIME_PYTHON:-python3}"
PROJECTS_ROOT="${PROJECTS_ROOT:-$HOME/projects}"

if [[ ! -e "${TARGET_RUNNER}" ]]; then
  echo "Runtime runner missing: ${TARGET_RUNNER}" >&2
  exit 1
fi

if [[ ! -L "${TARGET_RUNNER}" ]]; then
  echo "Runtime runner is not a symlink: ${TARGET_RUNNER}" >&2
  echo "Run: bash install_runtime_runner.sh" >&2
  exit 1
fi

TARGET_REALPATH="$(readlink -f "${TARGET_RUNNER}")"
if [[ "${TARGET_REALPATH}" != "${SOURCE_RUNNER}" ]]; then
  echo "Runtime runner drift detected." >&2
  echo "  expected: ${SOURCE_RUNNER}" >&2
  echo "  actual:   ${TARGET_REALPATH}" >&2
  echo "Run: bash install_runtime_runner.sh" >&2
  exit 1
fi

echo "Runtime runner synced: ${TARGET_RUNNER} -> ${SOURCE_RUNNER}"

PYTHONPATH_PREFIX="${PROJECTS_ROOT}/llm_client:${PROJECTS_ROOT}/agentic_scaffolding"
if ! PYTHONPATH="${PYTHONPATH_PREFIX}${PYTHONPATH:+:${PYTHONPATH}}" "${PYTHON_BIN}" - <<'PY'
from llm_client import acall_llm  # noqa: F401
import claude_agent_sdk  # noqa: F401
PY
then
  echo "Runtime Python environment is missing required shared imports." >&2
  echo "Expected to import llm_client public facade and claude_agent_sdk using:" >&2
  echo "  PROJECTS_ROOT=${PROJECTS_ROOT}" >&2
  echo "  OPENCLAW_RUNTIME_PYTHON=${PYTHON_BIN}" >&2
  echo "Install with: ${PYTHON_BIN} -m pip install -e \"${PROJECTS_ROOT}/llm_client[agents]\"" >&2
  exit 1
fi

echo "Runtime Python environment verified: llm_client facade + claude_agent_sdk importable"
