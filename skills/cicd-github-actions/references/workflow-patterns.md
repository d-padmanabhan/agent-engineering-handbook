# Workflow Patterns

## Pull Request Workflow

```yaml
name: PR Check

# ================================================================
# Purpose: Lints and tests pull-request code without deployment access
#
# Triggers:
#   - Pull requests targeting main
#
# Required Secrets:
#   - None
#
# Dependencies:
#   - Repository lockfile and test configuration
# ================================================================

on:
  pull_request:
    branches: [main]

permissions: {}

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint

  test:
    name: Test
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test -- --coverage
      - uses: actions/upload-artifact@v7
        with:
          name: coverage
          path: coverage/
          retention-days: 7
```

## Release Workflow

```yaml
name: Release

# ================================================================
# Purpose: Builds and publishes a tagged npm release
#
# Triggers:
#   - Version tags
#
# Required Secrets:
#   - NPM_TOKEN: publishes the package to the registry
#
# Dependencies:
#   - Valid package metadata and lockfile
#   - Package release runbook for partial publication
# ================================================================

on:
  push:
    tags:
      - 'v*'

permissions: {}

jobs:
  release:
    name: Publish release
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: write
      packages: write
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'

      - run: npm ci
      - run: npm run build
      - run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

      - uses: softprops/action-gh-release@v3
        with:
          generate_release_notes: true
```

## Docker Build and Push

```yaml
name: Docker

# ================================================================
# Purpose: Builds and publishes versioned container images
#
# Triggers:
#   - Push to main
#   - Version tags
#
# Required Secrets:
#   - None: publication uses the job-scoped repository token
#
# Dependencies:
#   - GitHub Container Registry
#   - Valid container build definition
# ================================================================

on:
  push:
    branches: [main]
    tags: ['v*']

permissions: {}

jobs:
  build:
    name: Build and publish image
    runs-on: ubuntu-latest
    timeout-minutes: 45
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v7

      - uses: docker/setup-buildx-action@v4

      - uses: docker/login-action@v4
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/metadata-action@v6
        id: meta
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}

      - uses: docker/build-push-action@v7
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## Scheduled Workflow

```yaml
name: Scheduled Tasks

# ================================================================
# Purpose: Runs bounded repository maintenance
#
# Triggers:
#   - Daily schedule
#   - Manual workflow dispatch
#
# Required Secrets:
#   - None
#
# Dependencies:
#   - Repository maintenance scripts
# ================================================================

on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight UTC
  workflow_dispatch:  # Manual trigger

permissions: {}

concurrency:
  group: scheduled-maintenance
  cancel-in-progress: false

jobs:
  cleanup:
    name: Run maintenance
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v7
      - run: ./scripts/cleanup.sh
```

## Environment Deployments

```yaml
name: Deploy

# ================================================================
# Purpose: Promotes a tested release through protected environments
#
# Triggers:
#   - Push to main
#
# Required Secrets:
#   - None: deployment uses environment-scoped OIDC
#
# Dependencies:
#   - Tested release artifact
#   - Production GitHub Environment approval
#   - Deployment rollback runbook
# ================================================================

on:
  push:
    branches: [main]

permissions: {}

jobs:
  staging:
    name: Deploy to staging
    runs-on: ubuntu-latest
    timeout-minutes: 30
    environment: staging
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v7
      - run: ./deploy.sh staging

  production:
    name: Deploy to production
    needs: staging
    runs-on: ubuntu-latest
    timeout-minutes: 30
    environment:
      name: production
      url: https://app.acme.com
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v7
      - run: ./deploy.sh production
```

## Path Filters

```yaml
on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'package.json'
      - '.github/workflows/ci.yml'
    paths-ignore:
      - '**.md'
      - 'docs/**'
```

## Conditional Steps

```yaml
steps:
  - name: Only on main
    if: github.ref == 'refs/heads/main'
    run: echo "On main branch"

  - name: Only on tags
    if: startsWith(github.ref, 'refs/tags/')
    run: echo "On tag"

  - name: Only on failure
    if: failure()
    run: echo "Previous step failed"
```

## Common Anti-Patterns

### Hardcoding Runner OS Commands

```yaml
# BAD: Breaks on Windows and macOS
- run: rm -rf dist/

# GOOD: Select Bash explicitly and check the path
- run: |
    if [ -d dist ]; then rm -rf dist; fi
  shell: bash
```

### Not Cleaning Up Artifacts

```yaml
# BAD: Retention is not tied to operational need
- uses: actions/upload-artifact@v7
  with:
    name: logs

# GOOD: Set intentional retention
- uses: actions/upload-artifact@v7
  with:
    name: logs
    retention-days: 7  # Adjust based on needs
```

### Missing Timeout Protection

```yaml
# BAD: Job runtime is not bounded
jobs:
  build:
    runs-on: ubuntu-latest

# GOOD: Set a justified timeout
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 30
```

## Dynamic Input Choices

Use `workflow_dispatch` with choice inputs for better UX:

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        type: choice
        options:
          - development
          - staging
          - production
      log-level:
        description: 'Log level'
        type: choice
        options:
          - debug
          - info
          - warning
          - error
        default: 'info'
      dry-run:
        description: 'Dry run mode'
        type: boolean
        default: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy
        env:
          TARGET_ENVIRONMENT: ${{ inputs.environment }}
          LOG_LEVEL: ${{ inputs.log-level }}
          DRY_RUN: ${{ inputs.dry-run }}
        run: |
          printf 'Deploying to %s\n' "$TARGET_ENVIRONMENT"
          printf 'Log level: %s\n' "$LOG_LEVEL"
          printf 'Dry run: %s\n' "$DRY_RUN"
```

## Choose the Smallest Reuse Boundary

- Use a **composite action** for a repeated sequence of steps that runs inside one job and does not need its own runner, permissions, or approval boundary.
- Use a **reusable workflow** for one or more complete jobs that need explicit inputs, secrets, outputs, permissions, runners, or environments.
- Keep logic local until it is repeated and stable. Premature shared abstractions make workflow behavior harder to inspect and change.

Define inputs and secrets explicitly. Avoid `secrets: inherit` across broad trust boundaries because it obscures which credentials the called workflow receives.

## Actionable Workflow Summary

Add a concise summary when the run produces information a reviewer or operator needs. Prefer the built-in summary file over a PR comment unless the result must remain attached to the pull request.

```yaml
- name: Write workflow summary
  if: always()
  env:
    EVENT_NAME: ${{ github.event_name }}
    REF_NAME: ${{ github.ref_name }}
    JOB_STATUS: ${{ job.status }}
  run: |
    {
      printf '## CI result\n\n'
      printf -- '- Event: `%s`\n' "$EVENT_NAME"
      printf -- '- Ref: `%s`\n' "$REF_NAME"
      printf -- '- Status: `%s`\n' "$JOB_STATUS"
    } >> "$GITHUB_STEP_SUMMARY"
```

Keep summaries free of secrets and sensitive raw logs. Link to retained artifacts for detailed output.
