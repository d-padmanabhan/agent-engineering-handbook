# Cloudflare Patterns

## Naming & Terminology Consistency

- Never use `CloudFlare` anywhere (code/documentation). If found, fix to `Cloudflare`
- For Cloudflare, do not use the word `Domain`. Always use `Zone`. If any docs mention “Cloudflare Domain”, fix to “Cloudflare Zone”

## Rules language regex strings (raw vs quoted)

Cloudflare expressions support string values as either quoted strings (`"..."`) or raw strings (`r"..."`).
For regex patterns, prefer raw strings to reduce escaping mistakes (Cloudflare recommends this for regular expressions).

- **Quoted string**: backslashes are parsed by the string literal first, then by the regex engine - easy to under/over-escape
- **Raw string**: fewer escape surprises, easier to review

> [!NOTE]
> Case-insensitivity is separate. Use `(?i)` inside the regex (raw vs quoted does not control case sensitivity).
>
> Docs: `https://developers.cloudflare.com/ruleset-engine/rules-language/values/` (String values and regular expressions)

Example (raw regex + anchors):

```text
(http.host matches r"(?i)^citizen-dev[0-9]+\.sbx\.apps\.acme\.com\.?$" and ip.src in $firm_egress_ips)
```

## Workers

### Basic Worker

```javascript
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // Route handling
    if (url.pathname === '/api/users') {
      return handleUsers(request, env);
    }
    
    if (url.pathname === '/api/data') {
      return handleData(request, env);
    }
    
    return new Response('Not Found', { status: 404 });
  }
};

async function handleUsers(request, env) {
  // Access KV storage
  const users = await env.USERS_KV.get('all', 'json');
  
  return new Response(JSON.stringify(users), {
    headers: { 'Content-Type': 'application/json' }
  });
}

async function handleData(request, env) {
  // Access D1 database
  const { results } = await env.DB.prepare(
    'SELECT * FROM data WHERE active = ?'
  ).bind(true).all();
  
  return Response.json(results);
}
```

For Durable Objects (stateful per-entity Workers), see the [Durable Objects](#durable-objects) section below.

## Durable Objects

Stateful, single-instance Workers with strongly-consistent storage. The right primitive when "exactly one place per identity holds the truth": per-user / per-room / per-tenant counters, websocket connection state, leader election, rate limiters, session stores, and any coordination problem that does not fit eventually-consistent KV / D1 patterns. As of Workers Runtime v3 (2024+), the recommended default is **SQLite-backed DOs** with hibernation enabled, which collapses the storage cost and unlocks `state.storage.sql`.

### Core rules

- **One DO per logical entity.** Derive the id from a stable business key via `idFromName('user-' + userId)`; never from a random key, or every request creates a new instance.
- **Single-threaded per instance.** All requests to the same DO are serialized. A slow `fetch` blocks every other caller of that instance. Move slow work to alarms or other Workers.
- **Use SQLite-backed storage by default** (`new_sqlite_classes` in your migration). `state.storage.sql.exec("SELECT ...")` is faster and cheaper than `storage.put/get` for anything relational. Plain KV-style `storage.put/get` is fine for tiny counters and flags.
- **All writes are transactional.** Individual `storage.put` calls are atomic; group multiple writes via `state.storage.transaction(async (txn) => { ... })`.
- **Hibernate websockets.** Use the Hibernation API (`state.acceptWebSocket(ws)`, `webSocketMessage`, `webSocketClose`) instead of long-lived `addEventListener` handlers - the instance can sleep between messages and you only pay for active work.
- **Alarms for delayed / periodic work.** `state.storage.setAlarm(timestamp)` plus an `async alarm()` handler survives migrations and reschedules. Do not use `setTimeout`.
- **Block hot keys.** A single DO for "global rate limiter keyed by something with one value" is a hotspot. Shard by request hash or tenant.
- **Handle 503 Durable Object reset.** During deployment migrations the DO can be killed mid-request; clients must retry. Surface this in your SDK / client code with backoff.

### Basic DO with SQLite storage

```typescript
import { DurableObject } from 'cloudflare:workers';

export class Room extends DurableObject {
  constructor(state: DurableObjectState, env: Env) {
    super(state, env);
    state.storage.sql.exec(`
      CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author TEXT NOT NULL,
        body TEXT NOT NULL,
        created_at INTEGER NOT NULL
      );
    `);
  }

  async post(author: string, body: string) {
    this.ctx.storage.sql.exec(
      'INSERT INTO messages (author, body, created_at) VALUES (?, ?, ?)',
      author, body, Date.now(),
    );
  }

  async history(limit = 50): Promise<unknown[]> {
    return this.ctx.storage.sql.exec(
      'SELECT id, author, body, created_at FROM messages ORDER BY id DESC LIMIT ?',
      limit,
    ).toArray();
  }
}

export default {
  async fetch(req: Request, env: Env) {
    const url = new URL(req.url);
    const roomName = url.pathname.split('/')[2];
    const id = env.ROOM.idFromName(roomName);
    const stub = env.ROOM.get(id);
    return new Response(JSON.stringify(await stub.history()), {
      headers: { 'content-type': 'application/json' },
    });
  },
};
```

