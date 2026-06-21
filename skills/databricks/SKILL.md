---
name: databricks
description: Databricks playbook. Workflows for workspace bootstrap, Unity Catalog migration, Lakeflow Spark Declarative Pipelines (formerly Delta Live Tables / DLT), Declarative Automation Bundles (formerly Databricks Asset Bundles), cluster policies/access modes, serverless SQL and jobs, Photon and cost tuning, governance audit, Mosaic AI/MLflow, and recovery via Delta time travel. Use when designing, operating, or auditing Databricks.
---

# Databricks - Playbook

**Companion rule:** [481-databricks.mdc](../../rules/481-databricks.mdc). This skill turns those patterns into end-to-end workflows.

> [!NOTE]
> Current Databricks names: **Lakeflow Spark Declarative Pipelines** is the current name for Delta Live Tables (DLT). **Declarative Automation Bundles** is the current name for Databricks Asset Bundles (DABs). Existing DLT/DAB code and docs still work, but new guidance should use the current names and mention the former names for searchability.

---

## When to invoke

Use when the user is:

- Bootstrapping a new Databricks workspace or account
- Migrating to Unity Catalog (from Hive metastore or no-governance state)
- Designing or reviewing a Lakeflow Spark Declarative Pipeline (formerly DLT)
- Deploying jobs, notebooks, and pipelines with Declarative Automation Bundles
- Setting cluster policies or rolling out Serverless / SQL Warehouses
- Tuning cost (cluster sizing, Photon, spot, job compute vs all-purpose)
- Governing data (Unity Catalog, tags, access control, lineage)
- Recovering from a bad change (Delta time travel / `RESTORE`)
- Hardening access (SCIM, SSO, service principals, OAuth tokens)

---

## Golden Rules

1. **Unity Catalog is the default.** Hive metastore is for legacy migration only.
2. **Service principals and OAuth**, not personal access tokens, for automation.
3. **Standard access mode by default.** Dedicated access mode only when the workload requires it; no-isolation shared is not acceptable for governed production.
4. **Job compute for jobs.** All-purpose clusters are for exploration.
5. **Delta is the default table format**; Delta Lake for Spark, Delta tables under Unity Catalog.
6. **Lineage and tags are not optional** - govern at ingest, not post hoc.
7. **Every notebook / repo change runs in CI** before it runs against prod data.
8. **Declarative Automation Bundles deploy projects**; Terraform provisions account/workspace infrastructure.
9. **System tables are operational infrastructure** for cost, audit, lineage, and query history.

## Non-Negotiables

- Production data uses Unity Catalog: three-part names, group/service-principal ownership, governed external locations or volumes.
- No persistent DBFS mounts (`dbfs:/mnt/...`) for governed production data.
- No personal access tokens in production automation.
- No `account users` grants, individual owners, or broad `ALL PRIVILEGES` grants without documented exception.
- Standard access mode is the default. Dedicated access mode must state the technical reason.
- Deployable jobs and Lakeflow pipelines use Declarative Automation Bundles with `databricks bundle validate` in CI.
- Serverless SQL / jobs / Lakeflow are preferred where available and appropriate; classic clusters require a reason and a policy.
- PII/PCI/sensitive tables require tags, masks, row filters, and audit visibility before gold/serving publication.

---

## Workflow 1 - Workspace Bootstrap

Stand up a new workspace with governance, security, and cost controls from day one.

### Steps

1. **Account-level setup**:
   - Account console used for identity, Unity Catalog metastore, and workspace provisioning
   - SSO via Okta / Entra ID / Google with SCIM provisioning
   - Admin role in a small, audited group
2. **Unity Catalog metastore** per region, tied to cloud storage location (one per region, one per env optionally)
3. **Workspace deployment** via Terraform (`databricks` provider):
   - Network: private subnets, VPC endpoints / Private Link
   - Customer-managed keys for notebooks and workspace storage
   - Workspace bound to specific metastore
4. **Groups and access** (via SCIM from IdP):
   - `admins-<workspace>` - workspace admins
   - `data-engineers-<env>`, `data-analysts-<env>`, `data-scientists-<env>`, `platform-<env>`
   - Keep global admin list tiny
5. **Cluster policies** (see Workflow 4) for all user-facing compute
6. **Catalog structure**:
   - Catalogs per environment (`dev`, `stage`, `prod`) or per domain (`sales`, `marketing`)
   - Schemas within: `raw`, `staging`, `curated`, `sandbox`
   - Default grants minimal; team-specific access roles
7. **External locations + storage credentials** (Unity Catalog) for cloud object storage; no direct S3/ADLS/GCS creds in notebooks
8. **Budget and alerts**:
   - System tables for billing (`system.billing.usage`)
   - Dashboards for cost by workspace / cluster / user / job
   - Alerts on spend anomalies

