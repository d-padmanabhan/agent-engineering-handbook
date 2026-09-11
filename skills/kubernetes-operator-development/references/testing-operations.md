# Operator Testing and Operations

Use this reference to select test layers, inject failures, validate upgrades,
and define production evidence.

## Test Layer Contract

Each test layer proves different behavior.

### Pure unit tests

Use table-driven Go tests for:

- desired-state construction and owned-field diffs;
- validation and default-independent business rules;
- provider translation and error classification;
- stable operation and idempotency key derivation;
- status condition transitions;
- rate-limit and retry decisions.

Keep these tests deterministic and independent of Kubernetes clients.

### Fake client tests

A controller-runtime fake client is useful for narrow client interactions. It
does not faithfully emulate API-server defaulting, validation, conversion,
admission, resource versions, cache lag, managed fields, or all subresource
behavior. Do not claim API correctness from fake-client tests.

### API-server and envtest tests

Use `envtest` or an equivalent real API server to test:

- CRD schema, defaults, CEL, and status subresource behavior;
- finalizer persistence and deletion timestamps;
- reconciliation, watches, field indexes, predicates, and conflicts;
- admission and conversion webhooks;
- status condition currency and generation changes.

Pin and provision compatible test assets through the repository's documented
tooling. Keep startup and test deadlines bounded.

`envtest` runs an API server and etcd, not a complete Kubernetes control plane.
It does not provide every built-in controller. Owner-reference garbage
collection, namespace behavior, scheduling, kubelet behavior, and other
controller effects require explicit test doubles or a real cluster.

### Provider contract tests

Test provider adapters against a controlled emulator, mock server, sandbox, or
test account. Cover:

- stable idempotency keys and conditional creates;
- success followed by a lost response;
- duplicate delivery and ownership conflicts;
- pagination and eventual consistency;
- 429 handling, bounded `Retry-After`, and quota exhaustion;
- authentication and authorization failures;
- conditional updates and stale versions;
- delete of an already absent object;
- bounded request and response handling.

Never point automated skill or unit evals at production providers.

### End-to-end tests

Use an isolated cluster and isolated provider scope. Verify:

1. create reaches a current ready condition;
2. update changes only owned fields;
3. external drift is repaired or reported according to policy;
4. restart and partial failure converge without duplicates;
5. retention and deletion follow the authorized policy;
6. adoption rejects ambiguous or unowned resources;
7. finalizer failure is visible and recoverable;
8. orphan discovery detects intentionally injected residue.

## Failure Injection Matrix

Inject failures at mutation boundaries, not only before calls:

- provider accepts create, response is lost;
- controller exits after provider success and before status update;
- status update conflicts after external mutation;
- cache returns pre-write state;
- credentials expire during cleanup;
- provider returns 429, 500, malformed data, or oversized data;
- two CRs target one external object;
- two clusters use the same namespaced name;
- deletion begins before finalizer registration;
- webhook or conversion service is unavailable during upgrade;
- old operator binary observes objects written by the new version.

For each case, assert provider call count, resulting ownership, status
currency, queue behavior, and eventual convergence or safe stop.

## Upgrade and Rollback Tests

Maintain fixtures from supported released CRD and operator versions. Test:

- old stored objects read by the new operator;
- round-trip conversion without semantic loss;
- storage-version migration;
- changed defaults on old and new objects;
- new fields observed by an older rollback binary;
- webhook rollout ordering and certificate readiness;
- no unintended create, delete, rename, or adoption during upgrade;
- rollback before and after storage migration.

Compilation and generated-manifest diffs are necessary but do not prove
semantic compatibility.

## Observability

Expose low-cardinality metrics for:

- reconcile attempts, outcomes, errors, and duration;
- queue depth and wait duration;
- provider calls, errors, throttles, and latency;
- conflict and retry counts;
- managed, ready, degraded, deleting, and orphaned resources;
- finalizer age and stuck deletions.

Do not label metrics with CR UID, arbitrary hostname, request ID, or raw error.
Use structured logs with controller, namespace, name, generation, and
reconcile correlation fields. Keep credentials, authorization headers, Secret
values, provider bodies, and sensitive external identifiers out of logs,
events, status, and metrics.

Emit Kubernetes Events for meaningful user-visible transitions, not every
reconcile. Bound and aggregate repeated events to prevent storms.

Health checks should prove process and manager health. Readiness should prove
the manager can process work. Do not make liveness depend on every external
provider, because a provider outage must not trigger a restart loop.

## Security and Runtime Readiness

Before release, verify:

- dedicated least-privilege ServiceAccount and provider identity;
- workload identity or short-lived brokered credentials;
- default-deny network policy with required API and provider egress;
- non-root runtime, dropped capabilities, seccomp, and read-only filesystem
  where compatible;
- image pinned by digest, signed, scanned, and accompanied by an SBOM;
- webhook TLS, certificate rotation, authentication assumptions, and network
  reachability;
- destination allowlists and SSRF controls for configurable provider URLs;
- bounded timeouts, retries, response sizes, concurrency, and shutdown;
- PodDisruptionBudget, leader election, and graceful termination appropriate
  to the deployment;
- runbooks for stuck finalizers, ownership collision, orphan cleanup, provider
  outage, credential failure, and rollback.

## Build and Verification Sequence

Use repository targets rather than inventing command variants. A typical Go
operator verification sequence includes:

```bash
make generate
make manifests
gofmt -w .
go vet ./...
go test -race ./...
golangci-lint run
govulncheck ./...
```

Then validate rendered CRDs and deployment manifests against supported
Kubernetes versions, inspect generated diffs, build the pinned image, and run
the applicable integration and end-to-end suites.

Do not weaken linters, race checks, schemas, or tests to pass generated code.
If a tool is unavailable, record the exact gap and the closest substitute.

## Authoritative Sources

- [Kubebuilder testing](https://book.kubebuilder.io/cronjob-tutorial/writing-tests)
- [controller-runtime envtest](https://pkg.go.dev/sigs.k8s.io/controller-runtime/pkg/envtest)
- [Kubernetes operator pattern](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
- [Kubernetes component health](https://kubernetes.io/docs/reference/using-api/health-checks/)
