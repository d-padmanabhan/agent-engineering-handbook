# Pre-Commit Hooks

## Why Pre-Commit?

Pre-commit hooks catch issues before they enter your commit history:

- Formatting errors (trailing whitespace, mixed line endings)
- Linting violations
- Security issues (leaked secrets, private keys)
- Large files that should not be committed
- Merge conflict markers left in code

## Manual Verification

Run hooks against all files before committing:

```bash
pre-commit run --all-files
```

Run against only staged files (faster):

```bash
pre-commit run
```

## Automatic Installation

Install hooks to run automatically on every commit:

```bash
pre-commit install
```

This creates a `.git/hooks/pre-commit` file that runs your configured checks.

## Keep Hooks Updated

Periodically update hook versions to get security fixes and improvements:

```bash
pre-commit autoupdate
```

Hook `rev` values must resolve to exact tags or SHAs. After `autoupdate`, review every hook change for runtime, file-scope, and mutation differences, then run the full suite. Follow the dependency and toolchain currency workflow (`${HANDBOOK_ROOT}/skills/core-engineering/references/dependency-and-toolchain-currency.md`).

> [!NOTE]
> If a commit fails because a hook modified task-scoped files, inspect the hook delta, rerun applicable verification, stage the reviewed changes, and retry. Include required generated, configuration, or lockfile changes from an authorized upgrade in the same commit. Do not stage pre-existing or concurrent unrelated files; another user or agent session may own them. If hook provenance is ambiguous or unexpectedly broad, stop and investigate instead of using `git add -A`.

## Example `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: detect-secrets

  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        language_version: python3.14

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/adrienverge/yamllint
    rev: v1.33.0
    hooks:
      - id: yamllint

  - repo: https://github.com/trufflesecurity/trufflehog
    rev: v3.63.0
    hooks:
      - id: trufflehog
```

## Common Pre-Commit Hooks

| Hook | Purpose |
|------|---------|
| `trailing-whitespace` | Remove trailing whitespace |
| `end-of-file-fixer` | Ensure files end with newline |
| `check-yaml` | Validate YAML syntax |
| `check-added-large-files` | Prevent large files |
| `check-merge-conflict` | Detect merge conflict markers |
| `detect-secrets` | Find secrets in code |
| `black` | Format Python code |
| `ruff` | Lint Python code |
| `shellcheck` | Lint shell scripts |
| `terraform_fmt` | Format Terraform files |
| `trufflehog` | Detect secrets |
