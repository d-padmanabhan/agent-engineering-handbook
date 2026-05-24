# Common Pitfalls

Failure modes observed across many Cloudflare Workers teams - not specific to any one team. Organized by symptom.

---

## Service Worker syntax in new code

**Symptom:** new Worker uses `addEventListener("fetch", ...)`; can't access bindings via `env`; can't use `WorkerEntrypoint` / RPC / named entrypoints.

**Cause:** older docs and StackOverflow examples still show Service Worker syntax. It's deprecated for new development.

**Fix:**

```typescript
// WRONG (Service Worker - deprecated)
addEventListener("fetch", (event) => {
  event.respondWith(handleRequest(event.request));
});

// RIGHT (Module Worker)
export default {
  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    return handleRequest(req, env, ctx);
  },
} satisfies ExportedHandler<Env>;
```

**Migration of existing Service Workers:** Cloudflare has an official [migration guide](https://developers.cloudflare.com/workers/reference/migrate-to-module-workers/). The migration is mechanical: bindings move from global scope to `env`; event listeners move to typed handler methods.

---

## Top-level `await` blocking startup

**Symptom:** cold-start regression after a recent change; first request after deploy takes 500ms+ when it used to take 50ms.

**Cause:** added `await fetch(...)` or `await initialize()` at module scope. This runs on every cold start, blocks the response, and consumes a subrequest.

**Fix - lazy init pattern:**

```typescript
// WRONG: blocks every cold start
const config = await fetch("https://config.example.com/").then((r) => r.json());

export default {
  async fetch(req, env, ctx) {
    return new Response(JSON.stringify(config));
  },
};

// RIGHT: fetch on first request, cache in module scope
let cachedConfig: Config | null = null;
async function getConfig(env: Env): Promise<Config> {
  if (cachedConfig) return cachedConfig;
  cachedConfig = await env.CONFIG_KV.get<Config>("config", "json");
  return cachedConfig!;
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const config = await getConfig(env);
    return new Response(JSON.stringify(config));
  },
} satisfies ExportedHandler<Env>;
```

**Better still:** make the config a binding (KV with the JSON, fetched via `env.CONFIG_KV.get()` per request - KV reads are cached at the edge and add ~1ms to subsequent same-isolate requests).

---

## Module-scope mutable state polluting requests

**Symptom:** intermittent state bleed between unrelated users' requests; reproducible only under load; logs show one user's data in another user's response occasionally.

**Cause:** mutated module-scope variable. Workers reuse isolates across requests within the same isolate's lifetime; module-scope `let` persists.

**Fix:** never use mutable module scope for per-request state. Move it into the handler:

```typescript
// WRONG: shared state across requests in this isolate
let currentUser: User | null = null;
export default {
  async fetch(req, env) {
    currentUser = await authenticate(req, env);   // ← mutated by every request
    return new Response(JSON.stringify(currentUser));
  },
};

// RIGHT: per-request state in the handler scope
export default {
  async fetch(req, env): Promise<Response> {
    const currentUser = await authenticate(req, env);
    return new Response(JSON.stringify(currentUser));
  },
} satisfies ExportedHandler<Env>;
```

For shared caches (e.g., a JWT verification key cache), use `const` + an immutable map keyed by something stable (issuer URL, key ID), not `let`-mutable.

---

## `void` fire-and-forget gets cancelled

**Symptom:** analytics events / async log writes / KV writes never land in production; works fine locally.

**Cause:** async work issued after the response was returned. The Worker terminates as soon as the response is sent; pending Promises get cancelled.

**Fix:** wrap fire-and-forget work in `ctx.waitUntil()`:

```typescript
// WRONG: cancelled when the Worker terminates
export default {
  async fetch(req, env, ctx): Promise<Response> {
    const response = new Response("ok");
    void env.ANALYTICS.writeDataPoint({ blobs: ["request"] });   // ← cancelled
    return response;
  },
};

// RIGHT: ctx.waitUntil extends the Worker's lifetime until the Promise settles
export default {
  async fetch(req, env, ctx): Promise<Response> {
    const response = new Response("ok");
    ctx.waitUntil(env.ANALYTICS.writeDataPoint({ blobs: ["request"] }));
    return response;
  },
} satisfies ExportedHandler<Env>;
```

**Cases to wrap in `waitUntil`:** analytics writes, async logs, KV / R2 / D1 writes that aren't on the critical path, cache.put(), Queue sends, telemetry exports.

---

## `Response` body consumed twice

**Symptom:** `TypeError: Body already used` after reading a response body once.

**Cause:** `Response` bodies are single-consumer streams. Reading once consumes them; second read throws.

**Fix - `response.clone()` before consuming:**

```typescript
// WRONG
const resp = await fetch(upstream);
const text = await resp.text();        // consumes body
const json = JSON.parse(text);         // OK
await cache.put(req, resp);            // FAILS - body already used

// RIGHT - clone before storing
const resp = await fetch(upstream);
ctx.waitUntil(cache.put(req, resp.clone()));   // clone for cache
const json = await resp.json();                 // consume the original
```

---

## Subrequest budget exhausted in a loop

**Symptom:** `Workers Runtime Exception: Too many subrequests` after a feature shipped that iterates over user-controlled input.

**Cause:** loop with one subrequest per iteration; user-controlled length means unbounded blast radius.

**Fix - batch where the API supports it:**

```typescript
// WRONG: one subrequest per item
for (const id of ids) {
  await env.DB.prepare("INSERT INTO events (id, ...) VALUES (?, ...)").bind(id).run();
}

// RIGHT: one subrequest for N statements
const stmts = ids.map((id) =>
  env.DB.prepare("INSERT INTO events (id, ...) VALUES (?, ...)").bind(id),
);
await env.DB.batch(stmts);   // single subrequest
```

For KV (no bulk write API), the alternatives are: write through R2 (one object with N keys serialized), or use D1, or use a Durable Object that batches internally.

---

## Secrets leaked to logs / error messages / response bodies

**Symptom:** secret appears in Workers Logs, error response, or browser network tab.

**Cause:** any of:

```typescript
console.log("env:", env);                        // logs all bindings including secrets
throw new Error(`DB error: ${env.DB_PASSWORD}`); // secret in thrown error
return new Response(JSON.stringify(env));        // secret in response body
```

**Fix:** never include secrets in any logging / error / response path. Validate this in PR review.

```typescript
// RIGHT: log only non-sensitive context
console.log("Request handled", {
  method: req.method,
  path: new URL(req.url).pathname,
  userId: ctx.user?.id,
});

// RIGHT: error messages don't include credentials
throw new Error("Database connection failed");   // generic; details in structured log
```

**Defense-in-depth:** add an ESLint rule or CI check that grep's for `env.<SECRET_NAME>` in source files outside the binding-use sites.

---

## Service binding URL hardcoded instead of using the binding

**Symptom:** Worker A calls Worker B's public `<name>.workers.dev` URL; slow; counts as outbound HTTP; doesn't honor version overrides.

**Fix:** declare a Service Binding in `wrangler.jsonc` and call via `env.BINDING.fetch()` or RPC:

```typescript
// WRONG
const resp = await fetch("https://auth-worker.example.workers.dev/validate", {...});

// RIGHT (HTTP-style service binding)
const resp = await env.AUTH.fetch(new Request("https://internal/validate", {...}));

// BEST (RPC via WorkerEntrypoint - typed, faster)
const user = await env.AUTH.validateToken(token);
```

---

## `compatibility_date` set to today's date on every deploy

**Symptom:** subtle behavior changes between deploys; tests pass before deploy, fail after.

**Cause:** bumping `compatibility_date` is a runtime behavior change. Doing it automatically (e.g., a Renovate bot or a `date +%F` in CI) means every deploy could change runtime semantics without code review.

**Fix:** set `compatibility_date` deliberately, reviewed against the [Runtime API changelog](https://developers.cloudflare.com/workers/configuration/compatibility-dates/). Bump it as a separate PR with the changelog summary in the description.

---

## `worker-configuration.d.ts` stale

**Symptom:** TypeScript errors after adding a binding to `wrangler.jsonc`; `env.NEW_BINDING` shows as `any` or undefined.

**Cause:** generated types file wasn't regenerated.

**Fix:**

```bash
wrangler types        # regenerates worker-configuration.d.ts from wrangler.jsonc
```

Add this as a `predev` and `prebuild` hook in `package.json` so it runs automatically:

```jsonc
"scripts": {
  "predev": "wrangler types",
  "prebuild": "wrangler types",
  "types": "wrangler types"
}
```

---

## Drift between Dashboard and `wrangler.jsonc`

**Symptom:** `wrangler deploy` reverts a change someone made in the Dashboard; or the Dashboard shows different bindings than `wrangler.jsonc` declares.

**Cause:** someone edited the Worker via Dashboard "Edit code" or Dashboard bindings UI while `wrangler.jsonc` was the source of truth.

**Fix:** the wrangler config is the source of truth. Detect drift by running `wrangler deploy --dry-run` periodically (e.g., a daily CI check); the dry-run plan should be empty if no source changes are pending. If the dry-run plan is non-empty unexpectedly, someone edited via Dashboard.

The break-glass exception is `wrangler secret put` from CI (or interactively) for secret rotation - that's the only steady-state Dashboard / API write pattern that doesn't go through `wrangler deploy`.

---

## Tests pass locally, fail in CI

**Common causes:**

1. **Different `compatibility_date`** between local dev and CI (check `wrangler.jsonc` matches; CI hasn't pulled latest).
2. **`worker-configuration.d.ts` stale in CI** (add `wrangler types` to the CI pipeline before `tsc --noEmit`).
3. **`.dev.vars` referenced in tests but not provided in CI** (use Vitest's `miniflare.bindings` instead of relying on `.dev.vars`).
4. **Outbound network in tests** (use `fetchMock.disableNetConnect()` to catch this; CI may not have network parity).

---

## Cron Trigger or Queue consumer never fires in production

**Symptom:** `wrangler.jsonc` declares a cron / queue consumer; deploys cleanly; doesn't execute.

**Causes:**

1. **The handler isn't defined.** A Cron Trigger needs `scheduled(event, env, ctx)`; a Queue consumer needs `queue(batch, env, ctx)`. Both must be in the same Worker that's listed in the trigger / consumer config.
2. **The Worker has multiple entry points and the cron is bound to a different one.** Verify with `wrangler triggers list`.
3. **Cron expression syntax error.** Cloudflare uses standard cron expressions but with their own validation. Test in the Dashboard or via `wrangler triggers list` after deploy.

---

## Cross-cutting prevention

The `401-cloudflare-workers.mdc` reviewer checklist is the single most effective preventive control. Most of the above pitfalls are caught by it:

- Module Workers syntax (catches Service Worker)
- `satisfies ExportedHandler<Env>` (catches typed Env)
- No secrets in logs (catches secret leakage)
- `ctx.waitUntil` for fire-and-forget (catches cancelled Promises)
- Named bindings only (catches public-URL Worker-to-Worker calls)
- No top-level await / module-scope state (catches cold-start regressions + state pollution)
- `compatibility_date` set and stable (catches the auto-bump trap)
- `wrangler types` + `tsc --noEmit` clean (catches stale generated types)
- `wrangler deploy --dry-run` clean (catches Dashboard drift)

Make the checklist a PR template in the repo so it auto-populates.
