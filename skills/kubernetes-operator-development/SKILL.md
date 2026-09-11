---
name: kubernetes-operator-development
description: Designs, implements, reviews, tests, and operates Kubernetes operators and controllers in Go with Kubebuilder and controller-runtime. Use when defining CRDs, reconciliation loops, status conditions, finalizers, admission webhooks, external-provider controllers, operator upgrades, envtest suites, or controller-runtime cache, retry, and concurrency behavior.
---

# Kubernetes Operator Development

Mandatory controller and cluster-mutation gates live in the Kubernetes rule
(`${HANDBOOK_ROOT}/rules/450-kubernetes.mdc`). This skill owns the operator
design and implementation workflow. Use the Kubernetes containers skill
(`${HANDBOOK_ROOT}/skills/kubernetes-containers/SKILL.md`) for workloads,
Helm, Argo CD, and cluster operations.

## Core Contract

A custom resource expresses desired intent. Reconciliation observes desired
and actual state, performs retry-safe work, and records what was observed.
Events only indicate that state might have changed; they are not durable
exactly-once commands.

Every design must answer:

- What is authoritative, and which fields does this controller own?
- How is each external resource identified and ownership-verified?
- What happens after duplicate delivery, restart, timeout, or lost response?
- What is safe to create, adopt, update, retain, and delete?
- What makes each condition current for the resource generation?
- What bounds retries, provider calls, concurrency, and tenant impact?
- How are API and operator upgrades rolled forward and back?

Do not implement a one-shot provisioning workflow inside `Reconcile`.

## Decide Whether to Build an Operator

Prefer an existing Kubernetes API, vendor operator, Crossplane provider,
cloud service operator, or composition mechanism when it already provides the
required ownership and lifecycle semantics.

Build a custom operator when continuous convergence, a domain-specific API,
multi-resource ownership, or custom lifecycle policy creates clear platform
value. Do not wrap a trivial remote API call merely to expose it as a CRD.

## Design Before Coding

Complete the design review template
(`${HANDBOOK_ROOT}/skills/kubernetes-operator-development/references/design-review-template.md`)
before scaffolding implementation. Resolve:

1. API intent, scope, maturity, and compatibility.
2. Source of truth and field ownership.
3. External identity, collision prevention, and adoption proof.
4. finalizer, deletion, orphan, and recovery behavior.
5. status conditions and readiness semantics.
6. retry, rate-limit, timeout, and concurrency budgets.
7. authentication, Kubernetes RBAC, and provider authorization.
8. test, upgrade, observability, and rollback evidence.

Use Kubebuilder scaffolding unless repository constraints justify another
framework. Verify current Kubebuilder, controller-runtime, Go, and Kubernetes
compatibility from official release and support documentation. Do not copy
version-specific snippets without checking the repository's pinned versions.

## Reconciliation Workflow

Keep `Reconcile` as orchestration:

1. Read the primary resource; ignore a true API `NotFound`.
2. Handle deletion before normal reconciliation.
3. Persist the finalizer before creating resources that require cleanup, then
   return or re-read before continuing.
4. Validate runtime prerequisites not enforceable at admission.
5. Observe actual state and verify ownership.
6. Build desired state and calculate the owned-field delta.
7. Apply at most the safe, bounded work justified by current observations.
8. Update status through the status subresource with current conditions and
   `observedGeneration`.
9. Return an error or explicit requeue only under the documented retry policy.

External creation must survive a successful provider mutation followed by a
lost response. Prefer a provider idempotency key or conditional create tied to
stable operation identity. Observe-before-create is useful but is not by
itself race-safe.

Use stable provider identifiers plus verifiable ownership metadata such as the
Kubernetes namespace, name, and UID. Status is operational state, not proof of
ownership. A deleted and recreated CR has a new UID and must not silently
inherit destructive authority over an old external resource.

Detailed runtime guidance:
`${HANDBOOK_ROOT}/skills/kubernetes-operator-development/references/reconciliation-runtime.md`.

## API and Lifecycle

- Use `apiextensions.k8s.io/v1` structural schemas and prune unknown fields.
- Prefer OpenAPI defaults and validation, then CEL, then admission webhooks
  only when schema mechanisms cannot express the policy.
- Model lists and maps with explicit merge semantics where field ownership or
  Server-Side Apply depends on them.
- Use `metav1.Condition`; condition types are positive summaries, reasons are
  stable machine-readable identifiers, and messages are safe human context.
- Make destructive deletion and adoption explicit, authorized, auditable, and
  ownership-checked. Conservative defaults are required for durable data.
- Treat conversion, storage-version migration, default changes, and rollback
  as one upgrade contract.

Detailed API guidance:
`${HANDBOOK_ROOT}/skills/kubernetes-operator-development/references/api-lifecycle.md`.

## Provider and Security Boundaries

- Prefer workload identity. Keep raw credentials outside model, CR `spec`,
  status, logs, events, and metrics.
- Grant Kubernetes and provider permissions per resource and action; avoid
  wildcard access.
- Validate provider destinations and identifiers. User-controlled endpoints
  require scheme, host, redirect, DNS, address, timeout, and response-size
  controls.
- Reuse bounded provider clients and transports. Coordinate controller,
  provider SDK, and HTTP retry layers so delays do not multiply.
- Apply global and per-tenant concurrency and rate limits. A noisy tenant must
  not consume the entire controller or provider budget.
- Do not force Server-Side Apply ownership over fields managed by humans or
  other controllers.

Use the workload identity, service resilience, observability, security
testing, and Go systems skills for their canonical cross-cutting workflows.

## Verification

Test at the smallest layer that proves the behavior:

- unit tests for desired-state construction, diffs, classification, and
  provider translation;
- API-server or `envtest` tests for schema, status, finalizers, watches,
  indexes, conflicts, and reconciliation;
- provider contract tests for idempotency, lost responses, throttling,
  eventual consistency, and ownership checks;
- upgrade tests for served and storage versions, conversion, changed defaults,
  rollback, and existing objects;
- end-to-end tests for create, drift, partial failure, restart, deletion,
  retention, adoption, and orphan recovery.

Fake clients do not prove API-server behavior. `envtest` does not run every
Kubernetes controller, so garbage collection and other control-plane behavior
need explicit substitutes or real-cluster tests.

Run repository generation, formatting, lint, race, vulnerability, manifest,
schema, and test commands. Confirm generated code and manifests are current
and inspect their diff. See the testing and operations reference
(`${HANDBOOK_ROOT}/skills/kubernetes-operator-development/references/testing-operations.md`).

## Review Output

Lead with correctness and data-loss risks. Report:

1. API and ownership contract.
2. Reconciliation safety under retry, concurrency, and partial failure.
3. Deletion, adoption, and upgrade hazards.
4. Security, scale, and operability gaps.
5. Exact verification evidence and remaining limitations.
