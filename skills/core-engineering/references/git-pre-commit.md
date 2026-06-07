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

> [!NOTE]
> If a commit fails due to pre-commit hook changes (e.g., auto-formatting), stage the changes and retry. Some hooks modify files in place to fix issues automatically.

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
