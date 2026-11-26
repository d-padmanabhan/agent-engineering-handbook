# Failure Policy and Resilience Testing

Write one failure policy per critical operation. A policy connects failure classification to bounded runtime behavior, user impact, observability, and recovery.

## Failure Policy Template

```text
Critical operation:
Caller and business outcome:
End-to-end deadline:
Required dependencies:
Optional dependencies:
Failure classes:
Retry owner and budget:
Idempotency or reconciliation:
Concurrency and queue bounds:
Circuit-breaker scope:
Fallback and correctness limits:
User-visible behavior:
Metrics and alerts:
Recovery owner:
Validation experiment:
Abort and rollback criteria:
```

## Failure Classification

Classify outcomes before assigning retry or breaker behavior:

- **Transient dependency failure**: bounded retry may help.
- **Persistent dependency failure**: fail fast or open a justified circuit.
- **Throttling or overload**: reduce offered load and honor bounded retry guidance.
- **Caller error**: return a stable client failure; do not retry or count against a dependency breaker.
- **Authentication or authorization failure**: fail closed; do not fallback around policy.
- **Business rejection**: return the domain outcome; it is not infrastructure failure.
- **Ambiguous mutation**: reconcile authoritative state before unsafe repetition. Reconciliation reads can lag the write, so a missing record is not proof that the mutation failed.
- **Cancellation or expired deadline**: stop work and propagate cancellation.
- **Programming defect**: surface and fix; do not mask with retries.

## Retry Budget

Bound:

- maximum attempts;
- maximum elapsed time;
- per-attempt timeout;
- backoff and jitter;
- retryable status and exception classes;
- concurrent retry volume;
- total amplification across layers.

One initial call plus two retries at three nested layers can create up to 27 dependency attempts. Assign retry ownership to one layer and disable or account for hidden SDK, proxy, mesh, and gateway retries.

Honor `Retry-After` only within the remaining deadline and with a maximum cap. A server-provided delay is untrusted input to resource scheduling.

## Fallback Review

Approve a fallback only when:

- it preserves required authorization and privacy controls;
- its data freshness and consistency are acceptable;
- callers can distinguish degraded output when that distinction matters;
- it has bounded capacity;
- operators can measure use and failure;
- recovery does not retain stale state indefinitely.

Unsafe examples:

- using cached authorization after revocation;
- showing an old account balance as current;
- accepting an order without durable confirmation;
- returning an empty successful response after a dependency failure.

## Resilience Experiments

Each experiment needs:

1. hypothesis;
2. exact fault and affected scope;
3. baseline;
4. observable acceptance criteria;
5. blast-radius limit;
6. abort condition;
7. recovery expectation;
8. owner and evidence capture.

Useful experiments:

- inject latency above the attempt timeout;
- return a controlled transient-error ratio;
- exhaust one dependency pool;
- saturate one tenant or priority queue;
- open and recover a circuit;
- remove fallback capacity;
- throttle a downstream quota;
- interrupt DNS, identity, configuration, or regional control planes;
- time out a mutation after the provider may have accepted it.

## Required Metrics

Measure by operation and meaningful partition:

- admitted, rejected, shed, timed-out, cancelled, and completed work;
- latency by outcome and percentile;
- queue depth and oldest-item age;
- in-flight work and pool utilization;
- attempts per logical operation;
- retry delay and exhausted retry budgets;
- breaker state, transitions, probes, and rejections;
- fallback requests, freshness, failures, and capacity;
- ambiguous outcomes and reconciliation age;
- user-visible success and degraded-result rate.

CPU and aggregate error rate alone cannot prove resilience.

## Review Failure

Reject a resilience design when:

- the normal path already exceeds the SLO budget;
- retries exceed the caller deadline;
- a fallback violates correctness or authorization;
- isolation exists only in the diagram but shares pools, queues, quotas, or control planes;
- the recovery path is untested;
- an operator cannot determine why work was rejected or degraded;
- success metrics improve only because errors are hidden.
