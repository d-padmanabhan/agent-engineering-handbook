# Go Testing Patterns

## Test Structure

```go
//  GOOD: Table-driven test
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
            t.Parallel()

            got := Add(tt.a, tt.b)
            if got != tt.want {
                t.Errorf("Add(%d, %d) = %d, want %d", tt.a, tt.b, got, tt.want)
            }
        })
    }
}

//  GOOD: Fuzz test
func FuzzParseURL(f *testing.F) {
    f.Add("https://acme.com")

    f.Fuzz(func(t *testing.T, url string) {
        _, err := ParseURL(url)
        _ = err  // Must not panic
    })
}
```

## Advanced Testing Patterns

**Test Helpers:**

> [!IMPORTANT]
> Keep helper utilities that import `testing`/`httptest` in `*_test.go` files.
> This prevents test scaffolding from being compiled into production binaries.

```go
func setupTestDB(t *testing.T) *sql.DB {
    t.Helper()  // Marks this as a test helper

    db, err := sql.Open("sqlite3", ":memory:")
    if err != nil {
        t.Fatalf("failed to open test DB: %v", err)
    }

    // Setup schema
    if _, err := db.Exec("CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT)"); err != nil {
        t.Fatalf("failed to create table: %v", err)
    }

    t.Cleanup(func() {
        db.Close()
    })

    return db
}

func TestUserService(t *testing.T) {
    db := setupTestDB(t)
    service := NewUserService(db)
    // Test implementation...
}
```

**Mocking with Interfaces:**

```go
type UserRepository interface {
    GetUser(ctx context.Context, id string) (*User, error)
}

type MockUserRepository struct {
    GetUserFunc func(ctx context.Context, id string) (*User, error)
}

func (m *MockUserRepository) GetUser(ctx context.Context, id string) (*User, error) {
    if m.GetUserFunc != nil {
        return m.GetUserFunc(ctx, id)
    }
    return nil, ErrNotFound
}

func TestUserService_GetUser(t *testing.T) {
    mockRepo := &MockUserRepository{
        GetUserFunc: func(ctx context.Context, id string) (*User, error) {
            if id == "test-id" {
                return &User{ID: "test-id", Name: "Test"}, nil
            }
            return nil, ErrNotFound
        },
    }

    service := NewUserService(mockRepo)
    user, err := service.GetUser(context.Background(), "test-id")

    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
    if user.Name != "Test" {
        t.Errorf("got name %q, want %q", user.Name, "Test")
    }
}
```

**Integration Tests:**

```go
//go:build integration
// +build integration

package integration

import (
    "testing"
    "context"
)

func TestUserService_Integration(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping integration test")
    }

    // Use real database
    db := setupRealDB(t)
    service := NewUserService(db)

    // Test with real dependencies
    user, err := service.CreateUser(context.Background(), &User{Name: "Test"})
    if err != nil {
        t.Fatalf("failed to create user: %v", err)
    }

    retrieved, err := service.GetUser(context.Background(), user.ID)
    if err != nil {
        t.Fatalf("failed to get user: %v", err)
    }

    if retrieved.Name != "Test" {
        t.Errorf("got name %q, want %q", retrieved.Name, "Test")
    }
}
```

**Concurrent Test Safety:**

```go
func TestConcurrentAccess(t *testing.T) {
    service := NewUserService(setupTestDB(t))

    t.Run("concurrent writes", func(t *testing.T) {
        const numGoroutines = 100
        var wg sync.WaitGroup
        wg.Add(numGoroutines)

        for i := 0; i < numGoroutines; i++ {
            go func(id int) {
                defer wg.Done()
                _, err := service.CreateUser(context.Background(), &User{
                    ID:   fmt.Sprintf("user-%d", id),
                    Name: fmt.Sprintf("User %d", id),
                })
                if err != nil {
                    t.Errorf("failed to create user: %v", err)
                }
            }(i)
        }

        wg.Wait()
    })
}
```

**Benchmark Tests:**

```go
func BenchmarkProcessItems(b *testing.B) {
    items := generateTestItems(1000)

    b.ResetTimer()
    b.ReportAllocs()

    for i := 0; i < b.N; i++ {
        ProcessItems(items)
    }
}

func BenchmarkProcessItemsParallel(b *testing.B) {
    items := generateTestItems(1000)

    b.ResetTimer()
    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            ProcessItems(items)
        }
    })
}

// Compare implementations
func BenchmarkOldImplementation(b *testing.B) {
    // Old code
}

func BenchmarkNewImplementation(b *testing.B) {
    // New optimized code
}
```

## CI Gates (Non-Negotiable)

```bash
gofmt -s -w .
go vet ./...
staticcheck ./...
golangci-lint run
go test -race ./...
govulncheck ./...
```
