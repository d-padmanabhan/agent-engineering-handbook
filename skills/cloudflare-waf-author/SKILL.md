---
name: cloudflare-waf-author
description: Workflow for crafting Cloudflare WAF rules across all three authoring interfaces - Terraform (cloudflare_ruleset), the Cloudflare Dashboard, and the Rulesets API. Covers both Custom Rules (actions like block, managed_challenge, log, skip-as-allow) and Managed-Rule Exceptions (action skip). Forces a docs-first read, peer-rule survey, explicit rule-type branch, and guards-by-type checklist before any expression is drafted. Use when adding or editing any Cloudflare WAF rule, when the user asks for a WAF block / challenge / allow / skip / OWASP child-rule bypass, or when reviewing such a change.
---

# Cloudflare WAF Author

**Companion rule:** `405-cloudflare-waf-rules.mdc` (file-scoped to Cloudflare ruleset Terraform / JSON; topic-discoverable for Dashboard authoring). The rule is the **gate**; this skill is the **workflow** through the gate.

**Voice:** opinionated. Every WAF rule is a policy commitment that ships to production at the edge. Custom rules can DoS your own users; managed-rule skips can silently bypass OWASP signatures. The job is to make the predicate exactly the right shape and exactly traceable to a request.

---

## When to invoke this skill

Invoke when:

- The user asks to add or edit a Cloudflare WAF rule of **any** kind - custom block, allow, challenge, log, or a managed-rule skip / exception / OWASP child-rule bypass.
- A diff touches a Cloudflare ruleset Terraform file (matches the file globs in `405-cloudflare-waf-rules.mdc`) or a JSON payload destined for the Rulesets API.
- The user is authoring a rule via the Cloudflare Dashboard (UI clicks under Security → WAF) and mentions it in the conversation.
- A user mentions a change ticket asking to "block country X", "allow IP range Y", "stop the WAF from blocking endpoint Z", or any equivalent.
- A code or change review finds a candidate rule that violates `405-cloudflare-waf-rules.mdc`.

Do NOT invoke for:

- Cloudflare Single Redirect / Origin Rule / Transform Rule edits - different ruleset phases.
- Account-level WAF policy or Bulk Redirects - this skill is zone-level WAF only.
- Bot Management or DDoS configuration - separate Cloudflare products.

---

## Pre-step: confirm the authoring interface

Before Step 0, confirm **which of the three interfaces** the user is authoring through. This determines provenance carriers, position semantics, and the templates you'll use in Step 4.

| Signal | Interface |
|---|---|
| The user opened a `.tf` file, mentioned `terraform apply`, or pushed a branch to an IaC repo | **Terraform** |
| The user said "I'm in the Cloudflare dashboard", "WAF section", "Security → WAF" | **Dashboard** |
| The user mentioned `curl`, `client/v4/zones/<id>/rulesets`, a JSON payload, or a script | **API** |

If unclear, ask. Per `405-cloudflare-waf-rules.mdc` § "Source-of-truth discipline (NON-NEGOTIABLE)", a zone should have **one** documented authoring path; if the user is authoring via a path other than the documented one, push back before proceeding.

---

## The six-step workflow

### Step 0 - Identify the rule type (the branching decision)

Before anything else, classify the request. Everything downstream depends on this.

| Symptom | Rule type | Ruleset phase | Typical actions |
|---|---|---|---|
| "Block traffic from country X" / "Allow only trusted IPs to /admin" / "Challenge known-bad ASN" | **Custom Rule** | `http_request_firewall_custom` | `block`, `managed_challenge`, `js_challenge`, `log`, `skip` (as allow) |
| "WAF is blocking my legitimate POST" / "Skip OWASP rule X for endpoint Y" / "False positive on file upload" | **Managed-Rule Exception (skip)** | `http_request_firewall_managed` | `skip` only |

> [!IMPORTANT]
> If the requester is asking for both ("allow these IPs AND skip the OWASP rules for them"), that's TWO separate rules in TWO separate phases. Don't conflate them. In Terraform, they live in separate files (or separate `cloudflare_ruleset` resources); in the Dashboard, they're under different navigation paths; in the API, they're separate ruleset IDs.

