"""Moltbot-local analyzer shim delegating to the repo-local analyzer module."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any


def _prepend_repo_root_if_present(path: Path) -> None:
    """Prepend a repo root when it exists and is not already importable."""

    if not path.is_dir():
        return
    resolved = str(path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


_REPO_ROOT = Path(__file__).resolve().parents[2]
_prepend_repo_root_if_present(_REPO_ROOT)

_PROJECTS_ROOT = Path(
    os.environ.get("PROJECTS_ROOT", str(Path.home() / "projects"))
).expanduser().resolve()
for _repo_name in ("llm_client", "agentic_scaffolding"):
    _prepend_repo_root_if_present(_PROJECTS_ROOT / _repo_name)
_ANALYZER_PATH = _REPO_ROOT / "analyzer.py"
if not _ANALYZER_PATH.is_file():
    raise FileNotFoundError(f"Expected canonical analyzer implementation at {_ANALYZER_PATH}")

_SPEC = importlib.util.spec_from_file_location("_moltbot_analyzer_runtime", _ANALYZER_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Could not load analyzer spec from {_ANALYZER_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

analyze_run = _MODULE.analyze_run
analyze_history = _MODULE.analyze_history
Proposal = _MODULE.Proposal
AnalysisReport = _MODULE.AnalysisReport
Proposal.model_rebuild(force=True, _types_namespace={"Any": Any})
AnalysisReport.model_rebuild(
    force=True,
    _types_namespace={"Any": Any, "Proposal": Proposal},
)
