# TypeScript Advanced Patterns

## Strict tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    
    "declaration": true,
    "sourceMap": true,
    "esModuleInterop": true,
    "skipLibCheck": false,
    
    "outDir": "./dist",
    "rootDir": "./src",
    
    "paths": {
      "@/*": ["src/*"],
      "@components/*": ["src/components/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

## Generics

```typescript
// Generic function
function identity<T>(arg: T): T {
  return arg;
}

// Generic with constraint
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// Generic class
class DataStore<T> {
  private items: T[] = [];
  
  add(item: T): void {
    this.items.push(item);
  }
  
  get(index: number): T | undefined {
    return this.items[index];
  }
}
```

## Mapped Types

```typescript
// Make all properties optional and nullable
type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object
    ? DeepPartial<T[P]>
    : T[P] | null;
};

// Extract keys of a certain type
type StringKeys<T> = {
  [K in keyof T]: T[K] extends string ? K : never;
}[keyof T];

// Create enum-like object from literal union
type Status = 'pending' | 'active' | 'complete';
type StatusRecord = Record<Status, string>;
```

## Conditional Types

```typescript
// Extract return type
type ReturnOf<T> = T extends (...args: never[]) => infer R ? R : never;

// Exclude null and undefined
type NonNullable<T> = T extends null | undefined ? never : T;

// Extract array element type
type ArrayElement<T> = T extends (infer E)[] ? E : never;
```

## Template Literal Types

```typescript
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';
type Endpoint = '/users' | '/products' | '/orders';

type ApiRoute = `${HttpMethod} ${Endpoint}`;
// 'GET /users' | 'GET /products' | 'POST /users' | ...

type EventName<T extends string> = `on${Capitalize<T>}`;
// EventName<'click'> = 'onClick'
```

## Type Guards

```typescript
// Custom type guard
function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'email' in value
  );
}

// Assertion function
function assertIsDefined<T>(value: T): asserts value is NonNullable<T> {
  if (value === undefined || value === null) {
    throw new Error('Value must be defined');
  }
}

// Usage
if (isUser(data)) {
  console.log(data.email);  // Type-safe
}
```

## Branded Types

```typescript
// Prevent mixing up similar types
type UserId = string & { readonly brand: unique symbol };
type OrderId = string & { readonly brand: unique symbol };

function createUserId(id: string): UserId {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-/.test(id)) {
    throw new Error('Invalid user ID format');
  }
  return id as UserId;
}

function createOrderId(id: string): OrderId {
  if (!/^order-[a-z0-9-]+$/.test(id)) {
    throw new Error('Invalid order ID format');
  }
  return id as OrderId;
}

function getUser(id: UserId): User {
  // ...
}

const userId = createUserId('123');
const orderId = createOrderId('order-456');

getUser(userId);   // ✅ OK
getUser(orderId);  // ❌ Type error
```

## Result Type Pattern

```typescript
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

function parseJson(json: string): Result<unknown> {
  try {
    return { ok: true, value: JSON.parse(json) };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e : new Error(String(e)) };
  }
}

// Usage
const result = parseJson(jsonString);
if (result.ok && isUser(result.value)) {
  console.log(result.value.name);
} else {
  console.error(result.ok ? 'Invalid user payload' : result.error.message);
}
```

## Zod Schema Validation

```typescript
import { z } from 'zod';

const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  age: z.number().min(0).max(150),
  role: z.enum(['admin', 'user', 'guest']),
});

type User = z.infer<typeof UserSchema>;

function validateUser(data: unknown): User {
  return UserSchema.parse(data);
}
```

## Error Handling

```typescript
class AppError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode: number = 500
  ) {
    super(message);
    this.name = 'AppError';
  }
}

class NotFoundError extends AppError {
  constructor(resource: string) {
    super(`${resource} not found`, 'NOT_FOUND', 404);
  }
}

// Usage
throw new NotFoundError('User');
```

## React Component Patterns

```typescript
// Props with children
interface ButtonProps {
  variant: 'primary' | 'secondary';
  onClick?: () => void;
  children: React.ReactNode;
}

// Generic component
interface ListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
}

function List<T>({ items, renderItem }: ListProps<T>) {
  return <ul>{items.map(renderItem)}</ul>;
}

// Discriminated union for state
type LoadingState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };
```
