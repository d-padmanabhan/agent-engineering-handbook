# Layer Commands

Command starters for each scanning layer in the [codebase security audit skill](../SKILL.md). Adapt them to the languages and frameworks present.

Before running anything:

- Apply the execution boundary in the skill. Commands marked **sandbox** run repository-controlled code, configuration, or plugins and must run only inside an OS-enforced sandbox.
- Run scanners with auditor-owned configuration where the tool supports it, and record any repository suppression files the scan honored.
- For confidential targets, disable tool telemetry and avoid registry or advisory lookups that send repository metadata to third parties without authorization.

```bash
GIT_REPO_ROOT="$(git rev-parse --show-toplevel)"
AUDIT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/security-audit.XXXXXX")"

# Optional in-repository location, only when Git already ignores it:
# candidate="$GIT_REPO_ROOT/.agent/reports/security-audit/$(date +%F)"
# git -C "$GIT_REPO_ROOT" check-ignore -q "$candidate" && mkdir -p "$candidate" && AUDIT_DIR="$candidate"
```

When `AUDIT_DIR` is inside the repository, exclude it from every scanner.

## Layer 1 - Secrets

Never print or persist secret values. Use redacting modes and record commit, path, rule, and a fingerprint instead of the value.

### Current Tree (Regex)

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
    # so this file does not trip the detect-private-key pre-commit hook.
    r'<BEGIN_MARKER>(RSA |EC |DSA )?<KEY_MARKER>',
    r'jdbc:[\w]+://[^\s"]+',                     # JDBC connection strings
    r'mongodb(\+srv)?://[^\s"]+',                # MongoDB URIs
    r'https?://[\w:]+@',                         # URLs with credentials
]
```

List matching locations without printing values:

```bash
rg --files-with-matches '<pattern>' --glob '!node_modules' --glob '!.git' --glob '!*.min.js'
```

### Entropy and Known-Format Scanners

```bash
set -o pipefail

# gitleaks v8.19+: `dir` scans the working tree, `git` scans history.
gitleaks dir --redact --config <auditor-gitleaks.toml> --report-format json --report-path "$AUDIT_DIR/gitleaks.json" .

# TruffleHog JSON includes raw values; strip them before writing.
trufflehog filesystem --json --no-update --no-verification . \
  | jq -c 'del(.Raw, .RawV2)' > "$AUDIT_DIR/trufflehog.json"

detect-secrets scan --all-files > "$AUDIT_DIR/secrets.baseline"   # stores hashes, not values
```

TruffleHog verifies each detected credential with its issuing provider unless `--no-verification` is set. Remove that flag only when the user explicitly authorizes live verification for this repository.

### Git History

```bash
gitleaks git --redact --config <auditor-gitleaks.toml> --log-opts="--all" \
  --report-format json --report-path "$AUDIT_DIR/gitleaks-history.json" .

trufflehog git file://. --no-verification --json \
  | jq -c 'del(.Raw, .RawV2)' > "$AUDIT_DIR/trufflehog-history.json"

# Locate commits and paths without printing file contents.
git log --all --diff-filter=A --name-only --format='%H %ad %an' -- '*.env' '*.pem' '*.key' 'credentials*' 'config/secrets*'
```

For each finding record the commit, date, author, path, rule, fingerprint, whether it was later removed, and whether live verification was authorized and performed. Exclude test fixtures, documentation examples, and placeholders such as `your-key-here`.

## Layer 2 - Software Composition Analysis

Prefer lockfile and manifest scanners. Resolving unpinned requirements or running build tools executes repository logic.

```bash
# Python: audit declared requirements, not the current environment
pip-audit --strict --no-deps --disable-pip -r requirements.txt   # pinned requirements
pip-audit --strict -r requirements.txt                            # sandbox: resolves and installs packages

# Node
npm audit --omit=dev
yarn audit --groups dependencies          # Yarn Classic only; sandbox when the repository sets a yarn path

# Go
govulncheck ./...

# Java (sandbox: runs Maven or Gradle build logic)
mvn org.owasp:dependency-check-maven:check
gradle dependencyCheckAnalyze

# Ruby
bundle audit check --update

# Rust
cargo audit

# .NET (sandbox: evaluates MSBuild and requires a restore)
dotnet list package --vulnerable --include-transitive

# Multi-ecosystem
osv-scanner --recursive .
grype dir:.
trivy fs --scanners vuln,license,secret .
trivy image <image:tag>
```

License risk:

```bash
trivy fs --scanners license .
# or per ecosystem: pip-licenses, license-checker (Node), go-licenses
```

## Layer 3 - SAST

Quick code-smell pass:

| Issue | What to look for |
|---|---|
| Hardcoded URLs | Base URLs and API endpoints that vary by environment |
| Hardcoded IDs | Cloud account, organization, or project IDs |
| Debug flags | `DEBUG = True`, verbose logging in production code |
| Insecure defaults | `verify=False`, `allow_all_origins`, disabled authentication |
| Missing input validation | User input passed directly to queries or commands |
| Overly broad exceptions | `except Exception: pass` hiding errors |

Language tools:

```bash
bandit -r . -ll -ii -f json -o "$AUDIT_DIR/bandit.json"                     # Python
gosec -fmt=json -out="$AUDIT_DIR/gosec.json" ./...                          # Go
eslint --ext .js,.jsx,.ts,.tsx --plugin security \
  --rule 'security/detect-eval-with-expression:error' .                     # JavaScript / TypeScript (sandbox: loads repository config and plugins)
spotbugs -textui -include findsecbugs-include.xml \
  -output "$AUDIT_DIR/spotbugs.xml" target/classes                          # Java (needs compiled classes; sandbox the build)
