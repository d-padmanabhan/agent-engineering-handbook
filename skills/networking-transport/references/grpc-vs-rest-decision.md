# gRPC vs REST: Decision Matrix

The honest tradeoffs. None of these are "best practice in all cases"; each row is the choice that makes the *least* trouble for that scenario.

## The matrix

| Scenario | Choice | Why |
|---|---|---|
| Public API consumed by third-party developers | **REST + JSON** | Curl-debuggable, OpenAPI spec, broadest tooling, no SDK generation for callers |
| Browser-callable (SPA -> backend) | **REST + JSON** or **Connect** | gRPC needs gRPC-Web + proxy; Connect calls work with plain `fetch` |
| Internal east-west, polyglot services, you own both ends | **gRPC + Protobuf** | Schema-first contract, code-gen in every language, ~5-10x smaller wire, ~3-5x faster (de)serialization, HTTP/2 multiplexing |
| Long-lived bidirectional streaming (chat, telemetry, agent comm) | **gRPC streaming** or **websocket** | gRPC if you control both ends; websocket if browser is a client |
| Client-driven shape (mobile app picks fields to reduce payload) | **GraphQL** | Single endpoint, query specifies shape |
| Want gRPC's contract discipline without HTTP/2 mandate | **Connect** or **Twirp** | Protobuf schemas + HTTP/1.1-friendly; Connect adds streaming |
| Mobile <-> backend | **REST + JSON** (or **REST + Protobuf**) | gRPC works but reconnect / battery / network-resilience matrices are harder than REST + retry |
| Event-driven / pub-sub | **Kafka / NATS / SQS** with Avro/Protobuf schemas | This is not a request/response problem; see `rules/483-kafka.mdc` |
| Webhook receiver (you receive notifications from a SaaS) | **REST + JSON** | Sender writes the contract; you don't get a vote on protocol |
| Service mesh east-west with sidecar proxies (Istio, Linkerd) | **gRPC** | Mesh assumes HTTP/2; mTLS, retries, load-balancing all out-of-box |
| AWS Lambda HTTP-triggered | **REST or HTTP API Gateway** | API Gateway WebSocket exists but gRPC is awkward (HTTP/1.1 LB); use REST/JSON or Lambda Function URLs |

## Worked example 1: internal microservice rewrite

**Before:** Python service calls Go service over REST/JSON. P99 of inter-service call is 80ms (45ms application + 25ms ser/deser of a 100-field nested response + 10ms HTTP overhead).

**After:** Same services, switched to gRPC/Protobuf.

| Metric | REST/JSON | gRPC/Protobuf |
|---|---|---|
| Wire payload | 18 KB JSON | 2.4 KB Protobuf |
| Serialization (Python side) | ~12ms | ~3ms |
| Deserialization (Go side) | ~9ms | ~2ms |
| Connection model | New TCP per call (no keepalive in old code) or pooled | Multiplexed HTTP/2 streams over one persistent connection |
| Schema discipline | "Look at the JSON response" + handwritten Python dataclass | `.proto` file is source of truth; Go + Python both generated |
| P99 latency | 80ms | ~52ms |
| Operator burden | None new | gRPC-aware load balancer; `grpcurl` for ops; observability hooks |

Net: a real win for an internal east-west call. The latency improvement is half wire size, half serialization; the schema-discipline win is bigger over the medium term.

Would not have been worth it for a 1-call-per-second admin endpoint.

## Worked example 2: public API where gRPC would have been wrong

**Scenario:** SaaS company shipping a public API for customer integrations.

**If they had picked gRPC:**

- Customer developers need to generate clients from `.proto`. Most don't want to install `protoc` and a language-specific plugin.
- Cannot curl the API for quick checks.
- Caching: no `Cache-Control` semantics; no CDN integration.
- Browser-side use: cannot call directly; needs gRPC-Web proxy.
- Spec discoverability: customers expect OpenAPI / Swagger; have to ship `.proto` instead.

**REST + JSON wins by default for public APIs** unless the audience is specifically tolerant of gRPC (e.g., internal partner integrations with controlled tooling).

## Worked example 3: streaming use case where gRPC is the right answer

**Scenario:** Server pushes telemetry samples to a control plane every second from 10,000 agents.

| Approach | Why it fails |
|---|---|
| HTTP polling | Massive overhead; one TCP+TLS handshake per second per agent |
| Websocket | Works; but no schema contract; bespoke ser/deser; hard to fan in across languages |
| gRPC bidirectional stream | Single long-lived HTTP/2 stream per agent; `.proto` defines the message contract; clients in 8 languages generated; mesh-friendly |

gRPC is the right answer because (a) streaming is first-class, (b) the contract is enforced by code-gen, (c) the load is high enough to justify the per-byte savings.

## The "five questions" before picking gRPC

1. **Do you control both ends?** If no -> REST or wait for callers to migrate.
2. **Do you need streaming?** If yes -> gRPC (or Connect/websocket).
3. **Are the calls high-frequency or large-payload?** If yes -> gRPC's wire savings matter.
4. **Are your callers comfortable with code-gen?** If polyglot internal -> yes; if external developers -> often no.
5. **Does your infra speak HTTP/2 end-to-end?** Service mesh, ALB, modern LB -> yes. Naive L4 LB, API Gateway REST mode, some VPN paths -> no.

If you can't say "yes" to at least 3 of those 5, default to REST/JSON.

## What about Connect (and Twirp)?

[Connect](https://connectrpc.com/) gives you:

- Protobuf schemas (gRPC's strongest feature)
- HTTP/1.1-friendly (no HTTP/2 mandate)
- Browser-callable directly with `fetch`
- Streaming (bidirectional in v2)
- Smaller language matrix than gRPC (Go, TS, Swift, Kotlin)

Connect is the right middle ground when you want gRPC's contract discipline but your runtime has HTTP/2 problems (some corporate environments, certain edge platforms) or you need browser callers without a proxy.

Twirp is similar but no streaming and a narrower ecosystem.

## What about GraphQL?

GraphQL is its own category, not a gRPC competitor. Use when:

- Clients (especially mobile) need to fetch different shapes from the same backend
- You have many small entities that compose in many ways
- You want client-driven projection without proliferating REST endpoints

Don't use when:

- Each query has roughly the same shape - REST is simpler
- You need granular caching - REST + ETag/Cache-Control is easier
- Authz is per-field - GraphQL pushes complexity to resolvers

## Bottom line

The wire format is a 5-year decision. Optimize for the *callers* you have, not the benchmarks you read.