If the rule type is unclear from the request, **stop and ask the requester**. Don't guess - the wrong phase is a wrong-behavior rule that may not fire at all.

---

### Step 1 - Docs-first read (cannot skip)

Open the docs for the chosen rule type and skim before writing any expression. Do not rely on training-data memory; the API and field names evolve. If a `user-cloudflare-docs` MCP server is configured in the workspace, prefer it for fresh fetches.

#### Always read (both rule types, all interfaces)

| Doc | Why |
|---|---|
| [Ruleset Engine fields reference](https://developers.cloudflare.com/ruleset-engine/rules-language/fields/) | Verify exact field names. Multi-value fields (headers) need `any(... [*] ...)`. |
| [Ruleset Engine operators / functions](https://developers.cloudflare.com/ruleset-engine/rules-language/operators/) | `eq`, `in`, `contains`, `starts_with`, `lower(...)`, `any(...)`. Operator gotchas live here. |
| [Cloudflare country codes reference](https://developers.cloudflare.com/network/country-codes/) | Always paste country codes from this page; never type from memory. |

#### Custom rules - additional reading

| Doc | Why |
|---|---|
| [WAF Custom Rules](https://developers.cloudflare.com/waf/custom-rules/) | Action options and their UX implications (`block` vs `challenge` vs `managed_challenge` vs `js_challenge`). |
| [`cf.*` request fields](https://developers.cloudflare.com/ruleset-engine/rules-language/fields/reference/) | `cf.client.bot`, `cf.threat_score`, `cf.waf.score` (Enterprise) - the high-leverage signals. |
| `400-cloudflare.mdc` § "WAF Attack Score (Plan-Aware)" | When and how to use the score fields without self-DoS. |

#### Managed-rule exceptions - additional reading

| Doc | Why |
|---|---|
| [Add an exception via API](https://developers.cloudflare.com/waf/managed-rules/waf-exceptions/define-api/) | Confirms the four exception types, the `action_parameters` shape, and the must-be-positioned-before-execute-rule rule. |
| [Create an exception (Ruleset Engine)](https://developers.cloudflare.com/ruleset-engine/managed-rulesets/create-exception/) | When to use `ruleset: current` vs `rulesets: [...]` vs `rules: { id: [...] }` (you almost always want the third). |
| [WAF changelog](https://developers.cloudflare.com/waf/change-log/) | Has the OWASP child-rule list you're targeting moved or been deprecated? |
| [OWASP Managed Ruleset reference](https://developers.cloudflare.com/waf/managed-rules/reference/owasp-core-ruleset/) | What the rule IDs you're skipping actually do. |

#### Interface-specific additional reading

| Interface | Additional doc |
|---|---|
| Terraform | [WAF Managed Rules with Terraform](https://developers.cloudflare.com/terraform/additional-configurations/waf-managed-rulesets/) and [`terraform-provider-cloudflare` changelog](https://github.com/cloudflare/terraform-provider-cloudflare/blob/master/CHANGELOG.md). |
| Dashboard | [Custom Rules in the Dashboard](https://developers.cloudflare.com/waf/custom-rules/create-dashboard/) and the Audit Logs documentation. |
| API | [Rulesets API reference](https://developers.cloudflare.com/api/operations/listAccountRulesets) plus the [expression test endpoint](https://developers.cloudflare.com/ruleset-engine/rulesets-api/test/). |

> [!IMPORTANT]
> Quote the relevant URL or sentence in your provenance artifact (Terraform comment, Dashboard runbook entry, or API sibling `.md`). "I read the docs" without a citation is not a citation.

---

### Step 2 - Peer-rule survey (cannot skip)

Identify the **closest existing rule** to your case in the same zone and mirror its shape. The carrier for the survey depends on the interface:

| Interface | How to survey |
|---|---|
| Terraform | Open the target `.tf` file (matching Step 0's phase). Read every rule. Pick the closest one. |
| Dashboard | Navigate to Security → WAF → Custom rules (or Managed rules → Exceptions). Read every existing rule's expression and description. |
| API | `GET /client/v4/zones/<zone_id>/rulesets/<ruleset_id>` to fetch the current ruleset JSON. Grep the `rules` array for similar patterns. |

If no peer matches, **stop and explain why** before drafting. The handbook's canonical shapes for both rule types live in `405-cloudflare-waf-rules.mdc` § "Pre-edit gate" - read those first.

> [!TIP]
> If the closest peer is a year old and the requester's flow doesn't match it cleanly, that's a signal the request may need a different approach (a new managed-rule sensitivity tune, a different action, or a code-side fix). Push back and discuss before drafting.

---

### Step 3 - Requester confirmation (cannot skip)

Ask for everything below before drafting. If any answer is missing, **stop**.

#### Always (both rule types, all interfaces)

- Change ticket / approval number, named owner, business justification
- Exact host(s), path(s), method(s) - confirmed against actual traffic, not assumed
- Source IP shape: trusted (named list) only / trusted + geo escape hatch / fully open / specific named source set
- Soak plan: how long in `log` mode before promoting to enforce, and how the soak will be validated (Security Events filter, dashboard, etc.)

#### Custom rules - additional

- Intended **action**: `block`, `managed_challenge`, `log` (soak), `skip` (allow)
- Is this complementing an existing block / allow rule? If so, which one - it must be positioned correctly relative to that rule.

#### Managed-rule exceptions - additional

- Browser-app or server-to-server flow? (Origin header pinning only works for browser flows.)
- Which OWASP child-rule IDs are actually firing on the legitimate flow? (Cloudflare Security Events filter: `action=block`, `host=...`, `path=...`, last 7 days. **Skip only those**, not the whole ruleset.)

> [!TIP]
> If a custom-rule requester says "block all foreign traffic" - push back. Without a trusted-IPs escape hatch, traveling internal users and partners are blocked. Always include the escape hatch.
>
> If a managed-rule-skip requester says "skip the whole OWASP managed ruleset for my host" - push back. Almost always 2-3 child rules are firing; skip those, not the whole ruleset.

---

### Step 4 - Draft the expression

Pick the template for your **interface** (from the pre-step) AND your **rule type** (from Step 0). Templates live in the `references/` directory to keep this SKILL.md focused on the workflow.

| Rule type | Terraform | Dashboard | API |
|---|---|---|---|
| Custom Rule | [references/templates-terraform.md](references/templates-terraform.md) § Custom Rule | [references/templates-dashboard.md](references/templates-dashboard.md) § Custom Rule | [references/templates-api.md](references/templates-api.md) § Custom Rule |
| Managed-Rule Exception | [references/templates-terraform.md](references/templates-terraform.md) § Managed-Rule Exception | [references/templates-dashboard.md](references/templates-dashboard.md) § Managed-Rule Exception | [references/templates-api.md](references/templates-api.md) § Managed-Rule Exception |

Common patterns across all six combinations (interface × rule type):

- **Path predicate** uses one of the four sanctioned shapes from `405-cloudflare-waf-rules.mdc` § "Path predicate decision matrix" - `eq` (default), `starts_with(..., "...")` with trailing slash, alternation, or - never - bare `starts_with` without trailing slash.
- **Multi-value headers** use `any(http.request.headers["X"][*] ...)`, never bare `eq`.
- **Content-type guards** use `any(lower(http.request.headers["content-type"][*])[*] contains "multipart/form-data")`.
- **Multipart skips** include the `filename=` body marker.
- **Trusted-IP guards** reference a named Cloudflare IP List (the convention in this skill is `$trusted_egress_ips`; your zone's actual list name will differ - use it).
- **Allow-before-block ordering** is non-negotiable in custom rules: the allow-skip rule must be positioned ABOVE the block rule it complements.

---

### Step 5 - Write the provenance artifact + verify four-source consistency

The provenance artifact is **mandatory** and its shape is interface-specific. From `405-cloudflare-waf-rules.mdc` § "Provenance + rationale (mandatory)":

| Interface | Carrier |
|---|---|
| Terraform | Inline HCL `//` comment block immediately above the rule resource (see templates). |
| Dashboard | (1) Rule `description` (purpose-based, optionally ticket-suffixed) **plus** (2) an out-of-band runbook entry (Confluence / ServiceNow / repo doc). Both are required - Audit Logs cover who / what / when but never *why*. |
| API | Repo-resident sibling `.md` file alongside the JSON payload. The `description` field carries the purpose. |

The artifact MUST include: ticket, host, path, method, traffic shape, peer-rule cross-reference (rule name or ID), per-guard justification, OWASP child-rule list lineage (for skip rules), approver, date, review-by date.

Then verify all four sources of truth agree:

- **Title** of the PR / change ticket / API call summary describes the predicate intent ("narrow", "broaden", "scope to trusted IPs", "block country X").
- **Body** uses the same vocabulary.
- **Provenance artifact** describes the actual code shape (not the intended shape).
- **Saved rule expression** matches all three.

A drift between any two of these is the most common cause of "the change shipped but did the wrong thing" incidents.

---

## Self-check before submitting

Run through the per-interface reviewer checklist from `405-cloudflare-waf-rules.mdc` § "Reviewer checklist". The high-leverage subset (always run):

### Always (both rule types, all interfaces)

- [ ] Cited at least one Cloudflare doc URL in the provenance artifact
- [ ] Identified peer rule in the same zone (rule name or ID)
- [ ] `description` field is purpose-based (Terraform: ticket-free, ticket lives in `//` comment; Dashboard / API: ticket-suffixed if your zone's convention is option (a) from the naming table)
- [ ] Path predicate matches one of the four sanctioned shapes
- [ ] Multi-value headers use `any(... [*] ...)` form (not bare `eq`)
- [ ] No hardcoded IPs - a named IP List is referenced
- [ ] Title / body / provenance artifact / saved rule expression all agree
- [ ] Soak plan documented (log-mode duration and validation method)

### Custom rules only

- [ ] Action choice (`block` / `managed_challenge` / `log` / skip-as-allow) is documented in the provenance artifact
- [ ] Allow-as-skip rules positioned ABOVE corresponding block rules
- [ ] Geo blocks include trusted-IPs escape hatch (unless OFAC compliance block)
- [ ] No `js_challenge` on `/api/*` paths
- [ ] New block-class rules went through a `log`-mode soak before being promoted
- [ ] Country codes copy-pasted from Cloudflare reference, not typed

### Managed-rule exceptions only

- [ ] OWASP child-rule IDs sourced from actual Security Events firings (not guessed from symptom)
- [ ] Skip rule positioned BEFORE the `execute` rule it bypasses
- [ ] Multipart skips include the `filename=` body marker
- [ ] Origin guard (when present) uses `any(... [*] eq "...")` form

### Per-interface additions

- Terraform: `terraform fmt` clean, `terraform plan` reviewed by author + at least one peer, file mode `100644`, heredoc indent matches neighboring rules.
- Dashboard: clone existing rule before editing, save as a single logical change per Audit Log entry, staging-zone dry-run completed, runbook entry created.
- API: `GET` + ETag captured, `PUT` with `If-Match`, `position.before`/`after` (not `index`), JSON validated via expression test endpoint, response logged to the run-log.

See [references/common-failure-modes.md](references/common-failure-modes.md) for failure-mode patterns observed across many WAF authoring teams (not specific to any one team).

---

## Related

- `405-cloudflare-waf-rules.mdc` - the rule (file-scoped guardrail; covers both rule types and all three interfaces)
- `400-cloudflare.mdc` - broader Cloudflare ruleset patterns including OWASP Managed Ruleset configuration (PL1 + anomaly score threshold 60)
- `cloud-platforms` skill - cross-cloud platform patterns
- `codebase-security-audit` skill - WAF rule reviews are security reviews
