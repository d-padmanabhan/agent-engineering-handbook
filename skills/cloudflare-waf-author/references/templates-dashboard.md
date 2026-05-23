# Templates: Cloudflare Dashboard (UI authoring)

Step-by-step UI workflow for both rule types. Pair with `405-cloudflare-waf-rules.mdc` § "Provenance + rationale (mandatory)" - the Dashboard sub-section.

**Why Dashboard authoring needs extra care:**

The Dashboard's Audit Logs capture *who*, *what*, and *when* but never *why*. Without a runbook entry, your rule is un-auditable. Without a staging-zone dry-run, you have no `terraform plan` equivalent. Without the clone-before-edit discipline, you have no rollback path.

**Conventions:**

- "Trusted IP list" means a [Cloudflare IP List](https://developers.cloudflare.com/waf/tools/lists/) configured in your account (e.g., `trusted_egress_ips`). Reference it as `$<list-name>` in expressions.
- `<your-app>`, `<host>`, `<endpoint>`, `<ticket-id>` are placeholders - replace before saving.
- Country codes pasted from the [Cloudflare country code reference](https://developers.cloudflare.com/network/country-codes/).

---

## Pre-flight: clone before edit (REQUIRED for any modification)

If you're modifying an existing rule, **clone it first**:

1. In the rules list, click the kebab menu on the existing rule → **Duplicate**.
2. Rename the clone with a `-staging` suffix (e.g., `<your-app>-allow-trusted-staging`).
3. Set the clone's action to `Log`.
4. Edit the clone's expression.
5. Save. Observe in Security Events for 24h.
6. Once validated, set the clone's action to the intended action (`Block`, `Skip`, etc.).
7. Disable the original.
8. After a further 24h with no regressions, delete the original and rename the clone (drop the `-staging` suffix).

If you're creating a brand-new rule, skip this section but follow the soak discipline (start in `Log`, observe, promote).

---

## Custom Rule (Security → WAF → Custom rules)

### 1. Navigate

Security → WAF → **Custom rules** → **Create rule**

### 2. Rule details

| Field | Value |
|---|---|
| **Rule name** | `<your-app>-<purpose>` (e.g., `<your-app>-allow-trusted-egress`) - or with ticket suffix if your zone's convention is option (a): `<your-app>-<purpose> \| <ticket-id>` |
| **If incoming requests match** | Custom filter expression (see below) |
| **Then take action** | Start with `Log` for the soak period. Promote to `Block` / `Managed Challenge` / `Skip` (allow) only after 24h of clean Security Events. |
| **With the following expression** | See the expression editor section below |

### 3. Expression editor

For an allow-trusted-egress + block-everyone-else pair, you'll create **two rules** (allow first, block second):

**Rule 1 (allow):**

```
Field:    Hostname (http.host)
Operator: equals
Value:    <host>

AND

Field:    Custom expression
Operator: (the editor switches to free-text)
Value:    (ip.geoip.country in {"US" "CA" "GB"} or ip.src in $trusted_egress_ips)
```

Action: **Skip** → in the skip configuration, select **All remaining custom rules** (this acts as an allow).

**Rule 2 (block):**

```
Field:    Hostname (http.host)
Operator: equals
Value:    <host>
```

Action: **Block** (after the soak period; start as `Log`).

### 4. Verify allow-before-block ordering

In the rules list, the allow rule MUST appear above the block rule (drag to reorder if needed). Cloudflare evaluates top-down; first match wins.

### 5. Save and verify the Audit Log entry

After save, navigate to **Manage Account → Audit Log** and confirm:

- One log entry per logical change (not multiple stacked changes in one save)
- The entry's actor, target zone, and rule description all match what you intended

### 6. Provenance: runbook entry (REQUIRED)

In your team's runbook (Confluence / ServiceNow / `waf-rules-log.md` in your governance repo), add:

```markdown
## <YYYY-MM-DD> - <your-app>-<purpose>

- **Ticket:** <ticket-id>
- **Zone:** <zone-name>
- **Phase:** http_request_firewall_custom
- **Rule name (description in Dashboard):** <your-app>-<purpose>
- **Peer rule:** <peer-rule-name-or-id> (the closest existing rule you mirrored)
- **Host / path / method:** <host> / <path-pattern> / <method>
- **Action:** <Log | Block | Skip | Managed Challenge>
- **Why each guard:**
  - <guard>: <one-sentence justification>
- **Soak plan:** Log mode for <N> hours; validated via Security Events filter (action=<original-action>, host=<host>).
- **Approval:** <requester>, <YYYY-MM-DD>
- **Review by:** <YYYY-MM-DD>
- **Audit Log entry ID:** <copy from Audit Log>
```

---

## Managed-Rule Exception (Security → WAF → Managed rules → Exceptions)

### 1. Source the OWASP child-rule IDs from Security Events FIRST

Before opening the exceptions UI, navigate to **Security → Events** and filter:

- Action: `block`
- Service: WAF
- Host: `<host>`
- URI Path: `<path>` (or `contains <path-prefix>`)
- Time: last 7 days

Note every **rule ID** that fired on legitimate traffic. These are the only IDs you should skip. If only 3 IDs fire, do not skip the whole ruleset.

### 2. Navigate

Security → WAF → **Managed rules** → **Exceptions** tab → **Add exception**

### 3. Exception configuration

| Field | Value |
|---|---|
| **Exception name** | `<your-app>-<endpoint>-skip` (or with ticket suffix per your zone's convention) |
| **When incoming requests match** | Expression editor - see below |
| **Skip rules** | Select **Specific rules** → check the IDs you noted in step 1. Never select **All rules in this ruleset** unless every single rule is firing on legitimate traffic, which is essentially never. |

### 4. Expression for the most common case (multipart file upload)

```
Field:    Hostname (http.host)
Operator: equals
Value:    <host>

AND

Field:    Request Method (http.request.method)
Operator: equals
Value:    POST

AND

Field:    URI Path (http.request.uri.path)
Operator: equals (or "starts with" if many child paths are legitimate; if "starts with", ALWAYS include the trailing slash)
Value:    <path>

AND

Field:    Custom expression
Operator: (free-text)
Value:    any(lower(http.request.headers["content-type"][*])[*] contains "multipart/form-data")

AND

Field:    Custom expression
Value:    http.request.body.raw contains "filename="

AND

Field:    Custom expression  (browser-flow only)
Value:    any(http.request.headers["origin"][*] eq "https://<browser-host>")

AND

Field:    Custom expression
Value:    ip.src in $trusted_egress_ips
```

### 5. Verify positioning

The exception must appear BEFORE the managed-rule execution it bypasses. In the Dashboard, exceptions are displayed in evaluation order under the Exceptions tab; verify yours appears above the OWASP execute rule's row.

### 6. Save, observe, and record

- Save the exception.
- Watch Security Events for 24h. Filter on the original blocked rule IDs - they should now show `action=skip` for the matching traffic and continue to show `action=block` for any other traffic (proving the exception is correctly scoped).
- Add the runbook entry (same shape as the custom-rule example above, with the additional fields: **OWASP child-rule IDs skipped** and **Security Events evidence** linking to the filter view).

---

## Anti-patterns specific to Dashboard authoring

From `405-cloudflare-waf-rules.mdc` § "Anti-patterns" - Dashboard-specific:

- Editing a live rule without first cloning it to a staging rule (no rollback path).
- Saving without recording the change in your team's runbook.
- Using bulk-edit / drag-to-reorder without a separate change ticket per logical change.
- Authoring directly in production zone without a staging-zone dry-run.
- Saving changes while another teammate is also editing the same zone (last-save-wins; coordinate via your team's change-management channel).
