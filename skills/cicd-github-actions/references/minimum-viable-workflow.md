# Minimum Viable GitHub Actions Workflow

A copy-paste-ready workflow that satisfies every item in the
[cicd-github-actions Essential Checklist](../SKILL.md#essential-checklist).
Adapt the build/test/publish steps to the project. Keep the structural
elements (`permissions: {}`, `concurrency:`, `timeout-minutes:`).

## The workflow

```yaml
name: <project>-Build and Publish

# ================================================================
# Purpose: Builds, scans, publishes, and verifies the project artifact
#
# Triggers:
#   - Push to main under <source-path>/**
#   - Manual workflow dispatch
#
# Required Secrets:
#   - None: cloud and registry authentication use OIDC
#
# Dependencies:
#   - Package registry
#   - Configured vulnerability scanner
#   - Protected GitHub Environment when publication requires approval
#   - Release rollback runbook
# ================================================================

run-name: Build & Publish - ${{ github.ref_name }}

on:
  workflow_dispatch:
  push:
    branches: ['main']
    paths:
      - '<source-path>/**'

# Concurrency:
#   cancel-in-progress: true. The latest commit on a ref wins; in-flight
#   builds for the same ref are cancelled when a newer push arrives. Use
#   cancel-in-progress: false for deploys that must run to completion.
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

# Workflow-root permissions are zero. Each job grants only what it needs.
permissions: {}

env:
  # Pin static config here.
  REGISTRY: <registry-host>
  IMAGE_NAME: <image-or-artifact-name>

jobs:
  build-and-publish:
    name: Build and publish
    runs-on: ubuntu-latest  # or self-hosted label
    timeout-minutes: 30

    permissions:
      id-token: write       # OIDC for cloud / registry auth
      contents: read

    steps:
      - name: Checkout code
        uses: actions/checkout@v7

      - name: Generate version
        id: version
        run: |
          set -euo pipefail
          PACKAGE_VERSION=$(tr -d '[:space:]' < <source-path>/VERSION)
          COMMIT_HASH=${GITHUB_SHA:0:8}
          SEMVER="${PACKAGE_VERSION}-${COMMIT_HASH}"
          echo "semver=${SEMVER}" >> "$GITHUB_OUTPUT"
          echo "Full version: ${SEMVER}"

      # ... build, scan, publish, verify steps ...

      - name: Display build summary
        if: always()
        env:
          BUILD_VERSION: ${{ steps.version.outputs.semver }}
        run: |
          {
            echo "## Build & Publish complete"
            echo ""
            printf '**Version:** `%s`\n' "$BUILD_VERSION"
          } >> "$GITHUB_STEP_SUMMARY"
```

## Essential checklist mapping

Each line below is satisfied by something in the template above:

| Checklist item | Line / block |
| --- | --- |
| Bordered documentation after `name:` | Operational comment block at the top |
| `permissions: {}` at workflow root | `permissions: {}` near the top |
| Job-level permissions (least privilege) | `permissions:` inside `build-and-publish` |
| Concurrency control configured | `concurrency:` block |
| Timeout values set on all jobs | `timeout-minutes: 30` |
| Secrets never logged | `env:` is for non-secret config; secrets reach steps via step-level `env:` |
| `set -euo pipefail` in shells | Inside `run: \|` for any multi-line block |
| Env vars quoted: `"$GITHUB_OUTPUT"` | Used everywhere |
| Caching for dependencies when beneficial | Add `cache:` to the relevant setup action |
| PR workflows use `pull_request` not `pull_request_target` | Default to `pull_request` |

## Current public action versions

Verified 2026-09-26. Major versions are mutable, so verify the latest stable
release and published major alias before each change.

| Action | Latest major | Notes |
| --- | --- | --- |
| `actions/checkout` | `v7` | Review release notes and runner compatibility before upgrading |
| `actions/setup-node` | `v7` | Review runtime and automatic cache behavior |
| `actions/setup-python` | `v7` | Review runtime and dependency cache behavior |
| `actions/cache` | `v6` | Cache only reproducible, non-sensitive state |
| `actions/upload-artifact` | `v7` | v7 supports `archive: false` for unzipped single-file uploads; multi-file globs now fail without `archive: false` |
| `actions/download-artifact` | `v8` | Validate downloaded artifacts before privileged use |
| `actions/github-script` | `v9` | Keep untrusted expressions out of generated JavaScript |
| `jfrog/setup-jfrog-cli` | `v5` | v5 default runtime is Node 24; v4.10.x stays on Node 20 if runner is older |
| `hashicorp/vault-action` | `v4` | Verify runner compatibility before upgrading |
| `aws-actions/configure-aws-credentials` | `v6` | Use job-scoped OIDC |
| `docker/setup-buildx-action` | `v4` | |
| `docker/build-push-action` | `v7` | |

Refresh procedure:

```bash
pre-commit autoupdate                                  # if hooks reference actions
gh release view --repo actions/checkout                # spot check
rg "uses: actions/" .github/workflows/                 # find what is in use
```

## Common adaptations

### No-build static SPA (no Node deps)

- Drop the version step's dependency manager detection
- Read version from a `VERSION` file or git tag
- Skip dependency SCA (no lockfile to audit) - guard with `if: steps.detect-pm.outputs.manager != 'none'`

### Node application

- Add `actions/setup-node@v7` with `cache: 'npm'` and `cache-dependency-path: package-lock.json`
- Add `npm ci`
- Add `npm test` (for CI) or skip in build-and-publish if a separate test job exists

### Go binary

- Add `actions/setup-go@v7`
- Cache via `setup-go`'s built-in cache
- `CGO_ENABLED=0 GOOS=linux go build`

### Self-hosted runner

- Replace `runs-on: ubuntu-latest` with the runner label, e.g. `runs-on: [self-hosted, linux]`
- Confirm the label, Node runtime version, and tool availability with the runner owner before bumping action major versions

## Anti-patterns to keep out

- `permissions: write-all` at workflow root
- `runs-on: ubuntu-latest` without a `timeout-minutes:` (jobs can run for the GitHub default of 6 hours)
- `actions/checkout@main` (mutable, replays at every run)
- `pull_request_target` for any job that runs untrusted PR code
- Echoing secrets via `echo "${{ secrets.X }}"` (always use step-level `env:`)
- Running `npm install` / `pip install` directly from PR-supplied lockfiles in `pull_request_target` workflows

## Validation before merge

```bash
# Lint workflows (catches a lot of YAML and expression bugs)
brew install actionlint                # macOS
actionlint .github/workflows/*.yml

# Test locally with act if helpful
brew install act
act push -W .github/workflows/<name>.yml --container-architecture linux/amd64
```
