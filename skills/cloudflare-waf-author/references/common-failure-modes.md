# Common Failure Modes

Failure-mode patterns observed across many Cloudflare WAF authoring teams - not specific to any one team. Use this as a checklist when reviewing a WAF PR / change ticket / API call: scan for the symptom, apply the lesson.

These are organized by *what shipped* and *what went wrong*. Each row also notes which interface(s) the failure typically manifests in.

---

## Path predicate failures

| Symptom | Interfaces | Root cause | Fix |
|---|---|---|---|
| Rule applies to unintended sibling paths (`/api/x-export`, `/api/x-v2`) | All | `starts_with(http.request.uri.path, "/api/x")` without trailing slash | Use `eq` for single endpoint, or `starts_with` with trailing slash for child paths, or alternation `(eq "/api/x" or starts_with("/api/x/"))` if both bare and children are legitimate |
| Rule applies to bare endpoint but not child paths (or vice versa) | All | Wrong choice from the path predicate matrix | Re-read `405-cloudflare-waf-rules.mdc` § "Path predicate decision matrix"; pick the shape the requester actually needs; document the choice |
| Rule applies to `/api/x` AND `/api/x/anything` when requester only wanted the bare endpoint | All | Used `starts_with(... "/api/x/")` thinking the trailing slash narrows it; actually broadens it | Use `eq "/api/x"` for the bare endpoint only |

---

## Multi-value header failures

| Symptom | Interfaces | Root cause | Fix |
|---|---|---|---|
| Expression validates but rule never fires on traffic the requester is certain has the header | All | Used bare `http.request.headers["X"] eq "..."` against a multi-value field | Use `any(http.request.headers["X"][*] eq "...")` |
| Content-type rule misses requests with `Multipart/Form-Data` or `multipart/form-data; boundary=...` | All | Used single-value `eq "multipart/form-data"` against the raw value | Use `any(lower(http.request.headers["content-type"][*])[*] contains "multipart/form-data")` |
| Origin guard misses browser requests that the requester confirmed have the header | All | Used `http.request.headers["origin"] eq "..."` (wrong syntax for a multi-value field) | Use `any(http.request.headers["origin"][*] eq "https://...")` |

---

## Multipart-upload skip failures

| Symptom | Interfaces | Root cause | Fix |
|---|---|---|---|
| Skip rule fires on POSTs that have `multipart/form-data` content-type but aren't actually file uploads | All | Missing `filename=` body marker | Add `and http.request.body.raw contains "filename="` |
| Skip rule fires on server-to-server POSTs that fake the multipart content-type | All | No origin / source guard | For browser-only flows, add `any(http.request.headers["origin"][*] eq "https://<browser-host>")`. For mixed flows, scope source IPs to a trusted IP List. |
| Skip rule bypasses WAY too many OWASP signatures | All | Used `action_parameters: { ruleset: "current" }` to skip the whole ruleset | Source the specific child rule IDs from Security Events on the actual zone; skip only those |

---

## Custom rule (block / challenge / allow) failures

