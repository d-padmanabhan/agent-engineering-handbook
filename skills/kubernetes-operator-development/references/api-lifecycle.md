# Operator API and Lifecycle

Use this reference when designing or reviewing CRD schemas, status, finalizers,
deletion, adoption, conversion, or upgrades.

## API Shape

Model user intent rather than provider calls. A resource such as
`ProtectedEndpoint` is usually a better platform API than fields for an HTTP
method, remote URL, and raw request body.

Choose namespaced scope when namespace tenancy, RBAC, and ownership apply.
Choose cluster scope only for concepts that genuinely span namespaces. A
namespaced CR does not make a global external resource name unique, so include
namespace and UID in external ownership identity.

Do not automatically begin every API at `v1alpha1`. Choose the version from
the API's promised stability:

- `v1alpha1`: experimental, limited compatibility promise;
- `v1beta1`: approaching stability but still subject to reviewed changes;
- `v1`: stable contract with compatibility and deprecation obligations.

An alpha label is not permission to make unplanned destructive changes.

## Structural Schema and Validation

Use `apiextensions.k8s.io/v1` and a structural OpenAPI v3 schema. Unknown fields
should be pruned unless a narrowly reviewed extension point requires
preservation.

Apply validation in this order:

1. OpenAPI type, format, enum, range, length, and required-field constraints.
2. CEL rules for cross-field and transition constraints that the API server
   can evaluate safely.
3. A validating webhook only for policy that cannot be represented in schema.
4. Reconciliation-time validation only for facts that require external state.

Prefer schema defaults to mutating admission. Defaults become part of API
compatibility: changing one can alter old clients and objects. Validate
defaulted values and distinguish omitted fields from explicit zero values when
that distinction matters.

For lists and maps, define atomic, set, or map semantics intentionally using
the Kubernetes schema extensions. These choices affect merge behavior,
patching, CEL cost, and Server-Side Apply ownership.

Do not call external providers from admission. Admission is on the Kubernetes
API request path and must remain fast, bounded, highly available, and
failure-aware.

## Spec and Status

`spec` is desired intent. `status` is the controller's latest observation.
Never write discovered IDs, runtime progress, or provider errors into `spec`.
Enable and use the status subresource.

Prefer `metav1.Condition` with a list map keyed by condition type:

```go
// +listType=map
// +listMapKey=type
// +optional
Conditions []metav1.Condition `json:"conditions,omitempty"`
```

Use `meta.SetStatusCondition` or equivalent semantics so
`lastTransitionTime` changes only when condition status changes. Each
condition should have:

- a positive, stable type such as `Ready`;
- `True`, `False`, or `Unknown`;
- a stable machine-readable reason;
- a concise message without secrets or raw provider responses;
- the observed generation to which it applies.

Consumers must not treat `Ready=True` as current unless its observed generation
matches `metadata.generation`. A top-level `status.observedGeneration` can be
useful, but it does not replace per-condition currency when conditions are
consumed independently.

Update status with a narrow status patch or update against current state.
Handle expected optimistic conflicts with a bounded re-read and retry or by
requeueing. Do not overwrite unrelated status written by another controller.

## Finalizers and Deletion

Add a finalizer before creating an external resource that requires cleanup.
Persist the finalizer and return or re-read before external creation. Cleanup
must be idempotent, and provider `NotFound` normally means cleanup succeeded.

A finalizer delays Kubernetes object deletion; it does not guarantee external
cleanup. Controllers can be unavailable, permissions can be revoked, an
administrator can remove finalizers, or a CRD can be removed incorrectly.
Document:

- maximum expected deletion duration and visible progress;
- terminal and retryable cleanup failures;
- a safe manual-unblock procedure;
- orphan discovery and repair;
- behavior when credentials or provider APIs are unavailable.

Do not add a finalizer when deletion has already started. Remove only this
controller's finalizer and only after its cleanup or explicit retention
contract is satisfied.

## Deletion Policy

Define `Delete`, `Retain`, or any archive behavior precisely. For durable data,
PKI, identity, production routing, and shared resources, use a conservative
default. A user-controlled `Delete` value is authorization-sensitive and must
not grant destructive provider authority merely because the schema accepts it.

Deletion must verify immutable external identity and ownership immediately
before mutation. Never delete based only on a display name, a mutable label, or
an ID copied from untrusted input.

## Adoption and Re-Creation

Adoption is a privileged lifecycle transition. Require:

- an explicit policy and authorized principal;
- a unique provider identity;
- verifiable ownership or a reviewed transfer mechanism;
- a conflict check proving no other CR owns the resource;
- an audit event and reversible handoff where the provider allows it.

Record Kubernetes namespace, name, and UID in provider metadata when possible.
A CR deleted and recreated with the same name has a different UID. It must not
silently gain authority over the old resource.

## Versioning, Conversion, and Upgrade

For multiple served versions, define one storage version and conversion that
round-trips all supported fields without semantic loss. Conversion webhooks
must be available, secured, monitored, and compatible through rollout and
rollback.

An upgrade plan must cover:

- CRD schema compatibility and validation ratcheting;
- served, storage, and deprecated versions;
- existing objects in old storage versions;
- conversion deployment ordering and certificate readiness;
- changed defaults, immutable fields, and status ownership;
- operator rollback while new objects or fields exist;
- generated manifests and client code.

Test upgrades from every supported release path with existing objects. Do not
remove a served version until clients have migrated and stored objects have
been rewritten to a supported storage version.

## Authoritative Sources

- [Kubernetes CRD documentation](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)
- [Kubernetes API conventions](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md)
- [Kubebuilder CRD generation](https://book.kubebuilder.io/reference/generating-crd.html)
- [Kubebuilder finalizers](https://book.kubebuilder.io/reference/using-finalizers)
