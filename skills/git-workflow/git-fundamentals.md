# Git Fundamentals

## What is a Ref?

A **ref** (reference) is Git's way of creating human-readable names for commit hashes. Instead of remembering `a3f8b2c...`, you use names like `main` or `v1.2.3`.

Refs are bookmarks pointing to specific commits in your repository's history. They are stored as simple text files in `.git/refs/` containing a 40-character commit SHA.

## Types of Refs

| Ref Type | Location | Purpose |
|----------|----------|---------|
| Local branches | `refs/heads/main` | Track your local work |
| Remote-tracking branches | `refs/remotes/origin/main` | Your local copy of what the remote server has |
| Tags | `refs/tags/v1.2.3` | Permanent markers for releases |
| HEAD | `.git/HEAD` | Special pointer to wherever you are right now |

## The Three-Tier Model

Understanding the relationship between remote and local branches prevents confusion:

```
Remote branch (on server)     :  main
                                  ↓
Remote-tracking branch (local):  origin/main
                                  ↓
Local branch (your work)      :  main
```

**Key insight:** When you run `git fetch`, only the remote-tracking branch updates. Your local branch and working files remain untouched.

This is why you can safely inspect remote changes before integrating them:

```bash
git fetch origin
git log origin/main          # See what's new on remote
git diff origin/main         # Compare with your local state
git merge origin/main        # Integrate when ready
```

## Fetch vs Pull

| Command | What It Does | Touches Working Tree? |
|---------|--------------|----------------------|
| `git fetch` | Downloads commits, updates remote-tracking refs | No |
| `git pull` | Fetch + merge (or rebase) into current branch | Yes |

**Why fetch is safer:** You can inspect what changed remotely before deciding to integrate. Fetch updates your "map" of the remote without changing your actual location or files.

## Always Prune Stale Refs

When branches are deleted on the remote, your local remote-tracking refs become stale "ghosts." Use `--prune` to clean them up:

```bash
git fetch origin --prune
```

**Recommended:** Enable automatic pruning globally:

```bash
git config --global fetch.prune true
```

Now every `git fetch` and `git pull` automatically removes stale remote-tracking branches.

> [!NOTE]
> `--prune` only removes remote-tracking branches (like `origin/feat-old`). It does NOT delete your local branches. Your local work is always safe.

## Robust Feature Branch Workflow

> [!IMPORTANT]
> Before creating any feature branch, fetch the remote and prove the selected base is current. Branch creation from a stale base is blocked. If the current worktree contains user changes, do not switch branches or stash those changes. An isolated worktree may be proposed, but it cannot be created without explicit HITL approval of the exact repository, path, branch, base ref, and command.

Required pre-branch proof:

```bash
git fetch origin --prune
test "$(git rev-parse main)" = "$(git rev-parse origin/main)"
```

If the proof fails, update local `main` with the clean-worktree workflow below or branch directly from the refreshed `origin/main`.

When creating a feature branch from an updated `main`, use this explicit pattern:

```bash
# Step 1: Download latest from remote, clean up deleted branches
git fetch origin --prune

# Step 2: Move to main branch explicitly
git switch main

# Step 3: Fast-forward only (refuses to create merge commits)
git pull --ff-only

# Step 4: Create and switch to feature branch
git switch -c feat/your-feature-name
```

**Why this pattern?**

| Step | Purpose |
|------|---------|
| `git fetch origin --prune` | Get latest state, clean stale refs |
| `git switch main` | Ensures you start from the right place |
| `git pull --ff-only` | Prevents accidental merge bubbles |
| `git switch -c` | Creates branch from now-updated main |

## Direct Remote-Base Alternatives

Skip your local `main` by branching directly from the refreshed `origin/main`.

### Clean Worktree

Use `git switch -c` only after proving the current worktree is clean:

```bash
git fetch origin --prune
test -z "$(git status --porcelain)"
git switch -c feat/your-feature origin/main
```

**Advantages:**

- Faster (one fewer step)
- Works even if your local `main` is in a weird state
- Guaranteed to start from remote's latest

**Use when:** Local `main` is stale and the current worktree is verified clean.

### Dirty Worktree - Worktree Requires HITL Approval

Preview a new sibling worktree so user changes remain untouched:

```bash
git fetch origin --prune
git worktree add -b feat/your-feature "../repo-feature" origin/main
```

Do not execute the preview until a human explicitly approves the exact
repository, destination path, branch, base ref, and command. A request to
create a branch or continue implementation is not worktree approval. After
approval, choose a sibling path that does not already exist and perform all
feature work there.

> [!IMPORTANT]
> `git switch -c` is prohibited for this path because Git can carry compatible uncommitted changes onto the new branch. The mandatory preservation gate is in the Git rule (`${HANDBOOK_ROOT}/rules/130-git.mdc#preserve-user-work`).

## Inspect remote state, then push

Fetch and inspect the current branch before pushing to an existing remote branch. Do not blindly run `git pull --rebase`; it modifies local history and may be unsafe with a dirty tree, shared commits, or merge-based repository policy. The mandatory push gate is in 130-git.mdc (`${HANDBOOK_ROOT}/rules/130-git.mdc#branches-history-and-remote-writes`).

```bash
git fetch origin --prune
git status --short --branch
git log --oneline --left-right --boundary HEAD...@{upstream}
```

Push when the branch is ahead only. If it is behind or diverged, integrate according to repository policy; rebase only when the worktree is clean and rewriting local commits is safe. Never force-push merely to bypass divergence.

For a brand-new branch with no upstream, use `git push -u origin HEAD`.
