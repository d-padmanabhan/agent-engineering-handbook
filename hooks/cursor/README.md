## Cursor Hooks Pack

This directory contains **optional** hook scripts and example `hooks.json` configs for Cursor.

Hooks are deterministic programs that run at defined points in the agent loop and can block, allow, or modify actions.

### Files

- `guard_before_shell.py`: Intended for `beforeShellExecution`
  - Denies obviously catastrophic delete commands
  - Asks for approval on remote writes / high-blast-radius commands
- `guard_before_read_file.py`: Intended for `beforeReadFile`
  - Denies reading common secret files (for example `.env`, private keys)
- `audit_log.py`: Intended for `preToolUse` (or other events)
  - Writes a redacted JSONL audit record to `.cursor/hooks/state/hook-audit.jsonl` (project) or `~/.cursor/hooks/state/hook-audit.jsonl` (user)
- `hooks.project.example.json`: Example project config (paths like `.cursor/hooks/...`)
- `hooks.user.example.json`: Example user config (paths like `./hooks/...`)

### Quick start (project)

From your repo root:

```bash
mkdir -p .cursor/hooks
cp -R /path/to/agent-engineering-handbook/hooks/cursor/*.py .cursor/hooks/
cp /path/to/agent-engineering-handbook/hooks/cursor/hooks.project.example.json .cursor/hooks.json
chmod +x .cursor/hooks/*.py
```
