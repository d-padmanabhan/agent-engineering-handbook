# Cursor Rules Index

Quick lookup table for all Cursor rules files in `rules/`.

## Core Rules (000-099)

| File | Description | Priority | Always Apply |
|------|-------------|----------|--------------|
| [010-workflow.mdc](010-workflow.mdc) | Plan/Implement/Review workflow with context persistence for complex projects. | 10 | Yes |
| [015-context-engineering.mdc](015-context-engineering.mdc) | Prompt packing, retrieval, and compaction patterns for reliable agent work. | 15 | Yes |
| [020-agent-audit.mdc](020-agent-audit.mdc) | Enforce no-remote-writes, mandatory verification, checkpoints/backups, and an auditable run report for AI agents. | 20 | Yes |

## Foundation (100-199)

| File | Description | Priority | Always Apply |
|------|-------------|----------|--------------|
| [100-core.mdc](100-core.mdc) | Repo-wide engineering guardrails for review & generation. | 100 | Yes |
| [110-configuration.mdc](110-configuration.mdc) | Patterns for managing configuration with proper precedence, environment variables, and validation. | 110 | Yes |
| [120-utilities.mdc](120-utilities.mdc) | Practical tool selection for agents reading docs, blogs, logs, and diagrams (curl, lynx, jq, httpie, ripgrep, Playwright, OCR, VLM) | 120 | Yes |
| [130-git.mdc](130-git.mdc) | Conventional commits, signed commits, PR hygiene, branch naming, and foundational GitHub repository scaffolding requirements. | 130 | Yes |
| [140-bash.mdc](140-bash.mdc) | Production-grade Bash standards for portability, safety, performance, and maintainability. | 140 | No |
| [150-justfile.mdc](150-justfile.mdc) | Standardized justfile patterns for consistent project commands across platforms and languages. | 150 | No |
| [160-github-actions.mdc](160-github-actions.mdc) | Secure, fast, maintainable workflows for this repo. | 160 | No |
| [170-cloudformation.mdc](170-cloudformation.mdc) | Secure, maintainable CloudFormation templates with best practices for AWS infrastructure. | 170 | No |
| [180-terraform.mdc](180-terraform.mdc) | Secure, efficient, modular Terraform with strong validation, docs, and CI hygiene. | 180 | No |
| [190-ansible.mdc](190-ansible.mdc) | Ansible playbooks, roles, best practices, idempotency, and infrastructure automation patterns | 190 | No |

## Languages (200-249)

| File | Description | Priority | Always Apply |
|------|-------------|----------|--------------|
| [200-python.mdc](200-python.mdc) | Opinionated, performance- and security-minded Python rules for generation and review. | 200 | No |
| [210-go.mdc](210-go.mdc) | Secure, idiomatic, maintainable Go with evidence-based performance; applies to generation and review. | 210 | No |
| [220-rust.mdc](220-rust.mdc) | Modern Rust patterns, ownership, error handling, async/await, and production-ready development practices | 220 | No |
| [230-javascript.mdc](230-javascript.mdc) | Secure-by-default, type-checked (JSDoc + @ts-check), performant, and testable JavaScript guidelines for generation and review. | 230 | No |
| [240-typescript.mdc](240-typescript.mdc) | Modern TypeScript patterns, type safety, advanced types, and production-ready configuration | 240 | No |
| [260-frontend.mdc](260-frontend.mdc) | Framework-agnostic frontend non-negotiables: rendering choice (SSG/SSR/SPA/ISR), bundle budgets, three-bucket state, WCAG 2.2 AA, Core Web Vitals, testing pyramid, supply-chain security. File-scoped to .tsx/.vue/.svelte/config files. | 260 | No |

## Tools & Platforms (250-299)

| File | Description | Priority | Always Apply |
|------|-------------|----------|--------------|
| [250-cli.mdc](250-cli.mdc) | Patterns and best practices for building command-line interfaces and tools. | 250 | No |

## Testing & Security (300-399)

