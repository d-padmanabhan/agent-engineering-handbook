---
name: codebase-security-audit
description: End-to-end codebase security audit using the practical eight-layer model - secrets scanning (regex + entropy), SAST (with taint analysis), SCA (deps + license), data-flow / taint, semantic / code-property-graph, IaC, custom rules, and DAST validation. Produces a severity-ranked remediation plan, .env templates, and a ready-to-use CI/CD continuous-scanning workflow. Covers OWASP Top 10 (2021) A01-A10 with curated ripgrep playbooks per category. Use when the user asks to "security audit", "harden this repo", "check for secrets", "find committed secrets", "OWASP audit", "SAST scan", "SCA / dependency audit", "IaC audit", "DAST validation", or "check for vulnerabilities".
---

# Codebase Security Audit & Remediation

A systematic, multi-layer security review with actionable fixes. Combines static (SAST), composition (SCA), secrets, data-flow / taint, semantic / CPG, infrastructure (IaC), custom rules, and dynamic (DAST) checks - and wires the results into CI/CD for continuous coverage.

**Companion rules:**

- `310-security.mdc` - principles + OWASP Top 10 + NHI Top 10
- `316-zero-trust.mdc` - Zero Trust principles (always-on)
- `160-github-actions.mdc` - secure CI workflow patterns

---

## When to invoke

Use when the user asks to:

- "Security audit" / "harden this repo" / "check for vulnerabilities"
- "Find committed secrets" / "scan for credentials"
- "OWASP audit" / "Top 10 review"
- "SAST scan" / "SCA / dependency audit" / "IaC audit" / "DAST validation"
- "Set up continuous security scanning"
- Open / re-open a security incident triage on a codebase

---

## Tooling Stack - Eight Practical Layers

Map every audit to these eight layers so coverage is explicit and gaps are visible.

| # | Layer | Purpose | Recommended Tools |
|---|---|---|---|
| 1 | **Secrets scanning** | Find exposed credentials in code & git history (regex + entropy) | `gitleaks`, `trufflehog`, `detect-secrets`, `ggshield`, ripgrep regex |
| 2 | **SAST** (static) | Code-level vulns - injection, crypto, access control | `semgrep`, `codeql`, `bandit` (Python), `gosec` (Go), `eslint-plugin-security` (JS/TS), `spotbugs` + `find-sec-bugs` (Java), `brakeman` (Ruby), `cppcheck` / `flawfinder` (C/C++) |
| 3 | **SCA** (deps) | Vulnerable / outdated / license-risky packages | `pip-audit`, `safety`, `npm audit`, `yarn audit`, `govulncheck`, `mvn dependency-check`, `osv-scanner`, `grype`, `trivy fs`, Snyk, Dependabot / Renovate |
| 4 | **Data-flow / taint** | Track untrusted input through code to a dangerous sink | `semgrep` (`mode: taint`), CodeQL data-flow libs, Pysa (Python) |
| 5 | **Semantic / CPG** | Behavior-aware deep analysis - privilege escalation, auth bypass | CodeQL (full DB build), Joern |
| 6 | **IaC scanning** | Misconfig in Terraform / K8s / cloud / Dockerfiles | `checkov`, `tfsec`, `terrascan`, `kube-linter`, `kubesec`, `kics`, `trivy config`, `hadolint` |
| 7 | **Custom rules** | Business-specific risks the off-the-shelf rules miss | Semgrep custom rules in `.semgrep/`, CodeQL custom queries in `.github/codeql/` |
| 8 | **DAST** (dynamic) | Validate runtime behavior on the deployed app | OWASP ZAP, Nuclei, Burp Suite, sqlmap (targeted) |

### Accuracy Principles (apply to every layer)

- **Data-flow > regex** for code-level findings - taint analysis cuts false positives sharply.
- **Combine multiple scanners** - overlap = confidence; gaps = blind spots.
- **Prioritize exploitability**, not just presence - internet-reachable + sensitive data + auth boundary crossed = top.
- **Tune rules** - suppress justified false positives with file-scoped comments (`# nosec`, `// semgrep-ignore`) and track them in an exception register.
- **Keep vuln databases fresh** - refresh OSV / GitHub Advisory feeds at least daily; pin scanner versions in CI.
- **Run continuously in CI/CD** - every PR, every merge, every deploy. Block on Critical/High; warn on Medium.

