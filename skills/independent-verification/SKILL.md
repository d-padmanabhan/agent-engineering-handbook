---
name: independent-verification
description: Independent, read-only verification workflow for consequential AI-generated changes. Use when security, IAM, production infrastructure, destructive migrations, broad architecture, sensitive data, financial logic, or explicit assurance requirements need a verifier distinct from the implementing model or tool. Binds verdicts to an immutable commit and diff hash, requires deterministic evidence first, treats AI verdicts as advisory, and escalates stale targets, disagreement, uncertainty, and high-risk release decisions to a human gate.
---

# Independent Verification

Use this skill to obtain evidence-backed review from a verifier that did not implement the change. This is a risk-control workflow, not a simulated panel and not a substitute for accountable human approval.

The mandatory trigger and release gate are owned by the workflow rule (`${HANDBOOK_ROOT}/rules/010-workflow.mdc`). This skill owns the verification procedure and artifact contract.

## Non-Negotiable Principles

1. **Deterministic evidence comes first.** Run applicable tests, lint, type checks, builds, policy checks, security scans, plans, and schema validation before asking a model to interpret the result.
2. **Freeze the review target.** Bind the request to an exact commit SHA and SHA-256 digest of the reviewed diff or patch. Moving branches and mutable working trees are not approval targets.
3. **Separate implementer and verifier.** Prefer a different tool and model provider. At minimum, use a fresh session with no implementer reasoning or hidden chain-of-thought.
4. **Keep the verifier read-only.** It reports findings and a verdict. It does not edit files, run deployments, write Git state, dismiss findings, or approve its own output.
5. **Use a trusted controller.** A small deterministic wrapper runs commands, enforces limits, checks hashes, and writes artifacts. It may create a worktree only after explicit HITL approval of the exact repository, destination path, branch, base ref, and command. The model never receives broad credentials or arbitrary write authority.
6. **Invalidate stale verdicts.** Any reviewed-file, commit, diff-hash, requirement, policy, or deterministic-evidence change requires another verification.
7. **AI verdicts are advisory.** A model cannot satisfy a mandatory human approval, CODEOWNERS review, protected-environment approval, or regulated sign-off.

## When Independent Verification Is Required

Require this workflow for:

- authentication, authorization, IAM, PKI, secrets, cryptography, or tenant boundaries;
- production infrastructure, deployment controls, destructive data/schema migrations, or rollback-sensitive changes;
- privacy, regulated data, financial calculations, safety-critical behavior, or irreversible external actions;
- broad architecture decisions, trust-boundary changes, or changes with difficult rollback;
- explicit user, policy, CODEOWNERS, compliance, or release-process requirements.

Use proportionate verification elsewhere:

- **Low risk:** deterministic checks and normal review.
- **Medium risk:** deterministic checks plus independent AI verification.
- **High or critical risk:** deterministic checks, independent AI verification, and an enforceable human gate.

Do not use file count as a risk classifier. A one-line IAM or production policy change can be critical; a broad generated-doc change can be low risk.

## Independence Levels

Record the actual level; do not overstate it:

1. **Same model, fresh session:** catches context and execution mistakes, but remains highly correlated.
2. **Different model family, same provider:** better diversity, with shared platform and training risks.
3. **Different provider and model family:** preferred AI verification for consequential work.
4. **Human domain owner:** accountable approval for high-risk release decisions.

Simulating multiple advisors inside one model is useful for ideation but is not independent verification.

## Verification Workflow

### 1. Classify Risk and Required Gates

State:

- risk tier and rationale;
- deterministic checks required;
- independent-verifier requirements;
- whether human approval is mandatory;
- release or deployment action that remains blocked.

If classification is uncertain, choose the higher tier until a human resolves it.

### 2. Freeze the Target

The trusted controller captures:

```bash
git rev-parse HEAD
git rev-parse '<target>^{tree}'
git diff --binary <base> <target> > reviewed.patch
git ls-tree -r --full-tree <target> > scope-manifest.txt
shasum -a 256 <reviewed-patch>
shasum -a 256 scope-manifest.txt
```

Prefer a clean, detached, read-only worktree at the target commit when its
creation has received the separate explicit HITL approval required by the Git
workflow rule. Otherwise, use an already approved checkout or a snapshot that
does not mutate the user's working tree.

For uncommitted work, the trusted controller must snapshot tracked, staged, unstaged, and untracked scoped files without modifying the real index. One Git-native approach is a temporary index:

```bash
temp_index="$(mktemp)"
GIT_INDEX_FILE="${temp_index}" git read-tree HEAD
GIT_INDEX_FILE="${temp_index}" git add -A -- path/to/approved-scope
snapshot_tree="$(GIT_INDEX_FILE="${temp_index}" git write-tree)"
git diff --binary <base> "${snapshot_tree}" > reviewed.patch
git ls-tree -r --full-tree "${snapshot_tree}" > scope-manifest.txt
rm -f "${temp_index}"
```

Before snapshotting, capture `git status --porcelain=v1 -z` and verify every approved changed or untracked path is represented in the snapshot manifest. Ignored files are excluded unless the approved scope explicitly includes a safe copy. Do not call a mutable working tree independently verified.

The request must include:

- repository identity;
- base and target commit SHAs, target type, and snapshot tree;
- diff and complete scope-manifest SHA-256 values;
- task requirements and approved scope;
- changed-file list;
- policy, requirements, and deterministic-evidence manifest hashes;
- relevant threat model, migration plan, or rollback plan.

### 3. Run Deterministic Gates

Run checks outside the model in a constrained controller. Examples:

- unit, integration, contract, and negative tests;
- compiler, formatter, linter, type checker, and build;
- SAST, SCA, secret, IaC, policy-as-code, and provenance checks;
- database migration validation and rollback rehearsal;
- Terraform/Kubernetes plans and schema validation.