| File | Description | Priority | Always Apply |
|------|-------------|----------|--------------|
| [300-testing.mdc](300-testing.mdc) | Comprehensive testing guide covering unit, integration, E2E, test frameworks, patterns, and CI/CD integration | 300 | No |
| [310-security.mdc](310-security.mdc) | Comprehensive security guide covering OWASP Top 10, secret management, vulnerability scanning, and secure coding practices | 310 | Yes |
| [315-iam.mdc](315-iam.mdc) | Practical security guidance for IAM design and identity protocols (OIDC/OAuth2/PKCE, SAML/ADFS) plus PKI and PAM operational patterns. | 315 | No |
| [316-zero-trust.mdc](316-zero-trust.mdc) | Distinguished-engineer Zero Trust: principles-first security across identity, network, data, workload, and AI/agent systems. | 316 | Yes |
| [317-okta.mdc](317-okta.mdc) | Okta Workforce Identity: orgs, apps, users/groups, policies, lifecycle (SCIM), Workflows, Advanced Server Access, Admin API, and terraform-provider-okta. | 317 | No |
| [318-workload-identity.mdc](318-workload-identity.mdc) | Attestation-based workload identity: SPIFFE/SPIRE/SVIDs/mTLS, cloud IAM (IRSA, GCP WI, Managed Identity, VPC Lattice), and OIDC federation bridges. | 318 | No |
| [320-api-design.mdc](320-api-design.mdc) | REST API design patterns, GraphQL, gRPC, versioning, authentication, and API documentation standards | 320 | No |
| [325-networking.mdc](325-networking.mdc) | Networking & transport non-negotiables: HTTP/gRPC client reuse, TCP keepalive, wire-format choice, protobuf field-number safety, idle-timeout discipline. File-scoped to .proto and buf.* files. | 325 | No |
| [330-observability.mdc](330-observability.mdc) | Logging, metrics, tracing, alerting, and observability patterns for production systems | 330 | No |

## Cloud & Infrastructure (400-499)

| File | Description | Priority | Always Apply |
|------|-------------|----------|--------------|
| [400-cloudflare.mdc](400-cloudflare.mdc) | End-to-end prompts and patterns for designing, testing, and deploying Cloudflare rulesets (WAF, Rate Limiting, Transform, Workers integration). | 400 | No |
| [401-cloudflare-workers.mdc](401-cloudflare-workers.mdc) | File-scoped non-negotiables for authoring or reviewing Cloudflare Workers in TypeScript: Module Workers only, typed Env from wrangler types, no secrets in logs, ctx.waitUntil for fire-and-forget, subrequest budgets, named bindings only, Service Bindings + RPC for Worker-to-Worker calls, wrangler.jsonc as source of truth. Loads on wrangler config files + common Worker entry-point names. | 401 | No |
| [405-cloudflare-waf-rules.mdc](405-cloudflare-waf-rules.mdc) | Interface-agnostic tactical playbook for Cloudflare WAF rule authoring across Terraform, Dashboard, and Rulesets API (custom rules + managed-rule exceptions): source-of-truth discipline, pre-edit gate, path predicate matrix, multi-value header syntax, required guards, per-interface provenance, anti-patterns, per-interface reviewer checklist. | 405 | No |
| [410-aws.mdc](410-aws.mdc) | Best practices for AWS services, EKS, Platform Engineering, Zero Trust, and cloud infrastructure patterns. | 410 | No |
| [412-aws-iam.mdc](412-aws-iam.mdc) | AWS-specific IAM guidance covering principal types, policy evaluation, cross-account assume role patterns, SCPs, KMS key policies/grants, and AccessDenied debugging. | 412 | No |
| [420-gcp.mdc](420-gcp.mdc) | GCP platform engineering patterns, Cloud Build, Terraform for GCP, and cloud architecture best practices | 420 | No |
| [430-azure.mdc](430-azure.mdc) | Azure platform engineering patterns, ARM/Bicep templates, Azure DevOps, and cloud architecture best practices | 430 | No |
| [440-docker.mdc](440-docker.mdc) | Production-ready Docker patterns, multi-stage builds, security scanning, and compose orchestration | 440 | No |
| [450-kubernetes.mdc](450-kubernetes.mdc) | Best practices for Kubernetes development, EKS operations, CRD development, concurrency patterns, and Podtrace-based runtime debugging. | 450 | No |
| [460-helm.mdc](460-helm.mdc) | Helm charts, best practices, templating, values management, and GitOps deployment patterns | 460 | No |
| [470-postgresql.mdc](470-postgresql.mdc) | Database naming conventions, schema patterns, and PostgreSQL best practices. | 470 | No |
| [475-sql.mdc](475-sql.mdc) | Safe, maintainable SQL patterns for analysts and engineers - command categories (DQL/DML/DDL/DCL/TCL), transactions, and destructive-operation guardrails. | 475 | No |
| [480-data-engineering.mdc](480-data-engineering.mdc) | Cross-platform data engineering standards (batch + streaming): data contracts, backfills, quality, governance, cost, and observability. | 480 | No |
| [481-databricks.mdc](481-databricks.mdc) | Databricks (Spark/Delta/Unity Catalog/DLT) patterns for safe, performant, governable data pipelines. | 481 | No |
| [482-snowflake.mdc](482-snowflake.mdc) | Snowflake warehouse, security, and query patterns (RBAC, cost/perf, streams/tasks, loading) for production data systems. | 482 | No |
| [483-kafka.mdc](483-kafka.mdc) | Confluent Kafka patterns for topics, schemas, producers/consumers, reliability, security, and operability. | 483 | No |
| [484-teradata.mdc](484-teradata.mdc) | Teradata-specific SQL and performance patterns (indexes, stats, spool, joins, QUALIFY) for safe and efficient workloads. | 484 | No |

