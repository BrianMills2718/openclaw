# Round 1 Implementation Note

- Changed files: `README.md`
- Tests run:
  - `pytest -q tests/test_runtime_bootstrap_imports.py -k 'codex_transport'` -> `2 passed`
  - `pytest -q tests/test_runtime_bootstrap_imports.py` -> fails in this session because a preloaded llm_client override path leads several unrelated bootstrap path-ordering assertions to see `/home/brian/projects/llm_client_worktrees/codex-transport-fallback` at `sys.path[0]`
- Residual risks:
  - The README is now aligned with `_bootstrap_runtime_env_defaults()`, but the broader bootstrap smoke file remains environment-sensitive when this worktree is launched with an llm_client override already pinned at the front of `sys.path`
- Commit sha: `9db08d0`
