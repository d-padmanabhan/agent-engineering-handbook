# RFC 9728 and MCP Discovery

Use current primary sources before implementing protocol-version-specific
behavior:

- [MCP authorization specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/index)
- [MCP Streamable HTTP specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http)
- [RFC 9728: OAuth 2.0 Protected Resource Metadata](https://www.rfc-editor.org/rfc/rfc9728.html)
- [RFC 8414: OAuth 2.0 Authorization Server Metadata](https://www.rfc-editor.org/rfc/rfc8414.html)

MCP evolves independently of the OAuth RFCs. Record the MCP protocol revisions
supported by the server and verify the current stable specification before
changing transport behavior.

## Trust Boundaries

1. The MCP resource server publishes RFC 9728 metadata.
2. The authorization server publishes RFC 8414 or OIDC metadata and issues
   access tokens.
3. The MCP client discovers both parties and obtains a token.
4. The resource server validates the token and independently authorizes the
   requested MCP operation.

Do not collapse these roles by proxying authorization-server metadata from the
MCP server.

## Metadata URI Construction

RFC 9728 inserts `/.well-known/oauth-protected-resource` between the authority
and the complete path of the resource identifier.

```text
https://mcp.acme.com/mcp
https://mcp.acme.com/.well-known/oauth-protected-resource/mcp

https://mcp.acme.com/platform/mcp/v1
https://mcp.acme.com/.well-known/oauth-protected-resource/platform/mcp/v1
```

Do not truncate the path. The `resource` member in the response must equal the
canonical resource identifier exactly. It uses HTTPS and has no fragment.

MCP clients can also use a root fallback:

```text
https://mcp.acme.com/.well-known/oauth-protected-resource
```

When several MCP resources share a host, path-derived metadata avoids
ambiguity. A root document is a compatibility endpoint, not a reason to merge
distinct resource identifiers or authorization policies.

## Metadata Contract

Example:

```json
{
  "resource": "https://mcp.acme.com/mcp/v1",
  "authorization_servers": [
    "https://acme.okta.com/oauth2/mcp"
  ],
  "scopes_supported": [
    "mcp:tools:read",
    "mcp:tools:execute"
  ],
  "bearer_methods_supported": [
    "header"
  ]
}
```

Requirements:

- `resource` is required by RFC 9728.
- MCP requires `authorization_servers` with at least one issuer.
- `scopes_supported` is recommended by RFC 9728, but it need not enumerate
  dynamically selected scopes.
- `bearer_methods_supported` is optional. Remote MCP implementations should
  accept bearer tokens in the `Authorization` header, not query parameters.
- Metadata contains identifiers and capabilities only, never credentials.

Validate configured URLs at startup. Reject fragments, embedded credentials,
unsupported schemes, and unexpected origins.

## Authentication Challenge

For missing or invalid credentials, return a Bearer challenge:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer resource_metadata="https://mcp.acme.com/.well-known/oauth-protected-resource/mcp/v1", scope="mcp:tools:read"
```

The `resource_metadata` value should identify the exact document for the
requested resource. The challenged scope is authoritative for that request and
does not need to equal the full `scopes_supported` set.

Do not return `403` for absent or invalid credentials. Reserve `403` for an
authenticated principal whose token or policy lacks the required authority.

## Streamable HTTP Coverage

Modern remote MCP uses a Streamable HTTP endpoint. Apply authentication before
the MCP transport handler so every method supported by the negotiated protocol
revision is covered.

Validate the `Origin` header on every incoming Streamable HTTP connection when
present. Compare a normalized origin against an explicit allowlist or reject
browser-originated traffic when the deployment does not support it. Return
`403 Forbidden` for an invalid origin. Do not treat Host, CORS response headers,
or network location as substitutes for this DNS-rebinding control.

HTTP+SSE endpoints from the 2024-11-05 protocol are deprecated. Support them
only when an explicit compatibility requirement exists, and apply the same
authentication and authorization controls to every legacy endpoint. Do not
describe `/mcp/sse` and `/mcp/messages` as the default architecture.
