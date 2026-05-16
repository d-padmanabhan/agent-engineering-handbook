---
name: cicd-github-actions
description: GitHub Actions best practices for CI/CD workflows. Covers security (permissions, secrets), performance (caching, matrix builds), reusable workflows, and common patterns for testing, building, and deploying. Use when working with .github/workflows/*.yml files, GitHub Actions, or when asking about CI/CD pipelines and automation.
---

# GitHub Actions CI/CD

## Core Objectives

- **Security**: Minimal permissions, secrets handling, OIDC
- **Performance**: Caching, matrix builds, parallelization
- **Maintainability**: Reusable workflows, composite actions
- **Reliability**: Concurrency control, retry logic

## Essential Checklist

- [ ] Workflows use minimal permissions (`permissions: {}` at root)
- [ ] Secrets never logged or exposed in artifacts
- [ ] Concurrency control configured
- [ ] Timeout values set on all jobs
- [ ] Caching implemented for dependencies
- [ ] PR workflows use `pull_request`, not `pull_request_target`

## Minimal Permissions

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

# Default: no permissions
permissions: {}

jobs:
  test:
    runs-on: ubuntu-latest
    # Job-level permissions
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npm test
```

## Caching

```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'

# Or explicit caching
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

## Matrix Builds

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        node-version: [18, 20, 22]
        os: [ubuntu-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      - run: npm ci
      - run: npm test
```

## Concurrency Control

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

## Secrets Handling

```yaml
env:
  # Reference secrets in env
  API_KEY: ${{ secrets.API_KEY }}

steps:
  - name: Use secret safely
    run: |
      # Mask in logs
      echo "::add-mask::${{ secrets.API_KEY }}"
      # Use in command
      curl -H "Authorization: Bearer $API_KEY" https://api.acme.com
```

## Reusable Workflows

```yaml
# .github/workflows/reusable-build.yml
name: Reusable Build

on:
  workflow_call:
    inputs:
      node-version:
        required: false
        type: string
        default: '20'
    secrets:
      NPM_TOKEN:
        required: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
      - run: npm ci
      - run: npm run build
```

```yaml
# Calling workflow
jobs:
  build:
    uses: ./.github/workflows/reusable-build.yml
    with:
      node-version: '20'
    secrets:
      NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

## Job Outputs

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.value }}
    steps:
      - id: version
        run: echo "value=$(cat VERSION)" >> $GITHUB_OUTPUT

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying ${{ needs.build.outputs.version }}"
```

## Action-version audit (when editing or reviewing an existing workflow)

Before changing logic in any `.github/workflows/*.yml`, audit every `uses:` reference for staleness. Stale pins are easier to bump in the same PR than in a follow-up.

```bash
# Audit one workflow file
WORKFLOW=.github/workflows/ci.yml
grep -oE 'uses:\s*[^@]+@v[0-9]+' "$WORKFLOW" \
  | awk '{print $2}' \
  | sort -u \
  | while read ref; do
      action="${ref%@*}"
      pinned_major="${ref##*@}"
      latest=$(gh api "repos/$action/releases/latest" --jq '.tag_name | split(".")[0]' 2>/dev/null)
      if [[ -z "$latest" ]]; then
        printf "%-50s pinned=%s  latest=ARCHIVED-OR-MISSING\n" "$action" "$pinned_major"
      elif [[ "$latest" != "$pinned_major" ]]; then
        printf "%-50s pinned=%s  latest=%s  *** BUMP ***\n" "$action" "$pinned_major" "$latest"
      else
        printf "%-50s pinned=%s  latest=%s  ok\n" "$action" "$pinned_major" "$latest"
      fi
    done
```

Decision matrix per finding:

| Pin state | Action |
|---|---|
| Latest major > pinned major | Bump in this PR; separate commit `deps(actions): bump <owner>/<repo> vN -> vN+1`; check CHANGELOG for breaks |
| Latest major == pinned major | Leave alone (Dependabot covers minor/patch) |
| Repo archived / 404 / no releases | Flag + propose replacement; do not silently downgrade |
| `@main` / `@master` / `@latest` / unpinned | Replace with current major pin |
| SHA-pinned `@<40-char-sha>` | Verify SHA matches a tagged release; if bumping, replace with new release SHA (not major); repos that pin by SHA do so deliberately |
| `# FROZEN:` / `# do-not-bump` comment | Skip; note in PR |

For the rationale, the breaking-change protocol, and reasoning about supply-chain risk of `@main`, see `rules/160-github-actions.mdc`.

## Detailed References

- **Workflow Patterns**: See [references/workflow-patterns.md](references/workflow-patterns.md)
- **Security**: See [references/security.md](references/security.md)
- **Troubleshooting**: See [references/troubleshooting.md](references/troubleshooting.md)
