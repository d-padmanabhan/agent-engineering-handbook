# Kubernetes Operator Design Review

Complete this record before implementation. Replace prompts with concrete
decisions and evidence. Use `Not applicable` with a reason instead of deleting
sections.

## Problem and Alternatives

- Problem and user outcome:
- Why continuous reconciliation is required:
- Existing Kubernetes API, vendor operator, Crossplane, or automation options
  evaluated:
- Why a custom operator is the smallest suitable solution:
- Non-goals:

## API Contract

- API group, kind, scope, and initial maturity:
- Intent expressed in `spec`:
- Provider details intentionally hidden:
- Required, optional, defaulted, and immutable fields:
- Structural schema, list/map semantics, and CEL rules:
- Admission or conversion webhooks and why schema is insufficient:
- Compatibility, deprecation, storage-version, and rollback policy:

## Authority and Ownership

- Source of truth:
- Fields and subresources this controller owns:
- Fields shared with humans or other controllers:
- External resources created or managed:
- Stable provider identity:
- Provider-side ownership metadata:
- Cluster, namespace, name, and UID collision prevention:
- Adoption requirements and authorization:

## Reconciliation Contract

- Observations used to calculate desired versus actual state:
- Pure desired-state and diff functions:
- Idempotency or conditional-mutation mechanism:
- Stable operation-key derivation:
- Lost-response recovery:
- Partial-failure recovery:
- Kubernetes and provider conflict handling:
- Cache-staleness tolerance and any justified uncached reads:
- Watches, indexes, predicates, and drift interval:

## Lifecycle and Destructive Behavior

- Finalizer registration point:
- `Delete`, `Retain`, archive, or detach semantics:
- Conservative default and rationale:
- Authorization for deletion-policy changes:
- Ownership proof immediately before update or delete:
- Cleanup retry and terminal-failure behavior:
- Maximum expected deletion duration:
- Stuck-finalizer manual recovery:
- Orphan discovery and repair:
- CR deletion and re-creation behavior:

## Status Contract

- Condition types and stable reasons:
- Definition of current `Ready=True`:
- `observedGeneration` semantics:
- Provider identifiers safe to expose:
- Progress and terminal-failure visibility:
- Status writer ownership and conflict handling:

## Dependencies and Budgets

- Kubernetes and controller-runtime compatibility:
- Provider consistency and quota model:
- Request deadline and response-size limits:
- Workqueue, SDK, and HTTP retry ownership:
- Maximum concurrent reconciles:
- Global and per-tenant rate limits:
- Shutdown and cancellation behavior:

## Identity and Security

- Kubernetes ServiceAccount and exact RBAC:
- Provider identity and exact permissions:
- Secret broker or workload identity:
- External destination validation and egress policy:
- Webhook TLS and certificate lifecycle:
- Sensitive data classification and redaction:
- Destructive-operation audit events:

## Verification

- Unit tests:
- API-server or `envtest` tests:
- Provider contract tests:
- Failure injection:
- Upgrade and rollback fixtures:
- End-to-end tests:
- Generated-code and manifest checks:
- Race, lint, vulnerability, image, and schema checks:

## Operations

- Metrics and cardinality:
- Structured log fields and redaction:
- Kubernetes Events:
- Health and readiness:
- Alerts and SLOs:
- Runbooks:
- Orphan and stuck-finalizer reporting:

## Review Questions

The design is not ready until it can answer:

1. What if reconciliation executes twice or concurrently?
2. What if the provider succeeds but the response is lost?
3. What if the process exits before status is written?
4. What if a cached read returns pre-write state?
5. What if another CR, cluster, controller, or human targets the same object?
6. What if the external resource changes outside Kubernetes?
7. What if deletion starts while the provider or credentials are unavailable?
8. What if an administrator removes a stuck finalizer?
9. What if the CR is recreated with the same name and a new UID?
10. What if the provider returns 429 for an hour?
11. What happens at 10,000 resources and under one noisy tenant?
12. Can the previous operator safely run after a rollback?
13. How does a user know that status is current and the resource is ready?
