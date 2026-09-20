---
name: git-workflow
description: Safe Git workflows for commits, branches, worktrees, recovery, signing, and remote synchronization. Use when creating or reviewing commits, branching, pushing, rebasing, restoring files, resolving divergence, using worktrees, or asking how Git behaves.
---

# Git Workflow

Use this skill for Git procedures. Mandatory authorization and preservation gates remain in the Git rule (`${HANDBOOK_ROOT}/rules/130-git.mdc`) and the agent audit rule (`${HANDBOOK_ROOT}/rules/020-agent-audit.mdc`).

## Non-Negotiable Workflow

1. Inspect the repository before changing it:

   ```bash
   git status --short --branch
   git branch --show-current
   git rev-parse HEAD
   ```

2. Preserve unrelated user changes. Never discard, stash, rewrite, or relocate them merely to simplify the task.
3. Treat commit, push, force update, history rewrite, restore/discard, destructive branch deletion, and worktree removal as separate authorization boundaries.
4. Run applicable tests, lint, formatting, type checks, and build steps before proposing a commit.
5. Before committing, show the complete message and exact file list, then wait for explicit confirmation.
6. Respect repository signing policy. If signing fails, stop; never silently create an unsigned commit.
7. Before pushing, fetch with pruning and inspect upstream divergence. Do not blindly pull, rebase, merge, or force-push.

## Common Workflows

### Create a feature branch

Start from a refreshed remote base.

For a clean worktree:

```bash
git fetch origin --prune
git switch main
git pull --ff-only
git switch -c feat/your-feature
```

When the current worktree has unrelated changes, preserve it and create an isolated worktree:

```bash
git fetch origin --prune
git worktree add -b feat/your-feature ../project-your-feature origin/main
```

Do not use `git switch -c` in a dirty worktree: compatible uncommitted changes can follow the new branch.

### Prepare a commit

Inspect status, staged and unstaged changes, and recent message style. Record the pre-task path baseline and treat every unrelated path as potentially owned by another user or agent session.

Stage explicit task paths, never the whole worktree by default. Avoid broad commands such as `git add -A`, `git add .`, or `git commit -a` when unrelated changes exist.

Run required hooks and generation after staging the intended change. Then compare status and the staged diff with the baseline:

- Include formatting, generated files, manifests, lockfiles, or configuration changes produced directly by task-scoped pre-commit hooks or an authorized dependency/tool upgrade when they are required for the commit.
- Review those induced changes, rerun applicable verification, and describe material hook or upgrade effects in the commit message.
- Leave all pre-existing and concurrently created unrelated files untouched and unstaged. A hook modifying unrelated paths is not permission to absorb them.
- Stop and investigate if provenance is ambiguous or a hook causes unexpectedly broad changes.

Before requesting commit approval, inspect the exact staged diff and show its complete added, modified, renamed, and deleted file list. Use the format and review gate in git-workflow.md (`${HANDBOOK_ROOT}/skills/git-workflow/git-workflow.md`).

### Push an existing branch

```bash
git fetch origin --prune
git status --short --branch
git log --oneline --left-right --boundary HEAD...@{upstream}
```

- Ahead only: push after authorization.
- Behind only: fast-forward only when repository policy permits.
- Diverged: stop and choose merge or rebase based on repository policy and whether commits are shared.
- Dirty worktree: do not rebase or merge until unrelated work is understood and preserved.

Use `git push -u origin HEAD` only for a new branch without an upstream. Never force-push unless that exact update was explicitly authorized; never force-push a protected default branch.

### Recover safely

Inspect reflog and repository state before choosing a recovery operation. Prefer creating a recovery branch or restoring a specific object over destructive reset. See git-reflog.md (`${HANDBOOK_ROOT}/skills/git-workflow/git-reflog.md`).

## References

- Git fundamentals (`${HANDBOOK_ROOT}/skills/git-workflow/git-fundamentals.md`) - refs, remotes, fetch/pull, and branch workflows
- Git workflow (`${HANDBOOK_ROOT}/skills/git-workflow/git-workflow.md`) - commits, signing, branches, PRs, and repository hygiene
- Modern Git commands (`${HANDBOOK_ROOT}/skills/git-workflow/git-modern-commands.md`) - `switch`, `restore`, moves, and worktrees
- Reflog (`${HANDBOOK_ROOT}/skills/git-workflow/git-reflog.md`) - recovery and history inspection
- Pre-commit (`${HANDBOOK_ROOT}/skills/git-workflow/git-pre-commit.md`) - hook setup and maintenance
