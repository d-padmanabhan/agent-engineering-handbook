# Cursor Commands

Cursor commands for workflow phase transitions. These provide "progressive disclosure" - loading context only when explicitly triggered.

## Installation

Copy the `commands/` folder to your project's `.cursor/` directory:

```bash
# From your project root
cp -r /path/to/agent-engineering-handbook/commands .cursor/commands
```

Or symlink:

```bash
ln -s /path/to/agent-engineering-handbook/commands .cursor/commands
```

## Available Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/init` | Initialize task | Starting new work, detecting complexity |
| `/plan` | Enter planning phase | Designing solution, documenting approach |
| `/creative` | Enter creative/design phase | Complex tasks requiring design decisions |
| `/qa` | Run QA validation | Before implementation (Level 2+ tasks) |
| `/build` | Enter implementation phase | After plan is approved |
| `/review` | Enter review phase | After implementation complete |
| `/self-review` | Comprehensive local PR review | Before creating PR, compare branch to main |
| `/quick-review` | Fast critical issues check | Pre-commit validation, rapid iteration |
| `/check-progress` | Fix issues and summarize progress | During development to fix errors and draft commit messages without staging |
| `/code-commit` | Format, pre-commit, stage, commit and push | When you want a controlled commit + push workflow with HITL approval |
| `/bash` | Bash mode (create/modify/review scripts) | When working on Bash scripts and you want to enforce `140-bash.mdc` |
| `/gha` | GitHub Actions mode (create/modify/review) | When working on `.github/workflows/*` and you want to enforce `160-github-actions.mdc` |
| `/python` | Python mode (create/modify/review) | When working on Python and you want to enforce `200-python.mdc` |
| `/javascript` | JavaScript mode (create/modify/review) | When working on JavaScript and you want to enforce `230-javascript.mdc` |
| `/go` | Go mode (create/modify/review) | When working on Go and you want to enforce `210-go.mdc` |
| `/terraform` | Terraform mode (create/modify/review) | When working on Terraform and you want to enforce `180-terraform.mdc` |
| `/markdown` | Markdown mode (write/modify/review) | When writing docs and you want to enforce `800-markdown.mdc` |
| `/aws` | AWS mode (design/implement/review) | When doing AWS work and you want to enforce `410-aws.mdc` |
| `/archive` | Archive completed task | Document lessons learned (Level 3-4) |

## Workflow

### Simple Tasks (Level 1)

```
/init -> /build -> /review
```

### Moderate Tasks (Level 2)

```
/init -> /plan -> /qa -> /build -> /review
```

### Complex Tasks (Level 3-4)

```
/init -> /plan -> /creative -> /qa -> /build -> /review -> /archive
```

## Usage

Type the command in Cursor chat:

```
/plan Add user authentication to the application
```

The AI will enter that phase and follow the corresponding workflow guidelines.

## Review Commands

### `/self-review` - Comprehensive Local PR Review

Performs a full code review comparing your branch to `main`:

- **6-phase structured review** following `100-core.mdc` and `010-workflow.mdc`
- **Priority framework:** Critical → Recommended → Optional issues
- **Language-specific tooling:** Runs appropriate linters (ruff, pylint, shellcheck, etc.)
- **Security focus:** OWASP Top 10 checks, secrets scanning, dependency audits
- **Audit integration:** Creates checkpoints and audit reports per `020-agent-audit.mdc`
- **Automated fixes:** Applies formatters and re-stages files
- **PR-ready output:** Structured report suitable for PR comments

**Use when:** Before creating a PR, need comprehensive analysis, want full audit trail.

### `/quick-review` - Fast Critical Issues Check

Streamlined review for rapid iteration:

- **Critical issues only:** Security vulnerabilities, bugs, breaking changes
- **Fast checks:** Runs only essential linters (errors, not warnings)
- **Quick feedback:** Minimal report focusing on must-fix issues
- **No deep analysis:** Skips style/documentation improvements

**Use when:** Pre-commit validation, rapid development cycles, small changes.

## Relationship to Rules

Commands trigger specific behaviors but work alongside rules:

- **Commands** - Explicit phase transitions (`/plan`, `/build`, `/self-review`)
- **Rules** - Standards that apply based on file patterns (`.mdc` files)
- **MCP Server** - On-demand rule loading via tool calls

Use all three together for maximum flexibility.
