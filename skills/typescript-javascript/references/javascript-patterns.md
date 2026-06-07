# JavaScript Patterns

## JSDoc Type Annotations

Enable TypeScript checking in JavaScript files:

```javascript
// @ts-check

/**
 * Fetches user data from the API.
 * @param {string} userId - The user's unique identifier
 * @returns {Promise<{id: string, name: string, email: string}>}
 * @throws {Error} If the user is not found
 */
async function fetchUser(userId) {
  const response = await fetch(`/api/users/${encodeURIComponent(userId)}`, {
    signal: AbortSignal.timeout(5_000),
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`User ${userId} not found`);
  }
  const data = await response.json();
  if (
    typeof data !== 'object' ||
    data === null ||
    typeof data.id !== 'string' ||
    typeof data.name !== 'string' ||
    typeof data.email !== 'string'
  ) {
    throw new TypeError('Invalid user response');
  }
  return data;
}

/**
 * @typedef {Object} User
 * @property {string} id
 * @property {string} name
 * @property {string} email
 */

/**
 * @param {User[]} users
 * @returns {Map<string, User>}
 */
function indexUsers(users) {
  return new Map(users.map(u => [u.id, u]));
}
```

## ES Modules

```javascript
// Named exports
export function fetchData() { }
export const API_URL = 'https://api.acme.com';

// Default export
export default class UserService { }

// Import
import UserService, { fetchData, API_URL } from './user-service.js';

// Dynamic import (code splitting)
const module = await import('./heavy-module.js');
```

## Async Patterns

```javascript
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

// Race (first to complete)
const fastest = await Promise.race([
  fetchFromPrimary(),
  fetchFromBackup()
]);

// Sequential with reduce
const results = await items.reduce(async (prevPromise, item) => {
  const acc = await prevPromise;
  const result = await processItem(item);
  return [...acc, result];
}, Promise.resolve([]));
```

## Error Handling

```javascript
// Structured logging
const logger = {
  info: (msg, meta = {}) => console.log(JSON.stringify({
    level: 'info',
    ts: new Date().toISOString(),
    msg,
    ...meta
  })),
  error: (msg, err) => console.error(JSON.stringify({
    level: 'error',
    ts: new Date().toISOString(),
    msg,
    error: err?.message,
    stack: err?.stack
  }))
};

// Wrap risky operations
async function fetchData(url) {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(5_000) });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    if (typeof data !== 'object' || data === null) {
      throw new TypeError('Invalid JSON response');
    }
    return data;
  } catch (error) {
    logger.error('Failed to fetch data', error);
    throw error;
  }
}
```

## Performance Patterns

```javascript
// Use Set for O(1) lookups
const allowedIds = new Set(['id1', 'id2', 'id3']);
if (allowedIds.has(userId)) {
  allow();
}

// Avoid O(n²) - use Set for unique values
const unique = [...new Set(array)];

// Debounce for noisy events
function debounce(fn, delay) {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

// Throttle for rate limiting
function throttle(fn, limit) {
  let inThrottle;
  return (...args) => {
    if (!inThrottle) {
      fn(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}
```

## Modern JavaScript Features

```javascript
// Destructuring
const { name, age = 0 } = user;
const [first, ...rest] = items;

// Spread operator
const merged = { ...defaults, ...overrides };
const combined = [...array1, ...array2];

// Optional chaining
const street = user?.address?.street;
const result = callback?.();

// Nullish coalescing
const value = input ?? defaultValue;  // Only for null/undefined
const value = input || defaultValue;  // For any falsy value

// Object shorthand
const x = 1, y = 2;
const point = { x, y };  // { x: 1, y: 2 }

// Computed property names
const key = 'dynamicKey';
const obj = { [key]: 'value' };
```

## Array Methods

```javascript
// map - transform each element
const doubled = numbers.map(n => n * 2);

// filter - select elements
const adults = users.filter(u => u.age >= 18);

// reduce - accumulate to single value
const total = items.reduce((sum, item) => sum + item.price, 0);

// find - first matching element
const admin = users.find(u => u.role === 'admin');

// some/every - boolean checks
const hasAdult = users.some(u => u.age >= 18);
const allAdults = users.every(u => u.age >= 18);

// flatMap - map + flatten
const allTags = posts.flatMap(p => p.tags);
```

## Classes

```javascript
class UserService {
  #apiUrl;  // Private field
  
  constructor(apiUrl) {
    this.#apiUrl = apiUrl;
  }
  
  async getUser(id) {
    const response = await fetch(`${this.#apiUrl}/users/${encodeURIComponent(id)}`, {
      signal: AbortSignal.timeout(5_000),
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`fetch user failed: HTTP ${response.status}`);
    }
    const data = await response.json();
    if (
      typeof data !== 'object' ||
      data === null ||
      typeof data.id !== 'string' ||
      typeof data.name !== 'string' ||
      typeof data.email !== 'string'
    ) {
      throw new TypeError('Invalid user response');
    }
    return data;
  }
  
  static fromEnv() {
    return new UserService(process.env.API_URL);
  }
}
```

## Testing with Jest/Vitest

```javascript
import { describe, it, expect, vi } from 'vitest';

describe('UserService', () => {
  it('should fetch user by id', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '1', name: 'Alice' })
    });
    global.fetch = mockFetch;
    
    const user = await fetchUser('1');
    
    expect(user.name).toBe('Alice');
    expect(mockFetch).toHaveBeenCalledWith('/api/users/1');
  });
  
  it('should throw on not found', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 });
    
    await expect(fetchUser('999')).rejects.toThrow('not found');
  });
});
```

## Security Patterns

```javascript
// Sanitize HTML (use DOMPurify)
import DOMPurify from 'dompurify';
element.innerHTML = DOMPurify.sanitize(userHtml);

// Safe text insertion
element.textContent = userInput;

// Validate input
function validateEmail(email) {
  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return pattern.test(email);
}

// Parameterized queries (example with pg)
const result = await client.query(
  'SELECT * FROM users WHERE id = $1',
  [userId]  // Never interpolate user input
);
```
