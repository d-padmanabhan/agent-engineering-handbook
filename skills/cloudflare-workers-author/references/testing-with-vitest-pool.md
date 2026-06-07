# Testing with `@cloudflare/vitest-pool-workers`

The canonical testing path for Cloudflare Workers. Runs your tests inside the Workers runtime via Miniflare, with bindings mocked or real (your choice), HMR for fast reruns, and isolated per-test storage.

**Versions (as of 2026):**

- `@cloudflare/vitest-pool-workers` v0.16.x stable
- Requires `vitest` 4.1+ and `@vitest/runner` 4.1+
- Wrangler 4.x (bundled with vitest-pool-workers as a dep)

**Don't use** `unstable_dev` for new tests - it's deprecated; vitest-pool-workers replaces it.

> [!IMPORTANT]
> **v0.16 removed `defineWorkersConfig` and the `@cloudflare/vitest-pool-workers/config` subpath.** Configure with the `cloudflareTest()` Vite plugin instead (shown below). If you see `Missing "./config" specifier in "@cloudflare/vitest-pool-workers"`, you're on 0.16+ with the old config import.

---

## Setup

### Install

```bash
npm install --save-dev @cloudflare/vitest-pool-workers vitest
```

### `vitest.config.ts`

```typescript
import { cloudflareTest } from "@cloudflare/vitest-pool-workers";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.jsonc" },
      // Optional: override or add miniflare config (takes precedence over wrangler.jsonc)
      // miniflare: {
      //   // e.g., mock service bindings for tests
      //   // serviceBindings: { AUTH: (req) => new Response("mocked") }
      // },
    }),
  ],
});
```

### `tsconfig.json` for tests

Create a tests-specific tsconfig (e.g., `test/tsconfig.json`) or extend the main one:

```jsonc
{
  "extends": "../tsconfig.json",
  "compilerOptions": {
    // `/types` declares the `cloudflare:test` module; the Workers runtime
    // globals come from the included worker-configuration.d.ts.
    "types": ["@cloudflare/vitest-pool-workers/types"]
  },
  "include": [
    "./**/*.ts",
    "../worker-configuration.d.ts"
  ]
}
```

`@cloudflare/vitest-pool-workers/types` provides types for the `cloudflare:test` module (the `SELF` fetcher, `env`, `runInDurableObject`, etc.).

---

## Unit tests

Import the Worker handler directly and call it with mocked env:

```typescript
// test/handler.unit.test.ts
import { describe, it, expect } from "vitest";
import worker from "../src/worker";

describe("worker.fetch", () => {
  it("returns 200 for /health", async () => {
    const req = new Request("https://example.com/health");
    const env = {} as Env;   // mock env (empty here; populate as needed)
    const ctx = new ExecutionContext();
    const response = await worker.fetch!(req, env, ctx);
    expect(response.status).toBe(200);
    expect(await response.text()).toBe("ok");
  });

  it("returns 404 for unknown paths", async () => {
    const req = new Request("https://example.com/nope");
    const env = {} as Env;
    const ctx = new ExecutionContext();
    const response = await worker.fetch!(req, env, ctx);
    expect(response.status).toBe(404);
  });
});
```

`ExecutionContext` is provided by the Workers runtime in tests; you don't need to construct a mock manually.

---

## Integration tests (in-process via `SELF.fetch`)

`SELF` is a service binding to your default-exported Worker. Calls route through the real handler, with all bindings resolved per your `wrangler.jsonc`.

```typescript
// test/handler.integration.test.ts
import { describe, it, expect } from "vitest";
import { SELF } from "cloudflare:test";

describe("integration", () => {
  it("creates a user and persists to D1", async () => {
    const createResp = await SELF.fetch("https://example.com/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer test-token" },
      body: JSON.stringify({ email: "alice@example.com", name: "Alice", orgId: "org-1" }),
    });
    expect(createResp.status).toBe(201);
    const created = (await createResp.json()) as { id: string };

    const fetchResp = await SELF.fetch(`https://example.com/api/users/${created.id}`, {
      headers: { "Authorization": "Bearer test-token" },
    });
    expect(fetchResp.status).toBe(200);
    const fetched = (await fetchResp.json()) as { email: string };
    expect(fetched.email).toBe("alice@example.com");
  });
});
```

---

## Accessing bindings directly in tests

The `env` import from `cloudflare:test` is your Worker's resolved env, useful for setup / teardown / assertions:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { env, SELF } from "cloudflare:test";

describe("D1 user creation", () => {
  beforeEach(async () => {
    // Clean slate per test (each test gets isolated storage anyway, but explicit is fine)
    await env.DB.exec("DELETE FROM users");
  });

  it("creates and reads via API + verifies via direct DB query", async () => {
    await SELF.fetch("https://example.com/api/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "alice@example.com", name: "Alice", orgId: "org-1" }),
    });

    // Direct DB assertion bypassing the Worker
    const { results } = await env.DB.prepare("SELECT email FROM users WHERE email = ?")
      .bind("alice@example.com").all();
    expect(results).toHaveLength(1);
  });
});
```

