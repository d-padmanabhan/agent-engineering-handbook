# Databricks Workspace Bootstrap

Terraform-driven setup for account, workspaces, Unity Catalog, groups, policies, system tables, and cost controls.

---

## Prerequisites

- Account console access (Databricks account owner / admin)
- Cloud subscription (AWS / Azure / GCP) with privileges to create IAM, networking, KMS, storage
- IdP for SSO + SCIM (Okta / Entra / Google)
- `databricks` Terraform provider configured with account- and workspace-level aliases
- Databricks CLI configured for Declarative Automation Bundles deployments

---

## Structure

```
terraform/
  account/                    # account-level: metastore, SCIM, admin groups
    main.tf
    variables.tf
    outputs.tf
  workspaces/
    prod-us-east/
      main.tf                 # workspace, network, KMS, cluster policies, catalog binding
      groups.tf               # group assignments
    stage-us-east/
    dev-us-east/
  catalogs/                   # Unity Catalog layout
    prod.tf
    stage.tf
    dev.tf
```

---

## Account-level (once per region)

```hcl
# Unity Catalog metastore (one per region)
resource "databricks_metastore" "this" {
  provider      = databricks.account
  name          = "primary-us-east-1"
  storage_root  = "s3://acme-uc-metastore-us-east-1/"
  region        = "us-east-1"
  owner         = "admins-account"
}

# SCIM from IdP (configured on IdP side pointing at account SCIM endpoint)
# Admin group
resource "databricks_group" "admins_account" {
  provider     = databricks.account
  display_name = "admins-account"
}
```

Tie SCIM in the IdP to provision these groups automatically; do not manage membership in Terraform if IdP is source of truth.

---

## Workspace

```hcl
resource "databricks_mws_networks" "this" {
  account_id   = var.databricks_account_id
  network_name = "ws-prod-us-east-vpc"
  vpc_id       = var.vpc_id
  subnet_ids   = var.private_subnet_ids
  security_group_ids = [var.databricks_sg_id]
}

resource "databricks_mws_customer_managed_keys" "this" {
  account_id   = var.databricks_account_id
  use_cases    = ["MANAGED_SERVICES", "STORAGE"]
  aws_key_info {
    key_arn = var.kms_key_arn
  }
}

resource "databricks_mws_workspaces" "prod" {
  account_id       = var.databricks_account_id
  workspace_name   = "prod-us-east"
  deployment_name  = "prod-us-east"
  network_id       = databricks_mws_networks.this.network_id
  managed_services_customer_managed_key_id = databricks_mws_customer_managed_keys.this.customer_managed_key_id
  storage_customer_managed_key_id          = databricks_mws_customer_managed_keys.this.customer_managed_key_id
  pricing_tier    = "PREMIUM"
}

# Bind workspace to metastore
resource "databricks_metastore_assignment" "prod" {
  provider     = databricks.account
  workspace_id = databricks_mws_workspaces.prod.workspace_id
  metastore_id = databricks_metastore.this.id
  default_catalog_name = "prod"
}
```

---

## Unity Catalog layout

```hcl
# External location for cloud storage
resource "databricks_storage_credential" "prod_uc" {
  name = "prod-uc-cred"
  aws_iam_role { role_arn = var.uc_role_arn }
}

resource "databricks_external_location" "prod_raw" {
  name           = "prod-raw"
  url            = "s3://acme-prod-uc/raw/"
  credential_name = databricks_storage_credential.prod_uc.name
}

# Catalog and schemas
resource "databricks_catalog" "prod" {
  name    = "prod"
  comment = "Production catalog"
  owner   = "admins-workspace"
}

resource "databricks_schema" "raw" {
  catalog_name = databricks_catalog.prod.name
  name         = "raw"
  owner        = "data-engineers-prod"
}

resource "databricks_schema" "curated" {
  catalog_name = databricks_catalog.prod.name
  name         = "curated"
  owner        = "data-engineers-prod"
}

# Grants
resource "databricks_grants" "prod_readers" {
  catalog = databricks_catalog.prod.name
  grant {
    principal  = "data-analysts-prod"
    privileges = ["USE_CATALOG", "USE_SCHEMA", "SELECT"]
  }
}
```

