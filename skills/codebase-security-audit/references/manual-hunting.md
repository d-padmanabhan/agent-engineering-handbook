# Manual Hunting

Checks for flaws that scanners rarely find. Use them in Phase 7 of the [codebase security audit skill](../SKILL.md), working through the coverage ledger in priority order. Every lead found here still goes through the candidate gate and refute-first validation before it becomes a finding.

Adapted and paraphrased from Cloudflare's [security-audit-skill](https://github.com/cloudflare/security-audit-skill/tree/c1c8a8c1471069fb0e188eeaff69b8e8db6564a8/skills/security-audit), Copyright (c) 2025-2026 Cloudflare, Inc., MIT License.

## Hunting Discipline

- Start each unit from a concrete invariant: the lower-trust principal, the input it controls, the control that should stop it, and the result that would cross the boundary.
- Compare sibling controls for equivalence, not just presence. A second path to the same state change often checks a weaker permission.
- Test sad paths: absent, empty, zero, negative, maximum, duplicate, out-of-order, and partially failed inputs.
- Look for disagreements between components: what one layer validates versus what the next layer assumes, including truncation, normalization, type coercion, and tenant scope.
- Read code that looks boring, half-finished, experimental, legacy, or explained away by a comment. Verify the comment.
- Use the API the way the frontend never would. The UI constrains users; the API may not.
- Check what the tests do not cover.
- A flag is not a finding. Trace the impact before reporting it.

## Access Control

- Is there another path to the same state change that checks a different or weaker permission?
- Can a request-body field override an owner, tenant, role, or status the permission system meant to restrict?
- Which endpoints authenticate but forget to authorize?
- Do bulk, batch, export, and import operations authorize each item, not just the request?
- Do background jobs, admin tools, legacy routes, and service clients carry the requesting principal, or run with broader authority?

## Business Logic

- **State machines:** Can steps be skipped, reversed, or replayed? Does a failure in step two roll back step one?
- **Races with business impact:** Non-atomic check-then-act operations that allow double spend, double approval, or lost updates.
- **Numeric manipulation:** Negative, zero, overflowing, imprecise, or string-coerced quantities.
- **Implicit trust:** Data from storage, configuration, plugins, or other components assumed safe because it was validated on a different path.
- **Time:** Expiry boundaries, rate windows, clock skew, and time-zone disagreements between components.
- **Defaults and fallbacks:** Security posture when configuration is missing, a feature flag is off, a dependency is unavailable, or a migration is half complete.

## Feature Abuse and Data Leakage

- **Export and backup:** Can a low-privilege user export data above their access, including deleted, draft, private, or other users' content?
- **Import and restore:** Can an import overwrite existing data, bypass validation, or write into collections the user cannot write?
- **Search, filter, and sort as oracles:** Can queries reveal the existence or values of content the user cannot read?
- **Enumeration through side effects:** Different errors, timings, sizes, or status codes for "does not exist" versus "no access", and enumeration through password reset, invite, or registration.
- **Preview and draft leakage:** Preview tokens that unlock more than one item, or drafts exposed through search, feeds, sitemaps, listings, or shared caches.
- **Callbacks as SSRF:** User-configurable webhook, notification, or callback URLs fetched by the server, including after redirects.

## Chained and Second-Order Flaws

- **Second-order use:** Data stored safely becomes dangerous later, for example a field name used as a JSON path, a slug used as a file path, escaped text rendered raw, or a stored string used as a URL, regex, template, or policy expression.
- **Capability growth:** Tokens, API keys, plugins, OAuth grants, or agent capabilities that broaden after delegation, refresh, caching, role change, or composition.
- **Timing windows:** Setup, migration, soft delete, revocation and cache expiry, and check-then-use windows where stale state is accepted.
- **Rollback and recovery:** Undelete, restore, and revision rollback must reapply current ownership, validation, and authorization.

## AI, LLM, and Agent Systems

The important flow is untrusted content, to model or memory, to a capability or sink.

