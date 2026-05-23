# Templates: Terraform (`cloudflare_ruleset`)

Drop-in HCL templates for both rule types. Pair with `405-cloudflare-waf-rules.mdc` § "Provenance + rationale (mandatory)" and the cumulative anti-patterns list.

**Conventions:**

- `$trusted_egress_ips` is a placeholder for your zone's named [IP List](https://developers.cloudflare.com/waf/tools/lists/). Replace with the actual list name configured in your account.
- `<your-app>`, `<host>`, `<endpoint>`, `<ticket-id>`, `<peer-rule-name>` are placeholders - replace before applying.
- All multi-value headers use the `any(... [*] ...)` form. Bare `eq` against a header is wrong.
- Country codes pasted from the [Cloudflare country code reference](https://developers.cloudflare.com/network/country-codes/), never typed.

---

## Custom Rule (phase `http_request_firewall_custom`)

The most common case is an allow + block pair. Draft both rules and confirm the **allow is positioned ABOVE the block** in the file (Cloudflare evaluates top-down; first match wins).

```hcl
// <ticket-id> - <Short purpose statement>. <Peer-rule cross-reference: e.g., "Same shape as <peer-rule-name>">.
//
// Why each guard:
//   - <country / geo predicate>: <one-sentence justification>
//   - <trusted-IPs escape hatch>: required so internal users (including travelers) are not blocked
//   - <path scope>: <eq vs starts_with-with-slash vs alternation>
//
// Soak plan: log mode for <N hours>, validated via Security Events filter (action=block, host=<host>), then promoted.
// Approval: <requester>, <YYYY-MM-DD>. Review by: <YYYY-MM-DD or "permanent + justification">.

# Allow trusted IPs + sanctioned regions (skip-as-allow). Positioned ABOVE the block rule.
{
  action      = "skip"   # skip-as-allow: bypasses the downstream block rule
  description = "<your-app>-allow-<region-or-purpose>"   # purpose-based; ticket lives in the // comment, not here
  enabled     = true
  expression  = <<-EOT
    http.host eq "<host>"
    and (ip.geoip.country in {"US" "CA" "GB"} or ip.src in $trusted_egress_ips)
  EOT
  logging = {
    enabled = true   # log every match - cheap, helps with debugging allow-rule scope
  }
  action_parameters = {
    ruleset = "current"   # skip the rest of THIS ruleset for matched traffic
  }
},

# Block everything else for this host. Positioned BELOW the allow.
{
  action      = "block"
  description = "<your-app>-block-non-allowlisted"
  enabled     = true
  expression  = <<-EOT
    http.host eq "<host>"
  EOT
  logging = {
    enabled = true   # required for block-class rules so blocked traffic is visible in Security Events
  }
},
```

> [!CAUTION]
> Before promoting `block` to enforced state, run it as `action = "log"` for at least 24h and confirm via Security Events that ONLY illegitimate traffic matches. The most common production incident is a block rule that matches legitimate traffic because the predicate was broader than the requester realized.

---

## Managed-Rule Exception (phase `http_request_firewall_managed`, action `skip`)

```hcl
// <ticket-id> - <Short purpose statement>. Same shape as <peer-rule-name>.
//
// Why each guard:
//   - <origin / trusted-IPs / etc>: <one-sentence justification>
//   - <path predicate choice>: <eq vs starts_with-with-slash vs alternation, with reason>
//   - <OWASP child-rule list lineage>: e.g., "shared baseline from <peer-rule-name>; added <id> for this incident because <reason>"
//
// Approval: <requester>, <YYYY-MM-DD>. Review by: <YYYY-MM-DD>.
{
  action      = "skip"
  description = "<your-app>-<endpoint>-skip"   # purpose-based; do NOT prefix with the ticket
  enabled     = true
  expression  = <<-EOT
    <host predicate>             # http.host eq "..." | http.host in {"..." "..."}
    and http.request.method eq "<METHOD>"
    and <path predicate>          # see decision matrix in 405-cloudflare-waf-rules.mdc
    and <content-type guard>      # any(lower(http.request.headers["content-type"][*])[*] contains "multipart/form-data")
    and <body marker>             # http.request.body.raw contains "filename="  (multipart only)
    and <origin guard>            # any(http.request.headers["origin"][*] eq "https://<browser-host>")  (browser flow only)
    and <source guard>            # ip.src in $trusted_egress_ips  (and/or ip.geoip.continent in {...})
  EOT
  # No logging block needed: skip rules are recorded automatically in WAF events when they fire.
  action_parameters = {
    rules = {
      (local.waf_ruleset_ids.cloudflare_owasp_core_ruleset_id) = [
        # Source the rule IDs from Security Events on YOUR zone, not from training data.
        # Filter: action=block, host=<host>, path=<path>, last 7 days. Note the rule IDs that fired.
        # Skip ONLY those IDs. Skipping the whole ruleset bypasses everything else too.
        "<owasp-rule-id-1>",
        "<owasp-rule-id-2>",
        # ... add only the IDs you confirmed are firing on legitimate traffic
      ]
    }
  }
},
```

> [!IMPORTANT]
> The OWASP child-rule IDs above are placeholders. The actual IDs change per Cloudflare ruleset version and per zone. Always source them from Security Events on the consuming zone. Hardcoding a baseline from another zone's history is how you ship overscoped skip rules.

---

## Notes on `logging.enabled`

- **`block` and `challenge` actions:** enable logging. Without it, blocked / challenged traffic is harder to see in Security Events.
- **`skip` action (custom rule used as allow):** enable logging. The allow is a policy decision worth recording for debugging.
- **`skip` action (managed-rule exception):** logging block can be omitted. Cloudflare records skip-rule matches in WAF events automatically; the `logging` block is for *additional* logging beyond the default. The original template carried `logging.enabled = true` everywhere as a defensive copy-paste - it's harmless but not required for skip exceptions.

---

## Pre-flight: Terraform validation

Before opening the PR:

```bash
terraform fmt -recursive
terraform validate
terraform plan -out=plan.tfplan
# Eyeball the plan diff - it should be exactly your new / modified rule(s) and nothing else.
```

If the plan shows changes you didn't make, **stop** - someone has been editing via the Dashboard / API and the source-of-truth is broken. Investigate before applying.