---

## Audit Workflow

### Phase 1 - Secrets Scanning (regex + entropy + history)

Combine regex (catches known formats) with entropy and verified-secret scanning (catches unknown formats).

#### 1a. Regex scan of the current tree

```python
PATTERNS = [
    r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[\w\-]{20,}',
    r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\']?[^\s"\']{8,}',
    r'(?i)(token|bearer)\s*[=:]\s*["\']?[\w\-\.]{20,}',
    r'(?i)(aws_access_key_id)\s*[=:]\s*[A-Z0-9]{20}',
    r'(?i)(aws_secret_access_key)\s*[=:]\s*[\w/+=]{40}',
    r'ghp_[A-Za-z0-9]{36}',                      # GitHub PAT
    r'xox[bpors]-[\w\-]{10,}',                   # Slack tokens
    # Private-key headers - replace BEGIN_MARKER and KEY_MARKER with the literal
    # text -----BEGIN<space> and PRIVATE<space>KEY respectively. Tokenized here
    # so this rule file does not trip the detect-private-key pre-commit hook.
    r'<BEGIN_MARKER>(RSA |EC |DSA )?<KEY_MARKER>',
    r'jdbc:[\w]+://[^\s"]+',                     # JDBC connection strings
    r'mongodb(\+srv)?://[^\s"]+',                # MongoDB URIs
    r'https?://[\w:]+@',                         # URLs with credentials
]
```

```bash
rg --no-heading -n '<pattern>' --glob '!node_modules' --glob '!.git' --glob '!*.min.js'
```

#### 1b. Entropy & verified-secret scan

```bash
gitleaks detect --redact --no-banner --report-format json --report-path gitleaks.json

trufflehog filesystem --json --no-update . > trufflehog.json
trufflehog git file://. --since-commit HEAD~500 --json > trufflehog-history.json

detect-secrets scan --all-files > .secrets.baseline
```

#### 1c. Git history scan (deep)

```bash
git log --all --diff-filter=A -p -- '*.env' '*.pem' '*.key' 'credentials*' 'config/secrets*'
# Replace KEY_MARKER below with the literal text BEGIN<space>PRIVATE<space>KEY
# (tokenized to avoid tripping the detect-private-key pre-commit hook in this rule file)
KEY_MARKER="<KEY_MARKER>"
git log --all -p -S "$KEY_MARKER" --
git log --all -p -S 'password' -- '*.py' '*.js' '*.yaml' '*.json' '*.yml'
gitleaks detect --log-opts="--all"
```

For each finding capture: commit hash, date, author, file path, whether the secret was later removed, and (if a tool reports it) whether the secret has been verified as live.

Exclude known false positives: test fixtures, documentation examples, placeholder values like `your-key-here`.

### Phase 2 - Software Composition Analysis (SCA)

Most real-world vulns come from libraries. Run scanners per ecosystem, then prioritize by exploitability.

#### 2a. Per-ecosystem dependency scanners

```bash
# Python
pip-audit --strict
safety check --full-report

# Node
npm audit --omit=dev
yarn audit --groups dependencies

# Go
govulncheck ./...

# Java / Maven / Gradle
mvn org.owasp:dependency-check-maven:check
gradle dependencyCheckAnalyze

# Ruby
bundle audit check --update

# Rust
cargo audit

# .NET
dotnet list package --vulnerable --include-transitive

# Multi-ecosystem
osv-scanner --recursive .
grype dir:.
trivy fs --scanners vuln,license,secret .
```

#### 2b. License risk

```bash
trivy fs --scanners license .
# or per-ecosystem: pip-licenses, license-checker (Node), go-licenses
```

Flag copyleft / non-commercial / unknown licenses on dependencies that ship in the product.

#### 2c. Prioritization

Rank findings in this order:

1. **Exploitability** - known exploited (CISA KEV), reachable from network, reachable code path.
2. **Severity** - CVSS >= 7.0 first, but use EPSS percentile when available.
3. **Fix availability** - patched version exists -> fix now.
4. **Blast radius** - service-tier, data sensitivity.

