# Hono Patterns + RPC via WorkerEntrypoint

Hono is the de facto router for Cloudflare Workers in TypeScript. It's edge-runtime-aware, typed, fast (~3 KB gzipped), and supports middleware composition, OpenAPI generation, and the patterns below.

For Worker-to-Worker calls, RPC via `WorkerEntrypoint` is the modern path (replaces HTTP service bindings for most cases).

---

## When to use Hono vs alternatives

| Choice | When |
|---|---|
| **Native `URL` + `switch`** | 1-3 routes, no middleware, smallest possible bundle |
| **Hono** | Many routes, middleware, typed env, OpenAPI, modern feel |
| **itty-router** | Tiny router, fewer features than Hono; older choice |
| **RPC via `WorkerEntrypoint`** | Worker-to-Worker only (no HTTP needed) |

---

## Hono setup

```bash
npm install hono
npm install --save-dev @hono/zod-validator zod   # for typed request validation
```

```typescript
// src/worker.ts
import { Hono } from "hono";
import { logger } from "hono/logger";
import { cors } from "hono/cors";
import { secureHeaders } from "hono/secure-headers";
import { HTTPException } from "hono/http-exception";

type Variables = {
  user?: { id: string; orgId: string };
};

const app = new Hono<{ Bindings: Env; Variables: Variables }>();

// Middleware (runs top-down for every matching request)
app.use("*", logger());
app.use("*", secureHeaders());
app.use("/api/*", cors({ origin: ["https://app.example.com"], credentials: true }));

// Routes
app.get("/health", (c) => c.text("ok"));

app.get("/api/users/:id", async (c) => {
  const id = c.req.param("id");
  const user = await c.env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(id).first();
  if (!user) throw new HTTPException(404, { message: "User not found" });
  return c.json(user);
});

// Error boundary (Hono-thrown HTTPException + uncaught errors)
app.onError((err, c) => {
  if (err instanceof HTTPException) {
    return err.getResponse();
  }
  console.error("Uncaught error", err);   // shows up in Workers Logs
  return c.json({ error: "Internal Server Error" }, 500);
});

// 404 fallback
app.notFound((c) => c.json({ error: "Not Found" }, 404));

export default app satisfies ExportedHandler<Env>;
```

---

## Typed env via generics

The `Hono<{ Bindings: Env; Variables: Vars }>` generic is what makes Hono pleasant on Workers. `c.env` is typed; `c.set("user", ...)` and `c.get("user")` are typed via `Variables`.

```typescript
type Variables = {
  user: { id: string; orgId: string };
  requestId: string;
};

const app = new Hono<{ Bindings: Env; Variables: Variables }>();

app.use("*", async (c, next) => {
  c.set("requestId", crypto.randomUUID());
  await next();
});

app.get("/me", (c) => {
  const user = c.get("user");   // typed as { id: string; orgId: string }
  return c.json({ user, requestId: c.get("requestId") });
});
```

---

## Request validation with Zod

```typescript
import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";

const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
  orgId: z.string().uuid(),
});

const app = new Hono<{ Bindings: Env }>();

app.post(
  "/api/users",
  zValidator("json", CreateUserSchema),   // validates body; 400 on failure
  async (c) => {
    const body = c.req.valid("json");   // typed as the schema's inferred type
    const result = await c.env.DB.prepare(
      "INSERT INTO users (email, name, org_id) VALUES (?, ?, ?) RETURNING id",
    ).bind(body.email, body.name, body.orgId).first();
    return c.json(result, 201);
  },
);
```

`zValidator` covers `json`, `query`, `param`, `header`, `cookie`, and `form`. The validated value is accessed via `c.req.valid("json")` and is fully typed.

---

## Middleware composition

```typescript
import { Hono, type MiddlewareHandler } from "hono";

// Custom auth middleware
const requireAuth: MiddlewareHandler<{ Bindings: Env; Variables: Variables }> =
  async (c, next) => {
    const token = c.req.header("Authorization")?.replace("Bearer ", "");
    if (!token) {
      return c.json({ error: "Unauthorized" }, 401);
    }
    const user = await validateToken(token, c.env);
    if (!user) {
      return c.json({ error: "Unauthorized" }, 401);
    }
    c.set("user", user);
    await next();
  };

// Apply to a route group
const api = new Hono<{ Bindings: Env; Variables: Variables }>();
api.use("*", requireAuth);
api.get("/profile", (c) => c.json(c.get("user")));

app.route("/api", api);
```

---

## OpenAPI generation (typed routes → spec → typed client)

Use `@hono/zod-openapi` to generate OpenAPI 3 specs from your route definitions:

```bash
npm install @hono/zod-openapi
```

```typescript
import { OpenAPIHono, createRoute, z } from "@hono/zod-openapi";

const app = new OpenAPIHono<{ Bindings: Env }>();

const route = createRoute({
  method: "get",
  path: "/api/users/{id}",
  request: {
    params: z.object({ id: z.string().uuid() }),
  },
  responses: {
    200: {
      content: { "application/json": { schema: UserSchema } },
      description: "User found",
    },
    404: { description: "User not found" },
  },
});

app.openapi(route, async (c) => {
  const { id } = c.req.valid("param");
  const user = await c.env.DB.prepare("SELECT * FROM users WHERE id = ?").bind(id).first<User>();
  if (!user) return c.json({ error: "Not Found" }, 404);
  return c.json(user, 200);
});

// Serve the OpenAPI spec
app.doc("/openapi.json", { openapi: "3.0.0", info: { title: "API", version: "1.0.0" } });

export default app satisfies ExportedHandler<Env>;
```

