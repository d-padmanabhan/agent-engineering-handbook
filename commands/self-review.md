---
description: Comprehensive local code review comparing current branch to main - PR-ready analysis
---

# SELF CODE REVIEW MODE ACTIVATED

You are now in **SELF REVIEW** phase - performing a comprehensive local code review comparing the current branch to `main`, following the structured review approach from `100-core.mdc` and `010-workflow.mdc`.

> [!IMPORTANT]
> This is a **read-only analysis**. No commits or pushes will be made without explicit user authorization (see `020-agent-audit.mdc`).

## Phase 1: Context Gathering & Audit Setup

**Audit Requirements (from `020-agent-audit.mdc`):**

- Record baseline: `HEAD` SHA, branch name, timestamp
- For **critical tasks**, write/append a full audit report
- For routine tasks, a lightweight entry (or no report) is acceptable

> [!NOTE]
> **Checkpoints:** Only create checkpoints (`git stash`, rollback branch) if Phase 5 (Automated Fixes) will be applied.
> For read-only analysis, baseline recording is sufficient.
>
> Do not discard user working-tree edits with `git restore` / `git checkout --` unless the user explicitly asks (see `020-agent-audit.mdc`).

1. **Branch Information:**
   - Current branch name (`git branch --show-current`)
   - Base branch (default: `main`)
   - Baseline SHA (`git rev-parse HEAD`)
   - Commits ahead of base (`git log --oneline main..HEAD`)
   - Files changed (`git diff main...HEAD --name-only`)

2. **Change Summary:**
   - Show staged changes (`git diff --cached --stat`)
   - Show unstaged changes (`git diff --stat`)
   - Ignore files/folders listed in `.gitignore`
   - Generate diff summary: `git diff main...HEAD --stat`

3. **Recent Commit History:**
   - Display last 3-5 commits: `git log --oneline -5 main..HEAD`
   - Show commit messages to understand change context

## Phase 2: Static Analysis

Run appropriate linters and analyzers based on project language:

**Python:**

- `ruff check .` (linting)
- `ruff format --check .` (format check)
- `mypy .` or `ty .` (type checking)
- `pylint` (aim for score ≥9.5)
- `bandit -r .` (security scanning)
- `pip-audit` (dependency vulnerabilities)
- `tox` (if applicable)

**Bash/Shell:**

- `shellcheck` on all `.sh` files
- `shfmt -d .` (format check)

**Go:**

- `gofmt -d .` (format check)
- `golangci-lint run`
- `govulncheck ./...`

**JavaScript/TypeScript:**

- `eslint . --max-warnings=0`
- `npm audit` (if `package.json` exists)
- `tsc --noEmit` (if TypeScript)

**Terraform:**

- `terraform fmt -check -recursive`
- `terraform validate`
- `tflint`

**General:**

- `pre-commit run --all-files` (if configured)
- `gitleaks detect --source .` (secrets scanning)

Report all findings with file/line references.

## Phase 3: Diff Analysis

Analyze `git diff main...HEAD` focusing on:

### Critical Issues (Must Fix)

- **Security vulnerabilities:** Hardcoded secrets, injection risks, OWASP Top 10 violations
- **Bugs:** Logic errors, null pointer risks, data loss scenarios
- **Breaking changes:** API modifications without migration path

### Recommended Improvements

- **Performance:** Inefficient algorithms, N+1 queries, missing caching
- **Maintainability:** Code duplication, unclear naming, missing error handling
- **Observability:** Missing logging (following logging policy), no metrics, poor error messages

### Optional Enhancements

- **Style:** Formatting inconsistencies, minor naming improvements
- **Documentation:** Missing docstrings, unclear comments
- **Future-proofing:** Deprecated patterns, missing type hints

## Phase 4: Review Report

Generate a structured review report:

```
## Summary
[Brief overview: X files changed, Y commits, main themes]

## Critical Issues
[File:line] Issue description
- Impact: [What breaks]
- Fix: [Specific code suggestion with diff]

## Recommended Improvements
[File:line] Issue description
- Impact: [Performance/maintainability concern]
- Suggestion: [Code improvement]

## Optional Enhancements
[Brief list of style/docs improvements]

## Diff Highlights
[Show problematic sections with inline comments]
```

## Phase 5: Automated Fixes (Optional)