brakeman -o "$AUDIT_DIR/brakeman.json" --format json                        # Ruby on Rails
flawfinder --html . > "$AUDIT_DIR/flawfinder.html"                          # C / C++
cppcheck --enable=warning,style,performance,portability .                   # C / C++ alternative
psalm --taint-analysis                                                      # PHP (sandbox: loads Composer autoloaders and plugins)
```

Multi-language Semgrep:

```bash
semgrep --metrics=off \
        --config=p/security-audit \
        --config=p/owasp-top-ten \
        --config=p/secrets \
        --config=p/cwe-top-25 \
        --json --output="$AUDIT_DIR/semgrep.json" .
```

Add language packs as needed: `p/python`, `p/javascript`, `p/typescript`, `p/golang`, `p/java`, `p/ruby`, `p/csharp`, `p/terraform`, `p/dockerfile`, `p/kubernetes`.

## Layer 4 - Data Flow and Taint

Semgrep taint mode:

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

```bash
semgrep --metrics=off --config .semgrep/ .
```

CodeQL (sandbox for compiled languages, where database creation runs the build):

```bash
codeql database create "$AUDIT_DIR/codeql-db" --language=python --source-root=.
codeql database analyze "$AUDIT_DIR/codeql-db" codeql/python-queries:Security \
  --format=sarifv2.1.0 --output="$AUDIT_DIR/codeql.sarif"
```

Use built-in queries such as `python-queries:Security/CWE-089/SqlInjection.ql`, or write a custom data-flow query for an application-specific source and sink pair.

Pysa (Python; sandbox, because Pyre reads repository configuration and `pyre init` writes into the target):

```bash
pyre init && pyre analyze --no-verify --save-results-to "$AUDIT_DIR/pysa-results"
```

## Layer 5 - Semantic and Code Property Graph

```bash
joern-parse . --output "$AUDIT_DIR/cpg.bin"
joern --script audit.sc
```

Typical queries: every path from an HTTP entry point to an unauthenticated database write, or functions that read `is_admin` without first calling `verify_session`.

## Layer 6 - Infrastructure as Code

```bash
checkov --directory . --framework all --output json --output-file-path "$AUDIT_DIR"   # sandbox if the repository has .checkov.yaml, .checkov.yml, or external checks
tfsec . --format json --out "$AUDIT_DIR/tfsec.json"
terrascan scan -d . -o json > "$AUDIT_DIR/terrascan.json"
kube-linter lint .
kubesec scan deployment.yaml
kics scan -p . -o "$AUDIT_DIR" --report-formats json
hadolint Dockerfile
trivy config .
```

Common IaC leads (confirm reachability and impact before reporting them as vulnerabilities):

- Storage buckets with public ACLs or policies.
- Security groups allowing `0.0.0.0/0` on administrative or database ports.
- IAM policies with `Action: "*"` or `Resource: "*"`.
- Kubernetes workloads running as root, privileged, or with host namespaces; missing `NetworkPolicy`.
- Dockerfiles using `:latest`, running as root, or passing secrets through `ARG`.
- Unencrypted storage or databases.
- Secrets in plain environment values instead of secret references.

## Layer 7 - Custom Rules

Author rules from confirmed root causes. See Phase 9 in the skill and the [Semgrep custom rules](semgrep-custom-rules.md) reference.

## Layer 8 - DAST

Run only after the authorization gate in the skill is satisfied: written authorization naming the target, endpoints, window, and techniques; an owned non-production target; dummy data; and rate limits.

Passive tier:

```bash
docker run --rm -v "$AUDIT_DIR":/zap/wrk/:rw -t ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t https://staging.acme.com -J zap-baseline.json
```

Active tier, limited to the endpoints and window named in the authorization:

```bash
# Template-driven checks against an explicit list of authorized URLs
nuclei -l authorized-urls.txt -severity critical,high,medium \
  -rate-limit 10 -jsonl -o "$AUDIT_DIR/nuclei.jsonl"

# Active scan scoped to an authorized ZAP context, time-boxed and throttled.
# The context file must be in "$AUDIT_DIR"; without it ZAP scans the whole host unscoped.
test -f "$AUDIT_DIR/authorized.context" && \
docker run --rm -v "$AUDIT_DIR":/zap/wrk/:rw -t ghcr.io/zaproxy/zaproxy:stable \
  zap-full-scan.py -t https://staging.acme.com -n authorized.context -m 10 \
  -z "-config scanner.threadPerHost=1 -config scanner.delayInMs=500 -config scanner.maxScanDurationInMins=30" \
  -J zap-full.json

# Targeted SQL injection confirmation at default risk and level
sqlmap -u "https://staging.acme.com/search?q=1" --batch --level=1 --risk=1 --delay=1 --threads=1
```

Verify the ZAP option keys against the pinned ZAP version. Higher `sqlmap` risk levels add heavier and data-modifying payloads; use them only when the authorization explicitly allows it and the target data is disposable.

## Repository Hygiene and Remediation Templates

Use these only when the user asked for remediation artifacts.

`.gitignore` entries to verify:

```gitignore
# Secrets and local config
.env
.env.*
*.pem
*.key
credentials.json
secrets.yaml

# Agent and scanner output
.agent/
gitleaks*.json
trufflehog*.json
semgrep.json
codeql.sarif
```

`.env.template`, committed without values:

```env
# Required - service API token, supplied by the secret manager
SERVICE_API_TOKEN=

# Optional - override default batch size (default: 50)
BATCH_SIZE=50
```

Load real values from an approved secret manager or a short-lived credential broker, not from a committed script.