Pair with [Scalar](https://github.com/scalar/scalar) or [Swagger UI](https://github.com/swagger-api/swagger-ui) for an in-Worker docs page.

---

## RPC via WorkerEntrypoint

For Worker-to-Worker calls on the same Cloudflare account, **RPC is faster and typed** compared to HTTP service bindings. You declare a class extending `WorkerEntrypoint` and the methods become directly callable from other Workers.

### Producer (Worker B exposes RPC methods)

```typescript
// worker-b/src/worker.ts
import { WorkerEntrypoint } from "cloudflare:workers";

export default class AuthService extends WorkerEntrypoint<Env> {
  // Required: even RPC-only Workers need a fetch handler.
  // Return 404 to make accidental HTTP access fail loudly.
  async fetch(): Promise<Response> {
    return new Response("This Worker is RPC-only", { status: 404 });
  }

  // Public RPC method - callable from other Workers
  async validateToken(token: string): Promise<{ userId: string; orgId: string } | null> {
    const session = await this.env.SESSION_KV.get<Session>(`token:${token}`, "json");
    if (!session || session.expiresAt < Date.now()) return null;
    return { userId: session.userId, orgId: session.orgId };
  }

  async createSession(userId: string, orgId: string): Promise<string> {
    const token = crypto.randomUUID();
    await this.env.SESSION_KV.put(
      `token:${token}`,
      JSON.stringify({ userId, orgId, expiresAt: Date.now() + 3600_000 }),
      { expirationTtl: 3600 },
    );
    return token;
  }
}
```

`wrangler.jsonc` (Worker B):

```jsonc
{
  "name": "auth-service",
  "main": "src/worker.ts",
  "compatibility_date": "2026-04-01"
}
```

### Consumer (Worker A calls Worker B via Service Binding)

`wrangler.jsonc` (Worker A):

```jsonc
{
  "name": "api",
  "main": "src/worker.ts",
  "compatibility_date": "2026-04-01",
  "services": [
    {
      "binding": "AUTH",
      "service": "auth-service"
      // omit `entrypoint` to bind to the default export
    }
  ]
}
```

Worker A code:

```typescript
import { Hono } from "hono";

const app = new Hono<{ Bindings: Env }>();

app.get("/api/me", async (c) => {
  const token = c.req.header("Authorization")?.replace("Bearer ", "");
  if (!token) return c.json({ error: "Unauthorized" }, 401);

  // RPC call - typed return value (TypeScript infers from the AuthService class shape via types)
  const user = await c.env.AUTH.validateToken(token);
  if (!user) return c.json({ error: "Unauthorized" }, 401);

  return c.json(user);
});

export default app satisfies ExportedHandler<Env>;
```

### Named entrypoints (multiple RPC classes per Worker)

A single Worker can export multiple `WorkerEntrypoint` classes for role-based RPC surfaces:

```typescript
// worker-b/src/worker.ts
import { WorkerEntrypoint } from "cloudflare:workers";

export default class extends WorkerEntrypoint<Env> {
  async fetch(): Promise<Response> {
    return new Response("404", { status: 404 });
  }
  async publicMethod() { /* ... */ }
}

export class AdminEntrypoint extends WorkerEntrypoint<Env> {
  async deleteUser(userId: string) { /* admin-only operation */ }
}
```

Bind explicitly:

```jsonc
"services": [
  { "binding": "AUTH", "service": "auth-service" },                      // default export
  { "binding": "ADMIN", "service": "auth-service", "entrypoint": "AdminEntrypoint" }
]
```

### RPC limits and gotchas

- **Max serialized payload:** 32 MB. Use `ReadableStream` for larger.
- **Class is stateless:** a new instance per invocation; use Durable Objects for state.
- **Smart Placement is ignored for RPC calls:** the called Worker runs locally on the same machine as the caller.
- **Version overrides via `Cloudflare-Workers-Version-Overrides` header are only supported on `fetch()`-based service binding calls**, not RPC method calls.

---

## Hono + RPC combination

Hono handles HTTP; RPC handles internal Worker-to-Worker. They compose:

```typescript
// API Worker - HTTP via Hono + RPC via WorkerEntrypoint (rare; both default-exported is mutually exclusive)
// More common: the API Worker uses Hono for HTTP, and calls OTHER Workers via RPC.

import { Hono } from "hono";

const app = new Hono<{ Bindings: Env }>();

app.post("/api/users", async (c) => {
  const { email, name } = await c.req.json();

  // RPC call to user-service Worker
  const user = await c.env.USER_SERVICE.createUser({ email, name });

  // RPC call to email-service Worker (async; doesn't block response)
  c.executionCtx.waitUntil(
    c.env.EMAIL_SERVICE.sendWelcome({ to: email, userId: user.id }),
  );

  return c.json(user, 201);
});

export default app satisfies ExportedHandler<Env>;
```