- Injected instructions by themselves are not a vulnerability. Report one only when code lets that content cross a boundary: it lands in another principal's context, exercises authority the requester does not hold, exposes data the requester cannot read, or reaches a sink the requester cannot reach directly.
- Instructions to the model are not a control. Only deterministic checks, authorization scoped to the resource, isolation, and narrowly scoped credentials count as boundaries.
- **Indirect injection:** Who can write retrieved documents, tool responses, emails, or issue bodies that enter another principal's context, and what capability is enabled there?
- **Context bleed:** Retrieval, embeddings, conversation history, and prompt caches keyed without tenant and ACL filters in the query and every cache key.
- **Memory poisoning:** Low-trust observations or model summaries written to durable memory that later shapes another user's or a privileged session.
- **Role confusion:** Prompt assembly that lets untrusted text impersonate a system message, prior turn, tool result, or policy.
- **Tool arguments:** Model-produced arguments reaching SQL, shell, file, URL fetch, or privileged APIs without handler-side validation. Structured output narrows shape; it does not authorize.
- **Confused deputy:** Tools that run with a broad service identity and do not re-check the requesting principal's permission on the named resource.
- **Approval binding:** An approval must bind the normalized tool name, complete arguments, requester, target, amount, expiry, and batch membership. Retries and resumed sessions must not reuse it for a changed or duplicate action.
- **Schema and dispatcher disagreement:** Aliases, extra fields, duplicate keys, coercions, or defaults that the validator and the handler interpret differently.
- **MCP identity:** Calls or results routed by attacker-influenceable server or tool names rather than the authenticated connection. Can two servers claim the same tool, or one server's response satisfy another's pending call?
- **Metadata as policy:** Tool descriptions, schemas, or hints from an MCP peer treated as authorization rather than guidance.
- **Unbounded delegated loops:** One request that can enqueue repeated spend, sends, or mutations without a budget, per-action authorization, cancellation, or idempotency.

Design-time controls for these systems are in the Zero Trust skill (`${HANDBOOK_ROOT}/skills/zero-trust/SKILL.md`), including HITL receipts and MCP hardening.

## CI, Supply Chain, and Release

- Treat CI configuration as authorization code. Establish which event triggered each workflow, whose code runs, which secrets and tokens exist, and what the job may publish or mutate.
- **Untrusted code in privileged workflows:** Pull requests, comments, forks, or dependency updates that run contributor code with secrets, write tokens, deployment authority, or trusted runners.
- **Expression and command injection:** Branch names, commit messages, issue fields, artifact names, or matrix values that reach shell commands or privileged inputs without validation.
- **Cache and artifact trust mixing:** A lower-trust job populates a cache, artifact, or workspace that a higher-trust job restores, executes, or releases.
- **Mutable build inputs:** Floating action references, mutable container tags, branches, unverified submodules, or downloaded tools whose content can change without review.
- **Integrity roots:** A checksum fetched from the same untrusted location as the artifact proves nothing. Identify the independent trusted root.
- **Build-to-release substitution:** Tests, signatures, and publication that refer to mutable names instead of one immutable digest.
- A vulnerable or unpinned dependency alone is not a finding. Show who can influence it, which build consumes it, and what boundary follows.

## Data Isolation and Lifecycle

- A tenant field on a record is not isolation. Find the query, key, path, or policy that enforces it on every read and write path, including raw clients, background jobs, and migrations.
- **Key collisions:** Cache keys, object paths, search document IDs, and deduplication keys that omit tenant or environment.
- **Derived copies:** Search indexes, caches, thumbnails, previews, analytics, logs, and exports whose ACLs drift from the primary record or are not invalidated on change.
- **Signed references:** Shared links and signed URLs that outlive ACL changes or allow more than the issuing principal could.
- **Soft delete and revocation:** Lookups, relations, jobs, and restores that ignore lifecycle state; sessions, caches, and subscriptions that keep authorizing after membership removal or revocation.
- **Restore:** Backups and undo that reintroduce memberships, credentials, or permissions current policy no longer allows.

## Availability and Resource Exhaustion

Use code-level analysis and bounded local fixtures. Never test availability against shared or deployed systems.

- Superlinear regular expressions, parsers, or evaluators on untrusted input.
- Decompression and representation amplification.
- Unbounded buffering, cardinality, queries, or downstream fan-out.
- Expensive work performed before authentication.
- Quota accounting with the wrong scope or reset behavior.
- Work that continues after cancellation, retry storms, fail-open amplification, and poison records that block queues.

## Web Protocols and Authentication

- Request framing disagreements between proxies and origins, and cache poisoning or deception through unkeyed input.
- Trust in `Host` and forwarded headers.
- CSRF, session fixation and invalidation, and cookie scope.
- JWT verification and claim binding; OAuth and OIDC state, nonce, redirect, and callback binding; SAML signed-object binding.
- MFA and step-up downgrade or bypass, passkey verification, account linking collisions, and recovery flows.
- API-key scope and resource binding, and mTLS peer versus application identity confusion.
