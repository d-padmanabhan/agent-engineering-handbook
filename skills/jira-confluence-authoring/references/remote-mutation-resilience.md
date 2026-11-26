# Remote Mutation Resilience

This reference covers Atlassian-specific behavior only. General retry budgets, jittered backoff, coordinated backoff, client-side pacing, request coalescing, and ambiguous-mutation handling are canonical in the service resilience skill (`${HANDBOOK_ROOT}/skills/service-resilience/SKILL.md`). Idempotency contracts are in the API design skill (`${HANDBOOK_ROOT}/skills/api-design/SKILL.md`), and multi-step recovery is in the distributed transactions skill (`${HANDBOOK_ROOT}/skills/distributed-transactions/SKILL.md`).

Public sources:

- [Jira Cloud rate limiting](https://developer.atlassian.com/cloud/jira/platform/rate-limiting/)
- [Build an app that respects rate limits](https://developer.atlassian.com/cloud/jira/platform/build-an-app-that-respects-rate-limits/)
- [Confluence Cloud rate limiting](https://developer.atlassian.com/cloud/confluence/rate-limiting/)
- [Jira search after write](https://developer.atlassian.com/cloud/jira/platform/search-and-reconcile/)

## Operation Ledger

Before the first write, assign a stable operation ID and record each step's target, status, returned IDs, keys, URLs, and latest snapshot token in a local, non-sensitive ledger. Reuse the operation ID for retries and resumption. Never store tokens, credentials, or restricted content in the ledger.

## Classifying Atlassian Responses

| Outcome | Examples | Action |
| --- | --- | --- |
| Partial success | MCP response reports the main write applied but a secondary action failed | Record what applied; never repeat the applied write |
| Throttled | `429` | Scoped shared backoff; retry within budget |
| Transient | `503` with `Retry-After` | Retry reads and conditional updates; for creates, treat as an unknown outcome |
| Conflict | Stale snapshot, version conflict, `409` | Re-read, reapply intent to the latest state, re-preview if material |
| Caller error | `400`, missing required field | Fix once using returned allowed values or repair hints; do not loop |
| Authorization | `401`, `403` | Stop and report; never retry or escalate access |
| Unknown outcome | Timeout, connection reset, `5xx` without a definitive result, tool error without a status | Reconcile before any repeat |

A `429` is a rejection, not a partial execution, so a create that received `429` may be retried after backoff. When an MCP tool hides the HTTP status and the message does not prove whether the write happened, treat it as an unknown outcome.

## Idempotency by Operation

| Operation | Safe to repeat? | Guard |
| --- | --- | --- |
| Reads and searches | Yes | Bounded retries |
| Confluence update with snapshot or version | Conditionally | The token rejects a stale replay; re-read on conflict |
| Jira field edit | State-dependent | Re-read; skip if the target state already holds |
| Jira transition | State-dependent | Re-read status; treat "already in target status" as done |
| Jira issue create | No | Reconcile before any repeat |
| Confluence page create | No | Reconcile by parent, title, author, and time window |
| Comments, links, attachments | No | Check for an existing matching item before repeating |

Jira issue creation has no idempotency key, and Jira does not deduplicate creates. A repeated create after a lost response can produce a duplicate.

## Atlassian Rate-Limit Signals

Apply the service resilience skill's coordinated backoff and client-side pacing, using these Atlassian signals:

- Treat `Retry-After` as a minimum. It can be delta-seconds or an HTTP date. Fall back to `X-RateLimit-Reset` when it is absent.
- Retry a `503` only when it carries `Retry-After`.
- Jira burst limits always return `Retry-After: 1`. Treat that as the shortest wait and keep backing off exponentially with jitter on repeated `429` responses.
- Slow down when `X-RateLimit-NearLimit` is `true`. Treat `Beta-` prefixed headers as early warnings, not enforced limits.
- Jira enforces per-issue write limits, currently 20 writes per 2 seconds and 100 per 30 seconds. Batch field changes to one issue into one edit.

Back off only the scope that was limited. Every scope except a global quota applies to one tenant.

| `RateLimit-Reason` | Scope | Response |
| --- | --- | --- |
| `jira-burst-based` | One tenant, endpoint, and method | Slow that endpoint for that tenant; continue others |
| `jira-per-issue-on-write` | One issue | Space out writes to that issue |
| `jira-quota-tenant-based` | All Jira traffic to one tenant | Pause Jira requests to that tenant |
| `jira-quota-global-based` | All Jira traffic from the app | Pause all Jira requests |
| `conf-tenant-based` | All Confluence traffic to one tenant | Pause Confluence requests to that tenant |
| `conf-global-based` | All Confluence traffic from the app | Pause all Confluence requests |
| Missing or unrecognized | Unknown | If the value contains `global`, pause the product for all tenants; if it contains `quota` or `tenant`, pause the product for that tenant; otherwise slow that endpoint for that tenant |

Atlassian documentation shows more than one spelling for Confluence reasons, and Confluence burst limits have no documented reason value. Match by substring rather than exact value, and log the raw header. Test this handling against mocked responses, never by generating load against a live tenant.

## Unknown-Outcome Reconciliation

Never repeat a create or other non-idempotent write after an unknown outcome until reconciliation has looked for it.

1. Stop issuing writes for that step and mark it unknown in the ledger.
2. Query authoritative state:
   - Jira issue: project, issue type, reporter, creation window, and summary. JQL text search is fuzzy, so use a phrase search to find candidates and then compare the summary exactly. Use a correlation marker only if the project already supports one, such as an approved label, field, or issue property.
   - Confluence page: list the parent's children through the pages API rather than relying on search, then compare exact title, author, and creation time. Do not assume titles are unique.
   - Confluence update: current version and its version message, when the operation ID was included there.
   - Comment or link: existing comments or links on the target.
3. Allow for eventual consistency. Jira JQL search does not guarantee read-after-write consistency, and Atlassian documents delays from seconds to minutes. `reconcileIssues` only helps when you already hold candidate issue IDs. Repeat the search with backoff over a window of several minutes.
4. Resolve:
   - exactly one match: adopt it, record its ID, and continue;
   - no match: the write is probably absent, not proven absent. An agent asks the user before recreating. Unattended automation may retry once, must reconcile again immediately afterward, and reports any duplicate without deleting it; and
   - multiple or ambiguous matches: stop and ask the user. Never delete a candidate automatically.

Do not add visible correlation markers to issues or pages without user or project approval.

## Partial Success in MCP Responses

Some Atlassian MCP tools report partial success. Treat the main write as applied:

- `createJiraIssue` with failed sprint assignment still returns the new issue key. Do not create the issue again; retry only the sprint assignment.
- `editJiraIssue` with a failed reorder still applies the field edit and returns `ranking.ranked: false`. Retry only the ranking.

## Linked Jira and Confluence Changes

Jira and Confluence share no transaction. Create the referenced object before anything links to it, record each step in the ledger, and on failure resume from the first incomplete step rather than restarting. Deleting or reverting completed steps is a separate, explicitly authorized mutation. Report partial completion with links to every created object.

## Bulk Changes

Produce a dry-run report of every target and intended change, obtain explicit confirmation of the exact scope, process with bounded concurrency and shared backoff, stop when failures exceed a stated threshold, and make the run resumable from the ledger.
