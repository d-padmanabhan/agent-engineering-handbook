---
description: Format, pre-commit, stage safely, propose commit message, commit and push (HITL gated)
---

# CODE COMMIT MODE ACTIVATED

You are running the **`/code-commit`** workflow to prepare a clean commit and push it to `origin`.

> [!IMPORTANT]
> This workflow includes **remote writes** (`git push`) and is **HITL gated**.
> Do not commit or push until the user explicitly approves.

---

## Step 0: Repo safety and context

If you are not sure which repo you are in, STOP and ask the user to confirm.

Collect context:

- Repo root: `git rev-parse --show-toplevel`
- Current branch: `git branch --show-current`
- Current HEAD: `git rev-parse HEAD`
- Remote: `git remote -v`

---

## Step 1: Review all changes

Review working tree and index:

- `git status`
- `git diff`
- `git diff --cached`

List changed files explicitly (for safe staging later):

- `git status --porcelain=v1`
- Derive the exact file list from porcelain output (do not guess)

---

## Step 2: Format and clean up (language-aware)

Detect the project language/framework based on **modified files** and run the appropriate formatter/linter.
If a tool is not installed or a project file is missing, report the reason and continue with the closest substitute.

### Bash

- `shfmt -w -i 2 -ci -sr -bn <changed_shell_files>`
- `shellcheck <changed_shell_files>`

### GitHub Actions

If workflows exist, run:

- `actionlint .github/workflows/*.yaml .github/workflows/*.yml`

### Terraform

- `terraform fmt -recursive`
- `terraform validate`
- `tflint`

### Python

Run (as applicable in this repo):

- `isort <changed_python_files>`
- `ty <changed_python_files>` (or `mypy <changed_python_files>`)
- `pylint <changed_python_files>` (aim for **≥ 9.5**)
- `ruff format <changed_python_files>`
- `ruff check <changed_python_files> --fix`
- `black <changed_python_files>` (if used in repo)
- `tox` (if applicable / configured)

> [!NOTE]
> If you change behavior while fixing docstrings, call it out in the summary.

### Go

- `gofmt -w -s <changed_go_files>`
- `go vet ./...`
- `staticcheck ./...`
- `golangci-lint run ./...`
- `govulncheck ./...`

### Rust

- `cargo fmt`

### Markdown

- `markdownlint --fix <changed_markdown_files>`

---

## Step 3: Run pre-commit (before staging/committing)

If pre-commit is configured, run:

- `pre-commit autoupdate && pre-commit run --all-files`

If pre-commit modifies files, re-run until it passes cleanly.

---

## Step 4: Stage safely (no `git add .`)

Stage **explicitly** by file name:

- `git add <file1> <file2> ...`

> [!IMPORTANT]
> Stage files safely (handles spaces) by iterating line-by-line:
>
> ```bash
> git status --porcelain=v1 | awk '{print $2}' | while IFS= read -r f; do
>   [ -n "$f" ] && git add -- "$f"
> done
> ```

Constraints:

- **DO NOT** use `git add .`
- **DO NOT** stage or commit `.gitignore` unless the user explicitly requested it

---

## Step 5: Draft a Conventional Commit message (HITL gate)

Draft a commit message following `rules/130-git.mdc`:

- Conventional Commits (`feat`, `fix`, `docs`, `chore`, `refactor`, `ci`, `test`, `perf`)
- First line ≤ 72 chars, imperative mood
- Bullets start with a capital letter, no period
- Prefer explaining **why** in the body

Then display:

1. Full commit message preview
2. Files to be committed (explicit list)

And ask:

`Should I proceed with this commit? (yes/no)`

> [!IMPORTANT]
> Do not add Cursor attribution trailers (see `rules/130-git.mdc`).

---

## Step 6: Write commit message file under `tmp/commit_messages`

Create the commit message file:

- Directory: `tmp/commit_messages` (create if missing)
- Filename format:
  - `YYYYMMDD_HHMMSS_<repo>_<branch>_<last7sha>.md`
  - Example: `20251228_154700_agent-engineering-handbook_main_abcd123.md`

Notes:

- Use repo name from `basename "$(git rev-parse --show-toplevel)"`
- Use branch name from `git branch --show-current`
- Use last 7 of current HEAD via `git rev-parse --short=7 HEAD`
- Ensure `tmp/` is gitignored before writing artifacts

> [!NOTE]
> You cannot know the new commit hash until after committing. If desired, copy/rename the message file after commit to include the new commit short hash.

---

## Step 7: Commit using the commit message file

Commit:

- `git commit -F tmp/commit_messages/<filename>.md`

Confirm:

- Display commit hash
- Display full commit message

---

## Step 8: Push to `origin` (HITL gate)

Before pushing, ask:

`Should I push this commit to origin/<current-branch>? (yes/no)`

If approved:

- `git push origin <current-branch>`

Confirm:

- Remote branch name
- `git status -sb` shows local is in sync
