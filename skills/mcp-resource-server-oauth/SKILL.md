---
name: mcp-resource-server-oauth
description: Designs, implements, reviews, and diagnoses OAuth protection for remote MCP resource servers using Streamable HTTP, RFC 9728 protected-resource metadata, standards-based authorization-server discovery, fail-closed token validation, and scope enforcement. Use when securing an MCP server that the user can edit and deploy, especially with Okta.
---

# MCP Resource Server OAuth

Use this skill for the resource-server side of OAuth on a remote MCP server.
Keep the authorization server, MCP client, and downstream tool credentials as
separate trust boundaries.

## Outcomes

A completed implementation:

- protects every request method on the Streamable HTTP MCP endpoint;
- publishes RFC 9728 protected-resource metadata;
- identifies one or more trusted authorization servers;
- validates access tokens without trusting token claims before signature
  verification;
- enforces required scopes and per-tool authorization;
- validates the Streamable HTTP `Origin` boundary;
- fails closed when OAuth configuration is absent or incomplete; and
- returns standards-compatible `401` and `403` challenges.

## Scope

Use this skill when the user can edit and deploy the remote MCP server.

Do not use it for:

- local stdio servers;
- client-only configuration such as Cursor `mcp.json`;
- authorization-server or Okta tenant administration;
- XAA, ID-JAG, token exchange, or delegated-agent design;
- downstream credentials used by MCP tools; or
- generic MCP tool design unrelated to inbound OAuth.

For those concerns, use the Okta, IAM security advisor, workload identity, or
MCP development skill as appropriate.

## Public Sources and Portability

Ground protocol and vendor claims in publicly accessible primary sources:

- the current public MCP authorization and transport specifications;
- RFC 9728, RFC 8414, RFC 6750, and applicable OAuth security BCPs; and
- public Okta developer documentation for authorization servers, access-token
  validation, metadata, and key rotation.

Do not embed organization-specific names, support channels, internal hostnames,
tenant identifiers, deployment paths, or proprietary procedures in this skill.
Use `acme.com` examples. Treat deployment-specific information discovered in a
user repository as task context, not reusable handbook content.

## Workflow

### 1. Establish the deployed contract

Inspect the code and deployment configuration before asking the user for facts
already present. Determine:

- the canonical HTTPS MCP resource URI;
- the Streamable HTTP endpoint and supported MCP protocol versions;
- trusted authorization-server issuer identifiers;
- token audience and required scopes;
- allowed browser origins or a policy that rejects browser-originated traffic;
- whether legacy HTTP+SSE compatibility is explicitly required; and
- the ingress, proxy, and middleware path through which every MCP request flows.

Treat HTTP+SSE as legacy compatibility, not the default transport. Apply
authentication before transport dispatch so every supported method on the MCP
endpoint is protected. Validate `Origin` on every Streamable HTTP connection
when present and return `403` for an invalid origin.

### 2. Define fail-closed configuration

Use an explicit authentication mode. For OAuth mode, require all of:

- `MCP_RESOURCE_URL`
- `OAUTH_ISSUER`
- `OAUTH_AUDIENCE`
- `OAUTH_REQUIRED_SCOPES`

Issuer, audience, scopes, and resource URI are validated public configuration,
not secrets. Keep actual client credentials, private keys, tokens, and API keys
in an approved secret broker.

Reject startup when OAuth mode is selected and any required value is missing or
invalid. Never infer API-key fallback from missing OAuth configuration. A
temporary legacy mode must be explicit, separately authorized, observable, and
time-bounded.

### 3. Publish protected-resource metadata

Implement RFC 9728 metadata for the canonical resource URI. Preserve the
resource URI's complete path when constructing the path-derived well-known URI.
For example:

```text
Resource: https://mcp.acme.com/mcp/v1
Metadata: https://mcp.acme.com/.well-known/oauth-protected-resource/mcp/v1
```

The document must contain the exact `resource` value and at least one
`authorization_servers` entry as required by MCP. Publish
`scopes_supported` when the supported set can be represented usefully.
`bearer_methods_supported` is optional RFC 9728 metadata.

Prefer a `WWW-Authenticate` challenge with an explicit `resource_metadata` URL.
Support root metadata as a compatibility fallback when deployment topology
allows it. Do not proxy or recreate authorization-server metadata on the MCP
server.

See [RFC 9728 and MCP discovery](references/protected-resource-discovery.md).

### 4. Validate access tokens

For Okta local JWT validation, require a custom authorization server. Discover
its RFC 8414 metadata from the configured issuer and use the returned
`jwks_uri`; do not construct a JWKS URL by string concatenation.

Use a maintained JWT/OAuth library and validate:

- signature with an explicit algorithm allowlist;
- exact issuer;
- intended audience;
- expiration and not-before bounds with minimal clock skew;
- access-token type or profile when the issuer provides a reliable signal; and
- scopes required for the requested operation.

Cache authorization-server metadata and JWKS according to HTTP cache
directives. Bound refreshes on an unknown `kid` to prevent attacker-driven
fetch loops. Restrict discovery and JWKS egress to configured HTTPS issuers and
their validated metadata destinations. Resolve and validate A and AAAA results
for every connection and redirect to prevent DNS rebinding.

See [Okta resource-server validation](references/okta-token-validation.md) and
the IAM rule (`${HANDBOOK_ROOT}/rules/315-iam.mdc`).

### 5. Enforce authorization and failure semantics

Authentication does not authorize tool execution. After token validation:

1. enforce route or operation scopes;
2. map the verified principal to an internal caller identity;
3. authorize `(caller, tool, resource, action)` before side effects; and
4. emit a redacted audit decision with a correlation identifier.

Return:

- `400 Bad Request` with `error="invalid_request"` for a malformed
  authorization request as defined by RFC 6750;
- `401 Unauthorized` with a Bearer challenge for missing, expired, untrusted,
  or otherwise invalid tokens;
- `403 Forbidden` with `error="insufficient_scope"`, the required scope, and
  `resource_metadata` when valid credentials lack required token scope;
- a generic `403 Forbidden` without `insufficient_scope` when token scopes are
  sufficient but independent per-tool policy denies access; and
- no token, raw claim set, or sensitive credential data in logs or errors.

Use the Zero Trust MCP hardening reference
(`${HANDBOOK_ROOT}/skills/zero-trust/references/mcp-hardening.md`) for per-tool
authorization, HITL, input validation, and auditing.

### 6. Verify proportionally

Choose checks from
[authorization and verification](references/authorization-and-verification.md)
based on the task:

- explanation or review: no live probes by default;
- implementation: focused metadata, authentication, scope, and configuration
  tests;
- diagnosis: only the probes needed to test the stated failure hypothesis; and
- non-local environments: identify the target and obtain applicable
  authorization before probing.

Never request, print, persist, or replay a live access token in agent context.

## Handoff

Report:

- the protected resource URI and metadata locations;
- trusted issuer, audience, and scope contract without credentials;
- routes and methods covered by authentication;
- focused evidence produced;
- legacy compatibility or migration mode still enabled; and
- unresolved authorization-server, client-registration, or deployment work
  owned by another team.
