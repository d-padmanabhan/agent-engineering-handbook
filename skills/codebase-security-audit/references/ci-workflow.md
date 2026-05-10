# Reference CI Workflow - 8-Layer Continuous Security

Drop-in `.github/workflows/security.yml` for any GitHub-hosted repo. Adjust language matrices per your stack. Block on Critical/High; warn on Medium.

```yaml
name: security

on:
  pull_request:
  push:
    branches: [main]
  schedule:
    # Daily refresh against newly-published CVEs.
    - cron: "0 6 * * *"
  workflow_dispatch:

# Least-privilege default; jobs that need more (CodeQL, dependency-review)
# elevate per-job.
permissions:
  contents: read

jobs:
  # ---------------------------------------------------------------------------
  # Layer 1 - Secrets scanning (regex + entropy + git history)
  # ---------------------------------------------------------------------------
  secrets:
    name: secrets (gitleaks + trufflehog)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: trufflehog
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          extra_args: --only-verified

  # ---------------------------------------------------------------------------
  # Layer 2 - SAST (Semgrep multi-pack + language-specific tool)
  # ---------------------------------------------------------------------------
  sast-semgrep:
    name: sast (semgrep)
    runs-on: ubuntu-latest
    container:
      image: returntocorp/semgrep:latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          semgrep ci \
            --config p/security-audit \
            --config p/owasp-top-ten \
            --config p/secrets \
            --config p/cwe-top-25 \
            --config p/python \
            --error

  sast-bandit:
    name: sast (bandit · python)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.14" }
      - run: pip install bandit[toml]
      - run: |
          bandit -r . \
            --severity-level medium \
            --confidence-level medium \
            --exclude ./.venv,./venv,./.git,./node_modules \
            -f txt

  # ---------------------------------------------------------------------------
  # Layer 5 - Semantic / CPG (CodeQL)
  # ---------------------------------------------------------------------------
  codeql:
    name: codeql (python)
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      actions: read
      contents: read
    strategy:
      matrix:
        language: [python]   # add javascript / go / java / cpp / csharp / ruby as needed
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
          queries: security-and-quality
      - uses: github/codeql-action/analyze@v3

  # ---------------------------------------------------------------------------
  # Layer 3 - SCA (dependencies + license)
  # ---------------------------------------------------------------------------
  sca-trivy:
    name: sca (trivy fs)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          scanners: vuln,license,secret,misconfig
          severity: CRITICAL,HIGH
          exit-code: "1"
          ignore-unfixed: true

  sca-osv:
    name: sca (osv-scanner)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google/osv-scanner-action/osv-scanner-action@v1.9.0
        with:
          scan-args: |-
            --recursive
            --skip-git
            ./

  sca-pip-audit:
    name: sca (pip-audit)
    runs-on: ubuntu-latest
    if: hashFiles('requirements.txt', 'pyproject.toml', 'poetry.lock') != ''
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.14" }
      - run: pip install pip-audit
      - run: pip-audit --strict

  # PR-only: GitHub-native dependency review against the merge base.
  dependency-review:
    name: dependency-review (pr)
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high
          comment-summary-in-pr: on-failure

  # ---------------------------------------------------------------------------
  # Layer 6 - IaC (Terraform / K8s / Dockerfile / CloudFormation)
  # ---------------------------------------------------------------------------
  iac-checkov:
    name: iac (checkov)
    runs-on: ubuntu-latest
    if: hashFiles('**/*.tf', '**/*.yaml', '**/*.yml', '**/Dockerfile') != ''
    steps:
      - uses: actions/checkout@v4
      - uses: bridgecrewio/checkov-action@master
        with:
          framework: all
          soft_fail: false

  # ---------------------------------------------------------------------------
  # Layer 8 - DAST (post-deploy, main only)
  # ---------------------------------------------------------------------------
  dast-staging:
    name: dast (zap baseline · staging)
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: zaproxy/action-baseline@v0.12.0
        with:
          target: "https://staging.example.com"
```

## Companion: `dependabot.yml`

```yaml
version: 2

updates:
  - package-ecosystem: pip
    directory: "/"
    schedule: { interval: weekly, day: monday, time: "06:00", timezone: America/New_York }
    open-pull-requests-limit: 5
    labels: [dependencies, security]
    commit-message: { prefix: "deps(pip)", include: scope }

  - package-ecosystem: github-actions
    directory: "/"
    schedule: { interval: weekly, day: monday, time: "06:00", timezone: America/New_York }
    open-pull-requests-limit: 5
    labels: [dependencies, ci]
    commit-message: { prefix: "deps(actions)", include: scope }
```

## Gating Recommendation

| Trigger | Required to pass | Allowed to warn |
|---|---|---|
| **Pull request** | secrets, sast-semgrep, sast-bandit, sca-trivy, sca-osv, sca-pip-audit, iac-checkov, dependency-review | codeql |
| **Merge to main** | all of the above + codeql | - |
| **Nightly schedule** | sca-* against fresh CVE feeds; alert on new Critical/High in unchanged code | - |
| **Post-deploy (main)** | dast-staging | - |

## Notes

- Use `actions/checkout@v4` with `fetch-depth: 0` for any job that scans git history.
- Pin third-party actions by SHA in security-sensitive repos (Dependabot will keep them updated).
- The CodeQL matrix should include every language present; add `javascript`, `go`, `java`, `cpp`, `csharp`, `ruby` as needed.
- For private repos with GitHub Advanced Security, CodeQL alerts surface in the Security tab with autofix suggestions.
- Substitute `sast-bandit` with `gosec`, `eslint-plugin-security`, `brakeman`, `spotbugs` per primary language.
