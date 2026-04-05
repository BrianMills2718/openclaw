"""Git utilities for runtime-cluster diff correlation.

These helpers classify changed files and summarize git state for OpenClaw's
task-graph/analyzer loop. They live in `moltbot` because the runtime cluster
belongs to the orchestration layer, not to `project-meta`.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import PurePosixPath

logger = logging.getLogger(__name__)

PROMPT_CHANGE = "PROMPT_CHANGE"
RUBRIC_CHANGE = "RUBRIC_CHANGE"
CODE_CHANGE = "CODE_CHANGE"
CONFIG_CHANGE = "CONFIG_CHANGE"
TEST_CHANGE = "TEST_CHANGE"


def get_git_head(cwd: str | None = None) -> str | None:
    """Return the short SHA for HEAD, or None when git is unavailable."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def get_diff_files(commit_a: str, commit_b: str, cwd: str | None = None) -> list[str]:
    """Return the changed file paths between two git revisions."""

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", commit_a, commit_b],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd,
        )
        if result.returncode != 0:
            logger.debug("git diff failed: %s", result.stderr.strip())
            return []
        return [line for line in result.stdout.strip().splitlines() if line]
    except Exception:
        logger.debug("get_diff_files failed", exc_info=True)
        return []


def get_working_tree_files(cwd: str | None = None) -> list[str]:
    """Return the staged, unstaged, and untracked file paths in the working tree."""

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=cwd,
        )
        if result.returncode != 0:
            logger.debug("git status failed: %s", result.stderr.strip())
            return []

        files: list[str] = []
        for raw_line in result.stdout.splitlines():
            line = raw_line.rstrip()
            if len(line) < 4:
                continue
            path_part = line[3:]
            if " -> " in path_part:
                path_part = path_part.split(" -> ", 1)[1]
            if path_part:
                files.append(path_part)
        return list(dict.fromkeys(files))
    except Exception:
        logger.debug("get_working_tree_files failed", exc_info=True)
        return []


def is_git_dirty(cwd: str | None = None) -> bool:
    """Return True when the current working tree has local changes."""

    return bool(get_working_tree_files(cwd=cwd))


def classify_diff_files(files: list[str]) -> set[str]:
    """Classify a changed-file list into coarse runtime-cluster categories."""

    categories: set[str] = set()
    for file_path in files:
        path = PurePosixPath(file_path)
        parts = path.parts
        name = path.name

        if "prompts" in parts:
            categories.add(PROMPT_CHANGE)
            continue
        if "rubrics" in parts:
            categories.add(RUBRIC_CHANGE)
            continue
        if "tests" in parts or name.startswith("test_"):
            categories.add(TEST_CHANGE)
            continue
        if name.endswith(".py"):
            categories.add(CODE_CHANGE)
            continue
        if name.endswith((".yaml", ".yml", ".json", ".toml")):
            categories.add(CONFIG_CHANGE)

    return categories
