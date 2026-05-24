# Project Bootstrap

A copy-paste-ready setup for a new Cloudflare Worker project in TypeScript using the modern toolchain.

**Conventions:**

- Wrangler v4.x (any 4.x; Wrangler 3.91+ supports `wrangler.jsonc`, but 4.x is the current major).
- TypeScript strict mode.
- Vitest 4.1+ with `@cloudflare/vitest-pool-workers` v0.13+ for testing (covered in `testing-with-vitest-pool.md`).
- `wrangler types` generates `worker-configuration.d.ts` from your `wrangler.jsonc` bindings.

---

## 1. `package.json`

```jsonc
{
  "name": "<your-worker>",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "types": "wrangler types",
    "build": "wrangler deploy --dry-run --outdir=dist",
    "dev": "wrangler dev",
    "deploy": "wrangler deploy",
    "deploy:staging": "wrangler deploy --env staging",
    "deploy:upload": "wrangler versions upload",
    "test": "vitest run",
    "test:watch": "vitest",
    "typecheck": "tsc --noEmit"
  },
  "devDependencies": {
    "@cloudflare/vitest-pool-workers": "^0.13.0",
    "@cloudflare/workers-types": "^4.20260401.0",
    "typescript": "^5.6.0",
    "vitest": "^4.1.0",
    "wrangler": "^4.0.0"
  },
  "dependencies": {
    "hono": "^4.6.0"
  }
}
```

Notes:

- `"type": "module"` is required - Workers ESM is the only supported module format for new code.
- `@cloudflare/workers-types` version matches your `compatibility_date` (e.g., `^4.20260401.0` pairs with `compatibility_date: "2026-04-01"`). The runtime types evolve; pin to a date.
- Don't add `hono` if you're using native `URL` + `switch` routing for a 1-3 route Worker.

---

## 2. `wrangler.jsonc`

```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "<your-worker>",
  "main": "src/worker.ts",
  "compatibility_date": "2026-04-01",
  "compatibility_flags": [
    // Include only if you actually import from node:* modules. Increases bundle size.
    // "nodejs_compat"
  ],

  // Smart Placement: Cloudflare auto-places the Worker near its dependencies
  // (e.g., D1 / origin server). Useful for chatty Workers; not for simple HTTP.
  "placement": { "mode": "smart" },

  // Observability: enable Workers Logs (persistent push-style logs).
  "observability": {
    "enabled": true,
    "head_sampling_rate": 1.0   // 1.0 = log every request; reduce for high-traffic Workers
  },

  // Vars: NON-SENSITIVE configuration only. Secrets go through `wrangler secret put`.
  "vars": {
    "ENVIRONMENT": "production",
    "LOG_LEVEL": "info"
  },

  // Bindings (declare the resources this Worker needs; populate after creating them)
  "kv_namespaces": [
    // { "binding": "SESSION_KV", "id": "<kv-namespace-id>" }
  ],
  "d1_databases": [
    // { "binding": "DB", "database_name": "production", "database_id": "<d1-id>" }
  ],
  "r2_buckets": [
    // { "binding": "ASSETS", "bucket_name": "production-assets" }
  ],
  "services": [
    // { "binding": "AUTH", "service": "auth-worker", "entrypoint": "AuthEntrypoint" }
  ],

  // Per-environment overrides
  "env": {
    "staging": {
      "vars": { "ENVIRONMENT": "staging", "LOG_LEVEL": "debug" },
      "kv_namespaces": [
        // { "binding": "SESSION_KV", "id": "<staging-kv-id>" }
      ]
    }
  }
}
```

Notes:

- The `$schema` reference gives you JSONC autocomplete and validation in editors that support it.
- `compatibility_date` is a contract with the runtime; bump it deliberately, not on every deploy.
- `placement: smart` is free; enable it unless you have a reason not to.
- `observability.enabled = true` ships logs to the Cloudflare Logs system (queryable in the dashboard and API). Without it, you only get `wrangler tail` for live streaming.

---

## 3. `tsconfig.json`