| Symptom | Interfaces | Root cause | Fix |
|---|---|---|---|
| Block rule fires on legitimate traffic; immediate outage | All | No `log`-mode soak before promotion to `block` | New block-class rules MUST run in `log` for at least 24h. Validate via Security Events that ONLY illegitimate traffic matches. Promote only after a clean window. |
| Geo block also blocks internal users when they travel | All | Geo predicate without trusted-IPs escape hatch | Always include `or ip.src in $trusted_egress_ips` (or your zone's equivalent named IP List). The only exception is OFAC compliance blocks. |
| Allow rule appears to do nothing; the block still fires | All | Allow rule positioned BELOW the block rule it complements | Cloudflare evaluates top-down; the allow MUST be above the block. In Terraform, list it earlier; in Dashboard, drag above; in API, use `position.before` with the block rule's ID. |
| `js_challenge` breaks API or CLI clients | All | Used `js_challenge` on `/api/*` paths | Use `managed_challenge` for ambiguous traffic, or scope the rule to non-API paths |
| Country list typo silently blocks unintended traffic | All | Country codes typed from memory; case-sensitive ISO-3166 alpha-2 | Always paste from the [Cloudflare country code reference](https://developers.cloudflare.com/network/country-codes/) |
| Hardcoded IP list goes stale; legitimate traffic blocked six months later | All | Hardcoded IPs instead of a named IP List reference | Use the named list (`$<list-name>`); the list is centrally maintained and rotates |

---

## Provenance / source-of-truth failures

| Symptom | Interfaces | Root cause | Fix |
|---|---|---|---|
| Code shipped doing the opposite of what the PR title said | All | Title-vs-code drift; PR title said "broaden" but expression used `eq` | All four sources of truth (title, body, provenance artifact, saved expression) must agree. Update them together or don't update at all. |
| Future on-call can't tell whether a rule should still exist | All | Missing provenance artifact (Terraform inline comment / Dashboard runbook / API sibling .md) | No rule ships without a provenance artifact. Period. |
| Description prefixed with ticket ID, making the rule unsearchable by purpose in the Dashboard | Terraform | Description treated as ticket-tracking; should be purpose-based when an inline comment carries the ticket | Use `<your-app>-<purpose>` as the description; put the ticket in the `//` comment. (Existing ticket-prefixed names kept as-is for log-history continuity.) |
| Dashboard / API edits not reflected in the Terraform source | Dashboard, API | Drift between authoring paths | Per `405-cloudflare-waf-rules.mdc` § "Source-of-truth discipline", pick ONE authoring path per zone and document it. Emergency edits via other paths must be ported back within 24h. |
| Two teammates' edits silently clobber each other via the API | API | No ETag / `If-Match` discipline | Always `GET` first, capture the ETag, `PUT` with `If-Match`. Handle 412 by re-fetching and re-applying intent (never blind-retry). |

---

## Terraform-specific failures

| Symptom | Root cause | Fix |
|---|---|---|
| `check-executables-have-shebangs` pre-commit fails on the `.tf` file | File mode flipped to `100755` (executable) | Restore to `100644` |
| `terraform plan` shows changes you didn't make | Someone has been editing via Dashboard or API, creating drift | Investigate before applying; either port the drift back into Terraform, or revert the out-of-band change |
| Heredoc body has inconsistent indentation creating noisy diffs | `<<-EOT` strips the shortest leading-whitespace prefix; semantic no-op but visually messy | Match the surrounding rule's indent |
| Outer parens wrapping a top-level `and` chain `(a and b and c)` | Stylistic over-grouping | Remove the outer parens; the parser handles top-level `and` without them |

---

## Dashboard-specific failures

| Symptom | Root cause | Fix |
|---|---|---|
| No rollback path when a new rule mis-fires in production | Edited the existing rule in place instead of cloning | Always clone first, edit the clone in log mode, validate, promote, disable original |
| Three semantically distinct changes recorded as one Audit Log entry | Bulk-edited / reordered in a single save | One logical change per save. Easier to debug; easier to revert. |
| Runbook drift: rules in production that nobody can explain | Saved without writing the runbook entry | Runbook entry is required, not optional. If your team can't commit to maintaining it, switch to Terraform or API authoring. |
| No `terraform plan` equivalent for "what will this change do?" | Direct production-zone authoring | Maintain a staging zone; save in log mode there first, observe 24h, then author in production |

---

## API-specific failures

| Symptom | Root cause | Fix |
|---|---|---|
| 412 Precondition Failed on `PUT` | Concurrent writer modified the ruleset between your `GET` and `PUT` | Re-fetch (`GET`), re-apply your intent against the new state, `PUT` again with the new ETag. Never blind-retry. |
| Rule landed at the wrong position; broke evaluation order | Used `position.index` instead of `position.before` / `position.after` with stable rule IDs | Always position by stable rule ID. Index-based positioning breaks the moment anyone else inserts a rule. |
| Syntax error discovered at `PUT` time after the destructive call | Skipped the expression test endpoint | Always validate via `POST /zones/<zone-id>/rulesets/test` before the `PUT` |
| Provenance lost; only the JSON survives | No sibling `.md` provenance file | Commit `rules/<name>.json` + `rules/<name>.md` together; PR review enforces it |

---

## Cross-cutting lesson

If you find yourself reaching for any of the following, **stop and rethink**:

- "Just skip the whole OWASP ruleset for this host" → almost always 2-3 child rules are the real problem. Source from Security Events.
- "Block all traffic from country X" → missing escape hatch. Internal users travel; partners are mobile.
- "PATCH this one rule field" → race conditions. `GET` + `PUT` + `If-Match` is safer.
- "I'll add the runbook entry later" → it never happens. Add it before saving.
- "It's just a quick Dashboard edit" → see the source-of-truth section. Drift compounds.
