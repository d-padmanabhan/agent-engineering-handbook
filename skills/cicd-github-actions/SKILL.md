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
- [ ] A bordered operational header follows the workflow `name:`
- [ ] Untrusted contexts and inputs reach shell commands through step-level `env`
- [ ] Production deploys use protected GitHub Environments
- [ ] Changed workflows pass `actionlint`

## Workflow Authoring Contract

Put a bordered operational comment block immediately after the workflow name.
Use the headings `Purpose`, `Triggers`, `Required Secrets`, and `Dependencies`,
with blank comment lines between sections. Record approval, rollback, recovery,
or runbook requirements under `Dependencies`.

```yaml
name: Deploy Application

# ================================================================
# Purpose: Deploys a tested release to a protected environment
#
# Triggers:
#   - Manual workflow dispatch
#
# Required Secrets:
#   - None: cloud authentication uses OIDC
#
# Dependencies:
#   - Published release artifact
#   - Production GitHub Environment approval
#   - Rollback runbook: docs/deployment-rollback.md
# ================================================================
```

Document reusable workflow and action inputs, outputs, secrets, defaults, and
side effects where they are declared. Give jobs and non-obvious steps
descriptive names, but do not add comments that merely restate YAML. Keep
secret values, sensitive identifiers, and production data out of comments,
summaries, logs, and artifacts.

Use the
[workflow documentation reference](references/workflow-documentation.md) for
the complete header pattern, interface descriptions, comments, summaries, and
review checklist.

Treat `${{ github.event.* }}`, `${{ inputs.* }}`, issue text, branch names, and action outputs as untrusted data. Do not interpolate them directly into a `run:` script. Assign them to step-level `env`, quote the shell variable, and validate constrained values before use. See [Security](references/security.md).

For a complete starting point and local validation commands, use the [minimum viable workflow](references/minimum-viable-workflow.md).

## Minimal Permissions

```yaml
name: CI

# ================================================================
# Purpose: Runs bounded validation for main and pull requests
#
# Triggers:
#   - Push to main
#   - Pull requests targeting main
#
# Required Secrets:
#   - None
#
# Dependencies:
#   - Repository lockfile and test configuration
# ================================================================

on:
  push:
    branches: [main]
  pull_request:

# Default: no permissions
permissions: {}

jobs:
  test:
    name: Test
    runs-on: ubuntu-latest
    timeout-minutes: 30
    # Job-level permissions
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: '20'
      - run: npm ci
      - run: npm test
```

## Caching

```yaml
- uses: actions/setup-node@v7
  with:
    node-version: '20'
    cache: 'npm'

# Or explicit caching
- uses: actions/cache@v6
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
    name: Test Node.js ${{ matrix.node-version }} on ${{ matrix.os }}
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: read
    strategy:
      fail-fast: false
      matrix:
        node-version: [18, 20, 22]
        os: [ubuntu-latest, macos-latest]
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
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
steps:
  - name: Use secret safely
    env:
      API_KEY: ${{ secrets.API_KEY }}
    run: |
      set -euo pipefail
      curl --fail --silent --show-error \
        -H "Authorization: Bearer ${API_KEY}" \
        https://api.acme.com
```

## Reusable Workflows

```yaml
# .github/workflows/reusable-build.yml
name: Reusable Build

# ================================================================
# Purpose: Builds and tests one supported Node.js version for a caller
#
# Triggers:
#   - Reusable workflow call
#
# Required Secrets:
#   - NPM_TOKEN: required only for private dependencies
#
# Dependencies:
#   - Caller supplies a supported Node.js version
# ================================================================

on:
  workflow_call:
    inputs:
      node-version:
        description: Supported Node.js version to build and test.
        required: false
        type: string
        default: '20'
    secrets:
      NPM_TOKEN:
        description: Registry token required only for private dependencies.
        required: false

permissions: {}

jobs:
  build:
    name: Build
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
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
        run: echo "value=$(cat VERSION)" >> "$GITHUB_OUTPUT"

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Report version
        env:
          VERSION: ${{ needs.build.outputs.version }}
        run: printf 'Deploying %s\n' "$VERSION"
```

## Action-Version Audit

Before changing workflow logic, audit every `uses:` reference. By default, query the latest stable GitHub release, derive its major alias, verify that the upstream publishes the alias, and use that alias. If the user explicitly requests an exact stable tag or immutable commit SHA, verify and use the requested pinning mode instead.

```bash
action="OWNER/REPO"
latest_tag="$(gh api "repos/${action}/releases/latest" --jq '.tag_name')"
if [[ "${latest_tag}" =~ ^v([0-9]+)(\.[0-9]+){1,2}$ ]]; then
  major_tag="v${BASH_REMATCH[1]}"
else
  printf 'Unsupported stable release tag: %s\n' "${latest_tag}" >&2
  exit 1
fi
gh api "repos/${action}/git/ref/tags/${major_tag}" --silent
printf 'uses: %s@%s # latest stable: %s\n' "${action}" "${major_tag}" "${latest_tag}"
```

Decision matrix per finding:

| Pin state | Action |
|---|---|
| Verified latest stable major alias | Retain after compatibility review |
| Exact stable tag or immutable SHA explicitly requested by the user | Verify and retain the requested pinning mode |
| Older major, older exact tag, `@main`, `@master`, `@latest`, unpinned, or invented alias | Replace with the verified latest stable major alias unless the user requested another verified mode |
| Archived, missing, prerelease-only, or no verifiable stable release or major alias | Stop and report; do not silently downgrade or replace |

Major aliases and release tags are mutable Git references. Restrict workflows to reviewed actions, read release provenance and notes, preserve independently revertible upgrades, run `actionlint`, and let Dependabot or Renovate propose future updates. Follow the GitHub Actions rule (`${HANDBOOK_ROOT}/rules/160-github-actions.mdc`) and dependency currency workflow (`${HANDBOOK_ROOT}/skills/core-engineering/references/dependency-and-toolchain-currency.md`).

## Detailed References

- **Workflow Documentation**: See [references/workflow-documentation.md](references/workflow-documentation.md)
- **Minimum Viable Workflow**: See [references/minimum-viable-workflow.md](references/minimum-viable-workflow.md)
- **Workflow Patterns**: See [references/workflow-patterns.md](references/workflow-patterns.md)
- **Security**: See [references/security.md](references/security.md)
- **Troubleshooting**: See [references/troubleshooting.md](references/troubleshooting.md)
