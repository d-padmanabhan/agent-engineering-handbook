---
name: workload-identity
description: Workload identity playbook (SPIFFE/SPIRE, cloud IAM, OIDC federation). Workflows for picking SPIFFE vs cloud IAM, deploying SPIRE on EKS, federating trust domains, bridging to AWS/GCP/Azure via OIDC, and migrating off long-lived workload secrets. Use when designing or hardening service-to-service auth for k8s, multi-cloud, or AI agents.
---

# Workload Identity - Playbook

**Companion rule:** `318-workload-identity.mdc`. This skill turns the principles into end-to-end workflows.

**Scope:** the *infrastructure* layer of identity. For the *application* layer (cross-app, agent-on-behalf-of-user), use `skills/okta` (XAA / ID-JAG) and `skills/zero-trust` (HITL gates, threat models).

---

## When to invoke

Use when the user is:

- Designing service-to-service auth for a Kubernetes platform
- Choosing between SPIFFE/SPIRE and cloud IAM (IRSA, GCP Workload Identity, Azure Managed Identity)
- Deploying SPIRE on EKS / GKE / AKS (or evaluating Red Hat ZTWIM on OpenShift)
- Federating SPIFFE trust domains (multi-cluster, multi-cloud, or cross-org)
- Bridging SPIRE to cloud IAM via OIDC (AssumeRoleWithWebIdentity, GCP WIF, Azure federated credentials)
- Migrating workloads off long-lived secrets, instance profiles, or shared service accounts
- Sizing the operational SLOs for a workload-identity rollout
- Picking between SPIRE topologies (single-cluster, nested, federated, HA)

---

## Golden Rules (anchor every decision)

1. **Attestation, not credentials.** If the design ships a long-lived workload secret, restart.
2. **Trust domain per environment.** `prod`, `staging`, `dev` are separate roots of authority.
3. **Image-digest selectors** beat image-tag selectors. Always.
4. **mTLS proves *who*. Authorization is separate.** Pair with Istio AuthorizationPolicy / OPA / Lattice auth policy.
5. **TTL in hours for X.509-SVIDs, minutes for JWT-SVIDs.** SDK auto-rotates.
6. **One substrate per workload, but the platform mixes both.** SPIFFE for portable / k8s east-west; cloud IAM for cloud-native single-cloud.
7. **OIDC bridge collapses "give pods cloud creds" to "trust my SPIFFE issuer".**

---

## Workflow 1 - Pick SPIFFE vs Cloud IAM

The most common architecture decision in this space.

### Steps

1. **Scope** the choice: which workload, which trust boundaries, which clouds, which platforms.
2. **Score against the dimensions** in [references/spiffe-vs-cloud-iam.md](references/spiffe-vs-cloud-iam.md):
   - Portability needed?
   - Attestation granularity required (image digest vs cloud role)?
   - Operational capacity for SPIRE (HA, CA, observability)?
   - Cloud-team IAM depth?
   - Service-mesh strategy?
3. **Default rules:**
   - Inside one cloud, IAM-deep team, no portability need → cloud IAM (IRSA / VPC Lattice for AWS; Workload Identity for GCP; Managed Identity for Azure)
   - Multi-cloud, k8s-heavy, ISV / portable platform → SPIFFE
   - Most enterprises: **both**, segmented by workload class
4. **Decide and document** in an ADR (don't fold this into a generic "design doc" - it's worth its own).
5. **Plan the OIDC bridge** (Workflow 4) if SPIFFE is on one side and cloud creds on the other.

**Deliverable:** ADR with decision, scope, alternatives considered, and the boundary between SPIFFE and cloud-IAM-managed workloads.

See [references/spiffe-vs-cloud-iam.md](references/spiffe-vs-cloud-iam.md).

---

## Workflow 2 - Deploy SPIRE on EKS

Production-ready SPIRE on EKS with image-digest selectors and Vault PKI as upstream CA.

### Steps

1. **Trust domain decision.** One per environment (`prod.example.com`, `staging.example.com`, `dev.example.com`). Hard to change later.
2. **SPIRE Server topology.**
   - HA: at least 2 replicas behind an internal NLB.
   - Datastore: RDS Postgres (Multi-AZ), encrypted at rest, in a private subnet.
   - UpstreamAuthority: Vault PKI (or AWS Private CA). SPIRE Server becomes an intermediate CA.
3. **SPIRE Agent.**
   - DaemonSet, runs as privileged for `/proc` and CRI socket access.
   - Node attestor: `aws_iid` (EC2 instance identity document) with the cluster's OIDC issuer.
4. **Workload attestor.**
   - `k8s` plugin with namespace, service-account, and **container image digest** selectors.
   - `unix` plugin as backup for non-k8s workloads on the node.