A failed mandatory check blocks `PASS`. The verifier may explain a failure but cannot waive it.

### 4. Start a Read-Only Verifier

The verifier receives only the frozen target, requirements, and evidence needed for review.

Required controls:

- no repository, Git, cloud, database, ticket, or coordination-file writes;
- no deployment or credential tools;
- no production credentials;
- bounded time, tokens, tool calls, and cost;
- network denied unless a specific read-only source is required and logged;
- implementer reasoning excluded; decisions and requirements may be included.

Do not use `--dangerously-skip-permissions`. If a CLI cannot perform read-only verification without bypass mode, do not use that CLI as the verifier.

### 5. Review Adversarially

The verifier must:

1. Confirm target SHA, diff hash, scope, and evidence.
2. Seek counterexamples and failure paths rather than affirming the implementation.
3. Check correctness, security, regressions, rollback, observability, and requirement coverage.
4. Distinguish evidence from inference.
5. Report exact files, lines, commands, or artifacts supporting each finding.
6. State uncertainty and missing evidence explicitly.
7. Avoid proposing unrelated cleanup or silently fixing findings.

### 6. Produce a Verdict

Allowed verdicts:

- `PASS`: all mandatory evidence passed and no blocking finding remains.
- `PASS_WITH_NOTES`: no blocker; documented non-blocking observations remain.
- `NEEDS_REVISION`: one or more blocking findings or mandatory checks failed.
- `INCONCLUSIVE`: target, evidence, access, independence, or confidence is insufficient.

`INCONCLUSIVE` fails closed for release purposes.

Write a schema-valid artifact under:

```text
.agent/reports/verifications/<target-sha>/<verification-id>.json
```

Use the [verification artifact schema](references/verification-artifact.schema.json). Keep `.agent/reports/` excluded from Git unless policy explicitly requires a protected evidence repository.

Validate locally:

```bash
uv run python -m evals.verification_artifact <artifact.json>
uv run python -m evals.verification_artifact --for-release <artifact.json>
```

Artifacts can contain sensitive file names, findings, identities, and operational evidence. The trusted controller must:

- redact credentials, tokens, personal data, and unnecessary payload content;
- reject symlink destinations and unknown schema fields;
- cap artifact and evidence sizes;
- create `.agent/reports/` with mode `0700` and files with mode `0600`;
- write to a temporary file, flush and `fsync`, then atomically rename;
- apply a documented retention and secure-deletion policy;
- store long-lived or regulated evidence in an access-controlled evidence system rather than a developer workstation.

### 7. Revalidate Before Acceptance

Immediately before accepting the verdict, the trusted controller recomputes:

- target commit SHA;
- diff SHA-256;
- scope, policy, requirements, and evidence-manifest hashes;
- deterministic evidence status.

Reject the verdict as stale if any value changed.

### 8. Apply the Human Gate

For high or critical risk, require approval through an enforceable mechanism such as:

- GitHub CODEOWNERS and protected-branch reviews;
- protected deployment environments;
- change-management approval tied to the immutable target;
- named security, data, risk, or service owner approval.

The approval UI must show target identity, diff/plan, authority, impact, rollback, deterministic evidence, verifier findings, and expiration. Store the approver identity, timestamp, request hash, authoritative approval-system name, and immutable approval-record ID.

Before release, the trusted controller must query the protected approval system and verify that the approval record is authentic, approved, unexpired, and bound to the same request hash. Never trust model-generated or artifact-only approval text.

## Disagreement and Escalation

Escalate to a human when:

- implementer and verifier disagree on a blocking finding;
- two verifiers disagree;
- evidence is missing, stale, contradictory, or unverifiable;
- the verifier reports low confidence or `INCONCLUSIVE`;
- a finding would require risk acceptance;
- policy, security, privacy, financial, or regulatory interpretation is disputed.

Models cannot vote to break a tie. Do not average security vetoes into a weighted score.

## Trusted Controller Boundary

After the applicable authorization gate, the controller may:

- create or remove an isolated worktree only when that exact operation has
  separate explicit HITL approval;
- run allowlisted deterministic commands;
- capture stdout, stderr, exit codes, and artifact hashes;
- invoke a verifier with read-only capabilities;
- validate the verdict schema and target hashes;
- write the final artifact with restrictive permissions.

The controller must not:

- let model output become shell syntax;
- expose broad environment credentials;
- accept unknown tool calls or artifact fields;
- mark a human gate approved;
- merge, deploy, migrate, or push because an AI returned `PASS`.

## Reviewer Checklist

- [ ] Risk tier and human-gate requirement recorded
- [ ] Base/target SHA and diff SHA-256 captured
- [ ] Deterministic checks completed outside the model
- [ ] Verifier independence level recorded honestly
- [ ] Verifier had read-only, least-privilege capabilities
- [ ] Implementer reasoning was not supplied
- [ ] Findings cite exact evidence
- [ ] Verdict artifact validates against the schema
- [ ] Target and evidence revalidated after review
- [ ] Stale, disputed, or inconclusive verdicts escalated
- [ ] Human approval enforced for high/critical release decisions

## Reject These Patterns

- The implementer verifies or approves its own work.
- One model role-plays multiple reviewers and calls that independent.
- The verifier edits the implementation or auto-fixes findings.
- Verification runs against `main`, `HEAD`, or another moving reference without recording the resolved SHA.
- A mutable `.coordination.md` row is the only evidence of approval.
- An AI verdict overrides failed tests, policy checks, CODEOWNERS, or a human gate.
- `--dangerously-skip-permissions` is justified by a deny list.
- A `PASS` remains valid after the target, diff, requirements, or evidence changes.
