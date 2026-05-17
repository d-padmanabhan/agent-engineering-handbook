---
title: Setup Guide
description: 60-second quick-start to wire this repo's rules, skills, commands, MCP, and hooks into a new project. See NEW_REPO_CHECKLIST.md for the full step-by-step.
---

# Setup Guide

The **60-second quick-start**. For the full multi-artifact setup (skills, commands, MCP server, lifecycle hooks, pre-commit, workspace context files, verification), see [NEW_REPO_CHECKLIST.md](NEW_REPO_CHECKLIST.md).

This repo is designed to be used across many projects via a **shared checkout** that you symlink (or submodule) into each project. Workspace context files stay **workspace-local** under `tmp/`, excluded via `.git/info/exclude` (not the committed `.gitignore`).

Agent-neutral: works with Cursor, Claude Code, and Codex.

## Quick-start (personal)

Clone once, symlink the artifacts you want into each project:

```bash
git clone https://github.com/d-padmanabhan/agent-engineering-handbook.git ~/agent-engineering-handbook

cd /path/to/your/project
mkdir -p .cursor
ln -s ~/agent-engineering-handbook/rules    .cursor/rules
ln -s ~/agent-engineering-handbook/skills   .cursor/skills
ln -s ~/agent-engineering-handbook/commands .cursor/commands

# Claude Code / Codex compatibility (optional - skills only)
mkdir -p .claude .codex
ln -s ~/agent-engineering-handbook/skills .claude/skills
ln -s ~/agent-engineering-handbook/skills .codex/skills
```

## Quick-start (team)

Submodule for version pinning so every collaborator gets the same revision:

```bash
git submodule add https://github.com/d-padmanabhan/agent-engineering-handbook.git .cursor-rules
mkdir -p .cursor
ln -s ../.cursor-rules/rules    .cursor/rules
ln -s ../.cursor-rules/skills   .cursor/skills
ln -s ../.cursor-rules/commands .cursor/commands
```

To bump the pinned revision:

```bash
cd .cursor-rules && git pull origin main && cd ..
git add .cursor-rules
git commit -m "chore: bump agent-engineering-handbook"
```

## Setup script (rules + context only)

Shortcut for the rules-and-context part of the setup. Skills, commands, MCP, and hooks are not yet automated by the script - do those manually per the checklist.

```bash
cd /path/to/your/project
/path/to/agent-engineering-handbook/setup-workspace.sh -S -l .
```

Or for many repos at once (one per subdirectory under the parent):

```bash
/path/to/agent-engineering-handbook/setup-all-repos.sh -S -l ~/parent-workspace
```

Flags:

- `-S` symlink rules
- `-l` lightweight context (`tmp/tasks.md` only)
- `-f` full context (4 files: tasks, project-brief, active-context, progress)
- `--ensure-gitignore` legacy: appends `tmp/` to `.gitignore`. Prefer the `.git/info/exclude` policy in the Git hygiene section below.

## Context files and templates

Templates live at `rules/templates/` in the repo (accessible as `.cursor/rules/templates/` after the symlink). Eight templates available:

| Template | Used by |
|---|---|
| `tasks.md.template` | every workflow (minimum) |
| `project-brief.md.template` | complex multi-phase work |
| `active-context.md.template` | complex multi-phase work |
| `progress.md.template` | complex multi-phase work |
| `creative-template.md.template` | design exploration / brainstorming |
| `design.md.template` | formal design doc |
| `prd.md.template` | product requirements |
| `reflect-template.md.template` | post-task reflection |

Workspace context files belong in `tmp/<name>.md`. See [`rules/010-workflow.mdc`](rules/010-workflow.mdc) for what each file means and when to use it.

## Git hygiene

`tmp/`, `.terraform/`, and `.terragrunt-cache/` are personal / per-clone workspaces and tool caches, not project-wide policy. Exclude them via `.git/info/exclude` so the convention does not leak into the committed `.gitignore`:

```bash
cat >> .git/info/exclude <<'EOF'
**/tmp/
.terraform/
.terragrunt-cache/
EOF
```

Full rationale in [NEW_REPO_CHECKLIST.md, Section 9](NEW_REPO_CHECKLIST.md#9-git-hygiene).

## Next steps

For skills / commands / MCP server / lifecycle hooks / pre-commit setup / end-to-end verification, follow [NEW_REPO_CHECKLIST.md](NEW_REPO_CHECKLIST.md).
