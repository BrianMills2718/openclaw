"""Tests for moltbot.git_utils."""

from __future__ import annotations

from git_utils import CODE_CHANGE
from git_utils import CONFIG_CHANGE
from git_utils import PROMPT_CHANGE
from git_utils import RUBRIC_CHANGE
from git_utils import TEST_CHANGE
from git_utils import classify_diff_files
from git_utils import get_git_head
from git_utils import get_working_tree_files
from git_utils import is_git_dirty


def test_classify_prompt_files() -> None:
    files = ["prompts/extract.yaml", "prompts/judge.yaml"]
    assert classify_diff_files(files) == {PROMPT_CHANGE}


def test_classify_rubric_files() -> None:
    files = ["rubrics/research_quality.yaml"]
    assert classify_diff_files(files) == {RUBRIC_CHANGE}


def test_classify_code_files() -> None:
    files = ["llm_client/analyzer.py", "llm_client/client.py"]
    assert classify_diff_files(files) == {CODE_CHANGE}


def test_classify_config_files() -> None:
    files = ["config.yaml", "pyproject.toml", "settings.json"]
    assert classify_diff_files(files) == {CONFIG_CHANGE}


def test_classify_test_files() -> None:
    files = ["tests/test_analyzer.py", "test_utils.py"]
    assert classify_diff_files(files) == {TEST_CHANGE}


def test_classify_mixed() -> None:
    files = [
        "prompts/extract.yaml",
        "llm_client/analyzer.py",
        "tests/test_analyzer.py",
        "config.yaml",
    ]
    assert classify_diff_files(files) == {
        PROMPT_CHANGE,
        CODE_CHANGE,
        TEST_CHANGE,
        CONFIG_CHANGE,
    }


def test_classify_empty() -> None:
    assert classify_diff_files([]) == set()


def test_classify_nested_prompts() -> None:
    files = ["llm_client/prompts/rubric_judge.yaml"]
    assert classify_diff_files(files) == {PROMPT_CHANGE}


def test_get_git_head_returns_string() -> None:
    result = get_git_head()
    assert result is not None
    assert len(result) >= 7


def test_get_git_head_nonexistent_dir() -> None:
    assert get_git_head(cwd="/nonexistent/path/that/does/not/exist") is None


def test_get_working_tree_files_type() -> None:
    files = get_working_tree_files()
    assert isinstance(files, list)
    assert all(isinstance(file_path, str) for file_path in files)


def test_get_working_tree_files_nonexistent_dir() -> None:
    assert get_working_tree_files(cwd="/nonexistent/path/that/does/not/exist") == []


def test_is_git_dirty_returns_bool() -> None:
    assert isinstance(is_git_dirty(), bool)


def test_is_git_dirty_nonexistent_dir() -> None:
    assert is_git_dirty(cwd="/nonexistent/path/that/does/not/exist") is False
