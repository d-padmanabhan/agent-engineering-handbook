---
name: networking-transport
description: Networking and transport-layer architecture for production services. TCP keepalive, head-of-line blocking, TTFB budget, HTTP/1.1 vs HTTP/2 vs HTTP/3, when to choose gRPC/Protobuf over REST/JSON, connection pooling, long-lived connections (websockets / SSE / gRPC streaming), and CDN-to-origin patterns. Use when designing service-to-service APIs, debugging tail latency, choosing a wire protocol, configuring load balancer idle timeouts, or evaluating HTTP/3 / QUIC for mobile / cross-region workloads.
---

# Networking & Transport - Architecture Patterns

The transport-and-wire-format layer underneath your API design. `320-api-design.mdc` covers the API surface (verbs, status codes, versioning). This skill covers everything below it: TCP, HTTP/n, QUIC, serialization, connection lifecycle, head-of-line, TTFB budget.

Get this layer wrong and your P99 latency, mobile UX, edge cold-start cost, and east-west microservice throughput all suffer in ways that profiling your application code can't fix.

## When to invoke

- Designing or reviewing a service-to-service API (REST vs gRPC choice)
- Debugging tail latency / TTFB spikes / "fast in isolation, slow in production"
- Configuring load balancer idle timeouts (NLB, ALB, API Gateway, Cloudflare)
- Designing long-lived connections (websockets, SSE, gRPC streaming)
- Evaluating HTTP/3 / QUIC for mobile / cross-region / lossy-network workloads
- Choosing a wire format (JSON vs Protobuf vs MessagePack vs Avro)
- Reviewing a `.proto` file or a protobuf schema change

## Five golden rules

1. **TCP keepalive is mandatory on long-lived clients.** Linux defaults (`tcp_keepalive_time = 7200s` = 2 hours) are wrong for cloud. Set explicit per-language values.
2. **Reuse HTTP clients.** A fresh client per request defeats keepalive and burns ~50-150ms on TCP+TLS handshake. The single most common production performance bug.
3. **Choose the wire by callers, not by hype.** External / browser / human-debugged -> REST/JSON. Internal east-west / polyglot / streaming -> gRPC/Protobuf. Don't gRPC your public API just because it's faster.
4. **HTTP/2 multiplexes streams; HTTP/3 multiplexes connections.** HTTP/2 still has TCP-level head-of-line. HTTP/3 fixes it. Matters when packet loss is non-zero (mobile, satellite, cross-region).
5. **Idle timeouts kill connections silently.** AWS NLB drops at 350s, ALB at 60s, API Gateway REST at 29s. Set keepalive < min(idle timeout) or watch your "random" disconnects.

---

## 1. Mental model: four layers, four latency budgets

```
+----------------------------------------+
|  L7 wire format    JSON / Protobuf     |  Serialization CPU + size on wire
+----------------------------------------+
|  L7 protocol       HTTP/1.1 /2 /3      |  Multiplexing + HoL behavior
+----------------------------------------+
|  L6 transport sec  TLS 1.2 /1.3        |  Handshake RTTs (1-RTT, 0-RTT, session resume)
+----------------------------------------+
|  L4 transport      TCP / QUIC (UDP)    |  Handshake, congestion control, HoL
+----------------------------------------+
|  L3 IP             routing / DNS       |  DNS lookup, geo distance, MTU
+----------------------------------------+
```

Latency tuning at each layer:

| Layer | Typical contribution to TTFB | Tuning levers |
|---|---|---|
| DNS | 0-50ms (cold), 0-1ms (cached) | TTL, edge DNS, prefetch |
| TCP handshake | 1 RTT (~5-150ms by geo) | Connection reuse (keepalive), HTTP/3 (0 RTT) |
| TLS handshake | 1-2 RTT (TLS 1.3 = 1; TLS 1.2 = 2) | TLS 1.3, session resumption, 0-RTT (with replay risk) |
| Request processing | App-dependent | Profile; out of scope here |
| First byte | Streaming vs buffering | Stream early; don't await full result before responding |

---

## 2. TCP keepalive

### What it is