---

## Isolated per-test storage

By default, each test runs against fresh storage (KV, D1, R2, DO). Cleanup is automatic. If you want shared state across tests in a file, use `beforeAll` to seed it explicitly.

```typescript
import { beforeAll } from "vitest";
import { env } from "cloudflare:test";

beforeAll(async () => {
  await env.DB.exec(`
    INSERT INTO users (id, email, name, org_id) VALUES
      ('u1', 'alice@example.com', 'Alice', 'org-1'),
      ('u2', 'bob@example.com', 'Bob', 'org-1')
  `);
});
```

---

## Testing Durable Objects

```typescript
import { describe, it, expect } from "vitest";
import { env, runInDurableObject } from "cloudflare:test";
import { Room } from "../src/room";

describe("Room DO", () => {
  it("increments counter", async () => {
    const id = env.ROOM.idFromName("test-room");
    const stub = env.ROOM.get(id);

    // Direct method call (RPC-style)
    const result = await stub.fetch(new Request("https://example.com/"));
    expect(await result.text()).toBe("1");

    const result2 = await stub.fetch(new Request("https://example.com/"));
    expect(await result2.text()).toBe("2");
  });

  it("can access DO internals via runInDurableObject", async () => {
    const id = env.ROOM.idFromName("test-room-2");
    const stub = env.ROOM.get(id);

    // runInDurableObject lets you assert on internal state directly
    await runInDurableObject(stub, async (instance: Room, state) => {
      await state.storage.put("count", 42);
    });

    const response = await stub.fetch(new Request("https://example.com/"));
    expect(await response.text()).toBe("43");   // 42 + 1
  });
});
```

---

## Mocking outbound `fetch()` calls

Use Miniflare's `serviceBindings` or Vitest's built-in mocking. The cleanest pattern for outbound HTTP is `fetchMock` from `cloudflare:test`:

```typescript
import { describe, it, expect, beforeAll, afterEach } from "vitest";
import { fetchMock } from "cloudflare:test";
import { SELF } from "cloudflare:test";

beforeAll(() => {
  fetchMock.activate();
  fetchMock.disableNetConnect();   // fail any unmocked outbound fetch
});

afterEach(() => {
  fetchMock.assertNoPendingInterceptors();
});

describe("upstream call", () => {
  it("handles upstream 500 gracefully", async () => {
    fetchMock.get("https://upstream.example.com")
      .intercept({ path: "/api/data" })
      .reply(500, "Internal Server Error");

    const resp = await SELF.fetch("https://example.com/api/proxy");
    expect(resp.status).toBe(502);   // your Worker should translate upstream 500 to 502
  });
});
```

---

## Test scripts

In `package.json`:

```jsonc
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "test:ui": "vitest --ui"
  }
}
```

---

## Anti-patterns specific to Workers testing

- **Using `unstable_dev`** (deprecated; the `vitest-pool-workers` path replaces it).
- **Testing the Worker against a deployed environment** (slow; flaky; shared state across runs). Use `vitest-pool-workers` for local in-runtime tests.
- **Mocking `Request` / `Response` with libraries built for Node.js** (Workers uses standard `Request` / `Response` constructors; just use them).
- **Sharing storage across tests** without explicit `beforeAll` seeding (creates order dependencies; vitest-pool-workers gives you isolated storage per test for a reason).
- **Not running `wrangler types` before tests** (the typed `Env` interface drifts from `wrangler.jsonc` bindings; tests pass locally but break in CI).
- **Skipping integration tests because unit tests are easier** (most Worker bugs are at the binding boundary - KV TTL, D1 prepared-statement binding, R2 metadata - which only integration tests catch).
