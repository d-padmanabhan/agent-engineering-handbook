# Agent Engineering Handbook MCP Server

**Model Context Protocol (MCP) server for Agent Engineering Handbook** - Production-grade AI agent rules for 15+ languages, multi-cloud infrastructure, and DevOps.

## Features

- **35+ Engineering Rules** covering languages, infrastructure, cloud platforms, and DevOps
- **15+ Languages:** Python, Go, Rust, TypeScript, JavaScript, Bash, and more
- **Multi-Cloud:** AWS, Azure, GCP, Cloudflare
- **Infrastructure as Code:** Terraform, CloudFormation, Kubernetes, Docker, Ansible, Helm
- **Production-Grade:** Security (OWASP), testing, observability, API design
- **Workflow Philosophy:** Plan/Implement/Review with Golden Rules

## Installation

### Prerequisites

- Node.js 25+
- npm or yarn

### Install from npm (when published)

```bash
npm install -g cursor-engineering-rules-mcp
```

### Install from source

```bash
cd mcp/cursor-rules-mcp
npm install
npm run build
npm link
```

## Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agent-engineering-handbook": {
      "command": "cursor-rules-mcp",
      "env": {
        "CURSOR_RULES_PATH": "/path/to/agent-engineering-handbook/rules"
      }
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json`:

```json
{
  "servers": {
    "agent-engineering-handbook": {
      "command": "cursor-rules-mcp",
      "env": {
        "CURSOR_RULES_PATH": "/path/to/agent-engineering-handbook/rules"
      }
    }
  }
}
```

### Environment Variables

- `CURSOR_RULES_PATH`: Optional path to rules directory (defaults to bundled rules)

## Usage

The MCP server provides three tools:

### 1. `fetch_workflow_guide`

Fetch the core workflow guide (Plan/Implement/Review with Golden Rules). **Essential reading for all AI agents.**

```typescript
// No arguments required
fetch_workflow_guide()
```

### 2. `fetch_rule`

Fetch a specific engineering rule.

```typescript
// Example: Fetch Python rules
fetch_rule({
  category: "languages",
  topic: "python"
})

// Example: Fetch AWS rules
fetch_rule({
  category: "cloud",
  topic: "aws"
})

