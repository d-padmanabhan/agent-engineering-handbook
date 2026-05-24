# Bindings and Storage Decision Matrix

The single most consequential design decision in any new Worker. Pick wrong and you'll be migrating data in six months. This matrix names each option's strengths, limits, and the cases where it's the wrong choice even when it looks right.

---

## Quick decision tree

```
Do you need to persist data?
├─ No → no storage binding needed
├─ Yes, small (<25 MB per value) and eventually-consistent OK
│  ├─ Read-heavy, few writes → KV
│  └─ Write-heavy → reconsider; KV is not for write-heavy workloads
├─ Yes, relational (joins, transactions, schema)
│  ├─ Fits in SQLite, single-region OK → D1
│  └─ Need multi-region writes or > D1 limits → Hyperdrive + your own Postgres
├─ Yes, blobs (any size)
│  ├─ Public assets → R2 (with public domain or Worker proxy)
│  └─ Private blobs → R2 with signed URLs or Worker-proxied access
├─ Yes, strongly-consistent coordination (websockets, rate limit, session)
│  └─ Durable Object (with optional SQLite-backed DO storage for relational-shaped DO state)
├─ Yes, connecting to existing Postgres / MySQL
│  └─ Hyperdrive (pools and caches; replaces direct TCP)
└─ Yes, vector search
   └─ Vectorize
```

---

## KV (Workers KV)

**Use for:** sessions, feature flags, rate-limit counters with eventually-consistent semantics, low-write config, cached JSON for `<60s` TTL use cases.

**Strengths:**

- Globally distributed reads (~10ms p50 from any edge)
- Free tier covers many use cases
- Simple key-value API; values up to 25 MB

**Limits:**

- Eventually consistent: a write may take up to 60s to propagate globally
- Write rate-limited (~1 write/sec per key)
- No transactions
- No querying (only `get` / `put` / `delete` / `list` by prefix)

**Wrong choice when:**

- Strong consistency required (use DO instead)
- High write rate (use D1 or DO)
- Values > 25 MB (use R2)
- Querying by anything other than key prefix (use D1)
- Storing relational data (use D1)

**`wrangler.jsonc`:**

```jsonc
"kv_namespaces": [
  { "binding": "SESSION_KV", "id": "<kv-id>" }
]
```

**TypeScript:**

```typescript
const session = await env.SESSION_KV.get<Session>(`session:${sid}`, "json");
await env.SESSION_KV.put(`session:${sid}`, JSON.stringify(data), {
  expirationTtl: 3600,   // seconds; key auto-deleted after TTL
});
```

---

## D1 (SQLite-backed)

**Use for:** relational data, queries with joins / aggregates, transactional updates, anything that benefits from SQL.

**Strengths:**

