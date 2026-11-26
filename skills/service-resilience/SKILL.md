---
name: service-resilience
description: Designs and reviews production resilience for service dependencies using deadlines, timeouts, bounded retries, circuit breakers, bulkheads, backpressure, load shedding, rate limits, fallbacks, idempotency, and recovery testing. Use when the user mentions circuit breaker, bulkhead, retries, cascading failure, partial failure, overload, graceful degradation, or resilient distributed services.
---

# Service Resilience

Design resilience as a bounded failure policy, not a collection of decorators. Every mechanism must protect a stated critical journey without creating retry storms, stale success, hidden data loss, or fragmented capacity.

## Resilience Contract

- Begin with critical journeys, SLOs, dependency budgets, and acceptable degraded outcomes.
- Put one end-to-end deadline around the operation. Allocate smaller attempt timeouts within it.
- Retry only classified transient failures for idempotent operations or operations protected by stable idempotency keys.
- Bound attempts, elapsed time, concurrency, queues, memory, and retry amplification.
- Isolate unrelated workloads with bulkheads sized from capacity and priority.
- Shed excess work before saturation destroys useful throughput.
- Use circuit breakers only when rejecting likely failures is cheaper and safer than attempting them.
- Treat fallbacks as alternate correctness contracts. Never return stale or fabricated success silently.
- Make ambiguous mutation outcomes reconcilable.
- Test failure, overload, recovery, and control-plane behavior with measurable acceptance criteria.

## Design Workflow

### 1. Define the critical journey

State:

- caller and business outcome;
- availability and latency SLO;
- synchronous dependencies;
- consistency and freshness requirements;
- acceptable partial or degraded result;
- operations that must fail closed;
- recovery owner and escalation path.

Do not apply one resilience policy to every endpoint or workload.

### 2. Allocate time and failure budgets

For each synchronous dependency, define:

- end-to-end deadline contribution;
- connect, request, and response timeout;
- retry owner and maximum attempts;
- transient failure classification;
- idempotency or reconciliation contract;
- concurrency and queue budget;
- fallback or explicit failure behavior.

Account for DNS, connection pools, proxies, SDK retries, service meshes, and gateways. Hidden retries consume the same caller deadline and multiply load.

### 3. Control load

Apply controls in this order:

1. admission priority and per-principal quotas;
2. bounded queues with maximum age;
3. bounded concurrency and connection pools;
4. backpressure or producer throttling;
5. load shedding with explicit retry guidance;
6. capacity scaling where it is fast enough to matter.

Do not rely on autoscaling after queues, memory, or downstream capacity are already exhausted.

Prevent synchronized load and respect downstream limits:

- Treat concurrent throttling responses from one dependency as one event. Record a shared backoff per limited scope that every caller checks before sending, instead of running independent per-request backoff loops.
- Back off only the scope the dependency reports as limited, such as one endpoint, resource, or tenant. Pause all traffic only for a shared quota.
- Pace calls to a rate-limited dependency client-side at its steady-state limit, for example with a token bucket, and share that budget across every worker and process that consumes the same quota.
- Treat `Retry-After` as the earliest allowed retry: never retry sooner, cap how long you will wait, and reschedule the work when the delay exceeds the deadline.
- Collapse concurrent identical reads and cache refills into one in-flight request, and randomize cache expiry or refresh ahead of expiry so entries do not expire together.
- Add random jitter to retries, reconnects, scheduled jobs, and fleet start times.

### 4. Isolate failure

Choose bulkheads around workloads that should not consume one another's capacity:

- dependency-specific connection pools;
- workload-specific worker pools or semaphores;
- priority queues;
- tenant or customer partitions;
- cells or deployment stamps;
- separate resource quotas.

Document reserved capacity, utilization trade-offs, fairness, and what happens when one partition is full.

Use the circuit breaker and bulkhead reference (`${HANDBOOK_ROOT}/skills/service-resilience/references/circuit-breakers-and-bulkheads.md`) for detailed state and sizing rules.

### 5. Limit repeated failure

Use a circuit breaker only when:

- failures are expensive enough to threaten caller or dependency capacity;
- recent outcomes predict near-term failure;
- calls can be rejected safely;
- recovery can be probed with bounded traffic;
- state scope and observability are defined.

A breaker does not replace timeouts, retries, admission control, or health checks. Avoid a global breaker when one tenant, endpoint, shard, region, or operation can fail independently.

### 6. Define degraded behavior

For every fallback, specify:

- trigger;
- data source and maximum staleness;
- authorization and privacy equivalence;
- user-visible indication;
- unsupported operations;
- cache invalidation or recovery;
- metric proving whether the fallback helps.

Prefer explicit unavailability over plausible but incorrect data.

### 7. Verify recovery

Test:

- timeout and cancellation propagation;
- retry amplification at each layer;
- breaker opening, probing, and closing;
- bulkhead exhaustion and unaffected workloads;
- queue age and shedding;
- dependency brownouts and slow responses;
- recovery without synchronized request floods;
- regional, quota, identity, DNS, and configuration failures;
- reconciliation after ambiguous writes.

Use the failure policy reference (`${HANDBOOK_ROOT}/skills/service-resilience/references/failure-policy-and-testing.md`) for review and experiment design.

## Pattern Selection

| Problem | Primary control | Important companion |
|---|---|---|
| Slow dependency | Deadline and attempt timeout | Cancellation and bounded concurrency |
| Brief transient failure | Bounded jittered retry | Idempotency and retry budget |
| Sustained likely failure | Circuit breaker | Timeout, observability, recovery probe |
| One workload starves another | Bulkhead | Priority, quotas, capacity plan |
| Offered load exceeds capacity | Admission control and shedding | Backpressure and retry guidance |
| Many callers retry or refresh at once | Shared scoped backoff and request coalescing | Jitter and randomized expiry |
| Calling a rate-limited dependency | Client-side pacing to its published limit | Shared quota budget and `Retry-After` |
| Optional dependency unavailable | Explicit fallback | Freshness and correctness contract |
| Mutation timed out | Reconciliation | Stable operation ID or idempotency key |
| Long asynchronous backlog | Queue-age limits | Consumer scaling, DLQ, replay policy |

## Anti-Patterns

- Retrying every exception at every layer.
- Retrying non-idempotent mutations with a new request ID.
- Letting every request or worker run its own backoff loop after a shared throttling event.
- Circuit breaker keyed globally across unrelated tenants or operations.
- Opening a breaker on caller validation or authorization failures.
- Half-open mode releasing an unbounded probe flood.
- Bulkheads with arbitrary sizes and no capacity or fairness model.
- Unbounded queues presented as reliability.
- Fallbacks that bypass authorization or return stale data as current.
- Health checks that call every dependency and cause synchronized failure.
- Catching errors and returning success to improve availability metrics.
- Chaos tests without hypotheses, blast-radius controls, or abort conditions.

## Required Output

Produce:

1. Critical journey, SLO, and dependency map
2. End-to-end deadline and retry budget
3. Failure classification and idempotency contract
4. Admission, concurrency, queue, and bulkhead policy
5. Circuit breaker scope and state policy where justified
6. Degraded behavior and correctness limits
7. Metrics, alerts, and recovery ownership
8. Failure experiments, acceptance criteria, and rollback triggers
