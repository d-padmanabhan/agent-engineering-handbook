---
name: zero-trust
description: Distinguished-engineer playbook for Zero Trust design reviews across identity, network, data, workload, and AI/agent systems. Principles-first, opinionated, threat-model-driven. Use when designing or reviewing auth flows, tool scopes for agents, MCP servers, RAG pipelines, egress policies, secret handling, HITL gates, or any change that crosses a trust boundary.
---

# Zero Trust - Distinguished Engineer Playbook

**Voice:** this skill speaks as a Distinguished Engineer in design review. Opinionated. Principles over products. Threat models before controls. Reversibility over cleverness. Will say "no" with reasons.

**Companion rule:** `316-zero-trust.mdc` (always-on). This skill turns those principles into reusable workflows.

---

## When to invoke this skill

Use when the user:

- Asks for Zero Trust review of an architecture, a PR, or a design doc
- Is designing or hardening an AI agent, MCP server, or RAG pipeline
- Needs a tool allow-list, capability-token design, or HITL gate
- Wants a threat model for prompt injection, secret leakage, or tool abuse
- Is arguing whether something is "Zero Trust" (it usually isn't)
- Needs cost / rate / quota controls treated as security

Do *not* use this skill for:

- OWASP Top 10 application bugs - use `security-testing` skill
- IAM protocol reference (OIDC mechanics, SAML bindings) - use `315-iam.mdc`
- Vendor-specific IAM (AWS, Azure, GCP) - use `412-aws-iam.mdc` and cloud rules

---

## The Five Golden Rules (anchor for every review)

1. Never trust, always verify.
2. Least privilege, per call, per session.
3. Assume breach.
4. Deterministic guardrails before LLM decisions.
5. Auditability for every trust decision.

When you cannot ground a design decision in one of these, stop and ask why.

---

## Workflow 1 - Design an Agent Under Zero Trust

Produce a Zero Trust design doc for a new AI agent or MCP-backed feature.

### Steps

1. **State the purpose and blast radius.** What can this agent change, send, buy, delete, or disclose? Write the worst-case outcome in one sentence.
2. **Enumerate tools.** Each tool gets: name, inputs, outputs, identity it runs as, resources it touches, and reversibility (reversible / destructive / irreversible).
3. **Scope each tool's identity.** Prefer narrow roles: `order_service_reader_for_tenant_X` beats `order_service_admin`.
4. **Replace credentials with capability tokens.** Tools accept short-lived tokens bound to `(caller, resource, action, time)`. Never raw secrets.
5. **Classify data flows.** For each tool: what data goes out (to model / external API), what data comes back. Mark PII/PCI/PHI fields.
6. **Design the HITL gate.** Every destructive/irreversible action has: preview, timeout, signed receipt, audit.
7. **Define per-tenant isolation.** Prompts, retrieval indexes, memory - all tenant-scoped. Prove it with a test.
8. **Set rate and cost caps.** Per session, per user, per tenant. Hard stops, not warnings.
9. **Specify audit events.** For each tool invocation: who, when, inputs (hashed/redacted), policy version, decision, result.
10. **Write the prompt-injection threat model.** Where does untrusted text enter? What's the worst thing a crafted input could do? What's the mitigation?

**Deliverable:** design doc with the sections above + a Do/Don't table.

See [references/agent-design.md](references/agent-design.md) for templates.

---

## Workflow 2 - Harden an Existing MCP Server

Take an MCP server from "it works" to "it's reviewed".

### Steps

1. **Inventory tools.** List every tool with signature and description. If you can't explain a tool in one sentence, it's too broad - split it.
2. **Flag overly broad tools.** Anything named `run_*`, `execute_*`, `query_*`, `fetch_url`, `write_file` without a path allow-list, `send_*` without a recipient allow-list. Replace with narrower tools.
3. **Require identity on every call.** The MCP server must verify who is calling (OIDC, mTLS, or signed caller token) and refuse to act without identity.
4. **Scope tokens to the caller.** Capability tokens minted per session, per caller, per resource. No shared master token.
5. **Add schema validation on inputs.** Reject out-of-schema inputs with structured errors; never pass unvalidated input to downstream systems.
6. **Sanitize outputs.** Strip secrets from tool outputs before returning. The model will log what it sees.
7. **Add an HITL wrapper** for destructive tools. The MCP server returns a "pending approval" result; a separate surface collects the signed approval; the tool executes only on receipt.
8. **Add audit emission.** Every tool call emits a structured event to an append-only store.
9. **Add rate + cost limits.** Per caller, per tool. Hard stops.
10. **Write a prompt-injection test suite.** Adversarial inputs for each tool; assert the server refuses or narrows the action.

**Deliverable:** PR with narrowed tools, capability-token auth, schema validation, audit emission, HITL wrapper, and tests.

See [references/mcp-hardening.md](references/mcp-hardening.md) for checklists and patterns.

---

## Workflow 3 - Review an AI Feature for Injection and Secret Leak

Fast review pass. Use on any PR that adds LLM calls or tool invocations.

### Steps

1. **Find every string the model sees.** System prompt, user input, tool outputs, RAG chunks, file contents, URL fetches. Each is an injection vector.
2. **Find every string the model emits that triggers a side effect.** Each is an output-injection risk.
3. **Check separation of instructions and data.** System prompt and trusted tool results vs user/tool content - distinct channels where the framework supports it.
4. **Check schema enforcement.** Structured output? Schema validated before use? Policy check before side effect?
5. **Check secret flow.** Does the model see any secret value? If yes - stop. Route through a tool.
6. **Check logging.** Are request/response bodies redacted? Are tool outputs scrubbed before logs?
7. **Check RAG provenance.** Is each chunk tagged with tenant/source/classification? Is retrieval filtered at query time? Is classification checked before rendering?
8. **Check HITL for destructive actions.** Does "the model said the user approved" short-circuit a gate? (Find the gate code; read it; make sure approval is a signed receipt, not a string.)
9. **Check tenant isolation** in memory and retrieval.
10. **Check cost and rate caps.**

**Deliverable:** review comments with principle references (golden rules 1-5) and concrete fixes.

See [references/injection-threat-model.md](references/injection-threat-model.md) for a reusable threat model. For auditing an existing codebase rather than reviewing a design, use the AI and agent checks in the codebase security audit manual-hunting reference (`${HANDBOOK_ROOT}/skills/codebase-security-audit/references/manual-hunting.md`).

---

## Workflow 4 - Add HITL Gates to Destructive Tools

Retrofit HITL onto an agent or tool layer that doesn't have one.

### Steps

1. **Enumerate destructive tools.** Delete, deploy, publish, pay, send, grant, message, push, commit.
2. **Define approval payload.** `{action, target, caller, preview, diff, requested_at, expires_at, request_hash}`.
3. **Build the gate surface.** UI (web, chat, email) that shows the payload and collects approval.
4. **Sign approvals.** Gate returns `{request_hash, approver_id, approved_at, signature}`. Signature uses a key the tool server can verify.
5. **Require signed receipts on tool invocation.** Tools reject calls without a valid, unexpired, matching receipt.
6. **Time-bound and single-use.** Receipts expire; receipts are single-use (tracked in a ledger).
7. **Audit approvals.** Every request, approval, denial, timeout logged to the append-only store.
8. **Test bypass attempts.** Can the model fake approval? Reuse a receipt? Race a replay? Expire-but-succeed?

**Deliverable:** gate service, receipt format, verification middleware, audit events, bypass test suite.

See [references/hitl-gates.md](references/hitl-gates.md) for sequence diagrams and receipt format.

---

## Workflow 5 - Produce a Zero Trust Threat Model + Reviewer Checklist

Output a short threat model for a feature crossing a trust boundary.

### Steps

1. **Describe the feature in one paragraph.** Scope, principals, data, actions.
2. **Draw the trust boundaries.** Mermaid diagram: principal -> verify -> authorize -> resource + audit.
3. **Enumerate the principals** and their identities (human, service, agent, model).
4. **Enumerate the assets** and classifications.
5. **Enumerate the actions** and reversibility.
6. **Enumerate threats** (STRIDE + AI-specific: prompt injection, secret leak, tool abuse, cost abuse, cross-tenant leak).
7. **For each threat: control, owner, test.**
8. **Emit the reviewer checklist** from `316-zero-trust.mdc` tailored to this feature.

**Deliverable:** one-page threat model + checklist attached to the PR or design doc.

See [references/threat-model-template.md](references/threat-model-template.md).

---

## Workflow 6 - Adversarially Validate an Architecture Pattern

Use after proposing a Zero Trust architecture and before treating the design as ready.

### Steps

1. **Restate the claimed guarantees.** Name the protected assets, principals, enforcement points, failure domains, and assumptions.
2. **Run the reality check.** Test scale, quotas, latency, availability, operational ownership, cost, control-plane dependency, and degraded behavior.
3. **Challenge necessity.** Identify a simpler design and state when the proposed pattern should not be used.
4. **Simulate abuse defensively.** For each credible path, record preconditions, affected control, blast radius, persistence, and observable evidence. Include identity theft, replay, confused deputy, privilege escalation, lateral movement, data exfiltration, agent tool abuse, and control-plane compromise where applicable.
5. **Switch to defender analysis.** Map each path to prevention, detection, containment, recovery, owner, and a deterministic test.
6. **Test chained failure.** Assume one preventive control fails; verify another distinct control detects or contains the attack rather than repeating the same decision.
7. **Revise and re-run.** Update the architecture, then repeat the reality and abuse checks until blockers are resolved or explicitly accepted.

**Deliverable:** adversarial architecture review with prioritized findings, simpler alternative, when-not-to-use criteria, control/test mapping, and unresolved risk owners.

Follow the adversarial architecture review reference (`${HANDBOOK_ROOT}/skills/zero-trust/references/adversarial-architecture-review.md`).

---

## Review Output Format

When reviewing, structure findings like this:

```
[BLOCKER] <one-line summary>
Principle: <which golden rule>
Evidence: <file:line or config snippet>
Why it matters: <blast radius / attack path>
Fix: <specific, actionable>

[IMPORTANT] <...>
[SUGGESTION] <...>
```

- BLOCKER = violates a golden rule or introduces unacceptable blast radius
- IMPORTANT = serious weakening of Zero Trust posture
- SUGGESTION = tightens posture; not required to merge

No vague "consider adding security". Be specific. Show the code.

---

## Common Failure Modes (call these out)

- "Zero Trust" used as marketing for what is still perimeter security
- Long-lived credentials because "rotation is a pain"
- Agent with admin role "temporarily"
- Model as policy engine ("the LLM will decide what's safe")
- RAG with a shared index across tenants
- HITL gate where the model synthesizes approval
- Audit logs in mutable app log store
- Rotation-as-control instead of short-lived credentials
- "Internal" APIs trusted because VPC
- Security groups used as the authorization layer

Each of these is in `316-zero-trust.mdc` with principle and fix.

---

## References

- [references/agent-design.md](references/agent-design.md) - Agent design template with tool inventory, HITL, audit plan
- [references/mcp-hardening.md](references/mcp-hardening.md) - MCP server hardening checklist and patterns
- [references/injection-threat-model.md](references/injection-threat-model.md) - Prompt injection threat model and defenses
- [references/hitl-gates.md](references/hitl-gates.md) - HITL gate design, receipt format, verification
- [references/threat-model-template.md](references/threat-model-template.md) - One-page Zero Trust threat model
- adversarial architecture review (`${HANDBOOK_ROOT}/skills/zero-trust/references/adversarial-architecture-review.md`) - Reality check, defensive abuse simulation, and design iteration

## Related

- Rule: `316-zero-trust.mdc` (the always-on companion)
- Rule: `310-security.mdc` (OWASP)
- Rule: `315-iam.mdc` (IAM protocols)
- Rule: `412-aws-iam.mdc` (AWS IAM specifics)
- Rule: `500-ai-ml.mdc`, `510-mcp-servers.mdc` (AI and MCP patterns)
- Rule: `020-agent-audit.mdc` (local agent guardrails)
- Skill: `security-testing` (OWASP checklist + testing)
- Skill: `codebase-security-audit` (evidence-gated audit of an existing codebase)
- Skill: `mcp-development` (building MCP servers)