OS-level periodic probes on idle TCP connections to detect dead peers. Without keepalive, a connection in a half-open state (peer died, NAT timed out, LB recycled) appears alive until the next read/write attempt fails.

### Why defaults are wrong

| OS / setting | Default | Problem in cloud |
|---|---|---|
| Linux `tcp_keepalive_time` | 7200s (2 hours) | LB drops connection at 60-350s; client believes still alive; first send after 6 minutes fails |
| Linux `tcp_keepalive_intvl` | 75s | OK |
| Linux `tcp_keepalive_probes` | 9 | Total death-detection time = 2h + 9*75s = ~2.2h |
| macOS `net.inet.tcp.keepidle` | 7200000ms | Same |
| Windows `KeepAliveTime` | 7200000ms | Same |

### What to set per environment

| Environment | Suggested idle | Why |
|---|---|---|
| AWS NLB-fronted (350s idle) | 60-120s | Probe twice before LB cuts |
| AWS ALB-fronted (60s idle, configurable) | 30s | Probe before LB cuts |
| API Gateway REST (29s idle, fixed) | Don't keepalive; reconnect per request | Pool inside a Lambda invocation only |
| Cross-region (RTT 100-200ms) | 30-60s | Detect partition fast |
| Inside k8s cluster | 30-60s | Pod churn, kube-proxy reset |

### Per-language settings

```go
// Go: customize the Transport's DialContext
tr := &http.Transport{
    DialContext: (&net.Dialer{
        Timeout:   5 * time.Second,
        KeepAlive: 30 * time.Second,    // probe interval
    }).DialContext,
    IdleConnTimeout:       90 * time.Second,
    MaxIdleConnsPerHost:   100,
    DisableKeepAlives:     false,
}
client := &http.Client{Transport: tr}
```

```python
# Python (requests/httpx) - OS-level keepalive only; tune via Session
import requests
from requests.adapters import HTTPAdapter

session = requests.Session()
session.mount('https://', HTTPAdapter(pool_connections=20, pool_maxsize=100))
# OS-level: sysctl net.ipv4.tcp_keepalive_time=60 (container or host)
```

```javascript
// Node: enable keepalive on the Agent (NOT default in older Node versions)
const https = require('https');
const agent = new https.Agent({
  keepAlive: true,
  keepAliveMsecs: 30_000,           // probe interval
  maxSockets: 100,
  timeout: 30_000,
});
```

### Anti-patterns

- Default OS keepalive in cloud (2-hour idle). Connection looks alive; first send fails.
- Creating a new `http.Client` / `requests` object per request. No pooled connection, no keepalive, ~50-150ms handshake tax per call.
- Setting keepalive longer than the load balancer's idle timeout. Backwards; LB still wins.

---

## 3. TCP head-of-line blocking

### The problem at three layers

| Layer | What blocks | Fixed by |
|---|---|---|
| **HTTP/1.1** | Whole connection blocks until current request completes (serial requests per connection) | Concurrent connections (browsers cap at ~6/host); HTTP/2 |
| **HTTP/2 over TCP** | Streams are multiplexed in software, but TCP packet loss blocks **all** streams on that connection until retransmit | HTTP/3 over QUIC |
| **TCP** | Lost packet stalls every higher-layer message on the connection | QUIC (per-stream loss handling at transport) |

### When this matters

- **Mobile networks** (packet loss 1-5%): HTTP/2 single connection performs worse than HTTP/1.1 with parallel connections because one lost packet stalls everything.
- **Cross-region** (especially via lossy intermediate networks): same.
- **High-fan-out backends**: one slow upstream response on an HTTP/2 connection delays unrelated responses sharing the connection.

### When it doesn't matter

- LAN / data-center east-west with <0.001% loss: HTTP/2 multiplexing wins; HoL is theoretical.
- HTTP/1.1 with one request at a time (most internal microservices today): never see it.

---

## 4. TTFB (time to first byte) budget

