# ops/openclaw/templates

This directory contains reusable OpenClaw task-graph templates.

## Use This Directory For

- declarative task graphs and handoff templates consumed by runtime launchers

## Working Rules

- Keep templates generic enough to reuse across tasks.
- If a template requires repo-specific instructions, point the runtime back to
  the target repo's local governance instead of embedding shadow policy here.
