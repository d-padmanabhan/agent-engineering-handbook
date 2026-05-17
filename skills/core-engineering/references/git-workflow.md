# Git & Commit Standards

## Commit Message Format

```
<type>(<scope>): <short summary>

<bulleted list of key changes>

<optional explanatory paragraph>
```

- First line ≤ **72 chars**, imperative mood ("add", "fix", "update")
- Bullets: start with a **capital letter**, **no period**
- Add a short **rationale paragraph** when the change is non-obvious
- Use issue refs when helpful (`Fixes #123`, `Refs #456`)

### Example

```
docs(upgrade): reorganize and enhance v3.4→v3.8 upgrade guide

- Prioritize ANF-disabled path (Path A)
- Add rationale for route table rotation logic
- Include Q-chat verification prompt
- Add ANF cost caution in Path B

Improves upgrade experience by making common path primary.
```

## Commit Types (Conventional Commits)

| Type | Purpose |
|------|---------|
| **feat** | New feature or enhancement |
| **fix** | Bug fix |
| **docs** | Documentation changes |
| **refactor** | Restructure without behavior change |
| **perf** | Performance improvement |
| **test** | Add/update tests |
| **ci** | GitHub Actions / build infra |
| **chore** | Dependencies, cleanup |
| **revert** | Revert a previous commit |

**Breaking Changes** require: `feat(api)!: ...` + footer:

```
BREAKING CHANGE: renamed output vpc_id to lattice_vpc_id
```

## Commit Footers and Trailers

**Allowed footers:**

- `BREAKING CHANGE: <description>` - for breaking changes
- `Fixes #<issue>`, `Closes #<issue>`, `Resolves #<issue>` - for issue tracking
- `Refs #<issue>` - for issue references
- `Co-authored-by: Name <email>` - for human co-authors only

**Prohibited footers:**

- **NEVER include AI-generated trailers** such as:
  - `Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>`
  - `Generated-By: Claude Code`
  - `AI-Assisted: true`
  - Any other footer indicating AI involvement

**Rationale:** Commit history should reflect human authorship and decision-making. AI tools are development assistants, not co-authors.

## Scopes

Use a concise noun oriented around the domain:

- `terraform`, `aws`, `gha`, `cli`, `docs`, `security`
- `module/<name>` for specific modules
- Jira ticket as scope (`PROJ-1234`) when applicable

## Branch Naming

```
<type>/<scope>-<short-topic>[-issue-<n>]
```

Examples:

```
feat/terraform-lattice-issue-421
fix/gha-permissions-pr-comment
docs/upgrade-guide-3-8
```

## History Hygiene

- Prefer small, logically cohesive commits
- Squash only noisy/WIP histories
- Rebase onto `main` before merge (unless policy forbids)
- Separate mechanical formatting from logical changes

## Commit signing

**Strict default (repos using agent-engineering-handbook):** commits must be cryptographically signed (SSH, GPG, or S/MIME per Git/GitHub), unless `CONTRIBUTING.md` documents an approved exception.

- Prefer **repo-local** `git config` for `commit.gpgsign`, signing key, and `tag.gpgsign` for releases
- Verify with `git log -1 --show-signature`; enable **Require signed commits** on protected branches when policy allows
- **Agents:** never use `--no-gpg-sign` unless the user explicitly requests it and the reason is recorded; if signing fails, stop and fix config-do not silently create unsigned commits

Full detail: workspace rule `130-git.mdc` (section **Commit signing**).

## Pull Request Standards

**PR Title** mirrors commit header:

```
<type>(<scope>): <concise summary>
```

**Body** must include:

- **What & Why**
- **Risk / Impact** (breaking changes, migrations)
- **Tests** (added/updated + any manual validation)
- **Screenshots or artifacts** where relevant
- **Linked Issues** (`Fixes #123`)

## Commit Approval Workflow

AI agents must **NEVER** commit code without explicit user approval.

Before executing any `git commit`:

1. Show the complete commit message in a formatted preview
2. Display files to be committed
3. Ask for explicit confirmation
4. Only execute after receiving explicit user approval

## Repository Scaffolding

Every repo must contain:

| File | Requirement |
|------|-------------|
| `.gitignore` | Based on language/framework presets |
| `.editorconfig` | Consistent indentation, LF, charset |
| `.gitattributes` | Normalize line endings |
| `.pre-commit-config.yaml` | Language-specific hooks |
| `.markdownlint.yaml` | Markdown rules |
| `.commitlintrc.yaml` | Commit conventions |
| `.dependabot.yaml` | Dependency updates |
| `CODEOWNERS` | Review policy ownership |
| `.github/PULL_REQUEST_TEMPLATE.md` | PR format enforcement |

## Sign-off & Security

- Signed commits required unless documented exception in `CONTRIBUTING.md` (see **Commit signing** above)
- DCO sign-off if required by project
- No secrets in commits, diffs, PRs, or screenshots
- Large binaries → artifacts, not git

## Repo Creation Checklist

- [ ] Meta files exist and follow best practices
- [ ] Pre-commit hooks enabled and documented
- [ ] Codeowners enforce mandatory reviews
- [ ] PR template references testing + security checks
- [ ] Dependabot and automation enabled
- [ ] Commit signing documented (or exception in `CONTRIBUTING.md`); protected branches require signed commits when possible
- [ ] No secrets or credentials in history

## Additional Git Resources

For comprehensive Git guidance, see:

- [git-fundamentals.md](git-fundamentals.md) - Refs, three-tier model, fetch vs pull, feature branch workflow
- [git-reflog.md](git-reflog.md) - Reflog patterns, recovery workflows, Git's safety net
- [git-modern-commands.md](git-modern-commands.md) - Modern Git commands (switch, restore, mv), worktrees
- [git-pre-commit.md](git-pre-commit.md) - Pre-commit hooks setup and configuration
