# Go Deployment & Distribution

## Building Binaries

```bash
# Build for current platform
go build -o myapp ./cmd/myapp

# Build for specific OS/architecture
GOOS=linux GOARCH=amd64 go build -o myapp-linux-amd64 ./cmd/myapp
GOOS=windows GOARCH=amd64 go build -o myapp-windows-amd64.exe ./cmd/myapp
GOOS=darwin GOARCH=arm64 go build -o myapp-darwin-arm64 ./cmd/myapp

# Build with version info
go build -ldflags "-X main.Version=$(git describe --tags)" -o myapp ./cmd/myapp

# Build optimized binary (smaller, faster)
go build -ldflags "-s -w" -o myapp ./cmd/myapp
# -s: omit symbol table and debug info
# -w: omit DWARF symbol table
```

## Hot Reload (Air) for Local Dev

Use **Air** to rebuild/restart on file changes during local development. This is a **developer convenience**, not a production or CI tool.

**Install (macOS):**

```bash
brew install air
```

**Install (Go toolchain, portable):**

```bash
go install github.com/air-verse/air@latest
```

**Initialize config (recommended):**

```bash
air init
```

**Run:**

```bash
air
# or:
air -c .air.toml
```

**Keep build output out of git:**

- Add `tmp/` (or whatever Air uses) to `.gitignore`

Minimal example `.air.toml` (adjust paths to your app layout; `air init` will generate a version-correct baseline):

```toml
root = "."
tmp_dir = "tmp"

[build]
cmd = "go build -o ./tmp/app ./cmd/server"
bin = "tmp/app"
include_ext = ["go"]
exclude_dir = ["tmp", "vendor", ".git"]
```

## Docker Multi-Stage Build

```dockerfile
# Build stage
FROM golang:1.25.0-alpine3.22 AS builder

WORKDIR /build

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY . .

# Build binary
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o myapp ./cmd/myapp

# Runtime stage - distroless + nonroot
FROM gcr.io/distroless/static-debian12:nonroot

WORKDIR /app
COPY --from=builder /build/myapp /app/myapp
USER nonroot:nonroot

EXPOSE 8080

CMD ["/app/myapp"]
```

## CI/CD with GitHub Actions

```yaml
name: Build and Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.25'
          cache: true

      - name: Run tests
        run: go test -race ./...

      - name: Run linters
        run: |
          golangci-lint run
          govulncheck ./...

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.25'

      - name: Build
        run: go build -ldflags="-s -w" -o myapp ./cmd/myapp

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: myapp
          path: myapp
```

## Version Management

```go
package main

import (
    "fmt"
    "runtime"
)

var (
    Version   = "dev"
    BuildTime = "unknown"
    GitCommit = "unknown"
)

func printVersion() {
    fmt.Printf("Version: %s\n", Version)
    fmt.Printf("Build Time: %s\n", BuildTime)
    fmt.Printf("Git Commit: %s\n", GitCommit)
    fmt.Printf("Go Version: %s\n", runtime.Version())
}

// Build with:
// go build -ldflags "-X main.Version=$(git describe --tags) -X main.BuildTime=$(date -u +%Y-%m-%dT%H:%M:%SZ) -X main.GitCommit=$(git rev-parse HEAD)"
```
