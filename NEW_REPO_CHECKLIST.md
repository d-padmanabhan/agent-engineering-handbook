---
title: New Repo Setup Checklist
description: Wire rules, skills, slash commands, MCP server, hooks, and workspace context files into a repo for any AI coding agent (Cursor, Claude Code, Codex).
---

# New Repo Setup Checklist

Wire this repo's rules, skills, slash commands, MCP server, hooks, and workspace context files into a new project. Agent-neutral: works with Cursor, Claude Code, and Codex.

> [!TIP]
> **Fast path** (if you keep this repo as a shared checkout):
>
> ```bash
> /path/to/agent-engineering-handbook/setup-workspace.sh -S -l .
> ```
>
> `-S` symlinks `rules/`, `-l` writes only `tmp/tasks.md`. Use `-f` for the full context-file set. The rest of this checklist documents what the script does **and the extras (skills, commands, MCP, hooks) it does not yet automate**.

## 1. Pick your install method

| Method | When | Trade-off |
|---|---|---|
| **Setup script** (`setup-workspace.sh`) | Default | Fast; symlinks `rules/` and scaffolds `tmp/`. Does not wire skills, commands, MCP, or hooks yet. |
| **Symlink** | Personal use across many projects | One `git pull` in the source repo updates every consumer. Symlinks don't survive zip download. |
| **Copy** | Self-contained projects, version-pinned | No live updates; re-copy on each bump. |
| **Submodule** | Team projects, version-controlled | Locks the version; survives zip; needs `git submodule update --remote` to bump. |

This checklist assumes symlink or submodule. Copy is one `cp -r` per directory.

## 2. Rules

Rules (`.mdc`) load globally (`alwaysApply: true`) or by file-glob match.

```bash
# Symlink (personal, one repo)
mkdir -p .cursor
ln -s /path/to/agent-engineering-handbook/rules .cursor/rules

# Submodule (team, pinned)
git submodule add https://github.com/d-padmanabhan/agent-engineering-handbook.git .cursor-rules
mkdir -p .cursor
ln -s ../.cursor-rules/rules .cursor/rules

# Verify
ls -la .cursor/rules
readlink .cursor/rules
```

**Agent-neutral alternative:** ship a single `AGENTS.md` at the repo root (Cursor + Codex honor it; Claude Code reads `CLAUDE.md` natively and is rolling out `AGENTS.md` support). Useful when you don't want a `.cursor/` directory.

## 3. Skills (Agent Skills)

Skills are multi-step playbooks: test plans, deployment runbooks, security audits, refactor guides, etc. Auto-selected via the SKILL.md `description` triggers; invoke manually as `/skill-name`.

```bash
# Cursor
ln -s /path/to/agent-engineering-handbook/skills .cursor/skills

# Claude Code
mkdir -p .claude
ln -s /path/to/agent-engineering-handbook/skills .claude/skills

# Codex
mkdir -p .codex
ln -s /path/to/agent-engineering-handbook/skills .codex/skills
```

Mix per project. See the **Skills shipped in this repo** section in the parent [README.md](README.md) for the catalog.

## 4. Slash commands

Slash commands provide explicit workflow phase transitions (`/plan`, `/build`, `/review`, `/self-review`, `/quick-review`, etc.).

```bash
# Copy (no upstream updates)
mkdir -p .cursor/commands
cp -r /path/to/agent-engineering-handbook/commands/* .cursor/commands/

# Symlink (live updates)
ln -s /path/to/agent-engineering-handbook/commands .cursor/commands
```

Type `/<command>` in your agent's chat to trigger. See [commands/README.md](commands/README.md) for the full catalog (~19 commands).

## 5. MCP server (optional, recommended)

Install if you want **on-demand rule loading** via tool calls instead of pre-loading every `.mdc`. Useful when context budget matters.

```bash
cd /path/to/agent-engineering-handbook/mcp/cursor-rules-mcp
npm install
npm run build
npm link        # optional: makes `cursor-rules-mcp` globally invokable
```

Then configure your agent. See [mcp/cursor-rules-mcp/INSTALLATION.md](mcp/cursor-rules-mcp/INSTALLATION.md) for per-agent setup (Claude Desktop, Cursor, Claude Code, Codex).

## 6. Lifecycle hooks (optional)

Deterministic guardrails (block reading `.env`, gate destructive shell commands) and audit logging via Cursor's hooks API.

```bash
/path/to/agent-engineering-handbook/scripts/cursor-hooks-install.sh
```

See [docs/HOOKS.md](docs/HOOKS.md) for what each hook does, how to disable individual checks, and how to write your own. **Cursor-specific** today; the hooks API is not yet portable across agents.

## 7. Workspace context files

Per-task context that the workflow rules (`010-workflow.mdc`, `020-agent-audit.mdc`) consume.

```bash
# Minimum: a tasks file
mkdir -p tmp
cp .cursor/rules/templates/tasks.md.template tmp/tasks.md
```

