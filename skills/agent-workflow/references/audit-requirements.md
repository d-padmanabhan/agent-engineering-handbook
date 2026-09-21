# Agent Audit Requirements

These rules apply to AI agents operating in workspaces. They are designed to make work **reversible**, **verifiable**, and **auditable**.

## 1. Remote Mutations: Explicit Authorization

Read-only operations need no checkpoint or extra approval. This includes file inspection, API `GET` requests, status/list/describe commands, plans/diffs, and read-only tool calls.

Remote mutations require user authorization. A direct request for a specific mutation counts as authorization. Ask again only when an operation is destructive, irreversible, security-sensitive, or materially broader than the request.

For high-risk mutations, record the authorization, commands, results, and exit codes.

Mutations include:

- `git push`, forced updates, tag pushes
- Creating/merging PRs, pushing branches
- `terraform apply`, `kubectl apply`, `helm upgrade`
- Database migrations against non-local DBs
- Any command that changes remote resources

**Commits are local-only** and allowed only after explicit user authorization.

## 2. Local Git Repository Discipline

These requirements apply when modifying files in a Git repository:

- Inspect `git status --short`, the current branch, and `HEAD` before routine edits.
- Preserve unrelated user changes and do not assume a clean working tree.
- Record the baseline only when the reporting tier requires an audit report.
- Create a backup branch only for history rewrites or changes with difficult rollback.
- Do not rebase or otherwise rewrite shared history unless explicitly authorized.

## 3. Risk-Based Backups and Checkpoints

Use the least disruptive safeguard proportional to risk.

No checkpoint is needed for read-only work, trivial local-only actions, or small reversible edits whose current diff is understood.

For routine edits, inspect a lightweight baseline:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
```

Create an explicit checkpoint for history rewrites, repository-wide mechanical changes, mass deletes/renames, broad multi-repository changes, or operations that require a clean tree while unrelated work exists.

- Use a backup branch before an authorized history rewrite.
- Use a patch or targeted file copy when only selected uncommitted work is at risk.
- Use `git stash` only when a clean tree is genuinely required; explain and promptly restore it.

For external mutations, use system-specific safeguards: dry run/plan, current-state capture, narrow scope, idempotency, concurrency/version checks, and a tested rollback path. A Git branch or stash does not protect remote infrastructure, data, or API state.

## 4. Local Verification Gate (Mandatory)

Before proposing any commit messages, run local verification as applicable:

- Unit/integration tests
- Lint
- Formatting
- Type checks
- Build/package step

If verification cannot run, state:

- The exact reason
- The closest substitute run instead
- What evidence was relied on

**Examples of verification commands (not exhaustive):**

- **Python:** `pytest`, `ruff check`, `ruff format --check`, `mypy`/`pyright`, `pylint`
- **JavaScript/TypeScript:** `npm test`, `npm run lint`, `npm run build`, `tsc --noEmit`
- **Go:** `go test ./...`, `golangci-lint run`, `gofmt -d .`
- **Rust:** `cargo test`, `cargo clippy`, `cargo fmt --check`
- **Shell:** `shellcheck *.sh`, `shfmt -d .`
- **General:** `pre-commit run --all-files` (if configured)

## 5. Proportional Audit Reporting

Use a full report for critical tasks: history rewrites, force updates, destructive operations, remote infrastructure/data changes, security or identity changes, broad multi-repository work, or changes with a substantial blast radius.

For routine tasks, a lightweight entry is optional. No report is needed for read-only or trivial local-only work.

When a full report is required:

**Repo root (required):**

- `GIT_REPO_ROOT="$(git rev-parse --show-toplevel)"`

**Path rules:**

- Write reports to: `<GIT_REPO_ROOT>/.agent/reports/agent_report_<repo>_<branch>_<timestamp>.md`
- Create `.agent/reports/` when it does not exist.
- Keep `.agent/reports/` excluded from Git.

> [!IMPORTANT]
> `.agent/reports/` is intended to be **gitignored**. Do not commit or push audit artifacts unless explicitly requested.

**Required contents:**

- Start and end timestamps (local time and UTC)
- Repo name, branch name, HEAD SHA
- Every command executed (copy-pasteable) with exit codes
- Summary of changes: `git status`, `git diff --stat`, changed files
- Verification outputs
- Proposed commit messages, if applicable
- Checkpoint decision and any checkpoint identifiers
- Any authorized remote-write operations

### Optional: Terminal Recordings (asciinema)

For complex debugging sessions or demos, agents MAY create terminal recordings using `asciinema`.

**When to record:**

- Complex debugging where timing/flow matters
- Sessions that would benefit from visual playback
- When user explicitly requests a recording

**Recording path:**

- Save to: `<GIT_REPO_ROOT>/.agent/reports/recordings/<repo>_<branch>_<yyyymmdd_HHMMSS>.cast`
- Reference the recording path in the markdown audit report

**How to record:**

```bash
# Start recording
asciinema rec -q "<GIT_REPO_ROOT>/.agent/reports/recordings/session.cast"

# ... perform commands ...

# Stop recording (Ctrl+D or exit)
```

**Important:**

- Recordings are a **supplement**, not a replacement for markdown reports
- The markdown report remains the **primary audit artifact** (searchable, structured)
- Recordings are for **understanding flow**, not for audit compliance

## 6. If Commits Are Authorized Later

Only after the user explicitly authorizes commits:

1. **Commit locally** with the agreed messages (respect commit signing (`${HANDBOOK_ROOT}/rules/130-git.mdc#commit-authorization-and-signing`): do not bypass signing unless the user explicitly requested an unsigned commit and the reason is recorded)
2. **If an audit report is required or already exists, append:**
   - Commit SHAs and commit messages
   - Output from: `git log --date=iso-strict -n <N>` (where `<N>` covers the new commits)
   - Signature status: e.g. `git log -n <N> --show-signature` (or note explicitly if commits are unsigned and why)
   - Confirmation that commits match the proposed plan
3. **Do NOT push** to remote unless explicitly authorized separately
4. **Record the authorization** in the audit report when one is required or already exists

## 7. GitHub CLI Mutation Policy

**Allowed without mutation authorization:**

- `gh repo view`
- `gh issue list` / `gh issue view`
- `gh pr list` / `gh pr view`
- `gh api` GET requests only

**Allowed only when explicitly authorized by the user's request:**

- `gh pr create`, `gh pr merge`
- `gh repo fork`
- Any `gh api` mutation (POST/PATCH/PUT/DELETE)

Preview the affected repository, branch, request body, or resource first. Seek separate confirmation for destructive, irreversible, privileged, or materially broader actions.

## 8. Required Sequence

```
Understand task → classify risk and mutation type → inspect baseline when editing →
take a checkpoint only if warranted → make the minimal change → verify proportionally →
report according to tier → obtain authorization for commits or remote mutations
```
