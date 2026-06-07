---
name: go-rust-systems
description: Go and Rust systems programming best practices for performance-critical, concurrent, and safe applications. Covers error handling, ownership/borrowing (Rust), context and goroutines (Go), testing patterns, and production deployment. Use when working with .go, .rs files, Cargo.toml, go.mod, or when asking about Go or Rust development.
---

# Go & Rust Systems Programming

## When to Use Which

| Use Case | Go | Rust |
|----------|----|----- |
| Web services, APIs | ✅ Excellent | ✅ Good |
| CLI tools | ✅ Excellent | ✅ Excellent |
| Systems programming | ✅ Good | ✅ Excellent |
| Memory-critical apps | ⚠️ GC overhead | ✅ Zero-cost |
| Concurrency | ✅ Goroutines | ✅ Fearless |
| Learning curve | ✅ Easy | ⚠️ Steeper |

## Go Quick Reference

### Essential Commands

```bash
go mod init <module>          # Initialize new module
go mod tidy                   # Add missing, remove unused
go test -race ./...          # Run with race detector
go test -cover ./...         # Show coverage
golangci-lint run            # Run all linters
govulncheck ./...            # Check vulnerabilities
```

### Critical Patterns

```go
// 1. Always check errors
result, err := someFunc()
if err != nil {
    return fmt.Errorf("operation failed: %w", err)  // Wrap with context
}

// 2. Use context for cancellation
func processData(ctx context.Context, data []string) error {
    for _, item := range data {
        select {
        case <-ctx.Done():
            return ctx.Err()  // Respect cancellation
        default:
            // Process item
        }
    }
    return nil
}

// 3. Defer cleanup immediately
file, err := os.Open("file.txt")
if err != nil {
    return err
}
defer file.Close()  // Defer right after open

// 4. Table-driven tests
func TestAdd(t *testing.T) {
    tests := []struct {
        name string
        a, b int
        want int
    }{
        {"positive", 1, 2, 3},
        {"negative", -1, -2, -3},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            if got := Add(tt.a, tt.b); got != tt.want {
                t.Errorf("Add() = %v, want %v", got, tt.want)
            }
        })
    }
}
```

### Control flow: `switch` vs `if` / `else`

Prefer **`switch`** for multi-way dispatch on one expression (and type switches); keep **`if`** for errors, booleans, guards, and two-branch logic. Do not rewrite `errors.Is` / `errors.As` chains just to use `switch`. Detail: `rules/210-go.mdc` (Simplicity & Idiomatic Go) and `references/go-idioms.md`.

### Mandatory Hardening Add-On (Go)

For HTTP/API client code, always apply the hardening checks from
`rules/210-go.mdc`:

- Use explicit `http.Server` values with `ReadHeaderTimeout`, `ReadTimeout`,
  `WriteTimeout`, and `IdleTimeout`; do not call `http.ListenAndServe`
  directly in production services.
- Bound inbound request bodies with `http.MaxBytesReader` before JSON decode.
- Use `Decoder.DisallowUnknownFields()` for public JSON APIs.
- Inject or construct explicit `*http.Client` values with timeouts and
  transport settings; do not use `http.Get`, `http.Post`, or
  `http.DefaultClient` in production services.
- Bound response reads before `io.ReadAll`
- Cap `Retry-After` and server-derived delays
- Avoid exported mutable policy/guardrail registries
- Keep test helpers in `*_test.go`
- Avoid side-effectful `init()`; perform app wiring in `cmd/<app>/main.go`
- Keep `go.mod` module/toolchain pinned and run `go mod tidy` / `go mod verify`
  in CI

Use semgrep + pre-commit checks for these patterns because standard linting
does not catch all of them reliably.

### How To Maintain Rule/Skill Parity

When you add a new Go hardening expectation:

1. Add the requirement to `rules/210-go.mdc` under **HTTP Client Hardening (MUST)**.
2. Add detection guidance (semgrep/pre-commit) in the same rule file.
3. Mirror the short operational summary in this `SKILL.md` section.
4. Update at least one concrete reference example under
   `skills/go-rust-systems/references/`.

This keeps policy (rules), agent behavior (skill), and examples in sync.

## Rust Quick Reference

### Essential Commands

```bash
cargo new my-project          # Create new project
cargo build --release         # Build optimized
cargo test                    # Run tests
cargo clippy                  # Linting
cargo fmt                     # Format code
cargo audit                   # Security audit
```

### Critical Patterns

```rust
// 1. Ownership - each value has one owner
let s1 = String::from("hello");
let s2 = s1;  // s1 moved to s2
// println!("{}", s1);  // Error: value borrowed after move

// 2. Borrowing - references don't take ownership
fn calculate_length(s: &String) -> usize {
    s.len()
}
let s1 = String::from("hello");
let len = calculate_length(&s1);
println!("{} has length {}", s1, len);  // s1 still valid

// 3. Result for error handling
fn parse_number(s: &str) -> Result<i32, ParseIntError> {
    s.parse::<i32>()
}

// Use ? for propagation
fn read_file(path: &str) -> Result<String, std::io::Error> {
    let contents = std::fs::read_to_string(path)?;
    Ok(contents)
}

// 4. Option for nullable values
fn find_user(id: u32) -> Option<User> {
    if id == 0 { None } else { Some(User { id }) }
}
```

## Go Error Handling