- Real SQL (SQLite syntax)
- Transactions via `batch()`
- Single-region read replica reads (with [D1 read replication](https://developers.cloudflare.com/d1/best-practices/read-replication/))
- Prepared statements with bound parameters (safe from SQL injection if used correctly)

**Limits:**

- Single primary region; writes go to the primary, reads can hit replicas
- 10 GB max per database (as of 2026)
- ~50 concurrent connections per Worker isolate
- No native foreign-key constraints unless you enable them per connection (`PRAGMA foreign_keys = ON`)

**Wrong choice when:**

- Multi-region active-active writes needed (use Hyperdrive + Postgres)
- Database larger than 10 GB (use Hyperdrive + Postgres / your own DB)
- Heavy analytics queries (use Analytics Engine or pipe to external warehouse)
- Strongly-consistent global locks (use DO)

**`wrangler.jsonc`:**

```jsonc
"d1_databases": [
  { "binding": "DB", "database_name": "production", "database_id": "<d1-id>" }
]
```

**TypeScript:**

```typescript
// Single query
const { results } = await env.DB.prepare(
  "SELECT id, name FROM users WHERE org_id = ? LIMIT 100",
).bind(orgId).all<User>();

// Batch (one subrequest for many statements; transactional)
await env.DB.batch([
  env.DB.prepare("INSERT INTO events (user_id, type) VALUES (?, ?)").bind(uid, "login"),
  env.DB.prepare("UPDATE users SET last_login = ? WHERE id = ?").bind(now, uid),
]);
```

**Always use prepared statements** with `.bind()`. Never concatenate user input into SQL strings.

---

## R2 (object storage, S3-compatible)

**Use for:** files, images, backups, model artifacts, anything blob-shaped.

**Strengths:**

- Zero egress fees (this is the headline feature; saves substantial $ vs S3)
- S3-compatible API (existing S3 tooling works)
- Any object size
- Object lifecycle rules (auto-delete after N days)
- Event notifications to Queues on object create / delete

**Limits:**

- No querying object metadata in bulk (use Worker + `list` for filtering)
- Eventual consistency on `list` after writes
- No native server-side encryption-with-customer-key (CMK); use client-side encryption if needed

**Wrong choice when:**

- Storing structured queryable data (use D1)
- Tiny key-value pairs (use KV; R2 has per-operation overhead)

**`wrangler.jsonc`:**

```jsonc
"r2_buckets": [
  { "binding": "ASSETS", "bucket_name": "production-assets" }
]
```

**TypeScript:**

```typescript
// Upload
await env.ASSETS.put(`uploads/${id}.png`, req.body!, {
  httpMetadata: { contentType: "image/png" },
});

// Download
const obj = await env.ASSETS.get(`uploads/${id}.png`);
if (!obj) return new Response("Not Found", { status: 404 });
return new Response(obj.body, {
  headers: { "Content-Type": obj.httpMetadata?.contentType ?? "application/octet-stream" },
});
```

---

## Durable Objects

**Use for:** strongly-consistent coordination, websocket fan-out, sticky sessions, rate limiting that must be exact, leader election, sharded state.

**Strengths:**

- Single-writer-per-ID semantics (no concurrent state mutation)
- Strongly consistent reads of own state
- Built-in `storage` API (with optional SQLite backing for relational-shaped DO state)
- Hibernation API (DO sleeps between requests; you don't pay for idle time)
- WebSocket support

**Limits:**

- Single region per DO instance (placement chosen by Cloudflare based on traffic)
- Each DO is a single-threaded actor (can't scale horizontally within one ID)
- Storage limits: 50 GB SQLite-backed, 256 KB per value in legacy KV-style

**Wrong choice when:**

- You want horizontal scaling without sharding (DO is per-ID single-writer)
- The data isn't keyed by some logical entity (DO IDs need a stable derivation - room ID, user ID, tenant ID)

**`wrangler.jsonc`:**

```jsonc
"durable_objects": {
  "bindings": [{ "name": "ROOM", "class_name": "Room" }]
},
"migrations": [
  { "tag": "v1", "new_sqlite_classes": ["Room"] }   // use SQLite-backed storage (recommended for new DOs)
]
```

**TypeScript:**

```typescript
import { DurableObject } from "cloudflare:workers";

export class Room extends DurableObject<Env> {
  async fetch(req: Request): Promise<Response> {
    const count = (await this.ctx.storage.get<number>("count")) ?? 0;
    await this.ctx.storage.put("count", count + 1);
    return new Response(String(count + 1));
  }
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const id = env.ROOM.idFromName("global");
    const stub = env.ROOM.get(id);
    return stub.fetch(req);
  },
} satisfies ExportedHandler<Env>;
```

---

## Hyperdrive (Postgres / MySQL connection pooling + caching)

**Use for:** connecting Workers to existing Postgres or MySQL databases.

**Strengths:**

- Connection pooling at the edge (Workers can't hold long-lived TCP connections; Hyperdrive does it for you)
- Edge query caching for read-heavy workloads (configurable per query)
- Single connection string in `wrangler.jsonc`; Hyperdrive routes through the closest edge pool

**Limits:**

- Only Postgres and MySQL; no MSSQL / Oracle / Cosmos
- Caching is opt-in per query (via `pg`'s `Hyperdrive` driver helper)

**`wrangler.jsonc`:**

```jsonc
"hyperdrive": [
  { "binding": "POSTGRES", "id": "<hyperdrive-id>" }
]
```

**TypeScript (with `postgres` driver):**

```typescript
import postgres from "postgres";

export default {
  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const sql = postgres(env.POSTGRES.connectionString, {
      max: 5,   // per-isolate pool size
      fetch_types: false,
    });
    try {
      const rows = await sql`SELECT id, name FROM users WHERE org_id = ${orgId} LIMIT 100`;
      return Response.json(rows);
    } finally {
      ctx.waitUntil(sql.end());   // close after response sent
    }
  },
} satisfies ExportedHandler<Env>;
```

---

## Queues

**Use for:** decoupling producer from consumer, batching, dead-letter handling, retries with backoff.

**Strengths:**

- At-least-once delivery
- Configurable batch size / batch timeout
- Dead-letter queue support
- Producer Worker writes; Consumer Worker pulls in batches

**`wrangler.jsonc`:**

```jsonc
"queues": {
  "producers": [{ "binding": "INGEST", "queue": "ingest" }],
  "consumers": [
    {
      "queue": "ingest",
      "max_batch_size": 25,
      "max_batch_timeout": 30,
      "dead_letter_queue": "ingest-dlq"
    }
  ]
}
```

**TypeScript (producer):**

```typescript
await env.INGEST.send({ userId, eventType, timestamp: Date.now() });
```

**TypeScript (consumer):**

```typescript
export default {
  async queue(batch: MessageBatch<MyMsg>, env: Env, ctx: ExecutionContext): Promise<void> {
    for (const msg of batch.messages) {
      try {
        await processMessage(msg.body, env);
        msg.ack();
      } catch (err) {
        msg.retry({ delaySeconds: 60 });   // retry with backoff
      }
    }
  },
} satisfies ExportedHandler<Env>;
```

---

## Workers AI + AI Gateway

**Use for:** LLM inference, embeddings, image generation, speech recognition - any AI workload.

**Pattern:** put **AI Gateway** in front of **Workers AI** (or any provider). Gateway gives you:

- Cost cap per gateway / per provider
- Response caching (configurable per request)
- Rate limiting
- Per-provider analytics
- Fallback chains (try OpenAI; if rate-limited, fall back to Workers AI)

**`wrangler.jsonc`:**

```jsonc
"ai": { "binding": "AI" }
```

**TypeScript:**

```typescript
// Through AI Gateway (recommended)
const response = await fetch(
  `https://gateway.ai.cloudflare.com/v1/${env.ACCOUNT_ID}/${env.GATEWAY_ID}/workers-ai/@cf/meta/llama-3.1-8b-instruct`,
  {
    method: "POST",
    headers: { "Authorization": `Bearer ${env.AI_TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({ messages: [{ role: "user", content: prompt }] }),
  },
);

// Direct (no Gateway - lose cost cap and caching)
const response = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", {
  messages: [{ role: "user", content: prompt }],
});
```

---

## Vectorize (vector embeddings)

**Use for:** semantic search, retrieval-augmented generation (RAG), recommendation systems.

**Strengths:**

- ANN index (approximate nearest neighbor) built in
- Filterable metadata (declare filterable fields at index creation)
- Cosine / euclidean / dot-product distance metrics

**`wrangler.jsonc`:**

```jsonc
"vectorize": [
  { "binding": "DOCS_INDEX", "index_name": "docs-v1" }
]
```

---

## Decision worked examples

**"I need to store user sessions."**
→ KV (low write, eventually consistent OK, small values). If sessions must be revoked instantly across regions, use DO instead.

**"I need to store user profiles with searchable fields."**
→ D1 (relational, queryable). Add indexes on the searchable columns.

**"I need to store uploaded files."**
→ R2 (any size; zero egress). Reference the R2 key from D1 user profiles.

**"I need exact-counter rate limiting per user."**
→ DO (one instance per user ID; strongly consistent counter).

**"I need approximate rate limiting per IP."**
→ KV (eventually consistent counter; cheap; "approximate" is the trade).

**"I need to call our existing Postgres database."**
→ Hyperdrive (pool + cache; one connection string in wrangler config).

**"I need to fan out webhook events to many downstream services."**
→ Queues (one consumer Worker per downstream; ack/retry per message).

**"I need LLM-powered chat."**
→ Workers AI behind AI Gateway (cost cap + caching + analytics).

**"I need RAG over my docs."**
→ Vectorize (semantic search) + R2 (raw docs) + Workers AI / AI Gateway (LLM completion).
