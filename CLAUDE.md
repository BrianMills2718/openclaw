# ops/openclaw

This directory contains the versioned OpenClaw runtime assets mirrored from the
live `$HOME/.openclaw` runtime.

## Use This Directory For

- queue runner and review-cycle code
- runtime defaults and launch utilities
- versioned prompt, schema, and template assets

## Route Narrower Work

- prompt templates -> `prompts/`
- report schemas -> `schemas/`
- task graph templates -> `templates/`

## Working Rules

- The mirror path in this repo is canonical. The runtime path under
  `$HOME/.openclaw` should be a symlink to these files, not a hand-maintained
  copy.
- OpenClaw is an orchestration layer, not the home of repo-local governance.
- When runtime behavior changes, update tests and README-level operator docs in
  the same change.