For complex multi-phase work, add the full context set:

```bash
cp .cursor/rules/templates/project-brief.md.template  tmp/project-brief.md
cp .cursor/rules/templates/active-context.md.template tmp/active-context.md
cp .cursor/rules/templates/progress.md.template       tmp/progress.md
```

Other available templates (use as needed):

- `creative-template.md.template` - design exploration / brainstorming
- `design.md.template` - formal design doc
- `prd.md.template` - product requirements
- `reflect-template.md.template` - post-task reflection

Optional working directories some workflows expect (create only what you use):

| Path | Used by |
|---|---|
| `tmp/pr/` | PR drafts |
| `tmp/pr_reviews/` | `/self-review`, `/quick-review` output |
| `tmp/agent_reports/` | `020-agent-audit.mdc` audit reports |
| `tmp/bug_reports/` | bug investigation notes |

```bash
mkdir -p tmp/pr tmp/pr_reviews tmp/agent_reports tmp/bug_reports
```

## 8. Pre-commit hooks (recommended)

Mirror this repo's pre-commit stack so your consumer repo gets the same lint + safety baseline. The full config is at [`.pre-commit-config.yaml`](.pre-commit-config.yaml); copy it as-is.

```bash
brew install pre-commit                                  # macOS
# pip install pre-commit                                 # any platform

cp /path/to/agent-engineering-handbook/.pre-commit-config.yaml .pre-commit-config.yaml
cp /path/to/agent-engineering-handbook/.markdownlint.yaml   .markdownlint.yaml
pre-commit install
pre-commit run --all-files                               # baseline run
```

Hooks in the shipped config:

| Repo | Hook(s) | Purpose |
|---|---|---|
| `pre-commit/pre-commit-hooks` v6.0.0 | `trailing-whitespace` (excludes `*.md`), `end-of-file-fixer` (excludes `*.mdc`), `check-yaml`, `check-added-large-files` (1 MB cap), `mixed-line-ending` (forces LF), `check-case-conflict`, `check-merge-conflict`, `detect-private-key` | File hygiene + obvious safety |
| `igorshubovych/markdownlint-cli` v0.47.0 | `markdownlint` with `--fix --config .markdownlint.yaml` | Markdown style enforcement (auto-fixes most issues) |
| `lycheeverse/lychee` nightly | `lychee` (stage: `manual`, files: `*.md` / `*.mdc`) | Link checker - run on demand: `pre-commit run lychee --hook-stage manual` |

### Secret scanning (separate from `.pre-commit-config.yaml`)

`ggshield` (GitGuardian) installs as its own git hook and runs **before** pre-commit-config.yaml. Install per-repo:

```bash
brew install gitguardian/tap/ggshield                    # macOS
# pipx install ggshield                                  # any platform

ggshield auth login                                      # one-time
ggshield install --mode local --type pre-commit          # per-repo
```

`ggshield` complements the config's `detect-private-key` (which only catches a small set of recognized key formats) with full GitGuardian secret detection.

For broader regex + entropy coverage (CI-grade), wire `gitleaks` into your GitHub Actions workflow instead of pre-commit; see the [`codebase-security-audit` skill's CI workflow reference](skills/codebase-security-audit/references/ci-workflow.md).

## 9. Git hygiene

- [ ] **Git Hygiene:** Add the following to `.git/info/exclude` (preferred) instead of the repo `.gitignore`: `**/tmp/`, `.terraform/`, `.terragrunt-cache/`. Do not modify the repo `.gitignore` for these entries.

```bash
cat >> .git/info/exclude <<'EOF'
**/tmp/
.terraform/
.terragrunt-cache/
EOF
```

Rationale: these are personal / per-clone workspaces and tool caches, not project-wide policy. `.git/info/exclude` keeps them out of *your* working tree without imposing the convention on every collaborator via the committed `.gitignore`.

## 10. Verify

End-to-end smoke test that the wiring actually works:

```bash
# Rules: at least one known rule is on disk
ls .cursor/rules/200-python.mdc                      # or 210-go.mdc, 410-aws.mdc, etc.

# Skills: at least one SKILL.md is discoverable
ls .cursor/skills/*/SKILL.md   | head -3             # expect 3+ matches

# Commands: at least one command markdown is present
ls .cursor/commands/*.md       | head -3             # expect 3+ matches

# Templates resolve through the rules symlink
ls .cursor/rules/templates/    | head -5             # expect template files

# Workspace exclusion is in effect (tmp/ should not appear in `git status`)
mkdir -p tmp && touch tmp/x && git status --short | grep '^?? tmp' && echo "FAIL: tmp/ leaking into git" || echo "ok: tmp/ excluded"
rm tmp/x
```

For agent-side verification: open a known file type (`.py`, `.tf`, `.go`) and confirm the matching rule is detected in the agent's settings panel (Cursor: Settings -> Rules & Memories; Claude Code: `/rules` command).

If any step fails, re-check the symlink / copy step for that artifact.
