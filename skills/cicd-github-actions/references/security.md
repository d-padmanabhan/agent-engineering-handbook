# GitHub Actions Security

## Permissions

```yaml
# Minimal permissions by default
permissions: {}

# Or explicitly set what's needed
permissions:
  contents: read
  pull-requests: write
  issues: read

# Job-level overrides
jobs:
  build:
    permissions:
      contents: read
  deploy:
    permissions:
      contents: read
      id-token: write  # For OIDC
```

## OIDC for Cloud Authentication

```yaml
# AWS
- uses: aws-actions/configure-aws-credentials@v6
  with:
    role-to-assume: arn:aws:iam::123456789:role/github-actions
    aws-region: us-east-1

# GCP
- uses: google-github-actions/auth@v3
  with:
    workload_identity_provider: projects/123/locations/global/workloadIdentityPools/github/providers/github
    service_account: github-actions@project.iam.gserviceaccount.com

# Azure
- uses: azure/login@v3
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

## Secrets Best Practices

```yaml
# Pass a secret through the step environment, not script interpolation
- name: Deploy
  env:
    API_KEY: ${{ secrets.API_KEY }}
  run: |
    set -euo pipefail
    ./deploy.sh

# Never in artifact
- uses: actions/upload-artifact@v7
  with:
    name: build
    path: |
      dist/
      !dist/**/*.env  # Exclude env files
```

Prefer step-level secret scope. Do not persist secrets through `GITHUB_ENV` unless later steps genuinely need them, and never print a secret merely to mask it.

Secrets cannot be referenced directly in `if:`. Map the secret at job scope,
then test the `env` context on the step:

```yaml
jobs:
  publish:
    env:
      PUBLISH_TOKEN: ${{ secrets.PUBLISH_TOKEN }}
    steps:
      - name: Publish when credentials are available
        if: env.PUBLISH_TOKEN != ''
        run: ./scripts/publish.sh
```

## Untrusted Contexts and Inputs

GitHub expressions are expanded before the shell parses a `run:` script. Shell quoting around `${{ ... }}` does not prevent command injection.

```yaml
# Unsafe: pull request titles can contain shell syntax
- run: echo "${{ github.event.pull_request.title }}"

# Safe: keep untrusted data out of the generated script
- name: Print pull request title
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: printf '%s\n' "$PR_TITLE"
```

Apply the same pattern to issue bodies, commit messages, branch names, dispatch inputs, matrix values, and third-party action outputs. For constrained inputs such as environments or versions, validate against an allowlist or strict format before using them in paths, commands, or deployment decisions.

## Third-Party Actions

Default to the verified latest stable major alias, such as
`actions/checkout@v7`. If the user explicitly requests an exact stable tag or
immutable commit SHA, verify and use that requested mode. Never use `@main`,
`@master`, `@latest`, an invented tag, or an unverified alias.

## Branch Protection

```yaml
# Only trigger on protected branches
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

# Use pull_request not pull_request_target for PRs
# pull_request_target has write access - dangerous for forks
```

## Protected Deployment Environments

Use a GitHub Environment for each deployment boundary, especially production. Configure required reviewers and deployment-branch restrictions in repository settings, and keep production credentials environment-scoped.

```yaml
jobs:
  deploy:
    environment:
      name: production
      url: https://app.acme.com
    permissions:
      contents: read
      id-token: write
```

Environment approval is the authorization gate. Do not implement production authorization by comparing `github.actor` to a username in workflow code.

## Self-Hosted Runner Trust Boundary

Treat a self-hosted runner as privileged infrastructure:

- Do not run untrusted fork or pull-request code on runners with internal network or credential access
- Prefer ephemeral, single-job runners with clean state
- Isolate runner groups by environment and restrict which workflows may target them
- Allowlist required egress and avoid exposing broad internal networks
- Keep the runner, base image, and preinstalled tools patched and monitored

Use GitHub-hosted runners by default when the workload does not require private networking, specialized hardware, or a controlled execution environment.

## Dependency Review

Use the repository's approved dependency-review integration and fail on the
configured severity policy. Verify that its latest stable release publishes the
required major alias before adding a `uses:` reference. Stop and report when
the latest release has no verifiable major alias instead of inventing one or
silently selecting an older major.

## Secret Scanning

```yaml
name: Security Scan

# ================================================================
# Purpose: Scans repository history for committed secrets
#
# Triggers:
#   - Push to main
#   - Pull requests
#
# Required Secrets:
#   - None
#
# Dependencies:
#   - Complete repository history
#   - Approved secret-scanning action
# ================================================================

on:
  push:
    branches: [main]
  pull_request:

permissions: {}

jobs:
  secrets:
    name: Scan secrets
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v3
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Supply Chain Security

```yaml
- name: Generate SBOM
  uses: anchore/sbom-action@v0
  with:
    path: .
    format: spdx-json
    output-file: sbom.json

- name: Scan for vulnerabilities
  uses: anchore/scan-action@v7
  with:
    sbom: sbom.json
    fail-build: true
    severity-cutoff: high
```
