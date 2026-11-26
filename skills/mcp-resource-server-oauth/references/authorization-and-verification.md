# Authorization and Proportional Verification

Token validity establishes a verified caller and token contract. It does not
grant every MCP capability.

Public standards:

- [RFC 6750: OAuth 2.0 Bearer Token Usage](https://www.rfc-editor.org/rfc/rfc6750.html)
- [RFC 9700: Best Current Practice for OAuth 2.0 Security](https://www.rfc-editor.org/rfc/rfc9700.html)

## Scope and Tool Authorization

Define required scopes by operation, not only by server:

```text
tools/list              -> mcp:tools:read
tools/call:get_report   -> mcp:reports:read
tools/call:start_job    -> mcp:jobs:execute
```

After JWT validation:

1. parse the issuer's documented scope claim;
2. require every scope needed by the requested operation;
3. map the verified subject and relevant claims to an internal principal;
4. evaluate per-tool policy for `(principal, tool, resource, action)`; and
5. execute only after both scope and policy checks allow the operation.

Do not infer authority from token possession, network location, email domain,
or a client-supplied tool name.

For a valid token missing required scopes, return:

```http
HTTP/1.1 403 Forbidden
WWW-Authenticate: Bearer error="insufficient_scope", scope="mcp:jobs:execute", resource_metadata="https://mcp.acme.com/.well-known/oauth-protected-resource/mcp/v1"
```

Use `401` for invalid credentials. Avoid revealing whether a sensitive tool or
resource exists when the caller is unauthorized. When scopes are sufficient
but independent per-tool policy denies access, return a generic `403` without
`insufficient_scope`; requesting broader scopes would not resolve that denial.

A malformed RFC 6750 authorization request can return `400` with
`error="invalid_request"`. Do not classify an invalid token as a malformed
request merely to avoid a Bearer `401` challenge.

For destructive tools, apply the independent HITL and capability controls in
`${HANDBOOK_ROOT}/skills/zero-trust/references/mcp-hardening.md`.

## Focused Implementation Tests

When authentication or discovery code changes, cover the changed boundary:

- exact path-derived and root metadata routes;
- exact `resource` and trusted `authorization_servers`;
- valid and invalid Streamable HTTP `Origin` behavior;
- unauthenticated MCP request returns `401` and a usable challenge;
- valid access token with expected issuer, audience, time bounds, and scope;
- invalid signature, issuer, audience, expiry, not-before, algorithm, or `kid`;
- ID token presented as an access token;
- valid token missing scope returns `403 insufficient_scope`;
- authenticated caller denied by per-tool policy;
- incomplete OAuth configuration prevents startup;
- OAuth configuration never falls back implicitly to API-key or anonymous mode;
- discovery/JWKS timeout, oversized response, redirect, and refresh-storm
  behavior; and
- no token or sensitive claims in logs, metrics, traces, or errors.

Use synthetic tokens and local test keys. Never paste a live token into source,
fixtures, command history, agent context, or test output.

## Verification by Task Type

### Explanation or Review

Read the relevant code and configuration. Do not run live probes by default.
Report assumptions and the focused checks that would be required before
release.

### Implementation

Run the smallest deterministic checks that exercise the changed boundary:

1. unit tests for metadata, configuration, and claim validation;
2. focused integration tests for middleware and response semantics;
3. repository lint or type checks for changed files; and
4. negative tests for downgrade and authorization failures.

Do not run unrelated full-repository test suites merely because they exist.
Run broader checks only when the change affects shared infrastructure, the
repository requires them as a release gate, or focused evidence reveals a
cross-cutting risk.

### Diagnosis

State a failure hypothesis first. Run only the probe needed to distinguish the
likely causes. Prefer metadata and response headers over credential-bearing
requests.

If a token is required, ask the user to run an approved local diagnostic that
prints only sanitized claim names and validation outcomes. Do not request the
token value.

### Non-local Environments

Before probing, identify:

- exact environment and hostname;
- whether the operation is read-only;
- data classification and logging implications;
- expected request volume; and
- authorization required by the environment owner.

Use bounded timeouts and response-size limits. Do not probe production merely
to complete a generic checklist.

## Release Evidence

Record only:

- target revision or artifact;
- configured resource, issuer, audience, and required scope identifiers;
- test names and pass/fail results;
- sanitized failure categories;
- remaining legacy mode and expiry; and
- known limitations.

Never record access tokens, authorization headers, private keys, client
secrets, raw JWKS cache contents, or sensitive claim values.