### Hibernating websockets

```typescript
export class Chat extends DurableObject {
  async fetch(req: Request) {
    if (req.headers.get('upgrade') !== 'websocket') return new Response('Expected WebSocket', { status: 426 });
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    this.ctx.acceptWebSocket(server);                    // Hibernation enabled
    return new Response(null, { status: 101, webSocket: client });
  }

  async webSocketMessage(ws: WebSocket, msg: string | ArrayBuffer) {
    // Broadcast to all connected sockets - no in-memory list to keep
    for (const peer of this.ctx.getWebSockets()) peer.send(msg);
  }

  async webSocketClose(ws: WebSocket, code: number) {
    ws.close(code, 'closed');
  }
}
```

The instance can hibernate between messages; `getWebSockets()` enumerates the still-attached connections on wake.

### Alarms (delayed / periodic work)

```typescript
export class JobRunner extends DurableObject {
  async schedule(jobId: string, runAt: number) {
    await this.ctx.storage.put(`job:${jobId}`, { runAt });
    const earliest = Math.min(runAt, (await this.ctx.storage.getAlarm()) ?? Infinity);
    await this.ctx.storage.setAlarm(earliest);
  }

  async alarm() {
    const now = Date.now();
    const due = await this.ctx.storage.list({ prefix: 'job:' });
    for (const [key, value] of due) {
      const job = value as { runAt: number };
      if (job.runAt <= now) {
        await this.process(key);
        await this.ctx.storage.delete(key);
      }
    }
    // Re-arm for the next due job
    const remaining = await this.ctx.storage.list({ prefix: 'job:' });
    const next = Math.min(...[...remaining.values()].map((v: any) => v.runAt));
    if (Number.isFinite(next)) await this.ctx.storage.setAlarm(next);
  }

  async process(jobKey: string) { /* ... */ }
}
```

### Rate limiter pattern

```typescript
export class RateLimiter extends DurableObject {
  async check(key: string, limit: number, windowMs: number): Promise<boolean> {
    const now = Date.now();
    const cutoff = now - windowMs;
    this.ctx.storage.sql.exec('DELETE FROM hits WHERE ts < ?', cutoff);
    const { count } = this.ctx.storage.sql
      .exec<{ count: number }>('SELECT COUNT(*) as count FROM hits').one();
    if (count >= limit) return false;
    this.ctx.storage.sql.exec('INSERT INTO hits (ts) VALUES (?)', now);
    return true;
  }
}
```

Key the DO by the *thing being limited* (user id, IP, tenant). For very high-cardinality limiting (per-IP global), shard via consistent hash to N DOs to avoid hotspots.

### wrangler.toml binding

```toml
[[durable_objects.bindings]]
name = "ROOM"
class_name = "Room"

[[migrations]]
tag = "v1"
new_sqlite_classes = ["Room"]   # SQLite-backed; recommended default
# new_classes = ["Room"]        # legacy KV-style storage; avoid for new work
```

### Anti-patterns

- Keying every DO by `'global'` for a counter / rate limiter. One DO can't scale past its own single-threaded limit; shard.
- Using `storage.put/get` for relational data when SQLite is available. The SQL backend is faster, cheaper, and queryable.
- Non-hibernating websocket handlers (`addEventListener('message', ...)`). The instance stays in memory between messages and you pay for it.
- `setTimeout` for delayed work. Doesn't survive instance migration; use `setAlarm`.
- Forgetting `await` on `storage.put`. The write may not have hit before the request returns; consistency guarantees do not hold.
- One giant `fetch` that fans out to other services synchronously. Move outbound calls to alarms or to other Workers; keep the DO request short.
- Not handling DO reset (503) on the client. Migrations and crashes happen; retry with backoff and reset stateful caches.

## Pages

### Configuration (wrangler.toml)

```toml
name = "my-app"
compatibility_date = "2024-01-01"

[site]
bucket = "./dist"

[[kv_namespaces]]
binding = "KV"
id = "xxx"

[[d1_databases]]
binding = "DB"
database_name = "my-db"
database_id = "xxx"

[vars]
ENVIRONMENT = "production"
```

### Pages Functions

File-routed Workers attached to a Pages project. Files under `functions/` map to URL paths automatically - `functions/api/users/[id].ts` handles `GET /api/users/:id`. Pages Functions and standalone Workers share the same runtime and bindings; pick Pages when the project also has static assets, pick a plain Worker when it's API-only.

#### Core rules

