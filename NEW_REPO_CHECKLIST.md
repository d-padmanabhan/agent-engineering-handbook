---
title: New Repo Setup Checklist
description: Quick checklist to wire Cursor rules and context templates into a repository.
---

# New Repo Setup Checklist

## Setup rules

- [ ] Add the rules (recommended: submodule + symlink):

```bash
git submodule add https://github.com/d-padmanabhan/cursor-engineering-rules.git .cursor-rules
mkdir -p .cursor
ln -s ../.cursor-rules/rules .cursor/rules
```

- [ ] Confirm `.cursor/rules` points where you expect:

```bash
ls -la .cursor/rules
readlink .cursor/rules
```

## Setup workspace context files

- [ ] Create `tmp/` (workspace-local, gitignored)
- [ ] Create `tmp/tasks.md` (minimum)

```bash
mkdir -p tmp/pr tmp/pr_reviews tmp/agent_reports tmp/bug_reports
cp .cursor/rules/templates/tasks.md.template tmp/tasks.md
```

Optional (for complex work):

- [ ] `tmp/project-brief.md`
- [ ] `tmp/active-context.md`
- [ ] `tmp/progress.md`

```bash
cp .cursor/rules/templates/project-brief.md.template tmp/project-brief.md
cp .cursor/rules/templates/active-context.md.template tmp/active-context.md
cp .cursor/rules/templates/progress.md.template tmp/progress.md
```

## Git hygiene (recommended)

- [ ] **Git Hygiene:** Add the following to `.git/info/exclude` (preferred) instead of the repo `.gitignore`: `**/tmp/`, `.terraform/`, `.terragrunt-cache/`. Do not modify the repo `.gitignore` for these entries.

```bash
cat >> .git/info/exclude <<'EOF'
**/tmp/
.terraform/
.terragrunt-cache/
EOF
```

Rationale: these are personal / per-clone workspaces and tool caches, not project-wide policy. `.git/info/exclude` keeps them out of *your* working tree without imposing the convention on every collaborator via the committed `.gitignore`.
