# Deployment + Gradual Rollouts

The safe path for shipping a Worker to production: upload as a version, gradually shift traffic, monitor, promote or roll back.

---

## Deployment models

| Model | Command | Use when |
|---|---|---|
| **Standard deploy** | `wrangler deploy` | Low-risk change; uploads and immediately serves 100% from the new version |
| **Gradual deployment** | `wrangler versions upload` then `wrangler versions deploy` | Production HTTP Workers serving customer traffic; any change to a binding or routing logic |

**Required for production:** gradual deployment. Standard deploy is for dev / staging / internal tools where instant rollback isn't critical.

---

## Gradual deployment commands

### 1. Upload a new version (without serving traffic)

```bash
wrangler versions upload
# Output includes the new version ID (e.g., 4f84cb40-1234-5678-9abc-def012345678)
# and the version's compatibility_date, bindings, etc.
```

The uploaded version is not yet serving any traffic; the previous deployment continues to serve 100%.

### 2. Create a deployment that splits traffic

Interactive (recommended for first-time rollouts):

```bash
wrangler versions deploy
# Prompts:
# - Which version IDs to include?
# - What percentage for each?
# - Optional deployment message
```

Non-interactive (for CI):

```bash
# 90% old, 10% new
wrangler versions deploy <old-version-id>@90 <new-version-id>@10 \
  --message "Canary 10% new"

# Auto-distribute remaining: 60% new, 40% (auto) old
wrangler versions deploy --version-id <new> --percentage 60
```

### 3. Promote to 100% after soak

```bash
wrangler versions deploy <new-version-id>@100 --message "Promote to 100%"
```

### 4. Roll back

```bash
# Re-deploy the previous version at 100%
wrangler versions deploy <previous-version-id>@100 --message "Rollback"
```

---

## Smoke-testing a specific version in production

You can route specific requests to a specific version using the `Cloudflare-Workers-Version-Overrides` request header. The override works even when the version is at 0% in the deployment.

```bash
# Hit production but force the new version (even if at 0% rollout)
curl https://api.example.com/health \
  -H 'Cloudflare-Workers-Version-Overrides: my-app="<new-version-id>"'
```

The version must be in the current deployment (visible in `wrangler deployments list` or the dashboard). If it's not in the deployment, the override is ignored.

**Pattern: smoke test before promotion.** Create a deployment with the new version at 0% and the previous at 100%. Smoke-test via the override header. If clean, promote to 1% / 10% / 100% gradually.

---

## Standard CI/CD pipeline (GitHub Actions example)

`.github/workflows/deploy.yml`:

```yaml
name: Deploy Worker

on:
  push:
    branches: [main]

permissions:
  contents: read
  id-token: write   # required for OIDC

jobs:
  deploy:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v5

      - uses: actions/setup-node@v5
        with:
          node-version: "22"
          cache: "npm"

      - run: npm ci
      - run: npm run types
      - run: npm run typecheck
      - run: npm test

      - name: Upload version
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: versions upload --message "${{ github.sha }} - ${{ github.event.head_commit.message }}"

      # For production - gradual rollout starts at 10%
      - name: Canary 10%
        if: github.ref == 'refs/heads/main'
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: versions deploy --y --percentage 10
        # Manual approval gate in GitHub Environments protects the next step

      - name: Wait for soak
        if: github.ref == 'refs/heads/main'
        run: sleep 600   # 10 minutes - replace with your monitoring check

      - name: Promote to 100%
        if: github.ref == 'refs/heads/main'
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: versions deploy --y --percentage 100
```

**Notes:**

- The 10% canary + 10-minute sleep is a starting point. Real soak should query your error / latency metrics; promote only when a defined SLO holds.
- For multi-stage rollouts (e.g., 1% → 10% → 50% → 100%), use GitHub Environments with manual approval between stages.

---

## OIDC for GitHub Actions (no long-lived API token)

Cloudflare supports OIDC trust from GitHub Actions, which removes the need for a long-lived `CLOUDFLARE_API_TOKEN` secret. Setup:

1. In the Cloudflare Dashboard → **My Profile → API Tokens → Create Token**, choose **GitHub OIDC** as the auth method.
2. Define the token's scopes (e.g., `Workers Scripts:Edit`, `Account Settings:Read`).
3. Bind the trust to a specific GitHub repo and branch ref (`refs/heads/main` for production deploys).
4. In your workflow, use `id-token: write` permissions and `cloudflare/oidc-login` (or pass the OIDC token to `wrangler-action`).

This is the same security pattern as AWS IAM OIDC trust from GitHub - covered in `skills/aws-iam/` if you want the parallel.

---

## Secrets management in CI

```bash
# CI pattern: read from a protected file or use secret bulk. Do not echo secrets.
wrangler secret put DATABASE_URL --env production < /run/secrets/database_url
```

**Rotation pattern:**

1. Generate new secret value (e.g., new API token at the provider)
2. `wrangler secret put NAME` with the new value (overwrites)
3. Wait one isolate-lifetime (~30s) for caches to drain
4. Revoke the old secret at the provider

Never store secrets in `vars`, committed `.dev.vars`, CLI arguments, or CI logs. The pattern above avoids echoing the secret value.

---

## Environments

For multi-environment Workers (staging + production), use `wrangler.jsonc` environments:

```jsonc
{
  "name": "my-worker",
  "main": "src/worker.ts",
  "compatibility_date": "2026-04-01",

  "vars": { "ENVIRONMENT": "production" },
  "kv_namespaces": [{ "binding": "KV", "id": "<prod-kv-id>" }],

  "env": {
    "staging": {
      "name": "my-worker-staging",   // separate Worker name
      "vars": { "ENVIRONMENT": "staging" },
      "kv_namespaces": [{ "binding": "KV", "id": "<staging-kv-id>" }]
    }
  }
}
```

Deploy:

```bash
wrangler deploy                  # uses top-level config (production)
wrangler deploy --env staging    # uses env.staging overrides
```

Per-environment secrets:

```bash
wrangler secret put API_KEY --env staging
wrangler secret put API_KEY --env production
```

---

## Observability during rollout

When a gradual deployment is in flight, both versions are running. To distinguish them in logs:

- Workers Logs (if `observability.enabled = true` in `wrangler.jsonc`) tags each log entry with the version ID.
- `wrangler tail` accepts `--version-id <id>` to filter live logs to one version.
- Cloudflare's Worker Analytics breaks down errors / requests / CPU time by version.

If error rates spike on the new version, run the rollback command. If clean for the soak window, promote.

---

## Anti-patterns

- **Standard deploy to production HTTP Workers.** Always go through `versions upload` + `versions deploy` for traffic-serving Workers; instant 100% switches give you no rollback window.
- **No soak between rollout stages.** Promoting 10% → 100% in 30 seconds defeats the gradual-rollout point.
- **`Cloudflare-Workers-Version-Overrides` left enabled on customer traffic.** The header is for smoke testing from your own tooling; don't propagate it from upstream to Worker.
- **Long-lived `CLOUDFLARE_API_TOKEN` in GitHub Secrets when OIDC is available.** OIDC trust + short-lived tokens are the modern security baseline.
- **Secrets in `vars` block.** `vars` is for non-sensitive config; secrets via `wrangler secret put`.
- **Editing the Worker via Dashboard "Edit code" while a wrangler.jsonc-managed deploy is in flight.** Drift between source-of-truth and what's deployed; the next `wrangler deploy` will silently revert the Dashboard edit.
