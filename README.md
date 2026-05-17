# Agent Engineering Handbook

> **Production-grade rules, skills, commands, and MCP server for AI coding agents - language, cloud, security, and AI/ML standards for 15+ stacks**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Comprehensive, battle-tested configuration for AI coding agents. Curated **rules** (`.mdc`), **Agent Skills**, **slash commands**, an **MCP server**, and **lifecycle hooks** covering languages, cloud platforms, DevOps tools, data platforms, identity systems, AI/ML, Zero Trust, and engineering patterns.

> [!NOTE]
> **Agent-neutral.** Originally built for Cursor; today the content ships in formats compatible with **Cursor**, **Claude Code**, and **Codex** - rules (`.cursor/rules/`, `AGENTS.md`), Agent Skills (`.cursor/skills/`, `.claude/skills/`, `.codex/skills/`), and slash commands. The MCP server works with any MCP-compatible client.
>
> **Renamed in May 2026** from `cursor-engineering-rules` to `agent-engineering-handbook` to reflect what the repo became (rules + skills + commands + MCP server + hooks for any AI coding agent, not just Cursor). GitHub redirects old URLs, so existing clones, submodules, and bookmarks keep working.

---

## What's Included

### Core Standards

- **[100-core.mdc](rules/100-core.mdc)** - Core coding standards and review guidelines
- **[015-context-engineering.mdc](rules/015-context-engineering.mdc)** - Context engineering (prompt packing, retrieval, compaction)
- **[010-workflow.mdc](rules/010-workflow.mdc)** - Development workflow patterns
- **[020-agent-audit.mdc](rules/020-agent-audit.mdc)** - Agent audit requirements
- **[130-git.mdc](rules/130-git.mdc)** - Git conventions, commit standards, and mandatory commit signing (with documented exceptions)

### Programming Languages

- **[200-python.mdc](rules/200-python.mdc)** - Python best practices (PEP 8, type hints, async)
- **[210-go.mdc](rules/210-go.mdc)** - Go patterns (error handling, concurrency, generics)
- **[230-javascript.mdc](rules/230-javascript.mdc)** - JavaScript/Node.js (ES modules, async/await)
- **[240-typescript.mdc](rules/240-typescript.mdc)** - TypeScript (type safety, advanced types)
- **[220-rust.mdc](rules/220-rust.mdc)** - Rust (ownership, borrowing, async)
- **[140-bash.mdc](rules/140-bash.mdc)** - Shell scripting (POSIX compliance, safety)

### Cloud Platforms

- **[410-aws.mdc](rules/410-aws.mdc)** - AWS (EKS, VPC Lattice, Zero Trust, IAM)
- **[430-azure.mdc](rules/430-azure.mdc)** - Azure (Bicep, Key Vault, App Service)
- **[420-gcp.mdc](rules/420-gcp.mdc)** - GCP (Cloud Run, GKE, Secret Manager)
- **[400-cloudflare.mdc](rules/400-cloudflare.mdc)** - Cloudflare (Workers, Rules Engine)

### AI & Machine Learning

- **[500-ai-ml.mdc](rules/500-ai-ml.mdc)** - LLM integration (OpenAI, Claude, Bedrock, Vertex AI)
- **[510-mcp-servers.mdc](rules/510-mcp-servers.mdc)** - Model Context Protocol servers

### DevOps & Infrastructure

- **[180-terraform.mdc](rules/180-terraform.mdc)** - Terraform (modules, state, validation)
- **[170-cloudformation.mdc](rules/170-cloudformation.mdc)** - CloudFormation templates
- **[450-kubernetes.mdc](rules/450-kubernetes.mdc)** - Kubernetes & EKS patterns, including Podtrace runtime debugging
- **[160-github-actions.mdc](rules/160-github-actions.mdc)** - GitHub Actions (workflows, security, OIDC)
- **[190-ansible.mdc](rules/190-ansible.mdc)** - Ansible (playbooks, roles, idempotency)
- **[460-helm.mdc](rules/460-helm.mdc)** - Helm charts and templating
- **[440-docker.mdc](rules/440-docker.mdc)** - Docker & containers (multi-stage builds, security)
- **[150-justfile.mdc](rules/150-justfile.mdc)** - Justfile patterns (modern command runner)