Output one row per finding: `package@version`, CVE/GHSA, CVSS, EPSS, fixed-in, license, ecosystem, severity, recommended action (upgrade / pin / replace / accept-with-justification).

Automate with **Dependabot** / **Renovate** for routine bumps; subscribe to GitHub Security Advisories per repo.

### Phase 3 - SAST (Static Application Security Testing)

Three sub-layers: quick code-smell review, an OWASP Top 10 curated catalog, and tool-driven SAST.

#### 3a. Code Smell Review (quick pass)

| Issue | What to Look For |
|---|---|
| Hardcoded URLs | Base URLs, API endpoints that vary by environment |
| Hardcoded IDs | Cloud account IDs, org IDs, project IDs |
| Debug flags | `DEBUG = True`, verbose logging in production code |
| Insecure defaults | `verify=False`, `allow_all_origins`, disabled auth |
| Missing input validation | User input passed directly to queries/commands |
| Overly broad exceptions | `except Exception: pass` hiding errors |

#### 3b. OWASP Top 10 (2021) Curated Checklist

For full operational depth (per-OWASP-category ripgrep snippets and fixes), see [references/owasp-top-10-playbook.md](references/owasp-top-10-playbook.md).

Quick pointers per category:

- **A01 Broken Access Control** - server-side authz on every route; CORS allow-list; IDOR ownership checks.
- **A02 Cryptographic Failures** - argon2/bcrypt for passwords; TLS verify on; AES-GCM with random IVs; KMS for keys; redact PII before logging.
- **A03 Injection** - parameterized queries; allow-list shell args; never `eval`/`exec`; auto-escaping templates.
- **A04 Insecure Design** - rate limits + lockouts; abuse cases; idempotency keys.
- **A05 Security Misconfiguration** - debug off in prod; least-privilege IAM; security headers; lock down management endpoints.
- **A06 Vulnerable Components** - covered by Phase 2 (SCA).
- **A07 AuthN Failures** - strong password policy (NIST 800-63B); HttpOnly/Secure/SameSite cookies; validate JWT alg/exp/iss/aud; MFA.
- **A08 Software/Data Integrity Failures** - safe yaml load; never pickle untrusted; sign artifacts (Sigstore/cosign); pin GitHub Actions by SHA.
- **A09 Logging/Monitoring Failures** - structured logs to SIEM; alerts on auth-failure spikes and admin actions.
- **A10 SSRF** - destination allow-list; block RFC1918/link-local/cloud-metadata; egress proxy with policy.

#### 3c. Language-aware SAST tools

```bash
# Python
bandit -r . -ll -ii -f json -o bandit.json

# Go
gosec -fmt=json -out=gosec.json ./...

# JavaScript / TypeScript
eslint --ext .js,.jsx,.ts,.tsx --plugin security --rule 'security/detect-eval-with-expression:error' .

# Java
spotbugs -textui -include findsecbugs-include.xml -output spotbugs.xml target/classes

# Ruby on Rails
brakeman -o brakeman.json --format json

# C / C++
flawfinder --html .   # or: cppcheck --enable=warning,style,performance,portability .

# PHP
psalm --taint-analysis
```

#### 3d. Multi-language SAST: Semgrep

```bash
semgrep --config=p/security-audit \
        --config=p/owasp-top-ten \
        --config=p/secrets \
        --config=p/cwe-top-25 \
        --json --output=semgrep.json .
```

Run language-specific packs as needed: `p/python`, `p/javascript`, `p/typescript`, `p/golang`, `p/java`, `p/ruby`, `p/csharp`, `p/terraform`, `p/dockerfile`, `p/kubernetes`.

### Phase 4 - Data-Flow / Taint Analysis

Tracks **untrusted source -> dangerous sink**; the single biggest precision boost over regex SAST.

#### Semgrep taint mode (lightweight, fast)