- **Let file routing do the work.** A file at `functions/api/users/[id].ts` handles `GET /api/users/:id` automatically. Reach for `[[catchall]].ts` only when route shapes are genuinely dynamic.
- **Dynamic segments via brackets.** `[id].ts` for a single segment, `[[path]].ts` for catch-all. `context.params.id` and `context.params.path` (string array) carry the values.
- **Method-specific handlers.** Export `onRequestGet`, `onRequestPost`, etc. Use plain `onRequest` only when one handler legitimately serves multiple methods.
- **Middleware via `_middleware.ts`.** Runs on every request to the directory tree it lives in. Use for auth, CORS, request-id injection, common error handling. Cascades from root.
- **`_routes.json` keeps assets static.** Without it, every request walks the functions tree, intercepting 404s for missing assets. Always include explicit exclude rules in production.
- **Bindings are identical to Workers.** `context.env.DB`, `context.env.KV`, `context.env.AI` all work the same.
- **Use `context.next()` in middleware**, not `fetch(context.request)`. Calling `fetch` re-enters the routing tree and creates loops.

#### Dynamic route handler

```typescript
// functions/api/users/[id].ts
export async function onRequestGet(context: EventContext<Env, 'id', unknown>) {
  const userId = context.params.id;
  const user = await context.env.DB.prepare(
    'SELECT id, name, email FROM users WHERE id = ?',
  ).bind(userId).first();
  if (!user) return new Response('Not Found', { status: 404 });
  return Response.json(user);
}

export async function onRequestDelete(context: EventContext<Env, 'id', unknown>) {
  await context.env.DB.prepare('DELETE FROM users WHERE id = ?').bind(context.params.id).run();
  return new Response(null, { status: 204 });
}
```

#### Middleware (auth + request id)

```typescript
// functions/_middleware.ts
export const onRequest: PagesFunction<Env>[] = [
  // Request id (runs first)
  async ({ request, next }) => {
    const requestId = crypto.randomUUID();
    const res = await next();
    res.headers.set('x-request-id', requestId);
    return res;
  },
  // Auth (runs second)
  async ({ request, env, next, data }) => {
    if (request.url.includes('/api/public')) return next();   // skip auth
    const token = request.headers.get('authorization')?.replace('Bearer ', '');
    const session = token ? await env.KV.get(`session:${token}`, 'json') : null;
    if (!session) return new Response('Unauthorized', { status: 401 });
    data.session = session;                                   // attach to context for downstream
    return next();
  },
];
```

#### `_routes.json` (production essential)

```jsonc
// public/_routes.json
{
  "version": 1,
  "include": ["/api/*", "/auth/*"],
  "exclude": ["/assets/*", "/favicon.ico", "/robots.txt"]
}
```

Only paths under `include` walk the functions tree; everything else serves from static assets directly. Without this, every asset 404 invokes a function.

#### Anti-patterns

- One `functions/[[catchall]].ts` that hand-parses URLs. Defeats file routing; loses Cloudflare's automatic param extraction; harder to review.
- Middleware that throws without catching. Pages returns a 500 with no context. Wrap in `try/catch` and return a structured error.
- Calling `fetch(context.request)` from middleware. Creates an infinite loop through the routing tree. Use `await next()`.
- No `_routes.json` on a SPA. Functions intercept asset 404s; you waste invocations and your bundle requests hit cold-start latency.
- Storing per-request state in module scope. Same Worker-isolate caveat applies - module scope is shared across requests, sometimes across deployments.

## D1 Database

```javascript
// Create table
await env.DB.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

// Insert
const result = await env.DB.prepare(
  'INSERT INTO users (name, email) VALUES (?, ?)'
).bind('Alice', 'alice@acme.com').run();

// Query
const { results } = await env.DB.prepare(
  'SELECT * FROM users WHERE email = ?'
).bind('alice@acme.com').all();

// Transaction (batch)
const batch = [
  env.DB.prepare('INSERT INTO users (name, email) VALUES (?, ?)').bind('Bob', 'bob@acme.com'),
  env.DB.prepare('INSERT INTO users (name, email) VALUES (?, ?)').bind('Carol', 'carol@acme.com'),
];
await env.DB.batch(batch);
```

## R2 Storage

```javascript
// Put object
await env.BUCKET.put('file.txt', 'Hello World', {
  httpMetadata: {
    contentType: 'text/plain'
  }
});

// Get object
const object = await env.BUCKET.get('file.txt');
if (object) {
  const text = await object.text();
  return new Response(text);
}

// List objects
const list = await env.BUCKET.list({ prefix: 'uploads/' });
for (const object of list.objects) {
  console.log(object.key);
}
```

### R2 Event Notifications