> [!IMPORTANT]
> **Before applying fixes:** Inspect the working-tree baseline and choose safeguards according to 020-agent-audit.mdc (`${HANDBOOK_ROOT}/rules/020-agent-audit.mdc`).
>
> Targeted, reversible fixes do not require a stash or backup branch. Create an explicit checkpoint for repository-wide formatting, mass rewrites/deletes, history changes, or operations that put unrelated user work at risk.

**Only proceed if user explicitly requests fixes or if Critical issues require formatting.**

1. **Formatting:** Apply formatters automatically:
   - Python: `ruff format .`, `isort .`
   - Bash: `shfmt -w -i 2 -ci -sr -bn .`
   - Go: `gofmt -w .`
   - Terraform: `terraform fmt -recursive`
   - General: `pre-commit run --all-files` (if configured)

2. **Re-stage formatted files:** `git add <formatted-files>`

3. **Re-run linters:** Verify fixes resolved issues

> [!TIP]
> If the user wants to revert formatting changes, propose the exact revert commands (for example `git restore <file>`), but do not run them unless the user explicitly asks. Checkpoints provide additional safety for complex changes.

## Phase 6: Verification & Audit Report

1. **Working directory status:** `git status`
2. **Linter status:** Re-run critical linters to confirm clean state
3. **Diff summary:** Show final `git diff main...HEAD --stat`
4. **Ready for PR:** Confirm all Critical issues resolved

**Generate an audit report when required by 020-agent-audit.mdc (`${HANDBOOK_ROOT}/rules/020-agent-audit.mdc`):**

- Resolve `GIT_REPO_ROOT="$(git rev-parse --show-toplevel)"`, create `<GIT_REPO_ROOT>/.agent/reports/` when needed, then write/append the report to `<GIT_REPO_ROOT>/.agent/reports/$(date +%F)-agent-report-<repo>-<branch>.md`
- Include:
  - Start/end timestamps (local and UTC)
  - Repo name, branch name, `HEAD` SHA
  - All commands executed with exit codes
  - `git status` and `git diff --stat` output
  - Verification outputs (linter/test results)
  - Checkpoint decision and identifiers, if any
  - Summary of findings

## Constraints

⚠️ **DO NOT:**

- Modify files outside the current diff
- Switch branches or perform unrelated Git operations
- Refactor code not part of current changes
- Add features not in the current scope
- Change APIs or break existing functionality
- **Commit or push** without explicit user authorization (see 020-agent-audit.mdc (`${HANDBOOK_ROOT}/rules/020-agent-audit.mdc`))
- Perform any remote writes (git push, PR creation, etc.)

✅ **DO:**

- Focus only on changed files
- Preserve existing functionality
- Apply fixes incrementally
- Explain the "why" behind each suggestion
- Provide actionable, specific feedback
- Create checkpoints before high-risk automated fixes (Phase 5)
- Document operations in an audit report when the task's reporting tier requires one

## Output Format

Present findings using the Priority Framework from `100-core.mdc`:

- **Critical:** Security, bugs, breaking changes
- **Recommended:** Performance, maintainability
- **Optional:** Style, documentation

Include code examples with minimal diffs suitable for PR comments.

## After Review

If Critical issues are found, document them clearly and wait for user direction.
If only Recommended/Optional issues remain, summarize and ask if user wants fixes applied.

**Next Steps:**

- **Read-only analysis complete:** Report findings, no changes made
- **If user requests fixes:** Create checkpoints → Apply fixes → Re-run verification (Phase 6)
- **If ready for PR:** User can proceed with commit/push (requires explicit authorization)
- **If issues found:** Document in audit report and wait for user decision

> [!NOTE]
> By default, `/self-review` performs **read-only analysis**. Checkpoints are only created if automated fixes (Phase 5) are applied.

**Optional: CodeRabbit Integration**

If CodeRabbit is available and configured for the repository:

- CodeRabbit can provide automated PR reviews after local validation
- Use CodeRabbit as a secondary layer for team consistency
- Always complete local review first for audit compliance
- CodeRabbit reviews complement but do not replace local review commands

---

**Integration:** This workflow aligns with:

- `010-workflow.mdc` Review Phase
- `100-core.mdc` Code Review Mode standards
- `020-agent-audit.mdc` Audit requirements
- `git-workflow` (`${HANDBOOK_ROOT}/skills/git-workflow/SKILL.md`) Commit procedures and standards
- `130-git.mdc` Mandatory Git safety gates