| Component | Cost (typical) | What to do about it |
|---|---|---|
| DNS lookup | 0-50ms cold, 0-1ms cached | High TTL, edge DNS, DNS prefetch in clients |
| TCP handshake | 1 RTT (5-150ms by geo) | Reuse connections (keepalive); HTTP/3 0-RTT |
| TLS handshake | 1 RTT (TLS 1.3) or 2 RTT (TLS 1.2) | TLS 1.3 mandatory; session resumption / tickets |
| Server processing | App-dependent | Profile; cache; precompute |
| First byte to client | 1 RTT to client | Stream the response; don't buffer-then-send |

**The streaming insight**: if your handler takes 800ms to compute a 4KB response, TTFB is 800ms + 1 RTT. If you stream incrementally, TTFB drops to whatever the first chunk takes (often <100ms). Big TTFB win, no algorithmic change required.

---

## 5. HTTP/1.1 vs HTTP/2 vs HTTP/3

| Aspect | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| Transport | TCP | TCP | QUIC over UDP |
| Connection per host | Many (browsers ~6) | One (multiplexed) | One (multiplexed) |
| Request concurrency on one connection | None (serial) | Many streams | Many streams |
| TCP HoL | N/A (serial) | Yes (packet loss blocks all streams) | No (per-stream) |
| Handshake RTT | 1 (TCP) + 1-2 (TLS) | 1 + 1-2 | 0-1 (0-RTT with replay caveat) |
| Header compression | None | HPACK | QPACK |
| Server push | None | Yes (deprecated 2022) | No (dropped) |
| Browser/server support | Universal | Universal | Strong but middlebox issues |
| When it wins | Simple, debuggable | Internal east-west, LAN | Mobile, cross-region, lossy networks |

### HTTP/3 prerequisites

- **UDP port 443 must be reachable end-to-end.** Some corporate proxies, old firewalls, and certain ISP middleboxes drop or rate-limit UDP/443.
- **Server advertises via `alt-svc` header** in an HTTP/2 or 1.1 response: `alt-svc: h3=":443"; ma=86400`.
- **Client must support and choose to attempt H3.** Browsers do this transparently; SDKs / curl need explicit flags.
- **TLS 1.3 mandatory** (HTTP/3 only runs over TLS 1.3+).

### When HTTP/3 is the right choice

- Public-facing edge traffic for mobile users
- Cross-region / cross-cloud / high-RTT paths
- Edge POPs to mobile clients (Cloudflare, Fastly, CloudFront all support)
- Anywhere packet loss meaningfully affects current HTTP/2 P95/P99

### When HTTP/2 is still right

- Internal east-west (low loss, low RTT, no UDP-path concerns)
- gRPC (which requires HTTP/2)
- Anywhere your egress path doesn't reliably pass UDP/443

---

## 6. REST/JSON vs gRPC/Protobuf vs GraphQL vs Connect

### Decision matrix

| Use case | Choice | Why |
|---|---|---|
| External public API | REST + JSON | Browser-debuggable, curl-friendly, broadest tooling, OpenAPI spec mature |
| Internal east-west microservices (polyglot) | **gRPC + Protobuf** | Schema-first, code generation, streaming, ~5-10x smaller wire, ~3-5x faster serialization, native HTTP/2 |
| Browser <-> internal services | REST or gRPC-Web (with proxy) or Connect | gRPC doesn't run in browsers natively; gRPC-Web requires an Envoy/Nginx proxy that translates |
| Client-driven shape (graph fetches) | GraphQL | Single endpoint, client picks fields, batches |
| Want gRPC's API style without HTTP/2 mandate | **Connect** (or Twirp) | Protobuf schemas, HTTP/1.1-friendly, browser-callable directly |
| Mobile <-> backend | REST + Protobuf (or Connect) | gRPC works on mobile but battery / network resilience varies |
| Event-driven / pub-sub | Kafka / NATS / SQS with Protobuf or Avro schemas | Not a request/response problem; see `483-kafka.mdc` |

See [`references/grpc-vs-rest-decision.md`](references/grpc-vs-rest-decision.md) for the long version with worked examples.

### gRPC's real wins

- **Schema-first contract.** `.proto` is the single source of truth; client + server generated from it. No "is this field optional?" debates.
- **Streaming.** Server, client, and bidirectional streams as first-class concepts. Long-lived RPC over a single connection.
- **Polyglot code-gen.** Same `.proto` -> Go, Python, Java, TS, Swift, Kotlin, Ruby, C++, Rust. Type-safe in each.
- **Smaller wire, faster parse.** Protobuf vs JSON: ~3-10x smaller, ~3-5x faster to (de)serialize.
- **HTTP/2 native.** Multiplexed streams, no per-request connection.

