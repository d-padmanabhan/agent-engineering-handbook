# Templates: Cloudflare Rulesets API

JSON payload templates and the safe `GET → modify → PUT` workflow for both rule types. Pair with `405-cloudflare-waf-rules.mdc` § "Anti-patterns" - API-specific.

**Why API authoring needs extra care:**

The API supports concurrent edits but does not enforce coordination. Without `If-Match` ETag handling, two writers silently clobber each other. Without test-endpoint validation, you discover syntax errors at `PUT` time - after the destructive operation has been attempted.

**Conventions:**

- `<zone-id>`, `<ruleset-id>`, `<api-token>`, `<host>`, `<your-app>`, `<endpoint>`, `<ticket-id>` are placeholders - replace before calling.
- The API token needs the `Zone WAF:Edit` permission scoped to the target zone.
- All examples use `curl`; equivalent calls in your preferred client (Python `requests`, Node `fetch`, a wrapper script) follow the same shape.

---

## The safe write workflow (always)

```bash
# 1. Fetch the current ruleset AND its ETag in one call
RESPONSE=$(curl -sSL -D headers.txt \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/<zone-id>/rulesets/<ruleset-id>")

ETAG=$(grep -i '^etag:' headers.txt | sed -e 's/etag: //i' -e 's/[[:space:]]*$//')
echo "Current ETag: $ETAG"

# 2. Save the current ruleset for diffing and rollback
echo "$RESPONSE" | jq '.result' > current-ruleset.json

# 3. Modify in your local editor (add your new rule to the .rules array)
cp current-ruleset.json proposed-ruleset.json
# ... edit proposed-ruleset.json ...

# 4. Validate the expression with the test endpoint BEFORE the destructive PUT
EXPR=$(jq -r '.rules[-1].expression' proposed-ruleset.json)
curl -sSL \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -X POST "https://api.cloudflare.com/client/v4/zones/<zone-id>/rulesets/test" \
  --data "{\"expression\": $(jq -Rs . <<<"$EXPR")}"
# Confirm "success": true in the response. If false, fix the expression and re-test.

# 5. PUT with If-Match to detect concurrent writes
curl -sSL \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -H "If-Match: $ETAG" \
  -X PUT "https://api.cloudflare.com/client/v4/zones/<zone-id>/rulesets/<ruleset-id>" \
  --data @proposed-ruleset.json \
  | tee response.json

# 6. Check for 412 Precondition Failed (concurrent write)
HTTP_CODE=$(jq -r '.errors[0].code // "ok"' response.json)
if [[ "$HTTP_CODE" == "412" ]]; then
  echo "Concurrent write detected. Re-fetch (step 1) and re-apply intent. NEVER blind-retry."
  exit 1
fi

# 7. Log the change to your run-log
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | <ticket-id> | PUT <ruleset-id> | new rule id: $(jq -r '.result.rules[-1].id' response.json)" >> waf-changes.log
```

---

## Custom Rule (phase `http_request_firewall_custom`)

Append two rules (allow + block) to the existing ruleset's `rules` array. **Position the allow above the block** using `position.before`.

### Allow-trusted-egress (position first)

```json
{
  "action": "skip",
  "description": "<your-app>-allow-trusted-egress",
  "enabled": true,
  "expression": "(http.host eq \"<host>\") and (ip.geoip.country in {\"US\" \"CA\" \"GB\"} or ip.src in $trusted_egress_ips)",
  "action_parameters": {
    "ruleset": "current"
  },
  "logging": {
    "enabled": true
  }
}
```

### Block-non-allowlisted (position after the allow)

```json
{
  "action": "block",
  "description": "<your-app>-block-non-allowlisted",
  "enabled": true,
  "expression": "http.host eq \"<host>\"",
  "logging": {
    "enabled": true
  }
}
```

### Positioning with `position.before` / `position.after`

If you're calling the per-rule create endpoint instead of `PUT`-ing the whole ruleset:

```bash
# Create the block rule first (no positioning needed - it goes at the end)
BLOCK_ID=$(curl -sSL \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -X POST "https://api.cloudflare.com/client/v4/zones/<zone-id>/rulesets/<ruleset-id>/rules" \
  --data @block-rule.json \
  | jq -r '.result.id')

# Create the allow rule with position.before pointing at the block rule's stable ID
jq --arg ref "$BLOCK_ID" '. + {position: {before: $ref}}' allow-rule.json > allow-with-position.json

curl -sSL \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -X POST "https://api.cloudflare.com/client/v4/zones/<zone-id>/rulesets/<ruleset-id>/rules" \
  --data @allow-with-position.json
```