```yaml
# .semgrep/sql-injection-taint.yaml
rules:
  - id: sql-injection-taint
    mode: taint
    pattern-sources:
      - patterns:
          - pattern-either:
              - pattern: request.args.get(...)
              - pattern: request.json[...]
              - pattern: request.form[...]
    pattern-sinks:
      - pattern-either:
          - pattern: $CONN.execute($Q, ...)
          - pattern: $CONN.cursor().execute($Q, ...)
    pattern-sanitizers:
      - pattern: sqlalchemy.text($Q).bindparams(...)
    message: User input flows into a SQL query without parameterization
    languages: [python]
    severity: ERROR
```

Run: `semgrep --config .semgrep/ .`

#### CodeQL (deep, GitHub Advanced Security)

```bash
codeql database create db --language=python --source-root=.
codeql database analyze db codeql/python-queries:Security \
  --format=sarifv2.1.0 --output=codeql.sarif
```

Use built-in queries `python-queries:Security/CWE-089/SqlInjection.ql`, etc., or write a custom data-flow query for an app-specific source/sink pair.

#### Pysa (Python, Meta)

```bash
pyre init && pyre analyze --no-verify --save-results-to .pysa-results
```

### Phase 5 - Semantic / Code Property Graph (advanced)

For complex flaws - privilege escalation paths, auth bypass, multi-step exploits. More compute but high precision.

- **CodeQL** - full DB build per language; richest query library.
- **Joern** - open-source CPG; supports Java, JS, Python, C/C++, Go, Kotlin.

  ```bash
  joern-parse .
  joern --script audit.sc           # run a query script over the CPG
  ```

Use cases: locate every path from an HTTP entry point that reaches an unauthenticated DB write; locate functions that read `is_admin` without first calling `verify_session`.

This phase is optional for small repos but **strongly recommended for systems handling auth, payments, PII, or PHI**.

### Phase 6 - Infrastructure-as-Code (IaC) Scanning

If the repo contains Terraform, CloudFormation, Kubernetes manifests, Helm charts, or Dockerfiles.

```bash
# Multi-IaC, single tool
checkov --directory . --framework all --output json --output-file-path checkov.json

# Terraform-specific
tfsec . --format json --out tfsec.json
terrascan scan -d . -o json > terrascan.json

# Kubernetes
kube-linter lint .
kubesec scan deployment.yaml
kics scan -p . -o kics.json --report-formats json

# Container images / Dockerfiles
hadolint Dockerfile
trivy config .
trivy image <image:tag>
```

Common IaC findings to flag:

- S3 buckets with `public-read` / `AllUsers` ACL.
- Security groups allowing `0.0.0.0/0` on sensitive ports (22, 3389, 3306, 5432, 6379, 27017, 9200).
- IAM policies with `Action: "*"` or `Resource: "*"`.
- K8s pods running as root (`runAsNonRoot: false`), without `readOnlyRootFilesystem`, with `privileged: true`, with `hostNetwork`/`hostPID`.
- K8s missing `NetworkPolicy`.
- Dockerfiles using `:latest`, running as root, or leaking secrets via `ARG`.
- Unencrypted storage / databases (`encrypted = false`).
- Secrets in env values instead of Secret refs / Vault / KMS.

### Phase 7 - Custom Rules (business-specific)

Off-the-shelf rules miss internal frameworks, data classifications, and house auth conventions. This is where the most accurate detections come from.

Place rules at:

- **Semgrep**: `.semgrep/<rule>.yaml` - picked up by `semgrep --config .semgrep/`.
- **CodeQL**: `.github/codeql/custom-queries/` - referenced from CodeQL workflow.

Examples to author for any non-trivial repo:

1. **Internal auth decorator missing** - every handler in `routes/` must have `@require_auth(scope=...)` or `@public_endpoint`.
2. **PII fields without redaction** - any logger call with a known PII field name (`email`, `ssn`, `phone`, `dob`, `card_number`) must wrap it in `redact()`.
3. **Internal SDK misuse** - internal HTTP client `mck_http.get()` must always pass `timeout=` and `verify=True`.
4. **Forbidden imports** - block `import requests` in modules that should use the internal client; block `import pickle` in services that accept external input.
5. **Tenant-scope check** - every DB query in a multi-tenant service must include a `tenant_id` filter.