### gRPC's real losses

- **Browsers don't speak gRPC.** Need gRPC-Web + Envoy translation, or use Connect.
- **Debuggable from a CLI?** Need `grpcurl` (not curl) and a reflection server or the `.proto` file.
- **Load balancing.** gRPC's persistent HTTP/2 connection breaks naive L4 load balancers; need L7 (Envoy, Linkerd, AWS Application LB with gRPC support).
- **No browser-friendly caching.** REST `Cache-Control` and CDN integration is a solved problem; gRPC isn't.
- **Tail-latency observability.** Per-call metrics need extra instrumentation; less out-of-box than HTTP middleware.

### Connect (and Twirp): the middle ground

- Protobuf schemas + code-gen (like gRPC)
- HTTP/1.1-friendly (like REST)
- Browser-callable directly with `fetch` (unlike gRPC)
- Streaming supported (Connect: yes; Twirp: no)
- Less feature-complete than gRPC but covers the common 80%

### Anti-pattern: gRPC for the public API

If your callers are external (third-party developers, mobile teams you don't control, browsers): use REST or Connect. gRPC's operational burden on external callers is real.

---

## 7. Protobuf design essentials

```protobuf
syntax = "proto3";

package myorg.users.v1;     // semantic-version the package; never break clients of v1

message User {
  string id = 1;            // field numbers are wire identity - never re-number
  string email = 2;
  string display_name = 3;
  reserved 4, 5;            // numbers of removed fields; prevents accidental reuse
  reserved "deprecated_field_name";

  // Presence semantics: in proto3, scalar zero values don't serialize.
  // Use `optional` (proto3 since 2020) or wrapper types for true "absent" semantics.
  optional string phone = 6;  // absent vs empty distinguishable
}

message UpdateUserRequest {
  string id = 1;
  // oneof for mutually-exclusive update modes
  oneof update {
    string new_email = 2;
    string new_display_name = 3;
  }
}
```

### Schema-evolution rules (memorize)

| Change | Compatible? |
|---|---|
| Add a new field with a new number | Yes (forward + backward) |
| Remove a field, **reserve the number** | Yes |
| **Re-number a field** | NO - changes wire identity; corrupts existing data |
| **Change a field's type** | NO (with rare exceptions like int32 <-> int64 same wire kind) |
| Rename a field (number unchanged) | Yes (wire is by number, not name) |
| Add value to an enum | Backward-compatible; old code sees UNKNOWN |
| Remove an enum value | Risky; old data may carry it |
| Change `optional` to `repeated` | NO |
| Make required field optional (proto2) | Yes (no-op in proto3; everything is optional) |

See [`references/protobuf-schema-evolution.md`](references/protobuf-schema-evolution.md) for the long form with examples.

### Wire-format gotchas

- **Default values don't appear on the wire** (proto3 scalars). Receiver can't distinguish "set to zero" from "absent". Use `optional` (since 2020) or wrapper types (`google.protobuf.StringValue`).
- **Field numbers 1-15 use 1 byte tag; 16+ use 2.** Reserve 1-15 for hot fields.
- **Unknown fields are preserved by default** in most languages. Don't strip them.
- **`bytes` and `string` are similar on the wire**; `bytes` skips UTF-8 validation. Use `bytes` for binary; `string` for text.

---

## 8. Connection pooling per language

The #1 production-performance bug: a fresh HTTP client per request.

### Go

```go
// BAD: new Client per request -> no keepalive
func bad(url string) {
    resp, _ := http.Get(url)  // uses http.DefaultClient with default Transport
    // but if you do `http.Client{Transport: &http.Transport{...}}` per call, you lose pooling
}

// GOOD: package-level (or DI'd) client, reused
var client = &http.Client{
    Timeout: 10 * time.Second,
    Transport: &http.Transport{
        MaxIdleConnsPerHost: 100,
        IdleConnTimeout:     90 * time.Second,
        DialContext: (&net.Dialer{
            Timeout:   5 * time.Second,
            KeepAlive: 30 * time.Second,
        }).DialContext,
    },
}
```

### Python

```python
# BAD: requests.get() per call - no session reuse
def bad(url):
    return requests.get(url)

# GOOD: Session pools connections, sends keepalive headers
session = requests.Session()
adapter = HTTPAdapter(pool_connections=20, pool_maxsize=100, max_retries=3)
session.mount('https://', adapter)
session.mount('http://', adapter)
```

### Node

```javascript
// BAD: implicit Agent per call (older Node)
const res = await fetch(url);

// GOOD: shared keepalive agent (Node 19+ defaults to keepAlive: true; older versions don't)
const https = require('https');
const agent = new https.Agent({ keepAlive: true, maxSockets: 100, timeout: 30_000 });
const res = await fetch(url, { agent });
```

### gRPC clients

```python
# Single channel reused across calls (NOT a channel per call)
channel = grpc.insecure_channel('service:50051', options=[
    ('grpc.keepalive_time_ms', 30_000),
    ('grpc.keepalive_timeout_ms', 5_000),
    ('grpc.keepalive_permit_without_calls', True),
    ('grpc.http2.max_pings_without_data', 0),
])
stub = MyServiceStub(channel)
```

A gRPC channel is itself a connection pool; create one per `(service, credentials)` pair and reuse for the lifetime of the process.

---

## 9. Long-lived connections

| Pattern | Protocol | Use when | Watch out for |
|---|---|---|---|
| **Websocket** | WS over HTTP Upgrade | Bidirectional, real-time, browser-friendly | LB idle timeout (NLB 350s; ALB 60s; Cloudflare 100s free / 300s paid); reconnect logic with exponential backoff |
| **Server-Sent Events (SSE)** | HTTP/1.1+ text/event-stream | Server-to-client push, browser-friendly, simpler than WS | One-way only; some proxies buffer; need `keepalive` comments to defeat idle timeouts |
| **gRPC streaming** | HTTP/2 streams | Polyglot service-to-service, bidirectional or unidirectional | Browser unsupported (use Connect streams instead); load balancer must understand HTTP/2 |
| **Long polling** | HTTP/1.1 | Legacy clients, last-resort fallback | High per-request overhead; consider SSE first |

### Idle-timeout cheat sheet

| Proxy / LB | Default idle timeout | Configurable |
|---|---|---|
| AWS Network Load Balancer (NLB) | 350s (TCP), 350s (UDP) | No (fixed) |
| AWS Application LB (ALB) | 60s | Yes, 1-4000s |
| AWS API Gateway REST | 29s | No (fixed; will be 30s+ for HTTP APIs) |
| AWS API Gateway WebSocket | 10 min idle, 2 hr total | No |
| Cloudflare WebSocket | 100s (free), 300s (paid) | No (use tickets/heartbeats) |
| Cloudflare HTTP/2 | 100s | No |
| Nginx (default) | 60s (proxy_read_timeout) | Yes |
| Envoy | 1h (stream_idle_timeout) | Yes |

**Application-level heartbeats** (every 30-60s) are the only reliable way to defeat idle-timeout disconnects across this matrix.

---

## 10. Edge / CDN patterns

- **Cold POPs** are real: first request to a POP that hasn't seen your origin pays a full handshake. Subsequent requests reuse the warm connection.
- **CDN-to-origin keepalive** is on by default in Cloudflare, Fastly, CloudFront. Verify and tune origin-side keepalive timeouts to match (origin must not drop before CDN reuses).
- **Anycast routing** brings the connection to the nearest POP; routes between POPs and origin use the CDN's own backbone (faster than the public internet for cross-region).
- **HTTP/3 from edge to client** is supported by all major CDNs; origin-to-edge usually remains HTTP/2.
- **Regional fall-through**: if a POP can't reach origin, CDN may try other regions. Configure origin allow-lists or auth that work from any POP.

---

## 11. Observability for the transport layer

Metrics to capture per outbound HTTP/gRPC client:

| Metric | Why |
|---|---|
| `http_client_requests_total{status, host}` | Error budget |
| `http_client_duration_seconds_bucket{host, status}` | P50/P95/P99 latency by host |
| `http_client_connection_reuses_total{host}` / `_creates_total` | Connection-pool effectiveness; ratio should be high |
| `tcp_keepalive_probe_failures_total` | OS-side dead-peer detection rate |
| `tls_handshake_duration_seconds_bucket` | Handshake cost contribution to TTFB |
| `dns_lookup_duration_seconds_bucket` | DNS cost (often forgotten) |
| `grpc_client_msg_received_total{rpc, code}` | gRPC streaming health |

For deeper observability patterns see `rules/330-observability.mdc`.

---

## 12. Anti-patterns

1. **New HTTP client per request.** Defeats connection reuse, burns ~50-150ms / call on handshake. #1 production performance bug.
2. **Default OS TCP keepalive in cloud.** 2-hour idle means connections look alive long after LB cut them; first write fails.
3. **HTTP/2 single connection across mobile / lossy networks.** TCP HoL stalls all streams; HTTP/1.1 parallel or HTTP/3 wins.
4. **gRPC for a browser-facing API without gRPC-Web/Connect.** Doesn't work; teams discover too late.
5. **Re-numbering a protobuf field.** Wire-incompatible; existing data and clients corrupt.
6. **proto3 scalar field for true "optional" semantics.** Default-zero-doesn't-serialize means receiver can't distinguish; use `optional` (since 2020) or wrappers.
7. **Buffering then sending.** TTFB blows up; stream incrementally where possible.
8. **Keepalive longer than LB idle timeout.** LB wins; "random" disconnects appear in P99.
9. **One TCP connection per RPC** in a high-call-rate service. Channel-per-call instead of channel-reuse is gRPC's equivalent of #1.
10. **Assuming HTTP/3 works without verifying UDP/443.** Corporate proxies and some ISPs filter; fall back gracefully.

---

## 13. Reviewer checklist

For any PR introducing or modifying an HTTP / gRPC client:

- [ ] Client is created once (package-level, DI, singleton) and reused
- [ ] Explicit timeout set (overall request, not just connect)
- [ ] TCP keepalive interval set < load balancer idle timeout
- [ ] `MaxIdleConnsPerHost` / pool size sized to the workload (default is often 2)
- [ ] TLS minimum is 1.2; prefer 1.3
- [ ] Retry policy bounded (max attempts, max total time, backoff with jitter)
- [ ] Metrics: latency histogram, status counter, connection-reuse ratio
- [ ] If gRPC: channel reused; keepalive options set; `permit_without_calls` if appropriate

For any PR adding or changing a `.proto`:

- [ ] No field re-numbered
- [ ] Removed fields have `reserved` for both number and name
- [ ] New fields use unused numbers (never reused)
- [ ] Optional semantics: `optional` keyword (proto3 since 2020) or wrapper types
- [ ] Package versioned in the namespace (`myorg.users.v1`)
- [ ] Generated code committed or generated in CI from the `.proto`

---

## References

- [`references/grpc-vs-rest-decision.md`](references/grpc-vs-rest-decision.md) - Decision matrix with worked examples
- [`references/protobuf-schema-evolution.md`](references/protobuf-schema-evolution.md) - Schema evolution rules, presence semantics, the field-renumber hazard

## Related

- Rule: `320-api-design.mdc` - API surface (verbs, status, versioning) - the layer above this skill
- Rule: `316-zero-trust.mdc` - Network section (mTLS, default-deny egress) - the security model on top of this transport
- Rule: `330-observability.mdc` - Logging, metrics, tracing - including the transport-layer metrics above
- Rule: `400-cloudflare.mdc` - CDN patterns, Workers, edge-to-origin connection lifecycle
- Rule: `410-aws.mdc` - AWS ALB/NLB/API Gateway idle-timeout specifics
- Rule: `483-kafka.mdc` - Kafka transport + Avro/Protobuf schema registry
- Rule: `510-mcp-servers.mdc` - MCP protocol patterns
- Skill: `zero-trust` - Network-tier security pairing
- Skill: `cloud-platforms` - Per-cloud LB and edge specifics
