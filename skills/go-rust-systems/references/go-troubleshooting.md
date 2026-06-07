# Go Troubleshooting Guide

## Debug Logging

```go
import "log/slog"

logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
    Level: slog.LevelDebug,
}))

logger.Debug("processing user", "user_id", userID, "step", "validation")
```

**Structured Logging Best Practices:**

```go
// GOOD: Include context in logs
logger.Info("user created",
    "user_id", userID,
    "email", email,
    "duration_ms", duration.Milliseconds(),
)

// GOOD: Use different log levels appropriately
logger.Debug("detailed debug info", "internal_state", state)
logger.Info("important events", "event", "user_login")
logger.Warn("recoverable issues", "warning", "rate_limit_approaching")
logger.Error("errors that need attention", "error", err)

// GOOD: Log errors with context
logger.Error("failed to process request",
    "error", err,
    "request_id", requestID,
    "user_id", userID,
)
```

## Using Delve

```bash
dlv debug ./cmd/myapp
dlv test ./pkg/mypackage
dlv attach <PID>

# Delve commands
(dlv) break main.main
(dlv) continue
(dlv) next
(dlv) print variable
(dlv) goroutines
(dlv) goroutine <id>
(dlv) stack
(dlv) locals
(dlv) args
```

**Debugging Goroutines:**

```go
// Add debug logging to track goroutines
import (
    "runtime"
    "log/slog"
)

func debugGoroutines(logger *slog.Logger) {
    buf := make([]byte, 1<<20)
    stackSize := runtime.Stack(buf, true)
    logger.Debug("goroutines", "stack", string(buf[:stackSize]))
}
```

## CPU Profiling

```bash
go test -cpuprofile=cpu.prof -bench=.
go tool pprof cpu.prof

# pprof commands
(pprof) top          # Top functions by CPU time
(pprof) top10        # Top 10 functions
(pprof) list func    # Show source code for function
(pprof) web          # Generate SVG graph
(pprof) png          # Generate PNG graph
(pprof) peek func    # Show callers and callees
```

**Memory Profiling:**

```bash
go test -memprofile=mem.prof -bench=.
go tool pprof mem.prof

# Memory-specific commands
(pprof) top -alloc_space    # Top allocators
(pprof) top -inuse_space   # Top memory users
(pprof) list func          # Show allocations in function
```

**HTTP Profiling:**

```go
import (
    "log"
    "net/http"
    _ "net/http/pprof"
    "time"
)

func main() {
    go func() {
        srv := &http.Server{
            Addr:              "localhost:6060",
            Handler:           http.DefaultServeMux,
            ReadHeaderTimeout: 5 * time.Second,
            ReadTimeout:       15 * time.Second,
            WriteTimeout:      30 * time.Second,
            IdleTimeout:       60 * time.Second,
        }
        log.Println(srv.ListenAndServe())
    }()
    // Application code...
}

// Then profile:
// go tool pprof http://localhost:6060/debug/pprof/profile
// go tool pprof http://localhost:6060/debug/pprof/heap
```

## Common Errors & Solutions

**Nil Pointer:**

```go
// BAD: Potential nil pointer dereference
func process(user *User) {
    fmt.Println(user.Name)  // Panic if user is nil
}

// GOOD: Check nil first
func process(user *User) error {
    if user == nil {
        return fmt.Errorf("user is nil")
    }
    fmt.Println(user.Name)
    return nil
}
```

**Index Out of Range:**

```go
// BAD: No bounds checking
func getFirst(items []Item) Item {
    return items[0]  // Panic if slice is empty
}

// GOOD: Check length
func getFirst(items []Item) (Item, error) {
    if len(items) == 0 {
        return Item{}, fmt.Errorf("items is empty")
    }
    return items[0], nil
}
```

**Race Conditions:**

```bash
# Run tests with race detector
go test -race ./...

# Build with race detector
go build -race

# Race detector will report:
# WARNING: DATA RACE
# Read at 0x00c00001a0f0 by goroutine 7:
# Previous write at 0x00c00001a0f0 by goroutine 6:
```

## Common Mistakes

### 1. Using Goroutines Without WaitGroup

```go
//  BAD: Fire-and-forget
func processItems(items []Item) {
    for _, item := range items {
        go process(item)  // No way to wait!
    }
}

//  GOOD: Use WaitGroup
func processItems(items []Item) {
    var wg sync.WaitGroup
    for _, item := range items {
        wg.Add(1)
        go func(item Item) {
            defer wg.Done()
            process(item)
        }(item)
    }
    wg.Wait()
}
```

### 2. Not Checking Error Returns

```go
//  BAD: Ignoring errors
result, _ := someFunc()

//  GOOD: Check errors
result, err := someFunc()
if err != nil {
    return fmt.Errorf("someFunc failed: %w", err)
}
```

### 3. Shadowing Variables with `:=`

```go
//  BAD: Shadowing err
result, err := step1()
if result.NeedsStep2 {
    result, err := step2()  // Shadows outer err!
}

//  GOOD: Reuse err
result, err := step1()
if result.NeedsStep2 {
    result, err = step2()  // Reuses outer err
}
```

### 4. Closing Channels from Receiver Side

```go
//  BAD: Receiver closes channel
func receiver(ch <-chan int) {
    for v := range ch {
        process(v)
    }
    close(ch)  // WRONG! Only sender should close
}

//  GOOD: Sender closes channel
func sender(ch chan<- int, values []int) {
    defer close(ch)
    for _, v := range values {
        ch <- v
    }
}
```

### 5. Global Mutable State

```go
//  BAD: Global mutable state
var cache = make(map[string]interface{})

func Get(key string) interface{} {
    return cache[key]  // Race!
}

//  GOOD: Encapsulated with mutex
type Cache struct {
    mu    sync.RWMutex
    items map[string]interface{}
}

func (c *Cache) Get(key string) (interface{}, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    val, ok := c.items[key]
    return val, ok
}
```