> [!IMPORTANT]
> Never use `position.index` - it breaks the moment anyone else inserts a rule above. Always position by stable rule ID via `position.before` or `position.after`.

---

## Managed-Rule Exception (phase `http_request_firewall_managed`, action `skip`)

### Source the OWASP child-rule IDs from Security Events FIRST

Before drafting the JSON, query Security Events on your zone:

```bash
curl -sSL \
  -H "Authorization: Bearer <api-token>" \
  "https://api.cloudflare.com/client/v4/zones/<zone-id>/security/events?action=block&host=<host>&period=10080" \
  | jq -r '.result.events[] | select(.matched_rules != null) | .matched_rules[] | .rule_id' \
  | sort -u
```

Note every rule ID returned. Skip ONLY those, not the whole ruleset.

### Skip-rule JSON

```json
{
  "action": "skip",
  "description": "<your-app>-<endpoint>-skip",
  "enabled": true,
  "expression": "(http.host eq \"<host>\") and (http.request.method eq \"POST\") and (http.request.uri.path eq \"<path>\") and (any(lower(http.request.headers[\"content-type\"][*])[*] contains \"multipart/form-data\")) and (http.request.body.raw contains \"filename=\") and (any(http.request.headers[\"origin\"][*] eq \"https://<browser-host>\")) and (ip.src in $trusted_egress_ips)",
  "action_parameters": {
    "rules": {
      "<owasp-managed-ruleset-id>": [
        "<owasp-rule-id-1>",
        "<owasp-rule-id-2>"
      ]
    }
  },
  "position": {
    "before": "<execute-rule-id>"
  }
}
```

> [!IMPORTANT]
> The OWASP child-rule IDs and managed-ruleset ID are placeholders. The actual IDs are zone-specific and change per ruleset version. Source them from Security Events (above) and from `GET /client/v4/accounts/<account-id>/rulesets/{ruleset_id}` for the managed-ruleset ID.

### Sibling provenance file (REQUIRED)

For every JSON file committed to the repo, create a sibling `.md` with the same name:

```
rules/
├── <your-app>-<endpoint>-skip.json    # the API payload
└── <your-app>-<endpoint>-skip.md      # the provenance
```

The `.md` shape (mirrors the Terraform `//` comment block):

```markdown
# <your-app>-<endpoint>-skip

- **Ticket:** <ticket-id>
- **Zone:** <zone-name> (<zone-id>)
- **Ruleset:** <ruleset-name> (<ruleset-id>)
- **Phase:** http_request_firewall_managed
- **Peer rule:** <peer-rule-name-or-id>
- **Host / path / method:** <host> / <path> / POST
- **Action:** skip
- **OWASP child-rule IDs skipped:** <id-1>, <id-2>  (sourced from Security Events on <YYYY-MM-DD>)
- **Why each guard:**
  - `<guard>`: <one-sentence justification>
- **Soak plan:** Log mode for <N> hours via a parallel `action: "log"` rule with the same expression; promoted to `skip` after validation.
- **Approval:** <requester>, <YYYY-MM-DD>
- **Review by:** <YYYY-MM-DD>
- **API call:** `PUT /zones/<zone-id>/rulesets/<ruleset-id>` on <YYYY-MM-DDTHH:MM:SSZ>
- **Run-log entry:** see `waf-changes.log` line <N>
```

PR review of the JSON + `.md` together enforces the provenance discipline.

---

## Anti-patterns specific to API authoring

From `405-cloudflare-waf-rules.mdc` § "Anti-patterns" - API-specific:

- Partial `PATCH` without fetching current state first (race conditions with concurrent edits).
- Hard-coding `position.index` instead of `position.before` / `position.after` with stable rule IDs.
- Calling the API without recording the change in a versioned JSON repo or run-log.
- Validating the JSON payload only at `PUT` time (use the expression test endpoint first).
- Skipping ETag / `If-Match` on writes (lets concurrent writers silently clobber).
- Blind-retrying on 412 Precondition Failed (always re-fetch and re-apply intent).