## AI & MCP (500-599)

| File | Description | Priority | Always Apply |
|------|-------------|----------|--------------|
| [500-ai-ml.mdc](500-ai-ml.mdc) | LLM API integration, cloud AI services (Vertex AI, Bedrock, Azure OpenAI), AI agents, prompt engineering, and RAG patterns | 500 | No |
| [510-mcp-servers.mdc](510-mcp-servers.mdc) | Patterns and best practices for building Model Context Protocol (MCP) servers and tools. | 510 | No |

## Documentation Standards (800-899)

| File | Description | Priority | Always Apply |
|------|-------------|----------|--------------|
| [800-markdown.mdc](800-markdown.mdc) | Markdown/MDX style: GitHub alerts, **clickable Markdown links** (no backticks on navigational URLs), and Mermaid diagrams. | 800 | Yes |
| [810-documentation.mdc](810-documentation.mdc) | Patterns for creating effective documentation including documentation websites and markdown best practices. | 810 | No |
| [815-reactflow-diagrams.mdc](815-reactflow-diagrams.mdc) | Interactive architecture canvases with @xyflow/react: nodes, edges, Cloudflare shell grouping, readability, verification. | 815 | No |
| [820-open-source.mdc](820-open-source.mdc) | Best practices for open source projects including contribution guidelines, documentation, and community management. | 820 | No |

## Local Overrides (900-999)

| File | Description | Priority | Always Apply |
|------|-------------|----------|--------------|
| [999-local-overrides.mdc](999-local-overrides.mdc) | Workspace-specific rule overrides. Customize this file for project-specific needs. | 999 | No |

---

## Quick Reference

- **Workflow**: [010-workflow.mdc](010-workflow.mdc), [015-context-engineering.mdc](015-context-engineering.mdc), [020-agent-audit.mdc](020-agent-audit.mdc)
- **Core engineering**: [100-core.mdc](100-core.mdc), [130-git.mdc](130-git.mdc), [110-configuration.mdc](110-configuration.mdc)
- **Utilities + docs**: [120-utilities.mdc](120-utilities.mdc), [800-markdown.mdc](800-markdown.mdc), [810-documentation.mdc](810-documentation.mdc), [815-reactflow-diagrams.mdc](815-reactflow-diagrams.mdc)
- **Languages**: [140-bash.mdc](140-bash.mdc), [200-python.mdc](200-python.mdc), [210-go.mdc](210-go.mdc), [220-rust.mdc](220-rust.mdc), [230-javascript.mdc](230-javascript.mdc), [240-typescript.mdc](240-typescript.mdc)
- **Security**: [310-security.mdc](310-security.mdc), [315-iam.mdc](315-iam.mdc), [316-zero-trust.mdc](316-zero-trust.mdc), [317-okta.mdc](317-okta.mdc), [318-workload-identity.mdc](318-workload-identity.mdc), [412-aws-iam.mdc](412-aws-iam.mdc)
- **Cloud + IaC**: [170-cloudformation.mdc](170-cloudformation.mdc), [180-terraform.mdc](180-terraform.mdc), [400-cloudflare.mdc](400-cloudflare.mdc), [401-cloudflare-workers.mdc](401-cloudflare-workers.mdc), [405-cloudflare-waf-rules.mdc](405-cloudflare-waf-rules.mdc), [410-aws.mdc](410-aws.mdc), [420-gcp.mdc](420-gcp.mdc), [430-azure.mdc](430-azure.mdc)
- **Containers**: [440-docker.mdc](440-docker.mdc), [450-kubernetes.mdc](450-kubernetes.mdc), [460-helm.mdc](460-helm.mdc)
- **Databases**: [470-postgresql.mdc](470-postgresql.mdc), [475-sql.mdc](475-sql.mdc)
- **AI + MCP**: [500-ai-ml.mdc](500-ai-ml.mdc), [510-mcp-servers.mdc](510-mcp-servers.mdc)

## Files Marked "Always Apply"

- [010-workflow.mdc](010-workflow.mdc)
- [015-context-engineering.mdc](015-context-engineering.mdc)
- [020-agent-audit.mdc](020-agent-audit.mdc)
- [100-core.mdc](100-core.mdc)
- [110-configuration.mdc](110-configuration.mdc)
- [120-utilities.mdc](120-utilities.mdc)
- [130-git.mdc](130-git.mdc)
- [310-security.mdc](310-security.mdc)
- [316-zero-trust.mdc](316-zero-trust.mdc)
- [800-markdown.mdc](800-markdown.mdc)
