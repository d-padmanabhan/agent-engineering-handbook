# Okta Resource-Server Token Validation

Use current Okta documentation:

- [Validate access tokens](https://developer.okta.com/docs/guides/validate-access-tokens/main/)
- [Custom authorization-server metadata](https://developer.okta.com/docs/api/openapi/okta-oauth/oauth/customas/getwellknownoauthconfigurationcustomas)
- [Signing-key rotation](https://developer.okta.com/docs/concepts/key-rotation/)

## Require the Correct Authorization Server

Use an Okta custom authorization server for access tokens consumed by an MCP
resource server. Its issuer normally includes `/oauth2/<authorizationServerId>`.

Do not locally validate access tokens from the Okta org authorization server,
whose issuer is the bare Okta domain. Okta documents those access tokens as
intended for Okta and subject to change. Reject that configuration for local
JWT validation rather than treating it as an MCP access-token issuer.

## Discover, Do Not Construct

Start from an exact allowlisted issuer. Retrieve its RFC 8414 authorization
server metadata and verify that the returned `issuer` exactly matches the
configured value.

RFC 8414 inserts the well-known component before an issuer path. For example:

```text
Issuer:
https://acme.okta.com/oauth2/mcp

RFC 8414 metadata:
https://acme.okta.com/.well-known/oauth-authorization-server/oauth2/mcp
```

Do not append `/.well-known/oauth-authorization-server` after the issuer path.
Use a standards-aware OAuth library where possible.

Use the returned `jwks_uri`. Do not assume that appending `/v1/keys` produces a
valid endpoint. Do not accept a token-controlled issuer, discovery URL, or JWKS
URL.

Discovery and key retrieval must:

- use HTTPS;
- reject embedded credentials and fragments;
- follow only bounded redirects that remain within the configured trust policy;
- block loopback, link-local, private, and metadata-service destinations unless
  an explicit private deployment requires and constrains them;
- resolve A and AAAA records and validate every selected address immediately
  before each connection, including after every redirect;
- pin each connection to a validated resolved address or use an HTTP client
  with equivalent DNS-rebinding protection;
- use connection and response-size limits; and
- avoid logging response bodies or tokens.

These controls prevent a configuration or discovery error from becoming SSRF
or uncontrolled egress.

## Validation Contract

Use a maintained library rather than implementing JOSE primitives. Configure
the library to:

- allow only the signing algorithms expected from the trusted issuer;
- select a key by `kid` from the discovered JWKS;
- verify the signature before consuming claims;
- require exact `iss`;
- require the configured audience in `aud`;
- require and validate `exp`;
- validate `nbf` when present;
- use a small, documented clock-skew allowance; and
- reject malformed, unsigned, encrypted, or unsupported token forms.

Ensure the credential is an access token, not an ID token, using a reliable
issuer-specific token profile or claim when available. Do not use an ID token
to authorize MCP resource access.

Validate scopes separately for each operation. Claims that are not part of the
documented authorization contract are untrusted application input even after
signature verification.

## Caching and Rotation

Keep discovery and JWKS clients process-scoped rather than constructing a new
client per request. Honor HTTP `Cache-Control` behavior from Okta.

When a validly formed token references an unknown `kid`:

1. refresh keys at most once within a bounded interval;
2. coordinate concurrent refreshes so one unknown key cannot create a fetch
   storm;
3. retry validation once; and
4. reject the token if the key remains unknown.

Never hardcode signing keys. Preserve cached valid keys during a short,
documented issuer outage only within their freshness policy; do not extend
token lifetime or skip signature verification.

## Configuration and Failure Behavior

Example public configuration:

```text
AUTH_MODE=oauth
MCP_RESOURCE_URL=https://mcp.acme.com/mcp/v1
OAUTH_ISSUER=https://acme.okta.com/oauth2/mcp
OAUTH_AUDIENCE=https://mcp.acme.com
OAUTH_REQUIRED_SCOPES=mcp:tools:read
```

These values identify trust relationships but are not credentials. Validate
them at startup.

If `AUTH_MODE=oauth`, missing or invalid OAuth configuration is a startup error.
Do not fall back to an API key, anonymous access, or a default issuer.

If a time-bounded API-key migration is unavoidable, require an explicit
`AUTH_MODE=legacy-api-key` plus an owner, expiry date, telemetry, rate limits,
and a rollback plan. Do not accept both modes implicitly on the same endpoint.
