---
name: typescript-javascript
description: TypeScript and JavaScript development standards for modern web and Node.js development. Covers strict TypeScript configuration, type safety patterns, ESM modules, async/await, testing with Jest/Vitest, and security best practices. Use when working with .ts, .tsx, .js, .mjs files, package.json, tsconfig.json, or when asking about TypeScript/JavaScript best practices.
---

# TypeScript & JavaScript Development

## Guiding Principles

1. **Type Safety**: Leverage strict mode, avoid `any`, use discriminated unions
2. **Explicit Over Implicit**: Prefer explicit types for clarity and maintainability
3. **Modern Defaults**: ESM, const/let, async/await, optional chaining
4. **Security First**: Never use `eval`, sanitize HTML, validate inputs

## Quick Reference

| Aspect | TypeScript | JavaScript |
|--------|------------|------------|
| **Package Manager** | `pnpm` preferred | `pnpm` preferred |
| **Module System** | ES Modules | ES Modules + `// @ts-check` |
| **Linting** | `eslint --max-warnings=0` | `eslint --max-warnings=0` |
| **Formatting** | Prettier | Prettier |
| **Types** | Strict mode | JSDoc types |

## Non-Negotiables

### NN-1: Validate at trust boundaries

Static types do not validate runtime data. Treat HTTP bodies, responses, webhooks, queue messages, localStorage/sessionStorage, environment variables, CLI args, and JSON files as `unknown` until validated with Zod or an explicit type guard.

Reject:

- `JSON.parse(raw) as T`
- `await response.json() as T`
- unchecked property access on remote JSON
- `as any` or double assertions (`value as unknown as T`)

### NN-2: Fetch/API calls require timeout + status check + schema validation

Every service/network `fetch` must include a timeout, check `response.ok`, and validate the JSON shape before returning typed data.

```typescript
import { z } from 'zod';

async function fetchJson<T>(
  url: string,
  schema: z.ZodType<T>,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    signal: options.signal ?? AbortSignal.timeout(5_000),
    headers: { Accept: 'application/json', ...options.headers },
  });
  if (!response.ok) {
    throw new Error(`request failed: HTTP ${response.status}`);
  }
  return schema.parse(await response.json());
}
```

### NN-3: Production servers are hardened by default

Node/Express/Fastify services need bounded request bodies, explicit CORS, security headers, request IDs, structured logging, generic 5xx responses, and graceful shutdown. Do not use direct `app.listen(...)` examples for production services without retaining and closing the server.

### NN-4: Package manager and runtime are pinned

Declare `packageManager` and Node engine policy in `package.json`; CI uses Corepack and the declared package manager.

```json
{
  "packageManager": "pnpm@10.0.0",
  "engines": { "node": ">=22" }
}
```

## Critical Patterns

```typescript
// 1. Use strict equality
if (value === 0) { }        // ✅ GOOD
if (value == 0) { }         // ❌ BAD

// 2. Handle Promise rejections
fetchData().catch(err => console.error(err));  // ✅ GOOD

// 3. Optional chaining and nullish coalescing
const name = user?.profile?.name ?? 'Guest';  // ✅ GOOD

// 4. Use Set/Map for lookups
const seen = new Set();     // ✅ GOOD (O(1))
const seen = [];            // ❌ BAD (O(n))

// 5. Never use eval or new Function
eval(userInput);            // ❌ NEVER DO THIS

// 6. Sanitize HTML
element.textContent = userInput;  // ✅ GOOD
element.innerHTML = userInput;    // ❌ BAD (XSS)
```

## TypeScript Configuration

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noUncheckedIndexedAccess": true,
    "esModuleInterop": true,
    "skipLibCheck": false
  }
}
```

## Avoid `any` - Use Proper Types

```typescript
// ❌ BAD - Loses all type safety
function processData(data: any): any {
  return data.value;
}

// ✅ GOOD - Generic type
function processData<T>(data: T): T {
  return data;
}

// ✅ GOOD - Unknown for truly unknown types
function processData(data: unknown): string {
  if (typeof data === 'object' && data !== null && 'value' in data) {
    return String((data as { value: unknown }).value);
  }
  throw new Error('Invalid data');
}
```

## Discriminated Unions

```typescript
type SuccessResponse = {
  status: 'success';
  data: { id: string; name: string };
};

type ErrorResponse = {
  status: 'error';
  error: { code: number; message: string };
};

type ApiResponse = SuccessResponse | ErrorResponse;

function handleResponse(response: ApiResponse): void {
  if (response.status === 'success') {
    console.log(response.data.id);  // Type-safe
  } else {
    console.log(response.error.message);  // Type-safe
  }
}
```

## Utility Types

```typescript
interface User {
  id: string;
  name: string;
  email: string;
  password: string;
}

type UserUpdate = Partial<User>;           // All optional
type UserCredentials = Pick<User, 'email' | 'password'>;
type UserPublic = Omit<User, 'password'>;  // Exclude password
type RequiredUser = Required<User>;        // All required
type ReadonlyUser = Readonly<User>;        // Immutable
```

## Async Patterns

```typescript
// Parallel execution
const [users, products] = await Promise.all([
  fetchUsers(),
  fetchProducts()
]);

// Handle partial failures
const results = await Promise.allSettled([
  fetchUsers(),
  fetchProducts()
]);

results.forEach(result => {
  if (result.status === 'fulfilled') {
    console.log(result.value);
  } else {
    console.error(result.reason);
  }
});
```

## Security Rules (Mandatory)

- Never use `eval`, `new Function`, or unsanitized `innerHTML`
- Use `textContent` for DOM insertion
- Validate and sanitize all external inputs
- Do not log secrets/tokens/PII
- Use parameterized queries; no string-built queries
- Enforce HTTPS; secure cookies (HttpOnly, SameSite)

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Functions/Variables | camelCase | `fetchUserData` |
| Classes/Interfaces | PascalCase | `UserService` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| Types | PascalCase | `ApiResponse` |

## Detailed References

- **TypeScript Patterns**: See [references/typescript-patterns.md](references/typescript-patterns.md) for advanced types, generics, mapped types
- **JavaScript Patterns**: See [references/javascript-patterns.md](references/javascript-patterns.md) for JSDoc, ESM, performance
