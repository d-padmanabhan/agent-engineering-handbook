# OWASP Top 10 (2021) - Audit Playbook

Per-category ripgrep snippets, common findings, and fixes. Companion to `SKILL.md` Phase 3b.

For each finding capture: file:line, OWASP ID, severity, fix. The ripgrep snippets are starting points - adapt to the languages/frameworks present.

---

## A01 - Broken Access Control

### What to look for

- Authorization checks performed only on the client (UI hides actions but server doesn't enforce).
- Routes/handlers missing auth decorators or middleware.
- IDOR: object IDs taken from request and used directly in queries without ownership checks.
- CORS configured with wildcard origins for credentialed endpoints.
- Force browsing: admin/debug routes reachable without role checks.

### Ripgrep starters

```bash
rg -n '(?i)allow[_-]?origin.*\*'
rg -n '(?i)cors.*origin.*true|cors.*credentials.*true' -C2
rg -n '@(app|router)\.(get|post|put|delete|patch)\(' -A2          # check each route for auth decorator above
rg -n '(?i)is_admin\s*=\s*(true|1)|role\s*==\s*["\']admin'         # client-side trust of role
rg -n 'request\.(args|json|body)\[["\']?(id|user_id|account_id)' -C2
```

### Fix

Enforce auth + ownership on the server (`@require_auth`, RBAC checks, scope claims), restrict CORS to explicit origins, deny by default.

---

## A02 - Cryptographic Failures

### Ripgrep starters

```bash
rg -n '(?i)hashlib\.(md5|sha1)\(|MessageDigest\.getInstance\(["\']?(MD5|SHA-?1)'
rg -n 'verify\s*=\s*False|rejectUnauthorized\s*:\s*false|InsecureSkipVerify\s*:\s*true'
rg -n '(?i)AES.*ECB|Cipher\.ECB|MODE_ECB'
rg -n '(?i)(SSLv3|TLSv?1\.0|TLSv?1\.1|PROTOCOL_TLSv1\b)'
rg -n '(?i)(password|secret|token|ssn|credit_?card)\b.*log(ger|ging|\.info|\.debug)' -C1
```

### Fix

`argon2` / `bcrypt` for passwords, enable TLS verification, AES-GCM with random IVs, manage keys in KMS / Vault, redact sensitive fields before logging.

---

## A03 - Injection

### Ripgrep starters

```bash
rg -n '(?i)(execute|cursor\.execute|query)\s*\(\s*["\'].*(\{|\+|%s|\$\{)' -C1
rg -n 'f["\'](SELECT|INSERT|UPDATE|DELETE) ' -i
rg -n 'shell\s*=\s*True|os\.system\(|popen\(|subprocess\.(call|run|Popen).*shell' -C1
rg -n '\beval\(|\bexec\(|new Function\(' -C1
rg -n 'render_template_string\(' -C2
```

### Fix

Parameterized queries / ORM-bound parameters, allowlist + escape for shell args (`subprocess.run([...], shell=False)`), avoid `eval` / `exec`, use auto-escaping templates.

---

## A04 - Insecure Design

Less mechanical; review the design surface.

- Missing rate limits on `/login`, `/reset`, `/signup`, `/mfa`.
- No account lockout / CAPTCHA after repeated failures.
- Trust boundaries crossed without validation.
- Business-logic flaws: negative quantities, race on balance updates, replay-able tokens.
- No threat model / abuse cases.

### Fix

Add rate limits + lockouts, write abuse cases, enforce server-side invariants, idempotency keys for state-changing requests.

---

## A05 - Security Misconfiguration

### Ripgrep starters

```bash
rg -n '(?i)debug\s*[:=]\s*(true|1)|FLASK_DEBUG|RAILS_ENV.*development' -C1
rg -n '"Action"\s*:\s*"\*"|"Resource"\s*:\s*"\*"'
rg -n 'public-read|AllUsers|0\.0\.0\.0/0' -C1
rg -n '(?i)(content-security-policy|strict-transport-security|x-frame-options|x-content-type-options)' -l
rg -n '/actuator|/debug/pprof|swagger-ui|/admin' -C1
```

### Fix

Disable debug in prod, scope IAM to least privilege, set security headers via middleware, lock down management endpoints behind auth + network ACLs.

### AWS-specific misconfig: IMDSv1 enabled on EC2 instances

Critical-severity misconfig that produced the Capital One 2019 breach (~$190M penalty). Every EC2 instance, Launch Template, and Auto Scaling Group MUST require IMDSv2.

```bash
# Audit: find any EC2 instance allowing IMDSv1
aws ec2 describe-instances \
  --filters "Name=metadata-options.http-tokens,Values=optional" \
  --query "Reservations[].Instances[].[InstanceId,LaunchTime,Tags[?Key==\`Name\`].Value|[0]]" \
  --output table

# Remediate one instance
aws ec2 modify-instance-metadata-options \
  --instance-id i-0abcdef1234567890 \
  --http-tokens required \
  --http-endpoint enabled \
  --http-put-response-hop-limit 1   # 2 for container-on-EC2 / EKS nodes

# Enforce account-wide: AWS Config managed rule
aws configservice put-config-rule --config-rule '{
  "ConfigRuleName": "ec2-imdsv2-check",
  "Source": { "Owner": "AWS", "SourceIdentifier": "EC2_IMDSV2_CHECK" }
}'
```

For Terraform / CloudFormation specifics, account-wide SCP enforcement, and the hop-limit reasoning (1 for bare metal vs 2 for containers), see `rules/410-aws.mdc` "Non-negotiable: IMDSv2 only" and `skills/aws-iam/references/eks-pod-identity-abac-and-lattice.md` "IMDS hardening for the underlying nodes".

---

## A06 - Vulnerable & Outdated Components

Covered by the **SCA phase** in the main skill (Phase 2). Run `pip-audit` / `npm audit` / `govulncheck` / `osv-scanner` / `trivy fs` per ecosystem.

---

## A07 - Identification & Authentication Failures

### Ripgrep starters

```bash
rg -n 'jwt\.decode\(.*verify\s*=\s*False|algorithms\s*=\s*\[\s*["\']none' -C1
rg -n '(?i)set-cookie' -C2                                # inspect for HttpOnly/Secure/SameSite
rg -n 'localStorage\.(setItem|getItem)\(["\'](token|jwt|auth)' -C1
rg -n '(?i)session.*url|jsessionid='
```

### Fix

Strong password policy (NIST 800-63B), `HttpOnly; Secure; SameSite=Lax/Strict` cookies, validate JWT `alg` / `exp` / `iss` / `aud`, MFA, rotate refresh tokens.

---

## A08 - Software & Data Integrity Failures

### Ripgrep starters

```bash
rg -n 'pickle\.loads?\(|yaml\.load\([^,]*\)|ObjectInputStream\(' -C1
rg -n 'curl\s+[^|]*\|\s*(bash|sh)' -C1
rg -n 'pull_request_target' -g '*.yml' -g '*.yaml'
```

### Fix

`yaml.safe_load`, avoid pickle for untrusted data, sign artifacts (Sigstore / cosign), verify checksums, use `pull_request` (not `_target`) for untrusted code, pin GitHub Actions by SHA.

---

## A09 - Security Logging & Monitoring Failures

- Confirm auth / admin / finance endpoints log on success and failure with structured fields.
- Confirm logs ship to a central store (CloudWatch / Splunk / Datadog / ELK).
- Confirm at least one alert exists for repeated auth failures.

### Fix

Structured JSON logging with `user_id`, `request_id`, `ip`, `event`, `outcome`; ship to SIEM; alerts on auth-failure spikes and admin actions.

---

## A10 - Server-Side Request Forgery (SSRF)

### Ripgrep starters

```bash
rg -n 'requests\.(get|post|put|delete)\(\s*[^"\'\)]+\)|urllib\.request\.urlopen\(' -C1
rg -n 'fetch\(\s*(req\.|request\.|params\.|body\.)'
rg -n '169\.254\.169\.254|metadata\.google\.internal'
```

### Fix

Destination allowlist (scheme + host), block RFC1918 / link-local / cloud-metadata ranges, resolve DNS once and reuse the IP, dedicated egress proxy with policy.
