---
title: Hooks
description: Deterministic lifecycle hooks for controlling agent behavior (Cursor and compatible hook systems).
---

# Hooks

Hooks are **deterministic scripts** that run at defined points in an agent loop (before shell execution, before reading files, after edits, at stop, etc). Unlike rules, hooks can **block, allow, or modify** actions reliably because they execute outside the model.

This repo ships an **optional Cursor hooks pack** under `hooks/cursor/`:

- Guardrails for risky commands (`beforeShellExecution`)
- Guardrails for sensitive file reads (`beforeReadFile`)
- Lightweight audit logging (optional)

> [!IMPORTANT]
> Hooks are not enabled by default. Start with **project hooks** (per-repo) before enabling global user hooks.

## Cursor hook configuration

Cursor loads hooks from:

- **Project**: `<repo>/.cursor/hooks.json` (runs from repo root)
- **User**: `~/.cursor/hooks.json` (runs from `~/.cursor`)

Hook scripts communicate via JSON over stdio (stdin input, stdout output). Cursor docs: `https://cursor.com/docs/agent/hooks`

## What we provide

### 1) Shell guard (`beforeShellExecution`)

- **File**: `hooks/cursor/guard_before_shell.py`
- **Goal**: deterministically gate dangerous/destructive commands and remote writes.

Behavior:

- **deny**: clearly destructive commands that are almost never correct to run autonomously (example: `rm -rf /`)
- **ask**: remote writes and high-blast-radius commands (example: `git push`, `terraform apply`)
- **allow**: everything else

### 2) File read guard (`beforeReadFile`)

- **File**: `hooks/cursor/guard_before_read_file.py`
- **Goal**: block sending sensitive file contents to the model.

Behavior:

- **deny**: obvious secret files (example: `.env`, private keys) and binary-ish content
- **allow**: everything else

### 3) Audit logger (optional)

- **File**: `hooks/cursor/audit_log.py`
- **Goal**: append a redacted JSON line log of hook events to a local file.

## Recommended rollout

### Step 1 - Project hooks (recommended)

Copy the example config and scripts into your repo:

```bash
mkdir -p .cursor/hooks
cp -R /path/to/agent-engineering-handbook/hooks/cursor/*.py .cursor/hooks/
cp /path/to/agent-engineering-handbook/hooks/cursor/hooks.project.example.json .cursor/hooks.json
chmod +x .cursor/hooks/*.py
```

### Step 2 - User hooks (optional)

Only after you like the behavior in a few repos, install globally:

```bash
/path/to/agent-engineering-handbook/scripts/cursor-hooks-install.sh --user
```

## Notes and safety

- Hooks run with your user permissions - treat them like any other local automation.
- Prefer **fail-open** while iterating (Cursor supports `failClosed` if you want fail-closed later).
- Keep matchers narrow to reduce noise and performance overhead.