Push notifications to a Queue when objects are created, deleted, or restored in a bucket. The consumer is a regular Queues consumer (see [Queues](#queues)) - same idempotency, batching, DLQ rules apply.

#### Core rules

- **Filter at the rule level, not in the consumer.** A rule scoped to `{ prefix: 'uploads/', suffix: '.jpg' }` only fires for that subset. Filtering in the consumer wastes invocations.
- **Idempotent consumers, always.** Queues guarantees at-least-once delivery. A retried event re-fetches an object whose content has not changed; design for that.
- **Event payload does not include the object body.** It includes bucket, key, size, etag, eventTime, eventType. Fetch the body in the consumer if you need it.
- **One rule per `{bucket, eventType, prefix, suffix}` tuple.** Multiple rules can target the same queue; the consumer dispatches by `event.eventType`.
- **Order is best-effort, not guaranteed.** A delete event for an object may arrive before the create event under load. Design state machines to be insensitive to reordering or to handle it explicitly.

#### Create the rule

```bash
wrangler r2 bucket notification create my-bucket \
  --event-type object-create \
  --event-type object-delete \
  --prefix uploads/ \
  --suffix .jpg \
  --queue uploads-events
```

Or via the dashboard: R2 -> bucket -> Settings -> Event Notifications.

#### Consumer

```typescript
interface R2EventMessage {
  account: string;
  bucket: string;
  eventTime: string;        // ISO 8601
  action: 'PutObject' | 'CopyObject' | 'CompleteMultipartUpload' | 'DeleteObject' | 'LifecycleDeletion';
  object: { key: string; size: number; eTag: string };
}

export default {
  async queue(batch: MessageBatch<R2EventMessage>, env: Env) {
    await Promise.allSettled(
      batch.messages.map(async (msg) => {
        try {
          if (msg.body.action === 'PutObject' || msg.body.action === 'CopyObject') {
            const object = await env.BUCKET.get(msg.body.object.key);
            if (!object) { msg.ack(); return; }      // already deleted; nothing to do
            await processUpload(env, msg.body.object.key, object);
          }
          if (msg.body.action === 'DeleteObject') {
            await cleanupMetadata(env, msg.body.object.key);
          }
          msg.ack();
        } catch (err) {
          isTransient(err) ? msg.retry({ delaySeconds: 2 ** msg.attempts }) : msg.ack();
        }
      }),
    );
  },
};
```

#### Anti-patterns

- Assuming strict ordering. The delete may arrive before the create under load; build state machines that handle that.
- Fetching the object body in the handler without an idempotency guard. A retry re-fetches and re-processes; tag the processing with the object's etag and skip if you've seen the same etag already.
- One broad rule (`prefix: ''`) that fires for every key, then filtering in the consumer. Burns Queue invocations. Add the prefix/suffix to the rule.
- Forgetting that lifecycle deletions also fire `DeleteObject`. If your consumer treats DeleteObject as "user-initiated", lifecycle expiry events will misroute.

## Workflows

Durable, replayable, multi-step orchestration on top of Workers. Use for long-running business logic (minutes to days), fan-out/fan-in pipelines, and agent-driven processes. As of Workflows v2 (May 2026), limits are 50k concurrent instances, 300 new/sec/account, and 2M queued per workflow - v2 is a transparent backend rearchitecture with no API changes.

### Core rules

- **Every side effect goes inside `step.do`.** Anything outside a step runs again on every replay, including HTTP calls, DB writes, and queue sends - that is the most common Workflows footgun.
- **Steps must be deterministic and idempotent.** A step that retries must be safe to run again. Use idempotency keys for external POSTs; use `upsert`/`merge` for DB writes.
- **Step return values must be JSON-serializable.** They are persisted and rehydrated on replay. No `Date`, `Map`, `Set`, class instances, or `undefined` properties - convert to plain objects/strings/numbers.
- **Use `step.sleep` / `step.sleepUntil` for waits**, never `setTimeout` or `await new Promise(r => setTimeout(r, ...))`. Only `step.sleep` survives hibernation.
- **Use `step.waitForEvent` for external triggers** (human approval, webhook callbacks) instead of polling loops.
- **Tune `retries` per step.** Cheap idempotent steps can retry aggressively; expensive or non-idempotent steps should retry few times with backoff and surface failures.

### Basic workflow

```typescript
import { WorkflowEntrypoint, WorkflowStep, WorkflowEvent } from 'cloudflare:workers';

type Params = { userId: string; orderId: string };

export class OrderWorkflow extends WorkflowEntrypoint<Env, Params> {
  async run(event: WorkflowEvent<Params>, step: WorkflowStep) {
    const { userId, orderId } = event.payload;

    const order = await step.do('fetch-order', async () => {
      const res = await fetch(`${this.env.API_URL}/orders/${orderId}`);
      if (!res.ok) throw new Error(`fetch-order failed: ${res.status}`);
      return res.json();
    });

    const charge = await step.do(
      'charge-payment',
      {
        retries: { limit: 3, delay: '10 seconds', backoff: 'exponential' },
        timeout: '30 seconds',
      },
      async () => {
        return await chargeIdempotent(this.env, {
          idempotencyKey: `order-${orderId}`,
          amount: order.total,
        });
      },
    );

    await step.sleep('cool-off', '5 minutes');

    await step.do('record-fulfillment', async () => {
      await this.env.DB.prepare(
        'INSERT INTO fulfillments (order_id, charge_id) VALUES (?, ?) ON CONFLICT(order_id) DO NOTHING',
      ).bind(orderId, charge.id).run();
    });

    return { orderId, chargeId: charge.id };
  }
}
```

### Parallel steps (fan-out / fan-in)

```typescript
const [user, inventory, pricing] = await Promise.all([
  step.do('fetch-user', () => fetchUser(userId)),
  step.do('fetch-inventory', () => fetchInventory(orderId)),
  step.do('fetch-pricing', () => fetchPricing(orderId)),
]);
```

Each child step is independently checkpointed and retried; the parent step does not need its own `step.do` wrapper.

### Waiting on external events

```typescript
const approval = await step.waitForEvent<{ approved: boolean }>(
  'await-manager-approval',
  { type: 'manager-approval', timeout: '24 hours' },
);

if (!approval.approved) return { status: 'rejected' };
```

Send the event from another Worker via `instance.sendEvent({ type, payload })`.

### wrangler.toml binding

```toml
[[workflows]]
name = "order-workflow"
binding = "ORDER_WORKFLOW"
class_name = "OrderWorkflow"
```

### Triggering instances

```typescript
const instance = await env.ORDER_WORKFLOW.create({
  id: `order-${orderId}`,          // optional but recommended - enables idempotent creation
  params: { userId, orderId },
});

const status = await instance.status();   // 'queued' | 'running' | 'paused' | 'complete' | 'errored'
```

### Anti-patterns

- Putting `await fetch(...)` or `await db.query(...)` directly in `run()` outside a `step.do`. Replay will re-execute it.
- Returning a class instance, `Map`, or `Date` from a step. It will not survive serialization.
- Using `setTimeout` or wall-clock `Date.now()` comparisons for delays. Use `step.sleep` and `step.sleepUntil`.
- One giant step that does ten things. Split - each `step.do` is your retry boundary and your replay savepoint.
- Polling an external system in a loop. Use `step.waitForEvent` or `step.sleep` between attempts.

## Queues

Pull-based async message delivery between Workers. Use for decoupling producers from consumers, smoothing bursty traffic, and fan-out to multiple consumers. Choose Queues when you need fire-and-forget delivery with retries; choose Workflows when you need durable multi-step state.

### Core rules

- **Consumers must be idempotent.** Messages can be redelivered after `retry()`, batch failure, or consumer crash. Use a dedupe key (message id, business id) and a "seen" check.
- **Acknowledge explicitly.** Call `msg.ack()` on success and `msg.retry()` on transient failure. Unacked messages are retried after the visibility timeout.
- **Configure a Dead Letter Queue.** Without a DLQ, poison messages cycle forever until they expire. With a DLQ, set `max_retries` modestly (3-5) and inspect the DLQ.
- **Tune batch size to consumer cost.** Small batches (1-10) for expensive per-message work; large batches (50-100) for cheap work. `max_batch_timeout` bounds latency.
- **Never block the batch on one slow message.** Process in `Promise.allSettled` and ack/retry each independently.

### Producer

```typescript
// Single message
await env.MY_QUEUE.send({ userId, event: 'signup' }, { contentType: 'json' });

// Batch send (up to 100 per call)
await env.MY_QUEUE.sendBatch([
  { body: { userId: 'a' } },
  { body: { userId: 'b' }, delaySeconds: 30 },
]);
```

### Consumer

```typescript
interface SignupEvent { userId: string; event: string }

export default {
  async queue(batch: MessageBatch<SignupEvent>, env: Env, ctx: ExecutionContext) {
    const results = await Promise.allSettled(
      batch.messages.map(async (msg) => {
        try {
          await processSignup(env, msg.body);
          msg.ack();
        } catch (err) {
          // Transient → retry with backoff. Permanent → ack to drop, or let DLQ catch it.
          if (isTransient(err)) {
            msg.retry({ delaySeconds: 2 ** msg.attempts });
          } else {
            msg.ack();   // or throw to send to DLQ via max_retries
          }
        }
      }),
    );
  },
};
```

### wrangler.toml

```toml
[[queues.producers]]
queue = "signups"
binding = "MY_QUEUE"

[[queues.consumers]]
queue = "signups"
max_batch_size = 25
max_batch_timeout = 5      # seconds
max_retries = 4
dead_letter_queue = "signups-dlq"
```

### Anti-patterns

- Calling `batch.ackAll()` at the top of the handler. You will lose messages whose processing failed.
- Re-sending to the same queue on failure instead of using `msg.retry()`. You lose backoff and retry counting.
- Per-message database connections in a 50-message batch. Open one connection per invocation, reuse across the batch.
- No DLQ. Poison messages will burn your retry budget forever.

## KV Storage

```javascript
// Put value
await env.KV.put('key', 'value', {
  expirationTtl: 3600  // 1 hour
});

// Put JSON
await env.KV.put('user:123', JSON.stringify({ name: 'Alice' }));

// Get value
const value = await env.KV.get('key');

// Get JSON
const user = await env.KV.get('user:123', 'json');

// Delete
await env.KV.delete('key');
```

## Hyperdrive

Connection pool + query cache that lets Workers talk to external Postgres / MySQL databases without paying per-request TCP handshake cost. Use Hyperdrive any time you need to query a regional Postgres/MySQL from Workers - direct connections from Workers are slow and burn your DB's connection limit.

### Core rules

- **Do not cache the client in module scope.** Workers isolates are short-lived and globally distributed; a module-scope client leaks across isolates and breaks on cold starts. Create the client per request.
- **Always close with `ctx.waitUntil(sql.end())`.** Closing inside the request path blocks the response. `waitUntil` lets the response return while the connection unwinds.
- **Keep the in-Worker pool small.** `max: 5` or less per invocation - Hyperdrive itself is the real pool. Your Worker is just one client.
- **Mark read-only queries.** Hyperdrive caches `SELECT` results when safe; queries with `SET` / writes / transactions are never cached. Use `cacheTtl` and `cacheTables` in the dashboard to tune.
- **Never put DB credentials in `wrangler.toml` or code.** The connection string lives in the Hyperdrive config (set via `wrangler hyperdrive create` or dashboard). The binding only exposes `connectionString` at runtime.

### Usage with `postgres.js`

```typescript
import postgres from 'postgres';

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext) {
    const sql = postgres(env.HYPERDRIVE.connectionString, {
      max: 5,
      fetch_types: false,   // skip type introspection - saves a round-trip per cold start
    });

    try {
      const users = await sql`
        SELECT id, email FROM users WHERE active = true LIMIT 10
      `;
      return Response.json(users);
    } finally {
      ctx.waitUntil(sql.end());
    }
  },
};
```

### wrangler.toml

```toml
[[hyperdrive]]
binding = "HYPERDRIVE"
id = "<hyperdrive-config-id-from-wrangler-create>"
```

Create the config first:

```bash
wrangler hyperdrive create my-db --connection-string="postgres://user:pass@host:5432/dbname"
```

### Anti-patterns

- Top-level `const sql = postgres(...)`. The client survives across requests in an isolate and across deployments unpredictably - connections leak.
- `await sql.end()` before `return new Response(...)`. Blocks the response on connection teardown.
- Connecting directly to Postgres from a Worker, bypassing Hyperdrive. Each request opens a fresh TCP+TLS connection - latency and connection-limit exhaustion follow.
- Putting the connection string in `[vars]`. It is a credential - keep it in the Hyperdrive config, not in source-controlled config.

## Workers AI

Run inference on Cloudflare's GPU fleet from Workers. Bind the `AI` namespace and call `env.AI.run(model, input)`. Pair with Vectorize for embeddings + RAG, and AI Gateway for caching, rate limiting, and per-app analytics.

### Core rules

- **Set a timeout on every `AI.run`.** Model calls can hang; use `AbortSignal.timeout(15_000)` or similar and surface a fallback response.
- **Stream long generations.** Set `stream: true` and pipe the `ReadableStream` directly into a `Response` with `content-type: text/event-stream`. Buffering a 4k-token response into memory burns CPU time and worsens TTFB.
- **Route through AI Gateway.** Bind `[[ai]]` to a gateway slug - you get free request logging, response caching, retry, and per-model cost visibility. Bypassing the gateway means flying blind in production.
- **Pin the model version.** Use `@cf/meta/llama-3.3-70b-instruct`, not `@cf/meta/llama`. Model aliases shift and break prompts silently.
- **Never trust model output.** Treat it as untrusted user input - sanitize before storing, escape before rendering, validate before passing to other systems.

### Text generation

```typescript
const result = await env.AI.run(
  '@cf/meta/llama-3.3-70b-instruct',
  {
    messages: [
      { role: 'system', content: 'You are a concise assistant.' },
      { role: 'user', content: userPrompt },
    ],
    max_tokens: 512,
    temperature: 0.2,
  },
  { gateway: { id: 'my-app', skipCache: false } },
);
```

### Streaming response

```typescript
const stream = await env.AI.run('@cf/meta/llama-3.3-70b-instruct', {
  messages: [...],
  stream: true,
});

return new Response(stream, {
  headers: { 'content-type': 'text/event-stream' },
});
```

### Embeddings + Vectorize

```typescript
const { data } = await env.AI.run('@cf/baai/bge-base-en-v1.5', {
  text: ['First document', 'Second document'],
});

await env.VECTORIZE.upsert([
  { id: 'doc-1', values: data[0], metadata: { source: 'kb' } },
  { id: 'doc-2', values: data[1], metadata: { source: 'kb' } },
]);

// At query time
const [queryVec] = (await env.AI.run('@cf/baai/bge-base-en-v1.5', { text: [query] })).data;
const matches = await env.VECTORIZE.query(queryVec, { topK: 5, returnMetadata: true });
```

### wrangler.toml

```toml
[ai]
binding = "AI"

[[vectorize]]
binding = "VECTORIZE"
index_name = "kb-index"
```

### Anti-patterns

- Calling `AI.run` inside a tight loop without `Promise.all`. Inference is the bottleneck - batch where the model supports it (embeddings) or fan out concurrently.
- Returning raw model output as HTML. Always escape; LLMs can be prompt-injected into emitting `<script>` tags.
- Re-embedding the same text on every request. Cache embeddings in KV / D1 / Vectorize keyed by a content hash.
- Using `temperature: 0` and assuming determinism. Workers AI is not bit-for-bit deterministic across hardware - assume some variance even at temp 0.

## Vectorize

Managed vector database. Use for RAG, semantic search, recommendations, deduplication, and any "find me items similar to this one" pattern. Pairs naturally with Workers AI embeddings (`@cf/baai/bge-*`) but accepts vectors from any model.

### Core rules

- **Dimension is fixed at index creation.** Match it to your embedding model (768 for bge-base-en-v1.5, 1024 for bge-large, 1536 for OpenAI text-embedding-3-small, 3072 for text-embedding-3-large). Cannot change after creation - wrong dimension means rebuilding the index.
- **Declare metadata indexes upfront.** Filterable metadata fields must be configured at creation (or added later via `wrangler vectorize create-metadata-index`). Filtering on undeclared fields falls back to a full-index scan.
- **Distance metric is fixed at creation.** `cosine` (default; what most embedding models target), `euclidean`, or `dot-product`. Match the model's training metric.
- **`returnValues: false` is the default; keep it that way.** The vector itself is rarely useful downstream; metadata and id are. Returning values wastes bandwidth.
- **Batch upserts up to 1000 vectors per call.** Use this aggressively for ingest; single-vector upserts dominate cost on large corpora.
- **Use namespaces for tenant isolation.** `namespace: 'tenant-X'` is the cheap, correct way to keep tenants in the same index without cross-leak. Cheaper than separate indexes; queries scoped to a namespace skip other tenants entirely.
- **Cache the content-hash -> vector-id mapping.** Re-embedding the same content because you didn't check is the #1 source of wasted Workers AI cost.

### Create an index

```bash
wrangler vectorize create kb-index \
  --dimensions 768 \
  --metric cosine

# Declare filterable metadata fields BEFORE ingesting
wrangler vectorize create-metadata-index kb-index \
  --property-name source --type string
wrangler vectorize create-metadata-index kb-index \
  --property-name tenant_id --type string
wrangler vectorize create-metadata-index kb-index \
  --property-name created_at --type number
```

### Ingest pipeline (with content-hash dedup)

```typescript
import { sha256 } from './hash';   // wraps crypto.subtle.digest

async function ingest(env: Env, docs: { id: string; text: string; source: string; tenantId: string }[]) {
  const toEmbed: typeof docs = [];
  for (const doc of docs) {
    const hash = await sha256(doc.text);
    const existingId = await env.KV.get(`embed-hash:${hash}`);
    if (existingId) continue;                         // already embedded under existingId
    toEmbed.push(doc);
  }
  if (toEmbed.length === 0) return;

  // Embed in one call (model supports batching)
  const { data } = await env.AI.run('@cf/baai/bge-base-en-v1.5', {
    text: toEmbed.map((d) => d.text),
  });

  // Upsert in one call (Vectorize supports up to 1000)
  await env.VECTORIZE.upsert(
    toEmbed.map((doc, i) => ({
      id: doc.id,
      values: data[i],
      metadata: {
        source: doc.source,
        tenant_id: doc.tenantId,
        created_at: Date.now(),
      },
              })),
    { namespace: toEmbed[0].tenantId },             // per-tenant namespace
  );

  // Update the dedup cache
  await Promise.all(toEmbed.map(async (doc) => {
    const hash = await sha256(doc.text);
    await env.KV.put(`embed-hash:${hash}`, doc.id);
  }));
}
```

### Query (hybrid: vector + metadata filter)

```typescript
const [queryVec] = (await env.AI.run('@cf/baai/bge-base-en-v1.5', { text: [userQuery] })).data;

const matches = await env.VECTORIZE.query(queryVec, {
  topK: 10,
  namespace: tenantId,
  returnValues: false,
  returnMetadata: 'all',
  filter: { source: { $eq: 'kb' }, created_at: { $gte: thirtyDaysAgo } },
});

// matches.matches[]: { id, score, metadata }
```

### wrangler.toml binding

```toml
[[vectorize]]
binding = "VECTORIZE"
index_name = "kb-index"
```

### Anti-patterns

- Creating the index with the wrong dimension. Wrong dimension means rebuilding from scratch later; double-check against the model's output shape before `wrangler vectorize create`.
- Not declaring metadata indexes. Every filter that touches an undeclared field becomes a full-index scan - linear in corpus size, eventually unusable.
- Using a single global index for multi-tenant data without namespaces. Queries leak across tenants; performance degrades as the index grows.
- Embedding the same content on every request. Hash the input, cache the vector id; only re-embed on content change.
- Single-vector upserts in a loop. Batch to 1000 per call; the per-call overhead dominates otherwise.
- Returning `values: true` by default. Doubles response size for almost no downstream benefit.

## AI Gateway

A universal proxy in front of model providers (Workers AI, OpenAI, Anthropic, Google, Azure OpenAI, Mistral, HuggingFace, Replicate, Bedrock, Vertex, etc.) that adds caching, retries, rate limiting, fallback chains, per-app analytics, audit logging, and prompt/response tracing. The Gateway works whether the caller is a Worker or an external app - it's a URL you POST to.

### Core rules

- **Route every model call through Gateway**, even direct OpenAI / Anthropic calls. The observability is free and you'll need it the first time a model misbehaves or the bill spikes.
- **Set caching TTL per route, not globally.** Semantically cacheable requests (deterministic retrievals, structured-output classification without temperature) get hours of TTL; chat requests usually get zero or seconds.
- **Configure a fallback chain in the dashboard.** Gateway can try OpenAI -> Anthropic -> Workers AI on provider failure without you reimplementing it in app code.
- **Use Gateway tokens for non-Workers callers.** Mint a Gateway token scoped to one gateway + provider; do not share account API keys across services. Tokens are revocable per-gateway.
- **Inspect costs in the dashboard.** Per-model, per-app, per-gateway spend with request counts is the closest thing to a single source of truth for AI bills.
- **Never cache error responses.** Gateway caches by default only on 2xx; double-check the cache configuration if you've custom-tuned it.

### Call from a Worker (gateway-bound)

```typescript
// wrangler.toml has [ai] binding = "AI" with default gateway routing
const result = await env.AI.run(
  '@cf/meta/llama-3.3-70b-instruct',
  { messages: [...], max_tokens: 512 },
  { gateway: { id: 'my-app', skipCache: false, cacheTtl: 3600 } },
);
```

### Call from Node / Python via the universal endpoint

The Gateway exposes a REST endpoint that mirrors the upstream provider's API exactly - drop-in replacement for the provider's URL.

```bash
# OpenAI through Gateway
curl https://gateway.ai.cloudflare.com/v1/<account-id>/<gateway-slug>/openai/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5","messages":[{"role":"user","content":"hi"}]}'

# Anthropic through Gateway
curl https://gateway.ai.cloudflare.com/v1/<account-id>/<gateway-slug>/anthropic/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-5","max_tokens":1024,"messages":[{"role":"user","content":"hi"}]}'
```

Same payload, same response shape, same SDK - just swap the base URL. The SDK call sites do not change.

### Fallback chain (dashboard-configured, but visible in the request)

When configured, Gateway tries the chain on provider error. Set the chain ordering in the Gateway settings and Gateway emits `cf-gateway-fallback-used` headers on the response when a fallback fired.

### Authenticated Gateway tokens

```bash
# Mint a token in the dashboard scoped to one gateway + one provider
# Use that token instead of bare provider keys for non-Worker callers
curl https://gateway.ai.cloudflare.com/v1/<account-id>/<gateway-slug>/openai/chat/completions \
  -H "cf-aig-authorization: Bearer <gateway-token>" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

Revoking the gateway token cuts off that caller's access without rotating the provider's key.

### Per-request observability metadata

Tag requests with custom metadata so the dashboard can slice by tenant / feature / experiment.

```typescript
const result = await env.AI.run(
  '@cf/meta/llama-3.3-70b-instruct',
  { messages: [...] },
  {
    gateway: {
      id: 'my-app',
      metadata: { tenant_id: tenantId, feature: 'support-summarizer', experiment: 'v2' },
    },
  },
);
```

### Anti-patterns

- Calling OpenAI / Anthropic directly when Gateway is available. You've lost observability, retries, fallback, caching, and per-app cost visibility for no upside.
- Caching error responses. A transient 500 cached for an hour becomes a fake outage. Only cache 2xx; let errors hit the upstream every time so they fix themselves.
- Aggressive TTL on chat completions. Stale completions reach users; trust degrades. Reserve caching for deterministic retrievals.
- Gateway tokens checked into source control. Same rules as any API key - vault, CI secret, or `wrangler secret put`.
- One gateway slug for ten unrelated apps. Use one slug per application so you can scope tokens, see per-app costs, and configure per-app caching independently.
- Skipping the metadata tagging. Without `metadata.tenant_id` (or similar) the cost dashboard is a single undifferentiated total - you can't answer "which tenant drove this month's bill".