```jsonc
{
  "compilerOptions": {
    "target": "ESNext",
    "lib": ["ESNext"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "types": [
      "@cloudflare/workers-types/2026-04-01"
    ],
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    "noEmit": true
  },
  "include": [
    "src/**/*",
    "worker-configuration.d.ts"
  ],
  "exclude": ["node_modules", "dist", ".wrangler"]
}
```

Notes:

- `types: ["@cloudflare/workers-types/2026-04-01"]` - the date suffix is REQUIRED to match `compatibility_date`. Without it, you get the latest types but may miss runtime APIs gated behind a flag.
- `verbatimModuleSyntax: true` enforces type-only imports (`import type { Foo } from "..."`) - catches accidental runtime imports of types.
- `include: ["src/**/*", "worker-configuration.d.ts"]` - the generated bindings types file MUST be included so `Env` is in scope everywhere.

---

## 4. `src/worker.ts` (minimal default-export HTTP Worker)

```typescript
// The `Env` interface comes from worker-configuration.d.ts (generated by `wrangler types`).
// Do not hand-author this interface; it will drift from wrangler.jsonc.

export default {
  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(req.url);

    if (url.pathname === "/health") {
      return new Response("ok", { status: 200 });
    }

    return new Response("Not Found", { status: 404 });
  },
} satisfies ExportedHandler<Env>;
```

For Hono-based routing, replace the handler body with a Hono app - see `hono-patterns.md`.

---

## 5. `.dev.vars` (local-only secrets; MUST be in `.gitignore`)

```bash
# .dev.vars - local development secrets (dotenv format)
# Do NOT commit. Production secrets via `wrangler secret put NAME`.
API_KEY=<your-local-test-key>
JWT_SIGNING_KEY=<your-local-jwt-key>
```

Then in `.gitignore`:

```
.dev.vars
.dev.vars.*
.wrangler/
worker-configuration.d.ts
node_modules/
dist/
```

(Whether to commit `worker-configuration.d.ts` is a per-repo choice. Committing it surfaces type changes in PRs but creates merge conflicts. Generating in CI keeps the repo clean but you need a `predev` hook to regenerate before `wrangler dev`. Pick one and document.)

---

## 6. Initial commands

```bash
# Install
npm install

# Generate the typed Env from wrangler.jsonc bindings
npm run types

# Type-check
npm run typecheck

# Local dev (Miniflare-backed; .dev.vars loaded automatically)
npm run dev

# Dry-run a deploy (catches binding misconfigurations without uploading)
npm run build

# Deploy
npm run deploy
```

---

## 7. Creating bindings (one-time setup per resource)

After bootstrap, create the actual resources and add their IDs to `wrangler.jsonc`:

```bash
# KV namespace
wrangler kv namespace create SESSION_KV
# Outputs: { binding = "SESSION_KV", id = "..." } - paste into wrangler.jsonc

# D1 database
wrangler d1 create production
# Outputs the database_id - paste into wrangler.jsonc

# R2 bucket
wrangler r2 bucket create production-assets

# Queue
wrangler queues create ingest

# Secret (prompts for value; CI: pipe from a CI secret)
wrangler secret put API_KEY
echo "$VALUE" | wrangler secret put API_KEY   # CI pattern
```

After adding bindings, **always re-run `npm run types`** so the generated `Env` interface includes them.

---

## 8. Smart Placement: when to enable

`placement: { mode: "smart" }` tells Cloudflare to run your Worker near its dependencies (D1, origin servers, Hyperdrive-backed Postgres). This reduces latency when the Worker makes many subrequests to a single backend.

**Enable when:**

- The Worker calls D1 in a tight loop (D1 is single-region)
- The Worker calls Hyperdrive (the Postgres pool is regional)
- The Worker calls a specific origin server repeatedly (e.g., a single origin in `us-east-1`)
- The Worker is part of a multi-Worker chain via Service Bindings

**Don't enable when:**

- The Worker is a simple HTTP proxy with no backend chatter
- The Worker fans out to many regions (smart placement would pick one region; you'd lose the multi-region benefit)
- The Worker uses RPC via Service Bindings (smart placement is ignored for RPC calls; the binding runs locally)

Smart Placement is free and reversible - turn it off if measurements show it's not helping.