// Example: Fetch Terraform rules
fetch_rule({
  category: "infrastructure",
  topic: "terraform"
})
```

**Available Categories:**

- `core`: workflow, context-engineering, agent-audit, core-principles, configuration, utilities, git
- `languages`: bash, python, go, rust, javascript, typescript
- `infrastructure`: justfile, cloudformation, terraform, ansible, docker, kubernetes, helm
- `cloud`: cloudflare, aws, aws-iam, gcp, azure
- `devops`: github-actions, cli
- `patterns`: testing, security, iam, zero-trust, okta, workload-identity, api-design, observability
- `data`: postgresql, sql, data-engineering, databricks, snowflake, kafka, teradata
- `ai`: ai-ml, mcp-servers
- `docs`: markdown, documentation, reactflow, open-source

### 3. `list_available_rules`

List all available engineering rules with categories, descriptions, and priorities.

```typescript
// No arguments required
list_available_rules()
```

## Example Workflow

1. **Start by reading the workflow guide:**

   ```typescript
   fetch_workflow_guide()
   ```

2. **List all available rules:**

   ```typescript
   list_available_rules()
   ```

3. **Fetch specific rules as needed:**

   ```typescript
   // Working on Python?
   fetch_rule({ category: "languages", topic: "python" })
   
   // Deploying to AWS?
   fetch_rule({ category: "cloud", topic: "aws" })
   
   // Writing Terraform?
   fetch_rule({ category: "infrastructure", topic: "terraform" })
   ```

## Rule Categories

### Core (Priority 10-130)

- **Workflow** (10): Plan/Implement/Review approach with Golden Rules
- **Context Engineering** (15): Prompt packing, retrieval, compaction
- **Agent Audit** (20): No remote writes, checkpoints, audit reports
- **Core Principles** (100): SOLID, DRY, KISS, YAGNI, Fail Fast
- **Configuration** (110): Config management, secrets, environments
- **Utilities** (120): Ripgrep, fzf, jq, yq, CLI tools
- **Git** (130): Conventional commits, branching, commit approval

### Languages (Priority 140-240)

- **Bash** (140): POSIX compliance, ShellCheck, safety patterns
- **Python** (200): Python 3.14+, type hints, AWS Lambda patterns
- **Go** (210): Idiomatic Go, error handling, concurrency
- **Rust** (220): Ownership, lifetimes, async patterns
- **JavaScript** (230): ES modules, async/await, Node.js
- **TypeScript** (240): Strict mode, ESM, modern patterns

### Infrastructure (Priority 150-460)

- **Justfile** (150): Modern command runner patterns
- **CloudFormation** (170): Templates, stacks, nested stacks
- **Terraform** (180): Modules, state management, workspaces
- **Ansible** (190): Playbooks, roles, idempotency
- **Docker** (440): Multi-stage builds, security, optimization
- **Kubernetes** (450): Manifests, operators, CRDs, security
- **Helm** (460): Charts, templating, releases

### Cloud (Priority 400-430)

- **Cloudflare** (400): Workers, Rules Engine, DNS, security
- **AWS** (410): EKS, VPC Lattice, Lambda, Zero Trust
- **AWS IAM** (412): Principals, SCPs, KMS, AccessDenied debugging
- **GCP** (420): GKE, Cloud Run, Secret Manager
- **Azure** (430): Bicep, Key Vault, App Service

### DevOps (Priority 160-250)

- **GitHub Actions** (160): Workflows, OIDC, security
- **CLI** (250): argparse, typer, rich, user experience

### Patterns (Priority 300-330)

- **Testing** (300): Unit, integration, E2E testing
- **Security** (310): OWASP, secrets, vulnerability scanning
- **IAM & Identity** (315): OIDC/OAuth2/PKCE, SAML, PKI, PAM
- **Zero Trust** (316): Distinguished-engineer Zero Trust for identity, network, data, workload, AI/agents
- **Okta** (317): Okta Workforce Identity (SSO, MFA, SCIM, policies, Workflows, ASA, terraform-provider-okta)
- **Workload Identity** (318): Attestation-based workload identity (SPIFFE/SPIRE, cloud IAM, OIDC federation)
- **API Design** (320): REST, GraphQL, gRPC patterns
- **Observability** (330): Logging, metrics, tracing

### Data (Priority 470-484)

- **PostgreSQL** (470): Schema design, migrations, performance, RLS
- **SQL** (475): DQL/DML/DDL/DCL/TCL, transactions, guardrails
- **Data Engineering** (480): Contracts, backfills, quality, governance
- **Databricks** (481): Spark, Delta, Unity Catalog, DLT
- **Snowflake** (482): RBAC, cost/perf, streams/tasks, loading
- **Kafka** (483): Topics, schemas, producers/consumers, DLQ
- **Teradata** (484): Indexes, stats, spool, joins, QUALIFY

### AI (Priority 500-510)

- **AI/ML** (500): LLM APIs, Bedrock, Vertex AI, prompt engineering, RAG
- **MCP Servers** (510): Model Context Protocol patterns

### Docs (Priority 800-820)

- **Markdown** (800): GFM, Mermaid diagrams
- **Documentation** (810): Docs sites, API docs, technical writing
- **React Flow diagrams** (815): Interactive architecture canvases
- **Open Source** (820): Contributing, licensing, community

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Watch mode
npm run watch

# Run locally
npm start
```

## Architecture

```
mcp/cursor-rules-mcp/
 src/
    api/
       client.ts          # API client for reading rules
    server/
       mcp-server.ts      # MCP server implementation
    index.ts               # Entry point
 package.json
 tsconfig.json
 README.md
```

## Comparison with AI Developer Guide

| Feature | AI Developer Guide | Agent Engineering Handbook |
|---------|-------------------|--------------------------|
| **Focus** | Workflow philosophy | Production standards |
| **Languages** | 3 (Python, Go, Shell) | 15+ |
| **Cloud Platforms** | 0 | 4 (AWS, Azure, GCP, Cloudflare) |
| **Infrastructure** | Basic | Comprehensive (Terraform, K8s, Docker, etc.) |
| **Security** | Basic | OWASP, IAM, secrets, compliance |
| **Best For** | Startups, teaching | Enterprise, production systems |

**Agent Engineering Handbook v2** combines both: workflow philosophy from AI Developer Guide + comprehensive production standards.

## Resources

- [Agent Engineering Handbook Repository](https://github.com/d-padmanabhan/agent-engineering-handbook)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Registry](https://github.com/modelcontextprotocol/registry)
- [MCP SDK](https://github.com/modelcontextprotocol/sdk)

## License

MIT

## Author

Platform Engineering Team

## Credits

- **Workflow Philosophy:** Inspired by [AI Developer Guide](https://github.com/dwmkerr/ai-developer-guide)
- **Technical Standards:** Comprehensive production-grade rules for enterprise engineering