Sample Semgrep custom rule: see [references/semgrep-custom-rules.md](references/semgrep-custom-rules.md).

### Phase 8 - DAST Validation (optional, runtime)

Validates exploitability of SAST findings against the running app. Use against staging, **never** prod-without-isolation.

```bash
# OWASP ZAP baseline (passive, fast)
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://staging.example.com -J zap-baseline.json

# ZAP full scan (active, slow, thorough)
docker run -t owasp/zap2docker-stable zap-full-scan.py \
  -t https://staging.example.com -J zap-full.json

# Nuclei (template-driven, very fast)
nuclei -u https://staging.example.com -severity critical,high,medium \
  -json -o nuclei.json

# Targeted: sqlmap on a specific suspect endpoint
sqlmap -u "https://staging.example.com/search?q=1" --batch --risk=2 --level=3
```

Use DAST to **confirm** SAST/CodeQL findings (especially A01, A03, A07, A10) and to catch runtime-only issues - TLS config, header drift, error-page leakage, session fixation.

### Phase 9 - .gitignore Audit

Verify these entries exist:

```gitignore
# Secrets & local config
.env
.env.*
*.pem
*.key
credentials.json
secrets.yaml
setup-env.sh
run-local.sh

# Scanner output
gitleaks.json
trufflehog*.json
semgrep.json
bandit.json
gosec.json
checkov.json
tfsec.json
trivy*.json
codeql.sarif
.pysa-results/

# IDE & OS
.DS_Store
.idea/
.vscode/settings.json

# Build artifacts
__pycache__/
node_modules/
dist/
*.pyc
```

### Phase 10 - Generate Remediation

#### .env.template

```env
# Required - GitHub personal access token with repo scope
GITHUB_TOKEN=

# Required - Jira cloud instance ID
JIRA_CLOUD_ID=

# Optional - override default batch size (default: 50)
BATCH_SIZE=50
```

#### setup-env.sh

```bash
#!/bin/bash
# Source this file to set environment variables for local development
# Usage: source setup-env.sh

export GITHUB_TOKEN="$(gh auth token)"
export JIRA_CLOUD_ID="your-cloud-id-here"
```

Add to `.gitignore` immediately after creation.

#### Severity & action matrix (exploitability-weighted)

| Severity | Examples | Action |
|---|---|---|
| **Critical** | Active secret in current code; SQLi/cmdi/SSRF reachable from internet; `alg:none` JWT; `eval` / `pickle.loads` on user input; CISA KEV-listed CVE in a public service; public S3 bucket with PII | Rotate any exposed secret, ship a hotfix, add a regression test, file an incident if data may have been accessed |
| **High** | Secret in git history; OWASP A02/A05/A06/A07/A08 with active exposure; permissive IAM (`*`/`*`); outdated dependency with known critical CVE; missing auth on sensitive route; K8s pod running privileged | Rotate the secret; patch in next deploy; consider BFG Repo-Cleaner if repo is shared |
| **Medium** | Hardcoded config; missing security headers; weak password policy; verbose logs of non-secret data; OWASP A09 gaps; copyleft-license risk on shipped dependency | Externalize to env var / config; add headers and logging in current sprint |
| **Low** | Code smells, defensive hardening, lint-level issues, unused dependencies | Fix in next commit / backlog |

Map every OWASP / SAST / SCA / IaC / DAST finding to one severity using **exploitability + blast radius**: data sensitivity, auth boundary crossed, internet-reachable, KEV/EPSS percentile, fix availability.

### Phase 11 - Verify

After fixes:

1. Re-run **secrets** scanners (regex + gitleaks + trufflehog) - confirm zero findings.
2. Re-run **SAST** (`semgrep`, language tool) - confirm previously flagged patterns no longer match.
3. Re-run **SCA** (`pip-audit` / `npm audit` / `govulncheck` / `osv-scanner` / `trivy fs`) - confirm no Critical/High CVEs.
4. Re-run **taint / CodeQL** queries on the fixed sources/sinks.
5. Re-run **IaC** (`checkov`, `tfsec`, `kube-linter`).
6. Re-run **DAST** baseline against staging.
7. Check `.gitignore` covers all sensitive files and scanner output.
8. Verify the app still runs with env vars: `source setup-env.sh && python main.py`.

