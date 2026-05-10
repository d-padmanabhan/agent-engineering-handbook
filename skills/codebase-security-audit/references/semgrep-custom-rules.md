# Semgrep Custom Rules - Patterns

Custom Semgrep rules in `.semgrep/<rule>.yaml` are picked up by `semgrep --config .semgrep/`. Custom rules consistently produce the highest signal-to-noise findings because they encode your house conventions and internal frameworks.

---

## Internal auth decorator missing

Every route handler in `routes/` must have `@require_auth(scope=...)` or `@public_endpoint`.

```yaml
# .semgrep/internal-auth-required.yaml
rules:
  - id: internal-auth-required
    message: Route handler is missing @require_auth or @public_endpoint
    severity: ERROR
    languages: [python]
    paths:
      include: ["routes/**"]
    patterns:
      - pattern: |
          @app.$METHOD(...)
          def $FN(...):
            ...
      - pattern-not-inside: |
          @require_auth(...)
          @app.$METHOD(...)
          def $FN(...):
            ...
      - pattern-not-inside: |
          @public_endpoint
          @app.$METHOD(...)
          def $FN(...):
            ...
```

---

## PII fields without redaction

Any logger call that includes a known PII field name must wrap it in `redact()`.

```yaml
# .semgrep/pii-redaction-required.yaml
rules:
  - id: pii-redaction-required
    message: PII field logged without redact()
    severity: ERROR
    languages: [python]
    pattern-either:
      - pattern: logger.$LEVEL(..., email=$EMAIL, ...)
      - pattern: logger.$LEVEL(..., ssn=$SSN, ...)
      - pattern: logger.$LEVEL(..., phone=$PHONE, ...)
      - pattern: logger.$LEVEL(..., card_number=$CC, ...)
    pattern-not: logger.$LEVEL(..., $FIELD=redact($VAL), ...)
```

---

## Internal SDK misuse

The internal HTTP client `mck_http.get()` must always pass `timeout=` and `verify=True`.

```yaml
# .semgrep/internal-http-client-misuse.yaml
rules:
  - id: internal-http-missing-timeout
    message: mck_http.$METHOD called without timeout
    severity: ERROR
    languages: [python]
    patterns:
      - pattern: mck_http.$METHOD(...)
      - pattern-not: mck_http.$METHOD(..., timeout=$T, ...)

  - id: internal-http-verify-disabled
    message: mck_http.$METHOD called with verify=False
    severity: ERROR
    languages: [python]
    pattern: mck_http.$METHOD(..., verify=False, ...)
```

---

## Forbidden imports

Block `import requests` in modules that should use the internal client; block `import pickle` in services that accept external input.

```yaml
# .semgrep/forbidden-imports.yaml
rules:
  - id: prefer-internal-http-client
    message: Use mck_http instead of requests
    severity: ERROR
    languages: [python]
    paths:
      include: ["services/**"]
    pattern-either:
      - pattern: import requests
      - pattern: from requests import ...

  - id: pickle-in-public-service
    message: pickle is forbidden in services that accept external input
    severity: ERROR
    languages: [python]
    paths:
      include: ["services/public/**"]
    pattern-either:
      - pattern: import pickle
      - pattern: from pickle import ...
```

---

## Tenant-scope check (multi-tenant DB queries)

Every DB query in a multi-tenant service must include a `tenant_id` filter.

```yaml
# .semgrep/tenant-scope-required.yaml
rules:
  - id: tenant-scope-required
    message: Query missing tenant_id filter in multi-tenant service
    severity: ERROR
    languages: [python]
    paths:
      include: ["services/multi_tenant/**"]
    patterns:
      - pattern-either:
          - pattern: $MODEL.query.filter_by(...)
          - pattern: db.session.query($MODEL).filter(...)
      - pattern-not-inside: |
          $MODEL.query.filter_by(..., tenant_id=$T, ...)
      - pattern-not-inside: |
          db.session.query($MODEL).filter(..., $MODEL.tenant_id == $T, ...)
```

---

## Authoring tips

- Start with one canonical violation in your repo; build the rule against it; expand `pattern-either` as you find variants.
- Always include `paths.include` to scope the rule - a global custom rule generates noise.
- Use `severity: ERROR` for rules you want CI to block on; `WARNING` for advisories.
- Add a `metadata.fix:` block when the auto-fix is unambiguous.
- Group related rules into one file (e.g., `internal-http-client.yaml` covers both timeout and verify).
- Run `semgrep --config .semgrep/ --test` against fixture files in `tests/semgrep-fixtures/` to keep rules honest.
- Review rules quarterly - frameworks evolve, paths change, conventions shift.
