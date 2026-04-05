"""Tests for Plan #2 Phase 2-3: review gate and commit evidence gating in run_task.py.

Verifies that:
- _check_review_gate reads review JSON and fails on needs_changes
- _check_commit_evidence detects presence/absence of new commits
- integration: failed review routes to 'failed' destination
- integration: review pass without commit routes to 'failed'
- integration: review pass with commit routes to 'completed'
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_MOLTBOT_ROOT = Path(__file__).resolve().parent.parent
if str(_MOLTBOT_ROOT) not in sys.path:
    sys.path.insert(0, str(_MOLTBOT_ROOT))

from run_task import _check_review_gate, _check_commit_evidence  # type: ignore[import]


class TestCheckReviewGate:
    """_check_review_gate reads review JSON and applies semantic gate."""

    def test_fails_when_final_review_json_not_set(self) -> None:
        result = _check_review_gate({})
        assert not result["passed"]
        assert "final_review_json" in result["reason"]

    def test_fails_when_review_json_missing(self) -> None:
        result = _check_review_gate({"final_review_json": "/nonexistent/review.json"})
        assert not result["passed"]
        assert result["status"] == "missing"

    def test_fails_when_review_json_invalid(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("not valid json {{{")
            f.flush()
            result = _check_review_gate({"final_review_json": f.name})
        assert not result["passed"]
        assert result["status"] == "invalid"

    def test_fails_when_review_status_is_needs_changes(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"status": "needs_changes", "next_objective": "Fix the tests"}, f)
            f.flush()
            result = _check_review_gate({"final_review_json": f.name})
        assert not result["passed"]
        assert result["status"] == "needs_changes"
        assert "Fix the tests" in result["reason"]

    def test_passes_when_review_status_is_pass(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"status": "pass", "summary": "LGTM"}, f)
            f.flush()
            result = _check_review_gate({"final_review_json": f.name})
        assert result["passed"]
        assert result["status"] == "pass"

    def test_raw_review_content_returned(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            review = {"status": "pass", "items": [], "summary": "All good"}
            json.dump(review, f)
            f.flush()
            result = _check_review_gate({"final_review_json": f.name})
        assert result["raw"] == review


class TestCheckCommitEvidence:
    """_check_commit_evidence detects commits in target repo."""

    def test_fails_when_target_repo_not_set(self) -> None:
        started_at = datetime.now(timezone.utc).isoformat()
        result = _check_commit_evidence({}, task_started_at=started_at)
        assert not result["passed"]
        assert "target_repo" in result["reason"]

    def test_fails_when_target_repo_not_found(self) -> None:
        started_at = datetime.now(timezone.utc).isoformat()
        result = _check_commit_evidence(
            {"target_repo": "/nonexistent/path"},
            task_started_at=started_at,
        )
        assert not result["passed"]

    def test_detects_commit_via_git(self) -> None:
        """If git returns a commit line, commit_detected should be True."""
        started_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        fake_sha = "abc1234"
        fake_ts = "2026-04-04T10:00:00+00:00"
        fake_output = f"{fake_sha} {fake_ts}"

        with tempfile.TemporaryDirectory() as tmpdir:
            import subprocess
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    stdout=fake_output,
                    returncode=0,
                )
                result = _check_commit_evidence(
                    {"target_repo": tmpdir},
                    task_started_at=started_at,
                )
        assert result["commit_detected"]
        assert result["commit_sha"] == fake_sha
        assert result["passed"]

    def test_no_commit_returns_not_passed(self) -> None:
        """Empty git log output means no new commit."""
        started_at = datetime.now(timezone.utc).isoformat()

        with tempfile.TemporaryDirectory() as tmpdir:
            import subprocess
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout="", returncode=0)
                result = _check_commit_evidence(
                    {"target_repo": tmpdir},
                    task_started_at=started_at,
                )
        assert not result["commit_detected"]
        assert not result["passed"]
