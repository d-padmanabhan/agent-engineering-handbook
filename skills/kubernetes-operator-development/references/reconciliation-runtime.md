# Reconciliation Runtime

Use this reference for level-based reconciliation, provider mutations,
controller-runtime cache semantics, conflicts, retries, concurrency, and rate
limits.

## Level-Based Reconciliation

Treat each request as a key to inspect, not as a description of one transition.
The same key may be queued repeatedly, coalesced, delayed, or reconstructed
after restart. Derive action from desired state plus current observations.

Keep orchestration separate from pure decisions:

```go
type Provider interface {
    Observe(ctx context.Context, identity ExternalIdentity) (ObservedState, error)
    Apply(ctx context.Context, operation Operation) (ApplyResult, error)
    Delete(ctx context.Context, operation DeleteOperation) error
}
```

Pass explicit external identity, ownership expectations, operation identity,
and preconditions. An interface that accepts only desired fields can hide
collision, adoption, and conditional-write requirements.

One CR can own multiple subresources. Reconcile each independently so a
failure after one success is recovered by observation, not a stored
`currentStep`. Use a durable workflow engine only when the domain truly needs
ordered, non-convergent business steps.

## Idempotency and Lost Responses

Observe-before-create avoids many duplicates but still permits a race:

1. Two workers observe absence.
2. Both create.
3. The provider accepts both.

Prefer, in order:

1. a provider-supported idempotency key derived from stable operation identity;
2. atomic conditional create with a unique provider key;
3. deterministic naming plus ownership tags and conflict handling;
4. a durable operation record with atomic claim and complete result replay.

Keep an idempotency key stable across retries of the same logical operation,
including process restarts. Do not generate a new key per reconcile attempt.
Bind the key to immutable owner identity and operation intent. If the provider
returns a conflict, observe and verify ownership before deciding it represents
success.

After a timeout or transport failure, treat the result as unknown. Observe by
stable identity before retrying a mutation. Never infer that the provider
failed merely because the client did not receive a response.

## External Identity and Ownership

Status can cache provider IDs for efficiency, but status can be lost, stale, or
copied. Make provider-side metadata authoritative where supported:

- controller or API group identity;
- cluster identity;
- Kubernetes namespace and name;
- Kubernetes object UID;
- managed field or subresource identity.

Before update or deletion, fetch the external resource and verify immutable
identity and expected owner metadata. Detect collisions between CRs, clusters,
or controller versions. Surface a stable condition instead of adopting or
overwriting by display name.

For providers without metadata, maintain a durable, transactional ownership
registry with uniqueness constraints and recovery procedures. A status field
alone is not that registry.

## Cached Reads and Writes

The default controller-runtime client normally reads from a shared informer
cache and writes directly to the API server. Cached reads can lag writes and
external events.

Design reconciliation to tolerate stale reads. In particular:

- do not require immediate read-your-write behavior for correctness;
- return after material writes when a fresh event can continue convergence;
- use resource versions and narrow patches for optimistic concurrency;
- use an uncached `APIReader` only for a specific correctness requirement;
- bound and observe live reads to avoid API-server overload;
- configure watched types and cache scope explicitly at scale.

Do not use sleep to wait for the cache. Do not broadly disable caching to hide
an incorrect state machine.

## Conflicts and Field Ownership

On an expected stale `resourceVersion` conflict, re-read current state and use
a bounded retry or requeue. Recompute the intended patch from current state;
do not replay a stale full-object update.

Repeated conflicts indicate unclear ownership, overly broad writes, or another
active reconciler. Instrument them and diagnose the competing writer.
Server-Side Apply can clarify ownership for Kubernetes children when list/map
schema semantics and field managers are deliberate. Never force ownership as
a default conflict-resolution strategy.

External providers need equivalent conditional update support when available:
ETags, versions, generation numbers, compare-and-swap, or provider-specific
preconditions.

## Retry Ownership

Classify failures by action:

- transient dependency or network failure: return an error for workqueue
  rate-limited retry;
- provider-directed throttling: honor a bounded `Retry-After` or reset time
  with jitter;
- dependency not ready or eventual consistency: use a bounded `RequeueAfter`;
- invalid desired state: set a current terminal condition and wait for a
  relevant watched change;
- authentication or authorization: set a safe condition and requeue only when
  credentials, policy, or a bounded refresh schedule can change the outcome;
- ownership collision: do not retry destructively; require resolution.

Choose one retry owner for each failure path. Controller workqueue, provider
SDK, and HTTP retries can multiply latency and calls. Bound attempts and total
deadline, propagate context, and make cancellation stop nested retries.

Never busy-loop. Add jitter to scheduled fleets so many CRs do not synchronize
provider calls.

## Concurrency and Rate Limits

Workqueue serialization for one key does not prove external serialization.
Operations can overlap across replicas, restarts, timeouts, duplicate CRs, or
different keys that map to one external resource.

Set `MaxConcurrentReconciles` from measured provider latency and quotas. Use
shared clients and global provider limiters, then add per-tenant fairness where
one tenant could starve others. Bound:

- active reconciles;
- calls per provider and credential;
- calls per tenant;
- in-flight creates and deletes;
- queue depth and reconcile duration;
- response body size and request deadline.

Enable leader election for replicated managers unless the complete controller
set is designed and tested for multi-active operation. Leader election reduces
duplicate managers; it does not replace provider idempotency or ownership
checks.

## Watches, Predicates, and Indexes

Watch every dependency whose change can recover a terminal condition, such as
a referenced Secret or policy CR. Use field indexes and mapping functions for
reverse lookups instead of cluster-wide list-and-filter operations.

Predicates reduce noise but can suppress necessary recovery. A generation-only
predicate misses relevant annotations, deletion transitions, referenced
objects, and provider-driven drift. Periodic reconciliation can be a safety net
for external drift, but its interval must fit scale and provider budgets.

## Authoritative Sources

- [controller-runtime client](https://pkg.go.dev/sigs.k8s.io/controller-runtime/pkg/client)
- [controller-runtime cache](https://pkg.go.dev/sigs.k8s.io/controller-runtime/pkg/cache)
- [controller-runtime controller options](https://pkg.go.dev/sigs.k8s.io/controller-runtime/pkg/controller)
- [Kubernetes controllers](https://kubernetes.io/docs/concepts/architecture/controller/)