5. **Registration entries.**
   - Author via Terraform (`spire-controller-manager` CRDs) or `spire-server entry create` in CI.
   - Selectors include `k8s:ns:<ns>`, `k8s:sa:<sa>`, `k8s:container-image:<image>@sha256:...`.
6. **Workload integration.**
   - Sidecar (Envoy + SDS) for polyglot workloads.
   - Library (`go-spiffe`, `java-spiffe`) for high-perf services.
   - Ambient mesh (Cilium / Istio Ambient) for encrypt-everything-east-west cases.
7. **Authorization on top.**
   - Istio AuthorizationPolicy with `source.principal` matching SPIFFE IDs.
   - Or Envoy ext_authz to OPA with Rego policy.
   - Default-deny per service.
8. **Audit and monitoring.**
   - SPIRE Server audit log → SIEM.
   - Metrics: SVID issuance latency, renewal failures, registration entry counts.
   - Alerts: handshake failure spikes, agent attestation failures.
9. **Cutover plan.**
   - Phase 1: SPIRE deployed but not enforced; shadow-mode logging.
   - Phase 2: Enforce per service (start with non-critical), measure error budget.
   - Phase 3: Default-deny across the mesh.
10. **Disaster recovery.**
    - Datastore backup, restore runbook.
    - Trust-bundle export for cross-region recovery.
    - Rotation of upstream CA documented.

**Deliverable:** Terraform modules (SPIRE Server, Agent DaemonSet, registration), runbooks, dashboards, error-budget policy.

See [references/spire-on-eks.md](references/spire-on-eks.md).

---

## Workflow 3 - Federate Trust Domains

Multi-cluster, multi-cloud, or cross-org. Two trust domains exchange bundles so workloads on each side can verify the other's SVIDs.

### Steps

1. **Define the federation graph.** Which trust domains federate with which? Federation is bilateral; consider a hub-and-spoke vs full-mesh.
2. **Bundle endpoint setup.** Each SPIRE Server exposes its bundle at an HTTPS endpoint, signed by a known certificate. Use a stable URL with rotation in mind.
3. **Bundle endpoint authentication.**
   - `https_spiffe` - peer authenticates the endpoint via a SPIFFE ID (best for mature deployments).
   - `https_web` - peer trusts the bundle endpoint cert via Web PKI (simpler bootstrap).
4. **Configure remote bundle on each Server.** `spire-server bundle set -id spiffe://other.example.com -path ...`.
5. **Federation policy.** Mark registration entries as federated so SPIRE issues SVIDs that include the federated trust bundle.
6. **Authorization across federation.** Istio / OPA policies must allow remote SPIFFE IDs explicitly. Don't trust by federation alone.
7. **Rotation and revocation.** Bundles are fetched periodically (default 5 min). Plan for partial unavailability of the remote endpoint.
8. **Audit.** Log federation events; alert on bundle fetch failures.

**Deliverable:** Federation topology diagram, bundle endpoint config, cross-domain authorization policies, runbook for adding/removing a federated peer.

---

## Workflow 4 - OIDC Bridge to Cloud IAM

Trade a JWT-SVID for cloud creds. No static cloud key.

### Steps

1. **Enable the SPIRE OIDC Discovery Provider.** Exposes `.well-known/openid-configuration` and the JWKS over HTTPS at a stable URL.
2. **Per cloud:**
   - **AWS** - register the SPIRE OIDC provider in IAM (Identity Provider). Define a trust policy on the target role with `sub` matching the specific SPIFFE ID. Workload calls `AssumeRoleWithWebIdentity`.
   - **GCP** - configure Workload Identity Federation: workload identity pool + provider pointing to the SPIRE OIDC endpoint; pool member maps to a service account; workload calls the STS endpoint.
   - **Azure** - federated credential on the User-Assigned Managed Identity referencing the SPIRE issuer + subject; workload calls the Azure AD token endpoint.
   - **Vault** - `auth/jwt` method with the SPIRE issuer; role binds bound claims to a Vault policy.
3. **Trust-policy hardening.** Always pin the `sub` claim to a specific SPIFFE ID. Never trust the issuer alone.
4. **Token TTLs.** Cloud creds inherit the issuing service's defaults; tune to minutes.
5. **Audit.** Log token exchanges on both sides; the cloud audit log is your record of who got what when.
6. **Rotation.** SPIRE auto-rotates the JWT-SVID; cloud trust policy doesn't need rotation as long as the issuer URL and JWKS are stable.

**Deliverable:** OIDC provider config per cloud, trust policies pinned to SPIFFE IDs, audit dashboards, key rotation runbook.

---

## Workflow 5 - Migrate Off Long-Lived Workload Secrets

The most-requested operational workflow.

### Steps