### Security & Testing

- **[310-security.mdc](rules/310-security.mdc)** - OWASP Top 10, secret management
- **[316-zero-trust.mdc](rules/316-zero-trust.mdc)** - Distinguished Engineer - Zero Trust (identity, network, data, workload, AI/agents)
- **[317-okta.mdc](rules/317-okta.mdc)** - Okta Workforce Identity (SSO, MFA, SCIM, policies, Workflows, ASA, terraform-provider-okta)
- **[318-workload-identity.mdc](rules/318-workload-identity.mdc)** - Workload identity (SPIFFE/SPIRE, cloud IAM, OIDC federation)
- **[300-testing.mdc](rules/300-testing.mdc)** - Unit/Integration/E2E testing strategies

### Patterns & Best Practices

- **[320-api-design.mdc](rules/320-api-design.mdc)** - REST API design patterns
- **[330-observability.mdc](rules/330-observability.mdc)** - Logging, metrics, tracing
- **[470-postgresql.mdc](rules/470-postgresql.mdc)** - PostgreSQL patterns
- **[475-sql.mdc](rules/475-sql.mdc)** - Safe SQL patterns (transactions, destructive guardrails)
- **[480-data-engineering.mdc](rules/480-data-engineering.mdc)** - Data engineering core (contracts, backfills, DQ, governance)
- **[481-databricks.mdc](rules/481-databricks.mdc)** - Databricks (Spark/Delta/Unity Catalog/DLT)
- **[482-snowflake.mdc](rules/482-snowflake.mdc)** - Snowflake (RBAC, cost/perf, ingestion, tasks)
- **[483-kafka.mdc](rules/483-kafka.mdc)** - Kafka / Confluent (schemas, semantics, DLQ, ops)
- **[484-teradata.mdc](rules/484-teradata.mdc)** - Teradata SQL and performance patterns
- **[810-documentation.mdc](rules/810-documentation.mdc)** - Documentation standards
- **[815-reactflow-diagrams.mdc](rules/815-reactflow-diagrams.mdc)** - Interactive architecture diagrams (@xyflow/react / React Flow); playbook: [skills/reactflow-architecture-diagrams/SKILL.md](skills/reactflow-architecture-diagrams/SKILL.md) (symlink into `.cursor/skills/` in consumer projects)
- **[820-open-source.mdc](rules/820-open-source.mdc)** - Open source project patterns
- **[250-cli.mdc](rules/250-cli.mdc)** - CLI application patterns
- **[110-configuration.mdc](rules/110-configuration.mdc)** - Configuration management

### Utilities

- **[120-utilities.mdc](rules/120-utilities.mdc)** - CLI utilities (lynx, curl, jq, ripgrep, fd, fzf)
- **[800-markdown.mdc](rules/800-markdown.mdc)** - Markdown & Mermaid diagrams

### Scripts

Utility scripts for Cursor maintenance:

- **[cursor-maintenance.sh](scripts/cursor-maintenance.sh)** - Clean cache, logs, and temp files to reclaim disk space
- **[cursor-hooks-install.sh](scripts/cursor-hooks-install.sh)** - Install optional deterministic Cursor hooks (guardrails + audit)

```bash
# Preview cleanup
./scripts/cursor-maintenance.sh --dry-run

# Run cleanup
./scripts/cursor-maintenance.sh
```

See [scripts/README.md](scripts/README.md) for details.

### Hooks (optional)

Deterministic lifecycle hooks to observe/control agent behavior (for example: gate destructive shell commands, block reading `.env` files).

- Docs: **[`docs/HOOKS.md`](docs/HOOKS.md)**
- Cursor hook pack: **[`hooks/cursor/`](hooks/cursor/)**