**Deliverable:** Terraform modules (account, workspace, UC, groups, policies), bootstrap runbook, cost dashboard.

See [references/workspace-bootstrap.md](references/workspace-bootstrap.md).

---

## Workflow 2 - Unity Catalog Migration

Migrate from Hive metastore (or no governance) to Unity Catalog.

### Steps

1. **Inventory**:
   - All databases / tables in Hive
   - Locations (mount points, `dbfs:/mnt/...`, direct S3 paths)
   - Access patterns (who reads / writes)
   - Data pipelines depending on Hive paths
2. **Metastore setup** (if not already done).
3. **External locations** in Unity Catalog for the cloud storage backing the Hive tables.
4. **Catalog and schema creation** that mirrors the source structure (or a better one).
5. **Migration options**:
   - **Upgrade in place**: `SYNC` command for schemas, or `CREATE TABLE ... LIKE ... LOCATION ...` to point UC tables at existing storage
   - **Copy**: `CREATE TABLE ... AS SELECT ...` into new UC tables (physical re-write; expensive but clean)
   - **Dual-write during transition**: write to both Hive and UC, read from UC, retire Hive
6. **Lineage and ownership**:
   - Set UC owner to a group, not a person
   - Add tags for sensitivity, owner, data steward
7. **Access control**:
   - Grants at catalog / schema / table level
   - No `ANONYMOUS FUNCTION` / `ALL PRIVILEGES` sprawl
   - Column-level masking / row filters where needed
8. **Cut over** pipelines and BI:
   - Update SQL Warehouses to use UC as default catalog
   - Update notebooks / jobs to reference `catalog.schema.table` three-part names
   - Disable Hive metastore access path after validation
9. **Decommission** Hive once all reads have moved.

**Deliverable:** Migration plan per database, cutover runbook, rollback plan, governance model (owners, stewards, tags, classifications).

---

## Workflow 3 - Lakeflow Spark Declarative Pipelines (formerly DLT)

Lakeflow Spark Declarative Pipelines for declarative, managed, observable pipelines. Existing DLT syntax still works; new Python should prefer `from pyspark import pipelines as dp`.

### When Lakeflow

- Streaming / micro-batch SCD pipelines
- Data quality enforcement (expectations) required
- Lineage and observability wanted out of the box
- Team prefers declarative SQL / Python over hand-orchestrated jobs

### When NOT Lakeflow

- One-off batch jobs
- Extensive custom Spark (Lakeflow constrains some APIs)
- Cost sensitivity with low duty cycle (pipeline compute has overhead)

### Current Python naming

```python
from pyspark import pipelines as dp

@dp.table
def raw_events():
    return spark.readStream.table("prod.raw.events")

@dp.materialized_view
def daily_event_counts():
    return spark.read.table("prod.silver.events").groupBy("event_date").count()
```

DLT compatibility mapping:

- `import dlt` -> `from pyspark import pipelines as dp`
- `@dlt.table` for streaming -> `@dp.table`
- `@dlt.table` for batch -> `@dp.materialized_view`
- `@dlt.view` -> `@dp.temporary_view`
- `dlt.apply_changes(...)` -> `dp.create_auto_cdc_flow(...)`

### Design

1. **Ingest to raw** (bronze) from cloud storage via Auto Loader or Kafka
2. **Stage** (silver) with schema enforcement, de-dup, CDC via `APPLY CHANGES INTO`
3. **Curated** (gold) for business aggregates / dimensional model
4. **Expectations** on each layer:
   - `@expect_or_drop` for quality-gate columns
   - `@expect_or_fail` for must-pass invariants
   - Track failure counts in DLT event log
5. **Serverless Lakeflow** where available for lower cost and managed sizing
6. **Continuous vs triggered**: continuous for streaming SLAs; triggered for batch windows
7. **Target target_lag** with Dynamic Tables equivalents or DLT settings
8. **Naming and lineage**: three-part UC names end-to-end; tags on every table

### Guardrails

- Pipeline in Git; deployed via Declarative Automation Bundles or Terraform
- CI: unit tests for transformations, integration test against a dev catalog
- Alerting: event log -> metrics -> alerts on expectation failures and pipeline failures
- Cost budget per pipeline

---

## Workflow 4 - Cluster Policies

Enforce cost, security, and compatibility at cluster-creation time.

### Policies to define

| Policy | Audience | Shape |
|---|---|---|
| `interactive-small` | Data analysts | Single-node or 1-4 workers; auto-terminate 30-60 min; Standard access mode |
| `interactive-medium` | Data engineers / scientists | 1-8 workers; auto-terminate 60 min; Standard access mode |
| `job-compute` | Jobs / Lakeflow | Fixed instance types; no interactive attach; auto-scale caps |
| `ml-gpu` | Data scientists | GPU-enabled types; restricted to ML group; auto-terminate 30 min |
| `shared-serverless-sql` | SQL users | Serverless SQL Warehouse sizes S/M/L, governed by policy |