1. **Inventory.** Every workload secret in production. Sources: secrets manager, k8s Secrets, Helm values, env vars, mounted files, code.
2. **Classify by replacement substrate:**
   - Cloud-resource access from a cloud workload → **cloud IAM** (IRSA / Pod Identity / Workload Identity / Managed Identity). Eliminates the secret entirely.
   - Service-to-service inside a cluster → **SPIFFE SVIDs** + mTLS, replace bearer tokens.
   - Cloud access from outside the cloud (CI, on-prem) → **OIDC federation** (GitHub OIDC → cloud STS; SPIRE → cloud STS).
   - Vendor / SaaS → **OAuth client credentials** with short-lived access tokens; rotate the client secret in vault.
3. **Migration order.** Highest blast radius first (admin-scoped, multi-tenant, internet-exposed). Lowest second (analytics workloads, dev tools).
4. **For each workload:**
   - Provision the new identity primitive.
   - Deploy code change to fetch creds from the new substrate.
   - Verify in shadow mode (both old and new working).
   - Cut over.
   - Revoke the old secret.
   - Confirm via audit that no caller is using the old secret.
5. **Decommission.** Revoke unused secrets after a grace period; delete the secret store entries.
6. **Prevent regression.**
   - CI: pre-commit secret scanning (Gitleaks / TruffleHog / GitGuardian).
   - PR template asks "is a new long-lived secret introduced?".
   - SCPs / OPA policies block the creation of static IAM users in prod accounts.

**Deliverable:** Inventory + status board, per-workload migration runbook, decommission audit, regression prevention controls.

---

## Workflow 6 - Cloudflare Access / AOP / Worker JWT Layering

Decision matrix for HTTP-edge identity. (Lifted from the broader Cloudflare context; see also `400-cloudflare.mdc`.)

| Layer | Usually redundant | Still useful |
|---|---|---|
| **Cloudflare Access** | Re-validating the same IdP token, same issuer/audience/group already enforced by Access | Centralized edge authorization for coarse route access |
| **Worker JWT validation** | Repeating Access policy checks with no new claims | API-specific checks: audience, scope, tenant, route, method, fine-grained claim conditions |
| **Origin validation** | A second full interactive login after Access | Lightweight verification of `Cf-Access-Jwt-Assertion`, AOP/mTLS, service-specific authorization |

**Rule of thumb:** do not duplicate the same authentication decision. Add another layer only when it enforces a different boundary or finer-grained authorization.

For internal workloads (not internet-origin HTTP), this rule is the same: each layer must answer a *different* question, or it's not pulling its weight.

---

## Anti-patterns (reviewers call these out)

1. EC2 instance profile as the identity for high-density shared compute.
2. One trust domain across environments.
3. Long-lived JWT-SVIDs (defeats rotation).
4. mTLS without an authorization layer ("we have mTLS so we're done").
5. Identity in the cert CN instead of the URI SAN.
6. Hand-distributed trust bundles instead of Workload API.
7. Treating SPIFFE and cloud IAM as complements *for the same workload*.
8. Self-signed SPIRE root in prod (no UpstreamAuthority).
9. Image-tag selectors instead of digest.
10. Assuming TTL is sufficient when sub-second revocation is required.

---

## Review Output Format

```
[BLOCKER] <one-line summary>
Principle: <which golden rule>
Evidence: <file:line, ADR ref, or runtime evidence>
Why it matters: <blast radius / attack path>
Fix: <specific, actionable>

[IMPORTANT] <...>
[SUGGESTION] <...>
```

BLOCKER = violates a golden rule (e.g., long-lived workload secret introduced; mTLS without authz; selector without image digest).
IMPORTANT = misalignment with `318-workload-identity.mdc`.
SUGGESTION = tightens posture / improves operability.

---

## References

- [references/spiffe-vs-cloud-iam.md](references/spiffe-vs-cloud-iam.md) - the decision matrix in depth
- [references/spire-on-eks.md](references/spire-on-eks.md) - SPIRE Server + Agent on EKS, Vault PKI upstream
- [references/oidc-federation-bridges.md](references/oidc-federation-bridges.md) - SPIRE → AWS / GCP / Azure / Vault

## Related

- Rule: `318-workload-identity.mdc` (the principles)
- Rule: `316-zero-trust.mdc` (always-on)
- Rule: `317-okta.mdc` (Okta + XAA at the application layer)
- Rule: `412-aws-iam.mdc` (IRSA, Pod Identity, VPC Lattice)
- Rule: `450-kubernetes.mdc` (mesh patterns)
- Skill: `zero-trust` (threat models, HITL, MCP hardening)
- Skill: `aws-iam` (AWS IAM operational patterns)
- Skill: `okta` (Okta operations, XAA workflows)