---

## Cluster policies

```hcl
resource "databricks_cluster_policy" "interactive_medium" {
  name = "interactive-medium"
  definition = jsonencode({
    "spark_version"        = { "type": "fixed", "value": "14.3.x-scala2.12" },
    # Provider-level field/value may vary by Databricks provider version.
    # Human-facing policy: Standard access mode for most UC workloads.
    "data_security_mode"   = { "type": "fixed", "value": "USER_ISOLATION" },
    "node_type_id"         = { "type": "allowlist", "values": ["i3.xlarge", "i3.2xlarge"] },
    "autotermination_minutes" = { "type": "range", "minValue": 15, "maxValue": 60 },
    "num_workers"          = { "type": "range", "minValue": 1, "maxValue": 8 },
    "custom_tags.cost_center" = { "type": "unlimited" },
    "custom_tags.owner"    = { "type": "unlimited" },
    "enable_elastic_disk"  = { "type": "fixed", "value": true },
    "spark_conf.spark.databricks.cluster.profile" = { "type": "fixed", "value": "singleNode", "hidden": true }
  })
}

resource "databricks_permissions" "interactive_medium_use" {
  cluster_policy_id = databricks_cluster_policy.interactive_medium.id
  access_control {
    group_name       = "data-engineers-prod"
    permission_level = "CAN_USE"
  }
}
```

---

## Cost controls

- **System tables** enabled at the account level (`system.billing.usage`, `system.access.audit`, `system.compute.*`, etc.)
- **Tags** enforced via cluster policies so billing rows are attributable
- **Budgets** (account console) with alerts at 50%, 75%, 90%, 100%
- **Dashboard** on top of `system.billing.usage` grouped by workspace / tag / user

---

## Secrets

```hcl
resource "databricks_secret_scope" "prod" {
  name = "prod"
  backend_type = "AZURE_KEYVAULT"   # or use DB-backed with caution
  keyvault_metadata {
    resource_id = var.keyvault_resource_id
    dns_name    = var.keyvault_dns
  }
}

resource "databricks_secret_acl" "prod_data_engineers" {
  scope       = databricks_secret_scope.prod.name
  principal   = "data-engineers-prod"
  permission  = "READ"
}
```

No long-lived tokens or cloud credentials in notebooks. Pull from scopes.

---

## CI / Deployment

- Terraform: plan + apply via CI on merge to `main`; pinned provider versions
- Declarative Automation Bundles (formerly Databricks Asset Bundles) for notebooks / jobs / Lakeflow pipelines: validate and deploy per env
- Pre-deploy tests (unit) and post-deploy smoke tests (integration against a dev catalog)

---

## Bootstrap checklist

- [ ] Metastore created per region
- [ ] SCIM from IdP; admin group populated from IdP
- [ ] Workspace via Terraform with Private Link / private subnets + CMK
- [ ] Workspace bound to metastore with `default_catalog_name`
- [ ] Catalogs and schemas for each env / domain, with group ownership
- [ ] External locations for cloud storage; no mounts / DBFS for persistent data
- [ ] Cluster policies for all user-facing compute
- [ ] Job compute policies separate from interactive
- [ ] Standard access mode default; Dedicated access mode exception documented
- [ ] Tags enforced; billable attribution
- [ ] System tables enabled; cost dashboard built
- [ ] Budgets and alerts configured
- [ ] Secrets via Key Vault / Secrets Manager scopes
- [ ] Audit (system.access.audit) streamed to SIEM
- [ ] Declarative Automation Bundles validate/deploy path configured for jobs and pipelines