```go
// Sentinel errors
var ErrNotFound = errors.New("not found")

// Custom error types
type ValidationError struct {
    Field string
    Issue string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed on %s: %s", e.Field, e.Issue)
}

// Error wrapping
if err != nil {
    return fmt.Errorf("failed to process user %s: %w", id, err)
}

// Error checking
if errors.Is(err, ErrNotFound) { /* handle */ }
var valErr *ValidationError
if errors.As(err, &valErr) { /* handle */ }
```

## Rust Error Handling

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("User not found: {0}")]
    NotFound(String),
    
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    
    #[error("Invalid input: {0}")]
    Validation(String),
}

// Use anyhow for applications, thiserror for libraries
fn process_user(id: &str) -> anyhow::Result<User> {
    let user = find_user(id)
        .ok_or_else(|| anyhow::anyhow!("User {} not found", id))?;
    Ok(user)
}
```

## Go Logging - Default Stack

**Default for new code:** `log/slog` (stdlib since 1.21) with the JSON handler. The ecosystem has aligned behind slog as the frontend; backends can be swapped without touching log statements if profiling shows logging is a bottleneck.

```go
opts := &slog.HandlerOptions{AddSource: true, Level: slog.LevelInfo}
slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stderr, opts)))
```

### Calling conventions, ordered by safety

```go
slog.Info("request", "method", "GET", "status", 200)                    // loose - error-prone
slog.InfoContext(ctx, "request", slog.String("method", "GET"), ...)     // recommended (enables trace correlation)
logger.LogAttrs(ctx, slog.LevelInfo, "request", slog.String(...), ...)  // safest (typed; compile-time)
```

### Trace correlation via `otelslog`

```go
import "go.opentelemetry.io/contrib/bridges/otelslog"

slog.SetDefault(otelslog.NewLogger("svc", otelslog.WithLoggerProvider(global.GetLoggerProvider())))
// MUST use *Context variants for span correlation:
logger.InfoContext(ctx, "processing", slog.String("order_id", id))
```

### Redaction via `LogValuer`

```go
type APIKey string
func (APIKey) LogValue() slog.Value { return slog.StringValue("REDACTED") }
```

Centralizes redaction so call sites cannot leak by accident.

### Decision matrix - when to swap backend

| Need | Choice | Notes |
|---|---|---|
| Default | `slog` + `JSONHandler` | ~101 ns/op, zero allocs; fast enough for almost everyone |
| OTel correlation | `slog` + `otelslog` bridge | Default if service runs on OpenTelemetry |
| Profiler shows logging is hot | `phuslu/log` as slog backend | ~38 ns/op (~2.7x stdlib); single maintainer is the trade-off |
| Maximum throughput, library API OK | `zerolog` native | ~25 ns/op, zero allocs; built-in sampling |
| Extensibility, advanced cores, test observers | `zap` native | `zapcore.Core` composition, `zaptest/observer`, `AtomicLevel` |
| CLI / TUI, human reads terminal | `charmbracelet/log` as slog backend | Coloring, icons, color downsampling |
| Existing logrus | Migrate hot paths to slog | Don't start new code on logrus (maintenance mode, ~15x slower than slog) |

**Footguns:**

- `zerolog` *as* slog backend re-encodes `WithAttrs` per `Handle()` call - ~46x slower than its native API. Use zerolog natively; don't bridge.
- `zerolog` chain without terminal `.Msg()` / `.Send()` silently drops the entry AND leaks the pooled `Event`.
- `zap.SugaredLogger` adds 1 alloc per call from variadic boxing.
- `slog` ships no TRACE / FATAL levels by default.

### Required CI lint

```bash
go install github.com/go-simpler/sloglint/cmd/sloglint@latest
sloglint -no-mixed-args -static-msg ./...
```

For the full rationale, library landscape, and benchmark numbers, see Section 7 (Logging) in `rules/210-go.mdc`.

---

## Detailed References

- **Go Patterns**: See [references/go-patterns.md](references/go-patterns.md) for concurrency, interfaces, testing
- **Go Idioms**: See [references/go-idioms.md](references/go-idioms.md) for Go Proverbs, zero value, dependency management, naming, project layout
- **Go Testing**: See [references/go-testing.md](references/go-testing.md) for table-driven tests, fuzz testing, mocking, integration tests, benchmarks
- **Go Troubleshooting**: See [references/go-troubleshooting.md](references/go-troubleshooting.md) for debug logging, Delve, profiling, common errors
- **Go Performance**: See [references/go-performance.md](references/go-performance.md) for evidence-based optimization, profiling, memory management
- **Go AWS Integration**: See [references/go-aws-integration.md](references/go-aws-integration.md) for AWS SDK v2, Lambda patterns, error handling
- **Go CLI Development**: See [references/go-cli-development.md](references/go-cli-development.md) for cobra, urfave/cli, CLI best practices
- **Go Design Patterns**: See [references/go-design-patterns.md](references/go-design-patterns.md) for factory, strategy, observer patterns
- **Go Generics**: See [references/go-generics.md](references/go-generics.md) for generic functions, types, constraints, interfaces
- **Go Deployment**: See [references/go-deployment.md](references/go-deployment.md) for building binaries, Docker, CI/CD, version management
- **Rust Patterns**: See [references/rust-patterns.md](references/rust-patterns.md) for ownership, lifetimes, async