---

## Slash Commands

Workflow commands for explicit phase transitions. Type `/command` in your agent's chat (Cursor / Claude Code / Codex) to trigger.

| Command | Purpose |
| --- | --- |
| `/init` | Initialize task - analyze project, detect complexity |
| `/plan` | Enter planning phase - analyze, design, document approach |
| `/creative` | Enter creative phase - explore design options for complex tasks |
| `/qa` | Run QA validation - check dependencies, config, environment |
| `/build` | Enter implementation phase - write code following approved plan |
| `/review` | Enter review phase - verify implementation, suggest improvements |
| `/self-review` | Comprehensive local PR review (compare branch to main) |
| `/quick-review` | Fast critical issues check (pre-commit validation) |
| `/check-progress` | Review work progress, propose commit message |
| `/archive` | Archive task - document lessons learned, update knowledge base |

**Installation:**

```bash
# Copy to your project
cp -r /path/to/agent-engineering-handbook/commands .cursor/commands

# Or symlink
ln -s /path/to/agent-engineering-handbook/commands .cursor/commands
```

**Workflow:**

```
Simple:   /init -> /build -> /review
Moderate: /init -> /plan -> /qa -> /build -> /review
Complex:  /init -> /plan -> /creative -> /qa -> /build -> /review -> /archive
```

See [commands/README.md](commands/README.md) for detailed documentation.

---

## MCP Server

Model Context Protocol (MCP) server for any MCP-compatible AI client (Cursor, Claude Desktop, Claude Code, Codex, and others).

```bash
# Install
cd mcp/cursor-rules-mcp
npm install
npm run build
npm link

# Configure Claude Desktop
# Add to ~/Library/Application Support/Claude/claude_desktop_config.json:
{
  "mcpServers": {
    "agent-engineering-handbook": {
      "command": "cursor-rules-mcp"
    }
  }
}
```

**Features:**

- Fetch workflow guide (Plan/Implement/Review)
- Fetch specific rules by category/topic
- List all available rules
- Just-in-time rule loading (load only what you need)

See [mcp/cursor-rules-mcp/README.md](mcp/cursor-rules-mcp/README.md) for full documentation.

---

## Configuration Approaches

Cursor supports two ways to load rules. Choose based on your needs:

### Approach A: Frontmatter-based (No `.cursorrules` needed)

Rules with `alwaysApply: true` in their frontmatter load automatically when placed in `.cursor/rules/`.

**Best for:** Personal setup, global rules across all projects

```bash
# Symlink to your home directory (applies to all projects)
mkdir -p ~/.cursor
ln -s /path/to/agent-engineering-handbook/rules ~/.cursor/rules

# Or symlink per-project
mkdir -p .cursor
ln -s /path/to/agent-engineering-handbook/rules .cursor/rules
```

**Rules that auto-load (`alwaysApply: true`):**

| Rule | Purpose |
| --- | --- |
| `010-workflow.mdc` | Plan/Implement/Review workflow |
| `015-context-engineering.mdc` | Prompt packing, retrieval, compaction |
| `020-agent-audit.mdc` | Agent audit requirements |
| `100-core.mdc` | Core coding standards |
| `110-configuration.mdc` | Configuration management |
| `120-utilities.mdc` | CLI tools |
| `130-git.mdc` | Git conventions and signed commits |
| `310-security.mdc` | Security best practices |
| `316-zero-trust.mdc` | Distinguished Engineer - Zero Trust |
| `800-markdown.mdc` | Markdown formatting |

Other rules load based on file patterns or explicit request.

### Approach B: Explicit `.cursorrules` file

Use a `.cursorrules` file for explicit control over which rules load.

**Best for:** Team projects, project-specific subsets, version-controlled config

```yaml
# .cursorrules - Option 1: Load all rules from directory
rulesDirectory: .cursor/rules

# .cursorrules - Option 2: Explicit rule list
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/200-python.mdc
  - .cursor/rules/410-aws.mdc
```