### Policy content

- **Enforced tags**: `cost_center`, `owner`, `env`, `pipeline` (billable by tag)
- **Runtime pinning** to LTS + latest patch
- **Init scripts** disallowed or restricted to vetted list
- **Access mode** = Standard for most UC workloads; Dedicated only by documented exception
- **DBFS / mount usage** disallowed in UC-only workspaces
- **Instance profiles / IAM roles** via managed service credentials

### Terraform

```hcl
resource "databricks_cluster_policy" "interactive_small" {
  name       = "interactive-small"
  definition = jsonencode({
    "spark_version"       = { "type": "fixed", "value": "14.3.x-scala2.12" },
    "autotermination_minutes" = { "type": "range", "minValue": 15, "maxValue": 60 },
    # Provider-level field/value may vary by Databricks provider version.
    # Human-facing policy: Standard access mode for most UC workloads.
    "data_security_mode"  = { "type": "fixed", "value": "USER_ISOLATION" },
    "custom_tags.cost_center" = { "type": "unlimited" },
    # ...
  })
}
```

Then grant `CAN_USE` to the right group.

---

## Workflow 5 - Cost and Performance Tuning

### Levers (ordered by impact)

1. **Right compute type**:
   - Serverless SQL for BI
   - Job compute (not all-purpose) for jobs
   - Serverless Lakeflow where eligible
2. **Photon** on for Spark SQL / DataFrame workloads - almost always faster and cheaper
3. **Auto-scaling** - set min low; max capped by policy
4. **Auto-terminate** - short for interactive; stricter on policies
5. **Spot instances** - on for job compute where tolerant of evictions; never for latency-critical
6. **Instance type** - memory-optimized for big joins; compute-optimized for ML inference; right-size vs spillage
7. **Query** - partition pruning, Z-order, `OPTIMIZE`/`VACUUM` cadence, broadcast joins, caching
8. **Storage**:
   - Delta `OPTIMIZE` when small-file metrics justify it, or use platform-managed optimization where available
   - `VACUUM` retention tuned to recovery needs
   - Liquid Clustering where partitioning would fight the query pattern

### Monitoring

- `system.billing.usage` for DBU cost by workspace, cluster, job, user, tag
- `system.query.history` for slow queries
- `system.compute.*` for cluster utilization
- Cost dashboard per team / product

---

## Workflow 6 - Governance Audit

### Steps

1. **Catalog inventory**: catalogs, schemas, tables, volumes, functions. Owner + tags per table.
2. **Access grants**: pull from `information_schema.*` and Unity Catalog grants. Flag:
   - Grants to `account users` (broad)
   - `ALL PRIVILEGES` at catalog / schema level
   - Non-group grants
3. **Sensitive data**:
   - PII tagged and masked
   - Row filters configured where applicable
   - Tokenization for PCI
4. **Network**:
   - Private Link / VPC endpoints
   - No public workspace access from the internet (IP ACLs, Private Access)
5. **Identity**:
   - SCIM from IdP
   - Personal access tokens rotated or replaced with OAuth
   - Service principals scoped; not in admin groups
6. **Secrets**:
   - Secret scopes used, not hard-coded; scoped to groups
   - Cloud-managed secrets (Key Vault / Secrets Manager) via backed scopes
7. **Audit**:
   - System tables `system.access.audit`, `system.access.table_lineage`, `system.access.column_lineage`
   - Cost and query monitoring from `system.billing.usage`, `system.query.history`, and `system.compute.*`
   - Streamed to SIEM; retention per policy
   - Alerts on privilege changes, admin role grants, token creation

## Workflow 7 - Export Workspace Assets into Git

Use when notebooks/files/workspace assets exist only in the Databricks workspace and are not yet in a Git folder or repo. Export first, then refactor.

### When to use

- A team built notebooks directly in `/Workspace/Users/...`
- A demo or prototype needs to become maintainable source
- A workspace-only notebook is about to be converted to a job or Lakeflow pipeline
- A review needs a diffable source snapshot before cleanup

### Steps

1. **Inventory workspace paths**:

   ```bash
   databricks workspace list /Workspace/Users/<user> --absolute
   databricks workspace list /Workspace/Shared/<project> --absolute
   ```

2. **Export the workspace directory**:

   ```bash
   mkdir -p workspace-export
   databricks workspace export-dir \
     /Workspace/Users/<user>/<project> \
     ./workspace-export/<project> \
     --overwrite
   ```