### Phase 12 - Continuous Scanning in CI/CD

Wire the layers into CI so every PR and merge is scanned automatically. Block on Critical/High; warn on Medium.

A complete reference workflow lives at [references/ci-workflow.md](references/ci-workflow.md). The skeleton:

- **secrets** - gitleaks + trufflehog (verified-only)
- **sast-semgrep** - multi-pack semgrep
- **sast-bandit** - language-specific tool (Bandit for Python; substitute per stack)
- **codeql** - matrix per language
- **sca-trivy** + **sca-osv** + **sca-pip-audit** (etc per ecosystem)
- **dependency-review** - PR-only, GitHub-native
- **iac** - checkov
- **dast-staging** - main-only, ZAP baseline against staging

Recommended gating:

- **PRs**: secrets + SAST + SCA + IaC must pass; CodeQL warns.
- **Merge to main**: above + CodeQL must pass.
- **Nightly**: re-run SCA against fresh CVE feeds; alert on new Critical/High in unchanged code.
- **Post-deploy**: DAST baseline against staging.

---

## Git History Remediation

If secrets were committed and the repo has collaborators:

```bash
# Option 1: BFG Repo-Cleaner (preferred, faster)
bfg --replace-text passwords.txt repo.git

# Option 2: git filter-repo
git filter-repo --invert-paths --path <secret-file>
```

**Always rotate the exposed credentials first** - cleaning history alone is not sufficient.

If no collaborators, a simpler approach:

```bash
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch <file>' HEAD
git push origin --force --all
```

---

## Output Format

Present findings as a structured report with **severity, layer (Secrets / SAST / SCA / Taint / CPG / IaC / DAST / Custom), OWASP ID (where applicable), file:line, evidence, and recommended action**. Group by severity (Critical first). Include an executive summary at the top.

```markdown
## Executive Summary
- Total findings: <N> (Critical: X, High: Y, Medium: Z, Low: W)
- Layer coverage: Secrets ✓ | SAST ✓ | SCA ✓ | Taint ✓ | CPG ✓ | IaC ✓ | DAST ✓ | Custom ✓
- OWASP coverage: A01:_, A02:_, A03:_, A04:_, A05:_, A06:_, A07:_, A08:_, A09:_, A10:_
- Top 3 risks: 1) ... 2) ... 3) ...
- Continuous scanning: <enabled / not-enabled> in CI/CD

## Findings - Critical
| Layer | OWASP | File:Line | Evidence | Fix |
|---|---|---|---|---|

## Findings - High / Medium / Low
...

## Layer Coverage Detail
- Secrets: <tools run, files scanned, findings>
- SAST: <tools run, rules used, findings>
- SCA: <ecosystems, advisories DB date, findings>
- Taint: <sources/sinks modeled, findings>
- CPG: <queries run, findings>
- IaC: <frameworks scanned, findings>
- DAST: <target, scan profile, findings>
- Custom: <rule files, findings>
```

---

## References

- [references/owasp-top-10-playbook.md](references/owasp-top-10-playbook.md) - per-OWASP-category ripgrep snippets and fixes
- [references/ci-workflow.md](references/ci-workflow.md) - complete reference `.github/workflows/security.yml`
- [references/semgrep-custom-rules.md](references/semgrep-custom-rules.md) - custom rule patterns for business-specific risks

## Related

- Rule: `310-security.mdc` - principles, OWASP Top 10, NHI Top 10
- Rule: `316-zero-trust.mdc` - Zero Trust principles (always-on)
- Rule: `160-github-actions.mdc` - secure CI patterns
- Rule: `440-docker.mdc`, `450-kubernetes.mdc` - workload hardening
- Skill: `security-testing` - shorter OWASP overview
- Skill: `zero-trust` - threat models, HITL gates, MCP hardening

## Attribution

Layer model and OWASP playbook adapted from a concrete tool-platform-analysis project audit. The eight-layer framing makes coverage explicit and gaps visible - if you can't tick all eight, you have unknown unknowns.
