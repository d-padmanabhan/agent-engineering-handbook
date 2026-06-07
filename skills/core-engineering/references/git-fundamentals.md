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

## Quick Alternative (With Caveats)

Skip your local `main` entirely by branching directly from `origin/main`:

```bash
git fetch origin --prune && git switch -c feat/your-feature origin/main
```

**Advantages:**

- Faster (one fewer step)
- Works even if your local `main` is in a weird state
- Guaranteed to start from remote's latest

**Use when:** Creating throwaway branches or when local `main` is messy.

## Sync with remote, then push (REQUIRED before every push)

**Always sync the current branch with its remote immediately before pushing to an existing remote branch** - pushing stale history triggers non-fast-forward rejections and tempts a history-clobbering `--force`. Use **pull with rebase** on the **current branch** so the same command works on `main` or any feature branch. See **130-git.mdc** (Sync with remote, then push) for full detail.

```bash
git pull origin $(git branch --show-current) --rebase
git push origin $(git branch --show-current)
```

One-liner: `git pull origin $(git branch --show-current) --rebase; git push origin $(git branch --show-current)`

Only exception - a brand-new branch with no upstream yet (nothing to pull): `git push -u origin HEAD`.