3. **Review exported formats**:
   - notebooks/files should be source-reviewable (`.py`, `.scala`, `.sql`, `.ipynb` depending on workspace format and export behavior)
   - remove generated output/noise before committing
   - do not export secrets, outputs containing credentials, or ad-hoc data dumps

4. **Commit exported source before refactoring** so cleanup has a baseline diff.
5. **Convert deployable assets** to Declarative Automation Bundles or Terraform:
   - jobs / tasks / pipelines -> bundle YAML
   - workspace permissions / groups / policies -> Terraform or account-level automation
   - notebooks -> thin orchestration over versioned Python/SQL libraries
6. **Lock down workspace edits** after migration:
   - repo/bundle becomes source of truth
   - direct workspace edits are break-glass only
   - production runs use deployed jobs/bundles, not ad-hoc notebook state

### What `workspace export-dir` does not capture

`databricks workspace export-dir` is useful for notebooks and workspace files. It does **not** fully capture jobs, permissions, clusters, SQL warehouses, secrets, Unity Catalog objects, alerts, dashboards, or pipelines as deployable infrastructure. Move those to Declarative Automation Bundles, Terraform, SQL, or API-managed configuration.

**Deliverable:** exported source committed to Git, plus a migration plan from workspace-only assets to bundle/Terraform-managed assets.

---

## Workflow 8 - Declarative Automation Bundles CI/CD

Use Declarative Automation Bundles (formerly Databricks Asset Bundles) for deployable Databricks projects.

### Minimum CI flow

1. Compile / unit test Python, SQL, and Scala code.
2. Store versioned artifacts in Unity Catalog volumes or a governed artifact repository.
3. Run `databricks bundle validate --target dev`.
4. Deploy to dev / staging with `databricks bundle deploy --target <target>`.
5. Run smoke/integration tests against a dev catalog.
6. Promote to production only after approval.

```bash
databricks bundle validate --target dev
databricks bundle deploy --target staging
databricks bundle run smoke-tests --target staging
```

Authentication for CI uses workload identity / OIDC or service principals. Do not use user PATs.

## Workflow 9 - AI / ML / Model Governance

For ML and AI workloads:

- Use MLflow model registry under Unity Catalog where available.
- Use service principals for scheduled training / serving jobs.
- Use Dedicated access mode only when ML runtime, GPUs, R, or unsupported Standard-mode APIs require it.
- Tag models, features, and evaluation tables with owner, sensitivity, environment, and cost center.
- Keep prompt/RAG/vector-search artifacts under governed catalogs, schemas, and volumes.

---

## Workflow 10 - Recovery via Delta Time Travel

Delta tables preserve history; `RESTORE` brings you back.

```sql
-- Inspect
DESCRIBE HISTORY my_table;

-- Query old state
SELECT * FROM my_table VERSION AS OF 42;
SELECT * FROM my_table TIMESTAMP AS OF '2026-04-19T10:00:00';

-- Restore the table
RESTORE TABLE my_table TO VERSION AS OF 42;
-- or
RESTORE TABLE my_table TO TIMESTAMP AS OF '2026-04-19T10:00:00';
```

### Guardrails

- `VACUUM` retention dictates how far back you can go - set per-table based on recovery needs
- For hard-delete / GDPR: use `VACUUM` with lower retention + explicit delete workflow
- Test `RESTORE` in dev; have a runbook

---

## Anti-patterns

1. Personal access tokens in production code
2. All-purpose clusters running scheduled jobs (expensive, contention)
3. No cluster policies (users pick 32-worker XL for ad-hoc queries)
4. Mount points and DBFS as persistent storage in UC workspaces
5. `USE CATALOG hive_metastore` lingering in prod after UC migration
6. Admin rights granted to groups that include all engineers
7. Notebooks as production code paths (without Declarative Automation Bundles or CI)
8. No Photon on compute that would benefit
9. Auto-terminate disabled "for convenience"
10. No cost dashboard; surprise bill each month
11. Treating Lakeflow / Declarative Pipelines as "just notebooks" without CI or bundle deployment
12. Dedicated compute used as a default instead of a documented exception
13. No system tables or audit export in production workspaces

---

## References

- [workspace-bootstrap.md](references/workspace-bootstrap.md) - Terraform-driven workspace + UC setup

## Related

- Rule: [481-databricks.mdc](../../rules/481-databricks.mdc)
- Rule: [480-data-engineering.mdc](../../rules/480-data-engineering.mdc) (cross-platform data contracts, DQ)
- Rule: [475-sql.mdc](../../rules/475-sql.mdc) (safe SQL patterns)
- Rule: [316-zero-trust.mdc](../../rules/316-zero-trust.mdc) (data tier under Zero Trust)
- Skill: [data-engineering](../data-engineering/) (pipeline concepts)
- Skill: [snowflake](../snowflake/) (for comparison)