> [!NOTE]
> When using `.cursorrules`, rules with `alwaysApply: true` still load automatically in addition to your explicit list.

See [examples/.cursorrules-example](examples/.cursorrules-example) for tech-stack templates.

### Multi-Repo Workspaces

For workspaces with many repositories, rules load based on file patterns. Open a `.py` file and Python rules load; open a `.go` file and Go rules load. Most repos need zero per-repo configuration.

See [Multi-Repo Workspaces](docs/HOW-TO-USE.md#multi-repo-workspaces) for detailed guidance.

---

## Quick Start

### Option 1: Use Individual Rules

Copy specific rules to your project:

```bash
# Create Cursor rules directory
mkdir -p .cursor/rules

# Copy specific rules you need
cp path/to/agent-engineering-handbook/rules/200-python.mdc .cursor/rules/
cp path/to/agent-engineering-handbook/rules/410-aws.mdc .cursor/rules/

# (Optional) Copy workflow templates (tasks, active-context, etc.)
mkdir -p .cursor/rules/templates
cp path/to/agent-engineering-handbook/rules/templates/*.template .cursor/rules/templates/
```

### Option 1.5: Use Setup Scripts (Convenience)

If you keep a shared checkout of this repo, you can bootstrap a workspace with:

```bash
/path/to/agent-engineering-handbook/setup-workspace.sh -S -l .
```

Add to your `.cursorrules` file:

```yaml
rules:
  - .cursor/rules/200-python.mdc
  - .cursor/rules/410-aws.mdc
```

### Option 2: Use All Rules (Recommended)

Symlink the entire rules directory:

```bash
# From your project root
ln -s /absolute/path/to/agent-engineering-handbook/rules .cursor/rules
```

Configure `.cursorrules`:

```yaml
# Load all rules
rulesDirectory: .cursor/rules

# Or be selective with alwaysApply rules
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/200-python.mdc
  - .cursor/rules/310-security.mdc
```

### Option 3: Cherry-Pick by Technology

Create a custom `.cursorrules` that includes only relevant rules:

```yaml
# Python + AWS project
rules:
  - .cursor/rules/100-core.mdc
  - .cursor/rules/130-git.mdc
  - .cursor/rules/200-python.mdc
  - .cursor/rules/410-aws.mdc
  - .cursor/rules/180-terraform.mdc
  - .cursor/rules/310-security.mdc
  - .cursor/rules/300-testing.mdc
```

---

## Rule Priorities

Rules have `alwaysApply` flags and priority levels:

- **Always Apply**: Core standards (100-core, 130-git, 310-security)
- **High Priority**: Language-specific rules for your stack
- **Medium Priority**: Platform/tool-specific rules
- **Low Priority**: Documentation and utility guides

See [rules/INDEX.md](rules/INDEX.md) for complete categorization.

---

## Features

### Production Quality

- **Battle-tested** patterns from real-world projects
- **Security-first** approach (OWASP Top 10, secret scanning)
- **Performance-focused** (benchmarks, optimization patterns)

### Comprehensive Coverage

- **6 programming languages** (Python, Go, TypeScript, JavaScript, Rust, Bash)
- **4 major cloud platforms** (AWS, Azure, GCP, Cloudflare)
- **10+ DevOps tools** (Terraform, K8s, Docker, Ansible, Helm, GitHub Actions)
- **AI/ML integration** (OpenAI, Claude, Bedrock, Vertex AI)

### Code Examples

- **Real-world examples** for every pattern
- **Good vs Bad** comparisons
- **Common mistakes** and anti-patterns
- **Quick reference** sections

### Modern Standards

- **Latest versions** (Python 3.14+, Go 1.25+, Node 22+)
- **Modern patterns** (async/await, generics, type safety)
- **Current tools** (ripgrep, fd, fzf, just, jq)

---

## Customization

### Workspace-Specific Overrides

Use `999-local-overrides.mdc` for project-specific rules:

```bash
# Copy to your project
cp rules/999-local-overrides.mdc .cursor/rules/999-local-overrides.mdc

# Edit to add project-specific rules
vim .cursor/rules/999-local-overrides.mdc
```

### Creating Custom Rules

Follow the standard format:

```markdown
---
title: My Custom Rule
description: Project-specific patterns
priority: 900
alwaysApply: false
files:
  include:
    - "**/*.py"
---

# My Custom Rule

## Pattern 1
[Your custom patterns here]
```

---

## Contributing

Contributions are welcome! Please see [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md) for guidelines.

### Areas for Contribution

- Additional language support (Java, C#, Ruby, PHP)
- More cloud platform patterns
- Industry-specific patterns (fintech, healthcare, etc.)
- Performance benchmarks
- Additional code examples

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

This project was inspired by and incorporates patterns from:

- **AI Developer Guide**: <https://github.com/dwmkerr/ai-developer-guide> - Workflow patterns and context management
- **Cursor Memory Bank**: <https://github.com/vanzan01/cursor-memory-bank> - Context file management patterns
- **Shellwright**: <https://github.com/dwmkerr/shellwright> - Terminal automation MCP server patterns and PTY session management

Thanks to [@DaKaZ](https://github.com/DaKaZ) for suggesting the commands-based workflow approach.

---

## Related Projects

- [dotcursorrules.com](https://dotcursorrules.com/) - Community directory of framework-specific cursor rules (Next.js, Laravel, React, etc.). Use dotcursorrules for **framework recipes** and this repo for **engineering discipline**.
- [ACE-FCA](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents) - Advanced Context Engineering for Coding Agents. Excellent methodology on context management, "frequent intentional compaction", and Research -> Plan -> Implement workflows.
- [Cursor Memory Bank](https://github.com/vanzan01/cursor-memory-bank) - Command-based workflow system using Cursor's `/commands` feature for progressive rule loading.
- [Shellwright](https://github.com/dwmkerr/shellwright) - Playwright for the shell. MCP server for terminal automation, screenshots, and GIF recording. Excellent example of MCP server implementation with PTY session management.
- [eslint-config-airbnb](https://github.com/airbnb/javascript) - JavaScript style guide
- [google-styleguides](https://github.com/google/styleguide) - Google's style guides
- [uber-go-guide](https://github.com/uber-go/guide) - Uber's Go style guide

> [!NOTE]
> **Three Ways to Load Context:** This repo supports multiple approaches:
>
> 1. **Rules** (`.mdc` files) - Auto-load based on `alwaysApply` flags and file patterns
> 2. **Commands** (`/plan`, `/build`, etc.) - Explicit phase transitions for progressive disclosure
> 3. **MCP Server** - On-demand rule loading via tool calls
>
> Use all three together for maximum flexibility, or pick what works for your workflow.

## Cursor rules vs Cursor skills

Based on Cursor's docs:

- **Cursor Rules** ([docs](https://cursor.com/docs/context/rules))
  - **What they are**: System-level instructions included at the start of model context to provide persistent guidance
  - **Where they live**: typically `.cursor/rules/` (project, version-controlled), plus User Rules (global) and Team Rules (dashboard). Also `AGENTS.md` as a simpler alternative
  - **How they apply**: always apply, agent decides, file-glob scoped, or manual `@` mention
  - **Best for**: coding standards, architectural constraints, security guardrails, "do/don't", house style

- **Cursor Skills / Agent Skills** ([docs](https://cursor.com/docs/context/skills))
  - **What they are**: portable, version-controlled packages that teach an agent a domain-specific workflow; may include executable scripts the agent runs
  - **Where they live**: `.cursor/skills/` (project) or `~/.cursor/skills/` (user). Cursor also discovers `.claude/skills/` and `.codex/skills/` for compatibility
  - **How they apply**: the agent can auto-select a relevant skill, or you can invoke it manually via `/skill-name`. You can force "manual only" by setting `disable-model-invocation: true`
  - **Best for**: repeatable multi-step playbooks (release, deploy, migration, audit, generating artifacts) and "do X end-to-end" flows

## Skills shipped in this repo

Skills under `skills/` cover repeatable end-to-end workflows that pair with the rules above. Cursor auto-selects them based on the SKILL.md `description:` triggers; invoke manually as `/<skill-name>` when needed.

### Engineering & code

- **[skills/agent-workflow](skills/agent-workflow/)** - Plan/Implement/Review workflow + audit
- **[skills/core-engineering](skills/core-engineering/)** - core engineering principles, code review
- **[skills/python-development](skills/python-development/)** - Python 3.14+ patterns
- **[skills/typescript-javascript](skills/typescript-javascript/)** - TS/JS patterns
- **[skills/go-rust-systems](skills/go-rust-systems/)** - Go and Rust systems programming
- **[skills/bash-shell-scripting](skills/bash-shell-scripting/)** - production Bash scripts
- **[skills/scripting-automation](skills/scripting-automation/)** - advanced Bash automation

### Security & identity

- **[skills/security-testing](skills/security-testing/)** - OWASP Top 10 + testing strategies (overview)
- **[skills/codebase-security-audit](skills/codebase-security-audit/)** - 8-layer audit (secrets / SAST / SCA / taint / CPG / IaC / custom / DAST) + reference CI workflow
- **[skills/zero-trust](skills/zero-trust/)** - Distinguished-engineer Zero Trust playbook
- **[skills/aws-iam](skills/aws-iam/)** - AWS IAM operational patterns
- **[skills/okta](skills/okta/)** - Okta Workforce Identity playbook
- **[skills/workload-identity](skills/workload-identity/)** - SPIFFE/SPIRE/cloud IAM/OIDC federation

### Cloud, data & infrastructure

- **[skills/cloud-platforms](skills/cloud-platforms/)** - AWS / Azure / GCP / Cloudflare patterns
- **[skills/infrastructure-iac](skills/infrastructure-iac/)** - Terraform / Docker / Ansible / CloudFormation
- **[skills/containers-orchestration](skills/containers-orchestration/)** - Docker patterns
- **[skills/kubernetes-containers](skills/kubernetes-containers/)** - Kubernetes / Helm
- **[skills/database-postgresql](skills/database-postgresql/)** - PostgreSQL patterns
- **[skills/data-engineering](skills/data-engineering/)** - data pipelines, contracts, quality
- **[skills/snowflake](skills/snowflake/)** - Snowflake operational playbook
- **[skills/databricks](skills/databricks/)** - Databricks operational playbook
- **[skills/cicd-github-actions](skills/cicd-github-actions/)** - GitHub Actions patterns
- **[skills/networking-transport](skills/networking-transport/)** - TCP keepalive, HoL blocking, TTFB budget, HTTP/1.1 vs 2 vs 3, gRPC/Protobuf vs REST/JSON, connection pooling, long-lived connections

### AI, MCP & analysis

- **[skills/mcp-development](skills/mcp-development/)** - building MCP servers
- **[skills/web-research-kb-refresh](skills/web-research-kb-refresh/)** - bounded web-research KB refresh with atomic swap (general pattern)
- **[skills/multi-perspective-review](skills/multi-perspective-review/)** - weighted multi-advisor decision review with industry-precedent pairs

### Documentation & artifacts

- **[skills/documentation-standards](skills/documentation-standards/)** - Markdown + Mermaid + ADR patterns
- **[skills/reactflow-architecture-diagrams](skills/reactflow-architecture-diagrams/)** - interactive React Flow architecture canvases
- **[skills/single-file-dashboard](skills/single-file-dashboard/)** - zero-dependency single-file HTML dashboards (emailable / airgap-safe)

### Workflow patterns (meta)

- **[skills/skills-composition](skills/skills-composition/)** - patterns for chaining skills, scope resolution, graceful degradation
